import json
import boto3
import os
import uuid
from datetime import datetime
from urllib.parse import unquote_plus

transcribe_client = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
TRANSCRIBE_ROLE_ARN = os.environ.get('TRANSCRIBE_ROLE_ARN', '')

def lambda_handler(event, context):
    """
    Triggered by S3 PUT event when video uploaded OR direct invocation.
    Checks user's allowTranscription flag and starts Transcribe job if allowed.
    """
    try:
        # Detect event source: S3 event or direct invocation
        if 'Records' in event:
            # S3 event
            for record in event['Records']:
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                video_type = None  # Will be detected from DynamoDB
                
                print(f"Processing S3 event: s3://{bucket}/{key}")
                
                # Parse S3 key: user-responses/{userId}/{questionId}_{timestamp}_{uuid}.webm
                parts = key.split('/')
                if len(parts) < 3 or not key.endswith('.webm'):
                    print(f"Skipping invalid S3 key format: {key}")
                    continue
                
                user_id = parts[1]
                filename = parts[2]
                question_id = filename.split('_')[0]
                
                print(f"Extracted: userId={user_id}, questionId={question_id}")
                process_transcription(user_id, question_id, bucket, key, video_type)
        else:
            # Direct invocation
            user_id = event['userId']
            question_id = event['questionId']
            s3_key = event['s3Key']
            video_type = event.get('videoType')
            
            print(f"Processing direct invocation: userId={user_id}, questionId={question_id}, videoType={video_type}")
            
            bucket = S3_BUCKET
            process_transcription(user_id, question_id, bucket, s3_key, video_type)
        
        return {'statusCode': 200, 'body': json.dumps('Processing complete')}
        
    except Exception as e:
        print(f"Error in startTranscription: {str(e)}")
        emit_metric('TranscriptionError', 1)
        raise

def process_transcription(user_id, question_id, bucket, key, explicit_video_type):
    """Process transcription for a video."""
    try:
        # Query DynamoDB for existing record
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        response = table.get_item(Key={'userId': user_id, 'questionId': question_id})
        existing_record = response.get('Item')
        
        # Determine video type
        if explicit_video_type:
            video_type = explicit_video_type
            print(f"Using explicit video type: {video_type}")
        elif existing_record and existing_record.get('videoMemoryS3Location'):
            video_type = 'video_memory'
            print(f"Detected video memory from videoMemoryS3Location")
        else:
            video_type = 'regular_video'
            print(f"Defaulting to regular video")
        
        # Set field prefix
        prefix = 'videoMemory' if video_type == 'video_memory' else 'video'
        
        # Check idempotency - skip if transcription already started
        if existing_record:
            if existing_record.get('videoMemoryTranscriptionJobName'):
                print(f"Transcription already started (videoMemoryTranscriptionJobName exists), skipping")
                return
            if existing_record.get('videoTranscriptionJobName'):
                print(f"Transcription already started (videoTranscriptionJobName exists), skipping")
                return
        
        print(f"Video type: {video_type}, field prefix: {prefix}")
            
        # Check transcription flag in userStatusDB
        allowed = check_transcription_flag(user_id)
        
        if not allowed:
            print(f"Transcription not allowed for user {user_id}")
            emit_metric('TranscriptionDenied', 1)
            return
        
        # Start transcription job
        job_name = start_transcription_job(user_id, question_id, bucket, key)
        
        # Update userQuestionStatusDB with correct field names
        update_question_status(user_id, question_id, job_name, prefix)
        
        emit_metric('TranscriptionAllowed', 1)
        print(f"Transcription started: {job_name} (type: {video_type})")
        
    except Exception as e:
        print(f"Error processing transcription: {str(e)}")
        emit_metric('TranscriptionError', 1)
        raise

def check_transcription_flag(user_id):
    """
    Check if user has transcription enabled in userStatusDB.
    Creates record with allowTranscription=false if missing.
    Returns True if allowed, False otherwise.
    """
    try:
        table = dynamodb.Table(os.environ.get('TABLE_USER_STATUS', 'userStatusDB'))
        response = table.get_item(Key={'userId': user_id})
        
        if 'Item' not in response:
            # User record doesn't exist, create with allowTranscription=true
            print(f"User {user_id} not in userStatusDB, creating with allowTranscription=true")
            table.put_item(Item={
                'userId': user_id,
                'allowTranscription': True,
                'createdAt': datetime.now().isoformat()
            })
            return True
        
        item = response['Item']
        
        # Check if allowTranscription attribute exists
        if 'allowTranscription' not in item:
            # Attribute missing, add it with default true
            print(f"allowTranscription missing for user {user_id}, setting to true")
            table.put_item(Item={**item, 'allowTranscription': True})
            return True
        
        return bool(item['allowTranscription'])
        
    except Exception as e:
        print(f"Error checking transcription flag: {str(e)}")
        # Fail closed - don't transcribe if we can't check the flag
        return False

def start_transcription_job(user_id, question_id, bucket, key):
    """
    Start Amazon Transcribe job for the video.
    Returns job name.
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    job_name = f"transcript-{user_id}-{question_id}-{timestamp}-{str(uuid.uuid4())[:8]}"
    
    media_uri = f"s3://{bucket}/{key}"
    
    # Store transcript alongside video with matching filename
    # Extract video filename and replace .webm with .json
    video_filename = key.split('/')[-1]  # childhood-00001_20250105_123456_a3f2.webm
    base_filename = video_filename.replace('.webm', '')  # childhood-00001_20250105_123456_a3f2
    output_key = f"user-responses/{user_id}/{base_filename}.json"
    
    try:
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat='webm',
            LanguageCode='en-US',
            OutputBucketName=S3_BUCKET,
            OutputKey=output_key,
            Settings={
                'ShowSpeakerLabels': False
            },
            JobExecutionSettings={
                'AllowDeferredExecution': True,
                'DataAccessRoleArn': TRANSCRIBE_ROLE_ARN
            }
        )
        
        print(f"Started Transcribe job: {job_name}")
        return job_name
        
    except transcribe_client.exceptions.ConflictException:
        # Job already exists (duplicate S3 event) - this is OK
        print(f"Transcribe job {job_name} already exists (idempotent)")
        return job_name
    except Exception as e:
        print(f"Error starting Transcribe job: {str(e)}")
        raise

def update_question_status(user_id, question_id, job_name, prefix):
    """
    Update userQuestionStatusDB with transcription job info using correct field names.
    """
    try:
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        table.update_item(
            Key={'userId': user_id, 'questionId': question_id},
            UpdateExpression=f'SET {prefix}TranscriptionJobName = :job, {prefix}TranscriptionStatus = :status, {prefix}TranscriptionStartTime = :time',
            ExpressionAttributeValues={
                ':job': job_name,
                ':status': 'IN_PROGRESS',
                ':time': datetime.now().isoformat()
            }
        )
        print(f"Updated userQuestionStatusDB for {user_id}/{question_id} with {prefix} prefix")
    except Exception as e:
        # Log but don't fail - transcription job already started
        print(f"Error updating userQuestionStatusDB: {str(e)}")

def emit_metric(metric_name, value):
    """Emit CloudWatch metric for monitoring."""
    try:
        cloudwatch.put_metric_data(
            Namespace='VirtualLegacy/Transcription',
            MetricData=[{
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.now()
            }]
        )
    except Exception as e:
        print(f"Error emitting metric {metric_name}: {str(e)}")
