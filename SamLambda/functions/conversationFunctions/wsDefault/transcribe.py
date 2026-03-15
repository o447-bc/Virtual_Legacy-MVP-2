"""
Transcription Module
Handles audio transcription using AWS Transcribe
"""

import boto3
from botocore.client import Config
import time
from datetime import datetime

# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
transcribe_client = boto3.client('transcribe')

S3_BUCKET = 'virtual-legacy'

def transcribe_audio(s3_key: str, user_id: str, question_id: str, turn_number: int) -> dict:
    """
    Transcribe audio from S3 using AWS Transcribe
    
    Args:
        s3_key: S3 key where audio is already stored
        user_id: User ID for job naming
        question_id: Question ID for job naming
        turn_number: Turn number for job naming
    
    Returns:
        dict: {'transcript': str, 'audio_url': str}
    """
    
    print(f"[TRANSCRIBE] Starting transcription for user {user_id}, question {question_id}, turn {turn_number}")
    
    try:
        # Use existing S3 file
        audio_url = f"s3://{S3_BUCKET}/{s3_key}"
        print(f"[TRANSCRIBE] Using audio from: {audio_url}")
        
        # Start transcription job (sanitize user_id for job name)
        timestamp = int(datetime.now().timestamp())
        safe_user_id = user_id.replace('@', '-').replace('.', '-')[:50]
        job_name = f"{safe_user_id}-{question_id}-turn{turn_number}-{timestamp}"
        print(f"[TRANSCRIBE] Starting job: {job_name}")
        
        # Transcribe supports: mp3, mp4, wav, flac, ogg, amr, webm
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': audio_url},
            MediaFormat='webm',
            LanguageCode='en-US'
        )
        
        # Poll for completion (max 60 seconds)
        max_attempts = 120  # 120 * 0.5s = 60 seconds
        for attempt in range(max_attempts):
            time.sleep(0.5)
            
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            print(f"[TRANSCRIBE] Attempt {attempt + 1}/{max_attempts}: Status = {status}")
            
            if status == 'COMPLETED':
                # Get transcript
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                print(f"[TRANSCRIBE] Job completed: {transcript_uri}")
                
                # Fetch transcript
                import urllib.request
                import json
                with urllib.request.urlopen(transcript_uri) as response:
                    transcript_data = json.loads(response.read())
                
                transcript = transcript_data['results']['transcripts'][0]['transcript']
                print(f"[TRANSCRIBE] Transcript: {transcript}")
                
                return {
                    'transcript': transcript,
                    'audio_url': audio_url
                }
            
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
                print(f"[TRANSCRIBE] Job failed: {failure_reason}")
                raise Exception(f"Transcription failed: {failure_reason}")
        
        # Timeout
        print(f"[TRANSCRIBE] Timeout waiting for transcription")
        raise Exception("Transcription timeout - audio may be too long")
        
    except Exception as e:
        print(f"[TRANSCRIBE] Error: {e}")
        raise
