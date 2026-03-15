"""
CheckInSender Lambda Function

Scheduled function that runs daily to send check-in emails to Legacy Makers
with inactivity trigger conditions. Monitors responsiveness and increments
missed check-in counters.

Requirements: 3.1, 3.4, 3.5, 13.6
"""
import json
import os
import sys
import boto3
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from datetime import timezone

# Add shared functions to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from email_utils import send_email_with_retry
from logging_utils import StructuredLogger


def lambda_handler(event, context):
    """
    Send check-in emails to Legacy Makers with inactivity trigger conditions.
    
    This function:
    1. Queries AccessConditionsDB ConditionTypeIndex for inactivity_trigger conditions
    2. For each condition:
       - Calculate days since last_check_in_sent (or created_at if never sent)
       - If days >= check_in_interval_days:
         - Generate unique check-in token (UUID)
         - Store token with user_id and condition_id in PersonaSignupTempDB
         - Send check-in email with verification link
         - Increment consecutive_missed_check_ins
         - Update last_check_in_sent timestamp
    3. Returns summary of emails sent
    
    Returns:
        dict: Summary of processing results
        {
            "emails_processed": int,
            "emails_sent": int,
            "emails_failed": int,
            "errors": [list of error messages]
        }
    """
    print("CheckInSender: Starting execution")
    
    emails_processed = 0
    emails_sent = 0
    emails_failed = 0
    errors = []
    
    try:
        dynamodb = boto3.resource('dynamodb')
        conditions_table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        temp_table = dynamodb.Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB'))
        
        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        current_time_iso = current_time.isoformat()
        print(f"CheckInSender: Current time: {current_time_iso}")
        
        # Query AccessConditionsDB using ConditionTypeIndex GSI
        # Query for inactivity_trigger conditions
        try:
            response = conditions_table.query(
                IndexName='ConditionTypeIndex',
                KeyConditionExpression='condition_type = :ctype',
                FilterExpression='#status = :pending_status',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':ctype': 'inactivity_trigger',
                    ':pending_status': 'pending'
                }
            )
            
            conditions = response.get('Items', [])
            print(f"CheckInSender: Found {len(conditions)} inactivity trigger conditions")
            
        except ClientError as e:
            error_msg = f"Failed to query AccessConditionsDB: {e.response['Error']['Message']}"
            print(f"CheckInSender ERROR: {error_msg}")
            errors.append(error_msg)
            return build_response(0, 0, 0, errors)
        
        # Process each condition
        for condition in conditions:
            emails_processed += 1
            
            try:
                relationship_key = condition.get('relationship_key')
                condition_id = condition.get('condition_id')
                check_in_interval_days = condition.get('check_in_interval_days', 30)
                last_check_in_sent = condition.get('last_check_in_sent')
                created_at = condition.get('created_at')
                consecutive_missed = condition.get('consecutive_missed_check_ins', 0)
                
                if not relationship_key or '#' not in relationship_key:
                    error_msg = f"Invalid relationship_key format: {relationship_key}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                # Split relationship_key to get initiator_id (Legacy Maker)
                parts = relationship_key.split('#')
                initiator_id = parts[0]
                
                print(f"CheckInSender: Processing condition {condition_id} for user {initiator_id}")
                
                # Calculate days since last check-in was sent
                reference_time_str = last_check_in_sent if last_check_in_sent else created_at
                
                if not reference_time_str:
                    error_msg = f"No reference time found for condition {condition_id}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                try:
                    reference_time = datetime.fromisoformat(reference_time_str.replace('Z', '+00:00'))
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                except Exception as e:
                    error_msg = f"Failed to parse reference time {reference_time_str}: {str(e)}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                days_since_last_sent = (current_time - reference_time).days
                print(f"  Days since last check-in sent: {days_since_last_sent}, interval: {check_in_interval_days}")
                
                # Check if it's time to send a check-in email
                if days_since_last_sent < check_in_interval_days:
                    print(f"  Skipping - not yet time to send check-in")
                    continue
                
                # Generate unique check-in token
                check_in_token = str(uuid.uuid4())
                
                # Store token in PersonaSignupTempDB with 7-day TTL
                ttl_timestamp = int((current_time + timedelta(days=7)).timestamp())
                
                try:
                    temp_table.put_item(
                        Item={
                            'userName': f'checkin#{check_in_token}',
                            'user_id': initiator_id,
                            'condition_id': condition_id,
                            'relationship_key': relationship_key,
                            'token_type': 'check_in',
                            'created_at': current_time_iso,
                            'ttl': ttl_timestamp
                        }
                    )
                    print(f"  Stored check-in token in temp table")
                    
                except ClientError as e:
                    error_msg = f"Failed to store check-in token: {e.response['Error']['Message']}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                # Get Legacy Maker email
                legacy_maker_email = get_user_email(initiator_id)
                
                if not legacy_maker_email:
                    error_msg = f"Could not retrieve email for user {initiator_id}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                # Send check-in email
                email_sent_success = send_check_in_email(
                    email=legacy_maker_email,
                    token=check_in_token,
                    check_in_interval_days=check_in_interval_days
                )
                
                if not email_sent_success:
                    error_msg = f"Failed to send check-in email to {legacy_maker_email}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    emails_failed += 1
                    continue
                
                print(f"  Check-in email sent to {legacy_maker_email}")
                
                # Update condition: increment consecutive_missed_check_ins and update last_check_in_sent
                try:
                    conditions_table.update_item(
                        Key={
                            'relationship_key': relationship_key,
                            'condition_id': condition_id
                        },
                        UpdateExpression='SET last_check_in_sent = :sent_time, consecutive_missed_check_ins = :missed_count',
                        ExpressionAttributeValues={
                            ':sent_time': current_time_iso,
                            ':missed_count': consecutive_missed + 1
                        }
                    )
                    print(f"  Updated condition: consecutive_missed_check_ins = {consecutive_missed + 1}")
                    
                except ClientError as e:
                    error_msg = f"Failed to update condition {condition_id}: {e.response['Error']['Message']}"
                    print(f"CheckInSender ERROR: {error_msg}")
                    errors.append(error_msg)
                    # Email was sent, so count as success even if update failed
                
                # Log check-in event
                StructuredLogger.log_check_in_sent(
                    relationship_key=relationship_key,
                    condition_id=condition_id,
                    user_id=initiator_id,
                    email=legacy_maker_email,
                    token=check_in_token,
                    consecutive_missed=consecutive_missed + 1
                )
                
                emails_sent += 1
                print(f"CheckInSender: Successfully sent check-in for condition {condition_id}")
                
            except Exception as e:
                error_msg = f"Unexpected error processing condition {condition.get('condition_id')}: {str(e)}"
                print(f"CheckInSender ERROR: {error_msg}")
                errors.append(error_msg)
                emails_failed += 1
                continue
        
        # Return summary
        summary = build_response(
            emails_processed,
            emails_sent,
            emails_failed,
            errors
        )
        
        # Log scheduled job execution summary
        StructuredLogger.log_scheduled_job_execution(
            job_name='CheckInSender',
            items_processed=emails_processed,
            items_successful=emails_sent,
            items_failed=emails_failed,
            errors=errors
        )
        
        print(f"CheckInSender: Execution complete. Summary: {json.dumps(summary)}")
        return summary
        
    except Exception as e:
        error_msg = f"Fatal error in CheckInSender: {str(e)}"
        print(f"CheckInSender FATAL ERROR: {error_msg}")
        errors.append(error_msg)
        return build_response(
            emails_processed,
            emails_sent,
            emails_failed,
            errors
        )


def get_user_email(user_id):
    """
    Get user email address from Cognito.
    
    Args:
        user_id: Cognito user ID
        
    Returns:
        str: Email address or None if not found
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            print("WARNING: USER_POOL_ID environment variable not set")
            return None
        
        try:
            response = cognito.admin_get_user(
                UserPoolId=user_pool_id,
                Username=user_id
            )
            
            # Extract email from user attributes
            for attr in response.get('UserAttributes', []):
                if attr['Name'] == 'email':
                    return attr['Value']
            
            return None
            
        except ClientError as e:
            print(f"Error looking up user in Cognito: {e.response['Error']['Message']}")
            return None
            
    except Exception as e:
        print(f"Error getting user email: {str(e)}")
        return None


def send_check_in_email(email, token, check_in_interval_days):
    """
    Send check-in email to Legacy Maker with verification link.
    
    Uses email_utils.send_email_with_retry for robust delivery with exponential backoff.
    
    Args:
        email: Email address of the Legacy Maker
        token: Unique check-in verification token
        check_in_interval_days: Check-in interval in days
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Build verification link
        # TODO: Update with production domain
        verification_link = f"http://localhost:8080/check-in?token={token}"
        
        # Email subject
        subject = "Virtual Legacy - Activity Check-In Required"
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #6366f1; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background-color: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #10b981; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .info-box {{ background-color: white; padding: 15px; border-left: 4px solid #6366f1; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .warning {{ color: #dc2626; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Activity Check-In Required</h2>
                    <p>Hello,</p>
                    <p>This is your periodic activity check-in for your Virtual Legacy account.</p>
                    <div class="info-box">
                        <p><strong>Why am I receiving this?</strong></p>
                        <p>You have configured inactivity-based access conditions for your legacy content. 
                        We send these check-ins every {check_in_interval_days} days to verify you are still active.</p>
                    </div>
                    <p><strong>Please click the button below to confirm you are active:</strong></p>
                    <a href="{verification_link}" class="button">Confirm I'm Active</a>
                    <div class="info-box">
                        <p class="warning">Important:</p>
                        <p>If you do not respond to check-in emails for the configured duration, 
                        your legacy content will be automatically released to your designated benefactors.</p>
                        <p>This link expires in 7 days.</p>
                    </div>
                    <p>If you did not set up inactivity monitoring or have questions, please contact support.</p>
                </div>
                <div class="footer">
                    <p>Virtual Legacy - Preserving memories for future generations</p>
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; font-size: 10px;">{verification_link}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Virtual Legacy - Activity Check-In Required
        
        Hello,
        
        This is your periodic activity check-in for your Virtual Legacy account.
        
        Why am I receiving this?
        You have configured inactivity-based access conditions for your legacy content. 
        We send these check-ins every {check_in_interval_days} days to verify you are still active.
        
        Please click the link below to confirm you are active:
        {verification_link}
        
        IMPORTANT:
        If you do not respond to check-in emails for the configured duration, 
        your legacy content will be automatically released to your designated benefactors.
        
        This link expires in 7 days.
        
        If you did not set up inactivity monitoring or have questions, please contact support.
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        # Use retry utility for robust email delivery
        result = send_email_with_retry(
            destination=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sender_email=sender_email
        )
        
        if result['success']:
            print(f"Check-in email sent successfully. MessageId: {result['message_id']}, Attempts: {result['attempts']}")
            return True
        else:
            print(f"Failed to send check-in email after {result['attempts']} attempts. Error: {result['error']}")
            return False
        
    except Exception as e:
        print(f"Error sending check-in email: {str(e)}")
        return False


def log_check_in_event(relationship_key, condition_id, email, token):
    """
    Log check-in email event to CloudWatch Logs.
    
    Args:
        relationship_key: Composite key (initiator_id#related_user_id)
        condition_id: Unique condition identifier
        email: Email address where check-in was sent
        token: Check-in verification token
    """
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            'event_type': 'check_in_email_sent',
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'email': email,
            'token': token,
            'timestamp': current_time,
            'processor': 'CheckInSender'
        }
        
        print(f"CHECK_IN_EVENT: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Error logging check-in event: {str(e)}")


def build_response(processed, sent, failed, errors):
    """
    Build standardized response object.
    
    Args:
        processed: Number of conditions processed
        sent: Number of emails sent successfully
        failed: Number of failed email sends
        errors: List of error messages
        
    Returns:
        dict: Response object
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'emails_processed': processed,
            'emails_sent': sent,
            'emails_failed': failed,
            'errors': errors,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    }
