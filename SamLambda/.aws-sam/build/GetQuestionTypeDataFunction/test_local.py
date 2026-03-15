import json
import app

def test_lambda_locally():
    """
    Test the lambda_handler function locally by connecting to the actual AWS DynamoDB.
    Make sure your AWS credentials are properly configured in your environment.
    """
    # Create a mock event and context
    event = {}
    context = {}
    
    # Call the lambda handler
    response = app.lambda_handler(event, context)
    
    # Print the response in a readable format
    status_code = response['statusCode']
    print(f"Status Code: {status_code}")
    
    if status_code == 200:
        body = json.loads(response['body'])
        print("\nResponse Body:")
        print(json.dumps(body, indent=2))
        
        # Print some summary information
        print(f"\nTotal unique question types: {body['uniqueQuestionTypesCount']}")
        
        # Print a table of question types, friendly names, and valid question counts
        print("\nQuestion Type Data:")
        print("-" * 80)
        print(f"{'Question Type':<20} | {'Friendly Name':<20} | {'Valid Questions':<15}")
        print("-" * 80)
        
        for i in range(len(body['questionTypes'])):
            q_type = body['questionTypes'][i]
            friendly = body['friendlyNames'][i]
            valid_count = body['numValidQuestions'][i]
            print(f"{q_type:<20} | {friendly:<20} | {valid_count:<15}")
    else:
        print(f"Error: {response['body']}")

if __name__ == "__main__":
    test_lambda_locally()