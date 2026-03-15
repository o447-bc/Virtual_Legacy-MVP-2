"""
Batch Progress Summary Lambda Function
=====================================
This function replaces multiple API calls with a single optimized call that returns
all progress data needed for the dashboard in one response.

PROBLEM SOLVED:
- Dashboard previously made N+1 API calls (1 for question types + N for each type's progress)
- Each call had network latency, Lambda cold starts, and DynamoDB query overhead
- Users experienced slow dashboard loading times

SOLUTION:
- Single Lambda function that batches all operations
- Caches question type data to avoid repeated scans
- Uses optimized DynamoDB queries and set operations
- Returns all dashboard data in one response

PERFORMANCE BENEFITS:
- Reduces N+1 API calls to 1 call (e.g., 4 calls → 1 call)
- Eliminates network latency multiplication
- Reduces Lambda cold start probability from N+1 to 1
- Optimizes DynamoDB operations with batch processing
- Caches static data (question types) for 5 minutes

DATA FLOW:
1. Extract userId from query parameters
2. Get cached or fresh question type data from allQuestionDB
3. Batch query user's answered questions from userQuestionStatusDB
4. Calculate progress using set operations for each question type
5. Return combined response with all dashboard data

RETURNS:
{
    "questionTypes": ["childhood", "values", "career"],           // Question type IDs
    "friendlyNames": ["Childhood Memories", "Core Values", "Career Journey"], // Display names
    "numValidQuestions": [25, 30, 20],                           // Total valid questions per type
    "progressData": {                                             // Unanswered counts per type
        "childhood": 5,    // 5 questions remaining
        "values": 10,      // 10 questions remaining
        "career": 3        // 3 questions remaining
    },
    "unansweredQuestionIds": {                                   // Specific unanswered question IDs
        "childhood": ["childhood-001", "childhood-005"],
        "values": ["values-002", "values-008"],
        "career": ["career-001"]
    }
}

DATABASE TABLES:
- allQuestionDB: Contains all questions with metadata (questionType, Valid, Difficulty, Question text)
- userQuestionStatusDB: Tracks which questions each user has answered (userId, questionId, questionType)
"""

import json
import boto3
import time
from botocore.exceptions import ClientError

# GLOBAL CACHING MECHANISM
# Lambda containers are reused between invocations, so global variables persist
# This allows us to cache question type data across multiple requests
cached_question_data = None  # Stores question types, friendly names, and valid question counts
cache_timestamp = 0          # When the cache was last updated (Unix timestamp)
CACHE_TTL = 300             # Cache time-to-live: 5 minutes (300 seconds)

# CORS HEADERS
# Pre-defined headers to avoid duplication and ensure consistent CORS policy
# Allows frontend to make requests from any origin during development
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',  # Allow requests from any domain
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'  # Supported HTTP methods
}

def lambda_handler(event, context):
    """
    MAIN LAMBDA HANDLER - Entry point for progress summary requests
    
    This function orchestrates the entire progress calculation process:
    1. Validates input parameters
    2. Gets question type metadata (cached when possible)
    3. Calculates user progress across all question types
    4. Returns combined response for dashboard
    
    INPUT:
    - event: API Gateway event containing query parameters
    - context: Lambda runtime context (unused)
    
    EXPECTED QUERY PARAMETERS:
    - userId: The Cognito user ID to get progress for (required)
    
    OUTPUT:
    - 200: Success with complete progress data
    - 400: Bad request (missing userId)
    - 500: Internal server error
    
    PERFORMANCE NOTES:
    - Uses caching to avoid repeated question type scans
    - Batches all progress calculations in single operation
    - Optimized for dashboard loading speed
    """
    try:
        # STEP 1: EXTRACT AND VALIDATE USER ID
        # API Gateway passes query parameters in event.queryStringParameters
        user_id = None
        if event.get('queryStringParameters'):
            user_id = event['queryStringParameters'].get('userId')
        
        # Validate userId is present and not empty
        if not user_id or user_id.strip() == '':
            return create_error_response(400, 'Missing required parameter: userId')
        
        # STEP 2: GET QUESTION TYPE METADATA
        # This includes question types, friendly names, and valid question counts
        # Uses caching to avoid repeated DynamoDB scans of allQuestionDB
        question_data = get_question_type_data()
        if not question_data:
            return create_error_response(500, 'Failed to retrieve question type data')
        
        # STEP 3: CALCULATE USER PROGRESS FOR ALL QUESTION TYPES
        # Batch operation that calculates progress across all question types
        # Returns both progress counts and specific unanswered question IDs
        progress_data, unanswered_data = get_batch_progress_data(
            question_data['questionTypes'],  # List of question types to process
            user_id                         # User to calculate progress for
        )
        
        # STEP 4: COMBINE ALL DATA INTO SINGLE RESPONSE
        # Merge question metadata with user-specific progress data
        response_data = {
            **question_data,  # Spread: questionTypes, friendlyNames, numValidQuestions
            'progressData': progress_data,        # Unanswered counts per question type
            'unansweredQuestionIds': unanswered_data  # Specific unanswered question IDs
        }
        
        # STEP 5: RETURN SUCCESS RESPONSE
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        # GLOBAL ERROR HANDLER
        # Catches any unexpected errors and returns standardized error response
        print(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def get_question_type_data():
    """
    GET QUESTION TYPE METADATA WITH INTELLIGENT CACHING
    
    This function retrieves static question type data that rarely changes:
    - List of all question types (e.g., "childhood", "values", "career")
    - Human-readable friendly names for each type
    - Count of valid questions per type
    
    CACHING STRATEGY:
    - Uses Lambda container global variables for caching
    - Cache TTL: 5 minutes (balances performance vs data freshness)
    - Avoids expensive DynamoDB scans on every request
    - Cache persists across Lambda invocations in same container
    
    DATA SOURCE:
    - allQuestionDB table contains all questions with metadata
    - Special records with pattern "{type}-00000" contain friendly names
    - Valid questions have Valid=1 attribute
    
    RETURNS:
    {
        "questionTypes": ["childhood", "values"],
        "friendlyNames": ["Childhood Memories", "Core Values"],
        "numValidQuestions": [25, 30]
    }
    
    PERFORMANCE:
    - Cache hit: ~1ms response time
    - Cache miss: ~100-500ms (DynamoDB scan + processing)
    """
    global cached_question_data, cache_timestamp
    
    # CACHE VALIDATION
    # Check if we have cached data and it's still within TTL
    current_time = time.time()
    if cached_question_data and (current_time - cache_timestamp) < CACHE_TTL:
        # Cache hit - return cached data immediately
        return cached_question_data
    
    try:
        # CACHE MISS - FETCH FRESH DATA FROM DYNAMODB
        # Initialize DynamoDB resource (more Pythonic than client)
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('allQuestionDB')
        
        # SCAN ENTIRE TABLE
        # Note: This is expensive but question data is relatively static
        # Consider adding GSI on questionType if table grows large
        response = table.scan()
        items = response.get('Items', [])
        
        # EXTRACT UNIQUE QUESTION TYPES
        # Use set to automatically deduplicate question types
        question_types_set = set(item['questionType'] for item in items if 'questionType' in item)
        question_types = list(question_types_set)  # Convert back to list for JSON serialization
        
        # BUILD PARALLEL ARRAYS FOR QUESTION TYPE METADATA
        # Arrays maintain order correspondence: questionTypes[i] maps to friendlyNames[i]
        friendly_names = []
        num_valid_questions = []
        
        for q_type in question_types:
            # FIND FRIENDLY NAME FROM SPECIAL METADATA RECORD
            # Convention: Records with ID "{type}-00000" contain display names
            # Example: "childhood-00000" contains "Childhood Memories"
            friendly_name = "Unknown"  # Default fallback
            for item in items:
                if (item.get('questionId') == f"{q_type}-00000" and 
                    'Question' in item):
                    friendly_name = item['Question']  # Question field contains friendly name
                    break
            friendly_names.append(friendly_name)
            
            # COUNT VALID QUESTIONS FOR THIS TYPE
            # Valid questions have Valid=1 attribute (vs Valid=0 for disabled)
            # This count is used for progress percentage calculations
            valid_count = sum(1 for item in items 
                            if (item.get('questionType') == q_type and 
                                item.get('Valid') == 1))
            num_valid_questions.append(valid_count)
        
        # UPDATE CACHE WITH FRESH DATA
        # Store in global variables that persist across Lambda invocations
        cached_question_data = {
            'questionTypes': question_types,
            'friendlyNames': friendly_names,
            'numValidQuestions': num_valid_questions
        }
        cache_timestamp = current_time  # Record when cache was updated
        
        return cached_question_data
        
    except ClientError as e:
        # DYNAMODB-SPECIFIC ERROR HANDLING
        # Could be throttling, permissions, or table not found
        print(f"DynamoDB error in get_question_type_data: {str(e)}")
        return None
    except Exception as e:
        # CATCH-ALL ERROR HANDLING
        # Handles JSON parsing, network issues, etc.
        print(f"Unexpected error in get_question_type_data: {str(e)}")
        return None

def get_batch_progress_data(question_types, user_id):
    """
    BATCH PROGRESS CALCULATION - Core optimization function
    
    This function calculates user progress across all question types in a single
    optimized operation, replacing what used to be N separate API calls.
    
    ALGORITHM:
    1. Single query to get ALL user's answered questions (not per-type)
    2. Group answered questions by type using hash maps
    3. For each question type:
       a. Get all valid questions for that type
       b. Use set operations to find unanswered questions
       c. Calculate progress metrics
    
    PERFORMANCE OPTIMIZATIONS:
    - Single user query instead of N queries (one per question type)
    - Set operations for O(1) lookups instead of O(n) list searches
    - Batch processing reduces DynamoDB request count
    - Error isolation: one failed type doesn't break others
    
    INPUT:
        question_types: List of question type IDs ["childhood", "values", "career"]
        user_id: Cognito user ID to calculate progress for
    
    OUTPUT:
        Tuple of (progress_data_dict, unanswered_questions_dict)
        
        progress_data_dict: {
            "childhood": 5,    # Number of unanswered questions
            "values": 10,
            "career": 3
        }
        
        unanswered_questions_dict: {
            "childhood": ["childhood-001", "childhood-005"],  # Specific question IDs
            "values": ["values-002", "values-008"],
            "career": ["career-001"]
        }
    
    ERROR HANDLING:
    - Individual question type failures don't break entire operation
    - Returns default values (0, []) for failed question types
    - Logs errors for debugging while maintaining service availability
    """
    try:
        # INITIALIZE DYNAMODB RESOURCES
        dynamodb = boto3.resource('dynamodb')
        questions_table = dynamodb.Table('allQuestionDB')      # All questions with metadata
        user_status_table = dynamodb.Table('userQuestionStatusDB')  # User's answered questions
        
        # INITIALIZE RESULT CONTAINERS
        progress_data = {}    # Will store unanswered counts per question type
        unanswered_data = {}  # Will store specific unanswered question IDs per type
        
        # STEP 1: GET ALL USER'S ANSWERED QUESTIONS IN SINGLE BATCH QUERY
        # This replaces N individual queries (one per question type)
        # Returns data grouped by question type for efficient processing
        answered_questions_by_type = get_user_answered_questions(user_status_table, user_id)
        
        # STEP 2: PROCESS EACH QUESTION TYPE INDIVIDUALLY
        # Even though we batch the user query, we still need to process each type
        # because valid questions are filtered per type
        for question_type in question_types:
            try:
                # GET ALL VALID QUESTIONS FOR THIS SPECIFIC TYPE
                # Valid questions have Valid=1 attribute in allQuestionDB
                valid_questions = get_valid_questions_for_type(questions_table, question_type)
                
                # GET USER'S ANSWERED QUESTIONS FOR THIS TYPE
                # Use .get() with empty set default to handle users with no answered questions
                answered_questions = answered_questions_by_type.get(question_type, set())
                
                # CALCULATE UNANSWERED QUESTIONS USING SET OPERATIONS
                # Convert to set for O(1) lookup performance instead of O(n) list operations
                # Set difference: valid_questions - answered_questions = unanswered_questions
                valid_questions_set = set(valid_questions)
                unanswered_questions = list(valid_questions_set - answered_questions)
                
                # STORE RESULTS FOR THIS QUESTION TYPE
                progress_data[question_type] = len(unanswered_questions)  # Count for progress percentage
                unanswered_data[question_type] = unanswered_questions     # IDs for specific question selection
                
            except Exception as e:
                # ERROR ISOLATION: One failed question type doesn't break entire operation
                print(f"Error processing question type {question_type}: {str(e)}")
                # Set safe defaults to maintain dashboard functionality
                progress_data[question_type] = 0   # Show as "no questions remaining"
                unanswered_data[question_type] = [] # Empty list of questions
        
        return progress_data, unanswered_data
        
    except Exception as e:
        # GLOBAL ERROR HANDLER FOR BATCH OPERATION
        print(f"Error in get_batch_progress_data: {str(e)}")
        # Return empty data structures to prevent dashboard crashes
        return {}, {}

def get_user_answered_questions(user_status_table, user_id):
    """
    SINGLE BATCH QUERY FOR ALL USER'S ANSWERED QUESTIONS
    
    This function replaces N individual queries (one per question type) with
    a single query that gets ALL answered questions for a user, then groups
    them by question type for efficient processing.
    
    DATABASE SCHEMA:
    userQuestionStatusDB:
    - Partition Key: userId (allows querying all questions for a user)
    - Sort Key: questionId (unique question identifier)
    - Attributes: questionType (for grouping), timestamp, etc.
    
    OPTIMIZATION STRATEGY:
    - Single DynamoDB query instead of N queries
    - Use sets for O(1) lookup performance in progress calculations
    - Handle pagination automatically for users with many answered questions
    - Group results by question type for efficient downstream processing
    
    INPUT:
        user_status_table: DynamoDB table resource for userQuestionStatusDB
        user_id: Cognito user ID to query answered questions for
    
    OUTPUT:
        Dict mapping question_type -> set of answered question IDs
        Example:
        {
            "childhood": {"childhood-001", "childhood-003", "childhood-007"},
            "values": {"values-002", "values-005"},
            "career": {"career-001"}
        }
    
    PERFORMANCE:
    - Single query vs N queries reduces network round trips
    - Set data structure enables O(1) lookups in progress calculations
    - Pagination handling ensures all data is retrieved for heavy users
    """
    answered_by_type = {}  # Will store question_type -> set of question IDs
    
    try:
        # SINGLE QUERY FOR ALL USER'S ANSWERED QUESTIONS
        # Query by partition key (userId) to get all answered questions at once
        # This is much more efficient than querying each question type separately
        response = user_status_table.query(
            KeyConditionExpression='userId = :uid',  # Get all records for this user
            ExpressionAttributeValues={':uid': user_id}
        )
        
        # PROCESS FIRST PAGE OF RESULTS
        # Group answered questions by question type using sets for performance
        for item in response.get('Items', []):
            question_id = item.get('questionId')
            question_type = item.get('questionType')
            
            # Validate required fields exist
            if question_id and question_type:
                # Initialize set for this question type if first time seeing it
                if question_type not in answered_by_type:
                    answered_by_type[question_type] = set()
                # Add question ID to the set (sets automatically handle duplicates)
                answered_by_type[question_type].add(question_id)
        
        # HANDLE PAGINATION FOR USERS WITH MANY ANSWERED QUESTIONS
        # DynamoDB limits response size, so we need to handle multiple pages
        # Continue querying until all answered questions are retrieved
        while 'LastEvaluatedKey' in response:
            response = user_status_table.query(
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ExclusiveStartKey=response['LastEvaluatedKey']  # Continue from where last query ended
            )
            
            # PROCESS ADDITIONAL PAGES
            # Same grouping logic as first page
            for item in response.get('Items', []):
                question_id = item.get('questionId')
                question_type = item.get('questionType')
                
                if question_id and question_type:
                    if question_type not in answered_by_type:
                        answered_by_type[question_type] = set()
                    answered_by_type[question_type].add(question_id)
        
        return answered_by_type
        
    except ClientError as e:
        # DYNAMODB ERROR HANDLING
        # Could be throttling, permissions, or table access issues
        print(f"Error querying user answered questions: {str(e)}")
        return {}  # Return empty dict to prevent downstream errors

def get_valid_questions_for_type(questions_table, question_type):
    """
    GET ALL VALID QUESTIONS FOR A SPECIFIC QUESTION TYPE
    
    This function retrieves all question IDs that are:
    1. Of the specified question type (e.g., "childhood", "values")
    2. Marked as valid (Valid=1) vs disabled (Valid=0)
    
    CURRENT IMPLEMENTATION:
    - Uses DynamoDB scan with filter expression
    - Scans entire table but filters server-side (more efficient than client filtering)
    - Handles pagination for large question sets
    
    PERFORMANCE CONSIDERATIONS:
    - Scan operation is expensive but necessary without GSI
    - TODO: Consider adding GSI on (questionType, Valid) for better performance
    - Current approach acceptable for moderate question volumes
    
    OPTIMIZATION OPPORTUNITY:
    - Global Secondary Index on questionType + Valid would enable Query instead of Scan
    - Query would be much faster: O(log n) vs O(n)
    - Trade-off: Additional storage cost vs query performance
    
    INPUT:
        questions_table: DynamoDB table resource for allQuestionDB
        question_type: Question type to filter for (e.g., "childhood")
    
    OUTPUT:
        List of valid question IDs for the specified type
        Example: ["childhood-001", "childhood-002", "childhood-005"]
    
    ERROR HANDLING:
    - Returns empty list on error to prevent downstream failures
    - Logs errors for debugging while maintaining service availability
    """
    valid_questions = []  # Will store list of valid question IDs
    
    try:
        # SCAN WITH SERVER-SIDE FILTERING
        # Scan entire table but filter on DynamoDB side (more efficient than client filtering)
        # Filter for questions that match both questionType AND Valid=1
        response = questions_table.scan(
            FilterExpression='questionType = :qtype AND Valid = :valid',
            ExpressionAttributeValues={
                ':qtype': question_type,  # Filter for specific question type
                ':valid': 1               # Only include valid/enabled questions
            }
        )
        
        # EXTRACT QUESTION IDS FROM FIRST PAGE
        for item in response.get('Items', []):
            question_id = item.get('questionId')
            if question_id:  # Validate question ID exists
                valid_questions.append(question_id)
        
        # HANDLE PAGINATION FOR LARGE QUESTION SETS
        # DynamoDB scan has size limits, so continue until all results retrieved
        while 'LastEvaluatedKey' in response:
            response = questions_table.scan(
                FilterExpression='questionType = :qtype AND Valid = :valid',
                ExpressionAttributeValues={
                    ':qtype': question_type,
                    ':valid': 1
                },
                ExclusiveStartKey=response['LastEvaluatedKey']  # Continue from last position
            )
            
            # EXTRACT QUESTION IDS FROM ADDITIONAL PAGES
            for item in response.get('Items', []):
                question_id = item.get('questionId')
                if question_id:
                    valid_questions.append(question_id)
        
        return valid_questions
        
    except ClientError as e:
        # DYNAMODB ERROR HANDLING
        print(f"Error getting valid questions for type {question_type}: {str(e)}")
        return []  # Return empty list to prevent downstream errors

def create_error_response(status_code, message):
    """
    CREATE STANDARDIZED ERROR RESPONSE
    
    This utility function ensures all error responses follow the same format
    and include proper CORS headers for frontend compatibility.
    
    STANDARDIZATION BENEFITS:
    - Consistent error format across all endpoints
    - Proper CORS headers prevent browser blocking
    - JSON format matches success responses
    - Centralized error response logic
    
    INPUT:
        status_code: HTTP status code (400, 401, 403, 500, etc.)
        message: Human-readable error description
    
    OUTPUT:
        Complete API Gateway response object with:
        - Proper HTTP status code
        - CORS headers for browser compatibility
        - JSON body with error message
    
    USAGE EXAMPLES:
        create_error_response(400, 'Missing required parameter: userId')
        create_error_response(500, 'Database connection failed')
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,  # Include CORS headers to prevent browser blocking
        'body': json.dumps({'error': message})  # Consistent JSON error format
    }