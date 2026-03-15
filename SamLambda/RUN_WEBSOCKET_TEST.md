# How to Run WebSocket Tests

## Option 1: Interactive Test (Prompts for credentials)

```bash
cd SamLambda
python3 test_websocket.py
```

You'll be prompted to enter:
- Username (email)
- Password

## Option 2: Automated Test (Uses environment variables)

```bash
cd SamLambda

# Set credentials
export COGNITO_USERNAME='your-email@example.com'
export COGNITO_PASSWORD='your-password'

# Run test
python3 test_websocket_auto.py
```

## Option 3: One-liner (Credentials inline)

```bash
cd SamLambda
COGNITO_USERNAME='your-email@example.com' COGNITO_PASSWORD='your-password' python3 test_websocket_auto.py
```

## Expected Output

```
============================================================
WebSocket Automated Test
============================================================

[13:45:23.456] [INFO] Using username: your-email@example.com
[13:45:23.457] [INFO] Initializing Cognito client...
[13:45:23.458] [INFO] Attempting authentication...
[13:45:24.123] [SUCCESS] ✅ Token obtained (length: 1234)
[13:45:24.124] [INFO] Connecting to wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod...
[13:45:24.567] [SUCCESS] ✅ Connected!
[13:45:24.568] [INFO] Sending: {"action": "test", "message": "Hello"}
[13:45:24.569] [INFO] Waiting for response...
[13:45:24.789] [SUCCESS] ✅ Received: {"type": "error", "message": "Action test not implemented yet"}
[13:45:24.790] [SUCCESS] ✅ Test complete!

============================================================
```

## Viewing Lambda Logs (if issues occur)

```bash
# Authorizer logs
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-WebSocketAuthorizerFunction --follow

# Connect handler logs
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-WebSocketConnectFunction --follow

# Default handler logs
aws logs tail /aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction --follow
```

## Troubleshooting

### 401 Unauthorized
- Token is invalid or expired
- Check username/password
- Verify Cognito User Pool configuration

### 403 Forbidden
- Token is valid but access denied
- Check authorizer Lambda function
- Verify IAM permissions

### Connection timeout
- Check network connectivity
- Verify WebSocket URL
- Check API Gateway status

### No response (timeout after connect)
- Connection works but Lambda not responding
- Check Lambda function logs in CloudWatch
- Verify Lambda has correct permissions
