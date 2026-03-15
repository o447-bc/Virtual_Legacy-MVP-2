import json
import boto3
import app

def test_get_question_types():
    """Test the getQuestionTypes function with the real DynamoDB table"""
    print("Testing getQuestionTypes function with real DynamoDB...")
    
    # Call the lambda function
    response = app.lambda_handler({}, {})
    
    # Check status code
    status_code = response['statusCode']
    print(f"Status code: {status_code}")
    
    # Parse and display the response body
    body = json.loads(response['body'])
    
    if 'questionTypes' in body:
        question_types = body['questionTypes']
        print(f"Found {len(question_types)} unique question types:")
        for qtype in sorted(question_types):
            print(f"  - {qtype}")
    else:
        print("No question types found or error in response")
        print(f"Response body: {body}")

# Direct connection to DynamoDB to verify table contents
def verify_table_contents():
    """Verify the contents of the allQuestionDB table"""
    print("\nVerifying DynamoDB table contents...")
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    try:
        # Scan the table to retrieve all items
        response = table.scan(
            ProjectionExpression='questionType'
        )
        
        # Extract unique questionTypes
        question_types = set(item['questionType'] for item in response['Items'])
        
        print(f"Direct scan found {len(question_types)} unique question types:")
        for qtype in sorted(question_types):
            print(f"  - {qtype}")
            
    except Exception as e:
        print(f"Error scanning table: {str(e)}")

if __name__ == '__main__':
    test_get_question_types()
    verify_table_contents()