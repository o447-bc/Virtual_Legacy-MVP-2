#!/bin/bash

echo "=========================================="
echo "LoadJSONToDynamoDB Lambda Diagnostics"
echo "=========================================="
echo ""

# Step 1: Check if Lambda function exists
echo "1. Checking if Lambda function exists..."
FUNCTION_NAME=$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'LoadJSON')].FunctionName" --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo "   ❌ Lambda function not found in AWS"
    echo "   Action: Deploy the Lambda function first"
    echo ""
    echo "   To deploy:"
    echo "   cd Lambda/LoadJSONToDynamoDB"
    echo "   ./deploy.sh"
    echo "   Then manually upload the zip file to AWS Lambda Console"
    exit 1
else
    echo "   ✅ Found Lambda function: $FUNCTION_NAME"
fi
echo ""

# Step 2: Get Lambda ARN
echo "2. Getting Lambda ARN..."
LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)
echo "   ARN: $LAMBDA_ARN"
echo ""

# Step 3: Check S3 event notification
echo "3. Checking S3 event notification configuration..."
S3_CONFIG=$(aws s3api get-bucket-notification-configuration --bucket virtual-legacy 2>&1)

if echo "$S3_CONFIG" | grep -q "LoadJSON"; then
    echo "   ✅ S3 trigger configuration found"
    echo "$S3_CONFIG" | jq '.LambdaFunctionConfigurations[] | select(.LambdaFunctionArn | contains("LoadJSON"))'
else
    echo "   ❌ No S3 trigger configured for LoadJSONToDynamoDB"
    echo "   Action: Configure S3 event notification (see fix script)"
fi
echo ""

# Step 4: Check Lambda permissions
echo "4. Checking Lambda permissions..."
POLICY=$(aws lambda get-policy --function-name "$FUNCTION_NAME" 2>&1)

if echo "$POLICY" | grep -q "s3.amazonaws.com"; then
    echo "   ✅ S3 has permission to invoke Lambda"
else
    echo "   ❌ S3 does not have permission to invoke Lambda"
    echo "   Action: Add Lambda permission (see fix script)"
fi
echo ""

# Step 5: Check recent CloudWatch logs
echo "5. Checking recent CloudWatch logs..."
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"
RECENT_LOGS=$(aws logs describe-log-streams \
    --log-group-name "$LOG_GROUP" \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --query 'logStreams[0].lastEventTimestamp' \
    --output text 2>&1)

if [ "$RECENT_LOGS" != "None" ] && [ "$RECENT_LOGS" != "" ]; then
    LAST_EVENT=$(date -r $((RECENT_LOGS / 1000)) 2>/dev/null || echo "Unknown")
    echo "   Last log event: $LAST_EVENT"
else
    echo "   ⚠️  No recent log events found"
    echo "   This suggests the Lambda has not been invoked recently"
fi
echo ""

# Step 6: List recent files in S3
echo "6. Checking recent files in S3 bucket..."
aws s3 ls s3://virtual-legacy/questions/questionsInJSON/ --recursive | tail -5
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
if [ -z "$FUNCTION_NAME" ]; then
    echo "Status: ❌ Lambda function not deployed"
elif echo "$S3_CONFIG" | grep -q "LoadJSON"; then
    echo "Status: ✅ Everything appears configured"
    echo "Next: Check CloudWatch logs for errors"
else
    echo "Status: ⚠️  Lambda exists but S3 trigger not configured"
    echo "Next: Run fix_trigger.sh to configure S3 event notification"
fi
echo ""
