import json
import boto3
from lambda_function import lambda_handler

def process_all_json_files():
    s3 = boto3.client('s3')
    bucket = 'virtual-legacy'
    prefix = 'questions/questionsInJSON/'
    
    # List all objects in the folder
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    
    if 'Contents' not in response:
        print("No files found")
        return
    
    # Filter for .json files
    json_files = [obj['Key'] for obj in response['Contents'] 
                  if obj['Key'].endswith('.json')]
    
    print(f"Found {len(json_files)} JSON files:")
    for file_key in json_files:
        print(f"  - {file_key}")
    
    # Process each file
    class MockContext:
        def __init__(self):
            self.function_name = "test-function"
            self.aws_request_id = "test-request-id"
    
    context = MockContext()
    
    for file_key in json_files:
        print(f"\n=== Processing {file_key} ===")
        
        # Create mock event for this file
        mock_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket},
                        "object": {"key": file_key}
                    }
                }
            ]
        }
        
        # Process the file
        result = lambda_handler(mock_event, context)
        print(f"Result: {result['statusCode']}")
        
        if result['statusCode'] != 200:
            print(f"Error processing {file_key}: {result['body']}")

if __name__ == "__main__":
    process_all_json_files()