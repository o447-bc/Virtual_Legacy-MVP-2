# VIRTUAL LEGACY CODEBASE - COMPLETE ONBOARDING FOR KIRO

## MISSION
You are taking over maintenance and development of Virtual Legacy, a production AWS-based application that is currently deployed. Your role is to understand this codebase completely, maintain code quality, fix bugs systematically, and implement new features following established patterns.

## APPLICATION OVERVIEW

### What Virtual Legacy Does
Virtual Legacy is a video-based digital legacy platform that helps people preserve their life stories for future generations. The application enables:

**Core User Roles:**
1. **MAKERS** - People who record video responses to life story questions
2. **BENEFICIARIES** - People who will receive and view these video memories (family members, descendants)

**Primary User Journey:**
1. A Maker signs up and creates their account
2. They can invite Beneficiaries (who they're creating memories for)
3. Makers are presented with curated life story questions organized by categories (Childhood, Schooling, Values, Career, Relationships, etc.)
4. For each question, Makers can:
   - Record a standard video response (30 seconds to 5 minutes)
   - Use AI Conversation Mode for a more natural, interview-style experience with follow-up questions
5. Videos are automatically processed: transcribed, thumbnails generated, and stored
6. Makers track their progress with streaks, completion percentages, and level-up achievements
7. Beneficiaries can eventually access these video memories (future feature)

### Key Features Implemented

**1. Question System**
- 100+ curated life story questions across multiple categories
- Questions stored in allQuestionDB with metadata (category, difficulty, tags)
- User progress tracked in userQuestionStatusDB (answered, skipped, in-progress)
- Questions presented in sequence with smart ordering

**2. Video Recording & Processing**
- Browser-based video recording (WebRTC)
- Upload to S3 with presigned URLs
- Automatic thumbnail generation using FFmpeg
- Video metadata storage with timestamps, duration, file sizes
- Support for both standard questions and conversation follow-ups

**3. AI Conversation Mode**
- Natural conversation flow where AI asks follow-up questions based on user responses
- Real-time transcription using Deepgram streaming API
- WebSocket-based communication for low-latency interaction
- Conversation sessions tracked with full history
- Follow-up questions generated contextually and stored as video memories

**4. Transcription System**
- Deepgram integration for audio-to-text conversion
- Streaming transcription for real-time conversation mode
- Batch transcription for standard video uploads
- Transcripts stored with video metadata for searchability
- Chunked processing for longer videos to handle API limits

**5. Progress Tracking & Gamification**
- Daily streak tracking (consecutive days of recording)
- Level system based on videos completed
- Progress bars showing completion by category and overall
- Achievement notifications for milestones
- Cached progress calculations for performance

**6. Relationship Management**
- Makers can invite Beneficiaries via email
- Relationship linking between Maker and Beneficiary accounts
- Access control for who can view whose videos
- Invitation system with Cognito user creation

**7. Authentication & Authorization**
- AWS Cognito for user management
- Custom attributes: firstName, lastName, userType (Maker/Beneficiary)
- Cognito triggers for user lifecycle events
- JWT token-based API authentication
- Fine-grained access control per user and relationship


## TECHNICAL ARCHITECTURE

### Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite as build tool and dev server
- Tailwind CSS for styling
- shadcn/ui component library
- AWS Amplify SDK for Cognito authentication
- React Router for navigation
- Context API for state management
- WebRTC for video recording
- WebSocket client for real-time features

**Backend:**
- AWS SAM (Serverless Application Model) for infrastructure as code
- Python 3.11 Lambda functions
- API Gateway (REST + WebSocket)
- DynamoDB for all data persistence
- S3 for video and media storage
- Cognito for authentication
- Deepgram API for transcription
- FFmpeg (Lambda Layer) for video processing

**Development Tools:**
- Git for version control
- AWS CLI and SAM CLI for deployment
- Boto3 for AWS SDK in Python
- pytest for testing

### AWS Infrastructure Details

**Region:** us-east-1 (primary deployment)

**S3 Buckets:**
- Main bucket structure:
  - `raw-videos/` - Original uploaded videos from users
  - `processed-videos/` - Transcoded/optimized videos (if applicable)
  - `thumbnails/` - Auto-generated video thumbnails
  - `user-uploads/` - Temporary upload staging area

**DynamoDB Tables:**

1. **allQuestionDB**
   - Purpose: Master question library
   - Partition Key: questionId (string)
   - Sort Key: questionType (string) - values: "standard", "followup", "conversation"
   - Attributes: Question (text), category, difficulty, tags, order, isActive
   - Access Pattern: Get question by ID, query by type, scan for admin

2. **userQuestionStatusDB**
   - Purpose: Track which questions each user has answered/skipped
   - Partition Key: userId (string - Cognito sub)
   - Sort Key: questionId (string)
   - Attributes: questionType, status (answered/skipped/in-progress), Question (text), answeredAt, videoId
   - Access Pattern: Get user's progress, query all questions for a user, update status

3. **userVideoDB**
   - Purpose: Store video metadata and transcripts
   - Partition Key: userId (string)
   - Sort Key: videoId (string - UUID)
   - Attributes: questionId, questionType, s3Key, thumbnailKey, duration, transcript, transcriptStatus, uploadedAt, conversationId (if from conversation mode)
   - Access Pattern: Get user's videos, get specific video, query by question

4. **userStreakDB**
   - Purpose: Track daily engagement streaks
   - Partition Key: userId (string)
   - Sort Key: date (string - YYYY-MM-DD)
   - Attributes: videosRecorded, currentStreak, longestStreak, lastActivityDate
   - Access Pattern: Get user's current streak, update daily activity

5. **relationshipDB**
   - Purpose: Link Makers to Beneficiaries
   - Partition Key: makerId (string)
   - Sort Key: beneficiaryId (string)
   - Attributes: relationshipType, invitedAt, acceptedAt, status (pending/active)
   - Access Pattern: Get Maker's beneficiaries, get Beneficiary's makers

6. **conversationDB**
   - Purpose: Track AI conversation sessions
   - Partition Key: userId (string)
   - Sort Key: conversationId (string - UUID)
   - Attributes: questionId, startedAt, completedAt, status, followUpCount, transcript
   - Access Pattern: Get user's conversations, get conversation details

**Lambda Functions (in SamLambda/functions/):**

*Cognito Triggers (cognitoTriggers/):*
- preSignUp - Validate user registration
- postConfirmation - Initialize user data after signup
- preAuthentication - Custom auth logic

*Question Functions (questionDbFunctions/):*
- getQuestions - Fetch questions for user (with filtering)
- getQuestionById - Get single question details
- updateQuestionStatus - Mark question as answered/skipped
- getNextQuestion - Smart question ordering logic

*Video Functions (videoFunctions/):*
- generateUploadUrl - Create presigned S3 URL for upload
- processVideoUpload - Triggered on S3 upload, generates thumbnail
- getVideos - Fetch user's video library
- deleteVideo - Remove video and cleanup S3
- transcribeVideo - Send video to Deepgram for transcription
- updateTranscript - Store transcription results

*Conversation Functions (conversationFunctions/):*
- startConversation - Initialize conversation session
- handleWebSocketMessage - Process real-time messages
- generateFollowUp - AI logic for follow-up questions
- endConversation - Finalize conversation and save
- streamTranscription - Handle Deepgram streaming

*Streak Functions (streakFunctions/):*
- updateStreak - Increment streak on video completion
- getStreak - Fetch current streak data
- calculateLevel - Determine user level based on activity

*Relationship Functions (relationshipFunctions/):*
- inviteBeneficiary - Send invitation email
- acceptInvitation - Link Maker and Beneficiary
- getRelationships - Fetch user's relationships

*Invite Functions (inviteFunctions/):*
- createInvite - Generate invitation with token
- processInvite - Handle invitation acceptance
- resendInvite - Resend invitation email

*Shared Utilities (shared/):*
- db_utils.py - DynamoDB helper functions
- s3_utils.py - S3 operations
- auth_utils.py - JWT validation, user context
- response_utils.py - Standard API response formatting
- constants.py - Shared constants and configuration

**API Gateway:**

*REST API:*
- `/questions` - GET, POST
- `/questions/{id}` - GET, PUT, DELETE
- `/videos` - GET, POST
- `/videos/{id}` - GET, DELETE
- `/upload-url` - POST (generate presigned URL)
- `/conversations` - GET, POST
- `/conversations/{id}` - GET, PUT
- `/streak` - GET, POST
- `/relationships` - GET, POST
- `/invite` - POST

*WebSocket API:*
- Connection management: $connect, $disconnect, $default
- Routes: startConversation, sendMessage, endConversation
- Used for real-time conversation mode with streaming transcription

**External Services:**
- Deepgram API - Speech-to-text transcription (streaming and batch)
- AWS SES - Email sending for invitations (future)


## FRONTEND ARCHITECTURE (FrontEndCode/)

### Directory Structure

```
FrontEndCode/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # shadcn/ui base components
│   │   ├── VideoRecorder.tsx
│   │   ├── QuestionCard.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── ConversationMode.tsx
│   │   └── ...
│   ├── pages/            # Route-level page components
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Questions.tsx
│   │   ├── VideoLibrary.tsx
│   │   ├── Profile.tsx
│   │   └── ...
│   ├── contexts/         # React Context providers
│   │   ├── AuthContext.tsx
│   │   ├── QuestionContext.tsx
│   │   └── ...
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useVideoRecorder.ts
│   │   ├── useWebSocket.ts
│   │   └── ...
│   ├── services/         # API client functions
│   │   ├── api.ts
│   │   ├── questionService.ts
│   │   ├── videoService.ts
│   │   ├── conversationService.ts
│   │   └── ...
│   ├── lib/              # Utility functions
│   │   └── utils.ts
│   ├── config/           # Configuration files
│   │   └── constants.ts
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── amplifyconfiguration.json  # Amplify config
├── public/               # Static assets
├── amplify/              # Amplify backend config
└── package.json
```

### Key Frontend Components

**Authentication Flow:**
- Uses AWS Amplify Auth with Cognito
- AuthContext provides: currentUser, signIn, signUp, signOut, isAuthenticated
- Protected routes check authentication status
- JWT tokens automatically included in API requests

**Video Recording:**
- VideoRecorder component uses MediaRecorder API
- Captures video/audio from user's camera and microphone
- Records in WebM format, converts to MP4 if needed
- Uploads to S3 using presigned URLs from backend
- Shows recording timer, preview, and controls

**Question Display:**
- QuestionCard shows question text, category, difficulty
- Tracks answered/skipped status with visual indicators
- "Record Answer" button launches VideoRecorder
- "Start Conversation" button launches ConversationMode

**Conversation Mode:**
- ConversationMode component manages WebSocket connection
- Real-time audio streaming to backend
- Displays AI-generated follow-up questions
- Shows live transcription of user's speech
- Records video while conversation is active

**Dashboard:**
- Shows user's progress: total videos, current streak, level
- Category-wise progress bars
- Recent videos grid with thumbnails
- Quick access to next question

**State Management:**
- AuthContext: User authentication state
- QuestionContext: Current question, progress data
- Local state in components for UI interactions
- API calls trigger re-fetches to update data

### Frontend-Backend Integration

**API Client (services/api.ts):**
```typescript
- Base URL from environment variable
- Axios instance with interceptors
- Automatic JWT token injection in headers
- Error handling and retry logic
- Response transformation
```

**Service Modules:**
- questionService: fetchQuestions, getQuestionById, updateStatus
- videoService: uploadVideo, getVideos, deleteVideo, getUploadUrl
- conversationService: startConversation, sendMessage, endConversation
- streakService: getStreak, updateStreak

**WebSocket Connection:**
- Connects to API Gateway WebSocket endpoint
- Sends audio chunks for real-time transcription
- Receives follow-up questions and transcription results
- Handles connection lifecycle (connect, disconnect, reconnect)


## BACKEND ARCHITECTURE (SamLambda/)

### SAM Template Structure (template.yml)

The template.yml file defines all AWS resources:

**Globals:**
- Runtime: python3.11
- Timeout: 30 seconds (varies by function)
- Environment variables: REGION, TABLE_NAMES, DEEPGRAM_API_KEY (from SSM)
- Layers: FFmpegLayer for video processing

**Resources Defined:**
- All Lambda functions with their triggers
- DynamoDB tables with indexes
- API Gateway REST and WebSocket APIs
- S3 buckets with event notifications
- IAM roles and policies
- Cognito User Pool and triggers
- Lambda Layers (FFmpeg)

### Critical Data Flows

**Flow 1: Standard Video Recording**
1. User clicks "Record Answer" on question
2. Frontend requests presigned S3 URL from `generateUploadUrl` Lambda
3. User records video in browser
4. Frontend uploads video directly to S3 using presigned URL
5. S3 triggers `processVideoUpload` Lambda
6. Lambda generates thumbnail using FFmpeg
7. Lambda stores video metadata in userVideoDB
8. Lambda updates userQuestionStatusDB (status = "answered")
9. Lambda triggers `transcribeVideo` Lambda (async)
10. Transcription sent to Deepgram, results stored back in userVideoDB
11. Lambda calls `updateStreak` to increment user's streak
12. Frontend polls or receives notification of completion

**Flow 2: AI Conversation Mode**
1. User clicks "Start Conversation" on question
2. Frontend calls `startConversation` Lambda via REST API
3. Lambda creates conversation record in conversationDB
4. Lambda returns WebSocket connection URL
5. Frontend establishes WebSocket connection
6. User starts speaking, audio chunks streamed via WebSocket
7. `handleWebSocketMessage` Lambda receives audio chunks
8. Lambda forwards audio to Deepgram streaming API
9. Deepgram returns real-time transcription
10. Lambda sends transcription back to frontend via WebSocket
11. When user pauses, Lambda calls `generateFollowUp` to create next question
12. Follow-up question sent to frontend via WebSocket
13. User answers follow-up, process repeats
14. User ends conversation, frontend calls `endConversation`
15. Lambda saves all follow-ups as separate video records
16. Lambda updates conversation status to "completed"

**Flow 3: User Invitation**
1. Maker enters Beneficiary email in UI
2. Frontend calls `createInvite` Lambda
3. Lambda generates unique invitation token
4. Lambda creates pending relationship in relationshipDB
5. Lambda sends invitation email (via SES or stored for manual send)
6. Beneficiary clicks invitation link
7. Link directs to signup page with token
8. Beneficiary signs up, `postConfirmation` trigger fires
9. Trigger calls `processInvite` Lambda with token
10. Lambda links Maker and Beneficiary in relationshipDB
11. Lambda updates relationship status to "active"

**Flow 4: Progress Calculation**
1. User loads Dashboard
2. Frontend calls `getQuestions` with userId
3. Lambda queries userQuestionStatusDB for all user's questions
4. Lambda calculates: total answered, by category, overall percentage
5. Lambda queries userStreakDB for current streak
6. Lambda calculates user level based on video count
7. Lambda returns aggregated progress data
8. Frontend displays progress bars and stats
9. Results cached in frontend for 5 minutes to reduce API calls

### Lambda Function Details

**Shared Utilities (functions/shared/):**

*db_utils.py:*
- get_item(table_name, key) - Fetch single item
- put_item(table_name, item) - Insert/update item
- query_items(table_name, key_condition) - Query with conditions
- scan_table(table_name, filter_expression) - Full table scan
- update_item(table_name, key, updates) - Partial update
- delete_item(table_name, key) - Remove item
- batch_write(table_name, items) - Bulk operations

*s3_utils.py:*
- generate_presigned_url(bucket, key, expiration) - Upload URL
- upload_file(bucket, key, file_data) - Direct upload
- download_file(bucket, key) - Retrieve file
- delete_file(bucket, key) - Remove file
- list_objects(bucket, prefix) - List files in folder

*auth_utils.py:*
- verify_jwt_token(token) - Validate Cognito JWT
- get_user_from_token(token) - Extract user info
- check_user_permission(user_id, resource_id) - Authorization
- get_cognito_user(user_id) - Fetch user attributes

*response_utils.py:*
- success_response(data, status_code=200) - Standard success
- error_response(message, status_code=400) - Standard error
- cors_headers() - CORS headers for API Gateway

**Video Processing Pipeline:**

*generateUploadUrl:*
- Input: userId, questionId, fileType
- Validates user authentication
- Generates unique videoId (UUID)
- Creates presigned S3 URL for raw-videos/ folder
- Returns: uploadUrl, videoId, expiresIn

*processVideoUpload:*
- Triggered by S3 event on raw-videos/ upload
- Extracts video metadata (duration, resolution, size)
- Uses FFmpeg to generate thumbnail (frame at 1 second)
- Uploads thumbnail to thumbnails/ folder
- Creates record in userVideoDB with metadata
- Triggers transcribeVideo asynchronously

*transcribeVideo:*
- Input: videoId, userId
- Downloads video from S3
- Extracts audio using FFmpeg
- Sends audio to Deepgram batch API
- Receives transcription text
- Updates userVideoDB with transcript
- Sets transcriptStatus to "completed"

**Conversation System:**

*startConversation:*
- Input: userId, questionId
- Creates conversationId (UUID)
- Stores initial conversation record in conversationDB
- Returns WebSocket connection URL and conversationId

*handleWebSocketMessage:*
- Receives messages on WebSocket routes
- Routes: "audioChunk", "endConversation", "ping"
- For audioChunk: forwards to Deepgram streaming
- Maintains conversation state in memory
- Sends transcription and follow-ups back to client

*generateFollowUp:*
- Input: conversationId, previousTranscript
- Uses AI logic (or predefined rules) to generate follow-up
- Creates new question record in allQuestionDB (type: "followup")
- Links follow-up to parent conversation
- Returns follow-up question text

*endConversation:*
- Input: conversationId
- Finalizes conversation record
- Creates video records for each follow-up answered
- Updates userQuestionStatusDB for all questions
- Calculates conversation duration and stats

**Deepgram Integration:**

*Streaming (for conversation mode):*
- WebSocket connection to Deepgram
- Send audio chunks as they arrive
- Receive interim and final transcripts
- Handle connection errors and reconnection

*Batch (for standard videos):*
- Upload audio file to Deepgram
- Poll for completion or use callback
- Retrieve full transcript
- Parse and store results

*Configuration:*
- API key stored in AWS Systems Manager Parameter Store
- Model: nova-2 (general purpose)
- Language: en-US
- Features: punctuation, diarization (speaker detection)


## DEPLOYMENT ARCHITECTURE

### Deployment Scripts

**deploy-all.sh:**
- Master deployment script
- Runs backend deployment first (SAM)
- Then runs frontend deployment (Amplify)
- Validates deployment success
- Usage: `./deploy-all.sh`

**deploy-backend.sh:**
- Builds SAM application
- Packages Lambda functions
- Deploys CloudFormation stack
- Updates SSM parameters
- Runs: `sam build && sam deploy --config-file samconfig.toml`

**deploy-frontend.sh:**
- Builds React app with Vite
- Syncs build to S3 or Amplify hosting
- Invalidates CloudFront cache
- Updates environment variables

### Environment Configuration

**Backend (samconfig.toml):**
- Stack name: virtual-legacy-backend
- Region: us-east-1
- S3 bucket for deployment artifacts
- Parameter overrides for environment-specific values
- Capabilities: CAPABILITY_IAM, CAPABILITY_AUTO_EXPAND

**Frontend (.env files):**
- VITE_API_ENDPOINT - API Gateway URL
- VITE_WEBSOCKET_ENDPOINT - WebSocket API URL
- VITE_COGNITO_USER_POOL_ID
- VITE_COGNITO_CLIENT_ID
- VITE_AWS_REGION
- VITE_S3_BUCKET

**SSM Parameters (stored in AWS Systems Manager):**
- /virtual-legacy/deepgram/api-key
- /virtual-legacy/conversation/max-followups
- /virtual-legacy/video/max-duration
- /virtual-legacy/email/sender-address

### Deployment Checklist (from DEPLOYMENT_CHECKLIST.md)

Pre-deployment:
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] SSM parameters set
- [ ] S3 buckets created
- [ ] Cognito User Pool configured
- [ ] Deepgram API key valid

Backend deployment:
- [ ] SAM build successful
- [ ] CloudFormation stack deployed
- [ ] Lambda functions updated
- [ ] API Gateway endpoints active
- [ ] DynamoDB tables created/updated

Frontend deployment:
- [ ] Build completes without errors
- [ ] Environment variables injected
- [ ] Assets uploaded to hosting
- [ ] DNS/CloudFront configured

Post-deployment:
- [ ] Smoke tests pass
- [ ] Authentication working
- [ ] Video upload functional
- [ ] Transcription working
- [ ] WebSocket connection stable

## CODING CONVENTIONS & PATTERNS

### Naming Conventions

**DynamoDB:**
- Tables: camelCase with "DB" suffix (userQuestionStatusDB)
- Attributes: camelCase (userId, questionId, createdAt)
- Keys: Descriptive names (userId, questionId, not just "id")

**Lambda Functions:**
- Function names: camelCase (generateUploadUrl, processVideoUpload)
- File names: snake_case (generate_upload_url.py)
- Handler: lambda_handler(event, context)

**S3 Keys:**
- Folders: kebab-case with trailing slash (raw-videos/, processed-videos/)
- Files: {userId}/{videoId}/{filename} structure
- Thumbnails: {userId}/{videoId}/thumbnail.jpg

**Frontend:**
- Components: PascalCase (VideoRecorder.tsx, QuestionCard.tsx)
- Hooks: camelCase with "use" prefix (useAuth.ts, useVideoRecorder.ts)
- Services: camelCase (questionService.ts, videoService.ts)
- Constants: UPPER_SNAKE_CASE (MAX_VIDEO_DURATION, API_ENDPOINT)

### Code Patterns

**Lambda Function Structure:**
```python
import json
import boto3
from shared.db_utils import get_item, put_item
from shared.response_utils import success_response, error_response
from shared.auth_utils import verify_jwt_token

def lambda_handler(event, context):
    try:
        # 1. Extract and validate input
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')
        
        # 2. Authenticate user
        token = event['headers'].get('Authorization')
        user = verify_jwt_token(token)
        
        # 3. Authorize access
        if user['sub'] != user_id:
            return error_response('Unauthorized', 403)
        
        # 4. Business logic
        result = perform_operation(user_id)
        
        # 5. Return response
        return success_response(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(str(e), 500)
```

**React Component Pattern:**
```typescript
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { questionService } from '@/services/questionService';

export const ComponentName: React.FC = () => {
  const { currentUser } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await questionService.getQuestions(currentUser.id);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};
```

**Error Handling:**
- Always use try-catch blocks in Lambda functions
- Log errors with context (user ID, operation, timestamp)
- Return user-friendly error messages
- Use appropriate HTTP status codes
- Never expose internal errors to frontend

**DynamoDB Access Patterns:**
- Use get_item for single item retrieval (most efficient)
- Use query for partition key + sort key conditions
- Avoid scan operations (expensive, slow)
- Use batch operations for multiple items
- Implement pagination for large result sets

**S3 Operations:**
- Always use presigned URLs for uploads (security)
- Set appropriate expiration times (15 minutes for uploads)
- Use lifecycle policies for old data cleanup
- Organize files in logical folder structure
- Include metadata in object tags

### Testing Patterns

**Unit Tests (tests/unit/):**
- Test individual functions in isolation
- Mock external dependencies (DynamoDB, S3, Deepgram)
- Use pytest fixtures for common setup
- Test happy path and error cases
- Aim for 80%+ code coverage

**Integration Tests (tests/integration/):**
- Test full workflows end-to-end
- Use real AWS services (test environment)
- Clean up test data after runs
- Test API Gateway + Lambda integration
- Verify DynamoDB data consistency

**Frontend Tests:**
- Component tests with React Testing Library
- Mock API calls with MSW (Mock Service Worker)
- Test user interactions and state changes
- Snapshot tests for UI consistency


## HISTORICAL CONTEXT - Q CHATS FOLDER

The "Q Chats" folder contains 30+ detailed conversation logs documenting the entire development journey of Virtual Legacy. These are CRITICAL for understanding design decisions, implementation details, and troubleshooting patterns.

### REQUIRED READING - Read these Q Chat files in order:

**Phase 1: Foundation (Read First)**
1. `2026-01-05 Virtual Legacy Comprehensive Summary.md` - MOST IMPORTANT: Complete system overview
2. `DEPLOYMENT_CHECKLIST.md` - Deployment procedures and validation
3. `IMPLEMENTATION_SUMMARY.md` - Core feature implementation details

**Phase 2: Authentication & User Management**
4. `2025-09-13 AUTHENTICATION_AND_ACCESS_CONTROL_DOCUMENTATION.md` - Auth system design
5. `2025-09-13 fixCameraOff.md` - Camera permission handling
6. `2025-12-31 Fix new maker login confirmation.md` - Login flow fixes
7. `PERSONA_IMPLEMENTATION_SUMMARY.md` - User roles (Maker/Beneficiary)
8. `FIRST_LAST_NAME_IMPLEMENTATION_SUMMARY.md` - User profile fields

**Phase 3: Question System**
9. `2025-09-7 Persona relationship implenent and UI.md` - Question-user relationships
10. `2026-01-01 Fixed question and followup sequence.md` - Question ordering logic
11. `2025-08-14 Adding Personas.html` - Question categorization
12. `2025-08-17 Getting personas to work.html` - Question system debugging

**Phase 4: Video & Media**
13. `2025-01-VIDEO-MEMORY-IMPLEMENTATION.md` - Video recording architecture
14. `2025-11-02 Update naming audio-video naming.md` - Media file naming conventions
15. `2025-11-16 Update benefactor for audio.md` - Audio handling improvements
16. `2025-01-BENEFACTOR-DASHBOARD-AUDIO-VIDEO-UPDATE.md` - Dashboard video features
17. `SHORT_VIDEO_THUMBNAIL_FIX.md` - Thumbnail generation fixes
18. `FFMPEG_LAYER_DOCUMENTATION.md` - FFmpeg Lambda layer setup

**Phase 5: Transcription System**
19. `2025-10-25 Deepgram Strategy.md` - Transcription service selection
20. `2025-10-25 Tradeoff analysis with all in with Deepgram.md` - Deepgram vs alternatives
21. `2025-10-25 Transcription via chunking.md` - Handling long videos
22. `2025-11-16 Transcription added to all video memories.md` - Transcription rollout
23. `TRANSCRIPTION_IMPLEMENTATION_SUMMARY.md` - Complete transcription docs
24. `TRANSCRIPTION_QUICK_REFERENCE.md` - Transcription API reference
25. `VIDEO_MEMORY_TRANSCRIPTION_PLAN.md` - Transcription architecture
26. `DEEPGRAM_TEST_RESULTS.md` - Transcription testing results
27. `STREAMING_TRANSCRIPTION_IMPLEMENTATION.md` - Real-time transcription

**Phase 6: Conversation Mode**
28. `2025-10-12 CONVERSATION_FEATURE_DOCUMENTATION.md` - Conversation mode design
29. `CONVERSATION_IMPLEMENTATION_PLAN.md` - Implementation roadmap
30. `CONVERSATION_QUICK_REFERENCE.md` - Conversation API reference
31. `CONVERSATION_TEST_PLAN.md` - Testing procedures
32. `2025-10-12 LLM video summarization.md` - AI integration
33. `2025-10-12 Summary of async batch conversation processing slowness.md` - Performance optimization
34. `2025-10-26 Add video recording after conversation.md` - Video capture in conversations

**Phase 7: WebSocket & Real-time**
35. `WEBSOCKET_DEPLOYMENT_SUMMARY.md` - WebSocket setup
36. `WEBSOCKET_MESSAGE_PROTOCOL.md` - Message format specification
37. `RUN_WEBSOCKET_TEST.md` - WebSocket testing guide
38. `STREAMING_IMPLEMENTATION_COMPLETE.md` - Streaming feature completion
39. `STREAMING_TEST_RESULTS.md` - Streaming performance data

**Phase 8: Progress & Gamification**
40. `2025-10-10 STREAK_IMPLEMENTATION_SUMMARY.md` - Streak system
41. `2025-10-04 Added total question progress bars.md` - Progress tracking
42. `2025-10-11 Total Progress cache bug.md` - Progress calculation fixes
43. `2025-10-25 Fixing level up.md` - Level system debugging
44. `2025-08-17 Improving progess bar speed.html` - Performance optimization

**Phase 9: Relationships & Invitations**
45. `2025-09-11 Linking Benefactor to Maker.md` - Relationship system
46. `2025-09-7 Persona relationship implenent and UI.md` - Relationship UI

**Phase 10: Dashboard & UI**
47. `2025-09-17 Speed Up Dashboard Load.md` - Dashboard performance
48. `2026-01-10 Audio Visualizer Q Plan.md` - Audio visualization
49. `2026-02-14 Graphic Equalizer for AI voice install.md` - Audio UI components
50. `2025-11-16 Completed Annotation.md` - Video annotation features

**Phase 11: Deployment & Infrastructure**
51. `DEPLOYMENT_GUIDE.md` - Step-by-step deployment
52. `DEPLOYMENT_README.md` - Deployment overview
53. `VISUAL_DEPLOYMENT_GUIDE.md` - Visual deployment walkthrough
54. `CICD_SETUP.md` - CI/CD pipeline setup
55. `DEPLOYMENT_COMPLETE.md` - Deployment completion checklist

**Phase 12: Data & Configuration**
56. `DATA_FORMAT_AUDIT.md` - Data schema documentation
57. `NAMING_CONVENTION_VERIFICATION_REPORT.md` - Naming standards
58. `CONFIGURATION_FIXED.md` - Configuration issues resolved
59. `CAMERA_FIX_VERIFICATION.md` - Camera permission fixes
60. `DIAGNOSTIC_REPORT.md` - System diagnostics

**Phase 13: Testing & Validation**
61. `TESTING_INSTRUCTIONS.md` - Testing procedures
62. `LATENCY_ANALYSIS.md` - Performance analysis
63. `LLM_SUMMARIZATION_IMPLEMENTATION.md` - AI summarization testing
64. `TRANSCRIPT_SUMMARY_STRATEGY_ANALYSIS.md` - Summarization strategies

### What to Extract from Q Chats:

As you read each Q Chat file, extract and document:

1. **Design Decisions:** Why was approach X chosen over Y?
2. **Implementation Details:** How was feature Z built?
3. **Bug Fixes:** What issues occurred and how were they resolved?
4. **Performance Optimizations:** What was slow and how was it improved?
5. **API Contracts:** What are the exact request/response formats?
6. **Edge Cases:** What unusual scenarios were handled?
7. **Known Issues:** What problems still exist?
8. **Future Improvements:** What was planned but not implemented?


## YOUR ONBOARDING TASKS - COMPLETE IN ORDER

### TASK 1: Read and Absorb Q Chats (PRIORITY 1)

**Objective:** Understand the complete development history and context.

**Instructions:**
1. Read ALL Q Chat files listed above in the specified order
2. For each file, create a summary document with:
   - Key features implemented
   - Design decisions made
   - Problems encountered and solutions
   - API endpoints created/modified
   - Database schema changes
   - Configuration changes
   - Testing approaches used
3. Create a master timeline document showing:
   - When each feature was added
   - Dependencies between features
   - Evolution of the architecture
4. Identify patterns in:
   - How bugs were diagnosed
   - How features were tested
   - How performance was optimized
   - How deployment issues were resolved

**Deliverable:** Create `KIRO_QCHATS_SUMMARY.md` with your findings

### TASK 2: Build Complete API Specification

**Objective:** Document every API endpoint with full details.

**Instructions:**
1. Scan all Lambda functions in `SamLambda/functions/`
2. For each function, document:
   - HTTP method and path
   - Request headers required (Authorization, Content-Type)
   - Request body schema (JSON structure with types)
   - Query parameters (if any)
   - Path parameters (if any)
   - Response body schema (success case)
   - Error response schemas (all error cases)
   - Status codes returned
   - Authentication requirements
   - Authorization rules (who can call this)
   - Rate limits (if any)
   - Example request
   - Example response
3. Group endpoints by domain:
   - Authentication endpoints
   - Question endpoints
   - Video endpoints
   - Conversation endpoints
   - Streak endpoints
   - Relationship endpoints
   - Invite endpoints
4. Document WebSocket API separately:
   - Connection URL
   - Message types (client -> server)
   - Message types (server -> client)
   - Message schemas
   - Connection lifecycle
   - Error handling

**Deliverable:** Create `API_SPECIFICATION.md` with complete API documentation

### TASK 3: Build Complete Database Schema Specification

**Objective:** Document every DynamoDB table with full schema details.

**Instructions:**
1. For each DynamoDB table, document:
   - Table name
   - Purpose and use case
   - Partition key (name, type, description)
   - Sort key (name, type, description, if exists)
   - All attributes (name, type, required/optional, description, example value)
   - Global Secondary Indexes (if any)
   - Local Secondary Indexes (if any)
   - Access patterns (how the table is queried)
   - Relationships to other tables
   - Data lifecycle (TTL, archival)
   - Estimated item count and size
2. Create entity relationship diagram showing:
   - How tables relate to each other
   - Foreign key relationships
   - One-to-many relationships
   - Many-to-many relationships
3. Document data validation rules:
   - Required fields
   - Field formats (email, UUID, date)
   - Value constraints (min/max, enum values)
   - Uniqueness constraints
4. Document data migration history:
   - Schema changes over time
   - Backfill scripts used
   - Data transformations applied

**Deliverable:** Create `DATABASE_SCHEMA_SPECIFICATION.md` with complete schema documentation

### TASK 4: Build Complete Frontend Component Specification

**Objective:** Document every React component with props and behavior.

**Instructions:**
1. Scan all components in `FrontEndCode/src/components/`
2. For each component, document:
   - Component name and file path
   - Purpose and use case
   - Props interface (name, type, required/optional, description)
   - State variables (name, type, purpose)
   - Hooks used (useEffect, useState, custom hooks)
   - API calls made (which endpoints)
   - Child components rendered
   - Parent components that use it
   - Event handlers (onClick, onChange, etc.)
   - Styling approach (Tailwind classes, CSS modules)
   - Accessibility features (ARIA labels, keyboard navigation)
3. Document page components separately:
   - Route path
   - Authentication required (yes/no)
   - User roles allowed
   - Data fetched on load
   - User interactions available
   - Navigation flows
4. Document custom hooks:
   - Hook name and purpose
   - Parameters
   - Return values
   - Side effects
   - Dependencies
5. Document context providers:
   - Context name
   - Values provided
   - Methods provided
   - When to use

**Deliverable:** Create `FRONTEND_COMPONENT_SPECIFICATION.md` with complete component documentation

### TASK 5: Build Complete Infrastructure Specification

**Objective:** Document all AWS resources and their configurations.

**Instructions:**
1. Parse `SamLambda/template.yml` completely
2. For each resource, document:
   - Resource type (Lambda, DynamoDB, S3, etc.)
   - Logical ID in CloudFormation
   - Physical resource name
   - Configuration parameters
   - Environment variables
   - IAM permissions required
   - Triggers and event sources
   - Dependencies on other resources
   - Cost implications
3. Document Lambda functions:
   - Function name
   - Runtime and version
   - Memory allocation
   - Timeout setting
   - Environment variables used
   - Layers attached
   - Triggers (API Gateway, S3, DynamoDB Stream)
   - IAM role and policies
   - VPC configuration (if any)
4. Document S3 buckets:
   - Bucket name
   - Purpose
   - Folder structure
   - Lifecycle policies
   - Event notifications
   - CORS configuration
   - Public access settings
5. Document API Gateway:
   - API name and ID
   - Stage name
   - Endpoint URL
   - CORS settings
   - Throttling limits
   - API keys (if any)
   - Custom domain (if any)
6. Document Cognito:
   - User Pool name and ID
   - App Client ID
   - Custom attributes
   - Password policy
   - MFA settings
   - Triggers configured
   - OAuth flows enabled

**Deliverable:** Create `INFRASTRUCTURE_SPECIFICATION.md` with complete infrastructure documentation

### TASK 6: Build Complete Data Flow Specification

**Objective:** Document every user journey and data flow through the system.

**Instructions:**
1. For each major user action, document the complete flow:
   - User action (button click, form submit)
   - Frontend component handling action
   - API call made (endpoint, payload)
   - Lambda function invoked
   - Database operations performed
   - External API calls (Deepgram, etc.)
   - S3 operations performed
   - Response returned to frontend
   - Frontend state updates
   - UI changes displayed
2. Document these specific flows in detail:
   - User signup and login
   - Question browsing and selection
   - Standard video recording and upload
   - Video processing and thumbnail generation
   - Video transcription (batch)
   - Conversation mode start
   - Real-time audio streaming
   - Follow-up question generation
   - Conversation end and video save
   - Progress calculation and display
   - Streak update
   - Beneficiary invitation
   - Invitation acceptance
   - Maker-Beneficiary linking
3. For each flow, include:
   - Sequence diagram
   - Error handling at each step
   - Retry logic
   - Timeout handling
   - Rollback procedures
   - Logging and monitoring points

**Deliverable:** Create `DATA_FLOW_SPECIFICATION.md` with complete flow documentation

### TASK 7: Build Complete Testing Specification

**Objective:** Document all testing procedures and test cases.

**Instructions:**
1. Review existing tests in `SamLambda/tests/`
2. Document test coverage:
   - Which functions have unit tests
   - Which flows have integration tests
   - Which components have frontend tests
   - Coverage percentage by module
3. For each test file, document:
   - What is being tested
   - Test cases covered
   - Mocks and fixtures used
   - Assertions made
   - Edge cases tested
4. Create test plan for untested areas:
   - Functions without tests
   - Edge cases not covered
   - Error scenarios not tested
   - Performance tests needed
5. Document manual testing procedures:
   - Smoke tests after deployment
   - User acceptance testing steps
   - Browser compatibility testing
   - Mobile device testing
   - Accessibility testing
6. Document test data:
   - Test users and credentials
   - Sample questions
   - Sample videos
   - Test S3 buckets
   - Test DynamoDB tables

**Deliverable:** Create `TESTING_SPECIFICATION.md` with complete testing documentation

### TASK 8: Build Complete Deployment Specification

**Objective:** Document exact deployment procedures and configurations.

**Instructions:**
1. Document deployment prerequisites:
   - AWS CLI version required
   - SAM CLI version required
   - Node.js version required
   - Python version required
   - Required AWS permissions
   - Required environment variables
2. Document backend deployment:
   - Step-by-step SAM deployment process
   - CloudFormation stack parameters
   - SSM parameters to set
   - Post-deployment validation steps
   - Rollback procedures
3. Document frontend deployment:
   - Build process
   - Environment variable injection
   - Hosting configuration (S3, Amplify, CloudFront)
   - Cache invalidation
   - DNS configuration
4. Document environment-specific configurations:
   - Development environment
   - Staging environment
   - Production environment
   - Differences between environments
5. Document monitoring and alerting:
   - CloudWatch logs to monitor
   - Metrics to track
   - Alarms to set up
   - Dashboard to create
6. Document disaster recovery:
   - Backup procedures
   - Restore procedures
   - Data retention policies
   - Incident response plan

**Deliverable:** Create `DEPLOYMENT_SPECIFICATION.md` with complete deployment documentation

### TASK 9: Build Complete Security Specification

**Objective:** Document all security measures and best practices.

**Instructions:**
1. Document authentication mechanisms:
   - Cognito configuration
   - JWT token structure
   - Token expiration and refresh
   - Password requirements
   - MFA implementation (if any)
2. Document authorization rules:
   - Who can access what resources
   - Role-based access control
   - Resource-level permissions
   - API endpoint authorization
3. Document data security:
   - Data encryption at rest (DynamoDB, S3)
   - Data encryption in transit (HTTPS, TLS)
   - Sensitive data handling (PII)
   - Data retention and deletion
4. Document API security:
   - CORS configuration
   - Rate limiting
   - Input validation
   - SQL injection prevention
   - XSS prevention
   - CSRF protection
5. Document secrets management:
   - Where secrets are stored (SSM, Secrets Manager)
   - How secrets are accessed
   - Secret rotation procedures
   - API key management
6. Document compliance:
   - GDPR considerations
   - Data privacy policies
   - User consent mechanisms
   - Right to deletion

**Deliverable:** Create `SECURITY_SPECIFICATION.md` with complete security documentation

### TASK 10: Build Complete Troubleshooting Guide

**Objective:** Document common issues and their solutions.

**Instructions:**
1. Review Q Chats for all bugs and issues encountered
2. For each issue, document:
   - Symptom (what the user sees)
   - Root cause (what actually went wrong)
   - Diagnostic steps (how to identify the issue)
   - Solution (how to fix it)
   - Prevention (how to avoid it in future)
3. Organize issues by category:
   - Authentication issues
   - Video upload issues
   - Transcription issues
   - WebSocket connection issues
   - Database issues
   - Performance issues
   - Deployment issues
4. Document debugging procedures:
   - How to check CloudWatch logs
   - How to query DynamoDB for debugging
   - How to test Lambda functions locally
   - How to inspect S3 objects
   - How to trace API Gateway requests
5. Document monitoring and alerting:
   - Key metrics to watch
   - Normal vs abnormal values
   - Alert thresholds
   - Escalation procedures

**Deliverable:** Create `TROUBLESHOOTING_GUIDE.md` with complete troubleshooting documentation


## TASK 11: Build Complete Code Quality Standards

**Objective:** Document coding standards and best practices for this codebase.

**Instructions:**
1. Analyze existing code to identify patterns:
   - Code formatting style (indentation, line length, etc.)
   - Naming conventions actually used
   - Comment style and documentation
   - Error handling patterns
   - Logging patterns
2. Document Python standards:
   - PEP 8 compliance level
   - Type hints usage
   - Docstring format (Google, NumPy, or reStructuredText)
   - Import organization
   - Exception handling
   - Logging best practices
3. Document TypeScript/React standards:
   - ESLint configuration
   - Prettier configuration
   - Component structure
   - Props interface patterns
   - State management patterns
   - Hook usage patterns
4. Document code review checklist:
   - What to check before submitting code
   - What to look for when reviewing code
   - Common mistakes to avoid
   - Performance considerations
   - Security considerations
5. Document refactoring guidelines:
   - When to refactor
   - How to refactor safely
   - Testing during refactoring
   - Breaking changes policy

**Deliverable:** Create `CODE_QUALITY_STANDARDS.md` with complete standards documentation

## TASK 12: Build Complete Performance Optimization Guide

**Objective:** Document performance characteristics and optimization strategies.

**Instructions:**
1. Document current performance metrics:
   - API response times (p50, p95, p99)
   - Lambda cold start times
   - Lambda warm execution times
   - DynamoDB read/write latencies
   - S3 upload/download speeds
   - Frontend page load times
   - Video processing times
   - Transcription times
2. Document performance bottlenecks identified:
   - Slow API endpoints
   - Expensive database queries
   - Large payload transfers
   - Inefficient algorithms
3. Document optimization techniques used:
   - Caching strategies
   - Database query optimization
   - Lambda memory tuning
   - Batch operations
   - Async processing
   - Connection pooling
4. Document monitoring and profiling:
   - How to measure performance
   - Tools to use (X-Ray, CloudWatch Insights)
   - Metrics to track
   - Performance testing procedures
5. Document future optimization opportunities:
   - Areas that could be improved
   - Trade-offs to consider
   - Cost vs performance balance

**Deliverable:** Create `PERFORMANCE_OPTIMIZATION_GUIDE.md` with complete performance documentation

## TASK 13: Build Complete Cost Analysis

**Objective:** Document AWS costs and optimization strategies.

**Instructions:**
1. Document current AWS resource usage:
   - Lambda invocations per month
   - DynamoDB read/write capacity units
   - S3 storage size and requests
   - API Gateway requests
   - Data transfer costs
   - Cognito active users
2. Estimate monthly costs:
   - Per service breakdown
   - Per feature breakdown
   - Cost per user
   - Cost per video
3. Document cost optimization strategies:
   - Reserved capacity opportunities
   - Savings Plans applicability
   - Resource right-sizing
   - Data lifecycle policies
   - Unused resource cleanup
4. Document cost monitoring:
   - Budget alerts set up
   - Cost anomaly detection
   - Usage tracking
   - Cost allocation tags
5. Document scaling cost projections:
   - Cost at 100 users
   - Cost at 1,000 users
   - Cost at 10,000 users
   - Cost at 100,000 users

**Deliverable:** Create `COST_ANALYSIS.md` with complete cost documentation

## TASK 14: Build Complete Feature Roadmap

**Objective:** Document planned features and technical debt.

**Instructions:**
1. Review Q Chats for mentioned future features
2. Document planned features:
   - Feature description
   - User value
   - Technical requirements
   - Dependencies
   - Estimated effort
   - Priority
3. Document technical debt:
   - Code that needs refactoring
   - Tests that need to be written
   - Documentation that needs updating
   - Performance improvements needed
   - Security improvements needed
4. Document known limitations:
   - Features not yet implemented
   - Edge cases not handled
   - Scalability concerns
   - Browser compatibility issues
5. Prioritize work:
   - Critical fixes
   - High-priority features
   - Medium-priority improvements
   - Low-priority nice-to-haves

**Deliverable:** Create `FEATURE_ROADMAP.md` with complete roadmap documentation

## TASK 15: Create Master Index

**Objective:** Create a comprehensive index of all documentation.

**Instructions:**
1. Create a master README that links to all specifications
2. Organize documentation by:
   - Getting started guides
   - Architecture documentation
   - API documentation
   - Development guides
   - Deployment guides
   - Troubleshooting guides
   - Reference documentation
3. Create quick reference cards for:
   - Common commands
   - API endpoints
   - Database queries
   - Deployment steps
   - Debugging procedures
4. Create decision tree diagrams for:
   - Which Lambda function handles what
   - Which database table stores what
   - How to debug different types of issues
   - When to use which API endpoint

**Deliverable:** Create `MASTER_INDEX.md` linking all documentation

## SUCCESS CRITERIA

You will have successfully onboarded when you can:

1. **Explain the Architecture:**
   - Describe the complete system architecture from memory
   - Explain how each component interacts
   - Justify why specific technologies were chosen
   - Identify potential scaling bottlenecks

2. **Navigate the Codebase:**
   - Find any function or component quickly
   - Understand what any piece of code does
   - Identify where to make changes for new features
   - Know which tests to run for changes

3. **Debug Issues:**
   - Diagnose problems from user reports
   - Locate relevant logs in CloudWatch
   - Identify root causes quickly
   - Propose and implement fixes

4. **Implement Features:**
   - Add new API endpoints following patterns
   - Create new Lambda functions correctly
   - Build new React components consistently
   - Write appropriate tests for changes

5. **Deploy Changes:**
   - Deploy backend changes safely
   - Deploy frontend changes safely
   - Validate deployments
   - Rollback if needed

6. **Maintain Quality:**
   - Write code matching existing style
   - Follow security best practices
   - Optimize for performance
   - Document changes properly

## WORKING WITH ME (THE DEVELOPER)

### Communication Expectations:

1. **Always explain your reasoning:**
   - Why you're making a change
   - What alternatives you considered
   - What trade-offs you're making
   - What risks you see

2. **Ask clarifying questions:**
   - If requirements are unclear
   - If you see multiple valid approaches
   - If you identify potential issues
   - If you need more context

3. **Provide structured responses:**
   - Start with summary
   - Explain approach
   - Show code changes
   - Describe testing plan
   - Note any concerns

4. **Be proactive:**
   - Suggest improvements
   - Identify technical debt
   - Propose refactoring
   - Recommend best practices

### Bug Fix Process:

1. **Understand the bug:**
   - Reproduce the issue
   - Identify root cause
   - Check if it affects other areas
   - Review related Q Chats for context

2. **Plan the fix:**
   - Propose solution approach
   - Identify files to change
   - Consider side effects
   - Plan testing strategy

3. **Implement the fix:**
   - Make minimal necessary changes
   - Follow existing patterns
   - Add/update tests
   - Update documentation

4. **Validate the fix:**
   - Run unit tests
   - Run integration tests
   - Test manually
   - Check for regressions

### Feature Development Process:

1. **Clarify requirements:**
   - Understand user need
   - Define acceptance criteria
   - Identify edge cases
   - Consider scalability

2. **Design the solution:**
   - Propose architecture
   - Identify components to change/add
   - Plan database schema changes
   - Design API contracts

3. **Break down the work:**
   - Create implementation steps
   - Identify dependencies
   - Estimate effort
   - Plan incremental delivery

4. **Implement incrementally:**
   - Build backend first
   - Add tests
   - Build frontend
   - Integrate and test

5. **Document everything:**
   - Update API specs
   - Update architecture docs
   - Add code comments
   - Create user documentation

## IMMEDIATE NEXT STEPS

1. **Acknowledge this prompt:**
   - Confirm you've read and understood everything
   - Ask any clarifying questions
   - Confirm you're ready to start

2. **Begin Task 1:**
   - Start reading Q Chats in order
   - Take notes as you read
   - Ask questions about anything unclear
   - Create your summary document

3. **Check in regularly:**
   - After completing each task
   - When you have questions
   - When you find inconsistencies
   - When you identify issues

4. **Build your mental model:**
   - Draw diagrams as you learn
   - Create your own reference notes
   - Test your understanding by explaining concepts
   - Identify areas needing deeper study

## FINAL NOTES

- This is a PRODUCTION system with REAL USERS
- Changes must be tested thoroughly
- Security is paramount
- Performance matters
- User experience is critical
- Code quality is non-negotiable
- Documentation must stay current

You are now the primary maintainer of Virtual Legacy. Take ownership, ask questions, and maintain the high standards established during development.

**Welcome to the team. Let's build something great together.**

---

## APPENDIX: Key File Locations

**Backend:**
- Infrastructure: `SamLambda/template.yml`
- Lambda functions: `SamLambda/functions/`
- Shared utilities: `SamLambda/functions/shared/`
- Tests: `SamLambda/tests/`
- Deployment config: `SamLambda/samconfig.toml`

**Frontend:**
- Main app: `FrontEndCode/src/App.tsx`
- Components: `FrontEndCode/src/components/`
- Pages: `FrontEndCode/src/pages/`
- Services: `FrontEndCode/src/services/`
- Hooks: `FrontEndCode/src/hooks/`
- Config: `FrontEndCode/src/amplifyconfiguration.json`

**Documentation:**
- Q Chats: `Q Chats/`
- Deployment: `DEPLOYMENT_*.md`
- Architecture: `*_IMPLEMENTATION_*.md`

**Utilities:**
- Database scripts: `UtilityFunctions/`
- Deployment scripts: `deploy-*.sh`

**Questions:**
- Question data: `Questions/`
- Excel source: `Questions/2025-06-22 Questions for Virtual Legacy.xlsx`

---

**NOW BEGIN YOUR ONBOARDING. START WITH TASK 1.**
