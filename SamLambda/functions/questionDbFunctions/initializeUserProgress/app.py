import os
"""
Initialize User Progress Lambda Function

This AWS Lambda function initializes progress tracking data for legacy makers when they log in.
It creates progress records in the userQuestionLevelProgressDB table for all available question types,
starting users at level 1 with valid difficulty-1 questions.

Author: Virtual Legacy MVP Team
Version: 1.0
Last Updated: 2025-09-14

API Endpoint: POST /functions/questionDbFunctions/initialize-progress/
Authentication: AWS Cognito JWT (legacy_maker persona required)
CORS: Enabled for cross-origin requests

Request Flow:
1. Handle CORS preflight OPTIONS requests
2. Validate JWT authentication and extract user ID
3. Verify user has 'legacy_maker' persona type
4. Check if user already has progress data (skip if exists)
5. Scan allQuestionDB to get question types and valid difficulty-1 questions
6. Create progress records for each question type in userQuestionLevelProgressDB
7. Return success response with count of initialized question types

Database Tables:
- userQuestionLevelProgressDB: Stores user progress tracking data
  - Partition Key: userId (string)
  - Sort Key: questionType (string)
  - Attributes: friendlyName, maxLevelCompleted, currentQuestLevel, remainQuestAtCurrLevel, numQuestComplete, totalQuestAtCurrLevel
- allQuestionDB: Contains all questions with metadata
  - Attributes: questionId, questionType, Difficulty, Valid

Error Handling:
- 401: Missing or invalid JWT authentication
- 400: Invalid profile data format
- 403: User is not a legacy maker
- 500: Database errors or unexpected exceptions

All responses include CORS headers for frontend compatibility.
"""

import json
import boto3

# Standard CORS headers for all responses
CORS_HEADERS = {
    'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'POST,OPTIONS'
}

def lambda_handler(event, context):
    """
    Main Lambda handler function for initializing user progress.
    
    Args:
        event (dict): API Gateway event containing HTTP request data
        context (object): Lambda runtime context with request metadata
    
    Returns:
        dict: HTTP response with statusCode, headers, and body
    """
    # Log function initialization for debugging
    # Force rebuild timestamp: 2025-09-15
    print(f"[INIT] Function started - Request ID: {context.aws_request_id}")
    print(f"[INIT] Event: {json.dumps(event)}")
    
    # Handle CORS preflight OPTIONS requests
    # These are sent by browsers before actual POST requests to check CORS permissions
    if event.get('httpMethod') == 'OPTIONS':
        print("[CORS] Handling OPTIONS request")
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    # Extract user ID from JWT claims provided by API Gateway Cognito authorizer
    # The 'sub' claim contains the unique user identifier from Cognito
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    print(f"[AUTH] Extracted user_id: {user_id}")
    
    # Validate that user is authenticated (user_id exists)
    if not user_id:
        print("[ERROR] No user_id found in JWT claims")
        return {
            'statusCode': 401,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    # Extract and validate persona type from JWT profile claim
    # The profile claim contains JSON data with user persona information
    profile = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('profile', '{}')
    print(f"[AUTH] Profile data: {profile}")
    
    try:
        # Parse JSON profile data to extract persona_type
        persona_data = json.loads(profile)
        persona_type = persona_data.get('persona_type')
        print(f"[AUTH] Parsed persona_type: {persona_type}")
    except Exception as e:
        print(f"[ERROR] Failed to parse profile: {e}")
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Invalid profile data'})
        }
    
    # Verify user has the required persona type for this operation
    # Only legacy makers are allowed to initialize progress data
    if persona_type != 'legacy_maker':
        print(f"[ERROR] Access denied - persona_type: {persona_type}")
        return {
            'statusCode': 403,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Only legacy makers allowed'})
        }
    
    try:
        # Initialize DynamoDB table resources
        # userQuestionLevelProgressDB: Stores user progress tracking data
        # allQuestionDB: Contains all questions with metadata (questionType, Difficulty, Valid)
        # userStatusDB: Stores global user level status
        progress_table = boto3.resource('dynamodb').Table('userQuestionLevelProgressDB')
        all_questions_table = boto3.resource('dynamodb').Table('allQuestionDB')
        user_status_table = boto3.resource('dynamodb').Table('userStatusDB')
        print("[DB] DynamoDB resources initialized")
        
        # Get existing progress data to determine what needs to be initialized
        print(f"[DB] Checking existing progress for user: {user_id}")
        existing = progress_table.query(
            KeyConditionExpression='userId = :uid', 
            ExpressionAttributeValues={':uid': user_id}
        )
        existing_question_types = {item['questionType'] for item in existing['Items']}
        print(f"[DB] Existing question types: {existing_question_types}")
        
        # Initialize user status with current level = 1 for new users
        print(f"[DB] Initializing user status for user: {user_id}")
        user_status_table.put_item(Item={
            'userId': user_id,
            'currLevel': 1,
            'allowTranscription': True
        })
        print("[DB] User status initialized with currLevel = 1, allowTranscription = True")
        
        # Scan allQuestionDB to collect question types and valid difficulty-1 questions
        # This single scan is more efficient than multiple queries
        print("[DB] Scanning allQuestionDB for question types and difficulty=1 questions")
        response = all_questions_table.scan()
        print(f"[DB] Found {len(response['Items'])} total questions")
        
        # Track all unique question types, friendly names, and valid difficulty-1 questions by type
        question_types = set()  # All unique question types found
        friendly_names = {}  # Friendly names for each question type
        difficulty_one_by_type = {}  # Valid difficulty-1 questions grouped by type with text
        
        # Process each question to extract types, friendly names, and filter valid difficulty-1 questions
        for item in response['Items']:
            q_type = item.get('questionType')
            if q_type:
                # Add to set of all question types
                question_types.add(q_type)
                
                # Get friendly name from themeName field (new structure) or metadata record (legacy)
                if 'themeName' in item and q_type not in friendly_names:
                    friendly_names[q_type] = item['themeName']
                # Legacy: Check for friendly name (questionId pattern: questionType-00000)
                question_id = item.get('questionId', '')
                if question_id == f"{q_type}-00000" and 'Question' in item:
                    friendly_names[q_type] = item['Question']
                
                # Support both new structure (difficulty, active, questionText) and legacy (Difficulty, Valid, Question)
                difficulty = item.get('difficulty') or item.get('Difficulty')
                is_valid = item.get('active') == True or item.get('Valid') == 1
                question_text = item.get('questionText') or item.get('Question')
                
                # Only include questions that are both difficulty=1 AND valid AND have question text
                # These will be the initial questions available to users
                if difficulty == 1 and is_valid and question_text:
                    if q_type not in difficulty_one_by_type:
                        difficulty_one_by_type[q_type] = {'ids': [], 'texts': []}
                    difficulty_one_by_type[q_type]['ids'].append(item['questionId'])
                    difficulty_one_by_type[q_type]['texts'].append(question_text)
        
        print(f"[DATA] Found question types: {list(question_types)}")
        print(f"[DATA] Friendly names found: {friendly_names}")
        for q_type in question_types:
            ids_count = len(difficulty_one_by_type.get(q_type, {}).get('ids', []))
            texts_count = len(difficulty_one_by_type.get(q_type, {}).get('texts', []))
            print(f"[DATA] {q_type}: {ids_count} question IDs, {texts_count} question texts")
        
        # Create progress records for missing question types only
        # Each record tracks user's progress within that specific question type
        records_created = 0
        for q_type in question_types:
            # Skip if this question type already has a progress record
            if q_type in existing_question_types:
                print(f"[SKIP] Question type {q_type} already initialized")
                continue
            
            # Get question data for this type
            question_data = difficulty_one_by_type.get(q_type, {'ids': [], 'texts': []})
            question_ids = question_data.get('ids', [])
            question_texts = question_data.get('texts', [])
            
            # IMPORTANT: Skip question types that have NO level 1 questions
            if len(question_ids) == 0:
                print(f"[SKIP] Question type {q_type} has no level 1 questions")
                continue
            
            # Validate array lengths match for index alignment
            if len(question_ids) != len(question_texts):
                print(f"[WARNING] Array length mismatch for {q_type}: {len(question_ids)} ids vs {len(question_texts)} texts")
                min_length = min(len(question_ids), len(question_texts))
                question_ids = question_ids[:min_length]
                question_texts = question_texts[:min_length]
            
            # Initialize progress data structure for this question type
            item_data = {
                'userId': user_id,  # Partition key: unique user identifier
                'questionType': q_type,  # Sort key: question type identifier
                'friendlyName': friendly_names.get(q_type, q_type),  # Human-readable name for the question type
                'maxLevelCompleted': 0,  # Highest difficulty level completed (starts at 0)
                'currentQuestLevel': 1,  # Current difficulty level (starts at 1)
                'remainQuestAtCurrLevel': question_ids,  # Available question IDs at current level
                'remainQuestTextAtCurrLevel': question_texts,  # Available question texts at current level (aligned with IDs)
                'numQuestComplete': 0,  # Total number of questions completed (starts at 0)
                'totalQuestAtCurrLevel': len(question_ids)  # Total questions available at current level
            }
            print(f"[DB] Writing progress record for {q_type} with {len(question_ids)} questions")
            
            # Write progress record to DynamoDB
            progress_table.put_item(Item=item_data)
            records_created += 1
        
        # Log successful completion and return success response
        total_existing = len(existing_question_types)
        total_expected = len(question_types)
        print(f"[SUCCESS] Created {records_created} new progress records for user {user_id}")
        print(f"[SUCCESS] User now has {total_existing + records_created} of {total_expected} question types initialized")
        
        if records_created == 0:
            message = 'All question types already initialized'
        else:
            message = f'Initialized {records_created} missing question types'
            
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': message})
        }
        
    except Exception as e:
        # Handle any unexpected errors during database operations
        # Log detailed error information for debugging
        print(f"[ERROR] Exception occurred: {str(e)}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Return 500 Internal Server Error with CORS headers
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal error: {str(e)}'})
        }