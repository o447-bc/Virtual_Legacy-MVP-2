#!/bin/bash

set -e

echo "=========================================="
echo "Fix LoadJSONToDynamoDB S3 Trigger"
echo "=========================================="
echo ""

# Get Lambda function name
echo "Finding Lambda function..."
FUNCTION_NAME=$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'LoadJSON')].FunctionName" --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Error: Lambda function not found"
    echo "Please deploy the Lambda function first"
    exit 1
fi

echo "✅ Found function: $FUNCTION_NAME"
echo ""

# Get Lambda ARN
echo "Getting Lambda ARN..."
LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)
echo "✅ ARN: $LAMBDA_ARN"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ Account ID: $ACCOUNT_ID"
echo ""

# Step 1: Add permission for S3 to invoke Lambda
echo "Step 1: Adding S3 invoke permission to Lambda..."
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id s3-trigger-permission-questions \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::virtual-legacy \
  --source-account "$ACCOUNT_ID" 2>&1 || echo "   (Permission may already exist)"
echo "✅ Permission added"
echo ""

# Step 2: Get existing S3 notification configuration
echo "Step 2: Getting existing S3 notification configuration..."
EXISTING_CONFIG=$(aws s3api get-bucket-notification-configuration --bucket virtual-legacy)
echo "✅ Retrieved existing configuration"
echo ""

# Step 3: Create new notification configuration
echo "Step 3: Creating new notification configuration..."
cat > /tmp/s3-notification-new.json << EOF
{
  "Id": "LoadJSONToDynamoDB-Trigger",
  "LambdaFunctionArn": "$LAMBDA_ARN",
  "Events": ["s3:ObjectCreated:*"],
  "Filter": {
    "Key": {
      "FilterRules": [
        {
          "Name": "prefix",
          "Value": "questions/questionsInJSON/"
        },
        {
          "Name": "suffix",
          "Value": ".json"
        }
      ]
    }
  }
}
EOF

# Merge with existing configuration
echo "$EXISTING_CONFIG" | jq --argjson new "$(cat /tmp/s3-notification-new.json)" \
  '.LambdaFunctionConfigurations += [$new]' > /tmp/s3-notification-merged.json

echo "✅ Configuration prepared"
echo ""

# Step 4: Apply the notification configuration
echo "Step 4: Applying S3 notification configuration..."
aws s3api put-bucket-notification-configuration \
  --bucket virtual-legacy \
  --notification-configuration file:///tmp/s3-notification-merged.json

echo "✅ S3 trigger configured successfully"
echo ""

# Step 5: Verify configuration
echo "Step 5: Verifying configuration..."
aws s3api get-bucket-notification-configuration --bucket virtual-legacy | \
  jq '.LambdaFunctionConfigurations[] | select(.LambdaFunctionArn | contains("LoadJSON"))'
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "The Lambda function will now be triggered automatically when"
echo "JSON files are uploaded to s3://virtual-legacy/questions/questionsInJSON/"
echo ""
echo "To test:"
echo "1. Upload a test JSON file to the S3 bucket"
echo "2. Check CloudWatch logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "3. Verify data in DynamoDB table: allQuestionDB"
echo ""

# Clean up temp files
rm -f /tmp/s3-notification-new.json /tmp/s3-notification-merged.json
