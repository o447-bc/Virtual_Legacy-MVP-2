import json
import app

def test_lambda_locally():
    """Test the getQuestionById function locally."""
    
    # Test with a valid question ID
    event = {
        'queryStringParameters': {
            'questionId': 'schooling-00004'
        }
    }
    context = {}
    
    response = app.lambda_handler(event, context)
    
    print(f"Status Code: {response['statusCode']}")
    print(f"Headers: {response['headers']}")
    
    if response['statusCode'] == 200:
        body = json.loads(response['body'])
        print(f"Question: {body.get('question')}")
        print(f"Question Type: {body.get('questionType')}")
    else:
        print(f"Error: {response['body']}")

if __name__ == "__main__":
    test_lambda_locally()