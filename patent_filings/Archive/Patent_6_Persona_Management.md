# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Dual-Persona Digital Legacy Platform with Token-Based Cross-Registration Beneficiary Onboarding

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction," "Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution," "Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination," "Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation," and "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to digital content management platforms with role-based access control, and more particularly to a computer-implemented system for managing a digital legacy platform with dual-persona user management, token-based invitation and cross-registration linking for unregistered beneficiaries, and transactional integrity guarantees for multi-step assignment creation workflows.

---

## BACKGROUND OF THE INVENTION

[0003] Digital legacy platforms enable individuals to create and preserve personal content (videos, audio recordings, written narratives) for designated recipients. These platforms require a user management system that distinguishes between content creators and content viewers, and that supports the common scenario where a content creator wishes to designate a recipient who does not yet have an account on the platform.

[0004] Existing platforms handle this scenario poorly. Most systems either require the recipient to create an account independently and then manually link to the content creator, or they send a simple invitation email that provides no automatic linking upon registration. This creates friction, data integrity issues, and a poor user experience.

[0005] Specific technical challenges include: (a) maintaining persona identity across the gap between user registration and account confirmation in authentication systems that use multi-stage triggers (e.g., pre-signup and post-confirmation); (b) atomically linking a newly registered user to a pre-existing assignment without race conditions or orphaned records; (c) ensuring that if any step in a multi-step assignment creation process fails (database writes, token creation, email sending), all previously completed steps are rolled back; and (d) embedding persona data in authentication tokens to avoid per-request database lookups while maintaining security.

[0006] There is therefore a need for a digital legacy platform with robust dual-persona management, seamless cross-registration beneficiary onboarding, and transactional integrity for assignment workflows.

---

## SUMMARY OF THE INVENTION

[0007] The present invention provides a computer-implemented system for managing a digital legacy platform with two distinct user personas — content creators who record personal narratives and content viewers who access the recorded content under configurable conditions. The system implements a complete lifecycle for designating content viewers, including a token-based invitation flow that seamlessly links newly registered users to pre-existing assignments, a pre-registration to post-registration data pipeline that preserves persona selection across authentication trigger stages, and transactional rollback logic that prevents orphaned database records when multi-step operations partially fail.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture Overview

[0008] FIG. 1 illustrates the overall system architecture according to an embodiment of the present invention. The system comprises a client application (110) with dual registration paths, an authentication service (120) with pre-registration and post-registration triggers, a temporary data store (130), a relationships database (140), an access conditions database (150), an invitation management subsystem (160), a persona enforcement layer (170), and an email notification service (180).

### 2. Dual-Persona User Model

[0009] The system defines two distinct user personas:

[0010] (a) Content Creator (referred to as "Legacy Maker" in the preferred embodiment): A user who records personal narratives through AI-guided conversations and video recordings, manages beneficiary assignments, and configures access conditions for their content.

[0011] (b) Content Viewer (referred to as "Legacy Benefactor" in the preferred embodiment): A user who views content created by one or more content creators, subject to the access conditions configured by each content creator.

[0012] The persona type is determined at registration time based on the user's selection from the client application. The client application provides two distinct registration paths: a first path for users who wish to create their own legacy (content creator persona), and a second path for users who wish to help preserve someone else's legacy (content viewer persona). A third path handles invited users who arrive via an invitation link — these users are assigned the content viewer persona automatically.

### 3. Persona Storage in Authentication Tokens

[0013] FIG. 2 illustrates the persona data flow through the authentication system according to an embodiment of the present invention.

[0014] The persona type is stored as a structured JSON object within the "profile" claim of the user's authentication token (e.g., a JWT issued by an authentication service such as AWS Cognito). The JSON object contains:

```json
{
  "persona_type": "legacy_maker" | "legacy_benefactor",
  "initiator_id": "<user's own Cognito sub>",
  "related_user_id": "<linked user ID or empty string>"
}
```

[0015] This approach provides several technical advantages: (a) the persona is available on every authenticated request without a database lookup, reducing latency and database load; (b) the persona data is cryptographically signed as part of the JWT, preventing client-side tampering; (c) the structured JSON format allows additional persona metadata to be added without schema changes to the authentication service.

### 4. Pre-Registration to Post-Registration Data Pipeline

[0016] The authentication service uses a two-stage trigger architecture (pre-registration and post-registration) with a temporal gap between them during which the user confirms their account. Persona selection data must survive this gap. The system implements a temporary data pipeline:

[0017] Stage 1 — Pre-Registration Trigger: When a user initiates registration, the client application passes the persona selection (e.g., "create_legacy", "setup_for_someone", "create_legacy_invited", "benefactor_invited") as client metadata. The pre-registration trigger function:

[0018] (a) Maps the client-facing persona choice to an internal persona type ("legacy_maker" or "legacy_benefactor") using a deterministic mapping function.

[0019] (b) Stores the persona type, persona choice, any invitation token, and the user's first and last name in a temporary database record keyed by the user's identifier, with a 1-hour TTL for automatic cleanup.

[0020] (c) If the user is registering via an invitation (invitation token present), sets the auto-confirm and auto-verify-email flags on the authentication response, bypassing the email verification step. This is secure because the email address was already validated when the content creator sent the invitation to that specific address.

[0021] Stage 2 — Post-Registration Trigger: After the user's account is confirmed, the post-registration trigger function:

[0022] (a) Retrieves the persona data from the temporary database using the user's identifier as the key.

[0023] (b) Constructs the persona JSON object and writes it to the user's "profile" attribute in the authentication service using an administrative API call.

[0024] (c) If a first name and last name were stored, writes them to the user's "given_name" and "family_name" attributes.

[0025] (d) Deletes the temporary database record to prevent stale data accumulation.

[0026] (e) If an invitation token is present, processes the invitation linking (described in Section 6 below).

[0027] The post-registration trigger includes a retry mechanism that attempts the persona attribute write up to 3 times with exponential backoff (0.5 seconds, 1.0 second). If all retries are exhausted, the function emits a CloudWatch metric ("PersonaWriteFailure") for operational alerting but does not fail the registration process — the user defaults to the content creator persona on subsequent logins.

### 5. Server-Side Persona Enforcement

[0028] A centralized PersonaValidator component provides server-side persona enforcement across all API endpoints:

[0029] (a) Persona Extraction: The `get_user_persona_from_jwt()` method extracts the persona JSON from the authentication token's "profile" claim, parsing it from the JWT claims provided by the API gateway authorizer. It returns a structured object containing user_id, email, persona_type, initiator_id, and related_user_id.

[0030] (b) Access Validation: The `validate_legacy_maker_access()` and `validate_legacy_benefactor_access()` methods check that the requesting user's persona type matches the required persona for the endpoint. Content creation endpoints (video upload, conversation initiation, assignment creation) require the content creator persona. Content viewing endpoints (viewing another user's videos, accessing transcripts) require the content viewer persona.

[0031] (c) Standardized Denial Response: The `create_access_denied_response()` method generates a consistent 403 response with CORS headers and a structured error body containing the error message and error type ("AccessDenied").

[0032] (d) Response Enrichment: The `add_persona_context_to_response()` method appends persona context (persona_type, user_id, is_initiator) to API response bodies, enabling the client application to adapt its user interface based on the user's role without additional API calls.

### 6. Token-Based Invitation and Cross-Registration Linking

[0033] FIG. 3 illustrates the invitation and cross-registration linking flow according to an embodiment of the present invention.

[0034] When a content creator designates a beneficiary who does not have an existing account, the system implements the following flow:

[0035] Step 1 — Beneficiary Lookup: The system queries the authentication service for a user with the specified email address. If found, the beneficiary is an existing user and a direct notification is sent. If not found, the invitation flow is initiated.

[0036] Step 2 — Invitation Token Creation: The system generates a UUID invitation token and stores it in the temporary database with a 30-day TTL. The stored record contains: the token as the primary key, the content creator's identifier, the beneficiary's email address (normalized to lowercase), the invite type ("maker_assignment"), the full assignment details including all access conditions, and the creation timestamp.

[0037] Step 3 — Invitation Email: An email is sent to the beneficiary containing a registration URL with the token embedded as a query parameter (e.g., `https://app.example.com/signup/create-legacy?invite={token}`). The email includes a formatted description of the access conditions that will govern the beneficiary's access to the content creator's content.

[0038] Step 4 — Registration with Token: When the beneficiary clicks the link, the client application detects the `invite` query parameter, stores it in component state, and passes it through the registration function as client metadata along with the persona choice "create_legacy_invited".

[0039] Step 5 — Cross-Registration Linking: During the post-registration trigger, the system:

[0040] (a) Retrieves the invitation token from the temporary database.

[0041] (b) Validates that the invite type is "maker_assignment" (not another invite type).

[0042] (c) Verifies that the registering user's email matches the invited email (case-insensitive comparison) as a security check.

[0043] (d) Creates a relationship record in the relationships database with the content creator as initiator and the new user as related user, with status "pending" (awaiting beneficiary acceptance).

[0044] (e) Creates access condition records in the access conditions database using the composite relationship key (initiator_id + "#" + related_user_id), one record per configured access condition.

[0045] (f) Deletes the consumed invitation token from the temporary database.

[0046] (g) Sends a notification email to the new user informing them of the pending assignment.

### 7. Transactional Rollback for Assignment Creation

[0047] FIG. 4 illustrates the transactional rollback mechanism according to an embodiment of the present invention.

[0048] The assignment creation process involves multiple sequential database writes and an external email send. The system implements compensating transactions (rollback) to maintain data integrity:

[0049] The operations proceed in order: (1) create relationship record, (2) create access condition records, (3) create invitation token (if beneficiary is unregistered), (4) send email.

[0050] If step 2 fails: The relationship record created in step 1 is deleted.

[0051] If step 3 fails: The relationship record and access condition records are deleted.

[0052] If step 4 fails: The relationship record, access condition records, and invitation token are all deleted.

[0053] Only after all steps succeed does the system return a success response to the client. If any step fails and rollback completes, the system returns a failure response indicating that no assignment was created. This ensures that the database never contains partial assignment state — either the complete assignment exists (relationship + conditions + token + email sent) or nothing exists.

### 8. Duplicate Assignment Prevention

[0054] Before creating a new assignment, the system checks for an existing assignment between the same content creator and beneficiary by querying the relationships database. If a duplicate is found, the system returns a 409 Conflict response without creating any records. For unregistered beneficiaries, the system uses a composite identifier format ("pending#" + email address) as the beneficiary identifier, enabling duplicate detection even before the beneficiary has registered.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0055] FIG. 1 is a block diagram illustrating the overall system architecture of the dual-persona digital legacy platform.

[0056] FIG. 2 is a flow diagram illustrating the persona data flow through the pre-registration and post-registration authentication triggers.

[0057] FIG. 3 is a flow diagram illustrating the invitation and cross-registration linking process for unregistered beneficiaries.

[0058] FIG. 4 is a flow diagram illustrating the transactional rollback mechanism for assignment creation.

---

## DRAWINGS

### FIG. 2 — Persona Data Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATION                         │
│                                                               │
│  Path A: "Create Your Legacy"    Path B: "Start Their Legacy" │
│  persona_choice: create_legacy   persona_choice: setup_for_   │
│  persona_type: legacy_maker      someone                      │
│                                  persona_type: legacy_         │
│  Path C: Invited User            benefactor                   │
│  persona_choice: create_legacy_                               │
│  invited + invite_token                                       │
└──────────────────────┬───────────────────────────────────────┘
                       │ signupWithPersona(email, password,
                       │   persona_choice, persona_type,
                       │   firstName, lastName, inviteToken)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              PRE-REGISTRATION TRIGGER                         │
│                                                               │
│  1. Map persona_choice → persona_type                         │
│  2. Store in PersonaSignupTempDB:                             │
│     Key: userName (Cognito user ID)                           │
│     Data: persona_type, persona_choice, invite_token,         │
│           first_name, last_name                               │
│     TTL: 1 hour                                               │
│  3. If invite_token present:                                  │
│     → autoConfirmUser = true                                  │
│     → autoVerifyEmail = true                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ [User confirms account / auto-confirmed]
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              POST-REGISTRATION TRIGGER                        │
│                                                               │
│  1. Retrieve from PersonaSignupTempDB by userName             │
│  2. Build persona JSON:                                       │
│     {"persona_type": "...", "initiator_id": "...",            │
│      "related_user_id": ""}                                   │
│  3. Write to Cognito profile attribute (3 retries + backoff)  │
│  4. Write given_name, family_name if available                │
│  5. Delete temp record                                        │
│  6. If invite_token → link_registration_to_assignment()       │
│  7. On retry exhaustion → emit PersonaWriteFailure metric     │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              SUBSEQUENT API REQUESTS                          │
│                                                               │
│  JWT contains: { "profile": "{\"persona_type\":               │
│    \"legacy_maker\", \"initiator_id\": \"abc123\",            │
│    \"related_user_id\": \"\"}" }                              │
│                                                               │
│  PersonaValidator.get_user_persona_from_jwt(event)            │
│  → Extracts persona, enforces access, enriches response       │
└──────────────────────────────────────────────────────────────┘
```

### FIG. 3 — Invitation and Cross-Registration Linking

```
CONTENT CREATOR (Legacy Maker)
         │
         │ createAssignment(benefactor_email, access_conditions)
         ▼
┌──────────────────────┐
│ Lookup email in      │
│ Cognito              │
└──────┬───────────────┘
       │
  ┌────┴────┐
  │         │
FOUND    NOT FOUND
  │         │
  ▼         ▼
┌──────┐  ┌──────────────────────────────────────────┐
│Send  │  │ INVITATION FLOW                           │
│notif.│  │                                           │
│email │  │ 1. Create relationship record              │
└──────┘  │ 2. Create access condition records         │
          │ 3. Generate UUID invitation token           │
          │ 4. Store token in temp DB (30-day TTL):     │
          │    {userName: token, initiator_id: maker,   │
          │     benefactor_email: email,                │
          │     invite_type: "maker_assignment",        │
          │     assignment_details: {conditions}}       │
          │ 5. Send invitation email with link:         │
          │    /signup/create-legacy?invite={token}     │
          │                                            │
          │ ⚠ If step 5 fails → rollback steps 1-4    │
          └──────────────────┬───────────────────────┘
                             │
                             │ [Beneficiary clicks link]
                             ▼
          ┌──────────────────────────────────────────┐
          │ REGISTRATION WITH TOKEN                   │
          │                                           │
          │ Client detects ?invite= param             │
          │ Passes token as clientMetadata             │
          │ Pre-signup: stores token, auto-confirms    │
          │ Post-confirmation:                         │
          │   1. Validate token (exists + not expired) │
          │   2. Verify email match (case-insensitive) │
          │   3. Create relationship record             │
          │   4. Create access condition records        │
          │   5. Delete consumed token                  │
          │   6. Send welcome notification email        │
          └──────────────────────────────────────────┘
```

### FIG. 4 — Transactional Rollback

```
┌─────────────────────────────────────────────────────────┐
│              ASSIGNMENT CREATION FLOW                     │
│                                                          │
│  Step 1: Create relationship record ──────────► SUCCESS  │
│          │                                               │
│  Step 2: Create access conditions ────────────► SUCCESS  │
│          │                                               │
│  Step 3: Create invitation token ─────────────► SUCCESS  │
│          │                                               │
│  Step 4: Send invitation email ───────────────► FAIL ✗   │
│          │                                               │
│          ▼                                               │
│  ROLLBACK:                                               │
│    ✗ Delete invitation token (step 3)                    │
│    ✗ Delete access conditions (step 2)                   │
│    ✗ Delete relationship record (step 1)                 │
│          │                                               │
│          ▼                                               │
│  Return 500: "Failed to send invitation email.           │
│               No assignment was created."                │
│                                                          │
│  DATABASE STATE: Clean (no orphaned records)             │
└─────────────────────────────────────────────────────────┘
```

---

## CLAIMS

1. A computer-implemented system for managing a digital legacy platform with dual-persona user management and cross-registration beneficiary onboarding, the system comprising:

   an authentication service configured to manage user accounts, each user account associated with a persona type selected from at least a content creator persona and a content viewer persona;

   a client application providing at least two distinct registration paths, a first path for users selecting the content creator persona and a second path for users selecting the content viewer persona, wherein the selected persona type is transmitted to the authentication service as client metadata during registration;

   a pre-registration trigger function configured to receive the persona type from the client metadata, store the persona type in a temporary data store keyed by the user's identifier with a time-to-live expiration, and return a registration response;

   a post-registration trigger function configured to retrieve the persona type from the temporary data store, write the persona type as a structured data object to a claim of the user's authentication token, delete the temporary data store record, and process any pending invitation linkages; and

   a persona enforcement layer configured to, on each authenticated API request, extract the persona type from the authentication token claim and validate that the requesting user's persona type is authorized for the requested operation.

2. The system of claim 1, wherein the structured data object written to the authentication token claim is a JSON object comprising at least the persona type, the user's own identifier, and a related user identifier, and wherein the persona enforcement layer parses the JSON object from the token claim without performing a database lookup.

3. The system of claim 1, further comprising a cross-registration invitation linking subsystem configured to, when a content creator designates a beneficiary who does not have an existing account:
   - generate a unique invitation token and store the token in the temporary data store with a time-to-live expiration, the stored record associating the token with the content creator's identifier, the beneficiary's email address, and assignment details including access conditions;
   - transmit an invitation message to the beneficiary's email address containing a registration URL with the invitation token embedded as a parameter;
   - upon the beneficiary initiating registration via the registration URL, pass the invitation token through the registration process as client metadata;
   - during the pre-registration trigger, store the invitation token in the temporary data store and set auto-confirmation flags to bypass email verification; and
   - during the post-registration trigger, validate the invitation token, verify that the registering user's email matches the invited email, create a relationship record and access condition records in the database, and delete the consumed invitation token.

4. The system of claim 3, further comprising transactional rollback logic for assignment creation, wherein:
   - the assignment creation process comprises sequential steps of creating a relationship record, creating access condition records, creating an invitation token, and sending an invitation email;
   - if any step fails, all database records created by previously completed steps are deleted; and
   - the system returns a failure response to the client only after all rollback deletions have completed, ensuring that the database never contains partial assignment state.

5. The system of claim 1, wherein the post-registration trigger function includes a retry mechanism that attempts the persona attribute write up to a configurable number of times with exponential backoff, and upon exhaustion of retries, emits a monitoring metric indicating persona write failure without failing the registration process, such that the user account is created with a default persona type.

6. The system of claim 3, wherein for unregistered beneficiaries, the system uses a composite identifier format comprising a prefix string concatenated with the beneficiary's email address as a temporary beneficiary identifier in the relationship record, enabling duplicate assignment detection before the beneficiary has registered, and wherein upon the beneficiary's registration, the temporary identifier is replaced with the beneficiary's actual user identifier.

7. The system of claim 1, wherein the persona enforcement layer further comprises a response enrichment function that appends persona context data to API response bodies, the persona context data comprising the user's persona type, user identifier, and a boolean indicating whether the user is the initiator of the relevant relationship, enabling the client application to adapt its user interface based on the user's role without additional API calls.

8. The system of claim 3, wherein the invitation token is stored with a 30-day time-to-live expiration, and wherein the cross-registration linking subsystem performs a manual expiration check in addition to relying on the database's automatic TTL deletion, to handle the case where the TTL deletion has not yet been processed at the time of token validation.

9. A computer-implemented method for onboarding an unregistered beneficiary to a digital legacy platform, the method comprising:

   receiving, from a content creator, a designation of a beneficiary by email address and one or more access conditions;

   determining that no user account exists for the beneficiary's email address;

   creating a relationship record in a database associating the content creator with a temporary beneficiary identifier derived from the email address;

   creating access condition records in the database associated with the relationship;

   generating a unique invitation token and storing the token in a temporary data store with a time-to-live expiration, the stored record encoding the content creator's identifier, the beneficiary's email address, and the access conditions;

   transmitting an invitation email to the beneficiary containing a registration URL with the embedded invitation token;

   upon the beneficiary registering via the registration URL, automatically confirming the beneficiary's account without separate email verification;

   validating the invitation token and verifying that the registering user's email matches the invited email;

   creating a new relationship record associating the content creator with the beneficiary's actual user identifier and creating corresponding access condition records; and

   deleting the consumed invitation token from the temporary data store.

10. The method of claim 9, further comprising, if the invitation email fails to send, deleting the relationship record, the access condition records, and the invitation token from the database before returning a failure response, ensuring no orphaned records exist.

---

## ABSTRACT

A computer-implemented system for managing a digital legacy platform with dual-persona user management and seamless cross-registration beneficiary onboarding. Users are assigned a content creator or content viewer persona at registration, with the persona stored as a JSON object in the authentication token for zero-latency server-side enforcement. When a content creator designates an unregistered beneficiary, the system generates an invitation token, sends an invitation email with an embedded registration link, and upon the beneficiary's registration, automatically links the new account to the pending assignment by validating the token, verifying email match, and creating relationship and access condition records in a single atomic flow. Transactional rollback logic ensures that partial failures during assignment creation never leave orphaned database records.
