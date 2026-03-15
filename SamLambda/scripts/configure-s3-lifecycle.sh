#!/bin/bash

# S3 Lifecycle Policy Configuration Script
# Configures lifecycle rules for cost optimization on virtual-legacy bucket
# Requirements: 3.7

set -e  # Exit on error

# Configuration
BUCKET_NAME="virtual-legacy"
REGION="us-east-1"

echo "=========================================="
echo "S3 Lifecycle Policy Configuration"
echo "=========================================="
echo "Bucket: $BUCKET_NAME"
echo "Region: $REGION"
echo ""

# Create lifecycle configuration JSON
LIFECYCLE_CONFIG='{
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
}'

echo "Step 1: Applying lifecycle configuration..."
echo "$LIFECYCLE_CONFIG" | aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration file:///dev/stdin \
    --region "$REGION"

echo "✓ Lifecycle configuration applied"
echo ""

# Verify configuration
echo "=========================================="
echo "Verification"
echo "=========================================="

echo "Retrieving lifecycle configuration..."
CURRENT_CONFIG=$(aws s3api get-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" 2>&1)

if echo "$CURRENT_CONFIG" | grep -q "TransitionToStandardIA"; then
    echo "✓ Rule 1: Transition to STANDARD_IA after 90 days - Configured"
else
    echo "✗ Rule 1: Configuration may have failed"
fi

if echo "$CURRENT_CONFIG" | grep -q "TransitionToGlacierIR"; then
    echo "✓ Rule 2: Transition to GLACIER_IR after 365 days - Configured"
else
    echo "✗ Rule 2: Configuration may have failed"
fi

if echo "$CURRENT_CONFIG" | grep -q "DeleteOldVersions"; then
    echo "✓ Rule 3: Delete old versions after 90 days - Configured"
else
    echo "✗ Rule 3: Configuration may have failed"
fi

echo ""
echo "=========================================="
echo "Configuration Complete"
echo "=========================================="
echo "Lifecycle policies configured:"
echo "  • Current versions → STANDARD_IA after 90 days"
echo "  • Current versions → GLACIER_IR after 365 days"
echo "  • Old versions deleted after 90 days"
echo ""
echo "Cost Optimization Benefits:"
echo "  • STANDARD_IA: ~50% cheaper than STANDARD"
echo "  • GLACIER_IR: ~70% cheaper than STANDARD"
echo "  • Version cleanup: Reduces storage costs"
echo ""
echo "Note: Lifecycle transitions are applied automatically"
echo "      by AWS based on object age."
echo "=========================================="
