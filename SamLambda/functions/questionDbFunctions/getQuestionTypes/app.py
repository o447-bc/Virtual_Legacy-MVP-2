# Import required libraries
import json  # For JSON serialization/deserialization
import boto3  # AWS SDK for Python
from botocore.exceptions import ClientError  # For handling AWS service errors

# Lambda function handler
# This function retrieves all unique question types from the allQuestionDB table
# Returns a JSON response with an array of unique question types
def lambda_handler(event, context):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB'))
    
    try:
        # Scan the table to retrieve all items
        # Using ProjectionExpression to only fetch the questionType attribute to minimize data transfer
        response = table.scan(
            ProjectionExpression='questionType'  # Only fetch the questionType attribute
        )
        
        # Extract unique questionTypes using a set comprehension to eliminate duplicates
        question_types = set(item['questionType'] for item in response['Items'])
        
        # Prepare the response with HTTP 200 status code
        # Convert set to list for JSON serialization and include in response body
        return {
            'statusCode': 200,  # Success status code
            'body': json.dumps({
                'questionTypes': list(question_types)  # Convert set to list for JSON serialization
            })
        }
    except ClientError as e:
        # Handle AWS service errors with appropriate error message
        # Return HTTP 500 status code to indicate server error
        return {
            'statusCode': 500,  # Internal server error status code
            'body': json.dumps({
                'error': 'Failed to retrieve question types. Please try again.'
            })
        }
    
