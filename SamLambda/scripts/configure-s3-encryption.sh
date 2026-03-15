#!/bin/bash

# S3 Bucket Encryption Configuration Script
# Configures the virtual-legacy bucket with KMS encryption, versioning, and security settings
# Requirements: 3.1, 3.2, 3.3, 3.4

set -e  # Exit on error

# Configuration
BUCKET_NAME="virtual-legacy"
REGION="us-east-1"
KMS_ALIAS="alias/soulreel-data-encryption"

echo "=========================================="
echo "S3 Bucket Encryption Configuration"
echo "=========================================="
echo "Bucket: $BUCKET_NAME"
echo "Region: $REGION"
echo "KMS Alias: $KMS_ALIAS"
echo ""

# Get KMS Key ARN from alias
echo "Step 1: Retrieving KMS Key ARN..."
KMS_KEY_ARN=$(aws kms describe-key --key-id "$KMS_ALIAS" --region "$REGION" --query 'KeyMetadata.Arn' --output text)

if [ -z "$KMS_KEY_ARN" ]; then
    echo "ERROR: Could not retrieve KMS key ARN for alias $KMS_ALIAS"
    echo "Please ensure the KMS key has been created via CloudFormation deployment."
    exit 1
fi

echo "✓ KMS Key ARN: $KMS_KEY_ARN"
echo ""

# Configure default encryption with KMS
echo "Step 2: Configuring default encryption with KMS..."
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "'"$KMS_KEY_ARN"'"
                },
                "BucketKeyEnabled": true
            }
        ]
    }' \
    --region "$REGION"

echo "✓ Default encryption configured with KMS"
echo "✓ S3 Bucket Key enabled (reduces KMS API costs by 99%)"
echo ""

# Enable versioning
echo "Step 3: Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled \
    --region "$REGION"

echo "✓ Versioning enabled"
echo ""

# Configure public access block (all 4 settings)
echo "Step 4: Configuring public access block..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        BlockPublicAcls=true,\
IgnorePublicAcls=true,\
BlockPublicPolicy=true,\
RestrictPublicBuckets=true \
    --region "$REGION"

echo "✓ Public access blocked (all 4 settings enabled)"
echo ""

# Verify configuration
echo "=========================================="
echo "Verification"
echo "=========================================="

echo "Verifying encryption configuration..."
ENCRYPTION_CONFIG=$(aws s3api get-bucket-encryption --bucket "$BUCKET_NAME" --region "$REGION" 2>&1)
if echo "$ENCRYPTION_CONFIG" | grep -q "aws:kms"; then
    echo "✓ Encryption: KMS configured"
else
    echo "✗ Encryption: Configuration may have failed"
fi

echo "Verifying versioning..."
VERSIONING_STATUS=$(aws s3api get-bucket-versioning --bucket "$BUCKET_NAME" --region "$REGION" --query 'Status' --output text)
if [ "$VERSIONING_STATUS" = "Enabled" ]; then
    echo "✓ Versioning: Enabled"
else
    echo "✗ Versioning: Not enabled (status: $VERSIONING_STATUS)"
fi

echo "Verifying public access block..."
PUBLIC_ACCESS=$(aws s3api get-public-access-block --bucket "$BUCKET_NAME" --region "$REGION" 2>&1)
if echo "$PUBLIC_ACCESS" | grep -q "true"; then
    echo "✓ Public Access: Blocked"
else
    echo "✗ Public Access: Configuration may have failed"
fi

echo ""
echo "=========================================="
echo "Configuration Complete"
echo "=========================================="
echo "The virtual-legacy bucket has been configured with:"
echo "  • KMS encryption with customer-managed key"
echo "  • S3 Bucket Key enabled (cost optimization)"
echo "  • Versioning enabled (data protection)"
echo "  • Public access blocked (security)"
echo ""
echo "Note: Existing objects are NOT automatically re-encrypted."
echo "New objects will be encrypted automatically with the KMS key."
echo "=========================================="
