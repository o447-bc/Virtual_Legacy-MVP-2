import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    # Print event for debugging
    print(f"Event received: {json.dumps(event)}")
    
    # Extract questionType from the event - handle different possible locations
    question_type = None
    
    # Check if questionType is directly in the event
    if 'questionType' in event:
        question_type = event['questionType']
    # Check if it's in query string parameters (API Gateway)
    elif 'queryStringParameters' in event and event['queryStringParameters'] and 'questionType' in event['queryStringParameters']:
        question_type = event['queryStringParameters']['questionType']
    # Check if it's in the body (API Gateway)
    elif 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            if 'questionType' in body:
                question_type = body['questionType']
        except:
            pass
    # Check if it's in path parameters (API Gateway)
    elif 'pathParameters' in event and event['pathParameters'] and 'questionType' in event['pathParameters']:
        question_type = event['pathParameters']['questionType']
    
    if not question_type:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Missing questionType parameter'
            })
        }
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    try:
        # Use query with a filter expression to count valid questions for the specified question type
        response = table.scan(
            FilterExpression='questionType = :qtype AND Valid = :valid',
            ExpressionAttributeValues={
                ':qtype': question_type,
                ':valid': 1
            }
        )
        
        # Count the valid questions
        valid_count = len(response['Items'])
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='questionType = :qtype AND Valid = :valid',
                ExpressionAttributeValues={
                    ':qtype': question_type,
                    ':valid': 1
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            valid_count += len(response['Items'])
        
        # Return only the count
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',  # For CORS support
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'validQuestionCount': valid_count
            })
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'error': f"Error accessing DynamoDB: {str(e)}"
            })
        }

