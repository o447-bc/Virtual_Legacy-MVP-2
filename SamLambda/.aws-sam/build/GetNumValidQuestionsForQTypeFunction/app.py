import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # Extract questionType from the event - check common locations
    question_type = None
    
    # Check query string parameters (most common for GET requests)
    if event.get('queryStringParameters') and event['queryStringParameters'].get('questionType'):
        question_type = event['queryStringParameters']['questionType']
    # Check direct event parameter
    elif event.get('questionType'):
        question_type = event['questionType']
    
    if not question_type:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Missing questionType parameter'
            })
        }
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    try:
        # Use scan with a filter expression to count valid questions for the specified question type
        # Support both new structure (active=true) and legacy structure (Valid=1)
        response = table.scan(
            FilterExpression='questionType = :qtype AND (active = :active_true OR Valid = :valid)',
            ExpressionAttributeValues={
                ':qtype': question_type,
                ':active_true': True,
                ':valid': 1
            }
        )
        
        # Count the valid questions
        valid_count = len(response['Items'])
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='questionType = :qtype AND (active = :active_true OR Valid = :valid)',
                ExpressionAttributeValues={
                    ':qtype': question_type,
                    ':active_true': True,
                    ':valid': 1
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            valid_count += len(response['Items'])
        
        # Return only the count
        return {
            'statusCode': 200,
            'body': json.dumps({
                'validQuestionCount': valid_count
            })
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Error accessing DynamoDB: {str(e)}"
            })
        }