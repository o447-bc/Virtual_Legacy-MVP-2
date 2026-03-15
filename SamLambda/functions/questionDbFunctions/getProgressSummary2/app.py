import os
import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

def decimal_default(obj):
    """Convert Decimal objects to int or float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    print(f"Event: {json.dumps(event)}")
    
    # Handle OPTIONS request for CORS preflight - EXACT same as getUnansweredQuestionsFromUser
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
    
    # Extract authenticated user ID from JWT claims - EXACT same as getUnansweredQuestionsFromUser
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
    
    # Extract userId parameter (but ignore it for security - use authenticated_user_id)
    thisUserId = None
    if event.get('queryStringParameters'):
        thisUserId = event['queryStringParameters'].get('userId')
    
    if not thisUserId:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Missing required parameter: userId'
            })
        }
    
    # Query userQuestionLevelProgressDB using authenticated_user_id for security
    try:
        dynamodb = boto3.resource('dynamodb')
        progress_table = dynamodb.Table('userQuestionLevelProgressDB')
        user_status_table = dynamodb.Table('userStatusDB')
        
        response = progress_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': authenticated_user_id}
        )
        
        # If no progress data exists, initialize it for first-time users
        if not response['Items']:
            print(f"[INIT] No progress data found for user {authenticated_user_id}, initializing...")
            
            # Initialize progress data
            all_questions_table = dynamodb.Table('allQuestionDB')
            
            # Initialize user status with current level = 1
            user_status_table.put_item(Item={
                'userId': authenticated_user_id,
                'currLevel': 1
            })
            
            # Scan allQuestionDB to get question types and valid difficulty-1 questions
            all_questions_response = all_questions_table.scan()
            
            # Process questions to extract types and difficulty-1 questions
            question_types = set()
            friendly_names = {}
            difficulty_one_by_type = {}
            
            for item in all_questions_response['Items']:
                q_type = item.get('questionType')
                if q_type:
                    question_types.add(q_type)
                    
                    # Check for friendly name (support both new and legacy formats)
                    if 'themeName' in item:
                        friendly_names[q_type] = item['themeName']
                    else:
                        question_id = item.get('questionId', '')
                        if question_id == f"{q_type}-00000" and 'Question' in item:
                            friendly_names[q_type] = item['Question']
                    
                    # Include active difficulty-1 questions with text (support both new and legacy formats)
                    difficulty = item.get('difficulty') or item.get('Difficulty')
                    is_active = item.get('active', False) if 'active' in item else (item.get('Valid') == 1)
                    question_text = item.get('questionText') or item.get('Question', '')
                    
                    if difficulty == 1 and is_active and question_text:
                        if q_type not in difficulty_one_by_type:
                            difficulty_one_by_type[q_type] = {'ids': [], 'texts': []}
                        difficulty_one_by_type[q_type]['ids'].append(item['questionId'])
                        difficulty_one_by_type[q_type]['texts'].append(question_text)
            
            # Create progress records for each question type
            for q_type in question_types:
                question_data = difficulty_one_by_type.get(q_type, {'ids': [], 'texts': []})
                question_ids = question_data.get('ids', [])
                question_texts = question_data.get('texts', [])
                
                # Skip question types that have no level 1 questions — these belong to higher
                # difficulty levels and should not appear on the Level 1 dashboard
                if len(question_ids) == 0:
                    print(f"[INIT] Skipping {q_type} - no level 1 questions available")
                    continue
                
                # Ensure array lengths match
                if len(question_ids) != len(question_texts):
                    min_length = min(len(question_ids), len(question_texts))
                    question_ids = question_ids[:min_length]
                    question_texts = question_texts[:min_length]
                
                item_data = {
                    'userId': authenticated_user_id,
                    'questionType': q_type,
                    'friendlyName': friendly_names.get(q_type, q_type),
                    'maxLevelCompleted': 0,
                    'currentQuestLevel': 1,
                    'remainQuestAtCurrLevel': question_ids,
                    'remainQuestTextAtCurrLevel': question_texts,
                    'numQuestComplete': 0,
                    'totalQuestAtCurrLevel': len(question_ids)
                }
                
                progress_table.put_item(Item=item_data)
            
            # Fetch the newly created progress data
            response = progress_table.query(
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': authenticated_user_id}
            )
            
            print(f"[INIT] Initialized progress for {len(response['Items'])} question types")
            print(f"[INIT] Returning progress items: {[item.get('questionType') for item in response['Items']]}")
        
        # Auto-sync userStatusDB if inconsistent
        if response['Items']:
            levels = [int(item.get('currentQuestLevel', 0)) for item in response['Items']]
            if levels:
                max_level = max(levels)
                status = user_status_table.get_item(Key={'userId': authenticated_user_id})
                if 'Item' in status and int(status['Item'].get('currLevel', 1)) != max_level:
                    print(f"[SYNC] Fixing userStatusDB: {status['Item'].get('currLevel')} -> {max_level}")
                    user_status_table.put_item(Item={'userId': authenticated_user_id, 'currLevel': max_level})
        
        print(f"[RETURN] Returning {len(response['Items'])} progress items to frontend")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'progressItems': response['Items']}, default=decimal_default)
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