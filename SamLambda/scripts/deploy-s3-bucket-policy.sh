#!/bin/bash

# S3 Bucket Policy Deployment Script
# Deploys CloudFormation stack to enforce encryption on virtual-legacy bucket
# Requirements: 3.5, 3.6

set -e  # Exit on error

# Configuration
STACK_NAME="soulreel-s3-bucket-policy"
TEMPLATE_FILE="s3-bucket-policy-stack.yml"
BUCKET_NAME="virtual-legacy"
REGION="us-east-1"
KMS_ALIAS="alias/soulreel-data-encryption"

echo "=========================================="
echo "S3 Bucket Policy Deployment"
echo "=========================================="
echo "Stack Name: $STACK_NAME"
echo "Bucket: $BUCKET_NAME"
echo "Region: $REGION"
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

# Check if stack exists
echo "Step 2: Checking if stack exists..."
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" 2>&1 || true)

if echo "$STACK_EXISTS" | grep -q "does not exist"; then
    echo "Stack does not exist. Creating new stack..."
    OPERATION="create-stack"
else
    echo "Stack exists. Updating stack..."
    OPERATION="update-stack"
fi
echo ""

# Deploy stack
echo "Step 3: Deploying CloudFormation stack..."
if [ "$OPERATION" = "create-stack" ]; then
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --parameters \
            ParameterKey=BucketName,ParameterValue="$BUCKET_NAME" \
            ParameterKey=KMSKeyArn,ParameterValue="$KMS_KEY_ARN" \
        --region "$REGION"
    
    echo "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"
else
    # Try to update, but handle "no updates" case
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://"$TEMPLATE_FILE" \
        --parameters \
            ParameterKey=BucketName,ParameterValue="$BUCKET_NAME" \
            ParameterKey=KMSKeyArn,ParameterValue="$KMS_KEY_ARN" \
        --region "$REGION" 2>&1 || true)
    
    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
        echo "✓ No updates needed - stack is already up to date"
    else
        echo "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    fi
fi

echo "✓ Stack deployment complete"
echo ""

# Verify deployment
echo "=========================================="
echo "Verification"
echo "=========================================="

STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text)

echo "Stack Status: $STACK_STATUS"

if [[ "$STACK_STATUS" == *"COMPLETE"* ]]; then
    echo "✓ Stack deployment successful"
    
    # Get outputs
    echo ""
    echo "Stack Outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output table
else
    echo "✗ Stack deployment may have failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo "The bucket policy has been deployed to enforce:"
echo "  • All uploads must use aws:kms encryption"
echo "  • All uploads must use the correct KMS key"
echo "  • Uploads without proper encryption will be denied"
echo ""
echo "Note: Ensure Lambda functions have kms:GenerateDataKey"
echo "      permission to upload objects successfully."
echo "=========================================="
