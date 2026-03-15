# Phase 1 Security Hardening - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying Phase 1 security hardening to the SoulReel infrastructure. The deployment follows a phased approach to minimize risk, with verification checkpoints after each phase.

**Estimated Total Deployment Time**: 45-60 minutes

**Prerequisites**:
- AWS CLI configured with appropriate credentials
- SAM CLI installed
- Access to AWS account with administrative permissions
- Backup of current CloudFormation template
- Email address for security alerts

## Pre-Deployment Checklist

- [ ] Review all changes in `template.yml`
- [ ] Run all unit tests locally
- [ ] Run all property tests locally (100+ iterations each)
- [ ] Backup current CloudFormation stack
- [ ] Document current API response time baselines
- [ ] Notify team of deployment window
- [ ] Prepare rollback plan

## Phase 1: Deploy KMS Key and Alias

### Step 1.1: Deploy KMS Resources

**Action**: Deploy CloudFormation stack with KMS key and alias

```bash
cd SamLambda
sam build
sam deploy --guided
```

**Configuration**:
- Stack name: `soulreel-backend` (or your existing stack name)
- AWS Region: `us-east-1` (or your deployment region)
- Confirm changes before deploy: Y
- Allow SAM CLI IAM role creation: Y
- Save arguments to configuration file: Y

**Expected Duration**: 3-5 minutes

### Step 1.2: Verify KMS Key Creation

**Verification Commands**:

```bash
# Get KMS key ID from stack outputs
KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name soulreel-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`DataEncryptionKeyId`].OutputValue' \
  --output text)

# Verify key exists and rotation is enabled
aws kms describe-key --key-id $KEY_ID

# Expected output should show:
# - KeyState: Enabled
# - KeyRotationEnabled: true

# Verify alias exists
aws kms list-aliases --query "Aliases[?AliasName=='alias/soulreel-data-encryption']"

# Expected output should show the alias pointing to the key
```

**Success Criteria**:
- ✅ KMS key exists with status "Enabled"
- ✅ Key rotation is enabled
- ✅ Alias "alias/soulreel-data-encryption" exists
- ✅ Key policy contains service principal statements

**Rollback Procedure** (if needed):
```bash
# Rollback to previous stack version
aws cloudformation rollback-stack --stack-name soulreel-backend

# Or delete the stack entirely
aws cloudformation delete-stack --stack-name soulreel-backend
```

---

## Phase 2: Update DynamoDB Tables with CMK Encryption

### Step 2.1: Deploy DynamoDB Encryption Updates

**Action**: Deploy stack update with DynamoDB table encryption changes

```bash
sam deploy
```

**Expected Duration**: 5-10 minutes (AWS re-encrypts existing data automatically)

### Step 2.2: Verify DynamoDB Encryption

**Verification Commands**:

```bash
# Verify PersonaSignupTempTable encryption
aws dynamodb describe-table \
  --table-name PersonaSignupTempDB \
  --query 'Table.SSEDescription'

# Expected output:
# {
#   "Status": "ENABLED",
#   "SSEType": "KMS",
#   "KMSMasterKeyArn": "arn:aws:kms:..."
# }

# Verify PersonaRelationshipsTable encryption
aws dynamodb describe-table \
  --table-name PersonaRelationshipsDB \
  --query 'Table.SSEDescription'

# Verify EngagementTable encryption
aws dynamodb describe-table \
  --table-name EngagementDB \
  --query 'Table.SSEDescription'

# Verify PITR is enabled on PersonaSignupTempDB
aws dynamodb describe-continuous-backups \
  --table-name PersonaSignupTempDB \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus'

# Expected output: "ENABLED"
```

**Success Criteria**:
- ✅ All three tables show SSEType: KMS
- ✅ All three tables reference DataEncryptionKey ARN
- ✅ PersonaSignupTempDB has PITR enabled
- ✅ Tables remain accessible (test with a read operation)

**Rollback Procedure** (if needed):
```bash
# WARNING: Cannot revert DynamoDB encryption from CMK to AWS-managed keys
# Only option is to restore from backup or recreate tables

# Rollback entire stack
aws cloudformation rollback-stack --stack-name soulreel-backend
```

**⚠️ Important Note**: DynamoDB encryption changes are permanent. Once a table is encrypted with a CMK, it cannot be reverted to AWS-managed keys without recreating the table.

---

## Phase 3: Configure S3 Bucket Encryption and Security

### Step 3.1: Configure S3 Bucket Encryption

**Action**: Apply encryption configuration to existing `virtual-legacy` bucket

See `S3_BUCKET_CONFIGURATION.sh` script for detailed commands.

```bash
# Get KMS key ARN
KEY_ARN=$(aws cloudformation describe-stacks \
  --stack-name soulreel-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`DataEncryptionKeyArn`].OutputValue' \
  --output text)

# Configure default encryption
aws s3api put-bucket-encryption \
  --bucket virtual-legacy \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "'$KEY_ARN'"
      },
      "BucketKeyEnabled": true
    }]
  }'

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket virtual-legacy \
  --versioning-configuration Status=Enabled

# Block all public access
aws s3api put-public-access-block \
  --bucket virtual-legacy \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true
```

**Expected Duration**: 1-2 minutes

### Step 3.2: Deploy S3 Bucket Policy

**Action**: Deploy bucket policy to enforce encryption

```bash
sam deploy
```

**Expected Duration**: 2-3 minutes

### Step 3.3: Configure S3 Lifecycle Policies

**Action**: Apply lifecycle rules to manage storage costs

```bash
# Create lifecycle configuration file
cat > lifecycle-config.json << 'EOF'
{
  "Rules": [
    {
      "Id": "TransitionToIA",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "TransitionToGlacier",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER_IR"
        }
      ]
    },
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
EOF

# Apply lifecycle configuration
aws s3api put-bucket-lifecycle-configuration \
  --bucket virtual-legacy \
  --lifecycle-configuration file://lifecycle-config.json
```

**Expected Duration**: 1 minute

### Step 3.4: Verify S3 Configuration

**Verification Commands**:

```bash
# Verify encryption configuration
aws s3api get-bucket-encryption --bucket virtual-legacy

# Expected output should show:
# - SSEAlgorithm: aws:kms
# - KMSMasterKeyID: (your key ARN)
# - BucketKeyEnabled: true

# Verify versioning
aws s3api get-bucket-versioning --bucket virtual-legacy

# Expected output: Status: Enabled

# Verify public access block
aws s3api get-public-access-block --bucket virtual-legacy

# Expected output: All four settings should be true

# Verify lifecycle policies
aws s3api get-bucket-lifecycle-configuration --bucket virtual-legacy

# Expected output: Three rules (TransitionToIA, TransitionToGlacier, DeleteOldVersions)

# Verify bucket policy
aws s3api get-bucket-policy --bucket virtual-legacy

# Expected output: Policy denying unencrypted uploads
```

**Success Criteria**:
- ✅ Default encryption uses KMS with DataEncryptionKey
- ✅ S3 Bucket Key is enabled
- ✅ Versioning is enabled
- ✅ All public access is blocked
- ✅ Lifecycle policies are configured
- ✅ Bucket policy enforces encryption

**Rollback Procedure** (if needed):
```bash
# Remove encryption enforcement policy
aws s3api delete-bucket-policy --bucket virtual-legacy

# Disable versioning (cannot be fully disabled, only suspended)
aws s3api put-bucket-versioning \
  --bucket virtual-legacy \
  --versioning-configuration Status=Suspended

# Remove lifecycle configuration
aws s3api delete-bucket-lifecycle --bucket virtual-legacy

# Note: Encryption configuration can be changed but not removed
```

---

## Phase 4: Deploy CloudTrail and Audit Logging

### Step 4.1: Deploy CloudTrail Resources

**Action**: Deploy stack update with CloudTrail and audit bucket

```bash
sam deploy
```

**Expected Duration**: 3-5 minutes

### Step 4.2: Verify CloudTrail Configuration

**Verification Commands**:

```bash
# Get trail name from stack
TRAIL_NAME=$(aws cloudformation describe-stacks \
  --stack-name soulreel-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`DataAccessTrailName`].OutputValue' \
  --output text)

# Verify trail status
aws cloudtrail get-trail-status --name $TRAIL_NAME

# Expected output:
# - IsLogging: true

# Verify trail configuration
aws cloudtrail describe-trails --trail-name-list $TRAIL_NAME

# Expected output should show:
# - IsMultiRegionTrail: true
# - LogFileValidationEnabled: true

# Verify event selectors
aws cloudtrail get-event-selectors --trail-name $TRAIL_NAME

# Expected output: Event selectors for S3 and DynamoDB data events

# Verify audit bucket exists and is encrypted
AUDIT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name soulreel-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogBucketName`].OutputValue' \
  --output text)

aws s3api get-bucket-encryption --bucket $AUDIT_BUCKET
```

**Success Criteria**:
- ✅ CloudTrail is logging (IsLogging: true)
- ✅ Trail is multi-region
- ✅ Log file validation is enabled
- ✅ Event selectors include S3 and DynamoDB
- ✅ Audit bucket is encrypted with DataEncryptionKey
- ✅ Audit bucket has public access blocked

### Step 4.3: Test CloudTrail Logging

**Action**: Perform test operations and verify they appear in logs

```bash
# Perform test S3 operation
aws s3 cp test-file.txt s3://virtual-legacy/test/test-file.txt

# Perform test DynamoDB operation
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"PK": {"S": "test"}, "SK": {"S": "test"}}'

# Wait 15 minutes for CloudTrail to deliver logs

# Check for logs in audit bucket
aws s3 ls s3://$AUDIT_BUCKET/AWSLogs/

# Download and inspect recent log file
aws s3 cp s3://$AUDIT_BUCKET/AWSLogs/$(aws sts get-caller-identity --query Account --output text)/CloudTrail/us-east-1/$(date +%Y/%m/%d)/ . --recursive

# Verify log file contains test operations
```

**Success Criteria**:
- ✅ Test operations appear in CloudTrail logs within 15 minutes
- ✅ Log files are encrypted
- ✅ Log file validation passes

**Rollback Procedure** (if needed):
```bash
# Stop CloudTrail logging
aws cloudtrail stop-logging --name $TRAIL_NAME

# Or rollback entire stack
aws cloudformation rollback-stack --stack-name soulreel-backend
```

---

## Phase 5: Enable GuardDuty Threat Detection

### Step 5.1: Deploy GuardDuty Resources

**Action**: Deploy stack update with GuardDuty detector and alerts

```bash
sam deploy
```

**Expected Duration**: 2-3 minutes

### Step 5.2: Configure SNS Email Subscription

**Action**: Subscribe email address to security alerts topic

```bash
# Get SNS topic ARN
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name soulreel-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityAlertTopicArn`].OutputValue' \
  --output text)

# Subscribe email address
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com

# Check email and confirm subscription
```

**Expected Duration**: 1 minute (plus email confirmation)

### Step 5.3: Verify GuardDuty Configuration

**Verification Commands**:

```bash
# Get detector ID
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# Verify detector is enabled
aws guardduty get-detector --detector-id $DETECTOR_ID

# Expected output:
# - Status: ENABLED
# - FindingPublishingFrequency: FIFTEEN_MINUTES

# Verify S3 protection is enabled
aws guardduty get-detector --detector-id $DETECTOR_ID \
  --query 'DataSources.S3Logs.Status'

# Expected output: ENABLED

# Verify EventBridge rule exists
aws events list-rules --name-prefix GuardDutyAlertRule

# Verify SNS topic exists
aws sns get-topic-attributes --topic-arn $TOPIC_ARN
```

**Success Criteria**:
- ✅ GuardDuty detector is enabled
- ✅ S3 protection is enabled
- ✅ Finding frequency is 15 minutes
- ✅ EventBridge rule exists with correct pattern
- ✅ SNS topic exists
- ✅ Email subscription is confirmed

### Step 5.4: Test GuardDuty Alerts

**Action**: Generate sample finding to test alert flow

```bash
# Generate sample finding
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types UnauthorizedAccess:S3/MaliciousIPCaller.Custom

# Wait 1-2 minutes for alert to be sent

# Check email for security alert
```

**Success Criteria**:
- ✅ Sample finding appears in GuardDuty console
- ✅ Email alert is received within 2 minutes

**Rollback Procedure** (if needed):
```bash
# Disable GuardDuty detector
aws guardduty update-detector \
  --detector-id $DETECTOR_ID \
  --no-enable

# Or rollback entire stack
aws cloudformation rollback-stack --stack-name soulreel-backend
```

---

## Phase 6: Harden IAM Policies for Lambda Functions

### Step 6.1: Deploy IAM Policy Updates

**Action**: Deploy stack update with hardened IAM policies

```bash
sam deploy
```

**Expected Duration**: 2-3 minutes

### Step 6.2: Verify Lambda Functions Still Work

**Verification Commands**:

```bash
# Test WebSocketDefaultFunction
aws lambda invoke \
  --function-name WebSocketDefaultFunction \
  --payload '{"body": "test"}' \
  response.json

# Check response for errors
cat response.json

# Test ProcessVideoFunction
aws lambda invoke \
  --function-name ProcessVideoFunction \
  --payload '{"Records": []}' \
  response.json

# Test MonthlyResetFunction
aws lambda invoke \
  --function-name MonthlyResetFunction \
  --payload '{}' \
  response.json

# Check CloudWatch Logs for any AccessDenied errors
aws logs tail /aws/lambda/WebSocketDefaultFunction --since 5m
aws logs tail /aws/lambda/ProcessVideoFunction --since 5m
aws logs tail /aws/lambda/MonthlyResetFunction --since 5m
```

**Success Criteria**:
- ✅ All Lambda functions execute successfully
- ✅ No AccessDenied errors in CloudWatch Logs
- ✅ Functions can access DynamoDB tables
- ✅ Functions can access S3 buckets
- ✅ Functions can access required AWS services

**Rollback Procedure** (if needed):
```bash
# Rollback to previous stack version
aws cloudformation rollback-stack --stack-name soulreel-backend

# This will restore previous IAM policies
```

---

## Phase 7: Add Resource Tagging

### Step 7.1: Deploy Resource Tags

**Action**: Deploy stack update with cost tracking tags

```bash
sam deploy
```

**Expected Duration**: 1-2 minutes

### Step 7.2: Verify Resource Tags

**Verification Commands**:

```bash
# Verify KMS key tags
aws kms list-resource-tags --key-id $KEY_ID

# Expected tags:
# - Project: SoulReel
# - SecurityPhase: Phase1
# - CostCenter: Security

# Verify CloudTrail tags
aws cloudtrail list-tags --resource-id-list $TRAIL_ARN

# Verify GuardDuty tags (via CloudFormation)
aws cloudformation describe-stack-resources \
  --stack-name soulreel-backend \
  --logical-resource-id GuardDutyDetector
```

**Success Criteria**:
- ✅ All security resources have required tags
- ✅ Tags are visible in AWS Cost Explorer

---

## Phase 8: Final Verification and Testing

### Step 8.1: Run Complete Test Suite

**Action**: Execute all unit, property, and integration tests

```bash
cd SamLambda

# Run unit tests
python -m pytest tests/unit/ -v

# Run property tests (100+ iterations each)
python -m pytest tests/property/ -v

# Run integration tests
python -m pytest tests/integration/ -v
```

**Expected Duration**: 10-15 minutes

**Success Criteria**:
- ✅ All unit tests pass
- ✅ All property tests pass (100+ iterations)
- ✅ All integration tests pass

### Step 8.2: Verify End-to-End Functionality

**Action**: Test complete video upload/download flow

```bash
# Upload test video
aws s3 cp test-video.mp4 s3://virtual-legacy/test/test-video.mp4

# Verify automatic encryption
aws s3api head-object \
  --bucket virtual-legacy \
  --key test/test-video.mp4 \
  --query 'ServerSideEncryption'

# Expected output: aws:kms

# Download video
aws s3 cp s3://virtual-legacy/test/test-video.mp4 downloaded-video.mp4

# Verify content matches original
diff test-video.mp4 downloaded-video.mp4

# Test API endpoints
curl -X POST https://your-api-gateway-url/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Success Criteria**:
- ✅ Video uploads successfully with automatic encryption
- ✅ Video downloads successfully with automatic decryption
- ✅ Downloaded content matches original
- ✅ API endpoints respond normally
- ✅ Response times within 10% of baseline

### Step 8.3: Monitor CloudWatch for Errors

**Action**: Check CloudWatch Logs for any errors

```bash
# Check Lambda function logs
aws logs tail /aws/lambda/WebSocketDefaultFunction --since 1h --follow
aws logs tail /aws/lambda/ProcessVideoFunction --since 1h --follow
aws logs tail /aws/lambda/MonthlyResetFunction --since 1h --follow

# Check for KMS-related errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/WebSocketDefaultFunction \
  --filter-pattern "KMS" \
  --since 1h

# Check for AccessDenied errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessVideoFunction \
  --filter-pattern "AccessDenied" \
  --since 1h
```

**Success Criteria**:
- ✅ No KMS-related errors
- ✅ No AccessDenied errors
- ✅ No unexpected errors in logs

### Step 8.4: Verify CloudTrail is Logging

**Action**: Confirm recent operations are being logged

```bash
# Check CloudTrail for recent events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --max-results 10

# Verify events from last hour
aws cloudtrail lookup-events \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --max-results 50
```

**Success Criteria**:
- ✅ Recent S3 and DynamoDB operations appear in CloudTrail
- ✅ Events are being logged within 15 minutes

### Step 8.5: Verify GuardDuty is Active

**Action**: Check GuardDuty status and findings

```bash
# Check detector status
aws guardduty get-detector --detector-id $DETECTOR_ID

# List recent findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{"Criterion":{"updatedAt":{"Gte":'$(date -u -d '24 hours ago' +%s)000'}}}'

# Get finding details
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids <finding-id>
```

**Success Criteria**:
- ✅ GuardDuty detector is active
- ✅ No high-severity findings (except test findings)

---

## Post-Deployment Tasks

### Task 1: Update Documentation

- [ ] Update README with new security features
- [ ] Document KMS key management procedures
- [ ] Document incident response procedures
- [ ] Update runbooks with new verification commands

### Task 2: Configure Monitoring

- [ ] Set up CloudWatch alarms for KMS API costs
- [ ] Set up CloudWatch alarms for GuardDuty findings
- [ ] Configure AWS Cost Explorer tags
- [ ] Set up monthly cost reports

### Task 3: Team Communication

- [ ] Notify team of successful deployment
- [ ] Share security alert email distribution list
- [ ] Schedule security review meeting
- [ ] Document lessons learned

### Task 4: Ongoing Maintenance

- [ ] Schedule quarterly IAM policy reviews
- [ ] Schedule monthly GuardDuty findings reviews
- [ ] Schedule monthly cost reviews
- [ ] Set calendar reminder for KMS key rotation verification (annual)

---

## Rollback Procedures

### Complete Stack Rollback

If critical issues occur, rollback the entire stack:

```bash
# Rollback to previous version
aws cloudformation rollback-stack --stack-name soulreel-backend

# Monitor rollback progress
aws cloudformation describe-stack-events \
  --stack-name soulreel-backend \
  --max-items 20

# Wait for rollback to complete
aws cloudformation wait stack-rollback-complete \
  --stack-name soulreel-backend
```

### Partial Rollback

If only specific components need rollback:

**S3 Bucket Configuration**:
```bash
# Remove bucket policy
aws s3api delete-bucket-policy --bucket virtual-legacy

# Suspend versioning
aws s3api put-bucket-versioning \
  --bucket virtual-legacy \
  --versioning-configuration Status=Suspended
```

**CloudTrail**:
```bash
# Stop logging
aws cloudtrail stop-logging --name soulreel-data-access-trail

# Delete trail
aws cloudtrail delete-trail --name soulreel-data-access-trail
```

**GuardDuty**:
```bash
# Disable detector
aws guardduty update-detector \
  --detector-id $DETECTOR_ID \
  --no-enable

# Delete detector
aws guardduty delete-detector --detector-id $DETECTOR_ID
```

### Important Rollback Limitations

⚠️ **Cannot Rollback**:
- DynamoDB encryption (once encrypted with CMK, cannot revert to AWS-managed keys)
- KMS key deletion (requires 7-30 day waiting period)

⚠️ **Data Considerations**:
- CloudTrail logs will be retained in audit bucket
- S3 object versions will be retained
- DynamoDB PITR backups will be retained for 35 days

---

## Troubleshooting

### Issue: KMS Key Creation Fails

**Symptoms**: CloudFormation fails with KMS quota error

**Solution**:
```bash
# Check KMS quotas
aws service-quotas get-service-quota \
  --service-code kms \
  --quota-code L-4E3F3F3F

# Request quota increase if needed
aws service-quotas request-service-quota-increase \
  --service-code kms \
  --quota-code L-4E3F3F3F \
  --desired-value 100
```

### Issue: Lambda Functions Get AccessDenied Errors

**Symptoms**: Lambda functions fail with AccessDenied when accessing resources

**Solution**:
```bash
# Check Lambda execution role
aws iam get-role --role-name <lambda-role-name>

# Check attached policies
aws iam list-attached-role-policies --role-name <lambda-role-name>

# Check inline policies
aws iam list-role-policies --role-name <lambda-role-name>

# Add missing KMS permissions if needed
aws iam put-role-policy \
  --role-name <lambda-role-name> \
  --policy-name KMSDecryptPolicy \
  --policy-document file://kms-policy.json
```

### Issue: S3 Uploads Fail with Access Denied

**Symptoms**: Applications cannot upload to S3 bucket

**Solution**:
```bash
# Verify bucket policy
aws s3api get-bucket-policy --bucket virtual-legacy

# Verify IAM role has kms:GenerateDataKey permission
aws iam get-role-policy \
  --role-name <role-name> \
  --policy-name <policy-name>

# Test upload with encryption headers
aws s3api put-object \
  --bucket virtual-legacy \
  --key test.txt \
  --body test.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id $KEY_ARN
```

### Issue: CloudTrail Not Logging Events

**Symptoms**: No events appearing in CloudTrail logs

**Solution**:
```bash
# Check trail status
aws cloudtrail get-trail-status --name soulreel-data-access-trail

# Check bucket policy allows CloudTrail
aws s3api get-bucket-policy --bucket $AUDIT_BUCKET

# Restart logging
aws cloudtrail start-logging --name soulreel-data-access-trail

# Wait 15 minutes and check again
```

### Issue: GuardDuty Alerts Not Received

**Symptoms**: No email alerts from GuardDuty

**Solution**:
```bash
# Verify SNS subscription is confirmed
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN

# Verify EventBridge rule is enabled
aws events describe-rule --name GuardDutyAlertRule

# Test with sample finding
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types UnauthorizedAccess:S3/MaliciousIPCaller.Custom

# Check SNS topic for delivery failures
aws sns get-topic-attributes --topic-arn $TOPIC_ARN
```

---

## Support and Escalation

### Internal Support

- **DevOps Team**: For deployment and infrastructure issues
- **Security Team**: For security configuration and policy questions
- **Development Team**: For application integration issues

### AWS Support

- **AWS Support Console**: For AWS service-specific issues
- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS Forums**: For community support

### Emergency Contacts

- **On-Call Engineer**: [Contact information]
- **Security Incident Response**: [Contact information]
- **AWS TAM** (if applicable): [Contact information]

---

## Appendix

### A. Verification Checklist

See `VERIFICATION_CHECKLIST.md` for complete verification procedures.

### B. Cost Breakdown

See `SECURITY_COST_BREAKDOWN.md` for detailed cost analysis.

### C. S3 Configuration Commands

See `S3_BUCKET_CONFIGURATION.sh` for complete S3 configuration script.

### D. Compliance Mapping

| Control | Requirement | Implementation |
|---------|-------------|----------------|
| Encryption at Rest | GDPR, HIPAA | KMS CMK for all data |
| Audit Logging | GDPR, SOC 2 | CloudTrail with log validation |
| Access Controls | GDPR, CCPA | Least-privilege IAM policies |
| Threat Detection | SOC 2 | GuardDuty with alerts |
| Data Recovery | Business Continuity | PITR, versioning, backups |

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-16  
**Next Review**: 2026-03-16
