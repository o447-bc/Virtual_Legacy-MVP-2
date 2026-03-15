# Virtual Legacy Lambda Function Architecture

**Date:** February 14, 2026  
**Status:** Complete Analysis  
**Total Functions:** 35 Lambda functions across 7 categories

---

## Table of Contents

1. [Overview](#overview)
2. [Function Categories](#function-categories)
3. [Shared Modules](#shared-modules)
4. [Architectural Patterns](#architectural-patterns)
5. [Function Inventory](#function-inventory)
6. [Dependencies & Layers](#dependencies--layers)
7. [Best Practices](#best-practices)

---

## Overview

The Virtual Legacy system uses 35 Lambda functions organized into 7 functional categories. Functions follow consistent patterns for security, error handling, and CORS, with shared modules for common logic.

**Design Philosophy:**
- **Separation of Concerns:** Functions grouped by domain (questions, videos, streaks, etc.)
- **Shared Code:** Common utilities in `/shared` directory
- **Modular Design:** WebSocket conversation mode uses 10 sub-modules
- **Security First:** JWT validation, persona-based access control
- **Graceful Degradation:** Non-critical operations never block core functionality

**Deployment:**
- **Runtime:** Python 3.12
- **Architecture:** ARM64 (most functions), x86_64 (FFmpeg-dependent)
- **Memory:** 128MB-1024MB depending on workload
- **Timeout:** 3s-120s depending on operation

---

## Function Categories

### 1. Cognito Triggers (2 functions)
**Purpose:** Handle user signup and confirmation flow

- **PreSignupFunction** - Store persona data during signup
- **PostConfirmationFunction** - Create relationships after email confirmation

**Trigger:** Cognito User Pool events  
**Timeout:** 10s  
**Memory:** 128MB

---

### 2. Question Management (16 functions)
**Purpose:** Question retrieval, progress tracking, level management

**Read Operations (9):**
- getNumQuestionTypes
- getQuestionTypeData
- getQuestionTypes
- getQuestionById
- getNumValidQuestionsForQType
- getTotalValidAllQuestions (cached)
- getUserCompletedQuestionCount (cached)
- getUnansweredQuestionsFromUser
- getUnansweredQuestionsWithText

**Progress Operations (5):**
- getProgressSummary (legacy)
- getProgressSummary2 (enhanced with levels)
- initializeUserProgress
- incrementUserLevel (legacy)
- incrementUserLevel2 (enhanced)

**Utility (2):**
- invalidateTotalValidQuestionsCache
- getAudioQuestionSummaryForVideoRecording

**Timeout:** 3s-15s  
**Memory:** 128MB-256MB

---

### 3. Video Management (7 functions)
**Purpose:** Video upload, processing, transcription, summarization

**Upload Flow:**
- getUploadUrl - Generate S3 presigned URL
- processVideo - Process uploaded video (thumbnail, DB, transcription)
- uploadVideoResponse - Legacy base64 upload (deprecated)

**Transcription Pipeline:**
- startTranscription - Trigger AWS Transcribe job
- processTranscript - Handle transcription completion (EventBridge)
- summarizeTranscript - Generate LLM summaries (Bedrock Claude)

**Retrieval:**
- getMakerVideos - Get all videos for a user

**Timeout:** 10s-120s  
**Memory:** 256MB-1024MB  
**Architecture:** x86_64 (for FFmpeg layer)

---

### 4. Conversation Mode (4 functions)
**Purpose:** Real-time AI conversation via WebSocket

- **wsAuthorizer** - Validate Cognito token on $connect
- **wsConnect** - Store connection in DynamoDB
- **wsDisconnect** - Cleanup on disconnect
- **wsDefault** - Handle all conversation messages (10 sub-modules)

**Timeout:** 10s (connect/disconnect), 30s (default)  
**Memory:** 128MB (connect/disconnect), 512MB (default)  
**Architecture:** x86_64 (for FFmpeg layer in default)

---

### 5. Relationship Management (3 functions)
**Purpose:** Benefactor-maker relationships

- createRelationship - Link benefactor to maker
- getRelationships - Get user's relationships
- validateAccess - Check access permissions

**Timeout:** 3s-10s  
**Memory:** 128MB

---

### 6. Streak Tracking (3 functions)
**Purpose:** Daily engagement tracking

- getStreak - Get streak data
- checkStreak - Get streak with status calculation
- monthlyReset - Reset freeze availability (scheduled)

**Timeout:** 3s-300s (monthly reset)  
**Memory:** 128MB-512MB (monthly reset)  
**Schedule:** monthlyReset runs on 1st of each month (cron)

---

### 7. Invitation System (1 function)
**Purpose:** Email invitations for new users

- sendInviteEmail - Send invitation via AWS SES

**Timeout:** 15s  
**Memory:** 256MB

---


## Shared Modules

### Location: `/functions/shared/`

**Purpose:** Centralized utilities used across multiple Lambda functions

### 1. persona_validator.py

**Purpose:** Centralized persona-based access control

**Key Methods:**
```python
# Extract persona from JWT
persona_info = PersonaValidator.get_user_persona_from_jwt(event)
# Returns: {user_id, email, persona_type, initiator_id, related_user_id}

# Validate legacy maker access
is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)

# Validate legacy benefactor access
is_valid, message = PersonaValidator.validate_legacy_benefactor_access(persona_info)

# Create access denied response
return PersonaValidator.create_access_denied_response(message)

# Add persona context to response
response_body = PersonaValidator.add_persona_context_to_response(response_body, persona_info)
```

**Used By:** All functions requiring persona-based access control

**Benefits:**
- Consistent access control logic
- Single source of truth for persona validation
- Standardized error responses

---

### 2. streak_calculator.py

**Purpose:** Pure functions for streak calculation logic

**Key Functions:**
```python
# Calculate new streak based on days elapsed
new_streak, freeze_used, freeze_available = calculate_new_streak(
    current_streak, days_since_last, freeze_available, last_video_date, current_date
)

# Check if milestone reached (7, 30, 100 days)
milestone = check_milestone(streak_count, previous_streak)
```

**Business Rules:**
- Same day: Streak unchanged
- Consecutive day: Streak +1
- Missed day with freeze: Streak maintained, freeze consumed
- Missed day without freeze: Streak resets to 1

**Used By:** processVideo, checkStreak

**Benefits:**
- Pure functions (no AWS dependencies)
- Easy to test
- Consistent streak logic

---

### 3. timezone_utils.py

**Purpose:** Timezone-aware date calculations for streak tracking

**Key Functions:**
```python
# Get user's timezone (cached)
timezone = get_user_timezone(user_id)  # Returns 'America/New_York' or 'UTC'

# Get current date in user's timezone
current_date = get_current_date_in_timezone(timezone)  # Returns 'YYYY-MM-DD'

# Calculate days between dates
days = calculate_days_between(date1_str, date2_str)

# Check if today is first of month
is_first = is_first_of_month(timezone)
```

**Caching:**
- `@lru_cache(maxsize=1000)` on get_user_timezone
- Reduces DynamoDB reads for repeated calls

**Used By:** processVideo, checkStreak, monthlyReset

**Benefits:**
- Accurate timezone-aware calculations
- Performance optimization via caching
- Graceful fallback to UTC

---

### 4. requirements_streak.txt

**Purpose:** Shared dependencies for streak functions

**Contents:**
```
pytz==2023.3
```

**Used By:** All functions using timezone_utils.py

---

## Architectural Patterns

### Pattern 1: Security - JWT User ID Extraction

**Implementation:**
```python
# ✅ ALWAYS extract from JWT
authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')

if not authenticated_user_id:
    return {
        'statusCode': 401,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': 'Unauthorized'})
    }

# ❌ NEVER trust client-provided userId
# user_id = json.loads(event['body']).get('userId')  # Security vulnerability!
```

**Used By:** All authenticated endpoints (35 functions)

**Why:** Prevents users from accessing other users' data by manipulating request parameters

---

### Pattern 2: CORS Handling

**Implementation:**
```python
# Handle OPTIONS preflight
if event.get('httpMethod') == 'OPTIONS':
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': ''
    }

# All responses include CORS headers
return {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '...',
        'Access-Control-Allow-Methods': '...'
    },
    'body': json.dumps(response_data)
}
```

**Used By:** All REST API functions (31 functions)

**Why:** Enables frontend to call API from different origin

---

### Pattern 3: Graceful Degradation

**Implementation:**
```python
# Non-critical operations wrapped in try/except
try:
    thumbnail_filename = generate_thumbnail(s3_key, user_id)
except Exception as e:
    print(f"Thumbnail generation failed (non-critical): {e}")
    thumbnail_filename = None
    # Video upload still succeeds

# Streak update
try:
    streak_data = update_user_streak(user_id)
except Exception as e:
    print(f"Streak update failed (non-critical): {e}")
    streak_data = {'streakCount': 0, 'error': str(e)}
    # Video upload still succeeds
```

**Used By:** processVideo, uploadVideoResponse

**Why:** Core functionality (video upload) never blocked by auxiliary features

---

### Pattern 4: Cache-Aside with SSM Parameter Store

**Implementation:**
```python
def get_cached_count(user_id):
    ssm_client = boto3.client('ssm')
    cache_key = f'/virtuallegacy/user_completed_count/{user_id}'
    
    # Try cache first
    try:
        response = ssm_client.get_parameter(Name=cache_key)
        cached_data = json.loads(response['Parameter']['Value'])
        return cached_data['count']
    except ssm_client.exceptions.ParameterNotFound:
        # Cache miss - query database
        count = query_database(user_id)
        
        # Store in cache
        ssm_client.put_parameter(
            Name=cache_key,
            Value=json.dumps({'count': count, 'timestamp': datetime.now().isoformat()}),
            Type='String',
            Overwrite=True
        )
        return count

def invalidate_cache(user_id):
    ssm_client = boto3.client('ssm')
    cache_key = f'/virtuallegacy/user_completed_count/{user_id}'
    
    try:
        ssm_client.delete_parameter(Name=cache_key)
    except ssm_client.exceptions.ParameterNotFound:
        pass  # Cache doesn't exist, that's fine
```

**Used By:** 
- getTotalValidAllQuestions (read)
- getUserCompletedQuestionCount (read)
- invalidateTotalValidQuestionsCache (invalidate)
- processVideo (invalidate)

**Cache TTL:** 24 hours (implicit - invalidated on update)

**Why:** Reduces DynamoDB read costs, improves response time

---

### Pattern 5: Async Processing with EventBridge

**Implementation:**
```python
# Step 1: Trigger async job
lambda_client = boto3.client('lambda')
lambda_client.invoke(
    FunctionName=os.environ.get('START_TRANSCRIPTION_FUNCTION_NAME'),
    InvocationType='Event',  # Async invocation
    Payload=json.dumps({
        'userId': user_id,
        'questionId': question_id,
        's3Key': s3_key
    })
)

# Step 2: Job completion triggers EventBridge rule
# EventBridge Rule Pattern:
{
    "source": ["aws.transcribe"],
    "detail-type": ["Transcribe Job State Change"],
    "detail": {
        "TranscriptionJobStatus": ["COMPLETED", "FAILED"]
    }
}

# Step 3: ProcessTranscriptFunction handles completion
def lambda_handler(event, context):
    job_name = event['detail']['TranscriptionJobName']
    status = event['detail']['TranscriptionJobStatus']
    
    if status == 'COMPLETED':
        # Download transcript, process, summarize
        pass
```

**Used By:** Video transcription pipeline (startTranscription → processTranscript → summarizeTranscript)

**Why:** Decouples long-running operations, enables retry logic, scales independently

---

### Pattern 6: Modular WebSocket Handler

**Implementation:**
```python
# wsDefault/app.py - Main handler
def lambda_handler(event, context):
    action = body.get('action')
    
    if action == 'start_conversation':
        return handle_start_conversation(connection_id, user_id, body)
    elif action == 'audio_response':
        return handle_audio_response(connection_id, user_id, body)
    elif action == 'end_conversation':
        return handle_end_conversation(connection_id, user_id)

# Separate modules for each concern
from transcribe import transcribe_audio          # transcribe.py
from llm import score_response, generate_followup  # llm.py
from speech import synthesize_speech             # speech.py
from storage import save_conversation            # storage.py
from conversation_state import get_state, update_state  # conversation_state.py
from config import load_config                   # config.py
```

**Modules:**
1. **app.py** - Main handler, routing
2. **config.py** - SSM parameter loading
3. **conversation_state.py** - State management
4. **transcribe.py** - AWS Transcribe integration
5. **transcribe_deepgram.py** - Deepgram integration (primary)
6. **transcribe_streaming.py** - AWS Transcribe Streaming (fallback)
7. **llm.py** - Bedrock Claude integration
8. **speech.py** - Amazon Polly integration
9. **storage.py** - S3 + DynamoDB persistence

**Used By:** wsDefault function

**Why:** Separation of concerns, testability, maintainability

---

### Pattern 7: Decimal Handling for DynamoDB

**Implementation:**
```python
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

# Usage
return {
    'statusCode': 200,
    'headers': {'Access-Control-Allow-Origin': '*'},
    'body': json.dumps(response_data, cls=DecimalEncoder)
}
```

**Used By:** All functions returning DynamoDB data

**Why:** DynamoDB stores numbers as Decimal, JSON doesn't support Decimal

---

## Function Inventory

### Cognito Triggers

#### 1. PreSignupFunction
**Path:** `cognitoTriggers/preSignup/app.py`  
**Trigger:** Cognito PreSignup  
**Purpose:** Store persona data during signup  
**Tables:** PersonaSignupTempDB (write)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Extract persona data from signup request
2. Store in PersonaSignupTempDB with 1-hour TTL
3. Return success to Cognito

---

#### 2. PostConfirmationFunction
**Path:** `cognitoTriggers/postConfirmation/app.py`  
**Trigger:** Cognito PostConfirmation  
**Purpose:** Create relationships after email confirmation  
**Tables:** PersonaSignupTempDB (read, delete), PersonaRelationshipsDB (write)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Retrieve persona data from PersonaSignupTempDB
2. Update Cognito user attributes (custom:persona_type, etc.)
3. Create relationship in PersonaRelationshipsDB if applicable
4. Delete temp record from PersonaSignupTempDB

---

### Question Management Functions

#### 3. getNumQuestionTypes
**Path:** `questionDbFunctions/getNumQuestionTypes/app.py`  
**Endpoint:** GET /functions/questionDbFunctions  
**Purpose:** Count unique question types  
**Tables:** allQuestionDB (scan)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 4. getQuestionTypeData
**Path:** `questionDbFunctions/getQuestionTypeData/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/typedata  
**Purpose:** Get all question types with metadata  
**Tables:** allQuestionDB (scan)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 5. getQuestionTypes
**Path:** `questionDbFunctions/getQuestionTypes/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/types  
**Purpose:** Get list of question types  
**Tables:** allQuestionDB (scan)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 6. getQuestionById
**Path:** `questionDbFunctions/getQuestionById/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/question  
**Purpose:** Get specific question by ID  
**Tables:** allQuestionDB (get_item)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 7. getNumValidQuestionsForQType
**Path:** `questionDbFunctions/getNumValidQuestionsForQType/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/validcount  
**Purpose:** Count valid questions for a type  
**Tables:** allQuestionDB (scan with filter)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 8. getTotalValidAllQuestions
**Path:** `questionDbFunctions/getTotalValidAllQuestions/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/totalvalidcount  
**Purpose:** Get total valid questions (cached 24 hours)  
**Tables:** allQuestionDB (scan)  
**Cache:** SSM `/virtuallegacy/total_valid_questions_cache`  
**Timeout:** 10s  
**Memory:** 128MB

---

#### 9. getUserCompletedQuestionCount
**Path:** `questionDbFunctions/getUserCompletedQuestionCount/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/usercompletedcount  
**Purpose:** Get user's completed count (cached 24 hours)  
**Tables:** userQuestionStatusDB (query)  
**Cache:** SSM `/virtuallegacy/user_completed_count/{userId}`  
**Timeout:** 10s  
**Memory:** 128MB

---

#### 10. invalidateTotalValidQuestionsCache
**Path:** `questionDbFunctions/invalidateTotalValidQuestionsCache/app.py`  
**Endpoint:** DELETE /functions/questionDbFunctions/invalidate-total-cache  
**Purpose:** Invalidate total questions cache  
**Cache:** SSM `/virtuallegacy/total_valid_questions_cache` (delete)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 11. getUnansweredQuestionsFromUser
**Path:** `questionDbFunctions/getUnansweredQuestionsFromUser/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/unanswered  
**Purpose:** Get unanswered questions for user  
**Tables:** allQuestionDB (scan), userQuestionStatusDB (query)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 12. getUnansweredQuestionsWithText
**Path:** `questionDbFunctions/getUnansweredQuestionsWithText/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/unansweredwithtext  
**Purpose:** Get unanswered questions with full text  
**Tables:** allQuestionDB (scan), userQuestionStatusDB (query)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 13. getProgressSummary
**Path:** `questionDbFunctions/getProgressSummary/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/progress-summary  
**Purpose:** Get progress summary (legacy)  
**Tables:** allQuestionDB (scan), userQuestionStatusDB (query)  
**Timeout:** 15s  
**Memory:** 256MB

---

#### 14. getProgressSummary2
**Path:** `questionDbFunctions/getProgressSummary2/app.py`  
**Endpoint:** GET /functions/questionDbFunctions/progress-summary-2  
**Purpose:** Get enhanced progress with levels  
**Tables:** userQuestionLevelProgressDB (query), userStatusDB (get_item, put_item), allQuestionDB (scan - initialization only)  
**Timeout:** 15s  
**Memory:** 256MB

**Special:** Auto-initializes progress data on first load

---

#### 15. initializeUserProgress
**Path:** `questionDbFunctions/initializeUserProgress/app.py`  
**Endpoint:** POST /functions/questionDbFunctions/initialize-progress  
**Purpose:** Initialize progress for new user  
**Tables:** allQuestionDB (scan), userQuestionLevelProgressDB (put_item), userStatusDB (put_item)  
**Timeout:** 15s  
**Memory:** 256MB

---

#### 16. incrementUserLevel
**Path:** `questionDbFunctions/incrementUserLevel/app.py`  
**Endpoint:** POST /functions/questionDbFunctions/increment-level  
**Purpose:** Increment user level (legacy)  
**Tables:** allQuestionDB (scan), userQuestionLevelProgressDB (get_item, put_item)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 17. incrementUserLevel2
**Path:** `questionDbFunctions/incrementUserLevel2/app.py`  
**Endpoint:** POST /functions/questionDbFunctions/increment-level-2  
**Purpose:** Enhanced level increment with validation  
**Tables:** allQuestionDB (scan), userQuestionLevelProgressDB (query, get_item, put_item, delete_item), userStatusDB (get_item, put_item)  
**Timeout:** 15s  
**Memory:** 256MB

---

#### 18. getAudioQuestionSummaryForVideoRecording
**Path:** `questionDbFunctions/getAudioQuestionSummaryForVideoRecording/app.py`  
**Endpoint:** POST /functions/questionDbFunctions/get-audio-summary-for-video  
**Purpose:** Get audio summary for video memory recording  
**Tables:** userQuestionStatusDB (get_item)  
**Timeout:** 5s  
**Memory:** 128MB

---


### Video Management Functions

#### 19. getUploadUrl
**Path:** `videoFunctions/getUploadUrl/app.py`  
**Endpoint:** POST /functions/videoFunctions/get-upload-url  
**Purpose:** Generate S3 presigned URL for video upload  
**S3:** Generate presigned PUT URL (5-minute expiry)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Extract questionId, questionType, contentType
2. Generate unique filename with timestamp
3. Create presigned URL for S3 PUT
4. Return URL, s3Key, filename

---

#### 20. processVideo
**Path:** `videoFunctions/processVideo/app.py`  
**Endpoint:** POST /functions/videoFunctions/process-video  
**Purpose:** Process uploaded video (thumbnail, DB, transcription)  
**Tables:** userQuestionStatusDB (put_item, update_item), userQuestionLevelProgressDB (get_item, put_item), EngagementDB (get_item, put_item), userStatusDB (get_item)  
**S3:** Get video, put thumbnail  
**Cache:** SSM `/virtuallegacy/user_completed_count/{userId}` (delete)  
**Invokes:** startTranscription (async)  
**Timeout:** 60s  
**Memory:** 1024MB  
**Architecture:** x86_64 (FFmpeg)  
**Layer:** ffmpeg-layer:1

**Flow:**
1. Verify video exists in S3
2. Generate thumbnail using FFmpeg (non-blocking)
3. Update userQuestionStatusDB
4. Update userQuestionLevelProgressDB (if regular video)
5. Update EngagementDB for streak (non-blocking)
6. Invalidate cache (non-blocking)
7. Trigger transcription if enabled (async)

**Shared Modules:** timezone_utils, streak_calculator

---

#### 21. uploadVideoResponse (Legacy)
**Path:** `videoFunctions/uploadVideoResponse/app.py`  
**Endpoint:** POST /functions/videoFunctions/upload  
**Purpose:** Upload video via base64 (deprecated)  
**Status:** Deprecated - use presigned URL pattern instead  
**Timeout:** 60s  
**Memory:** 1024MB  
**Architecture:** x86_64 (FFmpeg)

**Issue:** Hits API Gateway 10MB limit with base64 encoding

---

#### 22. startTranscription
**Path:** `videoFunctions/startTranscription/app.py`  
**Invoked By:** processVideo (async)  
**Purpose:** Start AWS Transcribe job  
**Tables:** userStatusDB (get_item), userQuestionStatusDB (get_item, update_item)  
**AWS:** Transcribe StartTranscriptionJob  
**Timeout:** 60s  
**Memory:** 256MB

**Flow:**
1. Verify video type (regular or video_memory)
2. Start Transcribe job with appropriate settings
3. Update transcriptionStatus to IN_PROGRESS

---

#### 23. processTranscript
**Path:** `videoFunctions/processTranscript/app.py`  
**Trigger:** EventBridge (Transcribe job completion)  
**Purpose:** Download transcript, trigger summarization  
**Tables:** userQuestionStatusDB (get_item, update_item)  
**S3:** Get transcript from Transcribe output, put processed transcript  
**Invokes:** summarizeTranscript (async)  
**Timeout:** 30s  
**Memory:** 256MB

**Flow:**
1. Get transcription job details
2. Download transcript from S3
3. Extract text from JSON
4. Save processed transcript to S3
5. Update userQuestionStatusDB with transcript
6. Trigger summarization (async)

---

#### 24. summarizeTranscript
**Path:** `videoFunctions/summarizeTranscript/app.py`  
**Invoked By:** processTranscript (async), wsDefault (conversation mode)  
**Purpose:** Generate LLM summaries using Bedrock Claude  
**Tables:** userQuestionStatusDB (get_item, update_item)  
**S3:** Get transcript  
**AWS:** Bedrock InvokeModel (Claude 3 Haiku)  
**SSM:** Get prompts from `/life-story-app/llm-prompts/*`  
**Timeout:** 120s  
**Memory:** 512MB

**Flow:**
1. Load transcript from S3 or parameter
2. Get LLM prompts from SSM
3. Generate one-sentence summary (Claude Haiku)
4. Generate detailed summary (Claude Haiku)
5. Update userQuestionStatusDB with summaries
6. Update summarizationStatus to COMPLETED

---

#### 25. getMakerVideos
**Path:** `videoFunctions/getMakerVideos/app.py`  
**Endpoint:** GET /videos/maker/{makerId}  
**Purpose:** Get all videos for a legacy maker  
**Tables:** userQuestionStatusDB (query), PersonaRelationshipsDB (query), allQuestionDB (get_item)  
**S3:** Generate presigned URLs for videos and thumbnails  
**Timeout:** 15s  
**Memory:** 256MB

**Flow:**
1. Validate access (relationship check)
2. Query userQuestionStatusDB for maker's videos
3. Enrich with question text from allQuestionDB
4. Generate presigned URLs for S3 objects
5. Return video list with metadata

---

### Conversation Mode Functions

#### 26. wsAuthorizer
**Path:** `conversationFunctions/wsAuthorizer/app.py`  
**Route:** $connect (custom authorizer)  
**Purpose:** Validate Cognito access token  
**AWS:** Cognito GetUser  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Extract token from query parameter
2. Validate with Cognito
3. Return IAM policy (Allow/Deny)

---

#### 27. wsConnect
**Path:** `conversationFunctions/wsConnect/app.py`  
**Route:** $connect  
**Purpose:** Store connection in DynamoDB  
**Tables:** WebSocketConnectionsDB (put_item)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Extract connectionId and userId
2. Store in WebSocketConnectionsDB with 2-hour TTL
3. Return success

---

#### 28. wsDisconnect
**Path:** `conversationFunctions/wsDisconnect/app.py`  
**Route:** $disconnect  
**Purpose:** Cleanup on disconnect  
**Tables:** WebSocketConnectionsDB (delete_item)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Extract connectionId
2. Delete from WebSocketConnectionsDB
3. Return success

---

#### 29. wsDefault
**Path:** `conversationFunctions/wsDefault/app.py`  
**Route:** $default (all messages)  
**Purpose:** Handle conversation messages  
**Tables:** WebSocketConnectionsDB (get_item), userQuestionStatusDB (put_item), userQuestionLevelProgressDB (put_item)  
**S3:** Put audio, put transcript  
**AWS:** Transcribe, Bedrock (Claude), Polly  
**SSM:** Get config from `/virtuallegacy/conversation/*`, `/virtuallegacy/deepgram/*`  
**Invokes:** summarizeTranscript (async)  
**Timeout:** 30s  
**Memory:** 512MB  
**Architecture:** x86_64 (FFmpeg)  
**Layer:** ffmpeg-layer:1

**Modules:**
1. **app.py** - Main handler, message routing
2. **config.py** - Load SSM parameters (score-goal, max-turns, models)
3. **conversation_state.py** - Manage conversation state
4. **transcribe.py** - AWS Transcribe integration
5. **transcribe_deepgram.py** - Deepgram integration (primary, 0.5s latency)
6. **transcribe_streaming.py** - AWS Transcribe Streaming (fallback, 5.6s latency)
7. **llm.py** - Bedrock Claude integration (scoring + response generation)
8. **speech.py** - Amazon Polly Neural TTS
9. **storage.py** - S3 + DynamoDB persistence

**Message Types:**
- start_conversation → Initialize conversation
- audio_response → Process user audio
- user_response → Process text (testing)
- end_conversation → Save and cleanup

**Flow (audio_response):**
1. Validate connection
2. Upload audio to S3
3. Transcribe with Deepgram (0.5s) or fallback to AWS Transcribe
4. Score response with Claude Haiku (0-5 points)
5. Generate follow-up with Claude Sonnet
6. Synthesize speech with Polly Neural
7. Send ai_speaking message with audio URL
8. Update cumulative score
9. Check if goal reached (12 points) or max turns (20)
10. If complete, save conversation and send conversation_complete

---

### Relationship Management Functions

#### 30. createRelationship
**Path:** `relationshipFunctions/createRelationship/app.py`  
**Endpoint:** POST /relationships  
**Purpose:** Create benefactor-maker relationship  
**Tables:** PersonaRelationshipsDB (put_item)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 31. getRelationships
**Path:** `relationshipFunctions/getRelationships/app.py`  
**Endpoint:** GET /relationships  
**Purpose:** Get user's relationships  
**Tables:** PersonaRelationshipsDB (query on main table + GSI)  
**AWS:** Cognito AdminGetUser (enrich with email)  
**Timeout:** 10s  
**Memory:** 128MB

**Flow:**
1. Query as initiator (main table)
2. Query as related user (GSI)
3. Enrich with user emails from Cognito
4. Return combined list

---

#### 32. validateAccess
**Path:** `relationshipFunctions/validateAccess/app.py`  
**Endpoint:** GET /relationships/validate  
**Purpose:** Validate access to user's content  
**Tables:** PersonaRelationshipsDB (query)  
**Timeout:** 3s  
**Memory:** 128MB

---

### Streak Tracking Functions

#### 33. getStreak
**Path:** `streakFunctions/getStreak/app.py`  
**Endpoint:** GET /streak  
**Purpose:** Get streak data  
**Tables:** EngagementDB (get_item)  
**Timeout:** 3s  
**Memory:** 128MB

---

#### 34. checkStreak
**Path:** `streakFunctions/checkStreak/app.py`  
**Endpoint:** GET /streak/check  
**Purpose:** Get streak with status calculation  
**Tables:** EngagementDB (get_item), userStatusDB (get_item - for timezone)  
**Timeout:** 5s  
**Memory:** 128MB

**Shared Modules:** timezone_utils

**Status Calculation:**
- active: Uploaded today or yesterday
- at_risk: Missed day but freeze available
- broken: Missed day without freeze

---

#### 35. monthlyReset
**Path:** `streakFunctions/monthlyReset/app.py`  
**Trigger:** EventBridge Schedule (cron: 0 0 1 * ? *)  
**Purpose:** Reset freeze availability on 1st of month  
**Tables:** EngagementDB (scan, batch_write_item)  
**AWS:** CloudWatch PutMetricData  
**Timeout:** 300s (5 minutes)  
**Memory:** 512MB

**Flow:**
1. Scan all users in EngagementDB
2. Reset freezeUsedThisMonth to False
3. Set streakFreezeAvailable to True
4. Batch update all records
5. Log metrics to CloudWatch

---

### Invitation System

#### 36. sendInviteEmail
**Path:** `inviteFunctions/sendInviteEmail/app.py`  
**Endpoint:** POST /invites/send  
**Purpose:** Send invitation email via SES  
**Tables:** PersonaSignupTempDB (put_item)  
**AWS:** SES SendEmail  
**Timeout:** 15s  
**Memory:** 256MB

**Flow:**
1. Generate invite token
2. Store in PersonaSignupTempDB with TTL
3. Send email via SES with registration link
4. Return success

---

## Dependencies & Layers

### Lambda Layers

#### 1. ffmpeg-layer:1
**ARN:** `arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1`  
**Purpose:** FFmpeg binary for video processing  
**Architecture:** x86_64  
**Used By:** processVideo, uploadVideoResponse, wsDefault

**Contents:**
- FFmpeg binary at `/opt/bin/ffmpeg`
- Required for thumbnail generation
- Required for audio format conversion

**Note:** Functions using this layer must be x86_64 architecture

---

### Python Dependencies

**Common (most functions):**
```
boto3 (AWS SDK)
botocore
```

**Streak Functions:**
```
pytz==2023.3  # Timezone calculations
```

**Conversation Mode:**
```
boto3
requests  # For Deepgram API
```

**Video Processing:**
```
boto3
subprocess  # For FFmpeg
```

---

## Best Practices

### 1. ✅ Consistent Error Handling

```python
try:
    # Main logic
    result = process_data()
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(result)
    }
except ClientError as e:
    print(f"DynamoDB error: {e}")
    return {
        'statusCode': 500,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': str(e)})
    }
except Exception as e:
    print(f"Unexpected error: {e}")
    return {
        'statusCode': 500,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': str(e)})
    }
```

---

### 2. ✅ Logging for Debugging

```python
print(f"[FUNCTION_NAME] Starting processing for user {user_id}")
print(f"[FUNCTION_NAME] Request body: {json.dumps(body)}")
print(f"[FUNCTION_NAME] DynamoDB response: {response}")
print(f"[FUNCTION_NAME] Completed successfully")
```

**Benefits:**
- CloudWatch Logs for debugging
- Structured logging with prefixes
- Easy to trace execution flow

---

### 3. ✅ Environment Variables

```python
# SAM template
Environment:
  Variables:
    WEBSOCKET_API_ENDPOINT: !Sub ${ConversationWebSocketApi}.execute-api.${AWS::Region}.amazonaws.com/prod
    START_TRANSCRIPTION_FUNCTION_NAME: !GetAtt StartTranscriptionFunction.Arn

# Lambda function
websocket_endpoint = os.environ.get('WEBSOCKET_API_ENDPOINT')
transcription_function = os.environ.get('START_TRANSCRIPTION_FUNCTION_NAME')
```

**Benefits:**
- No hardcoded values
- Easy to change per environment
- CloudFormation references

---

### 4. ✅ Shared Code Reuse

```python
# Add shared directory to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

# Import shared modules
from persona_validator import PersonaValidator
from timezone_utils import get_user_timezone
from streak_calculator import calculate_new_streak
```

**Benefits:**
- DRY principle
- Consistent logic
- Easy to test

---

### 5. ✅ Non-Blocking Operations

```python
# Critical operation
video_uploaded = upload_to_s3(video_data)

# Non-critical operations (don't block on failure)
try:
    thumbnail = generate_thumbnail(video_data)
except Exception as e:
    print(f"Thumbnail failed (non-critical): {e}")
    thumbnail = None

try:
    streak_data = update_streak(user_id)
except Exception as e:
    print(f"Streak update failed (non-critical): {e}")
    streak_data = {}

# Return success regardless
return {'success': True, 'thumbnail': thumbnail, 'streak': streak_data}
```

---

### 6. ✅ Async Invocations

```python
# Don't wait for long-running operations
lambda_client = boto3.client('lambda')
lambda_client.invoke(
    FunctionName='StartTranscriptionFunction',
    InvocationType='Event',  # Async - don't wait
    Payload=json.dumps(payload)
)

# Continue immediately
return {'message': 'Processing started'}
```

---

### 7. ✅ Timeout Configuration

**Guidelines:**
- Simple reads: 3s
- Complex queries: 10-15s
- Video processing: 60s
- LLM operations: 120s
- Batch operations: 300s

**Always set appropriate timeout to prevent hanging functions**

---

## Summary

**Total Functions:** 35 Lambda functions  
**Categories:** 7 functional domains  
**Shared Modules:** 4 reusable utilities  
**Layers:** 1 (FFmpeg for video processing)  
**Architectures:** ARM64 (most), x86_64 (FFmpeg-dependent)

**Strengths:**
- ✅ Consistent security patterns (JWT extraction)
- ✅ Graceful degradation (non-blocking operations)
- ✅ Modular design (shared code, WebSocket modules)
- ✅ Async processing (EventBridge, Lambda invocations)
- ✅ Comprehensive error handling
- ✅ Cache optimization (SSM Parameter Store)

**Areas for Improvement:**
- Consider consolidating similar functions (getProgressSummary vs getProgressSummary2)
- Add more unit tests for shared modules
- Implement circuit breakers for external API calls (Deepgram)
- Add request/response validation schemas

---

**Last Updated:** February 14, 2026  
**Status:** Complete Lambda architecture analysis
