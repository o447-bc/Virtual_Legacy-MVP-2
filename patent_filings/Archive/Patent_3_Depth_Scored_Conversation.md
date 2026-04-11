# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction," "Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution," "Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation," and "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to conversational AI systems, and more particularly to a computer-implemented system for conducting real-time voice conversations with automated narrative depth scoring, parallel multi-model language model processing, and adaptive conversation termination based on cumulative quality thresholds, implemented within a stateless serverless computing environment.

---

## BACKGROUND OF THE INVENTION

[0003] Conversational AI systems are widely used for customer service, information retrieval, and interactive experiences. However, existing systems are designed primarily for task completion (e.g., answering questions, resolving support tickets) rather than for eliciting deep, meaningful personal narratives from users.

[0004] When applied to personal narrative elicitation — such as recording life stories, conducting oral histories, or preserving personal memories — existing conversational AI systems suffer from several limitations.

[0005] First, existing systems have no mechanism for evaluating the quality or depth of a user's response. A user who provides a one-word answer receives the same treatment as a user who provides a rich, detailed narrative. There is no feedback loop that encourages deeper reflection or ensures that collected narratives meet a minimum quality standard.

[0006] Second, existing real-time conversational systems that use large language models (LLMs) for both response generation and response evaluation suffer from high latency when these operations are performed sequentially. In a voice conversation, latency of 4-8 seconds between a user's response and the AI's follow-up question disrupts natural conversational flow and degrades the user experience.

[0007] Third, serverless computing environments (such as AWS Lambda) are inherently stateless — each function invocation has no memory of previous invocations. Multi-turn conversations require state persistence across invocations, but existing approaches either use dedicated servers (increasing cost and operational complexity) or lose state between turns.

[0008] Fourth, speech-to-text transcription services vary in speed, accuracy, and reliability. Relying on a single transcription service creates a single point of failure that can disrupt real-time conversations.

[0009] There is therefore a need for a conversational AI system that provides real-time quality assessment of user responses, minimizes latency through parallel processing, maintains conversation state in a serverless environment, and provides resilient transcription through multi-service failover.

---

## SUMMARY OF THE INVENTION

[0010] The present invention provides a computer-implemented system for conducting real-time voice conversations with automated narrative depth scoring and adaptive termination. The system establishes a persistent bidirectional WebSocket connection between a client device and a serverless conversation engine. During each conversation turn, the user's spoken response is transcribed and simultaneously processed by two large language models operating in parallel: a first model generates a contextually-aware follow-up question, while a second model evaluates the narrative depth of the response and assigns a numeric score. Scores accumulate across turns, and the conversation automatically terminates when the cumulative score reaches a configurable threshold.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture

[0011] FIG. 1 illustrates the system architecture according to an embodiment of the present invention. The system comprises a client application (110), an API gateway with WebSocket support (120), a conversation engine implemented as serverless compute functions (130), a state persistence layer (140), a transcription subsystem (150), a text-to-speech subsystem (160), and encrypted cloud storage (170).

[0012] The client application (110) executes on a user's computing device and provides a voice conversation interface. The client application captures audio input via the device microphone using the MediaRecorder API or equivalent, establishes a WebSocket connection with the conversation engine, and plays back AI-generated audio responses.

[0013] The API gateway (120) provides a WebSocket endpoint with custom authorization. A custom authorizer function validates the user's authentication token (e.g., a Cognito access token passed as a query parameter) and extracts the user identifier. Upon successful authorization, the connection is established and the connection identifier is stored in a connections tracking database with a time-to-live (TTL) attribute for automatic cleanup.

[0014] The conversation engine (130) is the core component, implemented as a serverless compute function (e.g., AWS Lambda) that handles all WebSocket messages. The function is configured with sufficient memory (e.g., 512 MB) and timeout (e.g., 60 seconds) to accommodate LLM API calls and audio processing. The conversation engine routes incoming messages to appropriate handlers based on an action field in the message payload.

### 2. Conversation Lifecycle

[0015] FIG. 2 illustrates the conversation lifecycle according to an embodiment of the present invention.

[0016] Phase 1 — Connection and Initialization: The client application establishes a WebSocket connection. The custom authorizer validates the authentication token and extracts the user identifier. The connection identifier and user identifier are stored in the connections database.

[0017] Phase 2 — Conversation Start: The client sends a "start_conversation" message containing a question identifier and question text. The conversation engine creates a ConversationState object containing: connectionId, userId, questionId, questionText, turnNumber (initialized to 0), cumulativeScore (initialized to 0.0), turns (empty list), startedAt (current timestamp), completed (false), and completionReason (null). The state object is persisted to a NoSQL database (e.g., DynamoDB) keyed by connectionId, with a TTL of 2 hours. The question text is synthesized to speech and transmitted to the client as the opening prompt.

[0018] Phase 3 — Conversation Turns: For each user response, the following steps occur:

[0019] Step 3a — Audio Upload: The client requests a presigned upload URL from the conversation engine. The engine generates a presigned S3 PUT URL with a 15-minute expiration, scoped to the user's conversation path (e.g., conversations/{userId}/{questionId}/audio/turn-{N}-{timestamp}.webm). The client uploads the audio directly to S3 using the presigned URL, bypassing the compute layer.

[0020] Step 3b — Transcription: The conversation engine transcribes the uploaded audio using a cascading three-tier transcription subsystem:

[0021] Tier 1 — External API (e.g., Deepgram): The audio is sent to an external transcription API via a presigned S3 GET URL. This tier provides the lowest latency (approximately 0.5 seconds average) but may fail due to API rate limits or network issues. The API key is retrieved from a secure parameter store with in-memory caching.

[0022] Tier 2 — Streaming Transcription (e.g., AWS Transcribe Streaming): Upon failure of Tier 1, the audio file is downloaded from S3, converted from WebM to PCM WAV format using an audio processing binary (e.g., FFmpeg deployed as a Lambda layer), and streamed to a streaming transcription service. Audio is sent in 16KB chunks with minimal inter-chunk delay. This tier provides moderate latency (approximately 5 seconds) with higher reliability.

[0023] Tier 3 — Batch Transcription (e.g., AWS Transcribe batch): Upon failure of Tier 2, a batch transcription job is initiated. This tier provides the highest reliability but highest latency (approximately 15 seconds). The system polls for job completion.

[0024] Each tier is wrapped in exception handling, and timing instrumentation records the latency of each attempt for monitoring and optimization.

[0025] Step 3c — Parallel Depth Scoring and Response Generation: The transcribed text is simultaneously processed by two LLMs using a thread pool executor with 2 workers:

[0026] Worker 1 — Response Generation: A first LLM (e.g., Claude 3.5 Sonnet, configured with temperature 0.7) generates a contextually-aware follow-up question. The model receives the full conversation history (all prior turns) and a system prompt that instructs it to act as an empathetic interviewer who asks probing follow-up questions to elicit deeper reflection.

[0027] Worker 2 — Depth Scoring: A second LLM (e.g., Claude 3 Haiku, configured with temperature 0.3) evaluates the narrative depth of the user's response and produces a numeric score and reasoning. The scoring model evaluates factors including specificity of detail, emotional depth, personal reflection, unique perspective, and narrative completeness. The score is parsed from the model's response, with fallback handling for various response formats.

[0028] The parallel execution reduces per-turn latency by approximately 50% compared to sequential processing.

[0029] Step 3d — Score Accumulation and State Update: The depth score is added to the cumulative score in the conversation state object. The turn is recorded with the user's text, AI response, turn score, cumulative score, reasoning, and timestamp. The updated state is persisted to the database.

[0030] Step 3e — Continuation Decision: The system evaluates whether the conversation should continue by checking two conditions: (a) whether the cumulative score is below the configurable score threshold (e.g., 12 points), and (b) whether the turn count is below the configurable maximum (e.g., 20 turns). If both conditions are met, the AI's follow-up question is synthesized to speech and transmitted to the client, and the process repeats from Step 3a.

[0031] Phase 4 — Conversation Completion: When the cumulative score meets or exceeds the threshold (reason: "score_goal_reached") or the maximum turn count is reached (reason: "max_turns_reached"), the conversation terminates. The system: (a) saves the complete transcript to encrypted cloud storage as a JSON document; (b) updates the question status in the database with completion metadata including the final score, turn count, and transcript URL; (c) updates the user's progress record; (d) invalidates any cached completion counts; (e) triggers a summarization process that generates a one-sentence summary, detailed summary, and thoughtfulness score; and (f) transmits a completion message to the client containing the final score, total turns, transcript URL, and detailed summary.

[0032] Phase 5 — Cleanup: The conversation state is deleted from the database. If not explicitly deleted, the TTL attribute ensures automatic cleanup after 2 hours.

### 3. Conversation State Persistence

[0033] FIG. 3 illustrates the conversation state persistence mechanism according to an embodiment of the present invention.

[0034] The ConversationState class manages state for a single conversation session. The state is serialized to and deserialized from a NoSQL database (e.g., DynamoDB) on each Lambda invocation. Key implementation details include:

[0035] (a) Numeric Type Handling: The database stores numeric values as Decimal types, while the application uses float types. Custom conversion functions recursively convert between Decimal and float representations during serialization and deserialization, preventing type errors that would otherwise crash the conversation engine.

[0036] (b) TTL-Based Cleanup: Each state record includes a TTL attribute set to the current time plus 2 hours. The database automatically deletes expired records, preventing orphaned state from accumulating due to disconnected clients or crashed functions.

[0037] (c) Atomic State Updates: The complete state object is written on each turn using a put_item operation, ensuring consistency. The state includes the full conversation history, enabling any Lambda instance to resume the conversation regardless of which instance handled previous turns.

### 4. Configuration Management

[0038] Conversation parameters are stored in a secure parameter service (e.g., AWS SSM Parameter Store) and batch-fetched on the first invocation of each Lambda container. Parameters include: score_goal, max_turns, llm_conversation_model (model identifier for response generation), llm_scoring_model (model identifier for depth scoring), system_prompt, scoring_prompt, polly_voice_id, and polly_engine. A module-level cache dictionary persists across invocations within the same Lambda container, providing sub-millisecond parameter access on warm invocations. Default values are applied for any parameters not found in the parameter service.

[0039] This architecture enables zero-downtime configuration changes — operators can modify the score threshold, swap LLM models, or tune prompts without redeploying the conversation engine.

### 5. Structured Question Category System with Level Progression

[0040] The system maintains a question database storing questions organized into life-topic categories (e.g., childhood, career, relationships, values). Within each category, questions are organized at multiple difficulty levels. A progress tracking subsystem maintains, for each user and each category, the current level, the count of completed questions, and an ordered list of remaining unanswered questions at the current level (stored as parallel arrays of question identifiers and question texts).

[0041] When a user completes a conversation for a question, the system removes that question from the remaining questions list and increments the completed count. When all questions at the current level within a category are completed, the system advances the user to the next level and populates the remaining questions list with questions from the next level. The client application presents per-category progress bars derived from this data, guiding the user's selection of which conversation to initiate next.

### 6. Multi-Modal Content Linking and Video Memory

[0042] The system supports three distinct content types per question, all linked to a single database record: (a) an AI-guided audio conversation with depth scoring (stored with field prefix "audio"), (b) a direct video recording (stored with field prefix "video"), and (c) a supplementary video memory recorded after conversation completion (stored with field prefix "videoMemory"). The video memory is linked to the existing conversation record via a database update operation (not a new record creation), ensuring that all content for a given question is accessible through a single query.

### 7. Asynchronous Video Processing Pipeline

[0043] Upon video upload, the system triggers an asynchronous processing pipeline: (a) a processing function verifies the uploaded video exists in cloud storage, extracts a thumbnail image by detecting the video duration and seeking to the calculated midpoint using a media processing binary (e.g., FFmpeg), and initiates a transcription job; (b) an event rule (e.g., EventBridge) triggers a transcript processing function upon transcription completion; (c) a summarization function generates three structured outputs (one-sentence summary, detailed summary, thoughtfulness score) from the transcript. Each stage operates independently and fails gracefully — the upload success response is returned to the client regardless of whether thumbnail generation, transcription, or summarization succeeds.

[0044] The summarization function includes an idempotency check (skipping if already summarized), a per-question enable/disable flag, transcript length limits, and content-type-specific field prefix routing for storing results.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0040] FIG. 1 is a block diagram illustrating the system architecture of the depth-scored conversational elicitation system.

[0041] FIG. 2 is a flow diagram illustrating the complete conversation lifecycle from connection through completion.

[0042] FIG. 3 is a block diagram illustrating the conversation state persistence mechanism with TTL-based cleanup.

---

## DRAWINGS

### FIG. 1 — System Architecture

```
┌──────────────────────────────────────────────────────┐
│                CLIENT APPLICATION (110)                │
│  ┌────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Microphone │  │ Audio    │  │ Conversation     │  │
│  │ Capture    │  │ Playback │  │ UI (Score, Text) │  │
│  └─────┬──────┘  └────▲─────┘  └──────────────────┘  │
└────────┼──────────────┼──────────────────────────────┘
         │ WebSocket    │ WebSocket
         ▼              │
┌────────────────────────────────────────────────────────┐
│           API GATEWAY — WebSocket (120)                  │
│  ┌──────────────┐                                       │
│  │ Custom       │  Validates JWT, extracts userId        │
│  │ Authorizer   │                                       │
│  └──────────────┘                                       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│           CONVERSATION ENGINE (130)                      │
│           Lambda Function — 512MB / 60s                  │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Action Router                                    │    │
│  │ start_conversation | user_response |             │    │
│  │ audio_response | get_upload_url | end_conversation│    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │ Response LLM │  │ Scoring LLM  │  ◄── Parallel       │
│  │ (Sonnet)     │  │ (Haiku)      │      Execution      │
│  │ temp=0.7     │  │ temp=0.3     │                     │
│  └──────────────┘  └──────────────┘                     │
└───────────┬──────────────────────────┬─────────────────┘
            │                          │
            ▼                          ▼
┌───────────────────┐    ┌──────────────────────────────┐
│ STATE PERSISTENCE │    │ TRANSCRIPTION SUBSYSTEM (150) │
│ LAYER (140)       │    │                               │
│                   │    │ Tier 1: Deepgram (~0.5s)      │
│ DynamoDB Table    │    │    ▼ (on failure)             │
│ PK: connectionId  │    │ Tier 2: AWS Streaming (~5s)   │
│ TTL: 2 hours      │    │    ▼ (on failure)             │
│                   │    │ Tier 3: AWS Batch (~15s)       │
│ ConversationState:│    └──────────────────────────────┘
│ - turnNumber      │
│ - cumulativeScore │    ┌──────────────────────────────┐
│ - turns[]         │    │ TEXT-TO-SPEECH (160)          │
│ - completed       │    │ Amazon Polly (Neural)         │
│ - completionReason│    │ → S3 (KMS) → Presigned URL   │
└───────────────────┘    └──────────────────────────────┘
```

---

## CLAIMS

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

3. The system of claim 1, wherein the conversation engine is further configured to, upon termination of the conversation, invoke a summarization model to generate a one-sentence summary, a detailed summary, and a thoughtfulness score from the complete transcript, and store the summaries in association with the conversation record.

4. The system of claim 1, further comprising a cascading transcription subsystem configured to:
   - attempt transcription of the user's audio input using a first speech-to-text service;
   - upon failure of the first service, attempt transcription using a second speech-to-text service that converts the audio from a first format to a second format compatible with the second service; and
   - upon failure of the second service, attempt transcription using a third speech-to-text service operating in batch mode.

5. The system of claim 1, wherein the conversation engine is further configured to synthesize the generated follow-up question into speech audio using a text-to-speech service, store the speech audio in encrypted cloud storage, generate a time-limited access URL, and transmit the URL to the client application for playback.

6. The system of claim 1, wherein the conversation engine is further configured to terminate the conversation when a turn count reaches a configurable maximum turn limit, regardless of the cumulative score, and wherein the score threshold and maximum turn limit are stored in a parameter service and cached in memory across serverless compute invocations.

7. The system of claim 1, wherein the conversation state object further comprises a list of turn records, each turn record containing the user's transcribed text, the AI-generated response, the turn depth score, the cumulative score at that turn, scoring reasoning, and a timestamp, enabling reconstruction of the complete conversation from the state object.

8. The system of claim 1, further comprising a structured question category system wherein:
   - a question database stores a plurality of questions organized into life-topic categories, each category containing questions at a plurality of difficulty levels;
   - a progress tracking subsystem maintains, for each user and each category, a current level, a count of completed questions, and an ordered list of remaining unanswered questions at the current level; and
   - upon completion of all questions at a current level within a category, the progress tracking subsystem advances the user to a next level and populates the remaining questions list with questions from the next level,
   - wherein the client application presents per-category progress indicators derived from the progress tracking subsystem to guide the user's selection of which conversation to initiate.

9. The system of claim 1, wherein upon termination of the conversation, the system offers the user an option to record a supplementary video memory, and wherein the supplementary video memory is linked to the existing conversation record in the database via a database update operation that adds video-specific fields using a type-specific field prefix to the existing record, rather than creating a new record, such that a single database record for a given question contains both audio conversation data stored with a first field prefix and video memory data stored with a second, distinct field prefix.

10. The system of claim 3, wherein the summarization model produces three distinct outputs for each completed conversation: a one-sentence summary, a detailed narrative summary, and a numeric thoughtfulness score on a predefined scale, and wherein:
    - the three outputs are stored in the database using content-type-specific field prefixes that vary based on whether the source content is an audio conversation, a regular video recording, or a supplementary video memory;
    - an idempotency check prevents duplicate summarization of the same conversation; and
    - a per-question enable flag allows summarization to be selectively disabled for individual question records.

11. The system of claim 1, further comprising an asynchronous video processing pipeline triggered upon upload of a video recording to cloud storage, the pipeline comprising:
    - a processing function that verifies the uploaded video exists, extracts a thumbnail image by seeking to a calculated midpoint of the video duration using a media processing binary, and initiates a transcription job;
    - an event rule that triggers a transcript processing function upon completion of the transcription job; and
    - a summarization function invoked by the transcript processing function to generate structured summaries from the transcript,
    - wherein each stage of the pipeline operates independently and fails gracefully without affecting the success response returned to the client for the original upload.

---

## ABSTRACT

A computer-implemented system for eliciting personal narrative content through AI-guided voice conversations with real-time quality assurance. The system uses a persistent WebSocket connection between a client and a serverless conversation engine. During each turn, the user's spoken response is transcribed and simultaneously processed by two large language models in parallel: one generates a follow-up question while the other scores narrative depth. Scores accumulate across turns, and the conversation terminates when a configurable quality threshold is reached. Conversation state is persisted in a database with TTL-based cleanup, enabling stateful interactions in a stateless serverless environment.
