# KMS Decrypt Permissions Audit

## Executive Summary

After Phase 1 security hardening, all DynamoDB tables (PersonaRelationshipsDB, EngagementDB, PersonaSignupTempDB, and external tables like userQuestionStatusDB, userQuestionLevelProgressDB, userStatusDB) are now encrypted with KMS customer-managed keys. Lambda functions that read from these encrypted tables require `kms:Decrypt` and `kms:DescribeKey` permissions.

## Current Status

### ✅ Functions WITH KMS Decrypt Permissions (3)
1. **GetRelationshipsFunction** - Fixed ✅
2. **GetStreakFunction** - Fixed ✅  
3. **GetMakerVideosFunction** - Fixed ✅

### ⚠️ Functions MISSING KMS Decrypt Permissions

#### High Priority - Direct DynamoDB Access to Encrypted Tables

**Cognito Trigger Functions:**
1. **PreSignupFunction** - Writes to PersonaSignupTempTable (encrypted)
2. **PostConfirmationFunction** - Reads/writes PersonaSignupTempTable, writes to PersonaRelationshipsTable (both encrypted)

**Question Database Functions:**
3. **GetAudioQuestionSummaryForVideoRecordingFunction** - Reads userQuestionStatusDB
4. **GetUserCompletedQuestionCountFunction** - Queries userQuestionStatusDB
5. **GetUnansweredQuestionsFromUserFunction** - Queries userQuestionStatusDB
6. **GetUnansweredQuestionsWithTextFunction** - Queries userQuestionStatusDB
7. **GetProgressSummaryFunction** - Queries userQuestionStatusDB
8. **GetProgressSummary2Function** - Queries/writes userQuestionLevelProgressDB, writes userStatusDB
9. **InitializeUserProgressFunction** - Queries/writes userQuestionLevelProgressDB, writes userStatusDB
10. **IncrementUserLevelFunction** - Reads/writes userQuestionLevelProgressDB
11. **IncrementUserLevel2Function** - Queries/writes userQuestionLevelProgressDB, writes userStatusDB

**Relationship Functions:**
12. **CreateRelationshipFunction** - Writes to PersonaRelationshipsTable (encrypted)
13. **ValidateAccessFunction** - Reads PersonaRelationshipsTable (encrypted)

**Video Functions:**
14. **ProcessVideoFunction** - Reads/writes userQuestionStatusDB, userQuestionLevelProgressDB, EngagementTable, userStatusDB
15. **UploadVideoResponseFunction** - Writes userQuestionStatusDB, userQuestionLevelProgressDB, EngagementTable, userStatusDB
16. **StartTranscriptionFunction** - Reads/writes userStatusDB, updates userQuestionStatusDB
17. **ProcessTranscriptFunction** - Reads/updates userQuestionStatusDB
18. **SummarizeTranscriptFunction** - Reads/updates userQuestionStatusDB

**Streak Functions:**
19. **CheckStreakFunction** - Reads EngagementTable (encrypted), reads userStatusDB
20. **MonthlyResetFunction** - Scans/writes EngagementTable (encrypted)

**Invite Functions:**
21. **SendInviteEmailFunction** - Writes to PersonaSignupTempTable (encrypted)

**WebSocket Functions:**
22. **WebSocketConnectFunction** - Writes to WebSocketConnectionsTable (encrypted with SSE, not KMS)
23. **WebSocketDisconnectFunction** - Deletes from WebSocketConnectionsTable
24. **WebSocketDefaultFunction** - Reads WebSocketConnectionsTable, writes userQuestionStatusDB, userQuestionLevelProgressDB

#### Low Priority - Read-Only Access to Non-Encrypted Tables

These functions only read from `allQuestionDB` which may not be encrypted:
- GetNumQuestionTypesFunction
- GetQuestionTypeDataFunction
- GetNumValidQuestionsForQTypeFunction
- GetTotalValidAllQuestionsFunction
- GetQuestionTypesFunction
- GetQuestionByIdFunction

**Note:** Need to verify if `allQuestionDB` is encrypted. If it is, these also need KMS permissions.

## Encrypted Resources

### DynamoDB Tables (KMS Encrypted)
- PersonaRelationshipsDB ✅
- EngagementDB ✅
- PersonaSignupTempDB ✅
- userQuestionStatusDB (external, assumed encrypted)
- userQuestionLevelProgressDB (external, assumed encrypted)
- userStatusDB (external, assumed encrypted)
- WebSocketConnectionsTable (SSE enabled, not KMS)

### S3 Buckets (KMS Encrypted)
- virtual-legacy bucket with KMS encryption
- Functions accessing S3 also need KMS decrypt for S3 objects

## Recommended Fix Pattern

For each function that accesses encrypted DynamoDB tables or S3 buckets, add:

```yaml
- Statement:
    - Effect: Allow
      Action:
        - kms:Decrypt
        - kms:DescribeKey
      Resource: !GetAtt DataEncryptionKey.Arn
```

## Implementation Priority

### Phase 1 (Critical - User-Facing Features)
1. PostConfirmationFunction - Signup flow
2. CreateRelationshipFunction - Relationship creation
3. ValidateAccessFunction - Access control
4. GetUserCompletedQuestionCountFunction - Progress tracking
5. GetProgressSummary2Function - Dashboard
6. InitializeUserProgressFunction - User onboarding

### Phase 2 (High - Core Functionality)
7. ProcessVideoFunction - Video processing
8. UploadVideoResponseFunction - Video uploads
9. GetUnansweredQuestionsFromUserFunction - Question retrieval
10. GetUnansweredQuestionsWithTextFunction - Question retrieval
11. IncrementUserLevel2Function - Progress tracking
12. CheckStreakFunction - Streak tracking
13. MonthlyResetFunction - Streak reset

### Phase 3 (Medium - Supporting Features)
14. WebSocketDefaultFunction - Conversations
15. StartTranscriptionFunction - Transcription
16. ProcessTranscriptFunction - Transcription
17. SummarizeTranscriptFunction - Transcription
18. PreSignupFunction - Signup
19. SendInviteEmailFunction - Invites
20. GetAudioQuestionSummaryForVideoRecordingFunction - Video recording
21. GetProgressSummaryFunction - Legacy progress
22. IncrementUserLevelFunction - Legacy progress

## Testing Strategy

After adding KMS permissions:
1. Test each function individually
2. Monitor CloudWatch logs for AccessDeniedException errors
3. Verify no performance degradation
4. Check KMS API call metrics in CloudWatch

## Cost Impact

Each KMS decrypt operation costs $0.03 per 10,000 requests. With proper caching and efficient access patterns, the cost impact should be minimal (estimated $5-20/month for typical usage).
