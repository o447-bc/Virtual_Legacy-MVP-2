"""
Speech Synthesis Module
Converts text to speech using Amazon Polly
"""

import os
import base64
import boto3
from botocore.client import Config
from datetime import datetime

polly = boto3.client('polly', region_name='us-east-1')
# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

def text_to_speech(text: str, user_id: str, question_id: str, turn_number: int, voice_id: str, engine: str) -> str:
    """Convert text to speech, upload to S3, and return presigned URL.

    For turn 0 (initial question greeting), uses a shared cache key so the
    same question text is only synthesized once across all users. Turns 1+
    are unique per conversation and always synthesized fresh.
    """
    
    try:
        kms_key_arn = os.environ.get('KMS_KEY_ARN')
        if not kms_key_arn:
            print(f"[POLLY] ERROR: KMS_KEY_ARN environment variable not set")
            raise ValueError("KMS_KEY_ARN environment variable not set")

        # For turn 0, check shared cache first
        if turn_number == 0:
            cache_key = f"polly-cache/{question_id}/{voice_id}-{engine}.mp3"
            try:
                s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
                # Cache hit — generate presigned URL and return
                audio_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': cache_key},
                    ExpiresIn=3600,
                )
                print(f"[POLLY] Cache hit for {cache_key}")
                return audio_url
            except s3_client.exceptions.ClientError:
                # Cache miss — will synthesize below
                print(f"[POLLY] Cache miss for {cache_key}, synthesizing...")

        print(f"[POLLY] Synthesizing speech: {len(text)} characters")
        print(f"[POLLY] Voice: {voice_id}, Engine: {engine}")
        
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_id,
            Engine=engine
        )
        
        audio_data = response['AudioStream'].read()
        print(f"[POLLY] Audio generated: {len(audio_data)} bytes")
        
        # Determine S3 key
        if turn_number == 0:
            # Store at shared cache key for reuse across users
            s3_key = f"polly-cache/{question_id}/{voice_id}-{engine}.mp3"
        else:
            # Per-user key for follow-up responses (unique per conversation)
            timestamp = int(datetime.now().timestamp())
            s3_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}-{timestamp}.mp3"
        
        print(f"[POLLY] Uploading to s3://{S3_BUCKET}/{s3_key}")
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=audio_data,
            ContentType='audio/mpeg',
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=kms_key_arn
        )
        
        print(f"[POLLY] S3 upload successful")
        
        # Generate presigned URL (valid for 1 hour)
        audio_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        print(f"[POLLY] Presigned URL generated successfully")
        
        return audio_url
        
    except Exception as e:
        print(f"[POLLY] ERROR in text_to_speech: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[POLLY] Traceback: {traceback.format_exc()}")
        raise
