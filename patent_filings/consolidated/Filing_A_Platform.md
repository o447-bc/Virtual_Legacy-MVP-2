# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Digital Legacy Preservation Platform with AI-Guided Depth-Scored Conversation, Multi-Condition Access Control, and Dual-Persona User Management

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to a co-pending provisional application titled "AI Avatar Construction System with Structured Multimodal Data Collection, Psychological Profiling, and Advisory Reasoning," filed concurrently herewith and incorporated by reference in its entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to digital content preservation platforms, and more particularly to a computer-implemented system comprising: (a) an AI-guided conversational elicitation engine with real-time narrative depth scoring and adaptive termination; (b) a multi-condition access control system with automated inactivity detection for conditional content release to designated beneficiaries; and (c) a dual-persona user management architecture with token-based cross-registration beneficiary onboarding. The system is implemented as a serverless cloud-native application.

---

## BACKGROUND OF THE INVENTION

### Problems with Existing Personal Narrative Capture Systems

[0003] Existing personal narrative recording platforms — such as guided journaling applications, video testimony services, and oral history tools — suffer from a fundamental quality problem. These systems present questions or prompts to users but provide no mechanism for evaluating the quality or depth of the user's response. A user who provides a one-word answer receives the same treatment as a user who provides a rich, detailed narrative. There is no feedback loop that encourages deeper reflection or ensures that collected narratives meet a minimum quality standard suitable for long-term preservation or downstream processing.

[0004] Additionally, existing real-time conversational AI systems that use large language models (LLMs) for both response generation and response evaluation suffer from high latency when these operations are performed sequentially. In a voice conversation, latency of 4-8 seconds between a user's response and the AI's follow-up question disrupts natural conversational flow.

[0005] Furthermore, serverless computing environments are inherently stateless, yet multi-turn voice conversations require persistent state across invocations. Existing approaches either use dedicated servers (increasing cost and complexity) or lose state between turns.

### Problems with Existing Digital Asset Access Control

[0006] As individuals accumulate significant digital assets, the question of how to manage access after the individual's death or incapacitation becomes critical. Existing systems offer only binary access control — content is either accessible or not. There is no mechanism for nuanced, multi-condition release.

[0007] Existing "dead man's switch" systems use simple time-based thresholds (e.g., "release after 6 months of inactivity") that are prone to false positive activation. A person on extended vacation or in a hospital may trigger premature content release. There is no verification mechanism to distinguish genuine incapacitation from temporary inactivity.

### Problems with Existing Platform User Management

[0008] Digital legacy platforms require a user management system that distinguishes between content creators and content viewers, and that supports the common scenario where a content creator wishes to designate a recipient who does not yet have an account. Existing platforms handle this poorly — most require the recipient to create an account independently and then manually link to the content creator, creating friction and data integrity issues.

[0009] There is therefore a need for an integrated digital legacy platform that combines quality-controlled narrative elicitation, multi-condition access control with robust inactivity detection, and seamless dual-persona user management with cross-registration beneficiary onboarding.

---

## SUMMARY OF THE INVENTION

[0010] The present invention provides an integrated digital legacy preservation platform comprising three interconnected subsystems.

[0011] First, a conversational elicitation engine conducts real-time AI-guided voice conversations where a scoring model evaluates the narrative depth of each user response and the conversation continues until a cumulative quality threshold is met. Two large language models operate in parallel — one generating follow-up questions, one scoring depth — reducing per-turn latency by approximately 50%. Conversation state is persisted in a database with TTL-based cleanup, enabling stateful interactions in a stateless serverless environment.

[0012] Second, a multi-condition access control system enables content creators to designate beneficiaries with configurable release conditions including immediate access, time-delayed access, inactivity-triggered access with dual-threshold verification, and manual release. Scheduled serverless processors evaluate conditions automatically.

[0013] Third, a dual-persona user management system assigns each user a content creator or content viewer persona at registration, stores the persona in the authentication token for zero-latency enforcement, and implements a token-based invitation flow that seamlessly links newly registered beneficiaries to pre-existing assignments with transactional rollback on partial failure.

---

## DETAILED DESCRIPTION OF THE INVENTION

### Part I — System Architecture Overview

[0014] FIG. 1 illustrates the overall system architecture according to an embodiment of the present invention. The platform is implemented as a serverless cloud-native application comprising: a client application (101) built as a single-page web application; an API gateway (102) providing both REST and WebSocket endpoints with authentication; a plurality of serverless compute functions (103) implementing business logic; a NoSQL database service (104) providing multiple tables for different data domains; encrypted object storage (105) for media files; an authentication service (106) with pre-registration and post-registration triggers; a text-to-speech service (107); speech-to-text services (108); a large language model service (109); a parameter store (110) for configuration; scheduled event processors (111); and an email notification service (112).

[0015] In a preferred embodiment, the system is deployed on Amazon Web Services using AWS SAM (Serverless Application Model) with the following specific services: React/TypeScript frontend on AWS Amplify, API Gateway (REST + WebSocket), Lambda functions (Python 3.12), DynamoDB, S3 with KMS encryption, Cognito for authentication, Amazon Polly for text-to-speech, Amazon Transcribe and Deepgram for speech-to-text, Amazon Bedrock (Claude models) for LLM capabilities, SSM Parameter Store for configuration, EventBridge for scheduled processing, and SES for email.

### Part II — Conversational Elicitation Engine with Depth Scoring

#### II.1 — Question Database and Category System

[0016] The system maintains a question database storing a plurality of questions organized into life-topic categories. In a preferred embodiment, categories include: childhood and early life, family relationships, romantic relationships, career and professional life, values and beliefs, life lessons and wisdom, hobbies and passions, challenges and adversity, achievements and milestones, and legacy and future hopes.

[0017] Within each category, questions are organized at multiple difficulty levels. A progress tracking subsystem maintains, for each user and each category: a current level identifier, a count of completed questions (numQuestComplete), an ordered list of remaining unanswered question identifiers at the current level (remainQuestAtCurrLevel), and a parallel list of remaining question texts (remainQuestTextAtCurrLevel).

[0018] When a user completes a conversation for a question, the system removes that question from the remaining questions lists and increments the completed count. When all questions at the current level within a category are completed, the system advances the user to the next level and populates the remaining questions lists with questions from the next level.

[0019] The client application presents per-category progress bars derived from this data, showing the percentage of questions completed within each category. These progress bars serve as the primary navigation mechanism, guiding the user's selection of which conversation to initiate next.

#### II.2 — WebSocket Connection and Authentication

[0020] When a user selects a question to answer, the client application establishes a persistent bidirectional WebSocket connection with the conversation engine. The WebSocket API gateway includes a custom authorizer function that validates the user's authentication token (e.g., a Cognito access token passed as a query parameter), extracts the user identifier, and generates an IAM policy allowing or denying the connection. Upon successful authorization, the connection identifier is stored in a connections tracking database (WebSocketConnectionsDB) with a 24-hour TTL.

#### II.3 — Conversation State Management

[0021] The conversation engine creates a ConversationState object for each conversation session, containing: connectionId, userId, questionId, questionText, turnNumber (initialized to 0), cumulativeScore (initialized to 0.0), turns (empty list), startedAt (current Unix timestamp), completed (false), and completionReason (null).

[0022] The state object is persisted to a NoSQL database (ConversationStateDB) keyed by connectionId, with a TTL of 2 hours. Custom conversion functions recursively convert between the database's Decimal numeric type and the application's float type during serialization and deserialization, preventing type errors. Each Lambda invocation deserializes the state, processes the turn, and re-serializes, enabling stateful multi-turn conversations within a stateless serverless environment. The TTL ensures automatic cleanup of abandoned conversations.

#### II.4 — Conversation Turn Processing

[0023] For each user response, the following steps occur:

[0024] Step 1 — Audio Upload via Presigned URL: The client requests a presigned upload URL from the conversation engine. The engine generates a presigned S3 PUT URL with a 15-minute expiration, scoped to the user's conversation path (conversations/{userId}/{questionId}/audio/turn-{N}-{timestamp}.webm). The client uploads audio directly to S3 using the presigned URL, bypassing the compute layer for efficiency. S3 bucket default encryption automatically applies KMS encryption to all uploads.

[0025] Step 2 — Three-Tier Cascading Transcription: The uploaded audio is transcribed using a cascading three-tier subsystem:

[0026] Tier 1 — External API (Deepgram): The audio is sent to an external transcription API via a presigned S3 GET URL. The API key is retrieved from a secure parameter store with in-memory caching. This tier provides the lowest latency (approximately 0.5 seconds average) but may fail due to API rate limits or network issues.

[0027] Tier 2 — Streaming Transcription (AWS Transcribe Streaming): Upon failure of Tier 1, the audio file is downloaded from S3, converted from WebM to PCM WAV format (16kHz, mono) using FFmpeg deployed as a Lambda layer, and streamed to the streaming transcription service in 16KB chunks. This tier provides moderate latency (approximately 5 seconds).

[0028] Tier 3 — Batch Transcription (AWS Transcribe): Upon failure of Tier 2, a batch transcription job is initiated. This tier provides the highest reliability but highest latency (approximately 15 seconds).

[0029] Each tier is wrapped in exception handling with timing instrumentation recording the latency of each attempt.

[0030] Step 3 — Parallel Depth Scoring and Response Generation: The transcribed text is simultaneously processed by two LLMs using a thread pool executor with 2 workers:

[0031] Worker 1 — Response Generation: A first LLM (e.g., Claude 3.5 Sonnet, temperature 0.7) generates a contextually-aware follow-up question. The model receives the full conversation history (all prior turns with user text and AI responses) and a configurable system prompt instructing it to act as an empathetic interviewer.

[0032] Worker 2 — Depth Scoring: A second LLM (e.g., Claude 3 Haiku, temperature 0.3) evaluates the narrative depth of the user's response and produces a numeric score and reasoning. The scoring model evaluates specificity of detail, emotional depth, personal reflection, unique perspective, and narrative completeness. The score is parsed from the model's response with fallback handling for various response formats (direct number, "Score: X\nReasoning: ..." format).

[0033] The parallel execution reduces per-turn latency by approximately 50% compared to sequential processing.

[0034] Step 4 — Score Accumulation and Continuation Decision: The depth score is added to the cumulative score in the conversation state object. The turn is recorded with user text, AI response, turn score, cumulative score, reasoning, and timestamp. The updated state is persisted to the database.

[0035] The system evaluates whether the conversation should continue by checking: (a) whether the cumulative score is below a configurable score threshold (e.g., 12 points), and (b) whether the turn count is below a configurable maximum (e.g., 20 turns). If both conditions are met, the AI's follow-up question is synthesized to speech via Amazon Polly (neural engine), stored in S3 with KMS encryption, and a presigned URL is transmitted to the client for playback.

[0036] Step 5 — Conversation Completion: When the cumulative score meets or exceeds the threshold (reason: "score_goal_reached") or the maximum turn count is reached (reason: "max_turns_reached"), the conversation terminates. The system: (a) saves the complete transcript to S3 as a JSON document; (b) updates the question status in userQuestionStatusDB with completion metadata; (c) updates the user's progress record in userQuestionLevelProgressDB; (d) invalidates the SSM Parameter Store cache for the user's completion count; (e) triggers synchronous summarization; and (f) transmits a completion message to the client.

#### II.5 — Conversation Summarization

[0037] Upon conversation completion, a summarization function processes the full transcript through a large language model (Bedrock Claude) and generates three distinct outputs: (a) a one-sentence summary (oneSentence), (b) a detailed narrative summary (detailedSummary), and (c) a numeric thoughtfulness score on a 0-5 scale (thoughtfulnessScore).

[0038] The summarization function includes: idempotency checking (skipping if already summarized), a per-question enable/disable flag (enableTranscript), transcript length limits (truncating at 100,000 characters), and content-type-specific field prefix routing. The three outputs are stored in the database using prefixes that vary based on the content type: "audio" for audio conversations, "video" for regular video recordings, and "videoMemory" for supplementary video memories.

#### II.6 — Multi-Modal Content Types

[0039] For each question, the system supports three distinct content types linked to a single database record (userQuestionStatusDB, keyed by userId + questionId):

[0040] (a) AI-Guided Audio Conversation: The primary content type produced by the depth-scored conversation engine. Stored with field prefix "audio" (e.g., audioTranscriptUrl, audioConversationScore, audioTurnCount, audioOneSentence, audioDetailedSummary, audioSummarizationStatus).

[0041] (b) Direct Video Recording: A video recorded by the user via the MediaRecorder API, uploaded to S3 via presigned URL. Stored with field prefix "video" (e.g., videoS3Location, videoTranscriptionStatus, videoOneSentence, videoDetailedSummary).

[0042] (c) Supplementary Video Memory: A video recorded after completion of an audio conversation, capturing the user's visual reflection. Linked to the existing conversation record via a database update operation (not a new record), using field prefix "videoMemory" (e.g., videoMemoryS3Location, videoMemoryRecorded, videoMemoryTimestamp). The update operation verifies that an existing conversation record exists before adding video memory fields.

#### II.7 — Asynchronous Video Processing Pipeline

[0043] Upon video upload, an asynchronous processing pipeline is triggered:

[0044] Stage 1 — Processing: A processing function verifies the uploaded video exists in S3 (HEAD request), extracts a thumbnail image using FFmpeg deployed as a Lambda layer. The thumbnail extraction uses smart seek — the function detects the video duration, then seeks to the calculated midpoint (duration / 2) to capture a representative frame rather than the first frame. The thumbnail is scaled to 200 pixels wide and uploaded to S3.

[0045] Stage 2 — Transcription: An asynchronous transcription job is initiated. An EventBridge rule triggers a transcript processing function upon job completion.

[0046] Stage 3 — Summarization: The transcript processing function invokes the summarization function to generate the three structured outputs.

[0047] Each stage operates independently with graceful failure handling. The original video upload returns a success response immediately, regardless of whether thumbnail generation, transcription, or summarization succeeds.

#### II.8 — Configuration Management

[0048] Conversation parameters are stored in SSM Parameter Store and batch-fetched (using the batch get_parameters API) on the first invocation of each Lambda container. Parameters include: score_goal, max_turns, llm_conversation_model, llm_scoring_model, system_prompt, scoring_prompt, polly_voice_id, and polly_engine. A module-level cache dictionary persists across invocations within the same Lambda container via container reuse, providing sub-millisecond parameter access on warm invocations. Default values are applied for any parameters not found. This enables zero-downtime configuration changes.

#### II.9 — Engagement Streak System

[0049] An engagement subsystem tracks daily content creation activity using a dedicated database table (EngagementDB) with fields: userId, streakCount, lastVideoDate, streakFreezeAvailable, createdAt, lastUpdated.

[0050] The streak calculation is implemented as a pure function with the following business rules: (a) same-day activity — streak unchanged; (b) consecutive-day activity — streak increments by one; (c) missed day with freeze available — streak maintained, freeze consumed; (d) missed day without freeze — streak resets to one.

[0051] A monthly freeze replenishment process (scheduled Lambda) resets streakFreezeAvailable for all users on the first of each month. Milestone detection at configurable thresholds (7, 30, 100 days) emits CloudWatch metrics. All date calculations are timezone-aware using the user's configured timezone from userStatusDB.

[0052] The streak update is integrated into the video processing function with non-blocking error handling — video upload always succeeds even if the streak update fails. If streak calculator modules fail to import, a STREAK_ENABLED flag is set to false and streak tracking is silently disabled.

#### II.10 — SSM Parameter Store as Cache Layer

[0053] User completion counts are cached in SSM Parameter Store at keys like /virtuallegacy/user_completed_count/{userId} with application-level TTL (1 hour). The cache is invalidated (parameter deleted) on video completion or conversation completion events. This reduces DynamoDB query operations by approximately 80% compared to querying on every dashboard load.

### Part III — Multi-Condition Access Control System

#### III.1 — Access Condition Types

[0054] The system supports four types of access conditions:

[0055] (a) Immediate Access: The beneficiary gains access upon accepting the relationship invitation. Stored with condition_type = "immediate".

[0056] (b) Time-Delayed Access: Access is granted on or after a specific future date. Stored with condition_type = "time_delayed" and an activation_date field (ISO 8601). The activation date is validated to be in the future at creation time.

[0057] (c) Inactivity-Triggered Access: Access is granted when the content creator fails to respond to periodic check-in verifications for a configurable duration (1-24 months). Implements dual-threshold verification described in Section III.3. Stored with condition_type = "inactivity_trigger" along with inactivity_months, check_in_interval_days (default 30), consecutive_missed_check_ins (counter), and last_check_in (timestamp).

[0058] (d) Manual Release: The content creator explicitly releases access at any time. Stored with condition_type = "manual_release" and a released_at field populated upon release.

[0059] Multiple conditions can be assigned to a single relationship. All conditions must be satisfied for access to be granted (conjunctive evaluation). Different conditions can be specified for content viewing permission versus avatar interaction permission for the same beneficiary.

#### III.2 — Data Model

[0060] The relationships database (PersonaRelationshipsDB) stores content creator-beneficiary relationships with primary key = initiator_id (content creator), sort key = related_user_id (beneficiary), and attributes including relationship_type, status (pending/accepted/active/revoked), created_at, updated_at, and created_via. A Global Secondary Index (RelatedUserIndex) on related_user_id enables efficient reverse lookups.

[0061] The access conditions database (AccessConditionsDB) stores individual conditions with primary key = relationship_key (composite string: initiator_id + "#" + related_user_id), sort key = condition_id (UUID). Two GSIs enable efficient scheduled processing: ActivationDateIndex (partition key = condition_type, sort key = activation_date) and ConditionTypeIndex (partition key = condition_type).

#### III.3 — Dual-Threshold Inactivity Detection

[0062] FIG. 4 illustrates the dual-threshold inactivity detection mechanism. Three scheduled serverless processes operate in coordination:

[0063] Process 1 — Check-In Sender (daily cron): Queries AccessConditionsDB for inactivity_trigger conditions with status = "pending". For each condition where days since last check-in sent meets or exceeds check_in_interval_days: (a) generates a UUID verification token; (b) stores the token in PersonaSignupTempDB with 7-day TTL, associated with the user ID and condition ID; (c) sends a verification email with a link containing the token; (d) increments consecutive_missed_check_ins; (e) updates last_check_in_sent timestamp.

[0064] Process 2 — Check-In Response Handler (user-triggered): When the content creator clicks the verification link: (a) validates the token against PersonaSignupTempDB; (b) resets consecutive_missed_check_ins to zero; (c) updates last_check_in to current time; (d) deletes the used token.

[0065] Process 3 — Inactivity Processor (daily cron): Queries AccessConditionsDB for inactivity_trigger conditions with status = "pending". For each condition, evaluates the dual threshold:

[0066] Threshold 1: months_since_last_check_in >= inactivity_months (calculated using calendar-accurate relativedelta).

[0067] Threshold 2: consecutive_missed_check_ins >= max(1, expected_check_ins / 2), where expected_check_ins = max(1, (inactivity_months × 30) / check_in_interval_days).

[0068] Both thresholds must be satisfied simultaneously. This dual-threshold approach reduces false positive activation because: a person who responds to even one check-in resets the counter; the time threshold alone would activate regardless of check-in attempts; the counter alone could accumulate from email delivery failures.

[0069] Upon dual-threshold satisfaction: (a) relationship status updated to "active"; (b) condition status updated to "activated" with activated_at timestamp; (c) notification email sent to beneficiary; (d) activation event logged with structured metadata.

#### III.4 — Time-Delayed Condition Processing

[0070] A time-delay processor (hourly cron) queries AccessConditionsDB using the ActivationDateIndex GSI for time_delayed conditions where activation_date <= current time and status = "pending". For each match: updates relationship status to "active", updates condition status to "activated", sends notification email, logs activation event.

#### III.5 — Access Validation

[0071] When a requesting user attempts to access content or interact with an avatar, the access validation engine:

[0072] (a) Checks for self-access (always permitted).

[0073] (b) Queries PersonaRelationshipsDB for a direct relationship. If found with status "active", proceeds to condition evaluation.

[0074] (c) If no direct relationship, queries using the RelatedUserIndex GSI for a reverse relationship.

[0075] (d) Queries AccessConditionsDB for all conditions using the composite relationship_key.

[0076] (e) Evaluates each condition: immediate (always satisfied), time-delayed (current time >= activation_date), inactivity-trigger (status = "activated"), manual release (released_at populated).

[0077] (f) Returns access granted if all conditions satisfied, or access denied with a list of unmet conditions including type-specific details (remaining time, remaining inactivity period, pending manual release).

### Part IV — Dual-Persona User Management

#### IV.1 — Persona Model

[0078] The system defines two user personas: content creator ("Legacy Maker") who records narratives, manages assignments, and configures access conditions; and content viewer ("Legacy Benefactor") who views content subject to access conditions.

[0079] The persona type is stored as a JSON object within the "profile" claim of the user's JWT authentication token:

```json
{
  "persona_type": "legacy_maker" | "legacy_benefactor",
  "initiator_id": "<user's Cognito sub>",
  "related_user_id": "<linked user ID or empty>"
}
```

[0080] This eliminates per-request database lookups for persona verification. The JSON is cryptographically signed as part of the JWT.

#### IV.2 — Pre-Registration to Post-Registration Data Pipeline

[0081] The authentication service uses a two-stage trigger architecture with a temporal gap during account confirmation. The system bridges this gap:

[0082] Pre-Registration Trigger: Receives persona selection from client metadata (e.g., "create_legacy" → legacy_maker, "setup_for_someone" → legacy_benefactor, "create_legacy_invited" → legacy_maker with invite token). Stores persona_type, persona_choice, invite_token, first_name, and last_name in PersonaSignupTempDB keyed by userName with 1-hour TTL. If invite_token is present, sets autoConfirmUser and autoVerifyEmail to true.

[0083] Post-Registration Trigger: Retrieves persona data from PersonaSignupTempDB. Constructs persona JSON and writes to user's "profile" attribute via admin API. Writes given_name and family_name if available. Deletes temporary record. Processes invitation linking if token present.

[0084] The post-registration trigger includes a retry mechanism (3 attempts, exponential backoff at 0.5s intervals). On retry exhaustion, emits a PersonaWriteFailure CloudWatch metric but does not fail registration — user defaults to content creator persona.

#### IV.3 — Server-Side Persona Enforcement

[0085] A centralized PersonaValidator component provides enforcement across all API endpoints:

[0086] (a) get_user_persona_from_jwt(): Extracts persona JSON from the JWT "profile" claim via the API gateway authorizer context. Returns structured object with user_id, email, persona_type, initiator_id, related_user_id.

[0087] (b) validate_legacy_maker_access() / validate_legacy_benefactor_access(): Validates that the requesting user's persona matches the required persona for the endpoint.

[0088] (c) create_access_denied_response(): Generates standardized 403 response with CORS headers and structured error body.

[0089] (d) add_persona_context_to_response(): Enriches API response bodies with persona context (persona_type, user_id, is_initiator) enabling client-side UI adaptation without additional API calls.

#### IV.4 — Token-Based Invitation and Cross-Registration Linking

[0090] FIG. 5 illustrates the invitation and cross-registration linking flow.

[0091] When a content creator designates a beneficiary who does not have an account:

[0092] Step 1 — Beneficiary Lookup: System queries Cognito for a user with the specified email. If not found, invitation flow initiates.

[0093] Step 2 — Assignment Creation with Rollback: The system creates records in sequence: (1) relationship record in PersonaRelationshipsDB, (2) access condition records in AccessConditionsDB, (3) invitation token in PersonaSignupTempDB (UUID, 30-day TTL, containing initiator_id, benefactor_email normalized to lowercase, invite_type "maker_assignment", and full assignment_details including access conditions), (4) invitation email via SES. If any step fails, all previously created records are deleted (compensating transaction). Only after all steps succeed does the system return success.

[0094] Step 3 — Registration with Token: Beneficiary clicks link (e.g., /signup/create-legacy?invite={token}). Client detects the invite parameter, passes it through signupWithPersona() as clientMetadata.

[0095] Step 4 — Cross-Registration Linking: During post-confirmation trigger, the system calls link_registration_to_assignment() which: (a) validates the token exists and is type "maker_assignment"; (b) verifies email match (case-insensitive); (c) creates relationship record (status "pending"); (d) creates access condition records using composite key; (e) deletes consumed token. A notification email is sent to the new user.

#### IV.5 — Duplicate Assignment Prevention

[0096] Before creating a new assignment, the system checks for existing assignments between the same content creator and beneficiary. For unregistered beneficiaries, the system uses a composite identifier ("pending#" + email) as the temporary beneficiary identifier, enabling duplicate detection before registration.

### Part V — Security Architecture

[0097] All data is encrypted at rest using a customer-managed KMS key with automatic key rotation. All data in transit uses TLS 1.2+. S3 presigned URLs expire after 15 minutes (uploads) or 1 hour (playback). CloudTrail logs all data access events. GuardDuty provides threat detection with SNS alerts for high-severity findings. CORS is locked to a specific origin across three layers: API Gateway globals, GatewayResponse resources (for error responses), and Lambda function response headers. All Lambda functions read the allowed origin from an environment variable.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0098] FIG. 1 is a block diagram illustrating the overall system architecture of the digital legacy preservation platform.

[0099] FIG. 2 is a flow diagram illustrating the conversation turn processing cycle including parallel depth scoring and adaptive termination.

[0100] FIG. 3 is a block diagram illustrating the three-type content model with prefix-based field routing in the question status database.

[0101] FIG. 4 is a flow diagram illustrating the dual-threshold inactivity detection mechanism with three coordinating scheduled processes.

[0102] FIG. 5 is a flow diagram illustrating the invitation and cross-registration linking process for unregistered beneficiaries.

[0103] FIG. 6 is a flow diagram illustrating the persona data pipeline through pre-registration and post-registration authentication triggers.

---

## DRAWINGS

### FIG. 1 — Overall System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     CLIENT APPLICATION (101)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │ Voice Chat   │ │ Video        │ │ Dashboard with           │  │
│  │ Interface    │ │ Recorder     │ │ Category Progress Bars   │  │
│  └──────┬───────┘ └──────┬───────┘ └──────────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │ Benefactor   │ │ Assignment   │ │ Dual Registration        │  │
│  │ Dashboard    │ │ Manager      │ │ Paths (Maker/Benefactor) │  │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘  │
└─────────┼────────────────┼──────────────────────┼────────────────┘
          │ WebSocket      │ REST API             │ Cognito Auth
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (102)                              │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │ WebSocket API        │  │ REST API + Cognito Authorizer    │  │
│  │ + Custom Authorizer  │  │                                  │  │
│  └──────────┬──────────┘  └──────────────┬───────────────────┘  │
└─────────────┼────────────────────────────┼──────────────────────┘
              │                            │
              ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────────────────┐
│ CONVERSATION ENGINE  │    │ PLATFORM FUNCTIONS (40+)              │
│ (wsDefault Lambda)   │    │                                       │
│ 512MB / 60s          │    │ Assignment: Create, Get, Update,      │
│                      │    │   Accept/Decline, ManualRelease       │
│ ┌──────────────────┐ │    │ Video: Upload, Process, Transcribe,   │
│ │ Parallel LLM     │ │    │   Summarize, GetMakerVideos           │
│ │ ┌──────┐┌──────┐ │ │    │ Questions: Progress, Levels, Status   │
│ │ │Sonnet││Haiku │ │ │    │ Streaks: Check, Get, MonthlyReset     │
│ │ │Resp. ││Score │ │ │    │ Relationships: Create, Get, Validate  │
│ │ └──────┘└──────┘ │ │    │ Persona: Validator (shared layer)     │
│ └──────────────────┘ │    └──────────────────────────────────────┘
│ ┌──────────────────┐ │
│ │ 3-Tier Transcribe│ │    ┌──────────────────────────────────────┐
│ │ Deepgram→Stream  │ │    │ SCHEDULED PROCESSORS (111)            │
│ │ →Batch           │ │    │ TimeDelayProcessor (hourly)           │
│ └──────────────────┘ │    │ CheckInSender (daily)                 │
│ ┌──────────────────┐ │    │ InactivityProcessor (daily)           │
│ │ Polly TTS        │ │    │ MonthlyStreakReset (monthly)           │
│ └──────────────────┘ │    └──────────────────────────────────────┘
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                     │
│                                                                   │
│  DynamoDB Tables (104):                                           │
│  ┌────────────────────┐ ┌──────────────────┐ ┌────────────────┐  │
│  │userQuestionStatusDB│ │PersonaRelation-  │ │EngagementDB    │  │
│  │(userId+questionId) │ │shipsDB           │ │(userId)        │  │
│  │audio*/video*/      │ │(initiator+related)│ │streak+freeze   │  │
│  │videoMemory* fields │ │+ RelatedUserIndex│ │                │  │
│  ├────────────────────┤ ├──────────────────┤ ├────────────────┤  │
│  │userQuestionLevel-  │ │AccessConditionsDB│ │ConversationSta-│  │
│  │ProgressDB          │ │(rel_key+cond_id) │ │teDB            │  │
│  │(userId+questionType)│ │+ ActivationDate │ │(connectionId)  │  │
│  │level+remaining[]   │ │  Index           │ │TTL: 2 hours    │  │
│  │                    │ │+ ConditionType   │ │                │  │
│  │                    │ │  Index           │ │                │  │
│  ├────────────────────┤ ├──────────────────┤ ├────────────────┤  │
│  │PersonaSignupTempDB │ │WebSocketConnect- │ │userStatusDB    │  │
│  │(userName)          │ │ionsDB            │ │(userId)        │  │
│  │TTL: 1hr/7d/30d    │ │(connectionId)    │ │timezone, prefs │  │
│  └────────────────────┘ └──────────────────┘ └────────────────┘  │
│                                                                   │
│  S3 Encrypted Storage (105):                                      │
│  conversations/{userId}/{questionId}/audio/turn-{N}.webm          │
│  conversations/{userId}/{questionId}/ai-audio/turn-{N}.mp3        │
│  conversations/{userId}/{questionId}/transcript.json              │
│  user-responses/{userId}/{filename}.webm                          │
│  user-responses/{userId}/{filename}.jpg (thumbnails)              │
└──────────────────────────────────────────────────────────────────┘
```

### FIG. 2 — Conversation Turn Processing

```
┌──────────────┐
│ User Speaks   │◄──────────────────────────────────────┐
│ Response      │                                        │
└──────┬───────┘                                        │
       ▼                                                │
┌──────────────────┐                                    │
│ Upload Audio     │                                    │
│ via Presigned URL│                                    │
└──────┬───────────┘                                    │
       ▼                                                │
┌──────────────────┐                                    │
│ 3-Tier Cascade   │                                    │
│ Transcription    │                                    │
│ Deepgram(0.5s)   │                                    │
│ →Stream(5s)      │                                    │
│ →Batch(15s)      │                                    │
└──────┬───────────┘                                    │
       ▼                                                │
┌──────────────────────────────┐                        │
│ PARALLEL (ThreadPoolExecutor)│                        │
│ ┌────────────┐ ┌───────────┐ │                        │
│ │ Sonnet     │ │ Haiku     │ │                        │
│ │ temp=0.7   │ │ temp=0.3  │ │                        │
│ │ Generate   │ │ Score     │ │                        │
│ │ follow-up  │ │ depth     │ │                        │
│ └─────┬──────┘ └─────┬─────┘ │                        │
└───────┼──────────────┼───────┘                        │
        │              ▼                                │
        │    ┌──────────────────┐                       │
        │    │ cumScore +=      │                       │
        │    │ turnScore        │                       │
        │    │ Persist state    │                       │
        │    └──────┬───────────┘                       │
        │           ▼                                   │
        │    ┌──────────────────┐              ┌────────┴──────┐
        │    │ cumScore >=      │     NO       │ Synthesize    │
        │    │ threshold? ──────┼─────────────►│ follow-up     │
        │    │ OR maxTurns?     │              │ via Polly     │
        │    └──────┬───────────┘              │ → S3 → URL   │
        │           │ YES                      └───────────────┘
        │           ▼
        │    ┌──────────────────┐
        │    │ COMPLETION:      │
        │    │ Save transcript  │
        │    │ Update progress  │
        │    │ Invalidate cache │
        │    │ Summarize (3 out)│
        │    │ Offer video mem  │
        │    └──────────────────┘
```

### FIG. 4 — Dual-Threshold Inactivity Detection

```
┌─────────────────────────────────────────────────────────────┐
│  PROCESS 1: CHECK-IN SENDER (Daily Cron)                     │
│  For each inactivity_trigger (status=pending):               │
│  IF days_since_last_sent >= check_in_interval_days:          │
│    1. Generate UUID token → store (7-day TTL)                │
│    2. Email creator: "Click to confirm active"               │
│    3. INCREMENT consecutive_missed_check_ins                 │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PROCESS 2: CHECK-IN RESPONSE (User clicks link)             │
│    1. Validate token                                         │
│    2. RESET consecutive_missed_check_ins = 0                 │
│    3. Update last_check_in = now()                           │
│    ──► PREVENTS FALSE POSITIVE ACTIVATION                    │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PROCESS 3: INACTIVITY PROCESSOR (Daily Cron)                │
│  For each inactivity_trigger (status=pending):               │
│                                                              │
│  THRESHOLD 1: months_since_last_check_in >= inactivity_months│
│                        AND                                   │
│  THRESHOLD 2: consecutive_missed >= max(1, expected / 2)     │
│                                                              │
│  IF BOTH MET → activate relationship, notify beneficiary     │
└─────────────────────────────────────────────────────────────┘
```

### FIG. 5 — Invitation and Cross-Registration Linking

```
CONTENT CREATOR                    UNREGISTERED BENEFICIARY
      │                                     │
      │ createAssignment(email, conditions)  │
      ▼                                     │
┌──────────────────┐                        │
│ 1. Create rel.   │                        │
│ 2. Create conds. │                        │
│ 3. Create token  │                        │
│    (30-day TTL)  │                        │
│ 4. Send email ───┼───────────────────────►│
│                  │                        │
│ ⚠ Any fail →    │                        │
│   rollback all   │                        │
└──────────────────┘                        │
                                            │ Clicks invite link
                                            ▼
                              ┌──────────────────────────┐
                              │ Pre-signup:               │
                              │  Store token, auto-confirm│
                              ├──────────────────────────┤
                              │ Post-confirmation:        │
                              │  1. Validate token        │
                              │  2. Verify email match    │
                              │  3. Create relationship   │
                              │  4. Create conditions     │
                              │  5. Delete token          │
                              │  6. Send welcome email    │
                              └──────────────────────────┘
```

---

## CLAIMS

### Claim Set A — Conversational Elicitation Engine

1. A computer-implemented system for eliciting personal narrative content through AI-guided conversation, the system comprising:

   a client application configured to capture audio input from a user and establish a persistent bidirectional communication channel with a conversation engine;

   a conversation engine comprising one or more serverless compute functions, the conversation engine configured to:
   - (a) receive a transcribed text representation of the user's spoken response for a current conversation turn;
   - (b) concurrently invoke, using parallel thread execution, a first large language model to generate a follow-up question based on a conversation history comprising all prior turns, and a second large language model to evaluate the narrative depth of the user's response and produce a numeric depth score;
   - (c) add the numeric depth score to a cumulative score maintained in a conversation state object;
   - (d) compare the cumulative score against a configurable score threshold;
   - (e) when the cumulative score is below the threshold, transmit the generated follow-up question to the client application and repeat from step (a) for a subsequent turn;
   - (f) when the cumulative score meets or exceeds the threshold, terminate the conversation and persist a transcript of all turns; and

   a state persistence layer comprising a database configured to store the conversation state object keyed by a connection identifier, with a time-to-live attribute for automatic expiration.

2. The system of claim 1, wherein the first large language model is a higher-capability model configured with a first temperature parameter for creative response generation, and the second large language model is a lower-capability model configured with a second, lower temperature parameter for consistent numeric scoring.

3. The system of claim 1, further comprising a cascading transcription subsystem configured to attempt transcription using a first speech-to-text service, upon failure attempt a second service that converts the audio format, and upon failure attempt a third batch-mode service.

4. The system of claim 1, wherein the conversation engine synthesizes the generated follow-up question into speech audio using a text-to-speech service, stores the audio in encrypted cloud storage, and transmits a time-limited access URL to the client.

5. The system of claim 1, wherein upon termination, the conversation engine invokes a summarization model to generate a one-sentence summary, a detailed summary, and a thoughtfulness score, stored with content-type-specific field prefixes, with idempotency checking and a per-question enable flag.

6. The system of claim 1, further comprising a structured question category system wherein questions are organized into life-topic categories at multiple difficulty levels, with a progress tracking subsystem that advances the user to a next level upon completing all questions at a current level, and wherein the client application presents per-category progress indicators.

7. The system of claim 1, wherein for each question, the system supports three content types linked to a single database record: an AI-guided audio conversation stored with a first field prefix, a direct video recording stored with a second field prefix, and a supplementary video memory linked via database update with a third field prefix.

8. The system of claim 1, further comprising an asynchronous video processing pipeline comprising thumbnail extraction using smart seek to a calculated video midpoint, event-driven transcription processing, and AI summarization, wherein each stage fails gracefully without affecting the upload success response.

9. The system of claim 1, further comprising an engagement subsystem tracking daily activity with a streak counter, a streak freeze mechanism consuming one freeze per missed day with monthly replenishment, milestone detection with metric emission, and timezone-aware date calculations.

### Claim Set B — Multi-Condition Access Control

10. A computer-implemented method for managing conditional access to digital content in a cloud computing environment, the method comprising:

    receiving, from a content creator, a designation of a beneficiary and one or more access conditions, each specifying criteria for granting the beneficiary access;

    storing each access condition in a database using a composite key comprising identifiers of the content creator and the beneficiary;

    for an access condition of an inactivity-trigger type:
    - (a) executing a first scheduled process to periodically generate a unique verification token, store the token with a time-to-live expiration, transmit a verification message to the content creator, and increment a missed-verification counter;
    - (b) upon receipt of a valid verification token, resetting the missed-verification counter and updating a last-verified timestamp;
    - (c) executing a second scheduled process to evaluate whether both a duration since the last-verified timestamp exceeds a configurable inactivity threshold and the missed-verification counter exceeds a minimum threshold derived from the inactivity threshold and the verification interval; and
    - (d) upon both conditions being satisfied, activating the access condition and notifying the beneficiary.

11. The method of claim 10, further comprising, for a time-delayed access condition, executing a scheduled process to query for conditions where an activation date has passed and activating matching conditions.

12. The method of claim 10, wherein the minimum missed-verification threshold is calculated as the integer division of the product of the inactivity threshold in months and thirty, divided by the verification interval in days, divided by two.

13. The method of claim 10, wherein the content creator specifies different access conditions for content viewing permission and avatar interaction permission for the same beneficiary.

14. The method of claim 10, further comprising returning, upon an access validation request, a per-permission-type access determination with a list of unmet conditions including type-specific details.

### Claim Set C — Dual-Persona Management and Invitation System

15. A computer-implemented system for managing a digital legacy platform with dual-persona user management, the system comprising:

    an authentication service managing user accounts, each associated with a persona type selected from a content creator persona and a content viewer persona;

    a pre-registration trigger function configured to receive a persona selection from client metadata, store the persona selection in a temporary data store with a time-to-live expiration, and for invited users, set auto-confirmation flags bypassing email verification;

    a post-registration trigger function configured to retrieve the persona selection from the temporary data store, write the persona type as a structured JSON object to a claim of the user's authentication token, delete the temporary record, and process any pending invitation linkages, with a retry mechanism and monitoring metric emission on failure; and

    a persona enforcement layer configured to extract the persona type from the authentication token on each API request and validate authorization for the requested operation.

16. The system of claim 15, further comprising a cross-registration invitation linking subsystem configured to:
    - generate a unique invitation token associating a content creator with an unregistered beneficiary's email and access conditions;
    - upon the beneficiary registering via a URL containing the token, validate the token, verify email match, create relationship and access condition records, and delete the consumed token.

17. The system of claim 16, further comprising transactional rollback logic wherein if any step in assignment creation fails, all previously created database records are deleted before returning a failure response.

18. The system of claim 15, wherein for unregistered beneficiaries, the system uses a composite identifier comprising a prefix string and the email address as a temporary beneficiary identifier, enabling duplicate assignment detection before registration.

19. The system of claim 15, wherein the persona enforcement layer enriches API response bodies with persona context data enabling client-side UI adaptation without additional API calls.

---

## ABSTRACT

An integrated digital legacy preservation platform comprising three interconnected subsystems. A conversational elicitation engine conducts real-time AI-guided voice conversations with parallel dual-model depth scoring and adaptive termination based on cumulative quality thresholds, with stateful conversation management in a serverless environment. A multi-condition access control system enables content creators to designate beneficiaries with configurable release conditions including dual-threshold inactivity detection combining elapsed time with missed check-in verification counts. A dual-persona user management system assigns content creator or content viewer personas at registration via a pre-registration to post-registration data pipeline, with token-based cross-registration linking for unregistered beneficiaries and transactional rollback for assignment creation integrity.
