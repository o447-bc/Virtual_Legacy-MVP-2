import json
from lambda_function import lambda_handler

# Mock S3 event that triggers your Lambda
mock_event = {
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": "your-test-bucket"
                },
                "object": {
                    "key": "sports.json"
                }
            }
        }
    ]
}

# Mock context (minimal for testing)
class MockContext:
    def __init__(self):
        self.function_name = "test-function"
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        self.aws_request_id = "test-request-id"

if __name__ == "__main__":
    context = MockContext()
    
    # Call your Lambda function
    result = lambda_handler(mock_event, context)
    
    print("Lambda Response:")
    print(json.dumps(result, indent=2))