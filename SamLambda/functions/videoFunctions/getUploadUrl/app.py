import os
import json
import boto3
from botocore.client import Config
import uuid
from datetime import datetime
from cors import cors_headers
from responses import error_response


# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

def lambda_handler(event, context):
    # Handle CORS preflight (copied from incrementUserLevel2)
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
    
    # Extract user ID (copied from incrementUserLevel2)
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        body = json.loads(event['body'])
        question_id = body['questionId']
        question_type = body['questionType']
        content_type = body.get('contentType', 'video/webm')
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{question_id}_{timestamp}_{str(uuid.uuid4())[:8]}.webm"
        s3_key = f"user-responses/{user_id}/{filename}"
        
        # Generate pre-signed URL (5 minute expiration)
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': 'virtual-legacy',
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=300
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'uploadUrl': upload_url,
                's3Key': s3_key,
                'filename': filename,
                'expiresIn': 300
            })
        }
        
    except KeyError as e:
        print(f"Missing required field in getUploadUrl: {e}")
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Missing required field in request body'})
        }
    except Exception as e:
        print(f"Error in getUploadUrl: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }
