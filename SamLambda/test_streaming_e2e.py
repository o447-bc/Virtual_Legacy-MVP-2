#!/usr/bin/env python3
# If you get "ModuleNotFoundError: No module named 'boto3'", run:
# python3 test_streaming_e2e.py
# instead of:
# ./test_streaming_e2e.py
"""
End-to-End Streaming Transcription Test
Tests complete conversation flow with streaming transcription enabled
"""

import asyncio
import json
import boto3
import websockets
import time
from datetime import datetime

WEBSOCKET_URL = "wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod"
COGNITO_CLIENT_ID = "gcj7ke19nrev9gjmvg564rv6j"
COGNITO_REGION = "us-east-1"

def get_cognito_token(username, password):
    """Get Cognito access token"""
    client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
    response = client.initiate_auth(
        ClientId=COGNITO_CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={'USERNAME': username, 'PASSWORD': password}
    )
    return response['AuthenticationResult']['AccessToken']

async def test_streaming_conversation(token):
    """Test conversation with streaming transcription"""
    url = f"{WEBSOCKET_URL}?token={token}"
    
    print("\n" + "="*60)
    print("STREAMING TRANSCRIPTION E2E TEST")
    print("="*60)
    
    async with websockets.connect(url) as ws:
        print("✅ WebSocket connected")
        
        # Start conversation
        print("\n[1] Starting conversation...")
        await ws.send(json.dumps({
            "action": "start_conversation",
            "questionId": "test-streaming-q1",
            "questionText": "Test question for streaming transcription"
        }))
        
        response = await ws.recv()
        data = json.loads(response)
        print(f"✅ Conversation started: {data['type']}")
        
        # Send audio response using existing test audio
        print("\n[2] Sending audio response...")
        print("    Using test audio: test-audio/short_audio.webm")
        
        start_time = time.time()
        
        await ws.send(json.dumps({
            "action": "audio_response",
            "s3Key": "test-audio/short_audio.webm"
        }))
        
        print("    Waiting for transcription...")
        
        # Wait for score update (indicates transcription complete)
        response = await ws.recv()
        data = json.loads(response)
        elapsed = time.time() - start_time
        
        print(f"\n✅ Response received in {elapsed:.2f}s")
        print(f"   Type: {data['type']}")
        
        if data['type'] == 'score_update':
            print(f"   Turn Score: {data.get('turnScore', 'N/A')}")
            print(f"   Cumulative Score: {data.get('cumulativeScore', 'N/A')}")
            print(f"   Turn Number: {data.get('turnNumber', 'N/A')}")
        
        # Wait for AI response
        response = await ws.recv()
        data = json.loads(response)
        
        if data['type'] == 'ai_speaking':
            print(f"\n✅ AI response received")
            print(f"   Text: {data.get('text', '')[:100]}...")
        
        # Performance check
        print(f"\n" + "="*60)
        print("PERFORMANCE ANALYSIS")
        print("="*60)
        
        if elapsed < 6.0:
            print(f"✅ EXCELLENT: Latency {elapsed:.2f}s < 6.0s target")
            print(f"   Streaming transcription likely succeeded")
        elif elapsed < 10.0:
            print(f"⚠️  ACCEPTABLE: Latency {elapsed:.2f}s (6-10s)")
            print(f"   May have used batch transcription fallback")
        else:
            print(f"❌ SLOW: Latency {elapsed:.2f}s > 10s")
            print(f"   Likely used batch transcription")
        
        # End conversation
        print(f"\n[3] Ending conversation...")
        await ws.send(json.dumps({"action": "end_conversation"}))
        
        response = await ws.recv()
        data = json.loads(response)
        print(f"✅ Conversation ended: {data['type']}")
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)
        
        return elapsed

async def main():
    print("\n" + "="*60)
    print("Streaming Transcription E2E Test")
    print("="*60)
    
    username = input("\nUsername (email): ").strip()
    password = input("Password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required")
        return
    
    print("\nAuthenticating...")
    try:
        token = get_cognito_token(username, password)
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Run test
    try:
        elapsed = await test_streaming_conversation(token)
        
        print(f"\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total latency: {elapsed:.2f}s")
        
        if elapsed < 6.0:
            print("✅ Test PASSED - Streaming transcription working!")
        else:
            print("⚠️  Test completed but latency higher than expected")
            print("   Check CloudWatch logs for streaming errors")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
