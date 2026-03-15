import json
import boto3
import app

def test_valid_question_counts():
    """
    Test the lambda_handler function with different question types.
    This test directly calls the function and prints the results.
    """
    question_types = ["childhood", "schooling", "values"]
    
    print("Testing getNumValidQuestionsForQType function:")
    print("-" * 50)
    
    for q_type in question_types:
        # Create mock event with the question type
        event = {"questionType": q_type}
        
        # Call the lambda handler
        response = app.lambda_handler(event, None)
        
        # Parse and print the results
        if response['statusCode'] == 200:
            result = json.loads(response['body'])
            print(f"Question Type: {q_type}")
            print(f"Valid Question Count: {result['validQuestionCount']}")
        else:
            error = json.loads(response['body'])
            print(f"Error for {q_type}: {error['error']}")
        
        print("-" * 50)

if __name__ == "__main__":
    # Set up local AWS credentials if testing locally
    # This assumes you have AWS credentials configured
    # that have permission to access the allQuestionDB table
    
    test_valid_question_counts()