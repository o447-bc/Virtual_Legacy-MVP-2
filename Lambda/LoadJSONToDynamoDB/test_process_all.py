import json
from lambda_function import lambda_handler

# Test event to process all files
test_event = {
    "processAll": True,
    "bucket": "virtual-legacy",
    "prefix": "questions/questionsInJSON/"
}

class MockContext:
    def __init__(self):
        self.function_name = "test-function"
        self.aws_request_id = "test-request-id"

if __name__ == "__main__":
    context = MockContext()
    result = lambda_handler(test_event, context)
    print(f"Result: {result}")