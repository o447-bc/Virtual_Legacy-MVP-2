import os
import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from cors import cors_headers
from responses import error_response


# Custom JSON encoder to handle DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    # Extract questionId from query parameters
    question_id = None
    
    if event.get('queryStringParameters'):
        question_id = event['queryStringParameters'].get('questionId')
    else:
        question_id = event.get('questionId')
    
    if not question_id:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Missing required parameter: questionId'
            }, cls=DecimalEncoder)
        }
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB'))
        
        # Get the specific question by ID
        # First try to scan for the question since we're not sure of the key structure
        response = table.scan(
            FilterExpression='questionId = :qid',
            ExpressionAttributeValues={
                ':qid': question_id
            }
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Question not found'
                }, cls=DecimalEncoder)
            }
        
        item = response['Items'][0]  # Get the first (and should be only) match
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'question': item.get('Question')
            }, cls=DecimalEncoder)
        }
        
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'A server error occurred. Please try again.'
            }, cls=DecimalEncoder)
        }