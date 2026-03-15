#!/usr/bin/env python3
"""
WebSocket Connection Test
Tests the deployed WebSocket API with Cognito authentication
"""

import asyncio
import json
import boto3
import websockets
import sys
from datetime import datetime

# Configuration
WEBSOCKET_URL = "wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod"
COGNITO_CLIENT_ID = "gcj7ke19nrev9gjmvg564rv6j"
COGNITO_REGION = "us-east-1"

def log(message, level="INFO"):
    """Verbose logging with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()

def get_cognito_token(username, password):
    """Get Cognito access token for testing"""
    log("Initializing Cognito client...")
    log(f"Region: {COGNITO_REGION}")
    log(f"Client ID: {COGNITO_CLIENT_ID}")
    
    try:
        client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        log("Cognito client initialized successfully")
        
        log(f"Attempting authentication for user: {username}")
        log("Auth flow: USER_PASSWORD_AUTH")
        
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        log("Authentication response received")
        log(f"Response keys: {list(response.keys())}")
        
        if 'AuthenticationResult' in response:
            log("AuthenticationResult found in response")
            token = response['AuthenticationResult']['AccessToken']
            log(f"Access token length: {len(token)} characters")
            return token
        else:
            log("No AuthenticationResult in response", "ERROR")
            log(f"Full response: {json.dumps(response, indent=2)}", "ERROR")
            return None
            
    except client.exceptions.NotAuthorizedException as e:
        log(f"Authentication failed: Invalid username or password", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        return None
    except client.exceptions.UserNotFoundException as e:
        log(f"User not found: {username}", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        return None
    except Exception as e:
        log(f"Unexpected error during authentication", "ERROR")
        log(f"Exception type: {type(e).__name__}", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        return None

async def test_websocket_connection(token):
    """Test WebSocket connection with authentication"""
    url = f"{WEBSOCKET_URL}?token={token}"
    
    log("="*60)
    log("Starting WebSocket connection test")
    log(f"WebSocket URL: {WEBSOCKET_URL}")
    log(f"Token length: {len(token)} characters")
    log(f"Token preview: {token[:30]}...{token[-30:]}")
    log(f"Full URL (with token): {url[:80]}...")
    log("="*60)
    
    try:
        log("Initiating WebSocket connection...")
        log("Creating websockets.connect() context...")
        
        async with websockets.connect(url) as websocket:
            log("✅ WebSocket connection established!", "SUCCESS")
            log(f"Connection state: {websocket.state.name}")
            log(f"Local address: {websocket.local_address}")
            log(f"Remote address: {websocket.remote_address}")
            
            # Test sending a message
            test_message = {
                "action": "test",
                "message": "Hello from Python test"
            }
            
            log("\nPreparing test message...")
            log(f"Message content: {json.dumps(test_message, indent=2)}")
            message_str = json.dumps(test_message)
            log(f"Serialized message length: {len(message_str)} bytes")
            
            log("\nSending message to server...")
            await websocket.send(message_str)
            log("✅ Message sent successfully", "SUCCESS")
            
            # Wait for response
            log("\nWaiting for server response (timeout: 5 seconds)...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                log("✅ Response received!", "SUCCESS")
                log(f"Response length: {len(response)} bytes")
                log(f"Raw response: {response}")
                
                try:
                    parsed = json.loads(response)
                    log(f"Parsed JSON response: {json.dumps(parsed, indent=2)}")
                except json.JSONDecodeError:
                    log("Response is not valid JSON", "WARN")
                    
            except asyncio.TimeoutError:
                log("⏱️  Timeout waiting for response", "WARN")
                log("Connection is established but server didn't respond within 5 seconds")
            
            # Close connection
            log("\nInitiating connection close...")
            await websocket.close()
            log("✅ Connection closed gracefully", "SUCCESS")
            
    except websockets.exceptions.InvalidStatusCode as e:
        log(f"❌ Connection rejected by server", "ERROR")
        log(f"HTTP Status Code: {e.status_code}", "ERROR")
        log(f"Response headers: {e.headers}", "ERROR")
        
        if e.status_code == 401:
            log("→ 401 Unauthorized: Token is invalid or expired", "ERROR")
            log("  Check: Token format, expiration, and Cognito configuration", "ERROR")
        elif e.status_code == 403:
            log("→ 403 Forbidden: Token is valid but access denied", "ERROR")
            log("  Check: Authorizer Lambda function logic and IAM permissions", "ERROR")
        elif e.status_code == 500:
            log("→ 500 Internal Server Error: Server-side error", "ERROR")
            log("  Check: Lambda function logs in CloudWatch", "ERROR")
        else:
            log(f"→ Unexpected status code: {e.status_code}", "ERROR")
            
    except asyncio.TimeoutError:
        log("⏱️  Connection timeout", "ERROR")
        log("Failed to establish connection within timeout period")
        log("Check: Network connectivity, WebSocket URL, and API Gateway status")
        
    except websockets.exceptions.WebSocketException as e:
        log(f"❌ WebSocket protocol error", "ERROR")
        log(f"Exception type: {type(e).__name__}", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        
    except Exception as e:
        log(f"❌ Unexpected error", "ERROR")
        log(f"Exception type: {type(e).__name__}", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}", "ERROR")

async def main():
    print("\n" + "=" * 60)
    print("WebSocket Connection Test - VERBOSE MODE")
    print("=" * 60)
    log("Test script started")
    log(f"Python version: {sys.version}")
    log(f"Websockets library version: {websockets.__version__}")
    log(f"Boto3 version: {boto3.__version__}")
    
    # Get credentials
    print("\n" + "=" * 60)
    print("Step 1: Cognito Authentication")
    print("=" * 60)
    log("Prompting for credentials...")
    
    username = input("\nUsername (email): ").strip()
    password = input("Password: ").strip()
    
    log(f"Username entered: {username}")
    log(f"Password length: {len(password)} characters")
    
    if not username or not password:
        log("Username or password is empty", "ERROR")
        print("❌ Username and password required")
        return
    
    log("Credentials validated (non-empty)")
    
    # Get token
    print("\n" + "=" * 60)
    print("Step 2: Obtaining Access Token")
    print("=" * 60)
    
    token = get_cognito_token(username, password)
    
    if not token:
        log("Failed to obtain access token", "ERROR")
        log("Cannot proceed with WebSocket test", "ERROR")
        return
    
    log("✅ Access token obtained successfully", "SUCCESS")
    log(f"Token length: {len(token)} characters")
    log(f"Token preview: {token[:30]}...{token[-30:]}")
    
    # Test connection
    print("\n" + "=" * 60)
    print("Step 3: WebSocket Connection Test")
    print("=" * 60)
    
    await test_websocket_connection(token)
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    log("Test script finished")

if __name__ == "__main__":
    log("Script execution started")
    try:
        asyncio.run(main())
        log("Script execution completed successfully")
    except KeyboardInterrupt:
        log("\n\nTest interrupted by user (Ctrl+C)", "WARN")
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        log(f"Fatal error in main execution", "ERROR")
        log(f"Exception type: {type(e).__name__}", "ERROR")
        log(f"Exception details: {e}", "ERROR")
        import traceback
        log(f"Traceback:\n{traceback.format_exc()}", "ERROR")
