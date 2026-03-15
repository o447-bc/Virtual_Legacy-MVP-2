"""
AWS Lambda Function: LoadJSONToDynamoDB

Purpose:
    Processes JSON files containing question data from S3 and loads them into DynamoDB.
    This function can be triggered by S3 events (when files are uploaded) or manually
    invoked to process all existing files in a specified S3 prefix.

Functionality:
    1. Reads JSON files from S3 bucket 'virtual-legacy'
    2. Validates required fields (questionId, questionType)
    3. Formats questionId with leading zeros (e.g., "3" becomes "00003")
    4. Stores processed data in DynamoDB table 'allQuestionDB'
    5. Supports both single file processing and batch processing of all files

DynamoDB Schema:
    - Partition Key: questionId (formatted with leading zeros)
    - Sort Key: questionType

Trigger Methods:
    - S3 Event: Automatically processes newly uploaded JSON files
    - Manual Invoke: Processes all JSON files when event contains {"processAll": true}

Author: Virtual Legacy Project
Last Modified: [Current Date]
"""

import json
import boto3
import urllib.parse
from botocore.exceptions import ClientError

# Initialize AWS service clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')  # DynamoDB table for storing question data
s3 = boto3.client('s3')  # S3 client for reading JSON files

def process_single_file(bucket, key):
    """
    Process a single JSON file from S3 and load its contents into DynamoDB.
    
    This function:
    1. Downloads the JSON file from S3
    2. Parses the JSON content (handles both single objects and arrays)
    3. Validates required fields (questionId, questionType)
    4. Formats questionId with leading zeros for consistent sorting
    5. Stores each item in DynamoDB using batch operations for efficiency
    
    Args:
        bucket (str): S3 bucket name containing the JSON file
        key (str): S3 object key (file path) of the JSON file to process
        
    Returns:
        int: Number of items processed and stored in DynamoDB
        
    Raises:
        ValueError: If required fields are missing or invalid
        ClientError: If AWS service calls fail
    """
    print(f"Processing file: s3://{bucket}/{key}")
    
    # Download and parse JSON file from S3
    response = s3.get_object(Bucket=bucket, Key=key)
    body = response['Body'].read().decode('utf-8')
    data = json.loads(body)
    
    # Use DynamoDB batch writer for efficient bulk operations
    with table.batch_writer() as batch:
        # Check if this is the new nested format with themeId and questions array
        if isinstance(data, dict) and 'themeId' in data and 'questions' in data:
            # New format: {themeId, themeName, questions: [{questionId, difficulty, text, active}]}
            theme_id = data['themeId']
            theme_name = data.get('themeName', theme_id)
            questions = data['questions']
            
            print(f"Processing theme: {theme_name} ({theme_id}) with {len(questions)} questions")
            
            for question in questions:
                # Validate required fields
                if 'questionId' not in question:
                    raise ValueError(f"questionId missing in question: {question}")
                
                # Create item with questionType derived from themeId
                item = {
                    'questionId': question['questionId'],
                    'questionType': theme_id,
                    'questionText': question.get('text', ''),
                    'difficulty': question.get('difficulty', 5),
                    'active': question.get('active', True),
                    'themeName': theme_name
                }
                
                # Format questionId with leading zeros
                question_id_str = str(item['questionId']).strip()
                
                # Check if questionId is in format "questionType-number"
                if '-' in question_id_str:
                    parts = question_id_str.split('-')
                    if len(parts) == 2 and parts[1].isdigit():
                        # Format: questionType-number -> questionType-00000
                        question_type_part = parts[0]
                        number_part = parts[1].zfill(5)
                        question_id = f"{question_type_part}-{number_part}"
                    else:
                        question_id = question_id_str
                elif question_id_str.isdigit():
                    # Pure numeric questionId
                    question_id = question_id_str.zfill(5)
                else:
                    question_id = question_id_str
                
                item['questionId'] = question_id
                
                # Store the item in DynamoDB
                batch.put_item(Item=item)
            
            return len(questions)
        
        # Legacy format: Handle both single JSON objects and arrays of objects
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            # Validate that required fields exist in the JSON data
            if 'questionId' not in item:
                raise ValueError(f"questionId missing in item: {item}")
            if 'questionType' not in item:
                raise ValueError(f"questionType missing in item: {item}")
                
            # Format questionId with leading zeros for consistent sorting and display
            # Example: "3" becomes "00003", "123" becomes "00123"
            # Non-numeric IDs (like "custom-id") are left unchanged
            
            # Clean and format questionId
            question_id_str = str(item['questionId']).strip()


            
            # Check if questionId is in format "questionType-number"
            if '-' in question_id_str:
                parts = question_id_str.split('-')
                if len(parts) == 2 and parts[1].isdigit():
                    # Format: questionType-number -> questionType-00000
                    question_type_part = parts[0]
                    number_part = parts[1].zfill(5)
                    question_id = f"{question_type_part}-{number_part}"

                else:
                    question_id = question_id_str

            elif question_id_str.isdigit():
                # Pure numeric questionId
                question_id = question_id_str.zfill(5)

            else:
                question_id = question_id_str

            
            question_type = str(item['questionType'])
            
            # Ensure both keys have valid values (not empty strings)
            if not question_id or not question_type:
                raise ValueError(f"Invalid keys in item: {item}")
            
            # Update the item with the formatted questionId before storing
            item['questionId'] = question_id

                
            # Store the item in DynamoDB

            batch.put_item(Item=item)
    
    return len(items if isinstance(data, list) else [data])

def lambda_handler(event, context):
    """
    Main Lambda function handler that processes JSON files from S3 into DynamoDB.
    
    This function supports two modes of operation:
    1. S3 Event Mode: Triggered automatically when JSON files are uploaded to S3
    2. Manual Batch Mode: Processes all existing JSON files when invoked with processAll=true
    
    Event Structure for Manual Mode:
    {
        "processAll": true,
        "bucket": "virtual-legacy",  # Optional, defaults to 'virtual-legacy'
        "prefix": "questions/questionsInJSON/"  # Optional, defaults to 'questions/questionsInJSON/'
    }
    
    Event Structure for S3 Mode:
    Standard S3 event notification structure with Records array
    
    Args:
        event (dict): Lambda event object containing trigger information
        context (object): Lambda context object (unused but required)
        
    Returns:
        dict: HTTP response with statusCode and body containing processing results
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Check if this is a manual trigger to process all files in the S3 prefix
        if 'processAll' in event and event['processAll']:
            # Extract bucket and prefix from event, use defaults if not provided
            bucket = event.get('bucket', 'virtual-legacy')
            prefix = event.get('prefix', 'questions/questionsInJSON/')
            
            print(f"Manual batch processing mode: bucket={bucket}, prefix={prefix}")
            
            # List all objects in the specified S3 prefix
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            # Check if any files exist in the specified location
            if 'Contents' not in response:
                print("No files found in the specified S3 location")
                return {
                    'statusCode': 200,
                    'body': json.dumps('No files found')
                }
            
            # Filter to only process JSON files (ignore other file types)
            json_files = [obj['Key'] for obj in response['Contents'] 
                         if obj['Key'].endswith('.json')]
            
            print(f"Found {len(json_files)} JSON files to process")
            
            # Process each JSON file and track results
            total_items = 0
            processed_files = []
            
            for file_key in json_files:
                try:
                    print(f"Processing file: {file_key}")
                    items_count = process_single_file(bucket, file_key)
                    total_items += items_count
                    processed_files.append(file_key)
                    print(f"Successfully processed {file_key}: {items_count} items")
                except Exception as e:
                    # Log error but continue processing other files
                    print(f"Error processing {file_key}: {str(e)}")
            
            # Return summary of batch processing results
            result_message = f'Processed {len(processed_files)} files, {total_items} total items'
            print(f"Batch processing complete: {result_message}")
            return {
                'statusCode': 200,
                'body': json.dumps(result_message)
            }
        
        else:
            # Normal S3 event processing mode (triggered by file upload)
            print("S3 event processing mode")
            
            # Extract bucket and key from S3 event notification
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
            
            print(f"Processing S3 event for: s3://{bucket}/{key}")
            
            # Process the single file that triggered this event
            items_count = process_single_file(bucket, key)
            
            # Return success response with processing details
            result_message = f'Successfully processed {key}, {items_count} items'
            print(result_message)
            return {
                'statusCode': 200,
                'body': json.dumps(result_message)
            }
    
    except ClientError as e:
        # Handle AWS service-specific errors (S3, DynamoDB, etc.)
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        error_details = f"ClientError: {error_code} - {error_message}"
        print(error_details)
        return {
            'statusCode': 500,
            'body': json.dumps(error_details)
        }
    except Exception as e:
        # Handle all other unexpected errors
        error_details = f"Error: {str(e)}"
        print(error_details)
        return {
            'statusCode': 500,
            'body': json.dumps(error_details)
        }