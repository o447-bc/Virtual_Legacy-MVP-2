"""
Speech Synthesis Module
Converts text to speech using Amazon Polly
"""

import base64
import boto3
from botocore.client import Config
from datetime import datetime

polly = boto3.client('polly', region_name='us-east-1')
# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

S3_BUCKET = 'virtual-legacy'

def text_to_speech(text: str, user_id: str, question_id: str, turn_number: int, voice_id: str, engine: str) -> str:
    """Convert text to speech, upload to S3, and return S3 URL"""
    
    try:
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
        
        # Upload to S3 with KMS encryption
        timestamp = int(datetime.now().timestamp())
        s3_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}-{timestamp}.mp3"
        
        # Get KMS key ARN from environment
        import os
        kms_key_arn = os.environ.get('KMS_KEY_ARN')
        
        if not kms_key_arn:
            print(f"[POLLY] ERROR: KMS_KEY_ARN environment variable not set")
            raise ValueError("KMS_KEY_ARN environment variable not set")
        
        print(f"[POLLY] Uploading to s3://{S3_BUCKET}/{s3_key}")
        print(f"[POLLY] Using KMS encryption with key: {kms_key_arn}")
        
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
        print(f"[POLLY] URL length: {len(audio_url)} characters")
        
        return audio_url
        
    except Exception as e:
        print(f"[POLLY] ERROR in text_to_speech: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"[POLLY] Traceback: {traceback.format_exc()}")
        raise
