# Phase 1 Security Hardening - Verification Checklist

## Overview

This checklist provides step-by-step verification procedures for all Phase 1 security components. Each section includes CLI commands, expected outputs, and success criteria.

**Requirements Validated**: 11.1, 11.2, 11.3, 11.4, 11.5

---

## Pre-Verification Setup

### Set Environment Variables

```bash
# Set your stack name and region
export STACK_NAME="soulreel-backend"
export REGION="us-east-1"
export BUCKET_NAME="virtual-legacy"

# Get stack outputs
export KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`DataEncryptionKeyId`].OutputValue' \
  --output text)

export KEY_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`DataEncryptionKeyArn`].OutputValue' \
  --output text)

export TRAIL_NAME=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`DataAccessTrailName`].OutputValue' \
  --output text)

export AUDIT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogBucketName`].OutputValue' \
  --output text)

export DETECTOR_ID=$(aws guardduty list-detectors \
  --region $REGION \
  --query 'DetectorIds[0]' \
  --output text)

echo "Environment variables set successfully"
echo "KEY_ID: $KEY_ID"
echo "KEY_ARN: $KEY_ARN"
echo "TRAIL_NAME: $TRAIL_NAME"
echo "AUDIT_BUCKET: $AUDIT_BUCKET"
echo "DETECTOR_ID: $DETECTOR_ID"
```

---

## 1. KMS Key Verification

### 1.1 Verify Key Exists and is Enabled

**Command**:
```bash
aws kms describe-key --key-id $KEY_ID --region $REGION
```

**Expected Output**:
```json
{
  "KeyMetadata": {
    "KeyId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "KeyState": "Enabled",
    "Enabled": true,
    "KeyManager": "CUSTOMER",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "KeyUsage": "ENCRYPT_DECRYPT"
  }
}
```

**Success Criteria**:
- ✅ KeyState: "Enabled"
- ✅ Enabled: true
- ✅ KeyManager: "CUSTOMER"

### 1.2 Verify Key Rotation is Enabled

**Command**:
```bash
aws kms get-key-rotation-status --key-id $KEY_ID --region $REGION
```

**Expected Output**:
```json
{
  "KeyRotationEnabled": true
}
```

**Success Criteria**:
- ✅ KeyRotationEnabled: true

### 1.3 Verify Key Alias Exists

**Command**:
```bash
aws kms list-aliases \
  --region $REGION \
  --query "Aliases[?AliasName=='alias/soulreel-data-encryption']"
```

**Expected Output**:
```json
[
  {
    "AliasName": "alias/soulreel-data-encryption",
    "AliasArn": "arn:aws:kms:us-east-1:ACCOUNT:alias/soulreel-data-encryption",
    "TargetKeyId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
]
```

**Success Criteria**:
- ✅ Alias exists with correct name
- ✅ TargetKeyId matches KEY_ID

### 1.4 Verify Key Policy Contains Service Principals

**Command**:
```bash
aws kms get-key-policy \
  --key-id $KEY_ID \
  --policy-name default \
  --region $REGION \
  --output json | jq '.Policy | fromjson'
```

**Expected Output** (should contain):
```json
{
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT:root"}
    },
    {
      "Sid": "Allow CloudWatch Logs",
      "Principal": {"Service": "logs.amazonaws.com"}
    },
    {
      "Sid": "Allow Lambda",
      "Principal": {"Service": "lambda.amazonaws.com"}
    },
    {
      "Sid": "Allow DynamoDB",
      "Principal": {"Service": "dynamodb.amazonaws.com"}
    },
    {
      "Sid": "Allow S3",
      "Principal": {"Service": "s3.amazonaws.com"}
    }
  ]
}
```

**Success Criteria**:
- ✅ Root account has full permissions
- ✅ CloudWatch Logs service principal present
- ✅ Lambda service principal present
- ✅ DynamoDB service principal present
- ✅ S3 service principal present

---

## 2. DynamoDB Encryption Verification

### 2.1 Verify PersonaSignupTempDB Encryption

**Command**:
```bash
aws dynamodb describe-table \
  --table-name PersonaSignupTempDB \
  --region $REGION \
  --query 'Table.{SSE:SSEDescription,PITR:RestoreSummary}'
```

**Expected Output**:
```json
{
  "SSE": {
    "Status": "ENABLED",
    "SSEType": "KMS",
    "KMSMasterKeyArn": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
  }
}
```

**Success Criteria**:
- ✅ SSEType: "KMS"
- ✅ Status: "ENABLED"
- ✅ KMSMasterKeyArn matches KEY_ARN

### 2.2 Verify PersonaSignupTempDB PITR

**Command**:
```bash
aws dynamodb describe-continuous-backups \
  --table-name PersonaSignupTempDB \
  --region $REGION \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription'
```

**Expected Output**:
```json
{
  "PointInTimeRecoveryStatus": "ENABLED",
  "EarliestRestorableDateTime": "2026-02-15T10:00:00Z",
  "LatestRestorableDateTime": "2026-02-16T10:00:00Z"
}
```

**Success Criteria**:
- ✅ PointInTimeRecoveryStatus: "ENABLED"

### 2.3 Verify PersonaRelationshipsDB Encryption

**Command**:
```bash
aws dynamodb describe-table \
  --table-name PersonaRelationshipsDB \
  --region $REGION \
  --query 'Table.SSEDescription'
```

**Expected Output**:
```json
{
  "Status": "ENABLED",
  "SSEType": "KMS",
  "KMSMasterKeyArn": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
}
```

**Success Criteria**:
- ✅ SSEType: "KMS"
- ✅ KMSMasterKeyArn matches KEY_ARN

### 2.4 Verify EngagementDB Encryption

**Command**:
```bash
aws dynamodb describe-table \
  --table-name EngagementDB \
  --region $REGION \
  --query 'Table.SSEDescription'
```

**Expected Output**:
```json
{
  "Status": "ENABLED",
  "SSEType": "KMS",
  "KMSMasterKeyArn": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
}
```

**Success Criteria**:
- ✅ SSEType: "KMS"
- ✅ KMSMasterKeyArn matches KEY_ARN

### 2.5 Verify All Tables Use Same KMS Key

**Command**:
```bash
for table in PersonaSignupTempDB PersonaRelationshipsDB EngagementDB; do
  echo "Table: $table"
  aws dynamodb describe-table \
    --table-name $table \
    --region $REGION \
    --query 'Table.SSEDescription.KMSMasterKeyArn' \
    --output text
done
```

**Expected Output**:
```
Table: PersonaSignupTempDB
arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID
Table: PersonaRelationshipsDB
arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID
Table: EngagementDB
arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID
```

**Success Criteria**:
- ✅ All three tables show same KMS key ARN

---

## 3. S3 Bucket Encryption Verification

### 3.1 Verify Default Encryption Configuration

**Command**:
```bash
aws s3api get-bucket-encryption \
  --bucket $BUCKET_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "ServerSideEncryptionConfiguration": {
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms",
          "KMSMasterKeyID": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
        },
        "BucketKeyEnabled": true
      }
    ]
  }
}
```

**Success Criteria**:
- ✅ SSEAlgorithm: "aws:kms"
- ✅ KMSMasterKeyID matches KEY_ARN
- ✅ BucketKeyEnabled: true

### 3.2 Verify Versioning is Enabled

**Command**:
```bash
aws s3api get-bucket-versioning \
  --bucket $BUCKET_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "Status": "Enabled"
}
```

**Success Criteria**:
- ✅ Status: "Enabled"

### 3.3 Verify Public Access is Blocked

**Command**:
```bash
aws s3api get-public-access-block \
  --bucket $BUCKET_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "PublicAccessBlockConfiguration": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }
}
```

**Success Criteria**:
- ✅ All four settings are true

### 3.4 Verify Lifecycle Policies

**Command**:
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "Rules": [
    {
      "Id": "TransitionToStandardIA",
      "Status": "Enabled",
      "Transitions": [{"Days": 90, "StorageClass": "STANDARD_IA"}]
    },
    {
      "Id": "TransitionToGlacierIR",
      "Status": "Enabled",
      "Transitions": [{"Days": 365, "StorageClass": "GLACIER_IR"}]
    },
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
    }
  ]
}
```

**Success Criteria**:
- ✅ Three lifecycle rules exist
- ✅ Transition to STANDARD_IA after 90 days
- ✅ Transition to GLACIER_IR after 365 days
- ✅ Delete old versions after 90 days

### 3.5 Verify Bucket Policy Enforces Encryption

**Command**:
```bash
aws s3api get-bucket-policy \
  --bucket $BUCKET_NAME \
  --region $REGION \
  --output json | jq '.Policy | fromjson'
```

**Expected Output** (should contain):
```json
{
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    },
    {
      "Sid": "DenyIncorrectKMSKey",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption-aws-kms-key-id": "KEY_ARN"
        }
      }
    }
  ]
}
```

**Success Criteria**:
- ✅ Policy denies unencrypted uploads
- ✅ Policy denies uploads with wrong KMS key

### 3.6 Test Encryption Enforcement

**Command**:
```bash
# Create test file
echo "test content" > test-file.txt

# Try upload WITHOUT encryption (should fail)
aws s3api put-object \
  --bucket $BUCKET_NAME \
  --key test/unencrypted.txt \
  --body test-file.txt \
  --region $REGION 2>&1 | grep -q "AccessDenied" && echo "✅ Unencrypted upload blocked"

# Try upload WITH encryption (should succeed)
aws s3api put-object \
  --bucket $BUCKET_NAME \
  --key test/encrypted.txt \
  --body test-file.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id $KEY_ARN \
  --region $REGION && echo "✅ Encrypted upload succeeded"

# Verify object is encrypted
aws s3api head-object \
  --bucket $BUCKET_NAME \
  --key test/encrypted.txt \
  --region $REGION \
  --query 'ServerSideEncryption'

# Clean up
rm test-file.txt
aws s3api delete-object --bucket $BUCKET_NAME --key test/encrypted.txt --region $REGION
```

**Success Criteria**:
- ✅ Unencrypted upload is denied
- ✅ Encrypted upload succeeds
- ✅ Object shows ServerSideEncryption: "aws:kms"

---

## 4. CloudTrail Verification

### 4.1 Verify Trail Status

**Command**:
```bash
aws cloudtrail get-trail-status \
  --name $TRAIL_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "IsLogging": true,
  "LatestDeliveryTime": "2026-02-16T10:30:00Z",
  "LatestDigestDeliveryTime": "2026-02-16T10:30:00Z",
  "StartLoggingTime": "2026-02-15T10:00:00Z"
}
```

**Success Criteria**:
- ✅ IsLogging: true
- ✅ LatestDeliveryTime is recent (within 15 minutes)

### 4.2 Verify Trail Configuration

**Command**:
```bash
aws cloudtrail describe-trails \
  --trail-name-list $TRAIL_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "trailList": [
    {
      "Name": "soulreel-data-access-trail",
      "S3BucketName": "soulreel-audit-logs-ACCOUNT",
      "IsMultiRegionTrail": true,
      "LogFileValidationEnabled": true,
      "HasCustomEventSelectors": true
    }
  ]
}
```

**Success Criteria**:
- ✅ IsMultiRegionTrail: true
- ✅ LogFileValidationEnabled: true
- ✅ HasCustomEventSelectors: true

### 4.3 Verify Event Selectors

**Command**:
```bash
aws cloudtrail get-event-selectors \
  --trail-name $TRAIL_NAME \
  --region $REGION
```

**Expected Output**:
```json
{
  "EventSelectors": [
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::S3::Object",
          "Values": ["arn:aws:s3:::virtual-legacy/*"]
        }
      ]
    },
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": false,
      "DataResources": [
        {
          "Type": "AWS::DynamoDB::Table",
          "Values": [
            "arn:aws:dynamodb:us-east-1:ACCOUNT:table/PersonaRelationshipsDB",
            "arn:aws:dynamodb:us-east-1:ACCOUNT:table/EngagementDB"
          ]
        }
      ]
    }
  ]
}
```

**Success Criteria**:
- ✅ S3 data events configured for virtual-legacy bucket
- ✅ DynamoDB data events configured for tables
- ✅ ReadWriteType: "All" for both

### 4.4 Verify Audit Bucket Encryption

**Command**:
```bash
aws s3api get-bucket-encryption \
  --bucket $AUDIT_BUCKET \
  --region $REGION
```

**Expected Output**:
```json
{
  "ServerSideEncryptionConfiguration": {
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms",
          "KMSMasterKeyID": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
        }
      }
    ]
  }
}
```

**Success Criteria**:
- ✅ Audit bucket uses KMS encryption
- ✅ KMSMasterKeyID matches KEY_ARN

### 4.5 Test CloudTrail Logging

**Command**:
```bash
# Perform test operation
echo "test" > test.txt
aws s3 cp test.txt s3://$BUCKET_NAME/test/cloudtrail-test.txt --region $REGION

# Wait 15 minutes for CloudTrail to deliver logs
echo "Waiting 15 minutes for CloudTrail to deliver logs..."
sleep 900

# Check for recent events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=$BUCKET_NAME \
  --max-results 10 \
  --region $REGION \
  --query 'Events[0].{EventName:EventName,EventTime:EventTime,Username:Username}'

# Clean up
rm test.txt
aws s3 rm s3://$BUCKET_NAME/test/cloudtrail-test.txt --region $REGION
```

**Success Criteria**:
- ✅ PutObject event appears in CloudTrail
- ✅ Event timestamp is within last 15 minutes

---

## 5. GuardDuty Verification

### 5.1 Verify Detector is Enabled

**Command**:
```bash
aws guardduty get-detector \
  --detector-id $DETECTOR_ID \
  --region $REGION
```

**Expected Output**:
```json
{
  "Status": "ENABLED",
  "FindingPublishingFrequency": "FIFTEEN_MINUTES",
  "DataSources": {
    "S3Logs": {
      "Status": "ENABLED"
    },
    "CloudTrail": {
      "Status": "ENABLED"
    }
  }
}
```

**Success Criteria**:
- ✅ Status: "ENABLED"
- ✅ FindingPublishingFrequency: "FIFTEEN_MINUTES"
- ✅ S3Logs Status: "ENABLED"

### 5.2 Verify EventBridge Rule Exists

**Command**:
```bash
aws events describe-rule \
  --name GuardDutyAlertRule \
  --region $REGION
```

**Expected Output**:
```json
{
  "Name": "GuardDutyAlertRule",
  "State": "ENABLED",
  "EventPattern": "{\"source\":[\"aws.guardduty\"],\"detail-type\":[\"GuardDuty Finding\"],\"detail\":{\"severity\":[7,7.0,7.1,7.2,7.3,7.4,7.5,7.6,7.7,7.8,7.9,8,8.0,8.1,8.2,8.3,8.4,8.5,8.6,8.7,8.8,8.9,9,9.0,9.1,9.2,9.3,9.4,9.5,9.6,9.7,9.8,9.9,10]}}"
}
```

**Success Criteria**:
- ✅ State: "ENABLED"
- ✅ EventPattern includes severity ≥ 7.0

### 5.3 Verify SNS Topic Exists

**Command**:
```bash
export TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityAlertTopicArn`].OutputValue' \
  --output text)

aws sns get-topic-attributes \
  --topic-arn $TOPIC_ARN \
  --region $REGION \
  --query 'Attributes.{DisplayName:DisplayName,SubscriptionsConfirmed:SubscriptionsConfirmed}'
```

**Expected Output**:
```json
{
  "DisplayName": "SoulReel Security Alerts",
  "SubscriptionsConfirmed": "1"
}
```

**Success Criteria**:
- ✅ Topic exists
- ✅ At least one subscription confirmed

### 5.4 Test GuardDuty Alerts

**Command**:
```bash
# Generate sample finding
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types UnauthorizedAccess:S3/MaliciousIPCaller.Custom \
  --region $REGION

echo "Sample finding created. Check email for alert within 2 minutes."
echo "Also check GuardDuty console for the finding."

# List recent findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --region $REGION \
  --finding-criteria '{"Criterion":{"updatedAt":{"Gte":'$(date -u -d '1 hour ago' +%s)000'}}}'
```

**Success Criteria**:
- ✅ Sample finding appears in GuardDuty console
- ✅ Email alert received within 2 minutes

---

## 6. IAM Policy Verification

### 6.1 Verify Lambda Function Policies

**Command**:
```bash
# List all Lambda functions
aws lambda list-functions \
  --region $REGION \
  --query 'Functions[*].FunctionName' \
  --output text

# For each function, check IAM role
for func in WebSocketDefaultFunction ProcessVideoFunction MonthlyResetFunction; do
  echo "Function: $func"
  
  # Get role name
  ROLE_NAME=$(aws lambda get-function \
    --function-name $func \
    --region $REGION \
    --query 'Configuration.Role' \
    --output text | awk -F'/' '{print $NF}')
  
  echo "Role: $ROLE_NAME"
  
  # Get inline policies
  aws iam list-role-policies \
    --role-name $ROLE_NAME \
    --query 'PolicyNames'
  
  echo "---"
done
```

**Success Criteria**:
- ✅ All Lambda functions have IAM roles
- ✅ Roles have appropriate policies attached

### 6.2 Check for Wildcard Resources

**Command**:
```bash
# Check WebSocketDefaultFunction policy
ROLE_NAME=$(aws lambda get-function \
  --function-name WebSocketDefaultFunction \
  --region $REGION \
  --query 'Configuration.Role' \
  --output text | awk -F'/' '{print $NF}')

aws iam get-role-policy \
  --role-name $ROLE_NAME \
  --policy-name WebSocketDefaultFunctionPolicy \
  --query 'PolicyDocument' \
  --output json | jq '.Statement[] | select(.Resource == "*")'
```

**Expected Output**:
```json
{
  "Effect": "Allow",
  "Action": "polly:SynthesizeSpeech",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "us-east-1"
    }
  }
}
```

**Success Criteria**:
- ✅ Only Polly and CloudWatch use wildcard resources
- ✅ Wildcard resources have condition keys
- ✅ S3 and DynamoDB use specific ARNs

---

## 7. Resource Tagging Verification

### 7.1 Verify KMS Key Tags

**Command**:
```bash
aws kms list-resource-tags \
  --key-id $KEY_ID \
  --region $REGION
```

**Expected Output**:
```json
{
  "Tags": [
    {"TagKey": "Project", "TagValue": "SoulReel"},
    {"TagKey": "SecurityPhase", "TagValue": "Phase1"},
    {"TagKey": "CostCenter", "TagValue": "Security"}
  ]
}
```

**Success Criteria**:
- ✅ Project tag exists
- ✅ SecurityPhase tag exists
- ✅ CostCenter tag exists

### 7.2 Verify CloudTrail Tags

**Command**:
```bash
TRAIL_ARN=$(aws cloudtrail describe-trails \
  --trail-name-list $TRAIL_NAME \
  --region $REGION \
  --query 'trailList[0].TrailARN' \
  --output text)

aws cloudtrail list-tags \
  --resource-id-list $TRAIL_ARN \
  --region $REGION
```

**Expected Output**:
```json
{
  "ResourceTagList": [
    {
      "ResourceId": "arn:aws:cloudtrail:...",
      "TagsList": [
        {"Key": "Project", "Value": "SoulReel"},
        {"Key": "SecurityPhase", "Value": "Phase1"},
        {"Key": "CostCenter", "Value": "Security"}
      ]
    }
  ]
}
```

**Success Criteria**:
- ✅ All required tags present

---

## 8. End-to-End Functionality Verification

### 8.1 Test Video Upload with Encryption

**Command**:
```bash
# Create test video file (or use existing)
echo "test video content" > test-video.mp4

# Upload to S3
aws s3 cp test-video.mp4 s3://$BUCKET_NAME/test/verification-video.mp4 \
  --region $REGION

# Verify encryption
aws s3api head-object \
  --bucket $BUCKET_NAME \
  --key test/verification-video.mp4 \
  --region $REGION \
  --query '{Encryption:ServerSideEncryption,KeyId:SSEKMSKeyId}'
```

**Expected Output**:
```json
{
  "Encryption": "aws:kms",
  "KeyId": "arn:aws:kms:us-east-1:ACCOUNT:key/KEY_ID"
}
```

**Success Criteria**:
- ✅ Upload succeeds
- ✅ Object is encrypted with aws:kms
- ✅ Correct KMS key is used

### 8.2 Test Video Download with Decryption

**Command**:
```bash
# Download video
aws s3 cp s3://$BUCKET_NAME/test/verification-video.mp4 \
  downloaded-video.mp4 \
  --region $REGION

# Verify content matches
diff test-video.mp4 downloaded-video.mp4 && echo "✅ Content matches"

# Clean up
rm test-video.mp4 downloaded-video.mp4
aws s3 rm s3://$BUCKET_NAME/test/verification-video.mp4 --region $REGION
```

**Success Criteria**:
- ✅ Download succeeds
- ✅ Content matches original
- ✅ Decryption is automatic

### 8.3 Test Lambda Function Execution

**Command**:
```bash
# Test WebSocketDefaultFunction
aws lambda invoke \
  --function-name WebSocketDefaultFunction \
  --payload '{"body":"test"}' \
  --region $REGION \
  response.json

cat response.json
rm response.json

# Check for errors in CloudWatch Logs
aws logs tail /aws/lambda/WebSocketDefaultFunction \
  --since 5m \
  --region $REGION \
  --filter-pattern "ERROR"
```

**Success Criteria**:
- ✅ Lambda invocation succeeds
- ✅ No AccessDenied errors
- ✅ No KMS-related errors

---

## 9. Performance Verification

### 9.1 Measure API Response Times

**Command**:
```bash
# Test API endpoint response time
for i in {1..10}; do
  time curl -X GET https://your-api-gateway-url/endpoint \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -w "\nTime: %{time_total}s\n"
done
```

**Success Criteria**:
- ✅ Response times within 10% of baseline
- ✅ No timeout errors

---

## 10. Cost Monitoring Verification

### 10.1 Verify Cost Explorer Tags

**Command**:
```bash
# Check if cost allocation tags are active
aws ce list-cost-allocation-tags \
  --region us-east-1 \
  --query 'CostAllocationTags[?TagKey==`Project` || TagKey==`SecurityPhase` || TagKey==`CostCenter`]'
```

**Expected Output**:
```json
[
  {"TagKey": "Project", "Status": "Active"},
  {"TagKey": "SecurityPhase", "Status": "Active"},
  {"TagKey": "CostCenter", "Status": "Active"}
]
```

**Success Criteria**:
- ✅ All cost allocation tags are active

---

## Summary Checklist

### Phase 1 Components

- [ ] KMS key created and rotation enabled
- [ ] KMS key alias exists
- [ ] All DynamoDB tables encrypted with CMK
- [ ] PersonaSignupTempDB has PITR enabled
- [ ] S3 bucket has default encryption with CMK
- [ ] S3 bucket has versioning enabled
- [ ] S3 bucket has public access blocked
- [ ] S3 bucket has lifecycle policies
- [ ] S3 bucket policy enforces encryption
- [ ] CloudTrail is logging
- [ ] CloudTrail has log file validation
- [ ] CloudTrail event selectors configured
- [ ] Audit bucket is encrypted
- [ ] GuardDuty detector is enabled
- [ ] GuardDuty S3 protection is enabled
- [ ] EventBridge rule routes high-severity findings
- [ ] SNS topic has confirmed subscription
- [ ] Lambda IAM policies use least-privilege
- [ ] All security resources have cost tracking tags

### Functional Tests

- [ ] Video upload works with automatic encryption
- [ ] Video download works with automatic decryption
- [ ] Lambda functions execute without errors
- [ ] API endpoints respond normally
- [ ] Response times within 10% of baseline
- [ ] No AccessDenied errors in logs
- [ ] CloudTrail logs recent operations
- [ ] GuardDuty sample finding triggers alert

### Monitoring

- [ ] CloudWatch Logs show no errors
- [ ] Cost Explorer tags are active
- [ ] GuardDuty findings reviewed
- [ ] CloudTrail logs delivered to audit bucket

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-16  
**Requirements Validated**: 11.1, 11.2, 11.3, 11.4, 11.5
