# LoadJSONToDynamoDB Lambda Debugging Guide

## Problem - RESOLVED ✅
New JSON files uploaded to `s3://virtual-legacy/questions/questionsInJSON/` were not appearing in the allQuestionDB DynamoDB table.

## Root Cause
The Lambda function WAS being triggered correctly by S3 events, but it was failing because the JSON file structure changed. The Lambda expected a flat structure with `questionId` and `questionType` at the top level, but the new JSON files have a nested structure:

```json
{
  "themeId": "values",
  "themeName": "Values & Guiding Principles",
  "questions": [
    {
      "questionId": "Values-1",
      "difficulty": 7,
      "text": "What is one value...",
      "active": true
    }
  ]
}
```

## Solution Applied
Updated the Lambda function to handle both the legacy flat structure and the new nested structure. The function now:
1. Detects if the JSON has `themeId` and `questions` array
2. Extracts each question from the array
3. Creates DynamoDB items with:
   - `questionId`: Formatted with leading zeros (e.g., "Values-00001")
   - `questionType`: Derived from `themeId`
   - `questionText`: From the `text` field
   - `difficulty`: Question difficulty level
   - `active`: Whether the question is active
   - `themeName`: Human-readable theme name

## Results
- Lambda function updated and deployed successfully
- Processed 12 JSON files with 282 total questions
- All questions now in allQuestionDB table (299 total items including existing data)
- S3 trigger is working correctly

## Verification
Sample question in DynamoDB:
```json
{
  "questionId": "Values-00001",
  "questionType": "values",
  "questionText": "What is one value or principle you hold very dear — where do you think it came from?",
  "difficulty": 7,
  "active": true,
  "themeName": "Values & Guiding Principles"
}
```

## Future Uploads
The Lambda will now automatically process new JSON files when uploaded to `s3://virtual-legacy/questions/questionsInJSON/` with either structure format.

## How It Was Fixed

1. **Diagnosed the issue**: Checked CloudWatch logs and found the Lambda was being triggered but failing with "questionId missing" errors
2. **Identified root cause**: JSON structure mismatch between what Lambda expected and what was uploaded
3. **Updated Lambda code**: Modified `Lambda/LoadJSONToDynamoDB/lambda_function.py` to handle the new nested structure
4. **Deployed update**: Created deployment package and updated Lambda function in AWS
5. **Processed files**: Manually invoked Lambda to process all existing JSON files
6. **Verified**: Confirmed 282 questions successfully loaded into DynamoDB

## For Future Reference

If you need to manually process files again:

```bash
# Invoke Lambda to process all files
aws lambda invoke \
  --function-name LoadJSONToDynamoDB \
  --payload '{"processAll": true, "bucket": "virtual-legacy", "prefix": "questions/questionsInJSON/"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json && cat /tmp/response.json
```

Or use the local test script:
```bash
cd Lambda/LoadJSONToDynamoDB
python test_process_all.py
```
