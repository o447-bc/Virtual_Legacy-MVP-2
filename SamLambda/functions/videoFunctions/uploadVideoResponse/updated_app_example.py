import json
import boto3
import base64
import uuid
import sys
import os
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from persona_validator import PersonaValidator

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
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    try:
        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}
        
        # Extract required parameters
        user_id = body.get('userId')
        question_id = body.get('questionId')
        question_type = body.get('questionType')
        video_data = body.get('videoData')  # Base64 encoded video
        
        if not all([user_id, question_id, question_type, video_data]):
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Missing required parameters: userId, questionId, questionType, videoData'
                }, cls=DecimalEncoder)
            }
        
        # Validate persona access using shared validator
        persona_info = PersonaValidator.get_user_persona_from_jwt(event)
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        
        if not is_valid:
            return PersonaValidator.create_access_denied_response(message)
        
        # Validate user access (ensure user can only upload to their own folder)
        validate_user_access(user_id, event)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{question_id}_{timestamp}_{str(uuid.uuid4())[:8]}.webm"
        
        # Upload to S3
        s3_key = f"user-responses/{user_id}/{filename}"
        upload_to_s3(video_data, s3_key)
        
        # Update DynamoDB
        update_user_question_status(user_id, question_id, question_type, filename, s3_key)
        
        # Create response with persona context
        response_body = {
            'message': 'Video uploaded successfully',
            'filename': filename,
            's3Key': s3_key
        }
        
        # Add persona context for frontend
        response_body = PersonaValidator.add_persona_context_to_response(response_body, persona_info)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps(response_body, cls=DecimalEncoder)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'error': f"Error processing request: {str(e)}"
            }, cls=DecimalEncoder)
        }

def validate_user_access(user_id, event):
    """Validate that the authenticated user matches the userId in the request."""
    auth_context = event.get('requestContext', {}).get('authorizer', {})
    authenticated_user_id = auth_context.get('claims', {}).get('sub')
    
    if not authenticated_user_id or authenticated_user_id != user_id:
        raise ValueError("Unauthorized: User can only upload to their own folder")

def upload_to_s3(video_data_base64, s3_key):
    """Upload base64 encoded video data to S3."""
    try:
        video_bytes = base64.b64decode(video_data_base64)
        s3_client = boto3.client('s3')
        bucket_name = 'virtual-legacy'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=video_bytes,
            ContentType='video/webm',
            ServerSideEncryption='AES256'
        )
        
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")

def update_user_question_status(user_id, question_id, question_type, filename, s3_key):
    """Update userQuestionStatusDB with the video response."""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('userQuestionStatusDB')
        
        table.put_item(
            Item={
                'userId': user_id,
                'questionId': question_id,
                'questionType': question_type,
                'filename': filename,
                's3Location': f's3://virtual-legacy/{s3_key}',
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
        )
        
    except Exception as e:
        raise Exception(f"Failed to update database: {str(e)}")