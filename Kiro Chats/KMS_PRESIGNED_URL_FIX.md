# KMS Presigned URL Access Fix

## Date: February 21, 2026

## Problem

AI voice audio files are uploaded successfully to S3 with KMS encryption, but when the browser tries to play them using presigned URLs, it gets **403 Forbidden** errors.

## Root Cause

The KMS key policy allows decryption only when requests come **via AWS services** (Lambda, S3, DynamoDB) using the `kms:ViaService` condition:

```json
{
  "Sid": "Allow S3 Service",
  "Effect": "Allow",
  "Principal": {
    "Service": "s3.amazonaws.com"
  },
  "Action": ["kms:Decrypt", ...],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com"
    }
  }
}
```

**However, when a presigned URL is used:**
1. The Lambda generates a presigned URL with embedded temporary credentials
2. The browser makes a direct request to S3 using those credentials
3. S3 needs to decrypt the KMS-encrypted object
4. The request does NOT come "via" the S3 service - it comes directly from the browser
5. The `kms:ViaService` condition fails
6. Result: 403 Forbidden

## Solution

Add a statement to the KMS key policy that allows IAM principals (with explicit KMS permissions in their IAM policies) to decrypt objects without the `kms:ViaService` condition:

```yaml
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

This allows any IAM principal in the account (including Lambda execution roles using temporary credentials) to decrypt KMS-encrypted objects, as long as:
1. They have explicit KMS permissions in their IAM policy
2. They are in the same AWS account

## Why This Approach

**Alternative 1: Reference specific Lambda roles in KMS policy**
- Problem: Creates circular dependency (KMS key references roles, roles reference KMS key)
- CloudFormation deployment would fail

**Alternative 2: Remove `kms:ViaService` from service principals**
- Problem: Too permissive, allows any service to decrypt
- Security concern

**Chosen Approach: Allow account root with account condition**
- Delegates access control to IAM policies (defense in depth)
- No circular dependencies
- Scoped to the account only
- Lambda roles already have explicit KMS permissions in their IAM policies

## Security Considerations

- This allows any IAM principal in the account with KMS permissions to decrypt
- Defense in depth: IAM policies control which principals have KMS permissions
- Lambda roles already have S3 GetObject permissions scoped to specific paths
- Presigned URLs still expire after 1 hour, limiting the window of access
- The `kms:CallerAccount` condition ensures only principals in this account can use the key

## Implementation

Updated `SamLambda/template.yml` to add the new KMS key policy statement.

## Deployment

```bash
cd SamLambda
sam build
sam deploy --no-confirm-changeset
```

## Verification

After deployment, test that AI voice audio plays correctly in the browser.
