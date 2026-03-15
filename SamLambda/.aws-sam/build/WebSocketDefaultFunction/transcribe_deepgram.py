import boto3
from botocore.client import Config
import requests
import time
import os

S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
ssm_client = boto3.client('ssm', region_name='us-east-1')
# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', region_name='us-east-1', config=Config(signature_version='s3v4'))

# Cache API key
_api_key_cache = None

def get_deepgram_api_key():
    """Get Deepgram API key from SSM Parameter Store (cached)"""
    global _api_key_cache
    if _api_key_cache:
        return _api_key_cache
    
    response = ssm_client.get_parameter(
        Name='/virtuallegacy/deepgram/api-key',
        WithDecryption=True
    )
    _api_key_cache = response['Parameter']['Value']
    return _api_key_cache

def transcribe_audio_deepgram(s3_key: str, user_id: str, question_id: str, turn_number: int) -> dict:
    """
    Transcribe audio using Deepgram API
    Returns: {'transcript': str, 'audio_url': str}
    """
    total_start = time.time()
    print(f"[DEEPGRAM] Starting transcription for {s3_key}")
    
    try:
        # Get API key
        api_key = get_deepgram_api_key()
        
        # Generate presigned S3 URL (5 min expiry)
        presigned_start = time.time()
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=300
        )
        presigned_time = time.time() - presigned_start
        print(f"[DEEPGRAM] Generated presigned URL in {presigned_time:.2f}s")
        
        # Call Deepgram API
        api_start = time.time()
        response = requests.post(
            'https://api.deepgram.com/v1/listen',
            headers={
                'Authorization': f'Token {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'url': presigned_url
            },
            params={
                'model': 'nova-2',
                'language': 'en',
                'punctuate': 'true',
                'smart_format': 'true'
            },
            timeout=30
        )
        api_time = time.time() - api_start
        print(f"[DEEPGRAM] API call took {api_time:.2f}s")
        
        # Check response
        if response.status_code != 200:
            raise Exception(f"Deepgram API error: {response.status_code} - {response.text}")
        
        # Parse transcript
        result = response.json()
        transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
        confidence = result['results']['channels'][0]['alternatives'][0]['confidence']
        
        audio_url = f"s3://{S3_BUCKET}/{s3_key}"
        
        total_time = time.time() - total_start
        print(f"[DEEPGRAM] TOTAL TIME: {total_time:.2f}s (presigned: {presigned_time:.2f}s, api: {api_time:.2f}s)")
        print(f"[DEEPGRAM] Transcript ({len(transcript)} chars, confidence: {confidence:.2f}): {transcript}")
        
        return {
            'transcript': transcript,
            'audio_url': audio_url
        }
        
    except Exception as e:
        total_time = time.time() - total_start
        print(f"[DEEPGRAM] Error after {total_time:.2f}s: {e}")
        raise
