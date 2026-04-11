# PROVISIONAL PATENT APPLICATION

## UNITED STATES PATENT AND TRADEMARK OFFICE

---

## TITLE OF THE INVENTION

Multimodal Data Collection System with Quality-Controlled Narrative Elicitation and Psychological Profiling for AI Avatar Construction

---

## INVENTOR(S)

Name: Oliver Richard Astley
Residence: Chicago, Illinois, USA

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

[0001] This application is related to co-pending provisional applications titled "Advisory Response Generation System Using Personal Knowledge Graph and Psychological Profile with Attribution," "Real-Time Depth-Scored Conversational Elicitation System with Parallel LLM Processing and Adaptive Termination," "Conditional Digital Legacy Access Control with Dual-Threshold Inactivity Detection and AI Avatar Activation," and "Timed Psychological Assessment System Producing Continuous Personality Vectors for AI Avatar Decision Simulation," all filed concurrently herewith and incorporated by reference in their entirety.

---

## FIELD OF THE INVENTION

[0002] The present invention relates generally to systems and methods for structured multimodal personal data collection, and more particularly to a computer-implemented system that combines quality-controlled narrative elicitation with rapid-fire psychological profiling to collect data structured for constructing AI-powered digital avatars capable of simulating a person's personality, voice, visual likeness, and decision-making behavior.

---

## BACKGROUND OF THE INVENTION

[0003] The creation of AI-powered digital avatars that can convincingly represent a specific individual requires extensive, high-quality data across multiple modalities. An effective avatar must be able to simulate the individual's personality and knowledge (what they know and have experienced), their decision-making patterns (how they think and make choices), their voice (how they sound), and their visual appearance (how they look and move).

[0004] Existing approaches to collecting data for AI avatar construction suffer from several significant limitations. First, dedicated data collection sessions — such as voice cloning studio recordings, 3D face scanning, or structured interview sessions — require the subject to participate in activities whose sole purpose is data collection. This results in lower engagement, less authentic data, and a poor user experience. Subjects who know they are "training an AI" tend to perform rather than behave naturally.

[0005] Second, passive data collection from existing digital footprints — such as social media posts, emails, or messaging history — produces unstructured data of highly variable quality. Social media posts are often performative rather than authentic, and the data lacks the structured coverage across life domains needed for comprehensive personality modeling.

[0006] Third, existing personal narrative recording platforms (such as guided journaling apps or video testimony services) collect stories but provide no quality assurance mechanism. A user may provide superficial, one-sentence answers to profound life questions, resulting in data that is insufficient for avatar personality modeling. There is no existing system that ensures collected narrative data meets a minimum depth or richness threshold.

[0007] Fourth, no existing system combines narrative life data with psychological profiling data in a unified pipeline designed for avatar construction. Traditional psychological assessments (such as the Myers-Briggs Type Indicator or Big Five personality inventories) produce categorical labels (e.g., "INTJ" or "high openness") that are too coarse for individual-level decision-making simulation. These assessments were designed for population-level categorization, not for training AI models to simulate a specific individual's reasoning patterns.

[0008] Fifth, existing systems do not capture the instinctive, automatic decision-making patterns that most accurately predict real-world behavior. Deliberated self-reports (where subjects have unlimited time to consider their answers) tend to reflect how people want to be perceived rather than how they actually behave. There is a need for assessment methodologies that capture instinctive responses.

[0009] There is therefore a need for a system that collects high-quality, structured, multimodal personal data sufficient for AI avatar construction, where the data collection occurs as a natural byproduct of a meaningful user activity, where data quality is automatically enforced through quantitative scoring mechanisms, and where the collected data includes both experiential knowledge and cognitive decision-making patterns organized in a structure optimized for avatar model training.

---

## SUMMARY OF THE INVENTION

[0010] The present invention provides a computer-implemented system and method for collecting structured, quality-controlled multimodal data sufficient to construct an AI-powered digital avatar capable of simulating a person's personality, voice, visual likeness, and decision-making behavior.

[0011] In one aspect, the system operates in two data collection phases. In a first phase, the system conducts AI-moderated voice conversations with a user across structured life-topic categories. During each conversation, a scoring model evaluates the narrative depth of each user response and produces a numeric depth score. Depth scores accumulate across conversation turns, and the conversation continues until the cumulative score meets or exceeds a configurable quality threshold. This ensures that collected personality and knowledge data meets a minimum richness standard suitable for avatar personality modeling. Audio recordings of the user's voice are captured at each conversation turn, and video recordings of the user are optionally captured, accumulating voice samples and visual likeness data across multiple sessions.

[0012] In a second phase, the system administers a rapid-fire psychological assessment comprising forced-choice and quick-response questions presented in timed succession. The timed format is designed to capture instinctive decision-making patterns rather than deliberated self-reports. Questions span multiple psychological dimension categories including values conflicts, risk calibration, moral reasoning, emotional tendencies, and decision styles. For each question, the system captures both the user's selected response and the response latency. A trait extraction engine processes the responses and latencies to produce multi-dimensional continuous personality vectors, and a decision pattern modeler identifies characteristic reasoning patterns.

[0013] All collected data is stored in an encrypted hierarchical structure with cross-modal metadata linking, forming a unified personal data graph comprising three layers: an experience layer (conversation transcripts and AI-generated narrative summaries), a cognition layer (personality vectors and structured decision-making profiles), and a presence layer (voice audio samples and video recordings). This three-layer architecture enables holistic avatar construction where the avatar can draw on the individual's documented experiences, measured cognitive patterns, and captured physical presence.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. System Architecture Overview

[0014] Referring now to the drawings, FIG. 1 illustrates the overall system architecture of the multimodal data collection pipeline according to an embodiment of the present invention. The system comprises a client application (110), a conversation engine (120), a psychological assessment engine (130), a summarization engine (140), a trait extraction engine (150), a decision pattern modeler (160), and a unified data store (170).

[0015] The client application (110) is a web-based or native application executing on a user's computing device (e.g., smartphone, tablet, or personal computer). The client application provides user interfaces for conducting voice conversations, recording video, and completing psychological assessments. The client application communicates with backend services via secure network connections including REST API endpoints and persistent bidirectional WebSocket connections.

[0016] The conversation engine (120) is implemented as one or more serverless compute functions (e.g., AWS Lambda functions) that manage multi-turn voice conversations between the user and an AI interviewer. The conversation engine receives transcribed user speech, invokes large language models for response generation and depth scoring, manages conversation state, and determines when conversations should terminate based on cumulative quality scores.

[0017] The psychological assessment engine (130) administers rapid-fire assessments to the user, presenting timed questions, capturing responses and latencies, and forwarding the collected data to the trait extraction engine.

[0018] The summarization engine (140) processes completed conversation transcripts to generate structured knowledge representations including one-sentence summaries, detailed narrative summaries, and thoughtfulness scores.

[0019] The trait extraction engine (150) processes rapid-fire assessment responses and response latencies to produce multi-dimensional continuous personality vectors.

[0020] The decision pattern modeler (160) analyzes personality vectors to identify domain-specific reasoning patterns and produces structured decision-making profiles.

[0021] The unified data store (170) maintains the personal data graph for each user, organized into three layers with cross-layer metadata linking.

### 2. Phase 1: Quality-Controlled Narrative Collection

[0022] FIG. 2 illustrates the data flow for Phase 1 narrative collection according to an embodiment of the present invention.

[0023] The system maintains a question database (210) storing a plurality of questions organized into life-topic categories. In a preferred embodiment, the categories include but are not limited to: childhood and early life, family relationships, romantic relationships, career and professional life, values and beliefs, life lessons and wisdom, hobbies and passions, challenges and adversity, achievements and milestones, and legacy and future hopes. Each category contains multiple questions at varying depth levels, enabling progressive exploration of each life domain.

[0024] A progress tracking subsystem (220) tracks, for each user, which questions have been answered across all categories, the depth scores achieved, and the remaining unanswered questions. The progress tracking subsystem presents the user with visual progress indicators (e.g., progress bars per category) that motivate completion of questions across all categories, thereby ensuring broad personality coverage in the collected data.

[0025] When a user selects a question to answer, the client application establishes a persistent bidirectional communication channel (e.g., a WebSocket connection) with the conversation engine. The conversation proceeds as follows:

[0026] Step 1 — Conversation Initialization: The conversation engine creates a conversation state object (230) that tracks the connection identifier, user identifier, question identifier, question text, turn number, cumulative score, conversation history (all prior turns), and completion status. The state object is persisted in a database (e.g., DynamoDB) keyed by the connection identifier, with a time-to-live (TTL) attribute for automatic expiration (e.g., 2 hours). This enables stateful multi-turn conversations within a stateless serverless compute environment.

[0027] Step 2 — AI Greeting: The conversation engine presents the question text to the user, optionally synthesized into speech audio using a text-to-speech service (e.g., Amazon Polly). The synthesized audio is stored in encrypted cloud storage (e.g., S3 with KMS encryption) and a time-limited presigned URL is transmitted to the client for playback.

[0028] Step 3 — User Response Capture: The user speaks their response. The client application captures the audio using the device's microphone via the MediaRecorder API or equivalent. The audio is uploaded to encrypted cloud storage via a presigned URL, bypassing the compute layer for efficiency.

[0029] Step 4 — Audio Transcription: The user's audio is transcribed to text. In a preferred embodiment, a cascading transcription subsystem attempts transcription using multiple services in order of decreasing speed and increasing reliability: a first service (e.g., Deepgram API, approximately 0.5 seconds average latency), a second service (e.g., AWS Transcribe Streaming with audio format conversion, approximately 5 seconds), and a third service (e.g., AWS Transcribe batch processing, approximately 15 seconds). Each service is attempted in sequence, with automatic failover to the next service upon failure.

[0030] Step 5 — Parallel Depth Scoring and Response Generation: The transcribed user response is simultaneously processed by two large language models using parallel thread execution (e.g., ThreadPoolExecutor with 2 workers):

[0031] (a) A first large language model (e.g., Claude 3.5 Sonnet or equivalent high-capability model) generates a contextually-aware follow-up question based on the full conversation history. This model is configured with a higher temperature parameter (e.g., 0.7) to produce varied, empathetic, and contextually appropriate follow-up questions that encourage deeper reflection.

[0032] (b) A second large language model (e.g., Claude 3 Haiku or equivalent lightweight model) evaluates the narrative depth of the user's response and produces a numeric depth score. This model is configured with a lower temperature parameter (e.g., 0.3) to produce consistent, reproducible scores. The scoring model evaluates factors including specificity of detail, emotional depth, personal reflection, unique perspective, and narrative completeness.

[0033] The parallel execution reduces per-turn latency by approximately 50% compared to sequential processing, enabling natural conversational flow in real-time voice interactions.

[0034] Step 6 — Score Accumulation and Continuation Decision: The depth score from Step 5(b) is added to the cumulative score maintained in the conversation state object. The system then evaluates whether the conversation should continue by comparing the cumulative score against a configurable score threshold (e.g., 12 points). If the cumulative score is below the threshold and the turn count is below a configurable maximum (e.g., 20 turns), the follow-up question from Step 5(a) is transmitted to the client application (optionally synthesized to speech), and the process repeats from Step 3.

[0035] Step 7 — Conversation Termination and Data Persistence: When the cumulative score meets or exceeds the threshold (indicating sufficient narrative depth has been achieved) or the maximum turn count is reached, the conversation terminates. The complete conversation transcript (including all turns, scores, and reasoning) is persisted to encrypted cloud storage. The question status is updated in the database to reflect completion, and the user's progress record is updated.

[0036] Step 8 — Summarization: Upon conversation completion, the summarization engine processes the full transcript and generates: (a) a one-sentence summary capturing the essence of the narrative, (b) a detailed summary providing a comprehensive account, and (c) a thoughtfulness score (e.g., 0-5 scale) evaluating the overall quality of the narrative. These summaries are stored in association with the conversation record and serve as pre-processed inputs for the experience layer of the personal data graph.

[0037] Step 9 — Optional Video Memory Recording: After conversation completion, the user is optionally offered the opportunity to record a supplementary video memory. The video captures the user's face, expressions, and mannerisms while they reflect on the topic just discussed. The video is uploaded to encrypted cloud storage, a thumbnail is extracted (e.g., using FFmpeg), and the video record is linked to the existing conversation record in the database using type-specific field prefixes (e.g., "videoMemory*" fields) to maintain a unified multi-modal record per question.

[0038] Throughout Phase 1, the system accumulates: (a) conversation transcripts with per-turn depth scores across all life-topic categories, (b) AI-generated summaries and thoughtfulness scores, (c) voice audio samples from each conversation turn (stored at paths such as conversations/{userId}/{questionId}/audio/turn-{N}-{timestamp}.webm), and (d) video recordings with extracted thumbnails. This data forms the experience layer and presence layer of the personal data graph.

### 3. Phase 2: Rapid-Fire Psychological Profiling

[0039] FIG. 3 illustrates the data flow for Phase 2 psychological profiling according to an embodiment of the present invention.

[0040] The psychological assessment engine maintains a question bank (310) storing assessment questions organized into psychological dimension categories. In a preferred embodiment, the categories include:

[0041] (a) Values-Conflict Questions: Scenarios presenting the user with a choice between competing values (e.g., loyalty vs. honesty, individual freedom vs. collective responsibility, tradition vs. innovation). Example: "Your best friend asks you to lie for them to protect them from consequences. Do you lie or tell the truth?"

[0042] (b) Risk-Calibration Questions: Scenarios with varying risk-reward tradeoffs across different life domains (e.g., financial risk, career risk, relationship risk, health risk). Example: "You have a stable job with good benefits. A startup offers you equity but lower salary. What do you do?"

[0043] (c) Moral-Reasoning Questions: Ethical dilemmas calibrated to real-world scenarios that reveal the user's moral reasoning framework (utilitarian vs. deontological vs. virtue-based). Example: Trolley-problem variants adapted to everyday contexts.

[0044] (d) Emotional-Tendency Questions: Stimuli designed to reveal the user's characteristic emotional responses (e.g., response to criticism, response to unexpected change, response to conflict). Example: "When someone criticizes your work in front of others, your first instinct is to: (a) defend yourself immediately, (b) listen and reflect, (c) feel hurt but say nothing, (d) ask for specific examples."

[0045] (e) Decision-Style Questions: Questions revealing whether the user tends toward intuitive or analytical decision-making, and their characteristic information-gathering patterns. Example: "When making a major life decision, do you: (a) go with your gut feeling, (b) make a pros-and-cons list, (c) ask trusted people for advice, (d) research extensively before deciding?"

[0046] The assessment interface (320) presents questions to the user in rapid succession, enforcing a maximum response time per question (e.g., 10 seconds for forced-choice questions, 20 seconds for short-response questions). The timed format is a critical design choice: by limiting deliberation time, the system captures instinctive responses that more accurately reflect the user's automatic cognitive patterns — the patterns that drive real-world decision-making — rather than carefully constructed self-presentations.

[0047] For each question, the assessment interface captures: (a) the user's selected response or short text response, (b) the response latency (time elapsed between question presentation and response submission, measured in milliseconds), and (c) whether the question timed out (no response within the maximum time).

[0048] Questions that time out are recorded as timeouts and excluded from the personality vector calculation. The timeout rate itself is recorded as a metadata attribute of the psychological profile, as it may indicate decision avoidance tendencies or difficulty with certain question types.

[0049] In a preferred embodiment, the assessment engine selects questions adaptively based on the user's previously completed narrative conversations. For example, if the user has completed narrative conversations in the "career and professional life" category, the assessment engine may include additional risk-calibration and decision-style questions specific to career contexts, enabling targeted profiling in domains where narrative experience data exists.

[0050] The trait extraction engine (330) processes the collected responses and latencies as follows:

[0051] (a) Response Mapping: Each selected response is mapped to one or more positions along continuous psychological dimensions. Unlike categorical personality assessments that assign discrete labels, this system produces continuous values (e.g., a risk tolerance score of 0.73 on a 0-1 scale rather than a binary "risk-averse" or "risk-seeking" label).

[0052] (b) Latency Weighting: Each mapped position is weighted by a function of the response latency. In a preferred embodiment, responses with shorter latencies receive higher weights, on the basis that faster responses more accurately reflect instinctive cognitive patterns. The weighting function may be, for example, an inverse logarithmic function of the latency: weight = 1 / (1 + log(latency_ms / baseline_ms)), where baseline_ms is a calibration value determined during the first few questions of the assessment.

[0053] (c) Aggregation: The weighted positions across all questions are aggregated to produce a multi-dimensional personality vector. Each dimension of the vector represents the user's position along a continuous psychological scale (e.g., risk tolerance, empathy orientation, analytical vs. intuitive tendency, loyalty vs. independence, tradition vs. innovation).

[0054] The decision pattern modeler (340) analyzes the personality vector to identify domain-specific reasoning patterns. Rather than producing a single global personality description, the modeler identifies how the user's tendencies vary across decision domains. For example, a user might be risk-averse in financial decisions but risk-seeking in relationship decisions, or might prioritize loyalty in family contexts but prioritize honesty in professional contexts. The output is a structured decision-making profile that encodes these domain-specific tendencies.

[0055] The psychological profile (personality vector + decision-making profile) is stored in the cognition layer of the personal data graph, with metadata linking to the experience layer entries from the same life-topic domains.

### 4. The Three-Layer Personal Data Graph

[0056] FIG. 4 illustrates the three-layer personal data graph architecture according to an embodiment of the present invention.

[0057] The unified data store maintains, for each user, a personal data graph comprising three layers:

[0058] (a) Experience Layer (410): Contains conversation transcripts (with per-turn text, depth scores, and reasoning), AI-generated one-sentence summaries, detailed narrative summaries, and thoughtfulness scores. Data is organized by life-topic category and question, enabling retrieval of all experiential data related to a specific life domain. In a preferred embodiment, the experience layer is stored across a combination of a NoSQL database (e.g., DynamoDB) for metadata and structured fields, and object storage (e.g., S3) for full transcripts and audio files.

[0059] (b) Cognition Layer (420): Contains the multi-dimensional personality vector, the structured decision-making profile with domain-specific tendencies, raw assessment responses with latencies, and assessment metadata (timeout rate, completion rate, calibration baseline). The cognition layer is stored in the NoSQL database with the personality vector serialized as a JSON object.

[0060] (c) Presence Layer (430): Contains voice audio samples from conversation turns (accumulated across multiple conversations, providing diverse samples across emotional contexts and topics), video recordings with extracted thumbnails, and metadata about recording conditions (device type, audio quality metrics). The presence layer data is stored in encrypted object storage with metadata references in the NoSQL database.

[0061] Cross-layer metadata linking (440) enables retrieval of related data across layers. For example, given a question about career decisions, the system can retrieve: the narrative conversation transcript and summary (experience layer), the career-domain risk tolerance and decision style scores (cognition layer), and the voice audio samples from that conversation (presence layer). This cross-layer linking is implemented through shared key structures (e.g., userId + questionId + questionType) that span all three layers.

### 5. Avatar Construction from the Personal Data Graph

[0062] FIG. 5 illustrates the avatar construction process according to an embodiment of the present invention.

[0063] An avatar construction engine (510) processes the three-layer personal data graph to produce a unified avatar model comprising:

[0064] (a) Personality Simulation Model (520): Constructed from the experience layer and cognition layer. The personality simulation model encodes the individual's knowledge, opinions, communication style, and decision-making patterns. In a preferred embodiment, the personality simulation model is implemented as a retrieval-augmented generation (RAG) system where the experience layer serves as the retrieval corpus and the cognition layer provides personality calibration parameters that influence response generation. When presented with a novel query, the model retrieves relevant experience entries and applies the decision-making profile to generate responses that reflect how the specific individual would likely respond.

[0065] (b) Voice Synthesis Model (530): Constructed from the voice audio samples in the presence layer. The accumulated audio samples across multiple conversations provide diverse training data spanning different emotional contexts, speech rates, and topics. In a preferred embodiment, the voice synthesis model is trained using voice cloning techniques that can generate novel speech in the individual's voice from text input.

[0066] (c) Visual Likeness Model (540): Constructed from the video recordings in the presence layer. The video data captures the individual's facial appearance, expressions, and mannerisms. In a preferred embodiment, the visual likeness model can generate video of the individual's face synchronized with synthesized speech.

[0067] The personality simulation model is configured to weight personality attributes extracted from conversations with higher depth scores more heavily than attributes from conversations with lower depth scores when constructing the personality model. This ensures that the avatar's personality is primarily informed by the user's most thoughtful and detailed responses.

### 6. Engagement and Data Completeness Mechanisms

[0068] The system includes an engagement subsystem (610) that tracks a daily activity streak for the user across both narrative conversations and psychological assessment sessions. The streak subsystem implements the following business rules: same-day activity does not change the streak count; consecutive-day activity increments the streak by one; a missed day with a streak freeze available maintains the streak and consumes the freeze; a missed day without a freeze resets the streak to one. Streak freezes are replenished monthly. Milestones (e.g., 7-day, 30-day, 100-day streaks) are tracked and celebrated.

[0069] This gamification mechanism increases the volume and temporal distribution of collected data, which improves avatar quality by providing more diverse samples across different moods, times of day, and life circumstances.

### 7. Security and Encryption

[0070] All data in the personal data graph is encrypted at rest using customer-managed encryption keys (e.g., AWS KMS). All data in transit is protected by TLS 1.2 or higher. Access to the data is controlled by authentication (e.g., Cognito user pools with JWT tokens) and authorization (role-based access control distinguishing content creators from beneficiaries). Presigned URLs for media access expire after configurable time periods (e.g., 15 minutes for uploads, 1 hour for playback). Audit logging (e.g., CloudTrail) tracks all data access events.

### 8. Three-Type Content Model with Unified Question Records

[0071] For each question in the question database, the unified data store supports three distinct content types linked to a single question record identified by the composite key of user identifier and question identifier:

[0072] (a) AI-Guided Audio Conversation: The primary content type, produced by the depth-scored conversation engine. Stored with field prefixes "audio" (e.g., audioTranscriptUrl, audioConversationScore, audioTurnCount, audioOneSentence, audioDetailedSummary, audioThoughtfulnessScore, audioSummarizationStatus).

[0073] (b) Direct Video Recording: A video recorded by the user in response to a question prompt. Stored with field prefixes "video" (e.g., videoS3Location, videoTranscriptionStatus, videoTranscript, videoOneSentence, videoDetailedSummary, videoThoughtfulnessScore).

[0074] (c) Supplementary Video Memory: A video recorded after completion of an audio conversation, capturing the user's visual reflection on the topic just discussed. This content type is linked to the existing question record via a database update operation (not a new record creation), using field prefixes "videoMemory" (e.g., videoMemoryS3Location, videoMemoryRecorded, videoMemoryTimestamp, videoMemoryThumbnailS3Location). The update operation checks that an existing conversation record exists before adding video memory fields, ensuring data integrity.

[0075] This three-type model ensures that all content modalities for a given question are retrievable through a single database query, and that the video memory is always associated with its originating conversation.

### 9. Asynchronous Video Processing Pipeline

[0076] Upon video upload to encrypted cloud storage via a presigned URL, the system triggers an asynchronous processing pipeline:

[0077] Stage 1 — Processing: A processing function verifies the uploaded video exists in cloud storage (via a HEAD request), extracts a representative thumbnail image using a media processing binary (FFmpeg) deployed as a serverless compute layer. The thumbnail extraction uses smart seek — the function first detects the video duration, then seeks to the calculated midpoint (duration / 2) to capture a representative frame rather than the first frame (which is often black). The thumbnail is scaled to 200 pixels wide and uploaded to cloud storage. The function then updates the question record in the database and initiates an asynchronous transcription job.

[0078] Stage 2 — Transcription: A transcription service processes the video audio. An event-driven trigger (e.g., EventBridge rule) monitors for transcription job completion and invokes a transcript processing function.

[0079] Stage 3 — Summarization: The transcript processing function invokes a summarization function that processes the transcript through a large language model (e.g., Bedrock Claude) to generate three outputs: a one-sentence summary, a detailed narrative summary, and a numeric thoughtfulness score (0-5 scale). The summarization function includes idempotency checking (skipping if already summarized), a per-question enable/disable flag, and transcript length limits (truncating at 100,000 characters).

[0080] Each stage operates independently with graceful failure handling. The original video upload returns a success response to the user immediately after the video is verified in cloud storage, regardless of whether thumbnail generation, transcription, or summarization succeeds. This non-blocking design ensures that the core user action (recording a video) is never impeded by auxiliary processing failures.

### 10. Engagement Streak System with Freeze Mechanics

[0081] The engagement subsystem tracks daily content creation activity using a dedicated database table (EngagementDB) with the following fields per user: streakCount, lastVideoDate, streakFreezeAvailable, createdAt, and lastUpdated.

[0082] The streak calculation is implemented as a pure function (no external dependencies) for testability, with the following business rules:

[0083] (a) Same-day activity: If the user has already created content today (lastVideoDate equals current date), the streak count is unchanged.

[0084] (b) Consecutive-day activity: If the user's last content creation was exactly one day ago, the streak count increments by one.

[0085] (c) Missed day with freeze: If more than one day has elapsed and a streak freeze is available, the streak count is maintained and the freeze is consumed (streakFreezeAvailable set to false).

[0086] (d) Missed day without freeze: If more than one day has elapsed and no freeze is available, the streak count resets to one (today's activity counts as the start of a new streak).

[0087] A monthly freeze replenishment process, implemented as a scheduled serverless function, resets streakFreezeAvailable to true for all users on the first day of each calendar month.

[0088] Milestone detection checks whether the new streak count has crossed configurable thresholds (e.g., 7, 30, 100 days) and emits CloudWatch metrics for each milestone reached.

[0089] All date calculations are timezone-aware, using the user's configured timezone (stored in the user status database) to determine whether content creation events fall on the same day, consecutive days, or non-consecutive days. This prevents timezone-related edge cases where a user creating content at 11 PM and 1 AM (crossing midnight in UTC but not in their local timezone) would incorrectly break their streak.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

[0071] FIG. 1 is a block diagram illustrating the overall system architecture of the multimodal data collection pipeline.

[0072] FIG. 2 is a flow diagram illustrating the Phase 1 quality-controlled narrative collection process, including depth scoring and conversation termination logic.

[0073] FIG. 3 is a flow diagram illustrating the Phase 2 rapid-fire psychological profiling process, including response latency capture and trait extraction.

[0074] FIG. 4 is a block diagram illustrating the three-layer personal data graph architecture with cross-layer metadata linking.

[0075] FIG. 5 is a block diagram illustrating the avatar construction process from the three-layer personal data graph.

---

## DRAWINGS

*Note: The following are text descriptions of the drawings to be prepared as formal patent drawings before filing. Each figure should be prepared as a black-and-white line drawing on a separate sheet.*

### FIG. 1 — System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATION (110)                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐     │
│  │Voice Chat │  │Video Recorder│  │Psych Assessment UI     │     │
│  │Interface  │  │              │  │(Timed Questions)       │     │
│  └─────┬─────┘  └──────┬───────┘  └───────────┬────────────┘     │
└────────┼───────────────┼──────────────────────┼──────────────────┘
         │ WebSocket     │ REST/Presigned URL    │ REST API
         ▼               ▼                       ▼
┌────────────────┐ ┌──────────────┐  ┌──────────────────────────┐
│ CONVERSATION   │ │ VIDEO/AUDIO  │  │ PSYCHOLOGICAL ASSESSMENT │
│ ENGINE (120)   │ │ STORAGE      │  │ ENGINE (130)             │
│                │ │ (S3+KMS)     │  │                          │
│ ┌────────────┐ │ └──────────────┘  │ ┌──────────────────────┐ │
│ │Scoring LLM │ │                   │ │Question Bank (310)   │ │
│ │(Depth)     │ │                   │ │                      │ │
│ ├────────────┤ │                   │ ├──────────────────────┤ │
│ │Response LLM│ │                   │ │Trait Extraction      │ │
│ │(Follow-up) │ │                   │ │Engine (330)          │ │
│ ├────────────┤ │                   │ ├──────────────────────┤ │
│ │State Mgmt  │ │                   │ │Decision Pattern      │ │
│ │(DynamoDB)  │ │                   │ │Modeler (340)         │ │
│ └────────────┘ │                   │ └──────────────────────┘ │
└───────┬────────┘                   └────────────┬─────────────┘
        │                                         │
        ▼                                         ▼
┌──────────────────┐                 ┌──────────────────────────┐
│ SUMMARIZATION    │                 │ COGNITION LAYER          │
│ ENGINE (140)     │                 │ - Personality Vectors     │
│ - One-sentence   │                 │ - Decision Profiles       │
│ - Detailed       │                 │ - Raw Responses+Latency   │
│ - Thoughtfulness │                 └────────────┬─────────────┘
└───────┬──────────┘                              │
        │                                         │
        ▼                                         ▼
┌───────────────────────────────────────────────────────────────┐
│              UNIFIED DATA STORE (170)                          │
│  ┌─────────────────┐ ┌──────────────┐ ┌───────────────────┐  │
│  │ EXPERIENCE LAYER │ │COGNITION     │ │ PRESENCE LAYER    │  │
│  │ (410)            │ │LAYER (420)   │ │ (430)             │  │
│  │ - Transcripts    │ │- Personality │ │ - Voice Audio     │  │
│  │ - Summaries      │ │  Vectors     │ │   Samples         │  │
│  │ - Depth Scores   │ │- Decision    │ │ - Video           │  │
│  │ - Per Category   │ │  Profiles    │ │   Recordings      │  │
│  └────────┬─────────┘ └──────┬───────┘ └────────┬──────────┘  │
│           └──────────────────┼──────────────────┘              │
│                    CROSS-LAYER METADATA (440)                  │
│              (userId + questionId + questionType)               │
└───────────────────────────────────────────────────────────────┘
```

### FIG. 2 — Phase 1 Narrative Collection Flow

```
┌──────────────┐
│ User Selects │
│ Question     │
└──────┬───────┘
       ▼
┌──────────────────┐
│ Initialize       │
│ Conversation     │
│ State Object     │
│ (cumScore = 0)   │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ Present Question │
│ (Text + TTS)     │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ User Speaks      │◄─────────────────────────────┐
│ Response         │                               │
└──────┬───────────┘                               │
       ▼                                           │
┌──────────────────┐                               │
│ Transcribe Audio │                               │
│ (3-Tier Cascade) │                               │
└──────┬───────────┘                               │
       ▼                                           │
┌──────────────────────────────┐                   │
│ PARALLEL PROCESSING          │                   │
│ ┌────────────┐ ┌───────────┐ │                   │
│ │ Score      │ │ Generate  │ │                   │
│ │ Depth      │ │ Follow-up │ │                   │
│ │ (Haiku)    │ │ (Sonnet)  │ │                   │
│ └─────┬──────┘ └─────┬─────┘ │                   │
└───────┼──────────────┼───────┘                   │
        ▼              │                           │
┌──────────────────┐   │                           │
│ cumScore +=      │   │                           │
│ turnScore        │   │                           │
└──────┬───────────┘   │                           │
       ▼               │                           │
┌──────────────────┐   │                    ┌──────┴───────┐
│ cumScore >=      │   │         NO         │ Send         │
│ threshold?  ─────┼───┼───────────────────►│ Follow-up    │
│ OR maxTurns?     │   │                    │ Question     │
└──────┬───────────┘   │                    └──────────────┘
       │ YES           │
       ▼               │
┌──────────────────┐   │
│ Save Transcript  │   │
│ Update Progress  │   │
│ Trigger Summary  │   │
│ Offer Video Mem  │   │
└──────────────────┘
```

### FIG. 3 — Phase 2 Psychological Profiling Flow

```
┌────────────────────┐
│ Load Question Bank │
│ (Adaptive Select)  │
└────────┬───────────┘
         ▼
┌────────────────────┐
│ Present Question   │◄──────────────────────┐
│ Start Timer        │                        │
└────────┬───────────┘                        │
         ▼                                    │
┌────────────────────┐                        │
│ Capture Response   │                        │
│ + Latency (ms)     │                        │
│ OR Timeout         │                        │
└────────┬───────────┘                        │
         ▼                                    │
┌────────────────────┐         ┌──────────────┴──┐
│ More Questions?    │── YES ──► Next Question    │
└────────┬───────────┘         └─────────────────┘
         │ NO
         ▼
┌────────────────────────────────────────┐
│ TRAIT EXTRACTION ENGINE                │
│                                        │
│ 1. Map responses → dimension positions │
│ 2. Weight by latency (faster=higher)   │
│ 3. Aggregate → personality vector      │
└────────┬───────────────────────────────┘
         ▼
┌────────────────────────────────────────┐
│ DECISION PATTERN MODELER               │
│                                        │
│ 1. Cluster by decision domain          │
│ 2. Compute domain-specific tendencies  │
│ 3. Output structured profile           │
└────────┬───────────────────────────────┘
         ▼
┌────────────────────────────────────────┐
│ Store in Cognition Layer               │
│ Link to Experience Layer entries       │
└────────────────────────────────────────┘
```

### FIG. 4 — Three-Layer Personal Data Graph

```
┌─────────────────────────────────────────────────────────────┐
│                   PERSONAL DATA GRAPH                        │
│                   (Per User)                                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              EXPERIENCE LAYER (410)                   │    │
│  │                                                       │    │
│  │  Question A ─── Transcript + Scores + Summary         │    │
│  │  Question B ─── Transcript + Scores + Summary         │    │
│  │  Question C ─── Transcript + Scores + Summary         │    │
│  │  ...                                                  │    │
│  │  [Organized by Life-Topic Category]                   │    │
│  └──────────────────────┬────────────────────────────────┘    │
│                         │ Cross-Layer Links                   │
│  ┌──────────────────────┼────────────────────────────────┐    │
│  │              COGNITION LAYER (420)                     │    │
│  │                         │                              │    │
│  │  Personality Vector: [0.73, 0.45, 0.82, 0.31, ...]   │    │
│  │  Decision Profile:                                    │    │
│  │    Financial: risk-averse (0.28)                      │    │
│  │    Career: moderate risk (0.55)                       │    │
│  │    Relationships: risk-seeking (0.81)                 │    │
│  │    Moral: deontological tendency (0.67)               │    │
│  │  Assessment Metadata: timeout_rate=0.05               │    │
│  └──────────────────────┬────────────────────────────────┘    │
│                         │ Cross-Layer Links                   │
│  ┌──────────────────────┼────────────────────────────────┐    │
│  │              PRESENCE LAYER (430)                      │    │
│  │                         │                              │    │
│  │  Voice Audio: [turn1.webm, turn2.webm, ...]           │    │
│  │    (Accumulated across all conversations)              │    │
│  │  Video: [memory1.webm, memory2.webm, ...]             │    │
│  │  Thumbnails: [thumb1.jpg, thumb2.jpg, ...]            │    │
│  └───────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### FIG. 5 — Avatar Construction

```
┌─────────────────────────────────────────────────────────┐
│                 PERSONAL DATA GRAPH                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │Experience │  │Cognition     │  │Presence           │  │
│  │Layer      │  │Layer         │  │Layer              │  │
│  └─────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
└────────┼───────────────┼──────────────────┼──────────────┘
         │               │                  │
         ▼               ▼                  ▼
┌────────────────────────────────────────────────────────┐
│              AVATAR CONSTRUCTION ENGINE (510)            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Personality Simulation Model (520)                │   │
│  │ - RAG system with experience corpus               │   │
│  │ - Calibrated by cognition layer parameters        │   │
│  │ - Higher depth scores = higher weight             │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Voice Synthesis Model (530)                       │   │
│  │ - Trained on accumulated voice audio samples      │   │
│  │ - Diverse emotional contexts from conversations   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Visual Likeness Model (540)                       │   │
│  │ - Trained on video recordings                     │   │
│  │ - Captures facial appearance and mannerisms       │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│              UNIFIED AVATAR MODEL                       │
│  Capable of:                                            │
│  - Conversing in the person's persona                   │
│  - Answering "What would they do?" queries              │
│  - Speaking in the person's voice                       │
│  - Displaying the person's visual likeness              │
└────────────────────────────────────────────────────────┘
```

---

## CLAIMS

*Note: While formal claims are not required for a provisional application, the following claims are included to establish the scope of the invention and to support a subsequent non-provisional filing.*

1. A computer-implemented system for collecting multimodal personal data structured for constructing an AI avatar capable of simulating a person's decision-making behavior, the system comprising:

   a narrative collection engine configured to conduct multi-turn voice conversations with a user across a plurality of life-topic categories, wherein for each conversation:
   - a scoring model evaluates a narrative depth of each user response and produces a numeric depth score,
   - depth scores accumulate into a cumulative score, and
   - the conversation continues until the cumulative score meets or exceeds a configurable quality threshold;

   an audio and video capture subsystem configured to record the user's voice audio during each conversation turn and to record video of the user, storing recordings in association with corresponding conversation data;

   a psychological assessment engine configured to administer a rapid-fire assessment comprising a plurality of questions presented in timed succession, the questions designed to elicit instinctive responses revealing decision-making patterns, values hierarchies, and cognitive tendencies, wherein the assessment engine captures both the user's response and a response latency for each question;

   a trait extraction engine configured to process the rapid-fire assessment responses and response latencies to produce a multi-dimensional personality vector representing the user's position along a plurality of continuous psychological dimensions;

   a decision pattern modeler configured to analyze the personality vector and identify characteristic reasoning patterns of the user, producing a structured decision-making profile; and

   a unified data store configured to maintain a personal data graph for the user comprising:
   - an experience layer containing conversation transcripts and AI-generated narrative summaries,
   - a cognition layer containing the personality vector and structured decision-making profile, and
   - a presence layer containing voice audio samples and video recordings,
   - with cross-layer metadata linking enabling retrieval of related data across layers.

2. The system of claim 1, wherein the psychological assessment engine presents questions from a plurality of psychological dimension categories including at least values-conflict questions, risk-calibration questions, moral-reasoning questions, emotional-tendency questions, and decision-style questions, and wherein the trait extraction engine produces separate dimension scores for each category.

3. The system of claim 1, wherein the trait extraction engine weights responses with shorter response latencies more heavily than responses with longer response latencies when producing the personality vector, on the basis that faster responses more accurately reflect instinctive cognitive patterns.

4. The system of claim 1, further comprising an avatar construction engine configured to:
   - construct a personality simulation model from the experience layer and the cognition layer of the personal data graph;
   - construct a voice synthesis model from the voice audio samples in the presence layer; and
   - construct a visual likeness model from the video recordings in the presence layer;
   - wherein the personality simulation model is configured to generate responses to novel queries by reasoning from both the user's documented experiences and their characteristic decision-making patterns.

5. The system of claim 1, wherein the narrative collection engine and the psychological assessment engine are administered sequentially, with the narrative collection phase preceding the psychological assessment phase, and wherein the psychological assessment engine selects questions based in part on life-topic categories for which the user has completed narrative conversations, enabling targeted profiling of decision-making patterns in domains where narrative data exists.

6. The system of claim 1, wherein the rapid-fire assessment enforces a maximum response time per question, and wherein questions unanswered within the maximum response time are recorded as timeouts and excluded from the personality vector calculation, with the timeout rate itself recorded as a metadata attribute of the psychological profile.

7. The system of claim 1, further comprising an engagement subsystem configured to track a daily activity streak for the user across both narrative conversations and psychological assessment sessions, providing gamification incentives to increase the volume and temporal distribution of collected data.

8. The system of claim 4, wherein the avatar construction engine weights personality attributes extracted from conversations with higher depth scores more heavily than attributes from conversations with lower depth scores when constructing the personality simulation model.

9. The system of claim 1, wherein for each question in the question database, the unified data store supports three distinct content types linked to a single question record:
   - an AI-guided audio conversation with depth scoring, stored with a first set of database field prefixes;
   - a direct video recording uploaded by the user, stored with a second set of database field prefixes; and
   - a supplementary video memory recorded by the user after completion of an audio conversation, stored with a third set of database field prefixes and linked to the existing question record via a database update operation rather than creation of a new record,
   - such that all content modalities for a given question are retrievable through a single database query using the user identifier and question identifier as keys.

10. The system of claim 1, further comprising an asynchronous video processing pipeline triggered upon upload of a video recording, the pipeline comprising:
    - a processing function that verifies the uploaded video exists in encrypted cloud storage, extracts a representative thumbnail image by detecting the video duration and seeking to a calculated midpoint using a media processing binary deployed as a serverless compute layer, updates the question record in the database, and initiates an asynchronous transcription job;
    - an event-driven trigger that invokes a transcript processing function upon completion of the transcription job;
    - a summarization function that processes the transcript through a large language model to generate a one-sentence summary, a detailed narrative summary, and a numeric thoughtfulness score; and
    - wherein each stage of the pipeline operates independently with graceful failure handling, such that the original video upload is reported as successful to the user regardless of whether any subsequent processing stage fails.

11. The system of claim 1, further comprising an engagement subsystem that tracks daily content creation activity with:
    - a streak counter that increments by one for each consecutive day the user creates content, resets to one when a non-consecutive day occurs without a freeze available, and remains unchanged for multiple content creation events on the same day;
    - a streak freeze mechanism that, when a user misses exactly one day and a freeze is available, maintains the current streak count and consumes the freeze;
    - a monthly freeze replenishment process implemented as a scheduled serverless function that resets the freeze availability for all users on the first day of each calendar month;
    - milestone detection at configurable thresholds that emits monitoring metrics when a user's streak reaches a milestone value; and
    - timezone-aware date calculations using the user's configured timezone to determine whether content creation events fall on the same day, consecutive days, or non-consecutive days.

---

## ABSTRACT

A computer-implemented system for collecting structured, quality-controlled multimodal data for AI avatar construction. The system operates in two phases: a first phase conducting AI-moderated voice conversations with cumulative depth scoring to ensure narrative richness, and a second phase administering rapid-fire psychological assessments to capture instinctive decision-making patterns. Collected data is organized into a three-layer personal data graph comprising an experience layer (transcripts and summaries), a cognition layer (personality vectors and decision profiles), and a presence layer (voice and video recordings), with cross-layer metadata linking for holistic avatar construction.
