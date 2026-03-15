import os
"""AWS Lambda Function: Get Question Type Data

Purpose:
    Retrieves comprehensive data about all question types from the allQuestionDB table.
    This function provides metadata needed for the frontend to display question categories.

Returns:
    JSON object containing:
    {
        "uniqueQuestionTypesCount": <int>,     # Total number of unique question types
        "questionTypes": [<string>],           # Array of question type IDs (e.g., "childhood", "schooling")
        "friendlyNames": [<string>],           # Array of human-readable names for each type
        "numValidQuestions": [<int>]           # Array of valid question counts per type
    }

Example Response:
    {
        "uniqueQuestionTypesCount": 3,
        "questionTypes": ["childhood", "schooling", "values"],
        "friendlyNames": ["Childhood Memories", "School Years", "Personal Values"],
        "numValidQuestions": [25, 30, 15]
    }

API Endpoint: GET /functions/questionDbFunctions/typedata
Authentication: Requires Cognito JWT token
Caching: 5-minute cache to improve performance
"""

import json
import boto3
from botocore.exceptions import ClientError
import time

# Global cache variables (persist between Lambda invocations)
cached_data = None
cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes in seconds

def lambda_handler(event, context):
    global cached_data, cache_timestamp
    
    # Check if cached data is still valid (5-minute TTL)
    # This reduces DynamoDB scans and improves response time
    current_time = time.time()
    if cached_data and (current_time - cache_timestamp) < CACHE_TTL:
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(cached_data)
        }
    
    # Initialize DynamoDB client to access the questions database
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('allQuestionDB')
    
    try:
        # Scan the entire allQuestionDB table to get all question records
        # Note: This is acceptable for this use case as question data is relatively static
        response = table.scan()
        items = response['Items']
        
        # Extract unique question types from all items
        # Each question has a 'questionType' field (e.g., "childhood", "schooling", "values")
        question_types_set = set(item['questionType'] for item in items)
        question_types = list(question_types_set)
        count = len(question_types)
        
        # For each question type, gather additional metadata
        friendly_names = []        # Human-readable names for display
        num_valid_questions = []   # Count of valid questions per type
        
        for q_type in question_types:
            # Find the friendly name from themeName field (new structure)
            # or from special metadata record (legacy structure)
            friendly_name = "Unknown"
            for item in items:
                if item['questionType'] == q_type:
                    # New structure: themeName field exists in all records
                    if 'themeName' in item:
                        friendly_name = item['themeName']
                        break
                    # Legacy structure: metadata record with questionId format "{type}-00000"
                    elif item.get('questionId') == f"{q_type}-00000" and 'Question' in item:
                        friendly_name = item['Question']
                        break
            friendly_names.append(friendly_name)
            
            # Count how many valid questions exist for this question type
            # New structure uses 'active' field (boolean), legacy uses 'Valid' field (1/0)
            valid_count = sum(1 for item in items 
                            if item['questionType'] == q_type 
                            and (item.get('active') == True or item.get('Valid') == 1))
            num_valid_questions.append(valid_count)
        
        # Prepare the complete response data structure
        # This provides all information needed by the frontend to display question categories
        response_data = {
            'uniqueQuestionTypesCount': count,          # Total number of question types
            'questionTypes': question_types,            # Array of type IDs
            'friendlyNames': friendly_names,            # Array of display names
            'numValidQuestions': num_valid_questions    # Array of question counts
        }
        
        # Cache the response data for 5 minutes to reduce database load
        cached_data = response_data
        cache_timestamp = current_time
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_data)
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': f"Error accessing DynamoDB: {str(e)}"
            })
        }
    
