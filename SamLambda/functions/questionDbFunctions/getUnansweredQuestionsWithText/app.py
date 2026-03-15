import json
import boto3
import sys
import os
from botocore.exceptions import ClientError
from decimal import Decimal
from cors import cors_headers
from responses import error_response


# Temporarily disable persona validation
# from shared.persona_validator import PersonaValidator

# Custom JSON encoder to handle DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': ''
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
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Missing required parameters: questionType and userId'
            }, cls=DecimalEncoder)
        }
    
    try:
        # User data isolation enforced by DynamoDB IAM policy
        validate_basic_input(thisUserId)
        questions = get_unanswered_questions_with_text(thisQuestionType, thisUserId)
        
        # Create response
        response_body = {'questions': questions}
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_body, cls=DecimalEncoder)
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

def validate_basic_input(userId):
    """Basic input validation for userId parameter.
    
    Args:
        userId (str): The user ID from request parameters
        
    Raises:
        ValueError: If userId is invalid
    """
    if not userId or not isinstance(userId, str) or len(userId.strip()) == 0:
        raise ValueError("Invalid userId provided")

def get_unanswered_questions_with_text(thisQuestionType, thisUserId):
    """Get question texts for questions that match the question type and are not yet answered by the user."""
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    question_table = dynamodb.Table(os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB'))
    user_status_table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
    
    # 1. Get all valid questions of the specified type from allQuestionDB
    validQuestions = {}  # questionId -> question text
    question_response = question_table.scan(
        FilterExpression='Valid = :valid AND questionType = :qType',
        ExpressionAttributeValues={
            ':valid': 1,
            ':qType': thisQuestionType
        }
    )
    
    # Extract questionId and Question text
    for item in question_response['Items']:
        if 'questionId' in item and 'Question' in item:
            validQuestions[item['questionId']] = item['Question']
    
    # Handle pagination if necessary
    while 'LastEvaluatedKey' in question_response:
        question_response = question_table.scan(
            FilterExpression='Valid = :valid AND questionType = :qType',
            ExpressionAttributeValues={
                ':valid': 1,
                ':qType': thisQuestionType
            },
            ExclusiveStartKey=question_response['LastEvaluatedKey']
        )
        for item in question_response['Items']:
            if 'questionId' in item and 'Question' in item:
                validQuestions[item['questionId']] = item['Question']
    
    # 2. Get all answered questions for this user from userQuestionStatusDB with the specified question type
    currAnsweredQuestions = set()
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
            currAnsweredQuestions.add(item['questionId'])
    
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
                currAnsweredQuestions.add(item['questionId'])
    
    # 3. Return question texts for unanswered questions
    unanswered_questions = []
    for questionId, questionText in validQuestions.items():
        if questionId not in currAnsweredQuestions:
            unanswered_questions.append(questionText)
    
    return unanswered_questions