# Audio Upload Investigation

## ROOT CAUSE IDENTIFIED ✅

### The Issue
When KMS encryption was added to S3 uploads during Phase 1 security hardening, the S3 client was still using **AWS Signature Version 2** for generating presigned URLs. However, **KMS-encrypted objects require AWS Signature Version 4**.

### The Error
```
InvalidArgument: Requests specifying Server Side Encryption with AWS KMS managed keys require AWS Signature Version 4.
```

### The Fix
Configure all S3 clients to use Signature Version 4:
```python
from botocore.client import Config
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
```

## Current Status

### Issue 1: AI Voice (FIXED ✅)
- **Root Cause**: S3 client using Signature Version 2 for presigned URLs
- **Solution**: Updated all S3 clients to use Signature Version 4
- **Status**: DEPLOYED

### Issue 2: User Audio Upload (FIXED ✅)
- **Root Cause 1**: S3 bucket policy not deployed
- **Root Cause 2**: S3 client using Signature Version 2 for presigned URLs
- **Solution**: 
  1. Deployed updated S3 bucket policy
  2. Updated all S3 clients to use Signature Version 4
- **Status**: DEPLOYED

## Files Modified

All S3 clients updated to use Signature Version 4:
1. `SamLambda/functions/conversationFunctions/wsDefault/speech.py`
2. `SamLambda/functions/conversationFunctions/wsDefault/app.py`
3. `SamLambda/functions/conversationFunctions/wsDefault/storage.py`
4. `SamLambda/functions/conversationFunctions/wsDefault/transcribe.py`
5. `SamLambda/functions/conversationFunctions/wsDefault/transcribe_streaming.py`
6. `SamLambda/functions/conversationFunctions/wsDefault/transcribe_deepgram.py`

## Technical Details

### Why This Happened
When we added KMS encryption to S3 uploads for security compliance, we didn't update the S3 client configuration. The default boto3 S3 client uses Signature Version 2 for presigned URLs, which doesn't support KMS encryption parameters.

### AWS Signature Versions
- **Signature Version 2**: Legacy signing method, doesn't support KMS encryption
- **Signature Version 4**: Modern signing method, required for KMS-encrypted objects

### The Security Connection
This issue was directly caused by the Phase 1 security hardening:
- Added KMS encryption to all S3 uploads (requirement 3.1)
- KMS encryption requires Signature Version 4
- Existing code was using Signature Version 2
- Result: 403 Forbidden errors on presigned URL access

## Deployment Status
- ✅ S3 bucket policy deployed (2026-02-21 17:51 UTC)
- ✅ Backend Lambda functions deployed (2026-02-21 18:50 UTC)
- ✅ All S3 clients configured for Signature Version 4

## Testing Required
1. Test AI voice playback - should now work
2. Test user audio upload - should now work
3. Verify both features work end-to-end
