#!/usr/bin/env python3
"""
Automated WebSocket Test (uses environment variables)
Set COGNITO_USERNAME and COGNITO_PASSWORD before running
"""

import asyncio
import json
import boto3
import websockets
import sys
import os
from datetime import datetime

WEBSOCKET_URL = "wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod"
COGNITO_CLIENT_ID = "gcj7ke19nrev9gjmvg564rv6j"
COGNITO_REGION = "us-east-1"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def get_cognito_token(username, password):
    log("Initializing Cognito client...")
    try:
        client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        log("Attempting authentication...")
        
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': username, 'PASSWORD': password}
        )
        
        token = response['AuthenticationResult']['AccessToken']
        log(f"✅ Token obtained (length: {len(token)})", "SUCCESS")
        return token
    except Exception as e:
        log(f"❌ Authentication failed: {e}", "ERROR")
        return None

async def test_websocket(token):
    url = f"{WEBSOCKET_URL}?token={token}"
    log(f"Connecting to {WEBSOCKET_URL}...")
    
    try:
        async with websockets.connect(url) as ws:
            log("✅ Connected!", "SUCCESS")
            
            msg = {"action": "test", "message": "Hello"}
            log(f"Sending: {json.dumps(msg)}")
            await ws.send(json.dumps(msg))
            
            log("Waiting for response...")
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            log(f"✅ Received: {response}", "SUCCESS")
            
            await ws.close()
            log("✅ Test complete!", "SUCCESS")
            
    except websockets.exceptions.InvalidStatusCode as e:
        log(f"❌ Connection failed: HTTP {e.status_code}", "ERROR")
    except asyncio.TimeoutError:
        log("⏱️ Timeout (connection OK, no response)", "WARN")
    except Exception as e:
        log(f"❌ Error: {type(e).__name__}: {e}", "ERROR")

async def main():
    print("\n" + "="*60)
    print("WebSocket Automated Test")
    print("="*60 + "\n")
    
    username = os.environ.get('COGNITO_USERNAME')
    password = os.environ.get('COGNITO_PASSWORD')
    
    if not username or not password:
        print("❌ Set COGNITO_USERNAME and COGNITO_PASSWORD environment variables")
        print("\nExample:")
        print("  export COGNITO_USERNAME='your-email@example.com'")
        print("  export COGNITO_PASSWORD='your-password'")
        print("  python3 test_websocket_auto.py")
        return
    
    log(f"Using username: {username}")
    token = get_cognito_token(username, password)
    
    if token:
        await test_websocket(token)
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\nTest interrupted", "WARN")
