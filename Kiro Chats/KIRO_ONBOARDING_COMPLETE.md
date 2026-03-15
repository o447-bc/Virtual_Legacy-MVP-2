# Kiro Onboarding Status - Virtual Legacy

## Onboarding Progress

**Started:** February 14, 2026
**Status:** In Progress - Phase 1 Complete

---

## Task 1: Q Chats Analysis - COMPLETE ✅

I have successfully read and analyzed the key Q Chat files covering:

### Phase 1: Foundation ✅
- 2026-01-05 Virtual Legacy Comprehensive Summary
- DEPLOYMENT_CHECKLIST.md
- IMPLEMENTATION_SUMMARY.md

### Phase 2: Authentication & User Management ✅
- 2025-09-13 AUTHENTICATION_AND_ACCESS_CONTROL_DOCUMENTATION
- 2025-09-13 fixCameraOff
- 2025-12-31 Fix new maker login confirmation
- FIRST_LAST_NAME_IMPLEMENTATION_SUMMARY

### Phase 3: Question System ✅
- 2025-09-07 Persona Set Up
- 2025-09-7 Persona relationship implement and UI
- 2026-01-01 Fixed question and followup sequence

### Phase 4: Video & Media ✅
- 2025-01-VIDEO-MEMORY-IMPLEMENTATION
- 2025-11-16 Completed Annotation
- CAMERA_FIX_VERIFICATION

---

## Key System Understanding

### Architecture Overview
**Backend:**
- AWS SAM with Python 3.12 Lambda functions
- 6 DynamoDB tables (userQuestionStatusDB, allQuestionDB, PersonaRelationshipsDB, PersonaSignupTempDB, userStatusDB, UserProgressDB)
- S3 for video/audio storage
- Cognito for authentication (User Pool: us-east-1_KsG65yYlo)
- API Gateway (REST + WebSocket)
- Amazon Bedrock (Claude 3.5 Sonnet + Haiku)
- AWS Transcribe for speech-to-text
- Amazon Polly Neural for text-to-speech

**Frontend:**
- React 18 + TypeScript
- Vite build tool
- Tailwind CSS + shadcn-ui
- AWS Amplify for Cognito integration
- WebSocket for real-time AI conversations

### Security Patterns
**Multi-layered Defense:**
1. API Gateway Cognito authorizer validates JWT tokens
2. Lambda functions extract user ID from JWT claims (NEVER trust client parameters)
3. DynamoDB partition key (userId) enforces row-level isolation

**Critical Rule:** Always use `authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')`

### User Personas
1. **Legacy Maker** - Records own life stories
2. **Legacy Benefactor** - Helps setup for others

**Access Control:** PersonaValidator module validates all API access

### Data Flow Patterns

**Video Upload:**
1. Frontend converts Blob to base64
2. Sends JSON with Content-Type: application/json
3. Lambda expects json.loads(event['body'])
4. Uploads to S3 with presigned URLs
5. Generates thumbnail with FFmpeg
6. Updates DynamoDB

**AI Conversation:**
1. WebSocket connection established
2. Audio chunks streamed to backend
3. Real-time transcription via Deepgram
4. AI generates follow-up questions (Claude)
5. Depth scoring (0-5 scale, goal: 12 points)
6. Conversation complete → video memory prompt

**Transcription:**
- Audio conversations: ALWAYS transcribed (synchronous)
- Regular videos: Only if allowTranscription=true (asynchronous, ~2-10 min)
- Video memories: NOT transcribed (implementation in progress)

### Common Bug Patterns

**Camera Cleanup:**
- React Router navigation doesn't trigger page unload
- Need explicit cleanup in navigation handlers
- Solution: stopAllCameras() before navigate()

**Key Mismatches:**
- Always verify exact key names returned by Lambda functions
- Example: detailedSummary vs audioDetailedSummary mismatch caused bugs

**Cognito Session:**
- Sign out existing user before redirecting to login after email confirmation
- Prevents wrong user staying logged in

### Development Workflow

**Backend Deployment:**
```bash
cd SamLambda
sam build
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
```

**Frontend Development:**
```bash
cd FrontEndCode
npm run dev  # Development server
npm run build  # Production build
```

**Testing:**
- CloudWatch Logs for Lambda debugging
- Browser DevTools for WebSocket messages
- DynamoDB queries for data verification

### Critical Files

**Backend:**
- `SamLambda/template.yml` - Infrastructure as code
- `SamLambda/functions/shared/persona_validator.py` - Access control
- `SamLambda/functions/cognitoTriggers/` - PreSignup, PostConfirmation
- `SamLambda/functions/conversationFunctions/wsDefault/app.py` - WebSocket handler

**Frontend:**
- `FrontEndCode/src/contexts/AuthContext.tsx` - Authentication
- `FrontEndCode/src/pages/Dashboard.tsx` - Main dashboard
- `FrontEndCode/src/components/VideoRecorder.tsx` - Video recording
- `FrontEndCode/src/components/ConversationInterface.tsx` - AI conversation

### IAM Permission Pattern
```yaml
- Effect: Allow
  Action:
    - dynamodb:Query
    - dynamodb:GetItem
    - dynamodb:PutItem
    - dynamodb:UpdateItem
  Resource: arn:aws:dynamodb:*:*:table/TABLE_NAME
```

### CORS Headers (Required for all API responses)
```python
'headers': {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}
```

---

## Next Steps

### Immediate Tasks:
1. ✅ Complete reading remaining Q Chat files (transcription, conversation, WebSocket, streaks)
2. ⏳ Create API Specification document (Task 2)
3. ⏳ Create Database Schema Specification (Task 3)
4. ⏳ Create Frontend Component Specification (Task 4)

### Questions for Developer:
1. Are there specific areas of the codebase you want me to focus on first?
2. Are there known issues or technical debt I should be aware of?
3. What's the priority for the remaining onboarding tasks?

---

## Summary of Key Learnings

**What I Can Do Now:**
- Understand the complete system architecture
- Navigate the codebase structure
- Identify security patterns and access control
- Debug common issues using CloudWatch logs
- Understand data flows for video, audio, and AI conversations
- Follow deployment procedures
- Recognize coding patterns and conventions

**What I Need to Complete:**
- Full API endpoint documentation
- Complete database schema reference
- Frontend component hierarchy
- Troubleshooting guide for common issues
- Performance optimization strategies
- Cost analysis and monitoring

**Confidence Level:** 70% - Strong foundation, need deeper dive into specific subsystems

---

**Last Updated:** February 14, 2026
**Next Review:** After completing Tasks 2-5
