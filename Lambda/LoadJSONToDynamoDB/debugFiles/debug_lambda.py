import json
import pdb
from lambda_function import lambda_handler

# Mock event with your test data
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
    context = MockContext()
    
    # Set breakpoint here to step through
   # pdb.set_trace()
    
    result = lambda_handler(mock_event, context)
    print(f"Result: {result}")