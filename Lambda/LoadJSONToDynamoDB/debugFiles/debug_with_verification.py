import json
import boto3
from lambda_function import lambda_handler

# Mock event
mock_event = {
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": "virtual-legacy"
                },
                "object": {
                    "key": "questions/questionsInJSON/childhood.json"
                }
            }
        }
    ]
}

class MockContext:
    def __init__(self):
        self.function_name = "test-function"
        self.aws_request_id = "test-request-id"

if __name__ == "__main__":
    # Check current AWS config
    session = boto3.Session()
    print(f"AWS Region: {session.region_name}")
    print(f"AWS Profile: {session.profile_name}")
    
    # Run Lambda
    context = MockContext()
    result = lambda_handler(mock_event, context)
    print(f"Lambda Result: {result}")
    
    # Verify write
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    response = table.scan(Limit=5)
    print(f"\nItems in DynamoDB: {len(response['Items'])}")
    for item in response['Items']:
        print(f"- {item.get('questionId', 'NO_ID')}: {item.get('category', 'NO_CATEGORY')}")