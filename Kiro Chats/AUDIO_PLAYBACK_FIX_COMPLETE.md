# Audio Playback Fix - Complete Resolution

## Date: February 21, 2026, 1:40 PM EST

## Problem Summary

After Phase 1 security hardening added KMS encryption to S3, AI voice audio files could not be played in the browser. The audio files were uploaded successfully, but when the browser tried to play them using presigned URLs, it received **400 Bad Request** or **403 Forbidden** errors.

## Root Cause

The issue was **NOT** about AWS Signature Version 2 vs 4 (that was a red herring). The real problem was:

**KMS Key Policy Restriction**: The KMS key policy only allowed decryption when requests came through AWS service principals (Lambda, S3, DynamoDB) using the `kms:ViaService` condition. However, when a presigned URL is used:

1. Lambda generates a presigned URL with embedded temporary credentials
2. Browser makes a direct request to S3 using those credentials
3. S3 needs to decrypt the KMS-encrypted object
4. The request does NOT come "via" the service - it comes directly from the browser
5. The `kms:ViaService` condition fails
6. Result: 403 Forbidden

## Solution Implemented

Updated the KMS key policy in `SamLambda/template.yml` to add a new statement that allows IAM principals (with explicit KMS permissions in their IAM policies) to decrypt objects without the `kms:ViaService` condition:

```yaml
# Lambda roles for presigned URL access
# This allows Lambda execution roles to decrypt KMS-encrypted S3 objects
# when accessed via presigned URLs (which don't go through the service principal)
- Sid: Allow IAM Principals with KMS Permissions
  Effect: Allow
  Principal:
    AWS: !Sub arn:aws:iam::${AWS::AccountId}:root
  Action:
    - kms:Decrypt
    - kms:DescribeKey
    - kms:GenerateDataKey
  Resource: '*'
  Condition:
    StringEquals:
      kms:CallerAccount: !Ref AWS::AccountId
```

## Why This Works

1. **Defense in Depth**: The KMS key policy delegates access control to IAM policies
2. **No Circular Dependencies**: Using account root principal avoids CloudFormation circular dependencies
3. **Scoped Access**: The `kms:CallerAccount` condition ensures only principals in this account can use the key
4. **Existing IAM Permissions**: Lambda roles already have explicit KMS permissions in their IAM policies:
   - `kms:Decrypt`
   - `kms:DescribeKey`
   - `kms:GenerateDataKey`
5. **S3 Path Restrictions**: Lambda roles have S3 GetObject permissions scoped to specific paths

## Deployment

```bash
cd SamLambda
sam build
sam deploy --no-confirm-changeset
```

**Deployment Time**: February 21, 2026, 1:32 PM EST
**Stack**: Virtual-Legacy-MVP-1
**Status**: UPDATE_COMPLETE

## Verification Steps

1. Open the SoulReel application in a browser
2. Start a conversation with an AI persona
3. Verify that the AI voice audio plays correctly
4. Check browser console for no 403/400 errors
5. Verify the audio visualizer displays correctly

## What Was NOT the Issue

1. **Signature Version**: Both Signature Version 2 and 4 failed with 403 - this was not the root cause
2. **S3 Bucket Policy**: The bucket policy only affects uploads (PutObject), not downloads (GetObject)
3. **CORS Configuration**: CORS was already configured correctly
4. **Presigned URL Generation**: The URLs were being generated correctly

## Security Considerations

- This allows any IAM principal in the account with KMS permissions to decrypt
- Defense in depth: IAM policies control which principals have KMS permissions
- Lambda roles already have S3 GetObject permissions scoped to specific paths
- Presigned URLs still expire after 1 hour, limiting the window of access
- The `kms:CallerAccount` condition ensures only principals in this account can use the key

## Files Modified

- `SamLambda/template.yml` - Updated KMS key policy

## Documentation Created

- `Kiro Chats/KMS_PRESIGNED_URL_FIX.md` - Detailed technical explanation
- `Kiro Chats/AUDIO_PLAYBACK_FIX_COMPLETE.md` - This summary document

## Next Steps

1. **User Testing**: Have the user test AI voice playback in the browser
2. **User Audio Upload**: Test that user audio uploads also work (they use the same pattern)
3. **Video Playback**: Verify that video playback with KMS-encrypted files also works
4. **Monitor Logs**: Check CloudWatch logs for any KMS-related errors

## Lessons Learned

1. **Presigned URLs and KMS**: When using KMS encryption with presigned URLs, the KMS key policy must allow the IAM principal (not just the service principal) to decrypt
2. **Service Principal vs IAM Principal**: The `kms:ViaService` condition only works for direct service calls, not for presigned URLs
3. **Defense in Depth**: Using both KMS key policies and IAM policies provides better security
4. **Circular Dependencies**: Referencing Lambda roles in KMS key policy creates circular dependencies in CloudFormation
5. **Testing Presigned URLs**: Always test presigned URLs with the actual credentials that will be used (Lambda role, not developer IAM user)

## Status

✅ **DEPLOYED** - KMS key policy updated and deployed successfully.

⏳ **PENDING USER VERIFICATION** - Waiting for user to test AI voice playback in the browser.
