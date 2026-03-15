import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    try:
        # Scan the table to retrieve all items
        response = table.scan(
            ProjectionExpression='questionType'  # Only fetch the sort key
        )
        
        # Extract unique questionTypes
        question_types = set(item['questionType'] for item in response['Items'])
        count = len(question_types)
        
        # Prepare the response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'uniqueQuestionTypesCount': count,
                'questionTypes': list(question_types)
            })
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Error accessing DynamoDB: {str(e)}"
            })
        }
    
