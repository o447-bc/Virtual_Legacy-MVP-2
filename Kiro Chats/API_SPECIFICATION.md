# Virtual Legacy API Specification

**Date:** February 14, 2026  
**Status:** Complete Analysis  
**API Gateway Base URL:** `https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod`  
**WebSocket URL:** `wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod`

---

## Table of Contents

1. [Authentication](#authentication)
2. [REST API Endpoints](#rest-api-endpoints)
3. [WebSocket API](#websocket-api)
4. [Database Schema](#database-schema)
5. [Common Patterns](#common-patterns)
6. [Error Handling](#error-handling)

---

## Authentication

**Method:** AWS Cognito with JWT tokens

**User Pool:** `us-east-1_KsG65yYlo`  
**Authorizer:** CognitoAuthorizer (attached to all REST endpoints)

**Request Headers:**
```
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

**Security Pattern:**
```python
# ALWAYS extract user ID from JWT, NEVER trust client parameters
authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
```

---

## REST API Endpoints

### Question Management


#### 1. GET /functions/questionDbFunctions/typedata
**Function:** GetQuestionTypeDataFunction  
**Purpose:** Retrieve all question types with metadata  
**Auth:** Required  
**Query Parameters:** None  
**Response:**
```json
{
  "questionTypes": ["childhood", "family", "career"],
  "questionTypeData": {
    "childhood": {
      "friendlyName": "Childhood Memories",
      "description": "Questions about your early years"
    }
  }
}
```

#### 2. GET /functions/questionDbFunctions/types
**Function:** GetQuestionTypesFunction  
**Purpose:** Get list of all question types  
**Auth:** Required  
**Response:** `["childhood", "family", "career", ...]`

#### 3. GET /functions/questionDbFunctions/unanswered
**Function:** GetUnansweredQuestionsFromUserFunction  
**Purpose:** Get unanswered questions for authenticated user  
**Auth:** Required  
**Query Parameters:**
- `questionType` (required): Type of questions to retrieve  
**Response:**
```json
{
  "questions": [
    {
      "questionId": "childhood-001",
      "questionText": "What was your favorite childhood memory?",
      "questionType": "childhood"
    }
  ]
}
```

#### 4. GET /functions/questionDbFunctions/unansweredwithtext
**Function:** GetUnansweredQuestionsWithTextFunction  
**Purpose:** Get unanswered questions with full text  
**Auth:** Required  
**Query Parameters:**
- `questionType` (required)  
**Response:** Similar to /unanswered with additional text fields

#### 5. GET /functions/questionDbFunctions/question
**Function:** GetQuestionByIdFunction  
**Purpose:** Get specific question by ID  
**Auth:** Required  
**Query Parameters:**
- `questionId` (required)  
**Response:**
```json
{
  "questionId": "childhood-001",
  "questionText": "What was your favorite childhood memory?",
  "questionType": "childhood",
  "isValid": true
}
```

#### 6. GET /functions/questionDbFunctions/validcount
**Function:** GetNumValidQuestionsForQTypeFunction  
**Purpose:** Count valid questions for a question type  
**Auth:** Required  
**Query Parameters:**
- `questionType` (required)  
**Response:** `{ "count": 15 }`

#### 7. GET /functions/questionDbFunctions/totalvalidcount
**Function:** GetTotalValidAllQuestionsFunction  
**Purpose:** Get total count of all valid questions (cached 24 hours)  
**Auth:** Required  
**Cache:** SSM Parameter `/virtuallegacy/total_valid_questions_cache`  
**Response:** `{ "totalCount": 150 }`

#### 8. DELETE /functions/questionDbFunctions/invalidate-total-cache
**Function:** InvalidateTotalValidQuestionsCacheFunction  
**Purpose:** Invalidate total questions cache  
**Auth:** Required  
**Response:** `{ "message": "Cache invalidated" }`

#### 9. GET /functions/questionDbFunctions/usercompletedcount
**Function:** GetUserCompletedQuestionCountFunction  
**Purpose:** Get count of completed questions for user (cached 24 hours)  
**Auth:** Required  
**Cache:** SSM Parameter `/virtuallegacy/user_completed_count/{userId}`  
**Response:** `{ "count": 12 }`

---

### Progress Tracking

#### 10. GET /functions/questionDbFunctions/progress-summary
**Function:** GetProgressSummaryFunction  
**Purpose:** Get user progress summary (legacy endpoint)  
**Auth:** Required  
**Query Parameters:**
- `userId` (optional, defaults to authenticated user)  
**Response:**
```json
{
  "progressByType": {
    "childhood": { "answered": 5, "total": 15 },
    "family": { "answered": 3, "total": 12 }
  }
}
```

#### 11. GET /functions/questionDbFunctions/progress-summary-2
**Function:** GetProgressSummary2Function  
**Purpose:** Get enhanced progress summary with level tracking  
**Auth:** Required  
**Query Parameters:**
- `userId` (optional)  
**Response:**
```json
{
  "progressItems": [
    {
      "questionType": "childhood",
      "friendlyName": "Childhood Memories",
      "currentLevel": 2,
      "questionsInLevel": 5,
      "answeredInLevel": 3,
      "totalAnswered": 8,
      "totalQuestions": 15
    }
  ]
}
```

#### 12. POST /functions/questionDbFunctions/initialize-progress
**Function:** InitializeUserProgressFunction  
**Purpose:** Initialize progress tracking for new user  
**Auth:** Required  
**Body:** `{}`  
**Response:** `{ "message": "Progress initialized" }`

#### 13. POST /functions/questionDbFunctions/increment-level
**Function:** IncrementUserLevelFunction  
**Purpose:** Increment user level for question type (legacy)  
**Auth:** Required  
**Body:**
```json
{
  "questionType": "childhood"
}
```

#### 14. POST /functions/questionDbFunctions/increment-level-2
**Function:** IncrementUserLevel2Function  
**Purpose:** Enhanced level increment with validation  
**Auth:** Required  
**Body:**
```json
{
  "questionType": "childhood"
}
```

#### 15. POST /functions/questionDbFunctions/get-audio-summary-for-video
**Function:** GetAudioQuestionSummaryForVideoRecordingFunction  
**Purpose:** Get audio summary for video memory recording  
**Auth:** Required  
**Body:**
```json
{
  "questionId": "childhood-001"
}
```
**Response:**
```json
{
  "audioOneSentence": "Brief summary",
  "audioDetailedSummary": "Detailed summary"
}
```

---

### Video Management

#### 16. POST /functions/videoFunctions/get-upload-url
**Function:** GetUploadUrlFunction  
**Purpose:** Get S3 presigned URL for video upload  
**Auth:** Required  
**Body:**
```json
{
  "questionId": "childhood-001",
  "questionType": "childhood",
  "contentType": "video/webm"
}
```
**Response:**
```json
{
  "uploadUrl": "https://virtual-legacy.s3.amazonaws.com/...",
  "s3Key": "user-responses/{userId}/{filename}.webm",
  "filename": "childhood-001_20260214_120000_abc123.webm",
  "expiresIn": 300
}
```

#### 17. POST /functions/videoFunctions/process-video
**Function:** ProcessVideoFunction  
**Purpose:** Process uploaded video (thumbnail, transcription, DynamoDB)  
**Auth:** Required  
**Timeout:** 60 seconds  
**Memory:** 1024 MB  
**Body:**
```json
{
  "questionId": "childhood-001",
  "questionType": "childhood",
  "questionText": "What was your favorite childhood memory?",
  "s3Key": "user-responses/{userId}/video.webm",
  "filename": "video.webm",
  "allowTranscription": true
}
```
**Response:**
```json
{
  "message": "Video processed successfully",
  "filename": "video.webm",
  "s3Key": "user-responses/{userId}/video.webm",
  "thumbnailFilename": "thumbnail.jpg",
  "streakData": { "currentStreak": 5, "longestStreak": 10 }
}
```

#### 18. POST /functions/videoFunctions/upload
**Function:** UploadVideoResponseFunction (Legacy)  
**Purpose:** Upload video via base64 (deprecated, use presigned URL)  
**Auth:** Required  
**Timeout:** 60 seconds  
**Body:**
```json
{
  "questionId": "childhood-001",
  "questionType": "childhood",
  "questionText": "Question text",
  "videoData": "base64_encoded_video_string"
}
```
**Note:** Hits 10MB API Gateway limit. Use presigned URL pattern instead.

#### 19. GET /videos/maker/{makerId}
**Function:** GetMakerVideosFunction  
**Purpose:** Get all videos for a legacy maker  
**Auth:** Required  
**Path Parameters:**
- `makerId`: User ID of the legacy maker  
**Query Parameters:**
- `questionType` (optional): Filter by question type  
**Response:**
```json
{
  "videos": [
    {
      "questionId": "childhood-001",
      "questionText": "Question text",
      "videoUrl": "presigned_s3_url",
      "thumbnailUrl": "presigned_s3_url",
      "timestamp": "2026-02-14T12:00:00Z",
      "transcript": "Transcribed text",
      "oneSentence": "Brief summary",
      "detailedSummary": "Detailed summary"
    }
  ]
}
```

---

### Relationship Management

#### 20. POST /relationships
**Function:** CreateRelationshipFunction  
**Purpose:** Create relationship between benefactor and maker  
**Auth:** Required  
**Body:**
```json
{
  "relatedUserId": "user-id-of-maker",
  "relationshipType": "benefactor_to_maker"
}
```

#### 21. GET /relationships
**Function:** GetRelationshipsFunction  
**Purpose:** Get all relationships for authenticated user  
**Auth:** Required  
**Response:**
```json
{
  "relationships": [
    {
      "initiatorId": "benefactor-id",
      "relatedUserId": "maker-id",
      "relationshipType": "benefactor_to_maker",
      "createdAt": "2026-02-14T12:00:00Z",
      "relatedUserEmail": "maker@example.com",
      "relatedUserName": "John Doe"
    }
  ]
}
```

#### 22. GET /relationships/validate
**Function:** ValidateAccessFunction  
**Purpose:** Validate if user has access to another user's content  
**Auth:** Required  
**Query Parameters:**
- `targetUserId`: User ID to check access for  
**Response:**
```json
{
  "hasAccess": true,
  "relationshipType": "benefactor_to_maker"
}
```

---

### Streak Tracking

#### 23. GET /streak
**Function:** GetStreakFunction  
**Purpose:** Get current streak data for user  
**Auth:** Required  
**Response:**
```json
{
  "userId": "user-id",
  "currentStreak": 5,
  "longestStreak": 10,
  "lastEngagementDate": "2026-02-14",
  "freezeAvailable": true,
  "freezeUsedThisMonth": false
}
```

#### 24. GET /streak/check
**Function:** CheckStreakFunction  
**Purpose:** Check and update streak status  
**Auth:** Required  
**Response:** Same as GET /streak

---

### Invitation System

#### 25. POST /invites/send
**Function:** SendInviteEmailFunction  
**Purpose:** Send invitation email to new legacy maker  
**Auth:** Required  
**Body:**
```json
{
  "email": "newmaker@example.com",
  "message": "Optional personal message"
}
```
**Response:**
```json
{
  "message": "Invitation sent successfully",
  "inviteToken": "token-id"
}
```

---


## WebSocket API

**Endpoint:** `wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod`  
**Purpose:** Real-time AI conversation feature

### Connection

**URL:** `wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod?token={COGNITO_ACCESS_TOKEN}`

**Routes:**
- `$connect`: WebSocketAuthorizerFunction → WebSocketConnectFunction
- `$disconnect`: WebSocketDisconnectFunction
- `$default`: WebSocketDefaultFunction (handles all messages)

**Authentication:** Cognito access token in query parameter, validated by custom authorizer

### Message Protocol

**Client → Server Messages:**

1. **start_conversation**
```json
{
  "action": "start_conversation",
  "questionId": "childhood-001",
  "questionType": "childhood"
}
```

2. **audio_response**
```json
{
  "action": "audio_response",
  "audioData": "base64_encoded_audio",
  "turnNumber": 1
}
```

3. **user_response** (text-based, for testing)
```json
{
  "action": "user_response",
  "text": "User's response text",
  "turnNumber": 1
}
```

4. **end_conversation**
```json
{
  "action": "end_conversation"
}
```

**Server → Client Messages:**

1. **ai_speaking**
```json
{
  "type": "ai_speaking",
  "text": "AI's question or response",
  "audioUrl": "presigned_s3_url_to_mp3",
  "turnNumber": 0,
  "cumulativeScore": 0,
  "scoreGoal": 12
}
```

2. **score_update**
```json
{
  "type": "score_update",
  "turnScore": 3.5,
  "cumulativeScore": 7.0,
  "scoreGoal": 12,
  "turnNumber": 2,
  "reasoning": "Response showed good detail and emotion"
}
```

3. **conversation_complete**
```json
{
  "type": "conversation_complete",
  "finalScore": 12.5,
  "totalTurns": 5,
  "audioTranscriptUrl": "s3://virtual-legacy/conversations/.../transcript.json",
  "audioDetailedSummary": "Summary of the conversation"
}
```

4. **upload_url** (for audio upload)
```json
{
  "type": "upload_url",
  "uploadUrl": "presigned_s3_url",
  "s3Key": "conversations/{userId}/{questionId}/audio/turn-1.webm"
}
```

5. **error**
```json
{
  "type": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

### WebSocket Lambda Configuration

**WebSocketDefaultFunction:**
- **Timeout:** 30 seconds
- **Memory:** 512 MB
- **Architecture:** x86_64
- **Layer:** ffmpeg-layer:1

**Permissions:**
- DynamoDB: Read WebSocketConnectionsDB
- API Gateway: ManageConnections
- Transcribe: StartTranscriptionJob, GetTranscriptionJob
- Bedrock: InvokeModel (Claude 3.5 Sonnet, Claude 3 Haiku)
- Polly: SynthesizeSpeech
- S3: PutObject, GetObject (conversations/*, test-audio/*)
- SSM: GetParameter (/virtuallegacy/conversation/*, /virtuallegacy/deepgram/*)
- DynamoDB: PutItem, GetItem (userQuestionStatusDB, userQuestionLevelProgressDB)
- Lambda: Invoke SummarizeTranscriptFunction

---

## Database Schema

### DynamoDB Tables

#### 1. allQuestionDB
**Purpose:** Master question repository  
**Primary Key:** `questionId` (String)  
**Attributes:**
- `questionText`: String
- `questionType`: String
- `isValid`: Boolean
- `friendlyName`: String (for question type)
- `description`: String

#### 2. userQuestionStatusDB
**Purpose:** Track user's answered questions  
**Primary Key:** `userId` (String, HASH) + `questionId` (String, RANGE)  
**Attributes:**
- `questionType`: String
- `questionText`: String
- `filename`: String (video filename)
- `s3Key`: String (S3 object key)
- `thumbnailFilename`: String
- `timestamp`: String (ISO 8601)
- `videoTranscript`: String (optional)
- `videoOneSentence`: String (optional)
- `videoDetailedSummary`: String (optional)
- `videoMemoryTranscript`: String (optional, for post-conversation videos)
- `videoMemoryOneSentence`: String (optional)
- `videoMemoryDetailedSummary`: String (optional)
- `audioTranscript`: String (optional, for conversation mode)
- `audioOneSentence`: String (optional)
- `audioDetailedSummary`: String (optional)
- `transcriptionStatus`: String (NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED)
- `summarizationStatus`: String (NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED)
- `enableTranscript`: Boolean

#### 3. userQuestionLevelProgressDB
**Purpose:** Track user progress by question type and level  
**Primary Key:** `userId` (String, HASH) + `questionType` (String, RANGE)  
**Attributes:**
- `currentLevel`: Number
- `questionsInLevel`: Number
- `answeredInLevel`: Number
- `totalAnswered`: Number
- `totalQuestions`: Number
- `lastUpdated`: String (ISO 8601)

#### 4. userStatusDB
**Purpose:** User profile and settings  
**Primary Key:** `userId` (String)  
**Attributes:**
- `timezone`: String
- `personaType`: String (legacy_maker, legacy_benefactor)
- `createdAt`: String (ISO 8601)
- `lastActive`: String (ISO 8601)

#### 5. PersonaRelationshipsDB
**Purpose:** Link benefactors to makers  
**Primary Key:** `initiator_id` (String, HASH) + `related_user_id` (String, RANGE)  
**GSI:** RelatedUserIndex on `related_user_id`  
**Attributes:**
- `relationshipType`: String (benefactor_to_maker)
- `createdAt`: String (ISO 8601)
- `status`: String (active, inactive)

#### 6. PersonaSignupTempDB
**Purpose:** Temporary storage during signup  
**Primary Key:** `userName` (String)  
**TTL:** `ttl` attribute (1 hour)  
**Attributes:**
- `personaType`: String
- `initiatorId`: String (optional)
- `relatedUserId`: String (optional)

#### 7. EngagementDB (UserProgressDB)
**Purpose:** Streak tracking  
**Primary Key:** `userId` (String)  
**Attributes:**
- `currentStreak`: Number
- `longestStreak`: Number
- `lastEngagementDate`: String (YYYY-MM-DD)
- `freezeAvailable`: Boolean
- `freezeUsedThisMonth`: Boolean
- `lastUpdated`: String (ISO 8601)

#### 8. WebSocketConnectionsDB
**Purpose:** Track active WebSocket connections  
**Primary Key:** `connectionId` (String)  
**TTL:** `ttl` attribute (2 hours)  
**Attributes:**
- `userId`: String
- `questionId`: String
- `questionType`: String
- `connectedAt`: String (ISO 8601)

---

## Common Patterns

### 1. User ID Extraction
```python
# ALWAYS extract from JWT, NEVER trust client
user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
```

### 2. CORS Headers
```python
# All Lambda responses must include
{
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    },
    'body': json.dumps(response_data)
}
```

### 3. Cache Invalidation
```python
# After updating user data, invalidate cache
try:
    ssm_client = boto3.client('ssm')
    cache_param = f'/virtuallegacy/user_completed_count/{user_id}'
    ssm_client.delete_parameter(Name=cache_param)
except ssm_client.exceptions.ParameterNotFound:
    pass  # Cache doesn't exist, that's fine
except Exception as e:
    print(f"Cache invalidation failed (non-critical): {e}")
```

### 4. S3 Presigned URLs
```python
# Generate presigned URL for uploads
s3_client = boto3.client('s3')
upload_url = s3_client.generate_presigned_url(
    'put_object',
    Params={
        'Bucket': 'virtual-legacy',
        'Key': s3_key,
        'ContentType': content_type
    },
    ExpiresIn=300  # 5 minutes
)
```

### 5. Video Upload Flow
```
1. Frontend: POST /get-upload-url → Get presigned URL
2. Frontend: PUT to presigned URL → Upload video directly to S3
3. Frontend: POST /process-video → Trigger processing
4. Lambda: Generate thumbnail, update DynamoDB, trigger transcription
```

### 6. Transcription Flow
```
1. ProcessVideoFunction: Invoke StartTranscriptionFunction
2. StartTranscriptionFunction: Start AWS Transcribe job
3. EventBridge: Transcribe job complete → ProcessTranscriptFunction
4. ProcessTranscriptFunction: Download transcript, invoke SummarizeTranscriptFunction
5. SummarizeTranscriptFunction: Use Bedrock Claude to generate summaries
6. Update userQuestionStatusDB with transcript and summaries
```

---

## Error Handling

### Common Error Codes

**400 Bad Request:**
- Missing required parameters
- Invalid parameter format
- Invalid question ID

**401 Unauthorized:**
- Missing or invalid JWT token
- Expired token

**403 Forbidden:**
- User doesn't have access to requested resource
- Relationship validation failed

**404 Not Found:**
- Question not found
- User not found
- Video not found in S3

**413 Content Too Large:**
- Video exceeds 10MB when using base64 upload
- Solution: Use presigned URL upload pattern

**500 Internal Server Error:**
- Lambda execution error
- DynamoDB operation failed
- S3 operation failed
- Bedrock/Transcribe/Polly API error

### Error Response Format
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Additional error details"
}
```

### Debugging Steps

1. **Check CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/[FUNCTION-NAME] --since 10m --follow
```

2. **Common Issues:**
- "AccessDeniedException" → Check IAM permissions
- "Works on second try" → Initialization race condition
- "CORS error" → Check response headers
- "413 error" → Use presigned URL pattern
- "MediaElementAudioSource outputs zeroes" → Add `crossOrigin='anonymous'` to audio element

---

## API Limits

**API Gateway:**
- Maximum payload: 10 MB
- Maximum timeout: 29 seconds
- Throttle: 10,000 requests per second (default)

**Lambda:**
- Maximum timeout: 900 seconds (15 minutes)
- Maximum memory: 10,240 MB
- Maximum payload: 6 MB (synchronous), 256 KB (asynchronous)

**S3:**
- Maximum object size: 5 TB
- Presigned URL expiry: Configurable (typically 5-15 minutes)

**DynamoDB:**
- Maximum item size: 400 KB
- On-demand billing: No throughput limits

---

## Cost Estimates

**Per 1000 Conversations (5 turns each):**
- AWS Transcribe: ~$12.50 (5000 audio files × $0.0025)
- Bedrock Claude: ~$8.00 (scoring + responses)
- Amazon Polly: ~$2.00 (5000 TTS requests)
- S3: ~$0.50 (storage + requests)
- DynamoDB: ~$1.00 (on-demand requests)
- Lambda: ~$1.00 (execution time)
- **Total: ~$25 per 1000 conversations**

**Per 1000 Video Uploads:**
- S3: ~$2.00 (storage + bandwidth)
- Lambda: ~$3.00 (processing + thumbnail generation)
- Transcribe: ~$2.50 (if enabled)
- Bedrock: ~$1.50 (summarization)
- **Total: ~$9 per 1000 videos**

---

**Last Updated:** February 14, 2026  
**Status:** Complete API specification ready for development reference
