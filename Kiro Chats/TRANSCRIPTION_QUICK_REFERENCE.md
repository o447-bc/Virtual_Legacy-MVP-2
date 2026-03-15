# Video Transcription - Quick Reference

## Enable Transcription for a User

```bash
aws dynamodb update-item \
  --table-name userStatusDB \
  --key '{"userId": {"S": "USER_ID_HERE"}}' \
  --update-expression "SET allowTranscription = :val" \
  --expression-attribute-values '{":val": {"BOOL": true}}'
```

## Check Transcription Status

```bash
aws dynamodb get-item \
  --table-name userQuestionStatusDB \
  --key '{"userId": {"S": "USER_ID"}, "questionId": {"S": "QUESTION_ID"}}' \
  --query 'Item.transcriptionStatus.S'
```

## View Transcript

```bash
# From DynamoDB (if small)
aws dynamodb get-item \
  --table-name userQuestionStatusDB \
  --key '{"userId": {"S": "USER_ID"}, "questionId": {"S": "QUESTION_ID"}}' \
  --query 'Item.transcript.S'

# From S3 (always available)
aws s3 cp s3://virtual-legacy/user-responses/USER_ID/FILENAME.json ./
```

## List All Transcripts for a User

```bash
aws s3 ls s3://virtual-legacy/user-responses/USER_ID/ --recursive | grep .json
```

## View Recent Logs

```bash
# Check if transcription started
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-StartTranscriptionFunction-DpLW9VdSjugb --since 1h

# Check if transcription completed
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-ProcessTranscriptFunction-* --since 1h
```

## Check Metrics

```bash
# Count of transcriptions allowed
aws cloudwatch get-metric-statistics \
  --namespace VirtualLegacy/Transcription \
  --metric-name TranscriptionAllowed \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Count of transcriptions denied
aws cloudwatch get-metric-statistics \
  --namespace VirtualLegacy/Transcription \
  --metric-name TranscriptionDenied \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## File Locations

- **Videos:** `s3://virtual-legacy/user-responses/{userId}/{filename}.webm`
- **Thumbnails:** `s3://virtual-legacy/user-responses/{userId}/{filename}.jpg`
- **Transcripts:** `s3://virtual-legacy/user-responses/{userId}/{filename}.json`

## Default Settings

- **allowTranscription:** false (transcription disabled by default)
- **Language:** en-US
- **Format:** webm
- **Cost:** $0.024 per minute of video

## Common Issues

| Issue | Solution |
|-------|----------|
| Transcription not starting | Check allowTranscription flag is true |
| Job fails | Check video format (must be webm) |
| Transcript not in DynamoDB | Check transcriptS3Location field (may be too large) |
| No logs | Check S3 event notification is configured |

## Quick Test

1. Enable flag: `aws dynamodb update-item --table-name userStatusDB --key '{"userId": {"S": "TEST_USER_ID"}}' --update-expression "SET allowTranscription = :val" --expression-attribute-values '{":val": {"BOOL": true}}'`
2. Upload video via UI
3. Wait 2-5 minutes
4. Check: `aws s3 ls s3://virtual-legacy/user-responses/TEST_USER_ID/ | grep .json`
