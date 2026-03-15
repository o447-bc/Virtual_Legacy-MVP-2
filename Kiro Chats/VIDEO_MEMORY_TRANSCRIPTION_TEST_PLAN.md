# Video Memory Transcription - Test Plan

## Deployment Complete
✅ All Lambda functions updated and deployed successfully

## Changes Deployed

### 1. StartTranscriptionFunction
- Added GetItem permission on userQuestionStatusDB
- Handles both S3 events and direct invocations
- Detects video type from DynamoDB or explicit parameter
- Uses dynamic field names: videoMemoryTranscriptionJobName vs videoTranscriptionJobName
- Idempotency check prevents duplicate transcriptions

### 2. ProcessVideoFunction
- Added Environment variable: START_TRANSCRIPTION_FUNCTION_NAME
- Triggers transcription for video memories after DynamoDB update
- Checks allowTranscription flag before triggering
- Non-blocking error handling

### 3. ProcessTranscriptFunction
- Added GetItem permission on userQuestionStatusDB
- Detects video type by matching job name
- Uses dynamic field names based on video type
- Passes correct videoType to SummarizeTranscriptFunction

## Testing Instructions

### Prerequisites
1. Enable transcription for test user:
```bash
aws dynamodb update-item \
  --table-name userStatusDB \
  --key '{"userId": {"S": "YOUR_USER_ID"}}' \
  --update-expression "SET allowTranscription = :val" \
  --expression-attribute-values '{":val": {"BOOL": true}}'
```

### Test Case 1: Video Memory Transcription (Full Flow)

**Steps:**
1. Complete an audio conversation via UI
2. Record a video memory (post-conversation)
3. Wait 5-10 minutes for transcription to complete

**Expected Results:**
- Video memory uploaded to S3
- ProcessVideoFunction triggers StartTranscriptionFunction
- Amazon Transcribe processes video
- ProcessTranscriptFunction stores transcript
- SummarizeTranscriptFunction generates summaries

**Verification:**
```bash
# Check DynamoDB for video memory fields
aws dynamodb get-item \
  --table-name userQuestionStatusDB \
  --key '{"userId": {"S": "USER_ID"}, "questionId": {"S": "QUESTION_ID"}}' \
  --query 'Item.{
    videoMemoryS3Location: videoMemoryS3Location.S,
    videoMemoryTranscriptionJobName: videoMemoryTranscriptionJobName.S,
    videoMemoryTranscriptionStatus: videoMemoryTranscriptionStatus.S,
    videoMemoryTranscript: videoMemoryTranscript.S,
    videoMemoryTranscriptS3Location: videoMemoryTranscriptS3Location.S,
    videoMemoryOneSentence: videoMemoryOneSentence.S,
    videoMemoryDetailedSummary: videoMemoryDetailedSummary.S,
    videoMemoryThoughtfulnessScore: videoMemoryThoughtfulnessScore.N
  }'
```

**Expected Fields:**
- ✅ videoMemoryS3Location (set)
- ✅ videoMemoryTranscriptionJobName (set)
- ✅ videoMemoryTranscriptionStatus = 'COMPLETED'
- ✅ videoMemoryTranscript (if <300KB)
- ✅ videoMemoryTranscriptS3Location (set)
- ✅ videoMemoryOneSentence (set)
- ✅ videoMemoryDetailedSummary (set)
- ✅ videoMemoryThoughtfulnessScore (0-5)

**Check S3 Files:**
```bash
# List files for user
aws s3 ls s3://virtual-legacy/user-responses/USER_ID/

# Should see:
# {filename}.webm (video memory)
# {filename}.jpg (thumbnail)
# {filename}.json (transcript JSON)
# {filename}.txt (transcript text)
```

### Test Case 2: Regular Video Transcription (Verify No Regression)

**Steps:**
1. Upload a regular video via Record page
2. Wait 5-10 minutes

**Expected Results:**
- Regular video fields populated (video*, not videoMemory*)

**Verification:**
```bash
aws dynamodb get-item \
  --table-name userQuestionStatusDB \
  --key '{"userId": {"S": "USER_ID"}, "questionId": {"S": "QUESTION_ID"}}' \
  --query 'Item.{
    videoS3Location: videoS3Location.S,
    videoTranscriptionJobName: videoTranscriptionJobName.S,
    videoTranscriptionStatus: videoTranscriptionStatus.S,
    videoOneSentence: videoOneSentence.S
  }'
```

### Test Case 3: Transcription Disabled

**Steps:**
1. Set allowTranscription=false for test user
2. Record video memory

**Expected Results:**
- Video memory uploaded
- NO transcription triggered
- videoMemoryTranscriptionJobName NOT set

### Test Case 4: Idempotency

**Steps:**
1. Record video memory
2. Check CloudWatch logs for StartTranscriptionFunction
3. Should see both S3 event trigger AND direct invocation
4. Second call should skip (idempotency)

**Expected Logs:**
```
Processing S3 event: s3://virtual-legacy/user-responses/...
Detected video memory from videoMemoryS3Location
Transcription already started (videoMemoryTranscriptionJobName exists), skipping
```

## CloudWatch Logs

### StartTranscriptionFunction
```bash
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-StartTranscriptionFunction-* --since 10m --follow
```

**Look for:**
- "Processing direct invocation: videoType=video_memory"
- "Using explicit video type: video_memory"
- "Video type: video_memory, field prefix: videoMemory"
- "Transcription started: transcript-... (type: video_memory)"

### ProcessVideoFunction
```bash
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-ProcessVideoFunction-* --since 10m --follow
```

**Look for:**
- "[VIDEO MEMORY] Triggering transcription for video memory"
- "[VIDEO MEMORY] Transcription triggered successfully"

### ProcessTranscriptFunction
```bash
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-ProcessTranscriptFunction-* --since 10m --follow
```

**Look for:**
- "Detected video memory transcription"
- "Processing transcription: videoType=video_memory, prefix=videoMemory"
- "Triggered summarization for ... (videoType=video_memory)"

## Troubleshooting

### Issue: Transcription not starting
**Check:**
1. allowTranscription flag is true
2. ProcessVideoFunction logs show transcription trigger
3. StartTranscriptionFunction logs show job started

### Issue: Wrong field names used
**Check:**
1. StartTranscriptionFunction detected correct video type
2. ProcessTranscriptFunction matched correct job name
3. DynamoDB has correct prefix fields

### Issue: Summarization not working
**Check:**
1. ProcessTranscriptFunction passed correct videoType
2. SummarizeTranscriptFunction logs show video_memory type
3. DynamoDB has videoMemory* summary fields

## Success Criteria

✅ Video memory transcription works end-to-end
✅ Regular video transcription still works (no regression)
✅ Correct field names used (videoMemory* vs video*)
✅ Idempotency prevents duplicate transcriptions
✅ allowTranscription flag respected
✅ All summaries generated correctly

## Cost Impact

- Same as regular videos: $0.024/minute of video transcribed
- Only charged if allowTranscription=true
- User controls cost via flag

## Next Steps

After successful testing:
1. Update TRANSCRIPTION_IMPLEMENTATION_SUMMARY.md
2. Document video memory transcription
3. Update cost estimates
4. Consider enabling by default for new users
