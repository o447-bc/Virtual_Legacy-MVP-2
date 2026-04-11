# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction," "Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution," "Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination," and "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to digital content access control systems, and more particularly to a computer-implemented system for managing conditional access to digital legacy content and AI avatar interactions based on multiple configurable release conditions including automated inactivity detection with dual-threshold verification.

---

## BACKGROUND OF THE INVENTION

[0003] As individuals accumulate significant digital assets — personal videos, audio recordings, written narratives, and other digital content — the question of how to manage access to these assets after the individual's death or incapacitation becomes increasingly important. Unlike physical assets governed by wills and estate law, digital assets often lack structured mechanisms for conditional transfer.

[0004] Existing digital asset management systems suffer from several limitations. First, most systems offer only binary access control — content is either accessible or not. There is no mechanism for a content creator to specify nuanced conditions under which different beneficiaries gain access at different times or under different circumstances.

[0005] Second, existing "dead man's switch" or inactivity-based release systems use simple time-based thresholds (e.g., "release after 6 months of inactivity"). These systems are prone to false positive activation — a person on an extended vacation, in a hospital, or simply taking a break from the platform may trigger premature content release. There is no verification mechanism to distinguish genuine incapacitation from temporary inactivity.

[0006] Third, no existing system extends conditional access controls to AI avatar interactions. As AI avatar technology matures, the ability for a content creator to specify when and to whom their AI avatar becomes available — with the same granularity as content access — becomes critical for ethical deployment.

[0007] There is therefore a need for a multi-condition access control system that supports diverse release conditions, implements robust inactivity detection with false-positive mitigation, and extends to govern AI avatar interactions.

---

## SUMMARY OF THE INVENTION

[0008] The present invention provides a computer-implemented system and method for managing conditional access to digital content and AI avatar interactions. A content creator designates beneficiaries and assigns access conditions from four types: immediate access, time-delayed access, inactivity-triggered access, and manual release. For inactivity-triggered conditions, the system implements a dual-threshold verification mechanism combining elapsed time with missed check-in count to reduce false positive activation. The same framework governs both content viewing and avatar interaction permissions.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture

[0009] FIG. 1 illustrates the system architecture according to an embodiment of the present invention. The system comprises an assignment management interface (110), an access conditions database (120), a relationships database (130), a time-delay processor (140), a check-in sender (150), an inactivity processor (160), a check-in response handler (170), and an access validation engine (180).

### 2. Access Condition Types

[0010] The system supports four types of access conditions, each with distinct activation criteria:

[0011] (a) Immediate Access: The beneficiary gains access upon accepting the relationship invitation. No additional conditions must be met. The condition is stored with condition_type = "immediate" and is considered satisfied as soon as the relationship status transitions to "accepted."

[0012] (b) Time-Delayed Access: Access is granted on or after a specific future date configured by the content creator. The condition is stored with condition_type = "time_delayed" and an activation_date field containing an ISO 8601 datetime string. The activation date must be validated to be in the future at the time of creation.

[0013] (c) Inactivity-Triggered Access: Access is granted when the content creator fails to respond to periodic check-in verifications for a configurable duration. This condition type implements the dual-threshold verification mechanism described in detail in Section 4 below. The condition is stored with condition_type = "inactivity_trigger" along with fields for inactivity_months (configurable 1-24 months), check_in_interval_days (default 30 days), consecutive_missed_check_ins (counter), and last_check_in (timestamp).

[0014] (d) Manual Release: The content creator explicitly releases access at any time. The condition is stored with condition_type = "manual_release" and a released_at field that is populated when the creator triggers release.

[0015] Multiple conditions can be assigned to a single content creator-beneficiary relationship. All conditions must be satisfied for access to be granted (conjunctive evaluation). The content creator can specify different conditions for content viewing permission versus avatar interaction permission for the same beneficiary.

### 3. Data Model

[0016] FIG. 2 illustrates the data model according to an embodiment of the present invention.

[0017] The relationships database (130) stores content creator-beneficiary relationships with the following schema: primary key = initiator_id (content creator's user identifier), sort key = related_user_id (beneficiary's user identifier), and attributes including relationship_type, status (pending/accepted/active/revoked), created_at, and updated_at. A Global Secondary Index (GSI) on related_user_id enables efficient reverse lookups (finding all relationships where a given user is a beneficiary).

[0018] The access conditions database (120) stores individual access conditions with the following schema: primary key = relationship_key (a composite string formed by concatenating initiator_id + "#" + related_user_id), sort key = condition_id (a UUID). Additional attributes vary by condition type. Two GSIs enable efficient querying: an ActivationDateIndex (partition key = condition_type, sort key = activation_date) for time-delayed condition processing, and a ConditionTypeIndex (partition key = condition_type) for inactivity condition processing.

[0019] The composite relationship_key design enables efficient querying of all conditions for a specific relationship using a single query operation, while the GSIs enable the scheduled processors to efficiently find all conditions of a given type across all relationships.

### 4. Dual-Threshold Inactivity Detection

[0020] FIG. 3 illustrates the dual-threshold inactivity detection mechanism according to an embodiment of the present invention. This mechanism is the core innovation for the inactivity-triggered access condition type.

[0021] The mechanism comprises three scheduled serverless processes operating in coordination:

[0022] Process 1 — Check-In Sender (executed daily): This process queries the access conditions database for all inactivity_trigger conditions with status = "pending." For each condition, it calculates the days since the last check-in email was sent (or since the condition was created, if no email has been sent). If the elapsed days meet or exceed the configured check_in_interval_days (default 30), the process:

[0023] (a) Generates a unique verification token (UUID).

[0024] (b) Stores the token in a temporary data store with a 7-day TTL, associated with the content creator's user identifier and the condition identifier.

[0025] (c) Sends a verification email to the content creator containing a link with the embedded token (e.g., https://app.example.com/check-in?token={uuid}).

[0026] (d) Increments the consecutive_missed_check_ins counter for the condition.

[0027] (e) Updates the last_check_in_sent timestamp.

[0028] Process 2 — Check-In Response Handler (triggered by user action): When the content creator clicks the verification link in the email, the handler:

[0029] (a) Validates the token against the temporary data store (checking existence and TTL).

[0030] (b) Resets the consecutive_missed_check_ins counter to zero.

[0031] (c) Updates the last_check_in timestamp to the current time.

[0032] (d) Deletes the used token from the temporary data store.

[0033] This response confirms that the content creator is alive and active, preventing false positive activation.

[0034] Process 3 — Inactivity Processor (executed daily): This process queries the access conditions database for all inactivity_trigger conditions with status = "pending." For each condition, it evaluates the dual threshold:

[0035] Threshold 1 — Time Elapsed: The process calculates the months since the last verified check-in (last_check_in timestamp) using calendar-accurate month calculation (e.g., relativedelta). The elapsed months must meet or exceed the configured inactivity_months.

[0036] Threshold 2 — Missed Check-In Count: The process calculates the minimum expected missed check-ins based on the configured duration and interval: expected_check_ins = max(1, (inactivity_months × 30) / check_in_interval_days). The consecutive_missed_check_ins must meet or exceed max(1, expected_check_ins / 2).

[0037] Both thresholds must be satisfied simultaneously for activation. This dual-threshold approach significantly reduces false positive activation compared to time-only approaches because:

[0038] (a) A person who is temporarily inactive but responds to even one check-in email resets the missed counter, preventing activation.

[0039] (b) The time threshold alone would activate after the configured months regardless of whether check-ins were sent or received.

[0040] (c) The missed counter alone could accumulate due to email delivery failures rather than genuine inactivity.

[0041] (d) Requiring both thresholds ensures that sufficient time has passed AND the content creator has had multiple opportunities to verify their activity and failed to do so.

[0042] Upon dual-threshold satisfaction, the inactivity processor: (a) updates the relationship status to "active" in the relationships database; (b) updates the condition status to "activated" in the access conditions database with an activated_at timestamp; (c) sends a notification email to the beneficiary informing them that access has been granted; and (d) logs the activation event with structured metadata for audit purposes.

### 5. Time-Delayed Condition Processing

[0043] A time-delay processor (executed hourly) queries the access conditions database using the ActivationDateIndex GSI for time_delayed conditions where activation_date is less than or equal to the current time and status is "pending." For each matching condition, the processor updates the relationship status to "active," updates the condition status to "activated," sends a notification email to the beneficiary, and logs the activation event.

### 6. Access Validation

[0044] FIG. 4 illustrates the access validation flow according to an embodiment of the present invention.

[0045] When a requesting user attempts to access a content creator's content or interact with their AI avatar, the access validation engine evaluates all applicable conditions:

[0046] Step 1: Check for self-access (always permitted).

[0047] Step 2: Query the relationships database for a direct relationship (requesting user as beneficiary of the content creator). If found with status "active," proceed to condition evaluation.

[0048] Step 3: If no direct relationship found, query the relationships database using the reverse GSI (content creator as initiator, requesting user as related user). This handles cases where the content creator initiated the relationship.

[0049] Step 4: For the found relationship, query the access conditions database for all conditions using the composite relationship_key.

[0050] Step 5: Evaluate each condition against its type-specific criteria:
- Immediate: Always satisfied.
- Time-delayed: Satisfied if current time >= activation_date.
- Inactivity-trigger: Satisfied if condition status = "activated."
- Manual release: Satisfied if released_at is populated.

[0051] Step 6: If all conditions are satisfied, return access granted with the applicable permission types (content viewing, avatar interaction, or both). If any condition is unsatisfied, return access denied with a list of unmet conditions including type-specific details (e.g., remaining time for time-delayed, remaining inactivity period for inactivity-trigger).

### 7. Differentiated Content and Avatar Access

[0052] The system supports differentiated access conditions for content viewing versus AI avatar interaction. A content creator can configure, for example: content viewing access with a time-delayed condition (available after a specific date), and avatar interaction access with an inactivity-triggered condition (available only if the creator becomes inactive). This enables scenarios such as: "My children can view my recorded memories starting January 1, 2030, but can only interact with my AI avatar if I become inactive for 12 months."

[0053] The access validation engine evaluates conditions separately for each permission type and returns per-permission-type access determinations.

### 8. Dual-Persona User Management

[0054] The system implements a dual-persona architecture where each user is assigned a persona type at registration. The two persona types are: content creator (referred to as "Legacy Maker" in the preferred embodiment) who records personal narratives and manages beneficiary assignments, and content viewer (referred to as "Legacy Benefactor") who views content and interacts with avatars under the configured access conditions.

[0055] The persona type is stored as a JSON object within the "profile" claim of the user's authentication token (e.g., a Cognito JWT). The JSON object contains at minimum: persona_type, the user's own identifier (initiator_id), and a related_user_id field. This approach embeds persona data directly in the authentication token, eliminating the need for a separate database lookup on each API request.

[0056] A server-side PersonaValidator component extracts the persona from the JWT on each API request and enforces persona-based access control. Content creation endpoints (e.g., video upload, conversation initiation) require the content creator persona. Content viewing endpoints (e.g., viewing another user's videos) require the content viewer persona. The validator also enriches API responses with persona context (persona_type, user_id, is_initiator) enabling the client application to adapt its interface.

### 9. Cross-Registration Invitation Linking

[0057] When a content creator designates a beneficiary who does not have an existing account, the system implements a cross-registration linking flow:

[0058] Step 1: The system generates a UUID invitation token and stores it in a temporary database (PersonaSignupTempDB) with a 30-day TTL. The stored record associates the token with the content creator's identifier, the beneficiary's email address (normalized to lowercase), the invite type ("maker_assignment"), and the full assignment details including access conditions.

[0059] Step 2: An invitation email is sent to the beneficiary containing a registration URL with the token embedded as a query parameter (e.g., /signup/create-legacy?invite={token}).

[0060] Step 3: When the beneficiary clicks the link and initiates registration, the client application extracts the invite parameter and passes it through the signup function as client metadata.

[0061] Step 4: The pre-signup authentication trigger receives the client metadata, stores the invitation token and persona type in the temporary database keyed by the user's identifier (with 1-hour TTL), and auto-confirms the user (bypassing email verification since the email was already validated by the invitation).

[0062] Step 5: The post-confirmation authentication trigger retrieves the stored data, validates the invitation token against the temporary database, verifies that the registering user's email matches the invited email (case-insensitive comparison), creates the relationship record in the relationships database, creates access condition records in the access conditions database, and deletes the consumed invitation token.

### 10. Transactional Rollback

[0063] The assignment creation process implements transactional rollback to prevent orphaned database records. The creation flow proceeds in order: (1) create relationship record, (2) create access condition records, (3) create invitation token (if beneficiary is unregistered), (4) send email. If any step fails, all previously completed steps are rolled back: if email sending fails, the relationship record, access condition records, and invitation token are all deleted. This ensures that no partial assignment state exists in the database.

### 11. Pre-Signup to Post-Confirmation Data Pipeline

[0064] The persona assignment process spans two authentication triggers with a temporary database bridging the gap. The pre-signup trigger stores persona selection data (persona_type, persona_choice, invite_token, first_name, last_name) in a temporary database record with a 1-hour TTL. The post-confirmation trigger retrieves this data, applies it to the user's authentication profile, and deletes the temporary record. The post-confirmation trigger includes a retry mechanism that attempts the persona attribute write up to 3 times with 0.5-second exponential backoff. If all retries are exhausted, a CloudWatch metric (PersonaWriteFailure) is emitted for operational alerting, but the signup process is not failed — the user defaults to the content creator persona.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0054] FIG. 1 is a block diagram illustrating the system architecture of the conditional access control system.

[0055] FIG. 2 is a diagram illustrating the data model including the relationships database, access conditions database, and their key structures.

[0056] FIG. 3 is a flow diagram illustrating the dual-threshold inactivity detection mechanism with the three coordinating scheduled processes.

[0057] FIG. 4 is a flow diagram illustrating the access validation process.

---

## DRAWINGS

### FIG. 3 — Dual-Threshold Inactivity Detection

```
┌─────────────────────────────────────────────────────────────┐
│              DUAL-THRESHOLD INACTIVITY DETECTION             │
│                                                              │
│  PROCESS 1: CHECK-IN SENDER (Daily)                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ For each inactivity_trigger condition (status=pending): │  │
│  │                                                         │  │
│  │ IF days_since_last_sent >= check_in_interval_days:      │  │
│  │   1. Generate UUID token                                │  │
│  │   2. Store token (7-day TTL)                            │  │
│  │   3. Email creator: "Click to confirm active"           │  │
│  │   4. INCREMENT consecutive_missed_check_ins             │  │
│  │   5. Update last_check_in_sent                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                    │
│                          ▼                                    │
│  PROCESS 2: CHECK-IN RESPONSE (User-triggered)               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ When creator clicks verification link:                  │  │
│  │                                                         │  │
│  │   1. Validate token (exists + not expired)              │  │
│  │   2. RESET consecutive_missed_check_ins = 0             │  │
│  │   3. Update last_check_in = now()                       │  │
│  │   4. Delete used token                                  │  │
│  │                                                         │  │
│  │ ──► PREVENTS FALSE POSITIVE ACTIVATION                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                          │                                    │
│                          ▼                                    │
│  PROCESS 3: INACTIVITY PROCESSOR (Daily)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ For each inactivity_trigger condition (status=pending): │  │
│  │                                                         │  │
│  │ THRESHOLD 1: months_since_last_check_in                 │  │
│  │              >= inactivity_months                        │  │
│  │                                                         │  │
│  │              AND                                        │  │
│  │                                                         │  │
│  │ THRESHOLD 2: consecutive_missed_check_ins               │  │
│  │              >= max(1, expected_check_ins / 2)           │  │
│  │                                                         │  │
│  │ where expected = (inactivity_months × 30)               │  │
│  │                  / check_in_interval_days                │  │
│  │                                                         │  │
│  │ IF BOTH THRESHOLDS MET:                                 │  │
│  │   1. Update relationship status → "active"              │  │
│  │   2. Update condition status → "activated"              │  │
│  │   3. Notify beneficiary via email                       │  │
│  │   4. Log activation event                               │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## CLAIMS

1. A computer-implemented method for managing conditional access to digital content and AI avatar interactions in a cloud computing environment, the method comprising:

   receiving, from a content creator via a client application, a designation of a beneficiary and one or more access conditions, each access condition specifying criteria for granting the beneficiary a permission type selected from at least content viewing permission and avatar interaction permission;

   storing each access condition as a record in a database using a composite key comprising identifiers of the content creator and the beneficiary;

   for an access condition of an inactivity-trigger type:
   - (a) executing a first scheduled process at a first interval to generate a unique verification token, store the token with a time-to-live expiration, and transmit a verification message containing the token to the content creator;
   - (b) incrementing a missed-verification counter for the access condition upon each execution of the first scheduled process;
   - (c) upon receipt of a valid verification token from the content creator, resetting the missed-verification counter to zero and updating a last-verified timestamp;
   - (d) executing a second scheduled process at a second interval to evaluate whether both (i) a duration since the last-verified timestamp exceeds a configurable inactivity threshold and (ii) the missed-verification counter exceeds a minimum missed-verification threshold derived from the inactivity threshold and the first interval; and
   - (e) upon both conditions of step (d) being satisfied, activating the access condition and granting the beneficiary the specified permission type.

2. The method of claim 1, further comprising, for an access condition of a time-delayed type:
   executing a third scheduled process at a third interval to query the database for time-delayed conditions where an activation date is earlier than a current time and a status is pending;
   for each matching condition, transitioning the relationship status to active and transmitting a notification to the beneficiary.

3. The method of claim 1, wherein the minimum missed-verification threshold is calculated as the integer division of the product of the inactivity threshold in months and thirty, divided by the first interval in days, divided by two.

4. The method of claim 1, wherein the content creator specifies different access conditions for content viewing permission and avatar interaction permission for the same beneficiary, enabling the content creator to grant content viewing access under a first set of conditions and avatar interaction access under a second, more restrictive set of conditions.

5. The method of claim 1, further comprising:
   receiving, from a requesting user, an access validation request specifying a target content creator;
   querying the database for all access conditions associated with the relationship;
   evaluating each access condition against its type-specific criteria; and
   returning an access determination comprising a boolean access grant per permission type and, when access is denied, a list of unmet conditions with type-specific details.

6. The method of claim 1, wherein the composite key is a string concatenation of the content creator identifier, a delimiter character, and the beneficiary identifier, and wherein the database includes a secondary index on the condition type attribute enabling efficient querying of all conditions of a given type across all relationships.

7. The method of claim 1, further comprising, for an access condition of a manual-release type, receiving an explicit release instruction from the content creator and activating the access condition in response, wherein the manual release is revocable by the content creator at any time prior to the content creator's account becoming inactive.

8. The method of claim 1, further comprising a dual-persona user management system wherein:
   - each user is assigned a persona type selected from at least a content creator persona and a content viewer persona at the time of registration;
   - the persona type is stored as a structured data object within a claim of the user's authentication token, the structured data object comprising at least the persona type, the user's identifier, and a related user identifier;
   - a server-side persona enforcement component extracts the persona type from the authentication token on each API request and validates that the requesting user's persona type is authorized for the requested operation; and
   - API responses are enriched with persona context data enabling the client application to adapt its user interface based on the user's persona type.

9. The method of claim 1, further comprising a cross-registration invitation linking process for designating a beneficiary who does not have an existing account, the process comprising:
   - generating a unique invitation token and storing the token in a temporary data store with a time-to-live expiration, the stored record associating the token with the content creator's identifier, the beneficiary's email address, and the specified access conditions;
   - transmitting an invitation message to the beneficiary's email address containing a registration URL with the invitation token embedded as a parameter;
   - upon the beneficiary initiating registration via the registration URL, extracting the invitation token from the URL and passing it through the registration process as client metadata;
   - during a pre-registration trigger, storing the invitation token and persona type in the temporary data store for retrieval by a post-registration trigger;
   - during a post-registration trigger, retrieving the invitation token, validating the token against the temporary data store, verifying that the registering user's email matches the invited email, creating the relationship record and access condition records in the database, and deleting the consumed invitation token; and
   - automatically confirming the beneficiary's account without requiring separate email verification, on the basis that the email address was validated when the content creator sent the invitation.

10. The method of claim 9, further comprising transactional rollback logic wherein:
    - if the invitation email fails to send during assignment creation, the system deletes the previously created relationship record and access condition records from the database, preventing orphaned data;
    - if the invitation token creation fails, the system deletes the previously created relationship record; and
    - the assignment creation operation returns a failure response to the client only after all rollback operations have completed.

11. The method of claim 8, wherein the persona type assignment during registration comprises:
    - a pre-registration authentication trigger that receives the user's persona selection from the client application, stores the persona selection along with any invitation token in a temporary database record keyed by the user's identifier with a time-to-live expiration;
    - a post-registration authentication trigger that retrieves the persona selection from the temporary database record, writes the persona type as a structured JSON object to the user's authentication profile attribute, and deletes the temporary record; and
    - a retry mechanism in the post-registration trigger that attempts the persona attribute write up to a configurable number of times with exponential backoff, and upon exhaustion of retries, emits a monitoring metric indicating persona write failure.

---

## ABSTRACT

A computer-implemented system and method for managing conditional access to digital content and AI avatar interactions. A content creator designates beneficiaries and assigns access conditions from four types: immediate, time-delayed, inactivity-triggered, and manual release. For inactivity-triggered conditions, a dual-threshold verification mechanism requires both elapsed time and missed check-in count to exceed configurable thresholds before activation, reducing false positives. The same framework governs both content viewing and AI avatar interaction permissions, enabling differentiated access conditions per permission type per beneficiary.
