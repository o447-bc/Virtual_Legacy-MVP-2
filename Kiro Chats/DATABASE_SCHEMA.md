# Virtual Legacy Database Schema Deep Dive

**Date:** February 14, 2026  
**Status:** Complete Analysis  
**Database:** Amazon DynamoDB (8 tables)

---

## Table of Contents

1. [Overview](#overview)
2. [Table Schemas](#table-schemas)
3. [Access Patterns](#access-patterns)
4. [Relationships](#relationships)
5. [Indexes & GSIs](#indexes--gsis)
6. [Best Practices](#best-practices)
7. [Anti-Patterns Found](#anti-patterns-found)

---

## Overview

The Virtual Legacy system uses 8 DynamoDB tables with a mix of single-table and multi-table design patterns. Tables are optimized for specific access patterns with strategic use of Global Secondary Indexes (GSIs) for alternate query paths.

**Design Philosophy:**
- Security-first: User ID always extracted from JWT, never trusted from client
- Graceful degradation: Non-critical operations (streaks, thumbnails) never block core functionality
- Cache-aside pattern: SSM Parameter Store for frequently accessed counts
- TTL for cleanup: Temporary data auto-expires (signup temp, WebSocket connections)

---

## Table Schemas

### 1. allQuestionDB

**Purpose:** Master repository of all questions across all categories

**Primary Key:**
- Partition Key: `questionId` (String)

**Attributes:**
```python
{
    'questionId': 'childhood-00003',        # Format: {type}-{5-digit-number}
    'questionType': 'childhood',            # Category: childhood, family, career, etc.
    'Question': 'What was your favorite...', # Question text
    'Difficulty': 1,                        # Level: 1-5
    'Valid': 1,                             # 1=active, 0=deprecated
    'friendlyName': 'Childhood Memories'    # Display name (only on {type}-00000)
}
```

**Access Patterns:**
1. Get question by ID: `get_item(questionId)`
2. Scan all questions: `scan()` (used for initialization)
3. Filter by type + difficulty: `scan()` with FilterExpression

**Size:** ~150 questions, <1 MB total

**Notes:**
- Special record `{type}-00000` stores metadata (friendlyName, description)
- Scan operations acceptable due to small dataset size
- No GSI needed (single access pattern by ID)



---

### 2. userQuestionStatusDB

**Purpose:** Track user's answered questions with video/audio metadata

**Primary Key:**
- Partition Key: `userId` (String) - Cognito sub claim
- Sort Key: `questionId` (String)

**Attributes:**
```python
{
    # Core fields
    'userId': 'f488d498-70a1-70ce-219c-879efd75a079',
    'questionId': 'childhood-00003',
    'questionType': 'childhood',
    'Question': 'What was your favorite childhood memory?',
    'timestamp': '2026-02-14T12:00:00Z',
    'status': 'completed',
    
    # Video type indicator
    'videoType': 'regular_video' | 'video_memory',
    
    # Regular video fields
    'filename': 'childhood-00003_20260214_120000_abc123.webm',
    'videoS3Location': 's3://virtual-legacy/user-responses/{userId}/video.webm',
    'videoThumbnailS3Location': 's3://virtual-legacy/user-responses/{userId}/thumb.jpg',
    
    # Video memory fields (post-conversation recording)
    'videoMemoryS3Location': 's3://virtual-legacy/user-responses/{userId}/memory.webm',
    'videoMemoryThumbnailS3Location': 's3://virtual-legacy/user-responses/{userId}/memory_thumb.jpg',
    'videoMemoryRecorded': True,
    'videoMemoryTimestamp': '2026-02-14T13:00:00Z',
    
    # Transcription fields (regular video)
    'videoTranscriptionStatus': 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED',
    'videoTranscriptionJobName': 'transcribe-job-id',
    'videoTranscript': 'Full transcript text...',
    'videoTranscriptS3Location': 's3://virtual-legacy/transcripts/...',
    'videoTranscriptTextS3Location': 's3://virtual-legacy/user-responses/{userId}/transcript.txt',
    'enableTranscript': True,
    
    # Video memory transcription fields
    'videoMemoryTranscript': 'Memory transcript...',
    'videoMemoryTranscriptS3Location': 's3://virtual-legacy/transcripts/...',
    
    # LLM summarization fields (regular video)
    'videoSummarizationStatus': 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED',
    'videoOneSentence': 'Brief one-sentence summary',
    'videoDetailedSummary': 'Detailed multi-paragraph summary',
    
    # Video memory summarization fields
    'videoMemoryOneSentence': 'Memory brief summary',
    'videoMemoryDetailedSummary': 'Memory detailed summary',
    
    # Audio conversation fields (conversation mode)
    'audioTranscript': 'Full conversation transcript...',
    'audioOneSentence': 'Conversation brief summary',
    'audioDetailedSummary': 'Conversation detailed summary',
    'audioTranscriptS3Location': 's3://virtual-legacy/conversations/{userId}/{questionId}/transcript.json'
}
```

**Access Patterns:**
1. Get user's answer for question: `get_item(userId, questionId)`
2. Get all answers for user: `query(userId)`
3. Get answers by type: `query(userId)` + filter on questionType
4. Update transcription status: `update_item(userId, questionId)`

**Size:** ~10-100 items per user, 1-10 KB per item

**Field Naming Convention:**
- Regular videos: `video*` prefix
- Video memories: `videoMemory*` prefix  
- Audio conversations: `audio*` prefix

**Notes:**
- Composite key enables efficient user-scoped queries
- No GSI needed (all queries start with userId)
- Large text fields (transcripts, summaries) stored inline (acceptable for DynamoDB)
- Status fields enable async processing tracking

---

### 3. userQuestionLevelProgressDB

**Purpose:** Track user progress by question type with level system

**Primary Key:**
- Partition Key: `userId` (String)
- Sort Key: `questionType` (String)

**Attributes:**
```python
{
    'userId': 'f488d498-70a1-70ce-219c-879efd75a079',
    'questionType': 'childhood',
    'friendlyName': 'Childhood Memories',
    
    # Level tracking
    'currentQuestLevel': 2,                 # Current difficulty level (1-5)
    'maxLevelCompleted': 1,                 # Highest level fully completed
    
    # Current level progress
    'remainQuestAtCurrLevel': [             # Unanswered question IDs at current level
        'childhood-00015',
        'childhood-00016'
    ],
    'remainQuestTextAtCurrLevel': [         # Corresponding question texts
        'What was your first day of school like?',
        'Who was your best friend growing up?'
    ],
    'totalQuestAtCurrLevel': 5,             # Total questions at current level
    
    # Overall progress
    'numQuestComplete': 8,                  # Total questions answered across all levels
    'lastUpdated': '2026-02-14T12:00:00Z'
}
```

**Access Patterns:**
1. Get user progress for type: `get_item(userId, questionType)`
2. Get all progress for user: `query(userId)`
3. Update after video upload: `update_item(userId, questionType)`
4. Initialize new user: `put_item()` for each question type

**Size:** 3-10 items per user (one per question type), 1-5 KB per item

**Notes:**
- Arrays must stay synchronized (remainQuestAtCurrLevel ↔ remainQuestTextAtCurrLevel)
- Level progression logic in incrementUserLevel2Function
- Initialized on first dashboard load if missing (getProgressSummary2)

---

### 4. userStatusDB

**Purpose:** User profile and global settings

**Primary Key:**
- Partition Key: `userId` (String)

**Attributes:**
```python
{
    'userId': 'f488d498-70a1-70ce-219c-879efd75a079',
    'currLevel': 2,                         # Global max level across all types
    'timezone': 'America/New_York',         # User's timezone for streak calculations
    'personaType': 'legacy_maker',          # legacy_maker | legacy_benefactor
    'allowTranscription': True,             # Enable video transcription
    'createdAt': '2026-01-01T00:00:00Z',
    'lastActive': '2026-02-14T12:00:00Z'
}
```

**Access Patterns:**
1. Get user profile: `get_item(userId)`
2. Update timezone: `update_item(userId)`
3. Update global level: `update_item(userId)`

**Size:** 1 item per user, <1 KB per item

**Notes:**
- `currLevel` synced with max(currentQuestLevel) from userQuestionLevelProgressDB
- Auto-sync logic in getProgressSummary2Function
- Timezone critical for accurate streak calculations

---

### 5. PersonaRelationshipsDB

**Purpose:** Link legacy benefactors to legacy makers

**Primary Key:**
- Partition Key: `initiator_id` (String) - Benefactor's user ID
- Sort Key: `related_user_id` (String) - Maker's user ID

**Global Secondary Index:**
- **RelatedUserIndex**
  - Partition Key: `related_user_id`
  - Projection: ALL

**Attributes:**
```python
{
    'initiator_id': 'benefactor-user-id',
    'related_user_id': 'maker-user-id',
    'relationshipType': 'benefactor_to_maker',
    'createdAt': '2026-02-14T12:00:00Z',
    'status': 'active',                     # active | inactive
    'inviteToken': 'uuid-v4',               # Optional: invite token used
    'paymentId': 'stripe-payment-id'        # Optional: payment reference
}
```

**Access Patterns:**
1. Get maker's benefactors: `query(initiator_id)` on main table
2. Get benefactor's makers: `query(related_user_id)` on RelatedUserIndex
3. Validate access: Check if relationship exists between two users
4. Create relationship: `put_item()`

**Size:** 1-10 items per benefactor, <1 KB per item

**GSI Usage:**
- **RelatedUserIndex** enables bidirectional queries
- Allows makers to see who their benefactors are
- Enables access validation from either direction

**Notes:**
- Composite key prevents duplicate relationships
- GSI projects ALL attributes (no additional queries needed)
- Used by validateAccessFunction for content access control

---

### 6. PersonaSignupTempDB

**Purpose:** Temporary storage during signup process

**Primary Key:**
- Partition Key: `userName` (String) - Cognito username

**TTL Attribute:** `ttl` (Number) - Unix timestamp

**Attributes:**
```python
{
    'userName': 'user@example.com',
    'personaType': 'legacy_maker',
    'initiatorId': 'benefactor-user-id',    # Optional: if invited
    'relatedUserId': '',                    # Optional: relationship target
    'ttl': 1708012800,                      # Expires in 1 hour
    'createdAt': '2026-02-14T12:00:00Z'
}
```

**Access Patterns:**
1. Store signup data: `put_item()` in PreSignupFunction
2. Retrieve on confirmation: `get_item()` in PostConfirmationFunction
3. Delete after use: `delete_item()` in PostConfirmationFunction
4. Auto-cleanup: TTL deletes expired items

**Size:** Transient, typically <100 items, <1 KB per item

**TTL Configuration:**
- Enabled on `ttl` attribute
- Items expire 1 hour after creation
- Automatic cleanup by DynamoDB

**Notes:**
- Bridges Cognito PreSignup and PostConfirmation triggers
- Prevents race conditions in multi-step signup
- TTL ensures no orphaned data if signup fails

---

### 7. EngagementDB (UserProgressDB)

**Purpose:** Daily streak tracking for user engagement

**Primary Key:**
- Partition Key: `userId` (String)

**Attributes:**
```python
{
    'userId': 'f488d498-70a1-70ce-219c-879efd75a079',
    'streakCount': 5,                       # Current consecutive days
    'longestStreak': 10,                    # All-time record
    'lastVideoDate': '2026-02-14',          # YYYY-MM-DD format
    'streakFreezeAvailable': True,          # Can skip one day
    'freezeUsedThisMonth': False,           # Monthly reset flag
    'createdAt': '2026-01-01T00:00:00Z',
    'lastUpdated': '2026-02-14T12:00:00Z'
}
```

**Access Patterns:**
1. Get streak data: `get_item(userId)`
2. Update after video upload: `update_item(userId)`
3. Monthly reset: `scan()` + batch update (MonthlyResetFunction)

**Size:** 1 item per user, <1 KB per item

**Streak Business Rules:**
- Same day upload: Streak unchanged
- Consecutive day: Streak +1
- Missed day with freeze: Streak maintained, freeze consumed
- Missed day without freeze: Streak resets to 1
- Monthly reset: Freeze availability resets on 1st of month

**Notes:**
- Non-blocking: Video upload succeeds even if streak update fails
- Timezone-aware: Uses user's timezone from userStatusDB
- Milestones logged to CloudWatch at 7, 30, 100 days

---

### 8. WebSocketConnectionsDB

**Purpose:** Track active WebSocket connections for conversation mode

**Primary Key:**
- Partition Key: `connectionId` (String) - API Gateway connection ID

**TTL Attribute:** `ttl` (Number) - Unix timestamp

**Attributes:**
```python
{
    'connectionId': 'abc123xyz',            # API Gateway connection ID
    'userId': 'f488d498-70a1-70ce-219c-879efd75a079',
    'questionId': 'childhood-00003',
    'questionType': 'childhood',
    'connectedAt': '2026-02-14T12:00:00Z',
    'ttl': 1708020000,                      # Expires in 2 hours
    'conversationState': {                  # Optional: conversation metadata
        'turnNumber': 3,
        'cumulativeScore': 7.5,
        'scoreGoal': 12
    }
}
```

**Access Patterns:**
1. Store connection: `put_item()` on $connect
2. Get connection: `get_item(connectionId)`
3. Delete connection: `delete_item()` on $disconnect
4. Auto-cleanup: TTL deletes stale connections

**Size:** Transient, typically <50 active connections, <1 KB per item

**TTL Configuration:**
- Enabled on `ttl` attribute
- Connections expire 2 hours after creation
- Handles ungraceful disconnects

**Notes:**
- Used by WebSocketDefaultFunction to validate messages
- Prevents unauthorized access to conversations
- TTL ensures cleanup of abandoned connections

---


## Access Patterns

### Pattern 1: User Dashboard Load

**Flow:**
1. GET /progress-summary-2?userId={userId}
2. Query userQuestionLevelProgressDB by userId
3. If empty, initialize from allQuestionDB scan
4. Sync userStatusDB.currLevel with max level
5. Return progress data

**Tables Accessed:**
- userQuestionLevelProgressDB (Query)
- userStatusDB (GetItem, PutItem)
- allQuestionDB (Scan - only on first load)

**Optimization:**
- Progress data cached in frontend
- Initialization only happens once per user
- Scan acceptable due to small allQuestionDB size

---

### Pattern 2: Video Upload

**Flow:**
1. POST /get-upload-url → Get S3 presigned URL
2. PUT to S3 → Upload video directly
3. POST /process-video → Trigger processing
4. Generate thumbnail (FFmpeg)
5. Update userQuestionStatusDB (PutItem)
6. Update userQuestionLevelProgressDB (GetItem, PutItem)
7. Update EngagementDB for streak (GetItem, PutItem)
8. Invalidate SSM cache (/virtuallegacy/user_completed_count/{userId})
9. Trigger transcription (async)

**Tables Accessed:**
- userQuestionStatusDB (PutItem)
- userQuestionLevelProgressDB (GetItem, PutItem)
- userStatusDB (GetItem - for timezone)
- EngagementDB (GetItem, PutItem)

**Optimization:**
- S3 presigned URL bypasses API Gateway 10MB limit
- Thumbnail generation non-blocking
- Streak update non-blocking
- Transcription async via EventBridge

---

### Pattern 3: Get Unanswered Questions

**Flow:**
1. GET /unanswered?questionType=childhood
2. Scan allQuestionDB with filter (questionType, Difficulty, Valid)
3. Query userQuestionStatusDB by userId
4. Filter out answered questions
5. Return unanswered list

**Tables Accessed:**
- allQuestionDB (Scan with FilterExpression)
- userQuestionStatusDB (Query)

**Optimization:**
- Could add GSI on allQuestionDB (questionType, Difficulty) to avoid scan
- Current scan acceptable due to small dataset (<150 items)
- Frontend caches unanswered questions

---

### Pattern 4: Relationship Validation

**Flow:**
1. GET /relationships/validate?targetUserId={makerId}
2. Query PersonaRelationshipsDB by initiator_id (benefactor)
3. If not found, query RelatedUserIndex by related_user_id (maker)
4. Return hasAccess boolean

**Tables Accessed:**
- PersonaRelationshipsDB (Query on main table)
- PersonaRelationshipsDB (Query on RelatedUserIndex GSI)

**Optimization:**
- GSI enables bidirectional lookup
- Single query per direction (efficient)
- Result cached in frontend for session

---

### Pattern 5: Conversation Mode

**Flow:**
1. WebSocket $connect → Store in WebSocketConnectionsDB
2. Client sends audio_response
3. Query WebSocketConnectionsDB to validate connection
4. Upload audio to S3
5. Transcribe with AWS Transcribe
6. Score with Bedrock Claude Haiku
7. Generate response with Bedrock Claude Sonnet
8. Synthesize speech with Polly
9. Send ai_speaking message
10. Update userQuestionStatusDB on completion
11. WebSocket $disconnect → Delete from WebSocketConnectionsDB

**Tables Accessed:**
- WebSocketConnectionsDB (PutItem, GetItem, DeleteItem)
- userQuestionStatusDB (PutItem on completion)
- userQuestionLevelProgressDB (PutItem on completion)

**Optimization:**
- Connection validation cached in Lambda memory
- Async processing (transcribe, LLM, TTS) in parallel where possible
- TTL auto-cleanup of stale connections

---

### Pattern 6: Streak Calculation

**Flow:**
1. Video upload triggers update_user_streak()
2. Get user timezone from userStatusDB
3. Get current streak from EngagementDB
4. Calculate days since last video
5. Apply business rules (consecutive, freeze, reset)
6. Update EngagementDB with new streak
7. Log milestone to CloudWatch if reached

**Tables Accessed:**
- userStatusDB (GetItem - for timezone)
- EngagementDB (GetItem, PutItem)

**Optimization:**
- Non-blocking: Video upload succeeds regardless
- Timezone-aware date calculations
- CloudWatch metrics for analytics

---

## Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│  allQuestionDB  │
│  (Master Data)  │
└────────┬────────┘
         │
         │ Referenced by
         │
         ▼
┌──────────────────────────┐
│ userQuestionStatusDB     │◄──────┐
│ (User Answers)           │       │
└──────────┬───────────────┘       │
           │                       │
           │ Updates               │ References
           │                       │
           ▼                       │
┌──────────────────────────┐      │
│userQuestionLevelProgressDB│      │
│ (Progress Tracking)      │      │
└──────────┬───────────────┘      │
           │                       │
           │ Syncs with            │
           │                       │
           ▼                       │
┌──────────────────────────┐      │
│    userStatusDB          │──────┘
│  (User Profile)          │
└──────────┬───────────────┘
           │
           │ Provides timezone
           │
           ▼
┌──────────────────────────┐
│    EngagementDB          │
│  (Streak Tracking)       │
└──────────────────────────┘

┌──────────────────────────┐
│PersonaRelationshipsDB    │
│ (Benefactor ↔ Maker)     │
└──────────┬───────────────┘
           │
           │ Temporary storage
           │
           ▼
┌──────────────────────────┐
│PersonaSignupTempDB       │
│ (TTL: 1 hour)            │
└──────────────────────────┘

┌──────────────────────────┐
│WebSocketConnectionsDB    │
│ (Active Connections)     │
│ (TTL: 2 hours)           │
└──────────────────────────┘
```

### Relationship Types

**1. One-to-Many:**
- User → Questions Answered (userQuestionStatusDB)
- User → Progress Records (userQuestionLevelProgressDB)
- User → Streak Record (EngagementDB)

**2. Many-to-Many:**
- Benefactors ↔ Makers (PersonaRelationshipsDB with GSI)

**3. Reference:**
- userQuestionStatusDB.questionId → allQuestionDB.questionId
- userQuestionLevelProgressDB.questionType → allQuestionDB.questionType

**4. Synchronization:**
- userStatusDB.currLevel ↔ max(userQuestionLevelProgressDB.currentQuestLevel)

---

## Indexes & GSIs

### Global Secondary Indexes

**PersonaRelationshipsDB - RelatedUserIndex:**
- **Purpose:** Enable bidirectional relationship queries
- **Keys:** related_user_id (PK)
- **Projection:** ALL
- **Use Case:** Find all benefactors for a maker
- **Cost:** Doubles write costs, but essential for access validation

### Why No Other GSIs?

**allQuestionDB:**
- Small dataset (<150 items)
- Scan operations acceptable
- Single access pattern (by questionId)

**userQuestionStatusDB:**
- All queries start with userId (partition key)
- Sort key (questionId) provides efficient range queries
- No alternate access patterns needed

**userQuestionLevelProgressDB:**
- All queries start with userId
- Question type filtering done in application layer
- Small result sets (3-10 items per user)

**userStatusDB:**
- Single item per user
- Only accessed by userId
- No alternate queries needed

**EngagementDB:**
- Single item per user
- Only accessed by userId
- Monthly scan acceptable (once per month)

**WebSocketConnectionsDB:**
- Only accessed by connectionId
- Short-lived data (TTL: 2 hours)
- No alternate access patterns

---

## Best Practices

### 1. Security Pattern: JWT User ID Extraction

**Always extract user ID from JWT, never trust client:**
```python
# ✅ CORRECT
authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')

# ❌ WRONG - Never trust client-provided userId
user_id = json.loads(event['body']).get('userId')  # Security vulnerability!
```

**Why:** Prevents users from accessing other users' data by manipulating request parameters.

---

### 2. Graceful Degradation

**Non-critical operations never block core functionality:**
```python
# Thumbnail generation
try:
    thumbnail_filename = generate_thumbnail(s3_key, user_id)
except Exception as e:
    print(f"Thumbnail failed (non-critical): {e}")
    # Video upload still succeeds

# Streak update
try:
    streak_data = update_user_streak(user_id)
except Exception as e:
    print(f"Streak update failed (non-critical): {e}")
    # Video upload still succeeds
```

**Why:** Ensures core features (video upload) always work, even if auxiliary features fail.

---

### 3. Cache-Aside Pattern

**Use SSM Parameter Store for frequently accessed counts:**
```python
# Check cache first
try:
    cache = ssm_client.get_parameter(Name=f'/virtuallegacy/user_completed_count/{user_id}')
    return json.loads(cache['Parameter']['Value'])['count']
except ParameterNotFound:
    # Cache miss - query database
    count = query_database(user_id)
    # Store in cache (24 hour TTL)
    ssm_client.put_parameter(
        Name=f'/virtuallegacy/user_completed_count/{user_id}',
        Value=json.dumps({'count': count, 'timestamp': now}),
        Type='String',
        Overwrite=True
    )
    return count
```

**Invalidation:**
```python
# After video upload
try:
    ssm_client.delete_parameter(Name=f'/virtuallegacy/user_completed_count/{user_id}')
except ParameterNotFound:
    pass  # Cache doesn't exist, that's fine
```

**Why:** Reduces DynamoDB read costs, improves response time, simple invalidation strategy.

---

### 4. TTL for Automatic Cleanup

**Use TTL for temporary data:**
```python
# PersonaSignupTempDB - expires in 1 hour
{
    'userName': 'user@example.com',
    'ttl': int(time.time()) + 3600  # Unix timestamp
}

# WebSocketConnectionsDB - expires in 2 hours
{
    'connectionId': 'abc123',
    'ttl': int(time.time()) + 7200
}
```

**Why:** Prevents orphaned data, no manual cleanup needed, cost-effective.

---

### 5. Composite Keys for Efficient Queries

**Use userId as partition key for user-scoped data:**
```python
# userQuestionStatusDB
Primary Key: userId (PK) + questionId (SK)

# Query all answers for user (efficient)
table.query(KeyConditionExpression='userId = :uid')

# Get specific answer (efficient)
table.get_item(Key={'userId': uid, 'questionId': qid})
```

**Why:** Enables efficient user-scoped queries without scanning entire table.

---

### 6. Array Synchronization

**Keep parallel arrays in sync:**
```python
# userQuestionLevelProgressDB
{
    'remainQuestAtCurrLevel': ['q1', 'q2', 'q3'],
    'remainQuestTextAtCurrLevel': ['Text 1', 'Text 2', 'Text 3']
}

# When removing question
if question_id in remain_ids:
    idx = remain_ids.index(question_id)
    remain_ids.remove(question_id)
    if idx < len(remain_texts):
        remain_texts.pop(idx)  # Remove at same index
```

**Why:** Prevents data inconsistency, maintains array correspondence.

---

### 7. Status Tracking for Async Operations

**Use status fields to track async processing:**
```python
{
    'videoTranscriptionStatus': 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED',
    'videoSummarizationStatus': 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
}
```

**Why:** Enables retry logic, prevents duplicate processing, provides visibility.

---

## Anti-Patterns Found

### 1. ❌ Scan Operations on Large Tables

**Current:** allQuestionDB uses scan for filtering
```python
# Inefficient for large datasets
response = table.scan(
    FilterExpression='questionType = :type AND Difficulty = :diff'
)
```

**Better:** Add GSI on (questionType, Difficulty)
```yaml
GlobalSecondaryIndexes:
  - IndexName: TypeDifficultyIndex
    KeySchema:
      - AttributeName: questionType
        KeyType: HASH
      - AttributeName: Difficulty
        KeyType: RANGE
```

**Impact:** Currently acceptable (150 items), but will become inefficient at scale.

---

### 2. ❌ Synchronization Between Tables

**Current:** userStatusDB.currLevel synced with userQuestionLevelProgressDB
```python
# Auto-sync in getProgressSummary2
levels = [item.get('currentQuestLevel') for item in progress_items]
max_level = max(levels)
if status['currLevel'] != max_level:
    user_status_table.put_item({'userId': uid, 'currLevel': max_level})
```

**Better:** Single source of truth - calculate max level on-demand
```python
# Remove currLevel from userStatusDB
# Calculate max level when needed
max_level = max(item.get('currentQuestLevel') for item in progress_items)
```

**Impact:** Potential data inconsistency, extra write operations.

---

### 3. ❌ Large Arrays in Items

**Current:** remainQuestAtCurrLevel can grow large
```python
{
    'remainQuestAtCurrLevel': ['q1', 'q2', ..., 'q50'],  # Could be 50+ items
    'remainQuestTextAtCurrLevel': ['Text 1', 'Text 2', ..., 'Text 50']
}
```

**Better:** Store only IDs, fetch texts on-demand
```python
{
    'remainQuestAtCurrLevel': ['q1', 'q2', ..., 'q50']
}
# Fetch texts from allQuestionDB when needed
```

**Impact:** Larger item sizes, higher read/write costs, 400KB item limit risk.

---

### 4. ❌ Client-Provided User IDs (Security Risk)

**Found in some functions:**
```python
# ❌ WRONG - Trusts client parameter
thisUserId = event['queryStringParameters'].get('userId')
# Then uses thisUserId for queries
```

**Correct pattern:**
```python
# ✅ CORRECT - Always use JWT
authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
# Ignore client-provided userId parameter
```

**Impact:** Critical security vulnerability - users could access other users' data.

---

### 5. ⚠️ No Conditional Writes

**Current:** No conditional expressions on updates
```python
# Could cause race conditions
table.put_item(Item={'userId': uid, 'streakCount': new_count})
```

**Better:** Use conditional expressions for critical updates
```python
table.update_item(
    Key={'userId': uid},
    UpdateExpression='SET streakCount = :new',
    ConditionExpression='streakCount = :old',  # Prevent race conditions
    ExpressionAttributeValues={':new': new_count, ':old': old_count}
)
```

**Impact:** Potential data corruption in high-concurrency scenarios (currently low risk).

---

## Summary

**Strengths:**
- ✅ Security-first design (JWT user ID extraction)
- ✅ Graceful degradation (non-blocking operations)
- ✅ Efficient cache strategy (SSM Parameter Store)
- ✅ TTL for automatic cleanup
- ✅ Composite keys for efficient queries
- ✅ GSI for bidirectional relationships

**Areas for Improvement:**
- Add GSI to allQuestionDB for efficient filtering
- Remove currLevel synchronization (single source of truth)
- Reduce array sizes in userQuestionLevelProgressDB
- Add conditional writes for critical updates
- Audit all functions for client-provided user ID usage

**Overall Assessment:** Well-designed schema with good security practices and efficient access patterns. Minor optimizations recommended for scale.

---

**Last Updated:** February 14, 2026  
**Status:** Complete database schema analysis
