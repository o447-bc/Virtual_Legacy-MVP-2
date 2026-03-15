"""
Increment User Level Lambda Function

This AWS Lambda function handles incrementing a user's question level in the Virtual Legacy application.
When a user completes all questions at their current level, this function advances them to the next level
and prepares new questions for that level.

Author: Virtual Legacy Team
Version: 1.0
Last Modified: 2024

Dependencies:
- boto3: AWS SDK for Python
- json: JSON parsing and serialization

DynamoDB Tables:
- userQuestionLevelProgressDB: Stores user progress and current level
- allQuestionDB: Contains all available questions with difficulty levels

API Gateway Integration:
- Method: POST
- CORS enabled for cross-origin requests
- Requires user authentication via Cognito
"""

import json
import boto3
from decimal import Decimal

# Custom JSON encoder to handle DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """
    AWS Lambda handler function to increment user's question level.
    
    Args:
        event (dict): API Gateway event containing HTTP request data
        context (object): Lambda runtime context object
    
    Returns:
        dict: HTTP response with status code, headers, and body
    
    Process Flow:
    1. Handle CORS preflight requests
    2. Authenticate user from JWT token
    3. Parse request body for question type
    4. Retrieve current user progress from DynamoDB
    5. Increment user level and reset question counters
    6. Fetch new questions for the updated level
    7. Update user progress with new level data
    8. Return success response with new level info
    """
    # Step 1: Handle CORS preflight requests
    # OPTIONS requests are sent by browsers before actual requests to check CORS permissions
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    # Step 2: Extract and validate authenticated user ID from JWT token
    # The user ID is embedded in the JWT token claims after Cognito authentication
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Step 3: Parse request body to extract question type
        # Expected body format: {"questionType": "string"}
        body = json.loads(event['body'])
        question_type = body['questionType']
        
        # Step 4: Initialize DynamoDB resources and get current user progress
        # Connect to DynamoDB tables for user progress and question data
        dynamodb = boto3.resource('dynamodb')
        progress_table = dynamodb.Table('userQuestionLevelProgressDB')
        all_questions_table = dynamodb.Table('allQuestionDB')
        
        # Retrieve current progress record for this user and question type
        response = progress_table.get_item(Key={'userId': user_id, 'questionType': question_type})
        item = response['Item']
        
        # Step 5: Increment user level and reset progress counters
        # Advance to next difficulty level
        item['currentQuestLevel'] = int(item['currentQuestLevel']) + 1
        # Update the highest level completed (previous level)
        item['maxLevelCompleted'] = int(item['currentQuestLevel']) - 1
        # Reset completed questions counter for new level
        item['numQuestComplete'] = 0
        
        # Step 6: Fetch all valid questions for the new difficulty level
        # Query questions matching: question type, new difficulty level, and valid status
        # Support both new structure (difficulty, active, questionText) and legacy (Difficulty, Valid, Question)
        questions_response = all_questions_table.scan(
            FilterExpression='questionType = :qt AND (difficulty = :diff OR Difficulty = :diff) AND (active = :active_true OR Valid = :valid)',
            ExpressionAttributeValues={
                ':qt': question_type,
                ':diff': item['currentQuestLevel'],
                ':active_true': True,
                ':valid': 1
            }
        )
        
        # Step 7: Process new questions and update progress tracking
        new_questions = questions_response['Items']
        # Store list of question IDs remaining to be completed
        item['remainQuestAtCurrLevel'] = [q['questionId'] for q in new_questions]
        # Store question text for quick access (support both questionText and Question fields)
        item['remainQuestTextAtCurrLevel'] = [
            q.get('questionText') or q.get('Question', '') 
            for q in new_questions 
            if q.get('questionText') or q.get('Question')
        ]
        # Track total number of questions at this level
        item['totalQuestAtCurrLevel'] = len(new_questions)
        
        # Step 8: Save updated progress back to DynamoDB
        # This persists the level increment and new question data
        progress_table.put_item(Item=item)
        
        # Step 9: Clean item and return success response with complete updated progress item
        # Use JSON cleaning to handle all nested Decimal types
        clean_item = json.loads(json.dumps(item, cls=DecimalEncoder))
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'message': 'Level incremented',
                'updatedProgressItem': clean_item
            })
        }
        
    except Exception as e:
        # Handle any errors during processing and return error response
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }