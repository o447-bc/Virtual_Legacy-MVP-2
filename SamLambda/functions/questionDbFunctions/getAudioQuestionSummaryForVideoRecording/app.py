import os
"""
Get Audio Question Summary For Video Recording Lambda Function

Fetches the LLM-generated detailedSummary from userQuestionStatusDB
to display as a prompt when user records a video memory after audio conversation.

Author: Virtual Legacy Team
Version: 1.0
"""

import json
import boto3
from cors import cors_headers
from responses import error_response


def lambda_handler(event, context):
    """
    Fetch detailedSummary from userQuestionStatusDB for video memory recording prompt.
    
    Args:
        event: API Gateway event with questionId in body
        context: Lambda context
    
    Returns:
        dict: HTTP response with detailedSummary field
    """
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    # Extract user ID from JWT
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Parse request body
        body = json.loads(event['body'])
        question_id = body.get('questionId')
        
        if not question_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'questionId is required'})
            }
        
        # Query DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        
        response = table.get_item(
            Key={
                'userId': user_id,
                'questionId': question_id
            }
        )
        
        # Extract audioDetailedSummary
        if 'Item' in response:
            detailed_summary = response['Item'].get('audioDetailedSummary', '')
        else:
            detailed_summary = ''
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'audioDetailedSummary': detailed_summary})
        }
        
    except Exception as e:
        print(f"Error fetching summary: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Failed to fetch summary. Please try again.'})
        }
