import json
import boto3
import sys
import os
import subprocess
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal
from cors import cors_headers
from responses import error_response


S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

# STREAK TRACKING MODULE IMPORTS
# Import streak calculation modules from same directory (copied during deployment)
# These modules handle timezone-aware date calculations and streak business logic
try:
    from timezone_utils import get_user_timezone, get_current_date_in_timezone, calculate_days_between
    from streak_calculator import calculate_new_streak, check_milestone
    STREAK_ENABLED = True
    print("✅ Streak modules loaded successfully")
except ImportError as e:
    # Graceful degradation: If modules fail to load, disable streak tracking
    # Video uploads will still succeed, but streak won't be updated
    print(f"❌ Streak modules not available: {e}")
    STREAK_ENABLED = False

# Custom JSON encoder to handle DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def update_user_streak(user_id: str) -> dict:
    """
    Update user's daily video submission streak after successful upload.
    
    BUSINESS RULES:
    - Same day upload: Streak count unchanged
    - Consecutive day: Streak increments by 1
    - Missed day with freeze available: Streak maintained, freeze consumed
    - Missed day without freeze: Streak resets to 1
    - Monthly reset: Freeze availability resets on 1st of each month
    - Milestones: Logged at 7, 30, and 100 day streaks
    
    NON-BLOCKING DESIGN:
    - Video upload always succeeds even if streak update fails
    - Returns current streak data or safe defaults on error
    - All exceptions are caught and logged
    
    Args:
        user_id: Cognito user ID (sub claim from JWT)
        
    Returns:
        dict: Streak data with keys:
            - streakCount: Current streak count
            - streakFreezeAvailable: Whether freeze is available
            - freezeUsed: Whether freeze was used (optional)
            - error: Error message if update failed (optional)
    """
    # Early return if streak modules failed to load
    if not STREAK_ENABLED:
        return {'streakCount': 0, 'streakFreezeAvailable': True, 'error': 'Streak tracking disabled'}
    
    try:
        # STEP 1: Get user's timezone and current date
        # Uses timezone from userStatusDB or defaults to UTC
        timezone = get_user_timezone(user_id)
        current_date = get_current_date_in_timezone(timezone)
        
        # STEP 2: Fetch existing streak data from EngagementDB
        dynamodb = boto3.resource('dynamodb')
        progress_table = dynamodb.Table(os.environ.get('TABLE_ENGAGEMENT', 'EngagementDB'))
        
        response = progress_table.get_item(Key={'userId': user_id})
        
        if 'Item' not in response:
            # FIRST VIDEO UPLOAD: Initialize streak record
            # New users start with streak count of 1 and freeze available
            progress_table.put_item(
                Item={
                    'userId': user_id,
                    'streakCount': 1,
                    'lastVideoDate': current_date,
                    'streakFreezeAvailable': True,
                    'createdAt': datetime.now().isoformat()
                }
            )
            print(f"Initialized streak for new user {user_id}")
            return {'streakCount': 1, 'streakFreezeAvailable': True}
        
        # EXISTING USER: Calculate new streak based on business rules
        item = response['Item']
        current_streak = int(item.get('streakCount', 0))
        last_video_date = item.get('lastVideoDate', current_date)
        freeze_available = item.get('streakFreezeAvailable', True)
        
        # Calculate days elapsed since last video upload
        days_since = calculate_days_between(last_video_date, current_date)
        
        # Apply streak business logic to determine new streak count
        # Returns: (new_streak, freeze_used, new_freeze_available)
        new_streak, freeze_used, new_freeze_available = calculate_new_streak(
            current_streak, days_since, freeze_available, last_video_date, current_date
        )
        
        # MILESTONE DETECTION: Check if user reached 7, 30, or 100 day streak
        milestone = check_milestone(new_streak, current_streak)
        if milestone:
            print(f"🎉 MILESTONE: User {user_id} reached {milestone}-day streak!")
            try:
                # Log milestone to CloudWatch for analytics and monitoring
                cloudwatch = boto3.client('cloudwatch')
                cloudwatch.put_metric_data(
                    Namespace='VirtualLegacy/Streaks',
                    MetricData=[{
                        'MetricName': 'MilestoneReached',
                        'Value': milestone,
                        'Unit': 'Count',
                        'Dimensions': [{'Name': 'UserId', 'Value': user_id}]
                    }]
                )
            except Exception as cw_error:
                # Non-critical: Don't fail streak update if CloudWatch fails
                print(f"CloudWatch metric failed (non-critical): {cw_error}")
        
        # PERSIST UPDATED STREAK DATA to EngagementDB
        # Note: Could add conditional expression to prevent race conditions in high-concurrency scenarios
        try:
            progress_table.put_item(
                Item={
                    'userId': user_id,
                    'streakCount': new_streak,
                    'lastVideoDate': current_date,
                    'streakFreezeAvailable': new_freeze_available,
                    'createdAt': item.get('createdAt', datetime.now().isoformat()),
                    'lastUpdated': datetime.now().isoformat()
                }
            )
        except Exception as db_error:
            # Non-blocking: Return current data even if database update fails
            print(f"DynamoDB update failed: {db_error}")
            return {
                'streakCount': current_streak,
                'streakFreezeAvailable': freeze_available,
                'error': str(db_error)
            }
        
        # Log freeze usage for monitoring
        if freeze_used:
            print(f"❄️ Streak freeze used for user {user_id}")
        
        return {
            'streakCount': new_streak,
            'streakFreezeAvailable': new_freeze_available,
            'freezeUsed': freeze_used
        }
        
    except Exception as e:
        # GRACEFUL DEGRADATION: Catch all exceptions to prevent video upload failure
        print(f"Error updating streak for {user_id}: {e}")
        # Return safe default values - video upload succeeds regardless
        return {'streakCount': 0, 'streakFreezeAvailable': True, 'error': 'A server error occurred. Please try again.'}

def lambda_handler(event, context):
    # Handle CORS preflight OPTIONS request
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
    
    # Extract and validate authenticated user ID from JWT token
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}
        print(f"[VIDEO MEMORY] Request body: {body}")
        
        # Extract required parameters
        question_id = body.get('questionId')
        question_type = body.get('questionType')
        s3_key = body.get('s3Key')  # Video already uploaded to S3
        filename = body.get('filename')
        question_text = body.get('questionText', '')
        is_video_memory = body.get('isVideoMemory', False)  # Flag for video memory recording
        print(f"[VIDEO MEMORY] isVideoMemory flag: {is_video_memory}")
        
        if not all([question_id, question_type, s3_key, filename]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'error': 'Missing required parameters: questionId, questionType, s3Key, filename'
                }, cls=DecimalEncoder)
            }
        
        # Verify video exists in S3
        s3_client = boto3.client('s3')
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        except ClientError:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Video not found in S3'}, cls=DecimalEncoder)
            }
        
        # THUMBNAIL GENERATION (NON-BLOCKING)
        # Generate thumbnail asynchronously - video upload succeeds regardless of thumbnail result
        # This implements graceful degradation: core functionality (video upload) is never blocked
        # by auxiliary features (thumbnail generation)
        thumbnail_filename = None
        try:
            thumbnail_filename = generate_thumbnail(s3_key, user_id)
            print(f"Thumbnail generated successfully: {thumbnail_filename}")
        except Exception as e:
            print(f"Thumbnail generation failed (non-critical): {str(e)}")
            # GRACEFUL DEGRADATION: Continue with video upload success even if thumbnail fails
            # This ensures users can always upload videos, thumbnails are a nice-to-have feature
        
        # Update DynamoDB
        update_user_question_status(user_id, question_id, question_type, filename, s3_key, question_text, thumbnail_filename, is_video_memory)
        
        # Update progress in userQuestionLevelProgressDB (only for regular videos, not video memories)
        if not is_video_memory:
            update_user_progress(user_id, question_id, question_type)
        
        # INVALIDATE USER COMPLETED COUNT CACHE
        try:
            ssm_client = boto3.client('ssm')
            cache_param = f'/virtuallegacy/user_completed_count/{user_id}'
            ssm_client.delete_parameter(Name=cache_param)
            print(f"✅ Invalidated completed count cache for user {user_id}")
        except Exception as cache_error:
            if 'ParameterNotFound' not in str(cache_error):
                print(f"⚠️ Cache invalidation failed (non-critical): {cache_error}")
        
        # STREAK TRACKING: Update user's daily video submission streak (only for regular videos)
        # Non-blocking: Video upload succeeds even if streak update fails
        streak_data = {}
        if not is_video_memory:
            print(f"🔥 Calling update_user_streak for user {user_id}, STREAK_ENABLED={STREAK_ENABLED}")
            streak_data = update_user_streak(user_id)
            print(f"🔥 Streak update returned: {streak_data}")
        else:
            print(f"[VIDEO MEMORY] Skipping streak update for video memory")
        
        # Create response with streak data for frontend display
        response_body = {
            'message': 'Video processed successfully',
            'filename': filename,
            's3Key': s3_key,
            'streakData': streak_data  # Include streak info for UI update
        }
        
        if thumbnail_filename:
            response_body['thumbnailFilename'] = thumbnail_filename
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps(response_body, cls=DecimalEncoder)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }

def update_user_question_status(user_id, question_id, question_type, filename, s3_key, question_text, thumbnail_filename, is_video_memory):
    """Update userQuestionStatusDB with the video response."""
    try:
        print(f"[VIDEO MEMORY] Updating question status - isVideoMemory: {is_video_memory}")
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB'))
        
        if is_video_memory:
            print(f"[VIDEO MEMORY] Updating video memory fields for {question_id}")
            
            # Check if item exists first
            try:
                existing_item = table.get_item(Key={'userId': user_id, 'questionId': question_id})
                if 'Item' not in existing_item:
                    print(f"[VIDEO MEMORY] ERROR: No existing item found for userId={user_id}, questionId={question_id}")
                    print(f"[VIDEO MEMORY] Cannot add video memory to non-existent conversation record")
                    raise Exception(f"No conversation record found for question {question_id}. Complete an audio conversation first.")
                
                print(f"[VIDEO MEMORY] Found existing item, updating video memory fields")
            except Exception as e:
                if 'No conversation record' in str(e):
                    raise
                print(f"[VIDEO MEMORY] Error checking for existing item: {e}")
                raise
            
            # Video memory: Update existing item with video memory fields
            update_expression = 'SET videoType = :video_type, videoMemoryS3Location = :video_s3, videoMemoryRecorded = :recorded, videoMemoryTimestamp = :timestamp'
            expression_values = {
                ':video_type': 'video_memory',
                ':video_s3': f's3://virtual-legacy/{s3_key}',
                ':recorded': True,
                ':timestamp': datetime.now().isoformat()
            }
            
            if thumbnail_filename:
                update_expression += ', videoMemoryThumbnailS3Location = :thumb_s3'
                expression_values[':thumb_s3'] = f's3://virtual-legacy/user-responses/{user_id}/{thumbnail_filename}'
            
            print(f"[VIDEO MEMORY] Update expression: {update_expression}")
            
            response = table.update_item(
                Key={'userId': user_id, 'questionId': question_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            print(f"[VIDEO MEMORY] DynamoDB update successful")
            
            # Trigger transcription for video memory if enabled
            try:
                user_status_table = dynamodb.Table(os.environ.get('TABLE_USER_STATUS', 'userStatusDB'))
                user_response = user_status_table.get_item(Key={'userId': user_id})
                allow_transcription = user_response.get('Item', {}).get('allowTranscription', False)
                
                if allow_transcription:
                    print(f"[VIDEO MEMORY] Triggering transcription for video memory")
                    lambda_client = boto3.client('lambda')
                    lambda_client.invoke(
                        FunctionName=os.environ.get('START_TRANSCRIPTION_FUNCTION_NAME'),
                        InvocationType='Event',
                        Payload=json.dumps({
                            'userId': user_id,
                            'questionId': question_id,
                            's3Key': s3_key,
                            'videoType': 'video_memory'
                        })
                    )
                    print(f"[VIDEO MEMORY] Transcription triggered successfully")
                else:
                    print(f"[VIDEO MEMORY] Transcription not enabled for user")
            except Exception as transcription_error:
                # Non-blocking: Don't fail video upload if transcription trigger fails
                print(f"[VIDEO MEMORY] Failed to trigger transcription (non-critical): {transcription_error}")
        else:
            # Regular video response: Create new item
            item = {
                'userId': user_id,
                'questionId': question_id,
                'questionType': question_type,
                'videoType': 'regular_video',
                'filename': filename,
                'videoS3Location': f's3://virtual-legacy/{s3_key}',
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'Question': question_text,
                'videoTranscriptionStatus': 'NOT_STARTED',
                'videoTranscriptionJobName': None,
                'videoTranscript': None,
                'videoTranscriptS3Location': None,
                'videoTranscriptTextS3Location': None,
                'enableTranscript': True,
                'videoSummarizationStatus': 'NOT_STARTED'
            }
            
            if thumbnail_filename:
                item['videoThumbnailS3Location'] = f's3://virtual-legacy/user-responses/{user_id}/{thumbnail_filename}'
            
            table.put_item(Item=item)
        
    except Exception as e:
        print(f"[VIDEO MEMORY] DynamoDB update error: {str(e)}")
        import traceback
        print(f"[VIDEO MEMORY] Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to update database: {str(e)}")

def update_user_progress(user_id, question_id, question_type):
    """Update progress in userQuestionLevelProgressDB after video submission"""
    try:
        dynamodb = boto3.resource('dynamodb')
        progress_table = dynamodb.Table(os.environ.get('TABLE_QUESTION_PROGRESS', 'userQuestionLevelProgressDB'))
        
        # Get current progress item
        response = progress_table.get_item(Key={'userId': user_id, 'questionType': question_type})
        if 'Item' not in response:
            return  # Skip if no progress record exists
            
        progress_item = response['Item']
        
        # Update progress
        progress_item['numQuestComplete'] = int(progress_item.get('numQuestComplete', 0)) + 1
        
        # Remove question from remaining lists
        remain_ids = progress_item.get('remainQuestAtCurrLevel', [])
        remain_texts = progress_item.get('remainQuestTextAtCurrLevel', [])
        
        if question_id in remain_ids:
            idx = remain_ids.index(question_id)
            remain_ids.remove(question_id)
            if idx < len(remain_texts):
                remain_texts.pop(idx)
        
        progress_item['remainQuestAtCurrLevel'] = remain_ids
        progress_item['remainQuestTextAtCurrLevel'] = remain_texts
        
        # Save updated progress
        progress_table.put_item(Item=progress_item)
        
    except Exception as e:
        print(f"Error updating progress: {str(e)}")
        # Don't fail the main upload if progress update fails

def generate_thumbnail(s3_key, user_id):
    """
    Generate a JPEG thumbnail from an uploaded video using FFmpeg.
    
    This function performs the complete thumbnail generation workflow:
    1. Locates FFmpeg binary from multiple possible paths (Lambda layer or system)
    2. Downloads the source video from S3 to Lambda's /tmp/ directory
    3. Uses FFmpeg to extract a frame at 5 seconds and resize to 200px width
    4. Uploads the generated thumbnail back to S3 in the same user folder
    5. Cleans up temporary files to prevent Lambda storage issues
    
    ARCHITECTURE REQUIREMENTS:
    - Lambda function must use x86_64 architecture to match FFmpeg binary
    - FFmpeg layer must be attached with ARN: arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1
    - Function needs 1024MB memory and 60s timeout for video processing
    
    S3 PERMISSIONS REQUIRED:
    - s3:GetObject on source video (user-responses/{user_id}/*)
    - s3:PutObject on thumbnail destination (user-responses/{user_id}/*)
    - No encryption conditions in IAM policy (they block read operations)
    
    FFMPEG PROCESSING:
    - Uses FFmpeg to detect video duration for optimal seek time selection
    - Automatically seeks to half of video duration for representative frame
    - Scales to 200px width maintaining aspect ratio
    - Outputs as JPEG for web compatibility and smaller file size
    - Uses -y flag to overwrite existing files without prompting
    
    ERROR HANDLING:
    - Graceful degradation: video upload succeeds even if thumbnail fails
    - Comprehensive logging for debugging FFmpeg issues
    - Automatic cleanup of temp files in finally block
    - Multiple FFmpeg path detection for different deployment scenarios
    
    Args:
        s3_key (str): S3 key of the uploaded video (e.g., 'user-responses/user123/video.webm')
        user_id (str): User ID for organizing thumbnails in S3 folder structure
        
    Returns:
        str: Filename of the generated thumbnail (e.g., 'video.jpg')
        
    Raises:
        Exception: If FFmpeg is not found, video download fails, thumbnail generation fails,
                  or S3 upload fails. All exceptions are caught by caller for graceful degradation.
                  
    Example:
        thumbnail_filename = generate_thumbnail('user-responses/user123/video.webm', 'user123')
        # Returns: 'video.jpg'
        # Creates: S3 object at 'user-responses/user123/video.jpg'
    """
    print(f"Starting thumbnail generation for {s3_key}")
    
    # FFMPEG BINARY DETECTION
    # Search multiple possible locations where FFmpeg might be installed
    # Lambda layers typically install to /opt/, but exact path varies by layer implementation
    ffmpeg_paths = [
        '/opt/bin/ffmpeg',      # Most common Lambda layer path
        '/opt/ffmpeg/ffmpeg',   # Alternative layer structure
        '/opt/chrome-aws-lambda/bin/ffmpeg',  # Chrome/Puppeteer layer path
        '/opt/nodejs/node_modules/chrome-aws-lambda/bin/ffmpeg',  # Node.js Chrome layer
        '/usr/bin/ffmpeg',      # System installation (rare in Lambda)
        'ffmpeg'                # PATH environment variable (fallback)
    ]
    
    # DEBUG: LAMBDA LAYER INSPECTION
    # List contents of /opt/ directory to help debug layer installation issues
    # Lambda layers are mounted at /opt/, this helps identify if layer is properly attached
    try:
        import os
        if os.path.exists('/opt/'):
            opt_contents = os.listdir('/opt/')
            print(f"Lambda layer contents (/opt/): {opt_contents}")
            # Recursively list subdirectories to find FFmpeg binary location
            for item in opt_contents:
                item_path = f'/opt/{item}'
                if os.path.isdir(item_path):
                    try:
                        sub_contents = os.listdir(item_path)
                        print(f"Layer subdirectory {item_path}: {sub_contents}")
                    except Exception as sub_e:
                        print(f"Cannot list {item_path}: {sub_e}")
    except Exception as e:
        print(f"Layer inspection failed: {e}")
    # FFMPEG BINARY VALIDATION
    # Test each potential path by running 'ffmpeg -version' command
    # This ensures the binary exists, is executable, and matches Lambda architecture
    ffmpeg_path = None
    
    for path in ffmpeg_paths:
        try:
            # Test FFmpeg binary with version command (lightweight test)
            result = subprocess.run([path, '-version'], check=True, capture_output=True, text=True)
            ffmpeg_path = path
            print(f"✓ FFmpeg found and validated at: {path}")
            print(f"FFmpeg version info: {result.stdout.split()[2] if len(result.stdout.split()) > 2 else 'unknown'}")
            break
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"✗ FFmpeg not found at {path}: {str(e)}")
            continue
        except Exception as e:
            print(f"✗ Unexpected error testing {path}: {str(e)}")
            continue
    
    # FFMPEG AVAILABILITY CHECK
    # If no FFmpeg binary found, fail gracefully with descriptive error
    if not ffmpeg_path:
        error_msg = (
            "FFmpeg binary not found in Lambda environment. "
            "Ensure FFmpeg layer is attached and Lambda architecture matches binary (x86_64). "
            "Layer ARN: arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1"
        )
        print(f"CRITICAL: {error_msg}")
        raise Exception(error_msg)
    
    # S3 CLIENT AND FILE PATH SETUP
    s3_client = boto3.client('s3')
    bucket_name = S3_BUCKET
    
    # THUMBNAIL FILE NAMING CONVENTION
    # Convert video filename to thumbnail filename (same base name, .jpg extension)
    # Example: 'childhood-00003_20250920_182806_0bdae653.webm' -> 'childhood-00003_20250920_182806_0bdae653.jpg'
    video_filename = os.path.basename(s3_key)
    thumbnail_filename = video_filename.replace('.webm', '.jpg')
    thumbnail_s3_key = f"user-responses/{user_id}/{thumbnail_filename}"  # Same folder as video
    
    # LAMBDA TEMPORARY FILE PATHS
    # Lambda provides /tmp/ directory with 512MB-10GB storage (depending on configuration)
    # Files are automatically cleaned up when Lambda container is recycled
    video_path = f"/tmp/{video_filename}"        # Temporary video file for FFmpeg input
    thumbnail_path = f"/tmp/{thumbnail_filename}"  # Temporary thumbnail file for FFmpeg output
    
    try:
        # STEP 1: DOWNLOAD VIDEO FROM S3
        # Download source video to Lambda's temporary storage for FFmpeg processing
        # Requires s3:GetObject permission on the video file
        print(f"📥 Downloading video from S3: {s3_key}")
        try:
            s3_client.download_file(bucket_name, s3_key, video_path)
            file_size = os.path.getsize(video_path)
            print(f"✓ Video downloaded successfully to {video_path} ({file_size} bytes)")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                error_msg = f"Video file not found in S3: {s3_key}"
            elif error_code == 'AccessDenied':
                error_msg = f"Access denied to S3 video file: {s3_key}. Check IAM permissions."
            else:
                error_msg = f"S3 download failed ({error_code}): {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error downloading video from S3: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        # STEP 2: SMART THUMBNAIL GENERATION WITH DURATION DETECTION
        # Use FFmpeg to detect duration, then make single optimal FFmpeg call
        
        # Detect video duration using FFmpeg
        duration = get_video_duration(video_path, ffmpeg_path)
        if duration:
            print(f"📏 Detected video duration: {duration:.2f} seconds")
        else:
            print("⚠️ Could not detect duration, using safe fallback")
        
        # Calculate optimal seek time (half of duration)
        seek_time = calculate_seek_time(duration)
        seek_desc = "first frame" if seek_time == '0' else f"{seek_time}s"
        print(f"🎯 Using seek time: {seek_desc}")
        
        # Build FFmpeg command with optimal seek time
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-ss', seek_time,
            '-vframes', '1',
            '-vf', 'scale=200:-1',
            '-y',
            thumbnail_path
        ]
        
        print(f"🎬 Executing FFmpeg: {' '.join(cmd)}")
        
        try:
            # Single FFmpeg call with half-duration seek time
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout.strip():
                print(f"FFmpeg stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"FFmpeg stderr: {result.stderr.strip()}")
            
            print(f"✓ Thumbnail generated successfully with {seek_desc}")
            
        except subprocess.TimeoutExpired:
            raise Exception(f"FFmpeg processing timed out after 30 seconds (seek: {seek_desc})")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg failed with return code {e.returncode}")
            print(f"FFmpeg stdout: {e.stdout}")
            print(f"FFmpeg stderr: {e.stderr}")
            raise Exception(f"FFmpeg failed: {e.stderr or 'Unknown error'}")
        
        # STEP 3: VERIFY THUMBNAIL CREATION
        # Ensure FFmpeg actually created the output file
        if not os.path.exists(thumbnail_path):
            duration_info = f" (duration: {duration:.2f}s, seek: {seek_time}s)" if duration else f" (seek: {seek_time}s)"
            error_msg = f"Thumbnail file not created{duration_info}. Video may be corrupted or invalid."
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        # Verify thumbnail file has content (not empty)
        thumbnail_size = os.path.getsize(thumbnail_path)
        if thumbnail_size == 0:
            error_msg = "Generated thumbnail file is empty"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        print(f"✓ Thumbnail created successfully: {thumbnail_size} bytes")
        
        # STEP 4: UPLOAD THUMBNAIL TO S3
        # Upload generated thumbnail to same S3 folder as source video
        # Requires s3:PutObject permission on the thumbnail destination
        print(f"📤 Uploading thumbnail to S3: {thumbnail_s3_key}")
        try:
            s3_client.upload_file(
                thumbnail_path,
                bucket_name,
                thumbnail_s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',        # Proper MIME type for web display
                    'ServerSideEncryption': 'AES256',    # Match video encryption settings
                    'CacheControl': 'max-age=31536000'   # Cache for 1 year (thumbnails rarely change)
                }
            )
            print(f"✓ Thumbnail uploaded successfully: {thumbnail_filename}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                error_msg = f"Access denied uploading thumbnail to S3: {thumbnail_s3_key}. Check IAM permissions."
            else:
                error_msg = f"S3 thumbnail upload failed ({error_code}): {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error uploading thumbnail to S3: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        return thumbnail_filename
        
    finally:
        # CLEANUP: REMOVE TEMPORARY FILES
        # Always clean up temp files to prevent Lambda /tmp/ storage exhaustion
        # Lambda containers may be reused, so cleanup is critical for performance
        cleanup_files = [video_path, thumbnail_path]
        for temp_file in cleanup_files:
            if os.path.exists(temp_file):
                try:
                    file_size = os.path.getsize(temp_file)
                    os.remove(temp_file)
                    print(f"🧹 Cleaned up temp file: {temp_file} ({file_size} bytes)")
                except Exception as e:
                    # Log cleanup failures but don't raise exceptions
                    # Cleanup failures shouldn't break the main workflow
                    print(f"⚠️ Failed to clean up temp file {temp_file}: {str(e)}")
        
        # Log final /tmp/ directory status for monitoring
        try:
            tmp_usage = sum(os.path.getsize(os.path.join('/tmp', f)) 
                          for f in os.listdir('/tmp') 
                          if os.path.isfile(os.path.join('/tmp', f)))
            print(f"📊 /tmp/ directory usage after cleanup: {tmp_usage} bytes")
        except Exception as e:
            print(f"Could not calculate /tmp/ usage: {e}")

def get_video_duration(video_path, ffmpeg_path):
    """
    Get video duration using FFmpeg stderr parsing.
    
    Args:
        video_path (str): Path to video file
        ffmpeg_path (str): Path to ffmpeg binary
        
    Returns:
        float: Duration in seconds, or None if detection fails
    """
    try:
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-f', 'null', '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Parse stderr for duration line
        import re
        duration_pattern = r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})'
        match = re.search(duration_pattern, result.stderr)
        
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
            return total_seconds
        
        return None
        
    except Exception as e:
        print(f"⚠️ Duration detection failed: {e}")
        return None

def calculate_seek_time(duration):
    """
    Calculate seek time as half of video duration.
    
    Args:
        duration (float or None): Video duration in seconds
        
    Returns:
        str: Seek time for FFmpeg
    """
    if duration is None:
        return '0.5'  # Fallback when duration unknown
    
    return str(duration / 2.0)