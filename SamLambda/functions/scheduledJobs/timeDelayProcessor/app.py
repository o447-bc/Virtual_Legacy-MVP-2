"""
TimeDelayProcessor Lambda Function

Scheduled function that runs hourly to activate time-delayed access conditions.
Queries AccessConditionsDB for conditions with activation_date <= current_time,
updates relationship status to "active", and sends notification emails to Benefactors.

Requirements: 11.1, 11.4
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

from assignment_dal import update_relationship_status
from email_utils import send_email_with_retry
from logging_utils import StructuredLogger


def lambda_handler(event, context):
    """
    Process time-delayed access conditions that are ready to activate.
    
    This function:
    1. Queries AccessConditionsDB ActivationDateIndex for time_delayed conditions
       where activation_date <= current_time and status = "pending"
    2. For each condition found:
       - Parse relationship_key to get initiator_id and related_user_id
       - Update relationship status to "active" in PersonaRelationshipsDB
       - Update condition status to "activated" in AccessConditionsDB
       - Send notification email to Benefactor
       - Log activation event
    3. Returns summary of activations (count, any errors)
    
    Returns:
        dict: Summary of processing results
        {
            "activations_processed": int,
            "activations_successful": int,
            "activations_failed": int,
            "errors": [list of error messages]
        }
    """
    print("TimeDelayProcessor: Starting execution")
    
    activations_processed = 0
    activations_successful = 0
    activations_failed = 0
    errors = []
    
    try:
        dynamodb = boto3.resource('dynamodb')
        conditions_table = dynamodb.Table('AccessConditionsDB')
        
        # Get current time in UTC
        current_time = datetime.now(timezone.utc).isoformat()
        print(f"TimeDelayProcessor: Current time: {current_time}")
        
        # Query AccessConditionsDB using ActivationDateIndex GSI
        # Query for time_delayed conditions where activation_date <= current_time
        try:
            response = conditions_table.query(
                IndexName='ActivationDateIndex',
                KeyConditionExpression='condition_type = :ctype AND activation_date <= :current_time',
                FilterExpression='#status = :pending_status',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':ctype': 'time_delayed',
                    ':current_time': current_time,
                    ':pending_status': 'pending'
                }
            )
            
            conditions = response.get('Items', [])
            print(f"TimeDelayProcessor: Found {len(conditions)} conditions ready to activate")
            
        except ClientError as e:
            error_msg = f"Failed to query AccessConditionsDB: {e.response['Error']['Message']}"
            print(f"TimeDelayProcessor ERROR: {error_msg}")
            errors.append(error_msg)
            return build_response(0, 0, 0, errors)
        
        # Process each condition
        for condition in conditions:
            activations_processed += 1
            
            try:
                # Parse relationship_key to get initiator_id and related_user_id
                relationship_key = condition.get('relationship_key')
                condition_id = condition.get('condition_id')
                activation_date = condition.get('activation_date')
                
                if not relationship_key or '#' not in relationship_key:
                    error_msg = f"Invalid relationship_key format: {relationship_key}"
                    print(f"TimeDelayProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                # Split relationship_key into initiator_id and related_user_id
                parts = relationship_key.split('#')
                initiator_id = parts[0]
                related_user_id = parts[1]
                
                print(f"TimeDelayProcessor: Processing condition {condition_id} for {relationship_key}")
                print(f"  Activation date: {activation_date}")
                
                # Update relationship status to "active" in PersonaRelationshipsDB
                success, result = update_relationship_status(
                    initiator_id=initiator_id,
                    related_user_id=related_user_id,
                    new_status='active'
                )
                
                if not success:
                    error_msg = f"Failed to update relationship status for {relationship_key}: {result.get('error')}"
                    print(f"TimeDelayProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                print(f"TimeDelayProcessor: Updated relationship status to 'active' for {relationship_key}")
                
                # Update condition status to "activated" in AccessConditionsDB
                try:
                    conditions_table.update_item(
                        Key={
                            'relationship_key': relationship_key,
                            'condition_id': condition_id
                        },
                        UpdateExpression='SET #status = :activated_status, activated_at = :activated_at',
                        ExpressionAttributeNames={
                            '#status': 'status'
                        },
                        ExpressionAttributeValues={
                            ':activated_status': 'activated',
                            ':activated_at': current_time
                        }
                    )
                    print(f"TimeDelayProcessor: Updated condition status to 'activated' for {condition_id}")
                    
                except ClientError as e:
                    error_msg = f"Failed to update condition status for {condition_id}: {e.response['Error']['Message']}"
                    print(f"TimeDelayProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                # Get benefactor email for notification
                benefactor_email = get_benefactor_email(related_user_id)
                
                if benefactor_email:
                    # Send notification email to Benefactor
                    email_sent = send_access_granted_email(
                        benefactor_email=benefactor_email,
                        initiator_id=initiator_id,
                        activation_type='time_delayed',
                        activation_date=activation_date
                    )
                    
                    if email_sent:
                        print(f"TimeDelayProcessor: Notification email sent to {benefactor_email}")
                    else:
                        print(f"TimeDelayProcessor WARNING: Failed to send notification email to {benefactor_email}")
                        # Don't fail the activation if email fails
                else:
                    print(f"TimeDelayProcessor WARNING: Could not retrieve benefactor email for {related_user_id}")
                
                # Log activation event
                StructuredLogger.log_condition_activated(
                    relationship_key=relationship_key,
                    condition_id=condition_id,
                    condition_type='time_delayed',
                    activation_trigger='scheduled_time_reached',
                    scheduled_date=activation_date
                )
                
                activations_successful += 1
                print(f"TimeDelayProcessor: Successfully activated condition {condition_id}")
                
            except Exception as e:
                error_msg = f"Unexpected error processing condition {condition.get('condition_id')}: {str(e)}"
                print(f"TimeDelayProcessor ERROR: {error_msg}")
                errors.append(error_msg)
                activations_failed += 1
                continue
        
        # Return summary
        summary = build_response(
            activations_processed,
            activations_successful,
            activations_failed,
            errors
        )
        
        # Log scheduled job execution summary
        StructuredLogger.log_scheduled_job_execution(
            job_name='TimeDelayProcessor',
            items_processed=activations_processed,
            items_successful=activations_successful,
            items_failed=activations_failed,
            errors=errors
        )
        
        print(f"TimeDelayProcessor: Execution complete. Summary: {json.dumps(summary)}")
        return summary
        
    except Exception as e:
        error_msg = f"Fatal error in TimeDelayProcessor: {str(e)}"
        print(f"TimeDelayProcessor FATAL ERROR: {error_msg}")
        errors.append(error_msg)
        return build_response(
            activations_processed,
            activations_successful,
            activations_failed,
            errors
        )


def get_benefactor_email(related_user_id):
    """
    Get benefactor email address from Cognito or from pending user ID.
    
    Args:
        related_user_id: Benefactor's Cognito user ID or pending#{email}
        
    Returns:
        str: Email address or None if not found
    """
    try:
        # Check if this is a pending user (format: pending#email)
        if related_user_id.startswith('pending#'):
            email = related_user_id.replace('pending#', '')
            return email
        
        # Otherwise, look up in Cognito
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            print("WARNING: USER_POOL_ID environment variable not set")
            return None
        
        try:
            response = cognito.admin_get_user(
                UserPoolId=user_pool_id,
                Username=related_user_id
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
        print(f"Error getting benefactor email: {str(e)}")
        return None


def send_access_granted_email(benefactor_email, initiator_id, activation_type, activation_date):
    """
    Send notification email to Benefactor when access is granted.
    
    Uses email_utils.send_email_with_retry for robust delivery with exponential backoff.
    
    Args:
        benefactor_email: Email address of the benefactor
        initiator_id: Cognito user ID of the Legacy Maker
        activation_type: Type of activation (e.g., 'time_delayed')
        activation_date: Date when access was scheduled to activate
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Email subject
        subject = "Access Granted to Legacy Content"
        
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
                .button {{ display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .info-box {{ background-color: white; padding: 15px; border-left: 4px solid #10b981; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Access Granted to Legacy Content</h2>
                    <p>Good news! You now have access to legacy content from a Legacy Maker.</p>
                    <div class="info-box">
                        <p><strong>Activation Type:</strong> Time-Delayed Access</p>
                        <p><strong>Scheduled Date:</strong> {activation_date}</p>
                        <p><strong>Status:</strong> Access is now active</p>
                    </div>
                    <p>You can now view their videos, audio recordings, and text responses.</p>
                    <p>Click the button below to access the content:</p>
                    <a href="http://localhost:8080/dashboard" class="button">View Legacy Content</a>
                </div>
                <div class="footer">
                    <p>Virtual Legacy - Preserving memories for future generations</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Access Granted to Legacy Content
        
        Good news! You now have access to legacy content from a Legacy Maker.
        
        Activation Type: Time-Delayed Access
        Scheduled Date: {activation_date}
        Status: Access is now active
        
        You can now view their videos, audio recordings, and text responses.
        
        Visit your dashboard to access the content: http://localhost:8080/dashboard
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        # Use retry utility for robust email delivery
        result = send_email_with_retry(
            destination=benefactor_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sender_email=sender_email
        )
        
        if result['success']:
            print(f"Access granted email sent successfully. MessageId: {result['message_id']}, Attempts: {result['attempts']}")
            return True
        else:
            print(f"Failed to send access granted email after {result['attempts']} attempts. Error: {result['error']}")
            return False
        
    except Exception as e:
        print(f"Error sending access granted email: {str(e)}")
        return False


def log_activation_event(relationship_key, condition_id, activation_type, activation_date):
    """
    Log activation event to CloudWatch Logs.
    
    Args:
        relationship_key: Composite key (initiator_id#related_user_id)
        condition_id: Unique condition identifier
        activation_type: Type of activation (e.g., 'time_delayed')
        activation_date: Date when access was scheduled to activate
    """
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            'event_type': 'access_condition_activated',
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'activation_type': activation_type,
            'scheduled_activation_date': activation_date,
            'actual_activation_time': current_time,
            'processor': 'TimeDelayProcessor'
        }
        
        print(f"ACTIVATION_EVENT: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Error logging activation event: {str(e)}")


def build_response(processed, successful, failed, errors):
    """
    Build standardized response object.
    
    Args:
        processed: Number of conditions processed
        successful: Number of successful activations
        failed: Number of failed activations
        errors: List of error messages
        
    Returns:
        dict: Response object
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'activations_processed': processed,
            'activations_successful': successful,
            'activations_failed': failed,
            'errors': errors,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    }
