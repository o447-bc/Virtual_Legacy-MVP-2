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

# First, let's see what's actually in the S3 file
s3 = boto3.client('s3')
try:
    response = s3.get_object(Bucket='virtual-legacy', Key='questions/questionsInJSON/childhood.json')
    body = response['Body'].read().decode('utf-8')
    data = json.loads(body)
    
    print("=== S3 FILE CONTENTS ===")
    print(json.dumps(data, indent=2))
    print(f"\nData type: {type(data)}")
    
    if isinstance(data, list):
        print(f"Number of items: {len(data)}")
        for i, item in enumerate(data):
            print(f"Item {i}: {list(item.keys())}")
            if 'questionId' not in item:
                print(f"  ❌ Missing questionId in item {i}")
    else:
        print(f"Single item keys: {list(data.keys())}")
        if 'questionId' not in data:
            print("❌ Missing questionId in single item")
    
except Exception as e:
    print(f"Error reading S3 file: {e}")

print("\n=== RUNNING LAMBDA ===")
context = MockContext()
result = lambda_handler(mock_event, context)
print(f"Result: {result}")