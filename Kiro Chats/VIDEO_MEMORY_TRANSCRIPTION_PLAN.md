# Video Memory Transcription Implementation Plan - DRAFT 1

## Overview
Enable full transcription and LLM summarization for video memories using the EXACT same mechanisms as regular videos.

## Current State Analysis

### What Works (Regular Videos):
1. S3 upload triggers StartTranscriptionFunction via S3 event
2. StartTranscriptionFunction checks `allowTranscription` flag in userStatusDB
3. If enabled, starts Amazon Transcribe job
4. ProcessTranscriptFunction triggered by EventBridge when job completes
5. Transcript stored in S3 and DynamoDB (videoTranscript, videoTranscriptS3Location)
6. SummarizeTranscriptFunction called asynchronously
7. Bedrock generates: videoOneSentence, videoDetailedSummary, videoThoughtfulnessScore

### What Doesn't Work (Video Memories):
1. Video memories uploaded to S3 but NO transcription triggered
2. Fields reserved but unused: videoMemoryTranscript, videoMemoryTranscriptS3Location
3. No summaries generated: videoMemoryOneSentence, videoMemoryDetailedSummary, videoMemoryThoughtfulnessScore

## Root Cause
StartTranscriptionFunction only processes files matching pattern: `user-responses/*.webm`
Video memories use same path, so S3 event DOES trigger the function.
BUT: The function doesn't distinguish between regular videos and video memories.
Currently treats all videos the same way.

## Solution Strategy
Use the EXACT same infrastructure, just ensure video memories flow through it correctly.

---

## IMPLEMENTATION STEPS - DRAFT 1

### Phase 1: Update StartTranscriptionFunction
**Goal**: Ensure video memories trigger transcription

**Changes Needed**:
1. Function already triggered by S3 event for all .webm files
2. Already checks allowTranscription flag
3. Already starts Transcribe job
4. Already updates userQuestionStatusDB with transcriptionJobName, transcriptionStatus

**Issue**: Updates wrong fields for video memories
- Currently updates: transcriptionStatus, transcriptionJobName
- Should update: videoMemoryTranscriptionStatus, videoMemoryTranscriptionJobName (for video memories)

**Fix**: Detect if video is a video memory and use correct field names

**How to Detect Video Memory**:
- Check userQuestionStatusDB for existing record
- If record has videoMemoryS3Location matching current upload → it's a video memory
- If record has videoS3Location or no record → it's a regular video

### Phase 2: Update ProcessTranscriptFunction
**Goal**: Store transcript in correct fields based on video type

**Changes Needed**:
1. Detect video type (same logic as Phase 1)
2. If video memory:
   - Store in: videoMemoryTranscript, videoMemoryTranscriptS3Location, videoMemoryTranscriptTextS3Location
   - Update: videoMemoryTranscriptionStatus, videoMemoryTranscriptionCompleteTime
3. If regular video:
   - Store in: videoTranscript, videoTranscriptS3Location, videoTranscriptTextS3Location
   - Update: videoTranscriptionStatus, videoTranscriptionCompleteTime

### Phase 3: Update SummarizeTranscriptFunction
**Goal**: Already supports videoType parameter

**Current State**: ALREADY IMPLEMENTED
- Function accepts videoType parameter
- Dynamically sets field names based on videoType
- If videoType='video_memory': uses videoMemory* prefix
- If videoType='regular_video': uses video* prefix

**Changes Needed**: NONE - already correct

### Phase 4: Update ProcessTranscriptFunction to Pass videoType
**Goal**: Ensure SummarizeTranscriptFunction receives correct videoType

**Changes Needed**:
1. Detect video type (same logic as Phase 1 & 2)
2. Pass videoType='video_memory' or videoType='regular_video' to SummarizeTranscriptFunction

### Phase 5: Testing
**Goal**: Verify end-to-end flow

**Test Cases**:
1. Upload regular video with allowTranscription=true → verify video* fields populated
2. Upload video memory with allowTranscription=true → verify videoMemory* fields populated
3. Upload video memory with allowTranscription=false → verify no transcription
4. Check S3 for transcript files
5. Check DynamoDB for all fields

---

## CRITIQUE OF DRAFT 1

### Issues Identified:

1. **Video Type Detection Logic**: Checking userQuestionStatusDB for videoMemoryS3Location is fragile
   - What if the check happens before ProcessVideoFunction updates the record?
   - Race condition possible
   - Complex logic to match S3 keys

2. **Better Approach**: Use S3 object metadata or tags
   - ProcessVideoFunction could tag the S3 object with videoType
   - StartTranscriptionFunction reads the tag
   - More reliable, no race conditions

3. **Even Better Approach**: Check DynamoDB for videoType field
   - ProcessVideoFunction already sets videoType='video_memory' or 'regular_video'
   - StartTranscriptionFunction reads videoType from existing record
   - Simple, reliable, consistent with naming convention

4. **Timing Issue**: StartTranscriptionFunction triggered by S3 event IMMEDIATELY after upload
   - ProcessVideoFunction called by frontend AFTER upload
   - StartTranscriptionFunction might run BEFORE ProcessVideoFunction
   - videoType field might not exist yet

5. **Solution**: ProcessVideoFunction should run BEFORE transcription
   - Frontend already calls ProcessVideoFunction after upload
   - ProcessVideoFunction updates DynamoDB with videoType
   - Then StartTranscriptionFunction can read videoType reliably

6. **Problem**: S3 event triggers StartTranscriptionFunction automatically
   - Can't control timing
   - Might run before ProcessVideoFunction

7. **Better Solution**: Disable S3 event trigger for video memories
   - ProcessVideoFunction explicitly triggers transcription for video memories
   - Same pattern as audio conversations (synchronous trigger)
   - Full control over timing and parameters

8. **Issue with That**: S3 event notification can't filter by videoType (doesn't exist yet)
   - Would need to filter by S3 key pattern
   - But video memories use same path as regular videos

9. **Best Solution**: Let S3 event trigger for all videos, but add retry logic
   - StartTranscriptionFunction checks for videoType field
   - If not found, waits and retries (or skips and lets ProcessVideoFunction trigger it)
   - If found, uses videoType to determine field names

10. **Simplest Solution**: ProcessVideoFunction triggers transcription explicitly
    - For regular videos: S3 event triggers (existing behavior)
    - For video memories: ProcessVideoFunction triggers (new behavior)
    - StartTranscriptionFunction accepts videoType parameter
    - No race conditions, clean separation

---

## REVISED PLAN - DRAFT 2

### Architecture Decision
**Use explicit triggering for video memories, keep S3 event for regular videos**

### Phase 1: Update ProcessVideoFunction
**Goal**: Trigger transcription for video memories after DynamoDB update

**Changes**:
1. After updating DynamoDB with video memory fields
2. Check allowTranscription flag in userStatusDB
3. If true, invoke StartTranscriptionFunction directly with parameters:
   - userId, questionId, s3Key, videoType='video_memory'
4. StartTranscriptionFunction will handle the rest

**Why This Works**:
- ProcessVideoFunction runs AFTER upload, so timing is controlled
- videoType is known at call time
- No race conditions
- Reuses existing StartTranscriptionFunction logic

### Phase 2: Update StartTranscriptionFunction
**Goal**: Accept videoType parameter and use correct field names

**Changes**:
1. Check if event is from S3 (existing behavior) or direct invocation (new)
2. If S3 event: videoType='regular_video' (default)
3. If direct invocation: extract videoType from event
4. Use videoType to determine field names:
   - regular_video: transcriptionJobName, transcriptionStatus
   - video_memory: videoMemoryTranscriptionJobName, videoMemoryTranscriptionStatus
5. Update DynamoDB with correct fields

### Phase 3: Update ProcessTranscriptFunction
**Goal**: Detect video type and use correct field names

**Changes**:
1. Query userQuestionStatusDB to get existing record
2. Check which transcription fields are set:
   - If videoMemoryTranscriptionJobName matches job_name → video_memory
   - If transcriptionJobName matches job_name → regular_video
3. Use videoType to determine storage fields:
   - video_memory: videoMemoryTranscript, videoMemoryTranscriptS3Location, etc.
   - regular_video: videoTranscript, videoTranscriptS3Location, etc.
4. Pass videoType to SummarizeTranscriptFunction

### Phase 4: Testing Strategy
**Unit Tests**:
1. Test StartTranscriptionFunction with videoType='video_memory'
2. Test ProcessTranscriptFunction with video memory job
3. Test SummarizeTranscriptFunction with videoType='video_memory' (already works)

**Integration Tests**:
1. Upload video memory via UI
2. Verify ProcessVideoFunction triggers transcription
3. Wait for transcription to complete
4. Verify videoMemory* fields populated in DynamoDB
5. Verify transcript in S3

---

## CRITIQUE OF DRAFT 2

### Issues Identified:

1. **Complexity**: Adding direct invocation path to StartTranscriptionFunction
   - Function needs to handle two different event types
   - More complex logic
   - More error-prone

2. **Inconsistency**: Regular videos use S3 event, video memories use direct invocation
   - Different code paths
   - Harder to maintain

3. **Better Approach**: Make StartTranscriptionFunction handle both uniformly
   - Always check DynamoDB for videoType field
   - Use videoType to determine field names
   - Single code path for both

4. **Timing Issue Still Exists**: S3 event might trigger before ProcessVideoFunction
   - For regular videos, this is fine (videoType='regular_video' is default)
   - For video memories, videoType field might not exist yet
   - Need to handle missing videoType gracefully

5. **Solution**: Default behavior based on record existence
   - If no record in userQuestionStatusDB → regular_video (first upload)
   - If record exists with videoType → use that value
   - If record exists without videoType → regular_video (legacy)

6. **Issue**: Video memories ALWAYS have existing record (from audio conversation)
   - So checking for record existence works!
   - If record exists → check videoType field
   - If videoType='video_memory' → it's a video memory
   - If videoType='regular_video' or missing → it's a regular video

7. **Perfect!**: This approach works for both:
   - Regular videos: No existing record → create new with videoType='regular_video'
   - Video memories: Existing record with videoType='video_memory' → use that

8. **Remaining Issue**: ProcessVideoFunction sets videoType AFTER upload
   - S3 event triggers StartTranscriptionFunction immediately
   - Race condition still possible

9. **Solution**: ProcessVideoFunction should update videoType BEFORE returning success
   - Frontend waits for ProcessVideoFunction to complete
   - By the time S3 event triggers StartTranscriptionFunction, videoType is set
   - Actually, S3 event triggers IMMEDIATELY on upload, not after ProcessVideoFunction

10. **Real Timeline**:
    - Frontend uploads video to S3 → S3 event triggers StartTranscriptionFunction
    - Frontend calls ProcessVideoFunction → updates DynamoDB with videoType
    - StartTranscriptionFunction might run before or after ProcessVideoFunction
    - RACE CONDITION CONFIRMED

11. **Final Solution**: ProcessVideoFunction must trigger transcription explicitly
    - Disable S3 event for video memories (can't do this - same path)
    - OR: StartTranscriptionFunction checks videoType and retries if not found
    - OR: ProcessVideoFunction triggers transcription, StartTranscriptionFunction becomes idempotent

12. **Best Solution**: Make StartTranscriptionFunction idempotent and smart
    - Check if transcription already started (transcriptionJobName exists)
    - If yes, skip (idempotent)
    - If no, check videoType and start transcription
    - If videoType not found, assume regular_video (safe default)
    - ProcessVideoFunction can also trigger transcription (will be skipped if already started)

---

## FINAL PLAN - DRAFT 3

### Architecture Decision
**Make transcription system idempotent and video-type-aware**

### Key Insight
Video memories ALWAYS have an existing userQuestionStatusDB record (from audio conversation).
Regular videos usually DON'T have an existing record (first response).
Use this to distinguish video types reliably.

### Phase 1: Update StartTranscriptionFunction

**Changes**:
1. After extracting userId and questionId from S3 key
2. Query userQuestionStatusDB to check for existing record
3. Determine video type:
   ```python
   if existing_record and existing_record.get('videoMemoryS3Location'):
       video_type = 'video_memory'
       field_prefix = 'videoMemory'
   else:
       video_type = 'regular_video'
       field_prefix = 'video'
   ```
4. Check idempotency: if `{field_prefix}TranscriptionJobName` already exists, skip
5. Update DynamoDB with correct field names:
   - video_memory: videoMemoryTranscriptionJobName, videoMemoryTranscriptionStatus
   - regular_video: videoTranscriptionJobName, videoTranscriptionStatus

**Why This Works**:
- Video memories have videoMemoryS3Location set by ProcessVideoFunction
- Check is reliable: if videoMemoryS3Location exists, it's definitely a video memory
- No race condition: ProcessVideoFunction sets videoMemoryS3Location before returning
- Frontend waits for ProcessVideoFunction before showing success
- S3 event triggers after upload completes
- By then, videoMemoryS3Location is set

**Wait, Still a Race Condition**:
- S3 upload completes → S3 event triggers immediately
- Frontend calls ProcessVideoFunction → sets videoMemoryS3Location
- StartTranscriptionFunction might run before ProcessVideoFunction completes

**Solution**: Check S3 key pattern
- Video memories: user-responses/{userId}/{questionId}_*_*.webm
- Regular videos: same pattern
- Can't distinguish by S3 key alone

**Better Solution**: ProcessVideoFunction sets videoType FIRST, then uploads video
- No, video is already uploaded by frontend before ProcessVideoFunction is called

**Actual Flow**:
1. Frontend gets presigned URL
2. Frontend uploads video to S3 → S3 event triggers StartTranscriptionFunction
3. Frontend calls ProcessVideoFunction → updates DynamoDB
4. StartTranscriptionFunction runs (might be before or after step 3)

**Real Solution**: Add small delay in StartTranscriptionFunction
- Wait 2-3 seconds before checking DynamoDB
- Gives ProcessVideoFunction time to update
- Not ideal but practical

**Better Real Solution**: ProcessVideoFunction explicitly triggers transcription
- After updating DynamoDB with videoMemoryS3Location
- Check allowTranscription flag
- If true, invoke StartTranscriptionFunction with explicit parameters
- StartTranscriptionFunction checks idempotency (skip if already started by S3 event)

**This is the answer**: Dual trigger with idempotency
- S3 event triggers StartTranscriptionFunction (might run first)
- ProcessVideoFunction also triggers StartTranscriptionFunction (runs second)
- Whichever runs second will see transcriptionJobName already set and skip
- Both code paths work, no race condition issues

### Phase 2: Update ProcessVideoFunction

**Changes** (for video memories only):
1. After updating DynamoDB with videoMemoryS3Location
2. Check allowTranscription flag in userStatusDB
3. If true:
   ```python
   lambda_client.invoke(
       FunctionName='StartTranscriptionFunction',
       InvocationType='Event',
       Payload=json.dumps({
           'userId': user_id,
           'questionId': question_id,
           's3Key': s3_key,
           'videoType': 'video_memory'
       })
   )
   ```
4. StartTranscriptionFunction will check idempotency and start if needed

### Phase 3: Update StartTranscriptionFunction (Complete Logic)

**Changes**:
1. Detect event type:
   - S3 event: extract userId/questionId from S3 key
   - Direct invocation: extract from event payload
2. Query userQuestionStatusDB for existing record
3. Determine video type:
   - If event has videoType parameter: use it
   - Else if record has videoMemoryS3Location: video_type='video_memory'
   - Else: video_type='regular_video'
4. Determine field prefix:
   - video_memory → 'videoMemory'
   - regular_video → 'video'
5. Check idempotency: if `{prefix}TranscriptionJobName` exists, skip
6. Check allowTranscription flag
7. Start Transcribe job
8. Update DynamoDB with `{prefix}TranscriptionJobName` and `{prefix}TranscriptionStatus`

### Phase 4: Update ProcessTranscriptFunction

**Changes**:
1. Query userQuestionStatusDB for existing record
2. Determine video type by checking which transcription job name matches:
   ```python
   if record.get('videoMemoryTranscriptionJobName') == job_name:
       video_type = 'video_memory'
       prefix = 'videoMemory'
   elif record.get('videoTranscriptionJobName') == job_name:
       video_type = 'regular_video'
       prefix = 'video'
   else:
       # Fallback: check transcriptionJobName (legacy field)
       video_type = 'regular_video'
       prefix = 'video'
   ```
3. Store transcript with correct field names:
   - `{prefix}Transcript`
   - `{prefix}TranscriptS3Location`
   - `{prefix}TranscriptTextS3Location`
   - `{prefix}TranscriptionStatus`
   - `{prefix}TranscriptionCompleteTime`
4. Pass videoType to SummarizeTranscriptFunction

### Phase 5: Testing

**Unit Tests**:
1. Test StartTranscriptionFunction with S3 event (regular video)
2. Test StartTranscriptionFunction with direct invocation (video memory)
3. Test StartTranscriptionFunction idempotency (called twice)
4. Test ProcessTranscriptFunction with video memory job
5. Test ProcessTranscriptFunction with regular video job

**Integration Tests**:
1. Enable allowTranscription for test user
2. Complete audio conversation
3. Record video memory
4. Wait 5-10 minutes for transcription
5. Verify DynamoDB fields:
   - videoMemoryTranscriptionJobName
   - videoMemoryTranscriptionStatus='COMPLETED'
   - videoMemoryTranscript (if <300KB)
   - videoMemoryTranscriptS3Location
   - videoMemoryOneSentence
   - videoMemoryDetailedSummary
   - videoMemoryThoughtfulnessScore
6. Verify S3 files:
   - {filename}.json (Transcribe output)
   - {filename}.txt (plain text)

**Edge Cases**:
1. allowTranscription=false → no transcription
2. Video memory without prior audio conversation → should fail gracefully
3. Transcription job fails → error stored in videoMemoryTranscriptionError
4. Very long video → transcript stored in S3 only

---

## FINAL IMPLEMENTATION CHECKLIST

### Backend Changes:
- [ ] Update StartTranscriptionFunction to handle both S3 events and direct invocations
- [ ] Add video type detection logic to StartTranscriptionFunction
- [ ] Add idempotency check to StartTranscriptionFunction
- [ ] Update field names based on video type in StartTranscriptionFunction
- [ ] Update ProcessVideoFunction to trigger transcription for video memories
- [ ] Update ProcessTranscriptFunction to detect video type from job name
- [ ] Update ProcessTranscriptFunction to use correct field names based on video type
- [ ] Deploy all Lambda functions

### Testing:
- [ ] Unit test StartTranscriptionFunction with S3 event
- [ ] Unit test StartTranscriptionFunction with direct invocation
- [ ] Unit test StartTranscriptionFunction idempotency
- [ ] Unit test ProcessTranscriptFunction with video memory
- [ ] Integration test: complete audio conversation + video memory + transcription
- [ ] Verify all DynamoDB fields populated correctly
- [ ] Verify S3 transcript files created

### Documentation:
- [ ] Update TRANSCRIPTION_IMPLEMENTATION_SUMMARY.md
- [ ] Add video memory transcription section
- [ ] Document new field names
- [ ] Update cost estimates

---

## SUMMARY

**The Plan**:
1. StartTranscriptionFunction becomes video-type-aware and idempotent
2. ProcessVideoFunction explicitly triggers transcription for video memories
3. ProcessTranscriptFunction detects video type and uses correct field names
4. SummarizeTranscriptFunction already supports video memories (no changes needed)

**Why It Works**:
- Dual trigger (S3 event + explicit call) with idempotency prevents race conditions
- Video type detection based on existing DynamoDB record is reliable
- Field naming follows established convention (videoMemory* prefix)
- Reuses all existing infrastructure (Transcribe, Bedrock, S3, DynamoDB)
- Minimal code changes, maximum reuse

**Cost Impact**:
- Same as regular videos: $0.024/minute of video transcribed
- Only charged if allowTranscription=true
- User controls cost via flag

