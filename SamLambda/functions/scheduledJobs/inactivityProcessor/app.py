"""
InactivityProcessor Lambda Function

Scheduled function that runs daily to activate inactivity trigger conditions
when Legacy Makers fail to respond to check-in emails for the configured duration.

Requirements: 3.3, 3.6, 11.3, 11.4
"""
import json
import os
import sys
import boto3
from datetime import datetime
from dateutil.relativedelta import relativedelta
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
    Process inactivity trigger conditions and activate when threshold is met.
    
    This function:
    1. Queries AccessConditionsDB ConditionTypeIndex for inactivity_trigger conditions
    2. For each condition:
       - Calculate months since last_check_in
       - If months >= inactivity_months AND consecutive_missed_check_ins >= threshold:
         - Parse relationship_key to get initiator_id and related_user_id
         - Update relationship status to "active" in PersonaRelationshipsDB
         - Update condition status to "activated" in AccessConditionsDB
         - Send notification email to Benefactor
         - Log activation event
    3. Returns summary of activations
    
    Returns:
        dict: Summary of processing results
        {
            "activations_processed": int,
            "activations_successful": int,
            "activations_failed": int,
            "errors": [list of error messages]
        }
    """
    print("InactivityProcessor: Starting execution")
    
    activations_processed = 0
    activations_successful = 0
    activations_failed = 0
    errors = []
    
    try:
        dynamodb = boto3.resource('dynamodb')
        conditions_table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        
        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        current_time_iso = current_time.isoformat()
        print(f"InactivityProcessor: Current time: {current_time_iso}")
        
        # Query AccessConditionsDB using ConditionTypeIndex GSI
        # Query for inactivity_trigger conditions with status = pending
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
            print(f"InactivityProcessor: Found {len(conditions)} inactivity trigger conditions")
            
        except ClientError as e:
            error_msg = f"Failed to query AccessConditionsDB: {e.response['Error']['Message']}"
            print(f"InactivityProcessor ERROR: {error_msg}")
            errors.append(error_msg)
            return build_response(0, 0, 0, errors)
        
        # Process each condition
        for condition in conditions:
            activations_processed += 1
            
            try:
                relationship_key = condition.get('relationship_key')
                condition_id = condition.get('condition_id')
                inactivity_months = condition.get('inactivity_months', 6)
                last_check_in = condition.get('last_check_in')
                created_at = condition.get('created_at')
                consecutive_missed = condition.get('consecutive_missed_check_ins', 0)
                check_in_interval_days = condition.get('check_in_interval_days', 30)
                
                if not relationship_key or '#' not in relationship_key:
                    error_msg = f"Invalid relationship_key format: {relationship_key}"
                    print(f"InactivityProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                # Split relationship_key to get initiator_id and related_user_id
                parts = relationship_key.split('#')
                initiator_id = parts[0]
                related_user_id = parts[1]
                
                print(f"InactivityProcessor: Processing condition {condition_id} for {relationship_key}")
                print(f"  Inactivity threshold: {inactivity_months} months")
                print(f"  Consecutive missed check-ins: {consecutive_missed}")
                
                # Calculate months since last check-in
                # Use last_check_in if available, otherwise use created_at
                reference_time_str = last_check_in if last_check_in else created_at
                
                if not reference_time_str:
                    error_msg = f"No reference time found for condition {condition_id}"
                    print(f"InactivityProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                try:
                    reference_time = datetime.fromisoformat(reference_time_str.replace('Z', '+00:00'))
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                except Exception as e:
                    error_msg = f"Failed to parse reference time {reference_time_str}: {str(e)}"
                    print(f"InactivityProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                # Calculate months difference using relativedelta for accurate month calculation
                months_diff = relativedelta(current_time, reference_time)
                months_since_last_check_in = months_diff.years * 12 + months_diff.months
                
                print(f"  Months since last check-in: {months_since_last_check_in}")
                
                # Calculate minimum expected missed check-ins based on duration and interval
                # If inactivity_months = 6 and check_in_interval_days = 30, expect ~6 missed check-ins
                expected_check_ins = max(1, int((inactivity_months * 30) / check_in_interval_days))
                
                print(f"  Expected minimum missed check-ins: {expected_check_ins}")
                
                # Check if threshold is met:
                # 1. Enough months have passed since last check-in
                # 2. Sufficient check-ins have been missed (at least half of expected)
                threshold_met = (
                    months_since_last_check_in >= inactivity_months and
                    consecutive_missed >= max(1, expected_check_ins // 2)
                )
                
                if not threshold_met:
                    print(f"  Threshold not met - skipping activation")
                    continue
                
                print(f"  Threshold met - activating access")
                
                # Update relationship status to "active" in PersonaRelationshipsDB
                success, result = update_relationship_status(
                    initiator_id=initiator_id,
                    related_user_id=related_user_id,
                    new_status='active'
                )
                
                if not success:
                    error_msg = f"Failed to update relationship status for {relationship_key}: {result.get('error')}"
                    print(f"InactivityProcessor ERROR: {error_msg}")
                    errors.append(error_msg)
                    activations_failed += 1
                    continue
                
                print(f"InactivityProcessor: Updated relationship status to 'active' for {relationship_key}")
                
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
                            ':activated_at': current_time_iso
                        }
                    )
                    print(f"InactivityProcessor: Updated condition status to 'activated' for {condition_id}")
                    
                except ClientError as e:
                    error_msg = f"Failed to update condition status for {condition_id}: {e.response['Error']['Message']}"
                    print(f"InactivityProcessor ERROR: {error_msg}")
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
                        activation_type='inactivity_trigger',
                        inactivity_months=inactivity_months,
                        months_inactive=months_since_last_check_in
                    )
                    
                    if email_sent:
                        print(f"InactivityProcessor: Notification email sent to {benefactor_email}")
                    else:
                        print(f"InactivityProcessor WARNING: Failed to send notification email to {benefactor_email}")
                        # Don't fail the activation if email fails
                else:
                    print(f"InactivityProcessor WARNING: Could not retrieve benefactor email for {related_user_id}")
                
                # Log activation event
                StructuredLogger.log_condition_activated(
                    relationship_key=relationship_key,
                    condition_id=condition_id,
                    condition_type='inactivity_trigger',
                    activation_trigger=f'inactivity_detected_{months_since_last_check_in}_months'
                )
                
                activations_successful += 1
                print(f"InactivityProcessor: Successfully activated condition {condition_id}")
                
            except Exception as e:
                error_msg = f"Unexpected error processing condition {condition.get('condition_id')}: {str(e)}"
                print(f"InactivityProcessor ERROR: {error_msg}")
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
            job_name='InactivityProcessor',
            items_processed=activations_processed,
            items_successful=activations_successful,
            items_failed=activations_failed,
            errors=errors
        )
        
        print(f"InactivityProcessor: Execution complete. Summary: {json.dumps(summary)}")
        return summary
        
    except Exception as e:
        error_msg = f"Fatal error in InactivityProcessor: {str(e)}"
        print(f"InactivityProcessor FATAL ERROR: {error_msg}")
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


def send_access_granted_email(benefactor_email, initiator_id, activation_type, inactivity_months, months_inactive):
    """
    Send notification email to Benefactor when access is granted due to inactivity.
    
    Uses email_utils.send_email_with_retry for robust delivery with exponential backoff.
    
    Args:
        benefactor_email: Email address of the benefactor
        initiator_id: Cognito user ID of the Legacy Maker
        activation_type: Type of activation ('inactivity_trigger')
        inactivity_months: Configured inactivity threshold in months
        months_inactive: Actual months of inactivity detected
        
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
                .info-box {{ background-color: white; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0; }}
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
                    <p>You now have access to legacy content from a Legacy Maker.</p>
                    <div class="info-box">
                        <p><strong>Activation Type:</strong> Inactivity Trigger</p>
                        <p><strong>Inactivity Threshold:</strong> {inactivity_months} months</p>
                        <p><strong>Detected Inactivity:</strong> {months_inactive} months</p>
                        <p><strong>Status:</strong> Access is now active</p>
                    </div>
                    <p>The Legacy Maker has not responded to activity check-ins for {months_inactive} months, 
                    meeting the configured inactivity threshold of {inactivity_months} months.</p>
                    <p>You can now view their videos, audio recordings, and text responses.</p>
                    <p>Click the button below to access the content:</p>
                    <a href="{os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard" class="button">View Legacy Content</a>
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
        
        You now have access to legacy content from a Legacy Maker.
        
        Activation Type: Inactivity Trigger
        Inactivity Threshold: {inactivity_months} months
        Detected Inactivity: {months_inactive} months
        Status: Access is now active
        
        The Legacy Maker has not responded to activity check-ins for {months_inactive} months, 
        meeting the configured inactivity threshold of {inactivity_months} months.
        
        You can now view their videos, audio recordings, and text responses.
        
        Visit your dashboard to access the content: {os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard
        
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


def log_activation_event(relationship_key, condition_id, activation_type, inactivity_months, months_inactive, consecutive_missed):
    """
    Log activation event to CloudWatch Logs.
    
    Args:
        relationship_key: Composite key (initiator_id#related_user_id)
        condition_id: Unique condition identifier
        activation_type: Type of activation ('inactivity_trigger')
        inactivity_months: Configured inactivity threshold
        months_inactive: Actual months of inactivity
        consecutive_missed: Number of consecutive missed check-ins
    """
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            'event_type': 'access_condition_activated',
            'relationship_key': relationship_key,
            'condition_id': condition_id,
            'activation_type': activation_type,
            'inactivity_threshold_months': inactivity_months,
            'actual_months_inactive': months_inactive,
            'consecutive_missed_check_ins': consecutive_missed,
            'activation_time': current_time,
            'processor': 'InactivityProcessor'
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
