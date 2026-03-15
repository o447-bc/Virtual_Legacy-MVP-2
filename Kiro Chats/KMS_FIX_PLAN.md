# KMS Decrypt Permissions Fix Plan

## Overview

This document outlines the systematic approach to add KMS decrypt permissions to all Lambda functions that access encrypted DynamoDB tables after Phase 1 security hardening.

## Encrypted Tables in Scope

### CloudFormation-Managed (Confirmed KMS Encrypted)
1. **PersonaRelationshipsDB** - KMS encrypted ✅
2. **EngagementDB** - KMS encrypted ✅
3. **PersonaSignupTempDB** - KMS encrypted ✅
4. **WebSocketConnectionsTable** - SSE enabled (not KMS)

### Externally-Managed (Encryption Status Unknown)
5. **userQuestionStatusDB** - Need to verify encryption
6. **userQuestionLevelProgressDB** - Need to verify encryption
7. **userStatusDB** - Need to verify encryption
8. **allQuestionDB** - Need to verify encryption

## Fix Strategy

### Approach
Add KMS decrypt permissions to ALL functions that access ANY DynamoDB table, regardless of whether we've confirmed encryption. This is a defensive approach that:
- Prevents future AccessDeniedException errors if external tables get encrypted
- Has no negative impact if tables aren't encrypted (permissions just won't be used)
- Ensures consistency across all Lambda functions

### Standard Permission Block
```yaml
- Statement:
    - Effect: Allow
      Action:
        - kms:Decrypt
        - kms:DescribeKey
      Resource: !GetAtt DataEncryptionKey.Arn
```

## Functions to Fix (Priority Order)

### Phase 1: Critical User-Facing (Deploy First)
These functions are in the critical path for user signup, relationships, and core functionality:

1. **PostConfirmationFunction** (Line ~672)
   - Accesses: PersonaSignupTempTable ✅, PersonaRelationshipsTable ✅
   - Impact: Signup flow broken

2. **CreateRelationshipFunction** (Line ~1045)
   - Accesses: PersonaRelationshipsTable ✅
   - Impact: Cannot create relationships

3. **ValidateAccessFunction** (Line ~1098)
   - Accesses: PersonaRelationshipsTable ✅
   - Impact: Access control broken

4. **PreSignupFunction** (Line ~660)
   - Accesses: PersonaSignupTempTable ✅
   - Impact: Signup flow broken

5. **SendInviteEmailFunction** (Line ~1375)
   - Accesses: PersonaSignupTempTable ✅
   - Impact: Cannot send invites

### Phase 2: Core Functionality (Deploy Second)
These functions handle questions, progress, and video processing:

6. **GetUserCompletedQuestionCountFunction** (Line ~842)
   - Accesses: userQuestionStatusDB
   - Impact: Progress tracking broken

7. **GetProgressSummary2Function** (Line ~1007)
   - Accesses: userQuestionLevelProgressDB, userStatusDB
   - Impact: Dashboard broken

8. **InitializeUserProgressFunction** (Line ~1337)
   - Accesses: userQuestionLevelProgressDB, userStatusDB
   - Impact: User onboarding broken

9. **ProcessVideoFunction** (Line ~1146)
   - Accesses: userQuestionStatusDB, userQuestionLevelProgressDB, EngagementTable ✅, userStatusDB
   - Impact: Video processing broken

10. **UploadVideoResponseFunction** (Line ~1224)
    - Accesses: userQuestionStatusDB, userQuestionLevelProgressDB, EngagementTable ✅, userStatusDB
    - Impact: Video uploads broken

11. **GetUnansweredQuestionsFromUserFunction** (Line ~896)
    - Accesses: userQuestionStatusDB
    - Impact: Cannot fetch questions

12. **GetUnansweredQuestionsWithTextFunction** (Line ~945)
    - Accesses: userQuestionStatusDB
    - Impact: Cannot fetch questions

13. **IncrementUserLevel2Function** (Line ~1437)
    - Accesses: userQuestionLevelProgressDB, userStatusDB
    - Impact: Progress tracking broken

### Phase 3: Streak & Supporting Features (Deploy Third)

14. **CheckStreakFunction** (Line ~1478)
    - Accesses: EngagementTable ✅, userStatusDB
    - Impact: Streak checking broken

15. **MonthlyResetFunction** (Line ~1541)
    - Accesses: EngagementTable ✅
    - Impact: Monthly reset broken

16. **GetProgressSummaryFunction** (Line ~975)
    - Accesses: userQuestionStatusDB
    - Impact: Legacy progress broken

17. **IncrementUserLevelFunction** (Line ~1407)
    - Accesses: userQuestionLevelProgressDB
    - Impact: Legacy progress broken

18. **GetAudioQuestionSummaryForVideoRecordingFunction** (Line ~736)
    - Accesses: userQuestionStatusDB
    - Impact: Video recording feature broken

### Phase 4: Transcription & WebSocket (Deploy Fourth)

19. **WebSocketDefaultFunction** (Line ~569)
    - Accesses: WebSocketConnectionsTable, userQuestionStatusDB, userQuestionLevelProgressDB
    - Impact: Conversation feature broken

20. **StartTranscriptionFunction** (Line ~1579)
    - Accesses: userStatusDB, userQuestionStatusDB
    - Impact: Transcription broken

21. **ProcessTranscriptFunction** (Line ~1622)
    - Accesses: userQuestionStatusDB
    - Impact: Transcription broken

22. **SummarizeTranscriptFunction** (Line ~1679)
    - Accesses: userQuestionStatusDB
    - Impact: Transcription broken

## Implementation Steps

### Step 1: Verify External Table Encryption
Before proceeding, check if external tables are encrypted:
```bash
aws dynamodb describe-table --table-name userQuestionStatusDB --query 'Table.SSEDescription'
aws dynamodb describe-table --table-name userQuestionLevelProgressDB --query 'Table.SSEDescription'
aws dynamodb describe-table --table-name userStatusDB --query 'Table.SSEDescription'
aws dynamodb describe-table --table-name allQuestionDB --query 'Table.SSEDescription'
```

### Step 2: Batch Update Functions
Update functions in phases to minimize risk:
1. Update Phase 1 functions in template.yml
2. Deploy and test critical user flows
3. Update Phase 2 functions
4. Deploy and test core functionality
5. Continue with Phases 3 and 4

### Step 3: Testing After Each Phase
- Test affected user flows
- Check CloudWatch logs for AccessDeniedException
- Monitor KMS API call metrics
- Verify no performance degradation

### Step 4: Rollback Plan
If issues occur:
1. Revert template.yml to previous version
2. Redeploy stack
3. Investigate specific function causing issues
4. Fix and redeploy

## Cost Impact

- Each KMS decrypt operation: $0.03 per 10,000 requests
- Estimated additional cost: $10-30/month for typical usage
- Can be optimized with caching if needed

## Success Criteria

- [ ] No AccessDeniedException errors in CloudWatch logs
- [ ] All user flows working correctly
- [ ] No performance degradation
- [ ] KMS API call metrics within acceptable range
- [ ] All functions can read from encrypted tables

## Next Steps

1. Run verification commands to check external table encryption
2. Start with Phase 1 critical functions
3. Deploy and test incrementally
4. Document any issues encountered
5. Update audit document with final status
