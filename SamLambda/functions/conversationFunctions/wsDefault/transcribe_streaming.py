"""
Streaming Transcription Module
Handles audio transcription using Amazon Transcribe Streaming API for faster results
"""

import boto3
from botocore.client import Config
import subprocess
import os
import asyncio
import time
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

# Configure S3 client to use Signature Version 4 (required for KMS-encrypted objects)
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
S3_BUCKET = 'virtual-legacy'

class TranscriptHandler(TranscriptResultStreamHandler):
    """Handler for processing streaming transcript events"""
    
    def __init__(self, stream):
        super().__init__(stream)
        self.transcript = ""
    
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Process transcript events and extract final results"""
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:
                for alt in result.alternatives:
                    self.transcript += alt.transcript + " "

def convert_webm_to_pcm(webm_path: str, pcm_path: str) -> bool:
    """
    Convert WebM audio to PCM 16kHz WAV format using ffmpeg
    
    Args:
        webm_path: Path to input WebM file
        pcm_path: Path to output PCM WAV file
    
    Returns:
        bool: True if conversion successful
    """
    print(f"[STREAMING] Converting {webm_path} to PCM")
    
    # Find ffmpeg binary
    ffmpeg_paths = [
        '/opt/bin/ffmpeg',
        '/opt/ffmpeg/ffmpeg',
        '/usr/bin/ffmpeg',
        'ffmpeg'
    ]
    
    ffmpeg_path = None
    for path in ffmpeg_paths:
        if os.path.exists(path) or path == 'ffmpeg':
            try:
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    ffmpeg_path = path
                    print(f"[STREAMING] Found ffmpeg at: {path}")
                    break
            except:
                continue
    
    if not ffmpeg_path:
        raise Exception("ffmpeg not found - cannot convert audio")
    
    # Convert WebM to PCM 16kHz mono WAV
    # -i: input file
    # -ar 16000: sample rate 16kHz (required by Transcribe)
    # -ac 1: mono audio
    # -f s16le: PCM signed 16-bit little-endian
    cmd = [
        ffmpeg_path,
        '-i', webm_path,
        '-ar', '16000',
        '-ac', '1',
        '-f', 'wav',
        '-y',  # Overwrite output file
        pcm_path
    ]
    
    print(f"[STREAMING] Running ffmpeg: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=20,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[STREAMING] ffmpeg error: {result.stderr}")
            raise Exception(f"ffmpeg conversion failed: {result.stderr}")
        
        if not os.path.exists(pcm_path):
            raise Exception("PCM file not created")
        
        file_size = os.path.getsize(pcm_path)
        print(f"[STREAMING] Conversion successful: {file_size} bytes")
        return True
        
    except subprocess.TimeoutExpired:
        raise Exception("ffmpeg conversion timeout")
    except Exception as e:
        raise Exception(f"ffmpeg conversion error: {e}")

async def stream_audio_to_transcribe(pcm_path: str) -> str:
    """
    Stream PCM audio to Amazon Transcribe Streaming API
    
    Args:
        pcm_path: Path to PCM WAV file
    
    Returns:
        str: Transcribed text
    """
    print(f"[STREAMING] Starting Transcribe streaming for {pcm_path}")
    
    client = TranscribeStreamingClient(region="us-east-1")
    
    # Read audio file
    with open(pcm_path, 'rb') as audio_file:
        audio_data = audio_file.read()
    
    file_size = len(audio_data)
    print(f"[STREAMING] Audio size: {file_size} bytes")
    
    # Create audio stream generator
    async def audio_stream():
        # Validate WAV header
        if len(audio_data) > 44:
            if audio_data[:4] != b'RIFF' or audio_data[8:12] != b'WAVE':
                print(f"[STREAMING] Warning: Unexpected WAV header format")
        
        # Skip WAV header (44 bytes) and send raw PCM data
        chunk_size = 1024 * 16  # 16KB chunks (increased from 8KB)
        audio_pcm = audio_data[44:]  # Skip WAV header
        pcm_size = len(audio_pcm)
        print(f"[STREAMING] PCM data size: {pcm_size} bytes (after header)")
        
        chunks_sent = 0
        for i in range(0, pcm_size, chunk_size):
            chunk = audio_pcm[i:i + chunk_size]
            yield chunk
            chunks_sent += 1
            await asyncio.sleep(0.003)  # 3ms delay (reduced from 10ms)
        
        print(f"[STREAMING] Sent {chunks_sent} chunks")
    
    # Start streaming transcription
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    
    # Create handler
    handler = TranscriptHandler(stream.output_stream)
    
    # Send audio and process results concurrently
    await asyncio.gather(
        write_audio_stream(stream, audio_stream()),
        handler.handle_events()
    )
    
    transcript = handler.transcript.strip()
    print(f"[STREAMING] Transcript: {transcript}")
    
    return transcript

async def write_audio_stream(stream, audio_generator):
    """Write audio chunks to the stream"""
    async for chunk in audio_generator:
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()

def transcribe_audio_streaming(s3_key: str, user_id: str, question_id: str, turn_number: int) -> dict:
    """
    Transcribe audio using streaming API (faster than batch)
    
    Args:
        s3_key: S3 key where audio is stored
        user_id: User ID
        question_id: Question ID
        turn_number: Turn number
    
    Returns:
        dict: {'transcript': str, 'audio_url': str}
    """
    total_start = time.time()
    print(f"[STREAMING] Starting streaming transcription for {s3_key}")
    
    webm_path = None
    pcm_path = None
    
    try:
        # Download WebM from S3
        webm_path = f"/tmp/audio_{turn_number}.webm"
        pcm_path = f"/tmp/audio_{turn_number}.wav"
        
        download_start = time.time()
        print(f"[STREAMING] Downloading from S3: {s3_key}")
        s3_client.download_file(S3_BUCKET, s3_key, webm_path)
        download_time = time.time() - download_start
        
        webm_size = os.path.getsize(webm_path)
        print(f"[STREAMING] Downloaded: {webm_size} bytes in {download_time:.2f}s")
        
        # Convert to PCM
        convert_start = time.time()
        convert_webm_to_pcm(webm_path, pcm_path)
        convert_time = time.time() - convert_start
        print(f"[STREAMING] Conversion took {convert_time:.2f}s")
        
        # Stream to Transcribe
        transcribe_start = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            transcript = loop.run_until_complete(stream_audio_to_transcribe(pcm_path))
        finally:
            loop.close()
        transcribe_time = time.time() - transcribe_start
        print(f"[STREAMING] Transcription took {transcribe_time:.2f}s")
        
        audio_url = f"s3://{S3_BUCKET}/{s3_key}"
        
        total_time = time.time() - total_start
        print(f"[STREAMING] TOTAL TIME: {total_time:.2f}s (download: {download_time:.2f}s, convert: {convert_time:.2f}s, transcribe: {transcribe_time:.2f}s)")
        
        return {
            'transcript': transcript,
            'audio_url': audio_url
        }
        
    except Exception as e:
        elapsed = time.time() - total_start
        print(f"[STREAMING] Error after {elapsed:.2f}s: {e}")
        raise
        
    finally:
        # Cleanup temp files
        if webm_path and os.path.exists(webm_path):
            os.remove(webm_path)
            print(f"[STREAMING] Cleaned up {webm_path}")
        if pcm_path and os.path.exists(pcm_path):
            os.remove(pcm_path)
            print(f"[STREAMING] Cleaned up {pcm_path}")
