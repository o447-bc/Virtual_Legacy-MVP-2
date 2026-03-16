"""
CheckInResponse Lambda Function

Processes Legacy Maker responses to check-in emails. Validates tokens,
resets inactivity counters, and updates last check-in timestamps.

Requirements: 3.2, 3.5
"""
import json
import os
import sys
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from datetime import timezone

# Add shared functions to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from logging_utils import StructuredLogger
from cors import cors_headers
from responses import error_response



def lambda_handler(event, context):
    """
    Process Legacy Maker response to check-in email.
    
    This function:
    1. Extracts token from query parameter
    2. Validates token and retrieves user_id and condition_id from PersonaSignupTempDB
    3. Queries AccessConditionsDB for the specific condition
    4. Updates last_check_in to current timestamp
    5. Resets consecutive_missed_check_ins to 0
    6. Returns success page/response
    
    Query Parameters:
        token: Unique check-in verification token
    
    Returns:
        dict: API Gateway response with HTML success page or error message
    """
    print("CheckInResponse: Starting execution")
    
    try:
        # Extract token from query parameters
        query_params = event.get('queryStringParameters', {})
        if not query_params:
            print("CheckInResponse ERROR: No query parameters provided")
            return build_error_response(400, "Missing token parameter")
        
        token = query_params.get('token')
        if not token:
            print("CheckInResponse ERROR: Token parameter missing")
            return build_error_response(400, "Missing token parameter")
        
        print(f"CheckInResponse: Processing token: {token[:8]}...")
        
        # Validate token and retrieve check-in details
        dynamodb = boto3.resource('dynamodb')
        temp_table = dynamodb.Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB'))
        conditions_table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        
        # Look up token in temp table
        try:
            response = temp_table.get_item(
                Key={'userName': f'checkin#{token}'}
            )
            
            token_data = response.get('Item')
            if not token_data:
                print(f"CheckInResponse ERROR: Token not found or expired")
                return build_error_response(404, "Invalid or expired check-in link")
            
            user_id = token_data.get('user_id')
            condition_id = token_data.get('condition_id')
            relationship_key = token_data.get('relationship_key')
            
            if not all([user_id, condition_id, relationship_key]):
                print(f"CheckInResponse ERROR: Incomplete token data")
                return build_error_response(500, "Invalid token data")
            
            print(f"CheckInResponse: Token validated for user {user_id}, condition {condition_id}")
            
        except ClientError as e:
            error_msg = f"Failed to retrieve token: {e.response['Error']['Message']}"
            print(f"CheckInResponse ERROR: {error_msg}")
            return build_error_response(500, "Failed to validate token")
        
        # Get current time
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Query AccessConditionsDB for the specific condition
        try:
            response = conditions_table.get_item(
                Key={
                    'relationship_key': relationship_key,
                    'condition_id': condition_id
                }
            )
            
            condition = response.get('Item')
            if not condition:
                print(f"CheckInResponse ERROR: Condition not found")
                return build_error_response(404, "Check-in condition not found")
            
            # Verify this is an inactivity trigger condition
            if condition.get('condition_type') != 'inactivity_trigger':
                print(f"CheckInResponse ERROR: Invalid condition type: {condition.get('condition_type')}")
                return build_error_response(400, "Invalid condition type")
            
            print(f"CheckInResponse: Found condition {condition_id}")
            
        except ClientError as e:
            error_msg = f"Failed to retrieve condition: {e.response['Error']['Message']}"
            print(f"CheckInResponse ERROR: {error_msg}")
            return build_error_response(500, "Failed to retrieve condition")
        
        # Update condition: reset consecutive_missed_check_ins and update last_check_in
        try:
            conditions_table.update_item(
                Key={
                    'relationship_key': relationship_key,
                    'condition_id': condition_id
                },
                UpdateExpression='SET last_check_in = :check_in_time, consecutive_missed_check_ins = :zero',
                ExpressionAttributeValues={
                    ':check_in_time': current_time,
                    ':zero': 0
                }
            )
            
            print(f"CheckInResponse: Updated condition - reset consecutive_missed_check_ins to 0")
            
        except ClientError as e:
            error_msg = f"Failed to update condition: {e.response['Error']['Message']}"
            print(f"CheckInResponse ERROR: {error_msg}")
            return build_error_response(500, "Failed to update check-in status")
        
        # Delete the token from temp table (one-time use)
        try:
            temp_table.delete_item(
                Key={'userName': f'checkin#{token}'}
            )
            print(f"CheckInResponse: Deleted used token")
            
        except ClientError as e:
            # Log but don't fail - the check-in was successful
            print(f"CheckInResponse WARNING: Failed to delete token: {e.response['Error']['Message']}")
        
        # Get previous missed count for logging
        previous_missed_count = condition.get('consecutive_missed_check_ins', 0)
        
        # Log check-in response event
        StructuredLogger.log_check_in_response(
            user_id=user_id,
            condition_id=condition_id,
            relationship_key=relationship_key,
            token=token,
            previous_missed_count=previous_missed_count
        )
        
        print(f"CheckInResponse: Successfully processed check-in for user {user_id}")
        
        # Return success HTML page
        return build_success_response()
        
    except Exception as e:
        error_msg = f"Unexpected error in CheckInResponse: {str(e)}"
        print(f"CheckInResponse FATAL ERROR: {error_msg}")
        return build_error_response(500, "An unexpected error occurred")


def log_check_in_response_event(relationship_key, condition_id, user_id):
    """
    Log check-in response event to CloudWatch Logs.
    
    Args:
        relationship_key: Composite key (initiator_id#related_user_id)
        condition_id: Unique condition identifier
        user_id: User ID who responded to check-in
    """
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            'event_type': 'check_in_response_received',
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'user_id': user_id,
            'timestamp': current_time,
            'processor': 'CheckInResponse'
        }
        
        print(f"CHECK_IN_RESPONSE_EVENT: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Error logging check-in response event: {str(e)}")


def build_success_response():
    """
    Build HTML success response for check-in confirmation.
    
    Returns:
        dict: API Gateway response with HTML content
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Check-In Confirmed - Virtual Legacy</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f3f4f6;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                max-width: 600px;
                margin: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            .header {
                background-color: #10b981;
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
            }
            .content {
                padding: 40px 30px;
            }
            .success-icon {
                text-align: center;
                font-size: 64px;
                color: #10b981;
                margin-bottom: 20px;
            }
            .message {
                text-align: center;
                font-size: 18px;
                margin-bottom: 30px;
            }
            .info-box {
                background-color: #f0fdf4;
                border-left: 4px solid #10b981;
                padding: 15px;
                margin: 20px 0;
            }
            .button {
                display: inline-block;
                padding: 12px 24px;
                background-color: #6366f1;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                text-align: center;
                margin: 20px auto;
                display: block;
                width: fit-content;
            }
            .footer {
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 14px;
                background-color: #f9fafb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <div class="success-icon">✓</div>
                <div class="message">
                    <h2>Check-In Confirmed!</h2>
                    <p>Thank you for confirming your activity.</p>
                </div>
                <div class="info-box">
                    <p><strong>What happens now?</strong></p>
                    <p>Your inactivity counter has been reset to zero. You will receive another check-in email 
                    according to your configured schedule.</p>
                    <p>Your legacy content will remain private until you choose to release it or the 
                    inactivity conditions are met.</p>
                </div>
                <a href="{os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard" class="button">Go to Dashboard</a>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')
        },
        'body': html_content
    }


def build_error_response(status_code, message):
    """
    Build HTML error response.
    
    Args:
        status_code: HTTP status code
        message: Error message to display
        
    Returns:
        dict: API Gateway response with HTML error page
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error - Virtual Legacy</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f3f4f6;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                max-width: 600px;
                margin: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background-color: #dc2626;
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .error-icon {{
                text-align: center;
                font-size: 64px;
                color: #dc2626;
                margin-bottom: 20px;
            }}
            .message {{
                text-align: center;
                font-size: 18px;
                margin-bottom: 30px;
            }}
            .info-box {{
                background-color: #fef2f2;
                border-left: 4px solid #dc2626;
                padding: 15px;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #6366f1;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                text-align: center;
                margin: 20px auto;
                display: block;
                width: fit-content;
            }}
            .footer {{
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 14px;
                background-color: #f9fafb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <div class="error-icon">✗</div>
                <div class="message">
                    <h2>Check-In Error</h2>
                    <p>{message}</p>
                </div>
                <div class="info-box">
                    <p><strong>What should I do?</strong></p>
                    <p>If you believe this is an error, please contact support or try the link in your most recent check-in email.</p>
                    <p>Check-in links expire after 7 days.</p>
                </div>
                <a href="{os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard" class="button">Go to Dashboard</a>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')
        },
        'body': html_content
    }
