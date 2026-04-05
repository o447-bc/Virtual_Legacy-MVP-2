import os
"""
Increment User Level 2 Lambda Function

This AWS Lambda function handles incrementing a user's question level with global level completion logic.
It only advances users to the next level when ALL question types are completed at the current global level.

Author: Virtual Legacy Team
Version: 2.0
Last Modified: 2024

Dependencies:
- boto3: AWS SDK for Python
- json: JSON parsing and serialization

DynamoDB Tables:
- userQuestionLevelProgressDB: Stores user progress and current level
- userStatusDB: Stores global user level status
- allQuestionDB: Contains all available questions with difficulty levels

API Gateway Integration:
- Method: POST
- CORS enabled for cross-origin requests
- Requires user authentication via Cognito
"""

import json
import boto3
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
    """
    AWS Lambda handler function to increment user's question level with global level logic.
    
    Args:
        event (dict): API Gateway event containing HTTP request data
        context (object): Lambda runtime context object
    
    Returns:
        dict: HTTP response with status code, headers, and body
    
    Process Flow:
    1. Handle CORS preflight requests
    2. Authenticate user from JWT token
    3. Parse request body for question type
    4. Check if all question types are completed at current global level
    5. If yes: increment global level and unlock next level for all question types
    6. If no: return message that other question types must be completed first
    """
    # Step 1: Handle CORS preflight requests (identical to incrementUserLevel)
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
    
    # Step 2: Extract and validate authenticated user ID (identical to incrementUserLevel)
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Step 3: Parse request body to extract question type
        body = json.loads(event['body'])
        question_type = body['questionType']
        
        # Step 4: Initialize DynamoDB resources
        dynamodb = boto3.resource('dynamodb')
        progress_table = dynamodb.Table(os.environ.get('TABLE_QUESTION_PROGRESS', 'userQuestionLevelProgressDB'))
        user_status_table = dynamodb.Table(os.environ.get('TABLE_USER_STATUS', 'userStatusDB'))
        all_questions_table = dynamodb.Table(os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB'))
        
        # Step 5: Get user's current global level
        user_status_response = user_status_table.get_item(Key={'userId': user_id})
        if 'Item' not in user_status_response:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'User status not found. Please initialize progress first.'})
            }
        
        current_global_level = int(user_status_response['Item']['currLevel'])
        
        # Step 6: Get all progress items and filter to current global level only
        progress_response = progress_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        all_progress_items = progress_response['Items']
        print(f"Found {len(all_progress_items)} total progress items")
        
        # Filter to only items at current global level
        current_level_items = []
        for item in all_progress_items:
            if int(item.get('currentQuestLevel', 0)) == current_global_level:
                current_level_items.append(item)
        
        print(f"Found {len(current_level_items)} items at current global level {current_global_level}")
        
        # Handle inconsistent state: no items at current level but items exist at other levels
        if len(current_level_items) == 0 and len(all_progress_items) > 0:
            print("INCONSISTENT STATE: No items at global level, attempting recovery")
            # Find the maximum level that has items (progress items are source of truth)
            levels_with_items = [int(item.get('currentQuestLevel', 0)) for item in all_progress_items]
            effective_current_level = max(levels_with_items)
            print(f"Using effective current level: {effective_current_level}")
            
            # Sync userStatusDB to match reality
            print(f"Syncing userStatusDB from {current_global_level} to {effective_current_level}")
            user_status_table.put_item(Item={
                'userId': user_id,
                'currLevel': effective_current_level
            })
            
            # Re-filter using effective level
            current_level_items = []
            for item in all_progress_items:
                if int(item.get('currentQuestLevel', 0)) == effective_current_level:
                    current_level_items.append(item)
            current_global_level = effective_current_level
        
        # If still no items, return error
        if len(current_level_items) == 0:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'No progress data found at current level'})
            }
        
        # Check if ALL current level items are complete
        for item in current_level_items:
            remaining_count = len(item.get('remainQuestAtCurrLevel', []))
            print(f"Question type {item.get('questionType')} has {remaining_count} remaining questions")
            if remaining_count > 0:
                return {
                    'statusCode': 200,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                    'body': json.dumps({
                        'message': 'Complete all question types at current level before advancing',
                        'levelComplete': False,
                        'currentGlobalLevel': current_global_level
                    })
                }
        
        print("All current level items are complete, proceeding with level advancement")
        
        # Step 7: Get question types that exist at new level BEFORE updating global level
        new_global_level = current_global_level + 1
        print(f"Preparing to advance from level {current_global_level} to {new_global_level}")
        
        # Support both new structure (difficulty, active) and legacy (Difficulty, Valid)
        next_level_questions = all_questions_table.scan(
            FilterExpression='(difficulty = :diff OR Difficulty = :diff) AND (active = :active_true OR Valid = :valid)',
            ExpressionAttributeValues={
                ':diff': new_global_level,
                ':active_true': True,
                ':valid': 1
            }
        )
        print(f"Found {len(next_level_questions['Items'])} questions at level {new_global_level}")
        
        # Filter by assignedQuestions if user has completed the life-events survey
        assigned_questions = user_status_response.get('Item', {}).get('assignedQuestions')
        assigned_ids = None
        if assigned_questions:
            if isinstance(assigned_questions, list):
                assigned_questions = {'standard': assigned_questions, 'instanced': []}
            assigned_ids = set(assigned_questions.get('standard', []))
            for group in assigned_questions.get('instanced', []):
                assigned_ids.update(group.get('questionIds', []))
        
        # Extract unique question types
        question_types = set()
        questions_by_type = {}
        for item in next_level_questions['Items']:
            q_type = item.get('questionType')
            if q_type:
                # Skip questions not in assignedQuestions if user has survey data
                if assigned_ids is not None and item['questionId'] not in assigned_ids:
                    continue
                question_types.add(q_type)
                if q_type not in questions_by_type:
                    questions_by_type[q_type] = []
                questions_by_type[q_type].append(item)
        
        if not question_types:
            print(f"ERROR: No questions available at level {new_global_level}")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': f'No questions available at level {new_global_level}'})
            }
        
        print(f"Question types at level {new_global_level}: {list(question_types)}")
        
        # Step 8: Prepare new progress items BEFORE making any database changes
        new_progress_items = []
        for q_type in question_types:
            questions = questions_by_type[q_type]
            
            # Get friendly name from themeName field (new structure) or special record (legacy)
            friendly_name = q_type
            for q in questions:
                # New structure: themeName field
                if 'themeName' in q:
                    friendly_name = q['themeName']
                    break
                # Legacy: special metadata record
                if q.get('questionId') == f"{q_type}-00000":
                    friendly_name = q.get('Question', q_type)
                    break
            
            # Prepare new progress item - support both questionText and Question fields
            question_ids = []
            question_texts = []
            for q in questions:
                question_text = q.get('questionText') or q.get('Question')
                if question_text:
                    question_ids.append(q['questionId'])
                    question_texts.append(question_text)
            
            new_item = {
                'userId': user_id,
                'questionType': q_type,
                'currentQuestLevel': new_global_level,
                'remainQuestAtCurrLevel': question_ids,
                'remainQuestTextAtCurrLevel': question_texts,
                'totalQuestAtCurrLevel': len(question_ids),
                'numQuestComplete': 0,
                'maxLevelCompleted': current_global_level,
                'friendlyName': friendly_name
            }
            new_progress_items.append(new_item)
            print(f"Prepared progress item for {q_type} with {len(question_ids)} questions")
        
        # Step 9: Now perform database operations with rollback capability
        try:
            # Update global level first
            print(f"Updating global level to {new_global_level}")
            user_status_table.put_item(Item={
                'userId': user_id,
                'currLevel': new_global_level
            })
            
            # Delete existing progress items
            print(f"Deleting {len(all_progress_items)} existing progress items")
            for progress_item in all_progress_items:
                progress_table.delete_item(
                    Key={
                        'userId': progress_item['userId'],
                        'questionType': progress_item['questionType']
                    }
                )
            
            # Create new progress items
            print(f"Creating {len(new_progress_items)} new progress items")
            for new_item in new_progress_items:
                progress_table.put_item(Item=new_item)
                print(f"Created progress item for {new_item['questionType']}")
            
            print(f"Successfully completed level advancement to {new_global_level}")
            
        except Exception as db_error:
            print(f"ERROR during database operations: {str(db_error)}")
            print(f"Attempting rollback to level {current_global_level}")
            
            try:
                # Rollback global level
                user_status_table.put_item(Item={
                    'userId': user_id,
                    'currLevel': current_global_level
                })
                
                # Restore original progress items
                for original_item in all_progress_items:
                    progress_table.put_item(Item=original_item)
                
                print(f"Rollback completed successfully")
                
            except Exception as rollback_error:
                print(f"CRITICAL: Rollback failed: {str(rollback_error)}")
            
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'error': f'Level advancement failed: {str(db_error)}',
                    'levelComplete': False,
                    'currentGlobalLevel': current_global_level
                })
            }
        
        # Step 10: Return success response
        clean_items = json.loads(json.dumps(new_progress_items, cls=DecimalEncoder))
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'message': f'Global level incremented to {new_global_level}',
                'levelComplete': True,
                'newGlobalLevel': new_global_level,
                'updatedProgressItems': clean_items
            })
        }
        
    except Exception as e:
        # Handle any errors during processing
        print(f"[ERROR] incrementUserLevel2: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Failed to increment user level. Please try again.'})
        }