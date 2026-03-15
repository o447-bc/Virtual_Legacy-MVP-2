# Video Transcription Implementation Summary

## Overview
Asynchronous video transcription system using Amazon Transcribe, triggered automatically when videos are uploaded to S3. Transcription is controlled by a per-user flag in DynamoDB.

## Architecture

```
Video Upload → S3 (user-responses/) → S3 Event → StartTranscription Lambda
                                                         ↓
                                                   Check allowTranscription flag
                                                         ↓
                                        [If false] → Skip (emit metric)
                                        [If true]  → Start Transcribe Job
                                                         ↓
                                                   Amazon Transcribe
                                                         ↓
                                                   EventBridge Event
                                                         ↓
                                              ProcessTranscript Lambda
                                                         ↓
                                              Store in DynamoDB/S3
```

## Components Created

### 1. IAM Role: TranscribeServiceRole
- **ARN:** `arn:aws:iam::962214556635:role/TranscribeServiceRole`
- **Purpose:** Allows Amazon Transcribe to access S3 buckets
- **Permissions:**
  - Read videos from `s3://virtual-legacy/user-responses/*`
  - Write transcripts to `s3://virtual-legacy/user-responses/*`

### 2. Lambda: StartTranscriptionFunction
- **Trigger:** S3 ObjectCreated events on `user-responses/*.webm`
- **Function:**
  1. Parse S3 key to extract userId and questionId
  2. Check `allowTranscription` flag in userStatusDB
  3. If false: Skip transcription, emit CloudWatch metric
  4. If true: Start Transcribe job, update userQuestionStatusDB
- **Metrics Emitted:**
  - `VirtualLegacy/Transcription/TranscriptionAllowed`
  - `VirtualLegacy/Transcription/TranscriptionDenied`
  - `VirtualLegacy/Transcription/TranscriptionError`

### 3. Lambda: ProcessTranscriptFunction
- **Trigger:** EventBridge rule on Transcribe job completion
- **Function:**
  1. Parse job name to extract userId and questionId
  2. Download transcript from S3
  3. If transcript <300KB: Store in DynamoDB
  4. If transcript ≥300KB: Store S3 location reference only
  5. Update userQuestionStatusDB with results

### 4. S3 Event Notification
- **Bucket:** virtual-legacy
- **Event:** s3:ObjectCreated:*
- **Prefix:** user-responses/
- **Suffix:** .webm
- **Target:** StartTranscriptionFunction

### 5. EventBridge Rule
- **Pattern:** Transcribe Job State Change (COMPLETED or FAILED)
- **Target:** ProcessTranscriptFunction

## File Storage Structure

### Videos and Related Files
```
s3://virtual-legacy/user-responses/{userId}/
├── childhood-00001_20250105_123456_a3f2.webm    (video)
├── childhood-00001_20250105_123456_a3f2.jpg     (thumbnail)
└── childhood-00001_20250105_123456_a3f2.json    (transcript)
```

**Note:** Transcripts use the same base filename as videos, just with .json extension instead of .webm

## Database Schema Changes

### userStatusDB
**New Attribute:**
- `allowTranscription` (Boolean, default: false)
  - Controls whether transcription is enabled for the user
  - Created automatically during user initialization

### userQuestionStatusDB
**New Attributes:**
- `transcriptionStatus` (String): 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
- `transcriptionJobName` (String): Transcribe job identifier
- `transcriptionStartTime` (String): ISO timestamp when job started
- `transcriptionCompleteTime` (String): ISO timestamp when job completed
- `transcript` (String): Full transcript text (if <300KB)
- `transcriptS3Location` (String): S3 URI to transcript JSON (always stored)
- `transcriptionError` (String): Error message if job failed

## Default Behavior

### For New Users
- `allowTranscription` is set to **false** by default
- Videos are uploaded normally
- Transcription is **skipped** (not started)
- No Transcribe costs incurred

### When allowTranscription = true
- Videos trigger transcription automatically
- Transcripts stored alongside videos in S3
- Transcript text stored in DynamoDB (if small enough)
- Costs: $0.024 per minute of video transcribed

## How to Enable Transcription for a User

### Option 1: AWS Console (Manual)
1. Go to DynamoDB → userStatusDB table
2. Find the user's record (userId as partition key)
3. Edit item → Set `allowTranscription` to `true`
4. Save

### Option 2: AWS CLI
```bash
aws dynamodb update-item \
  --table-name userStatusDB \
  --key '{"userId": {"S": "USER_ID_HERE"}}' \
  --update-expression "SET allowTranscription = :val" \
  --expression-attribute-values '{":val": {"BOOL": true}}'
```

### Option 3: Python Script
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('userStatusDB')

table.update_item(
    Key={'userId': 'USER_ID_HERE'},
    UpdateExpression='SET allowTranscription = :val',
    ExpressionAttributeValues={':val': True}
)
```

## How to Access Transcripts

### From DynamoDB
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('userQuestionStatusDB')

response = table.get_item(
    Key={
        'userId': 'USER_ID_HERE',
        'questionId': 'childhood-00001'
    }
)

item = response['Item']
status = item.get('transcriptionStatus')  # COMPLETED, IN_PROGRESS, FAILED, NOT_STARTED
transcript = item.get('transcript')  # Text if <300KB
s3_location = item.get('transcriptS3Location')  # S3 URI (always present if transcribed)
```

### From S3 (Direct Access)
```bash
# List transcripts for a user
aws s3 ls s3://virtual-legacy/user-responses/USER_ID_HERE/ --recursive | grep .json

# Download a specific transcript
aws s3 cp s3://virtual-legacy/user-responses/USER_ID_HERE/childhood-00001_20250105_123456_a3f2.json ./
```

### Transcript JSON Format (from Transcribe)
```json
{
  "jobName": "transcript-abc123-childhood-00001-20250105-a3f2",
  "accountId": "962214556635",
  "results": {
    "transcripts": [
      {
        "transcript": "Hello, my name is John and I grew up in..."
      }
    ],
    "items": [
      {
        "start_time": "0.0",
        "end_time": "0.5",
        "alternatives": [{"confidence": "0.99", "content": "Hello"}],
        "type": "pronunciation"
      }
      // ... more items
    ]
  },
  "status": "COMPLETED"
}
```

## Monitoring

### CloudWatch Metrics
- **Namespace:** VirtualLegacy/Transcription
- **Metrics:**
  - `TranscriptionAllowed`: Count of transcriptions started
  - `TranscriptionDenied`: Count of transcriptions skipped (flag=false)
  - `TranscriptionError`: Count of errors during processing

### CloudWatch Logs
- **StartTranscription:** `/aws/lambda/Virtual-Legacy-MVP-1-StartTranscriptionFunction-*`
- **ProcessTranscript:** `/aws/lambda/Virtual-Legacy-MVP-1-ProcessTranscriptFunction-*`

### View Recent Logs
```bash
# StartTranscription logs
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-StartTranscriptionFunction-DpLW9VdSjugb --since 1h --follow

# ProcessTranscript logs
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-ProcessTranscriptFunction-* --since 1h --follow
```

## Cost Estimates

### Amazon Transcribe
- **Standard:** $0.024 per minute
- **Example:** 100 videos/month × 3 min average = $7.20/month

### Lambda
- **Execution:** Negligible (free tier covers most usage)
- **StartTranscription:** ~100ms per invocation
- **ProcessTranscript:** ~500ms per invocation

### S3 Storage
- **Transcripts:** ~$0.023/GB/month
- **Example:** 100 transcripts × 50KB average = 5MB = $0.0001/month

### Total Estimated Cost
- **With 30% adoption:** ~$2.16/month (30 videos transcribed)
- **With 100% adoption:** ~$7.20/month (100 videos transcribed)

## Testing

### Test with Flag Disabled (Default)
1. Upload a video via the UI
2. Check CloudWatch Logs for StartTranscriptionFunction
3. Should see: "Transcription not allowed for user {userId}"
4. Check CloudWatch Metrics: TranscriptionDenied should increment
5. No Transcribe job created

### Test with Flag Enabled
1. Enable flag for test user (see "How to Enable" above)
2. Upload a video via the UI
3. Check CloudWatch Logs for StartTranscriptionFunction
4. Should see: "Started Transcribe job: transcript-..."
5. Check AWS Console → Transcribe → Jobs (should see IN_PROGRESS)
6. Wait 2-5 minutes for completion
7. Check CloudWatch Logs for ProcessTranscriptFunction
8. Should see: "Transcript stored successfully"
9. Check DynamoDB userQuestionStatusDB for transcript data
10. Check S3 for transcript JSON file alongside video

### Verify Transcript Location
```bash
# List files for a user
aws s3 ls s3://virtual-legacy/user-responses/USER_ID_HERE/

# Should see:
# childhood-00001_20250105_123456_a3f2.webm
# childhood-00001_20250105_123456_a3f2.jpg
# childhood-00001_20250105_123456_a3f2.json  <-- transcript
```

## Troubleshooting

### Transcription Not Starting
1. Check S3 event notification is configured: `aws s3api get-bucket-notification-configuration --bucket virtual-legacy`
2. Check Lambda has permission: `aws lambda get-policy --function-name Virtual-Legacy-MVP-1-StartTranscriptionFunction-*`
3. Check CloudWatch Logs for errors
4. Verify flag is true: Query userStatusDB for the user

### Transcription Job Fails
1. Check Transcribe console for error message
2. Common issues:
   - Invalid video format (must be webm with supported codec)
   - Video file corrupted
   - S3 permissions issue
3. Check ProcessTranscript logs for error details
4. Error stored in userQuestionStatusDB `transcriptionError` field

### Transcript Not Appearing
1. Check transcriptionStatus in userQuestionStatusDB
2. If IN_PROGRESS: Wait longer (can take 2-10 minutes)
3. If FAILED: Check transcriptionError field
4. If COMPLETED: Check transcript field (small) or transcriptS3Location (large)

## Future Enhancements (Not Implemented)

### API Endpoints (Planned by User)
- GET/POST endpoints for flag management
- GET endpoint for transcript retrieval
- Bulk operations for admin users

### Potential Features
- Multi-language support (change LanguageCode in StartTranscription)
- Custom vocabulary for better accuracy
- Speaker identification (already configured but disabled)
- Automatic profanity filtering
- Transcript search functionality
- Batch reprocessing of existing videos

## Rollback Instructions

If issues arise and you need to disable the system:

### Disable S3 Trigger (Stops New Transcriptions)
```bash
# Get current config
aws s3api get-bucket-notification-configuration --bucket virtual-legacy > /tmp/current-config.json

# Edit to remove VideoTranscriptionTrigger entry
# Then apply:
aws s3api put-bucket-notification-configuration --bucket virtual-legacy --notification-configuration file:///tmp/current-config.json
```

### Delete EventBridge Rule (Stops Processing Completions)
```bash
aws events remove-targets --rule Virtual-Legacy-MVP-1-ProcessTranscriptFunctionTranscribeComplete-* --ids 1
aws events delete-rule --name Virtual-Legacy-MVP-1-ProcessTranscriptFunctionTranscribeComplete-*
```

### Full Rollback (Remove All Components)
```bash
cd SamLambda
sam delete --stack-name Virtual-Legacy-MVP-1
```

**Note:** This will remove ALL Lambda functions, not just transcription ones. Only use if you want to completely reset the stack.

## Files Modified

### New Files Created
- `SamLambda/functions/videoFunctions/startTranscription/app.py`
- `SamLambda/functions/videoFunctions/processTranscript/app.py`

### Files Modified
- `SamLambda/template.yml` (added 2 Lambda functions, EventBridge rule)
- `SamLambda/functions/videoFunctions/uploadVideoResponse/app.py` (added transcript fields)
- `SamLambda/functions/questionDbFunctions/initializeUserProgress/app.py` (added allowTranscription flag)

### IAM Resources Created
- TranscribeServiceRole (manual creation via AWS CLI)

### S3 Configuration
- Added event notification for video uploads

## Support

For issues or questions:
1. Check CloudWatch Logs first
2. Verify DynamoDB records (userStatusDB, userQuestionStatusDB)
3. Check S3 for transcript files
4. Review Transcribe console for job status
5. Check this documentation for troubleshooting steps

---

**Implementation Date:** January 5, 2025  
**Status:** ✅ COMPLETE AND DEPLOYED  
**Version:** 1.0
