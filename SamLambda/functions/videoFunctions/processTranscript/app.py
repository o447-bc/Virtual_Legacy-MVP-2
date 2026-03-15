import json
import boto3
import os
from datetime import datetime

transcribe_client = boto3.client('transcribe')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
SUMMARIZE_FUNCTION_NAME = os.environ.get('SUMMARIZE_FUNCTION_NAME', '')
MAX_TRANSCRIPT_SIZE = 300000  # 300KB limit for DynamoDB storage

def lambda_handler(event, context):
    """
    Triggered by EventBridge when Transcribe job completes.
    Retrieves transcript and stores in DynamoDB.
    """
    try:
        print(f"EventBridge event: {json.dumps(event)}")
        
        detail = event['detail']
        job_name = detail['TranscriptionJobName']
        job_status = detail['TranscriptionJobStatus']
        
        print(f"Processing job: {job_name}, status: {job_status}")
        
        # Parse job name: transcript-{userId}-{questionId}-{timestamp}-{uuid}
        # userId is a UUID with hyphens, questionId can have hyphens
        # Timestamp format: YYYYMMDD-HHMMSS (split into 2 parts by dash)
        # Format: transcript-34c884b8-7041-7009-dd6d-0a1f6b652e1c-childhood-00002-20251005-135904-959a511b
        if not job_name.startswith('transcript-'):
            print(f"Invalid job name format: {job_name}")
            return {'statusCode': 400, 'body': 'Invalid job name'}
        
        # Remove 'transcript-' prefix
        remainder = job_name[11:]  # Skip 'transcript-'
        
        # Split by dash
        parts = remainder.split('-')
        if len(parts) < 9:  # Minimum: 5 UUID parts + 1 questionId part + timestamp (2 parts) + uuid
            print(f"Invalid job name format: {job_name}")
            return {'statusCode': 400, 'body': 'Invalid job name'}
        
        # Last 3 parts are: timestamp_date (YYYYMMDD), timestamp_time (HHMMSS), uuid (8 chars)
        uuid_suffix = parts[-1]
        timestamp_time = parts[-2]
        timestamp_date = parts[-3]
        
        # Everything before timestamp is userId-questionId
        user_question_parts = parts[:-3]
        
        # UUID is always 5 parts (8-4-4-4-12 format)
        if len(user_question_parts) < 6:  # 5 UUID parts + at least 1 questionId part
            print(f"Invalid job name format: {job_name}")
            return {'statusCode': 400, 'body': 'Invalid job name'}
        
        # First 5 parts are userId (UUID format: 8-4-4-4-12)
        user_id = '-'.join(user_question_parts[:5])
        # Remaining parts are questionId
        question_id = '-'.join(user_question_parts[5:])
        
        print(f"Extracted: userId={user_id}, questionId={question_id}")
        
        if job_status == 'COMPLETED':
            process_completed_job(user_id, question_id, job_name)
        elif job_status == 'FAILED':
            process_failed_job(user_id, question_id, job_name)
        
        return {'statusCode': 200, 'body': json.dumps('Processing complete')}
        
    except Exception as e:
        print(f"Error in processTranscript: {str(e)}")
        raise

def process_completed_job(user_id, question_id, job_name):
    """Process successfully completed transcription job."""
    try:
        # Query DynamoDB to determine video type
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        record = response.get('Item', {})
        
        # Determine video type by matching job name
        if record.get('videoMemoryTranscriptionJobName') == job_name:
            video_type = 'video_memory'
            prefix = 'videoMemory'
            print(f"Detected video memory transcription")
        elif record.get('videoTranscriptionJobName') == job_name:
            video_type = 'regular_video'
            prefix = 'video'
            print(f"Detected regular video transcription")
        else:
            # Fallback for legacy records
            video_type = 'regular_video'
            prefix = 'video'
            print(f"Using fallback: regular video")
        
        print(f"Processing transcription: videoType={video_type}, prefix={prefix}")
        
        # Get job details from Transcribe
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        
        job = response['TranscriptionJob']
        transcript_file_uri = job['Transcript']['TranscriptFileUri']
        
        print(f"Transcript URI: {transcript_file_uri}")
        
        # Extract S3 key from URI
        # URI format: https://s3.region.amazonaws.com/bucket/key or s3://bucket/key
        if transcript_file_uri.startswith('s3://'):
            transcript_key = transcript_file_uri.replace(f"s3://{S3_BUCKET}/", "")
        else:
            transcript_key = transcript_file_uri.split(f"{S3_BUCKET}/")[1]
        
        # Download transcript from S3
        transcript_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=transcript_key)
        transcript_json = json.loads(transcript_obj['Body'].read().decode('utf-8'))
        transcript_text = transcript_json['results']['transcripts'][0]['transcript']
        
        print(f"Transcript retrieved: {len(transcript_text)} characters")
        
        # Create plain text transcript file
        txt_s3_location = None
        if transcript_text:
            txt_key = transcript_key.replace('.json', '.txt')
            try:
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=txt_key,
                    Body=transcript_text.encode('utf-8'),
                    ContentType='text/plain'
                )
                txt_s3_location = f"s3://{S3_BUCKET}/{txt_key}"
                print(f"Plain text transcript saved: {txt_s3_location}")
            except Exception as e:
                print(f"Warning: Failed to save plain text transcript: {str(e)}")
        
        # Determine storage strategy based on size
        if len(transcript_text) > MAX_TRANSCRIPT_SIZE:
            # Store only S3 location
            print(f"Transcript too large ({len(transcript_text)} chars), storing S3 location only")
            update_status = {
                f'{prefix}TranscriptionStatus': 'COMPLETED',
                f'{prefix}TranscriptionCompleteTime': datetime.now().isoformat(),
                f'{prefix}Transcript': None,
                f'{prefix}TranscriptS3Location': f"s3://{S3_BUCKET}/{transcript_key}",
                f'{prefix}TranscriptTextS3Location': txt_s3_location
            }
        else:
            # Store full transcript in DynamoDB
            update_status = {
                f'{prefix}TranscriptionStatus': 'COMPLETED',
                f'{prefix}TranscriptionCompleteTime': datetime.now().isoformat(),
                f'{prefix}Transcript': transcript_text,
                f'{prefix}TranscriptS3Location': f"s3://{S3_BUCKET}/{transcript_key}",
                f'{prefix}TranscriptTextS3Location': txt_s3_location
            }
        
        # Update DynamoDB
        update_question_status(user_id, question_id, update_status)
        print(f"Transcript stored successfully for {user_id}/{question_id}")
        
        # Trigger summarization asynchronously (non-blocking)
        if transcript_text and SUMMARIZE_FUNCTION_NAME:
            try:
                lambda_client.invoke(
                    FunctionName=SUMMARIZE_FUNCTION_NAME,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps({
                        'userId': user_id,
                        'questionId': question_id,
                        'transcript': transcript_text,
                        'videoType': video_type
                    })
                )
                print(f"✅ Triggered summarization for {user_id}/{question_id} (videoType={video_type})")
            except Exception as e:
                # Non-blocking: Don't fail transcript processing if summarization trigger fails
                print(f"⚠️ Failed to trigger summarization (non-critical): {e}")
        else:
            print(f"Skipping summarization: transcript_text={bool(transcript_text)}, function_name={SUMMARIZE_FUNCTION_NAME}")
        
    except Exception as e:
        print(f"Error processing completed job: {str(e)}")
        # Update status to failed
        update_question_status(user_id, question_id, {
            'transcriptionStatus': 'FAILED',
            'transcriptionCompleteTime': datetime.now().isoformat(),
            'transcriptionError': str(e)
        })
        raise

def process_failed_job(user_id, question_id, job_name):
    """Process failed transcription job."""
    try:
        # Query DynamoDB to determine video type
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        record = response.get('Item', {})
        
        # Determine video type by matching job name
        if record.get('videoMemoryTranscriptionJobName') == job_name:
            prefix = 'videoMemory'
        elif record.get('videoTranscriptionJobName') == job_name:
            prefix = 'video'
        else:
            prefix = 'video'  # Fallback
        
        # Get job details to extract error message
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        
        job = response['TranscriptionJob']
        failure_reason = job.get('FailureReason', 'Unknown error')
        
        print(f"Transcription failed: {failure_reason}")
        
        # Update DynamoDB with failure using correct field names
        update_question_status(user_id, question_id, {
            f'{prefix}TranscriptionStatus': 'FAILED',
            f'{prefix}TranscriptionCompleteTime': datetime.now().isoformat(),
            f'{prefix}TranscriptionError': failure_reason
        })
        
    except Exception as e:
        print(f"Error processing failed job: {str(e)}")
        raise

def update_question_status(user_id, question_id, updates):
    """Update userQuestionStatusDB with transcription results."""
    try:
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        
        # Build update expression dynamically
        update_expr_parts = []
        expr_attr_values = {}
        
        for key, value in updates.items():
            if value is not None:
                update_expr_parts.append(f"{key} = :{key}")
                expr_attr_values[f":{key}"] = value
        
        if not update_expr_parts:
            return
        
        update_expression = 'SET ' + ', '.join(update_expr_parts)
        
        table.update_item(
            Key={'userId': user_id, 'questionId': question_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_attr_values
        )
        
        print(f"Updated userQuestionStatusDB for {user_id}/{question_id}")
        
    except Exception as e:
        print(f"Error updating userQuestionStatusDB: {str(e)}")
        raise
