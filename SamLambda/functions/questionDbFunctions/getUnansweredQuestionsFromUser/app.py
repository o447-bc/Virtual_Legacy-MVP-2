import json
import boto3
import sys
import os
from botocore.exceptions import ClientError

# Temporarily disable persona validation
# from shared.persona_validator import PersonaValidator

def lambda_handler(event, context):
    print(f"Event: {json.dumps(event)}")
    
    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': ''
        }
    
    # Extract authenticated user ID from JWT claims
    authenticated_user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    print(f"Authenticated user ID: {authenticated_user_id}")
    
    if not authenticated_user_id:
        print("No authenticated user ID found in token")
        return {
            'statusCode': 401,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Unauthorized: No user ID in token'
            })
        }
    
    # Extract parameters from the event
    thisQuestionType = None
    thisUserId = None
    
    # Check query string parameters
    if event.get('queryStringParameters'):
        thisQuestionType = event['queryStringParameters'].get('questionType')
        thisUserId = event['queryStringParameters'].get('userId')
    # Check direct event parameters
    else:
        thisQuestionType = event.get('questionType')
        thisUserId = event.get('userId')
    
    if not thisQuestionType or not thisUserId:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Missing required parameters: questionType and userId'
            })
        }
    
    # Use authenticated user ID from token instead of parameter for security
    # User data isolation enforced by using authenticated user ID
    try:
        print(f"Calling get_unanswered_questions with questionType: {thisQuestionType}, userId: {authenticated_user_id}")
        validQuestionIds = get_unanswered_questions(thisQuestionType, authenticated_user_id)
        
        # Create response
        response_body = {'unansweredQuestionIds': validQuestionIds}
        print(f"Returning {len(validQuestionIds)} unanswered questions")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_body)
        }
    except ClientError as e:
        print(f"DynamoDB ClientError: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Database error. Please try again.'
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'An unexpected error occurred. Please try again.'
            })
        }

def validate_basic_input(userId):
    """Basic input validation for userId parameter.
    
    Args:
        userId (str): The user ID from request parameters
        
    Raises:
        ValueError: If userId is invalid
    """
    if not userId or not isinstance(userId, str) or len(userId.strip()) == 0:
        raise ValueError("Invalid userId provided")

def get_unanswered_questions(thisQuestionType, thisUserId):
    """Get question IDs that match the question type and are not yet answered by the user.
    
    Args:
        thisQuestionType (str): The type of questions to retrieve
        thisUserId (str): The user ID to check against
        
    Returns:
        list: List of question IDs that are valid and not yet answered by the user
    """
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    question_table = dynamodb.Table('allQuestionDB')
    user_status_table = dynamodb.Table('userQuestionStatusDB')
    
    # 1. Get all valid questions of the specified type from allQuestionDB using GSI
    validQuestionIds = []
    question_response = question_table.query(
        IndexName='questionTypeIndex',
        KeyConditionExpression='questionType = :qType AND Valid = :valid',
        ExpressionAttributeValues={
            ':qType': thisQuestionType,
            ':valid': 1
        }
    )
    
    # Extract just the questionId values
    for item in question_response['Items']:
        if 'questionId' in item:
            validQuestionIds.append(item['questionId'])
    
    # Handle pagination if necessary
    while 'LastEvaluatedKey' in question_response:
        question_response = question_table.query(
            IndexName='questionTypeIndex',
            KeyConditionExpression='questionType = :qType AND Valid = :valid',
            ExpressionAttributeValues={
                ':qType': thisQuestionType,
                ':valid': 1
            },
            ExclusiveStartKey=question_response['LastEvaluatedKey']
        )
        for item in question_response['Items']:
            if 'questionId' in item:
                validQuestionIds.append(item['questionId'])
    
    # 2. Get all answered questions for this user from userQuestionStatusDB with the specified question type
    currAnsweredQuestions = []
    user_response = user_status_table.query(
        KeyConditionExpression='userId = :uid',
        FilterExpression='questionType = :qType',
        ExpressionAttributeValues={
            ':uid': thisUserId,
            ':qType': thisQuestionType
        }
    )
    
    # Extract just the questionId values
    for item in user_response['Items']:
        if 'questionId' in item:
            currAnsweredQuestions.append(item['questionId'])
    
    # Handle pagination if necessary
    while 'LastEvaluatedKey' in user_response:
        user_response = user_status_table.query(
            KeyConditionExpression='userId = :uid',
            FilterExpression='questionType = :qType',
            ExpressionAttributeValues={
                ':uid': thisUserId,
                ':qType': thisQuestionType
            },
            ExclusiveStartKey=user_response['LastEvaluatedKey']
        )
        for item in user_response['Items']:
            if 'questionId' in item:
                currAnsweredQuestions.append(item['questionId'])
    
    # 3. Remove answered questions from valid questions
    # Convert to set for O(1) lookups instead of O(n) list searches
    answered_questions_set = set(currAnsweredQuestions)
    unanswered_question_ids = [qid for qid in validQuestionIds if qid not in answered_questions_set]
    
    return unanswered_question_ids