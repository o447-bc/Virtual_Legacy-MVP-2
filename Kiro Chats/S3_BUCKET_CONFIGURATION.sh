#!/bin/bash

################################################################################
# S3 Bucket Configuration Script for Phase 1 Security Hardening
#
# This script configures the existing 'virtual-legacy' S3 bucket with:
# - Customer-managed KMS encryption
# - S3 Bucket Key (reduces KMS costs by 99%)
# - Versioning
# - Public access block
# - Lifecycle policies for cost optimization
# - Bucket policy to enforce encryption
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - KMS key already created via CloudFormation
# - Permissions to modify S3 bucket configuration
#
# Usage:
#   ./S3_BUCKET_CONFIGURATION.sh
#
# Requirements: 3.1, 3.2, 3.3, 3.4, 3.7
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
BUCKET_NAME="virtual-legacy"
STACK_NAME="soulreel-backend"
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if bucket exists
log_info "Checking if bucket '$BUCKET_NAME' exists..."
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    log_error "Bucket '$BUCKET_NAME' does not exist or you don't have access."
    exit 1
fi
log_info "Bucket exists ✓"

# Get KMS key ARN from CloudFormation stack
log_info "Retrieving KMS key ARN from CloudFormation stack..."
KEY_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DataEncryptionKeyArn`].OutputValue' \
    --output text)

if [ -z "$KEY_ARN" ]; then
    log_error "Could not retrieve KMS key ARN from stack '$STACK_NAME'."
    log_error "Make sure the CloudFormation stack is deployed with the DataEncryptionKey resource."
    exit 1
fi
log_info "KMS Key ARN: $KEY_ARN ✓"

################################################################################
# Step 1: Configure Default Encryption with KMS
################################################################################

log_info "Step 1: Configuring default encryption with KMS..."

aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms",
                "KMSMasterKeyID": "'"$KEY_ARN"'"
            },
            "BucketKeyEnabled": true
        }]
    }'

log_info "Default encryption configured ✓"
log_info "  - Algorithm: aws:kms"
log_info "  - KMS Key: $KEY_ARN"
log_info "  - Bucket Key: Enabled (reduces KMS costs by 99%)"

# Verify encryption configuration
log_info "Verifying encryption configuration..."
ENCRYPTION_CONFIG=$(aws s3api get-bucket-encryption --bucket "$BUCKET_NAME")
echo "$ENCRYPTION_CONFIG" | grep -q "aws:kms" && log_info "Encryption verification passed ✓"

################################################################################
# Step 2: Enable Versioning
################################################################################

log_info "Step 2: Enabling versioning..."

aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled

log_info "Versioning enabled ✓"
log_info "  - Protects against accidental deletion"
log_info "  - Allows recovery of previous versions"

# Verify versioning
log_info "Verifying versioning configuration..."
VERSIONING_STATUS=$(aws s3api get-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --query 'Status' \
    --output text)

if [ "$VERSIONING_STATUS" = "Enabled" ]; then
    log_info "Versioning verification passed ✓"
else
    log_warn "Versioning status: $VERSIONING_STATUS"
fi

################################################################################
# Step 3: Block All Public Access
################################################################################

log_info "Step 3: Blocking all public access..."

aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        BlockPublicAcls=true,\
IgnorePublicAcls=true,\
BlockPublicPolicy=true,\
RestrictPublicBuckets=true

log_info "Public access blocked ✓"
log_info "  - BlockPublicAcls: true"
log_info "  - IgnorePublicAcls: true"
log_info "  - BlockPublicPolicy: true"
log_info "  - RestrictPublicBuckets: true"

# Verify public access block
log_info "Verifying public access block configuration..."
PUBLIC_ACCESS=$(aws s3api get-public-access-block --bucket "$BUCKET_NAME")
echo "$PUBLIC_ACCESS" | grep -q "true" && log_info "Public access block verification passed ✓"

################################################################################
# Step 4: Configure Lifecycle Policies
################################################################################

log_info "Step 4: Configuring lifecycle policies..."

# Create temporary lifecycle configuration file
LIFECYCLE_CONFIG=$(cat <<'EOF'
{
  "Rules": [
    {
      "Id": "TransitionToStandardIA",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "TransitionToGlacierIR",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
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
      "Filter": {
        "Prefix": ""
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
EOF
)

# Apply lifecycle configuration
echo "$LIFECYCLE_CONFIG" | aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration file:///dev/stdin

log_info "Lifecycle policies configured ✓"
log_info "  - Transition to STANDARD_IA after 90 days"
log_info "  - Transition to GLACIER_IR after 365 days"
log_info "  - Delete old versions after 90 days"

# Verify lifecycle configuration
log_info "Verifying lifecycle configuration..."
LIFECYCLE_RULES=$(aws s3api get-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --query 'Rules[*].Id' \
    --output text)

if echo "$LIFECYCLE_RULES" | grep -q "TransitionToStandardIA"; then
    log_info "Lifecycle configuration verification passed ✓"
else
    log_warn "Could not verify lifecycle rules"
fi

################################################################################
# Step 5: Apply Bucket Policy to Enforce Encryption
################################################################################

log_info "Step 5: Applying bucket policy to enforce encryption..."

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create bucket policy
BUCKET_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    },
    {
      "Sid": "DenyIncorrectKMSKey",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption-aws-kms-key-id": "${KEY_ARN}"
        }
      }
    }
  ]
}
EOF
)

# Apply bucket policy
echo "$BUCKET_POLICY" | aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy file:///dev/stdin

log_info "Bucket policy applied ✓"
log_info "  - Denies uploads without aws:kms encryption"
log_info "  - Denies uploads with incorrect KMS key"

# Verify bucket policy
log_info "Verifying bucket policy..."
POLICY_EXISTS=$(aws s3api get-bucket-policy --bucket "$BUCKET_NAME" 2>/dev/null)
if [ -n "$POLICY_EXISTS" ]; then
    log_info "Bucket policy verification passed ✓"
else
    log_warn "Could not verify bucket policy"
fi

################################################################################
# Summary
################################################################################

echo ""
log_info "=========================================="
log_info "S3 Bucket Configuration Complete!"
log_info "=========================================="
echo ""
log_info "Bucket: $BUCKET_NAME"
log_info "KMS Key: $KEY_ARN"
echo ""
log_info "Configuration Summary:"
log_info "  ✓ Default encryption: aws:kms with Bucket Key"
log_info "  ✓ Versioning: Enabled"
log_info "  ✓ Public access: Blocked (all 4 settings)"
log_info "  ✓ Lifecycle policies: Configured"
log_info "  ✓ Bucket policy: Enforces encryption"
echo ""
log_info "Cost Optimization:"
log_info "  - S3 Bucket Key reduces KMS API calls by 99%"
log_info "  - Lifecycle policies reduce storage costs"
log_info "  - Old versions deleted after 90 days"
echo ""
log_info "Next Steps:"
log_info "  1. Test video upload with encryption"
log_info "  2. Verify CloudTrail is logging S3 events"
log_info "  3. Monitor CloudWatch for any errors"
log_info "  4. Update application documentation"
echo ""

################################################################################
# Verification Commands
################################################################################

log_info "Verification Commands:"
echo ""
echo "# Check encryption configuration:"
echo "aws s3api get-bucket-encryption --bucket $BUCKET_NAME"
echo ""
echo "# Check versioning status:"
echo "aws s3api get-bucket-versioning --bucket $BUCKET_NAME"
echo ""
echo "# Check public access block:"
echo "aws s3api get-public-access-block --bucket $BUCKET_NAME"
echo ""
echo "# Check lifecycle policies:"
echo "aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET_NAME"
echo ""
echo "# Check bucket policy:"
echo "aws s3api get-bucket-policy --bucket $BUCKET_NAME"
echo ""
echo "# Test upload with encryption:"
echo "aws s3api put-object --bucket $BUCKET_NAME --key test.txt --body test.txt --server-side-encryption aws:kms --ssekms-key-id $KEY_ARN"
echo ""

################################################################################
# Rollback Commands
################################################################################

log_info "Rollback Commands (if needed):"
echo ""
echo "# Remove bucket policy:"
echo "aws s3api delete-bucket-policy --bucket $BUCKET_NAME"
echo ""
echo "# Suspend versioning (cannot be fully disabled):"
echo "aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Suspended"
echo ""
echo "# Remove lifecycle configuration:"
echo "aws s3api delete-bucket-lifecycle --bucket $BUCKET_NAME"
echo ""
echo "# Note: Encryption configuration cannot be removed, only changed"
echo ""

log_info "Configuration script completed successfully!"
exit 0
