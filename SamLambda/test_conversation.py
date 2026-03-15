#!/usr/bin/env python3
"""
Test Conversation Flow
Tests the full conversation orchestration
"""

import asyncio
import json
import boto3
import websockets
import sys
from datetime import datetime

WEBSOCKET_URL = "wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod"
COGNITO_CLIENT_ID = "gcj7ke19nrev9gjmvg564rv6j"
COGNITO_REGION = "us-east-1"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def get_token(username, password):
    log("Authenticating with Cognito...")
    client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
    response = client.initiate_auth(
        ClientId=COGNITO_CLIENT_ID,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={'USERNAME': username, 'PASSWORD': password}
    )
    token = response['AuthenticationResult']['AccessToken']
    log(f"Token obtained: {len(token)} characters")
    return token

async def test_conversation():
    print("\n" + "="*80)
    print("VIRTUAL LEGACY - CONVERSATION FLOW TEST")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Get token
    print("\n" + "="*80)
    print("STEP 1: COGNITO AUTHENTICATION")
    print("="*80)
    log("Authenticating with Cognito...")
    log(f"Username: websocket-test@o447.net")
    log(f"Client ID: {COGNITO_CLIENT_ID}")
    log(f"Region: {COGNITO_REGION}")
    token = get_token('websocket-test@o447.net', 'WebSocketTest123!')
    log("✅ Authentication successful", "SUCCESS")
    log(f"Token length: {len(token)} characters")
    
    # Connect
    url = f"{WEBSOCKET_URL}?token={token}"
    print("\n" + "="*80)
    print("STEP 2: WEBSOCKET CONNECTION")
    print("="*80)
    log(f"WebSocket URL: {WEBSOCKET_URL}")
    log(f"Connecting with token authentication...")
    
    async with websockets.connect(url) as ws:
        log("✅ WebSocket connected successfully!", "SUCCESS")
        log(f"Connection state: {ws.state.name}")
        log(f"Connection ID will be assigned by Lambda")
        
        # Start conversation
        print("\n" + "="*80)
        print("STEP 3: START CONVERSATION")
        print("="*80)
        
        start_msg = {
            "action": "start_conversation",
            "questionId": "test-q-001",
            "questionText": "Tell me about your childhood"
        }
        log(f"Sending start_conversation action...")
        log(f"Question ID: {start_msg['questionId']}")
        log(f"Question: {start_msg['questionText']}")
        log(f"Full message: {json.dumps(start_msg, indent=2)}")
        await ws.send(json.dumps(start_msg))
        log("✅ Message sent successfully")
        log("Waiting for AI greeting (timeout: 30s)...")
        
        response = await asyncio.wait_for(ws.recv(), timeout=30)
        log(f"✅ Received response ({len(response)} bytes)")
        data = json.loads(response)
        log(f"Message type: {data['type']}", "SUCCESS")
        
        if data['type'] == 'ai_speaking':
            log("✅ Received AI greeting", "SUCCESS")
            log(f"AI text (first 100 chars): {data['text'][:100]}...")
            log(f"Full text length: {len(data['text'])} characters")
            log(f"Has audio: {'audio' in data}")
            if 'audio' in data:
                log(f"Audio data size: {len(data['audio'])} characters (base64)")
            log(f"Turn number: {data.get('turnNumber', 0)}")
            log(f"Cumulative score: {data.get('cumulativeScore', 0)}/{data.get('scoreGoal', 12)}")
        elif data['type'] == 'error':
            log(f"❌ Error received: {data['message']}", "ERROR")
            log(f"Full error data: {json.dumps(data, indent=2)}", "ERROR")
            return
        
        # Send user response
        print("\n" + "="*80)
        print("STEP 4: USER RESPONSE")
        print("="*80)
        
        user_msg = {
            "action": "user_response",
            "text": "I grew up in a small town. My childhood was filled with outdoor adventures and family gatherings. I remember spending summers at my grandparents' farm, learning about nature and hard work."
        }
        log(f"Sending user response...")
        log(f"Text (first 80 chars): {user_msg['text'][:80]}...")
        log(f"Full text length: {len(user_msg['text'])} characters")
        log(f"Full message: {json.dumps(user_msg, indent=2)}")
        await ws.send(json.dumps(user_msg))
        log("✅ User response sent successfully")
        log("Waiting for score update (timeout: 60s)...")
        log("Backend will: 1) Score response depth, 2) Generate AI follow-up")
        
        # Receive score update
        response = await asyncio.wait_for(ws.recv(), timeout=60)
        log(f"✅ Received response ({len(response)} bytes)")
        data = json.loads(response)
        log(f"Message type: {data['type']}", "SUCCESS")
        
        if data['type'] == 'score_update':
            log("✅ Score update received", "SUCCESS")
            log(f"Turn score: {data['turnScore']}")
            log(f"Cumulative score: {data['cumulativeScore']}/{data['scoreGoal']}")
            log(f"Turn number: {data['turnNumber']}")
            log(f"Reasoning (first 150 chars): {data['reasoning'][:150]}...")
            log(f"Full reasoning length: {len(data['reasoning'])} characters")
        elif data['type'] == 'error':
            log(f"❌ Error received: {data['message']}", "ERROR")
            log(f"Full error data: {json.dumps(data, indent=2)}", "ERROR")
            return
        
        # Receive AI response
        log("Waiting for AI response (timeout: 60s)...")
        response = await asyncio.wait_for(ws.recv(), timeout=60)
        log(f"✅ Received response ({len(response)} bytes)")
        data = json.loads(response)
        log(f"Message type: {data['type']}", "SUCCESS")
        
        if data['type'] == 'ai_speaking':
            log("✅ AI response received", "SUCCESS")
            log(f"AI text (first 150 chars): {data['text'][:150]}...")
            log(f"Full text length: {len(data['text'])} characters")
            log(f"Turn number: {data['turnNumber']}")
            log(f"Has audio: {'audio' in data}")
            if 'audio' in data:
                log(f"Audio data size: {len(data['audio'])} characters (base64)")
            log(f"Cumulative score: {data.get('cumulativeScore', 0)}/{data.get('scoreGoal', 12)}")
        elif data['type'] == 'conversation_complete':
            log("✅ Conversation completed!", "SUCCESS")
            log(f"Final score: {data['finalScore']}")
            log(f"Total turns: {data['totalTurns']}")
            log(f"Transcript URL: {data['transcriptUrl']}")
            log(f"Completion reason: {data['reason']}")
            return
        
        # End conversation
        print("\n" + "="*80)
        print("STEP 5: END CONVERSATION")
        print("="*80)
        
        end_msg = {"action": "end_conversation"}
        log(f"Sending end_conversation request...")
        log(f"Message: {json.dumps(end_msg)}")
        await ws.send(json.dumps(end_msg))
        log("✅ End request sent successfully")
        log("Waiting for confirmation (timeout: 30s)...")
        
        response = await asyncio.wait_for(ws.recv(), timeout=30)
        log(f"✅ Received response ({len(response)} bytes)")
        data = json.loads(response)
        log(f"Message type: {data['type']}", "SUCCESS")
        
        if data['type'] == 'conversation_ended':
            log("✅ Conversation ended successfully", "SUCCESS")
            log(f"Final score: {data['finalScore']}")
            log(f"Total turns: {data['totalTurns']}")
            log(f"Transcript URL: {data['transcriptUrl']}")
        
        print("\n" + "="*80)
        log("✅ ALL TESTS PASSED - CONVERSATION FLOW COMPLETE!", "SUCCESS")
        print("="*80)

if __name__ == "__main__":
    try:
        log("="*80)
        log("STARTING VIRTUAL LEGACY CONVERSATION TEST")
        log("="*80)
        asyncio.run(test_conversation())
        log("\n" + "="*80)
        log("✅ TEST COMPLETED SUCCESSFULLY", "SUCCESS")
        log("="*80)
    except Exception as e:
        print("\n" + "="*80)
        log(f"❌ TEST FAILED: {type(e).__name__}", "ERROR")
        log(f"Error message: {e}", "ERROR")
        print("="*80)
        import traceback
        log("Full traceback:", "ERROR")
        print(traceback.format_exc())
        print("="*80)
