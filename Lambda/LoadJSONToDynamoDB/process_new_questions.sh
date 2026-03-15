#!/bin/bash

echo "=========================================="
echo "Process New Questions Manually"
echo "=========================================="
echo ""
echo "This script will manually trigger the Lambda function to process"
echo "all JSON files in s3://virtual-legacy/questions/questionsInJSON/"
echo ""
echo "⚠️  WARNING: This does NOT delete existing records in allQuestionDB"
echo "   If you have duplicates, you'll need to manually delete them from"
echo "   the DynamoDB console first."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Finding Lambda function..."
FUNCTION_NAME=$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'LoadJSON')].FunctionName" --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Lambda function not found in AWS"
    echo ""
    echo "Falling back to local execution..."
    echo ""
    
    # Check if we have AWS credentials configured
    if ! aws sts get-caller-identity &>/dev/null; then
        echo "❌ AWS credentials not configured"
        exit 1
    fi
    
    # Run the local test script
    echo "Running local processing script..."
    cd "$(dirname "$0")"
    python test_process_all.py
    
else
    echo "✅ Found function: $FUNCTION_NAME"
    echo ""
    echo "Invoking Lambda function..."
    
    # Create event payload
    EVENT_PAYLOAD='{
      "processAll": true,
      "bucket": "virtual-legacy",
      "prefix": "questions/questionsInJSON/"
    }'
    
    # Invoke Lambda
    aws lambda invoke \
      --function-name "$FUNCTION_NAME" \
      --payload "$EVENT_PAYLOAD" \
      --cli-binary-format raw-in-base64-out \
      /tmp/lambda-response.json
    
    echo ""
    echo "Response:"
    cat /tmp/lambda-response.json | jq '.'
    echo ""
    
    # Check CloudWatch logs
    echo "Recent CloudWatch logs:"
    aws logs tail /aws/lambda/$FUNCTION_NAME --since 1m
    
    rm -f /tmp/lambda-response.json
fi

echo ""
echo "=========================================="
echo "✅ Processing Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify questions in DynamoDB console"
echo "2. Run diagnose_trigger.sh to check S3 trigger configuration"
echo "3. Run fix_trigger.sh if S3 trigger is not configured"
echo ""
