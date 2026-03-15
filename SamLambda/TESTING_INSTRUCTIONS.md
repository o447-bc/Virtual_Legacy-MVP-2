# Streaming Transcription Testing Instructions

## Deployment Validation ✅

The following have been verified:

### Lambda Configuration
```bash
aws lambda get-function-configuration \
  --function-name Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb
```

✅ **Architecture**: x86_64 (required for ffmpeg layer)
✅ **Layers**: arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1
✅ **Timeout**: 30 seconds
✅ **Memory**: 512 MB

### Test Audio File
```bash
aws s3 ls s3://virtual-legacy/test-audio/
```

✅ **File exists**: short_audio.webm (268,844 bytes)

### Code Deployment
✅ **Build**: Successful
✅ **Deploy**: Successful
✅ **Stack Status**: UPDATE_COMPLETE

## Manual Testing Required

Since the test requires user credentials, please run the following tests:

### Test 1: End-to-End Streaming Test

**Run:**
```bash
cd SamLambda
python3 test_streaming_e2e.py
```

**Enter your credentials when prompted**

**Expected Results:**

**If Streaming Works (Success):**
```
✅ Response received in 2-4 seconds
✅ EXCELLENT: Latency 2.5s < 6.0s target
   Streaming transcription likely succeeded
```

**If Fallback to Batch (Still OK):**
```
✅ Response received in 8-9 seconds
⚠️  ACCEPTABLE: Latency 8.5s (6-10s)
   May have used batch transcription fallback
```

**If Complete Failure:**
```
❌ Error processing audio: [error message]
```

### Test 2: Check CloudWatch Logs

**Run (in separate terminal):**
```bash
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --follow
```

**Then run the E2E test**

**Look for these patterns:**

**Streaming Success:**
```
[AUDIO] Attempting streaming transcription
[STREAMING] Starting streaming transcription
[STREAMING] Found ffmpeg at: /opt/bin/ffmpeg
[STREAMING] Conversion successful: XXXXX bytes
[STREAMING] Transcript: [your speech]
[AUDIO] Streaming transcription successful
```

**Streaming Failure (Fallback):**
```
[AUDIO] Attempting streaming transcription
[STREAMING] Error: [error details]
[AUDIO] Streaming failed: [error]
[AUDIO] Falling back to batch transcription
[TRANSCRIBE] Starting transcription
```

**Import Error (Critical):**
```
ModuleNotFoundError: No module named 'amazon_transcribe'
```
or
```
ImportError: cannot import name 'transcribe_audio_streaming'
```

## Troubleshooting

### If you see "ModuleNotFoundError: No module named 'amazon_transcribe'"

**Cause**: Dependency not installed during build

**Fix**:
```bash
cd SamLambda
sam build --use-container
sam deploy --no-confirm-changeset
```

### If you see "ffmpeg not found"

**Cause**: Layer not attached or wrong architecture

**Check**:
```bash
aws lambda get-function-configuration \
  --function-name Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --query '{Arch:Architectures[0],Layers:Layers[*].Arn}'
```

**Should show**:
- Architecture: x86_64
- Layer: arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1

### If you see "Transcribe streaming timeout"

**Cause**: Audio file too large or network issues

**Check audio file size**:
```bash
aws s3 ls s3://virtual-legacy/test-audio/short_audio.webm
```

Should be < 1 MB for test

### If fallback rate is high (>50%)

**Check CloudWatch logs for common errors**:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --filter-pattern "[STREAMING] Error" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

## Performance Benchmarking

After running several conversations, measure performance:

### Query Average Latency

```bash
# Get recent conversation logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --filter-pattern "[AUDIO]" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  | grep -E "(Streaming transcription|Batch transcription) successful"
```

### Count Streaming vs Batch

```bash
# Count streaming successes
aws logs filter-log-events \
  --log-group-name /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --filter-pattern "[AUDIO] Streaming transcription successful" \
  --start-time $(date -u -d '24 hours ago' +%s)000 \
  | grep -c "Streaming transcription successful"

# Count batch fallbacks
aws logs filter-log-events \
  --log-group-name /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb \
  --filter-pattern "[AUDIO] Falling back to batch" \
  --start-time $(date -u -d '24 hours ago' +%s)000 \
  | grep -c "Falling back"
```

## Success Criteria

✅ **Deployment**: Lambda configuration correct
✅ **Test Audio**: File exists in S3
⏳ **E2E Test**: Needs user credentials to run
⏳ **Performance**: Needs real conversation data
⏳ **Reliability**: Needs 24-48 hours of monitoring

## Next Steps

1. **Run E2E Test**: Use your credentials to test
2. **Monitor Logs**: Watch for streaming success/failure patterns
3. **Measure Performance**: Track latency over multiple conversations
4. **Analyze Fallback Rate**: Investigate if >10%
5. **User Feedback**: Collect feedback on responsiveness

## Quick Test Command

```bash
# One-line test (requires credentials)
cd SamLambda && python3 test_streaming_e2e.py
```

## Monitoring Dashboard

Consider creating CloudWatch dashboard with:
- Streaming success rate
- Average latency (streaming vs batch)
- Fallback rate
- Error rate

---

**Status**: Ready for manual testing
**Last Updated**: October 19, 2025
