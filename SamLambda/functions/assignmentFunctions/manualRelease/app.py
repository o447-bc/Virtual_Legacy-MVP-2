"""
ManualRelease Lambda Function

Allows Legacy Makers to manually release content to all Benefactors with
manual_release access conditions. Implements idempotence to prevent duplicate
releases and notifications.

Requirements: 4.1, 4.2, 4.3, 4.5
"""
import json
import os
import sys
import boto3

from datetime import datetime
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Set
from datetime import timezone

# Add shared functions to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from assignment_dal import update_relationship_status
from logging_utils import StructuredLogger
from cors import cors_headers
from responses import error_response



def lambda_handler(event, context):
    """
    Manually release content to all Benefactors with manual_release conditions.
    
    This function is idempotent - calling it multiple times will not result in
    duplicate notifications or status updates.
    
    Request Body: {} (empty - releases all manual_release conditions for the user)
    
    Response:
    {
        "success": boolean,
        "message": "string",
        "summary": {
            "total_conditions": number,
            "already_released": number,
            "newly_released": number,
            "notifications_sent": number,
            "errors": number
        },
        "details": [
            {
                "benefactor_email": "string",
                "status": "released" | "already_released" | "error",
                "notification_sent": boolean,
                "error": "string (optional)"
            }
        ]
    }
    """
    
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': ''
        }
    
    try:
        # Extract Legacy Maker ID from Cognito authorizer claims
        legacy_maker_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
        if not legacy_maker_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Unable to identify user from token'})
            }
        
        print(f"Processing manual release for Legacy Maker: {legacy_maker_id}")
        
        # Query AccessConditionsDB for all manual_release conditions
        manual_release_conditions = get_manual_release_conditions(legacy_maker_id)
        
        if not manual_release_conditions:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'success': True,
                    'message': 'No manual release conditions found',
                    'summary': {
                        'total_conditions': 0,
                        'already_released': 0,
                        'newly_released': 0,
                        'notifications_sent': 0,
                        'errors': 0
                    },
                    'details': []
                })
            }
        
        # Process each condition
        summary = {
            'total_conditions': len(manual_release_conditions),
            'already_released': 0,
            'newly_released': 0,
            'notifications_sent': 0,
            'errors': 0
        }
        details = []
        
        # Track benefactors we've already notified to avoid duplicates
        notified_benefactors: Set[str] = set()
        
        for condition in manual_release_conditions:
            result = process_manual_release_condition(
                condition,
                legacy_maker_id,
                notified_benefactors
            )
            
            # Update summary
            if result['status'] == 'already_released':
                summary['already_released'] += 1
            elif result['status'] == 'released':
                summary['newly_released'] += 1
            elif result['status'] == 'error':
                summary['errors'] += 1
            
            if result.get('notification_sent'):
                summary['notifications_sent'] += 1
            
            details.append(result)
        
        # Log manual release event
        StructuredLogger.log_manual_release(
            initiator_id=legacy_maker_id,
            released_by=legacy_maker_id,
            conditions_released=summary['newly_released'],
            benefactors_notified=summary['notifications_sent']
        )
        
        # Return success response with summary
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'success': True,
                'message': f"Manual release completed. Released {summary['newly_released']} assignments.",
                'summary': summary,
                'details': details
            })
        }
        
    except Exception as e:
        print(f"Unexpected error in manual release: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }


def get_manual_release_conditions(legacy_maker_id: str) -> List[Dict]:
    """
    Query AccessConditionsDB for all manual_release conditions owned by the user.
    
    Uses the ConditionTypeIndex GSI to efficiently find all manual_release conditions,
    then filters to only those where the Legacy Maker is the initiator.
    
    Args:
        legacy_maker_id: Cognito user ID of the Legacy Maker
        
    Returns:
        List of condition records
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        
        # Query using ConditionTypeIndex GSI
        response = table.query(
            IndexName='ConditionTypeIndex',
            KeyConditionExpression='condition_type = :ctype',
            ExpressionAttributeValues={
                ':ctype': 'manual_release'
            }
        )
        
        all_conditions = response.get('Items', [])
        
        # Filter to only conditions owned by this Legacy Maker
        # relationship_key format: "initiator_id#related_user_id"
        user_conditions = []
        for condition in all_conditions:
            relationship_key = condition.get('relationship_key', '')
            if relationship_key.startswith(f"{legacy_maker_id}#"):
                user_conditions.append(condition)
        
        print(f"Found {len(user_conditions)} manual_release conditions for user {legacy_maker_id}")
        return user_conditions
        
    except ClientError as e:
        print(f"Error querying manual_release conditions: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"Unexpected error querying conditions: {str(e)}")
        return []


def process_manual_release_condition(
    condition: Dict,
    legacy_maker_id: str,
    notified_benefactors: Set[str]
) -> Dict:
    """
    Process a single manual_release condition.
    
    Implements idempotence by checking if already released. Updates both
    AccessConditionsDB and PersonaRelationshipsDB, and sends notification
    email if not already sent.
    
    Args:
        condition: Condition record from AccessConditionsDB
        legacy_maker_id: Cognito user ID of the Legacy Maker
        notified_benefactors: Set of benefactor IDs already notified (to avoid duplicates)
        
    Returns:
        Dict with status, benefactor_email, notification_sent, and optional error
    """
    relationship_key = condition.get('relationship_key', '')
    condition_id = condition.get('condition_id', '')
    
    # Parse relationship_key to get benefactor ID
    # Format: "initiator_id#related_user_id"
    parts = relationship_key.split('#')
    if len(parts) != 2:
        return {
            'benefactor_email': 'unknown',
            'status': 'error',
            'notification_sent': False,
            'error': 'Invalid relationship_key format'
        }
    
    initiator_id, related_user_id = parts
    
    # Verify ownership (should already be filtered, but double-check)
    if initiator_id != legacy_maker_id:
        return {
            'benefactor_email': 'unknown',
            'status': 'error',
            'notification_sent': False,
            'error': 'Unauthorized - not the assignment creator'
        }
    
    # Check if already released (idempotence)
    if condition.get('released_at'):
        print(f"Condition {condition_id} already released at {condition.get('released_at')}")
        return {
            'benefactor_email': get_benefactor_email(related_user_id),
            'status': 'already_released',
            'notification_sent': False,
            'released_at': condition.get('released_at')
        }
    
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Update condition with released_at timestamp and released_by user_id
        success = update_condition_released(
            relationship_key,
            condition_id,
            current_time,
            legacy_maker_id
        )
        
        if not success:
            return {
                'benefactor_email': get_benefactor_email(related_user_id),
                'status': 'error',
                'notification_sent': False,
                'error': 'Failed to update condition'
            }
        
        # Update relationship status to "active"
        success, result = update_relationship_status(
            initiator_id,
            related_user_id,
            'active'
        )
        
        if not success:
            print(f"Warning: Failed to update relationship status: {result.get('error')}")
            # Continue anyway - condition is released
        
        # Send notification email to Benefactor (only if not already sent)
        notification_sent = False
        benefactor_email = get_benefactor_email(related_user_id)
        
        if related_user_id not in notified_benefactors:
            try:
                notification_sent = send_access_granted_email(
                    benefactor_email=benefactor_email,
                    legacy_maker_id=legacy_maker_id
                )
                if notification_sent:
                    notified_benefactors.add(related_user_id)
            except Exception as email_error:
                print(f"Warning: Failed to send notification email: {str(email_error)}")
                # Don't fail the release - it's already processed
        
        return {
            'benefactor_email': benefactor_email,
            'status': 'released',
            'notification_sent': notification_sent,
            'released_at': current_time
        }
        
    except Exception as e:
        print(f"Error processing condition {condition_id}: {str(e)}")
        return {
            'benefactor_email': get_benefactor_email(related_user_id),
            'status': 'error',
            'notification_sent': False,
            'error': 'A server error occurred. Please try again.'
        }


def update_condition_released(
    relationship_key: str,
    condition_id: str,
    released_at: str,
    released_by: str
) -> bool:
    """
    Update a condition record with release information.
    
    Args:
        relationship_key: Composite key "initiator_id#related_user_id"
        condition_id: Unique condition identifier
        released_at: ISO 8601 timestamp
        released_by: User ID who triggered the release
        
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        
        table.update_item(
            Key={
                'relationship_key': relationship_key,
                'condition_id': condition_id
            },
            UpdateExpression='SET released_at = :released_at, released_by = :released_by, #status = :status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':released_at': released_at,
                ':released_by': released_by,
                ':status': 'activated'
            }
        )
        
        return True
        
    except ClientError as e:
        print(f"Error updating condition: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Unexpected error updating condition: {str(e)}")
        return False


def get_benefactor_email(related_user_id: str) -> str:
    """
    Get benefactor email from user ID or pending format.
    
    Args:
        related_user_id: Cognito user ID or "pending#email" format
        
    Returns:
        str: Email address
    """
    # Check if it's a pending user (format: "pending#email")
    if related_user_id.startswith('pending#'):
        return related_user_id.replace('pending#', '')
    
    # Look up user in Cognito
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            return 'unknown@example.com'
        
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=related_user_id
        )
        
        # Extract email from attributes
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                return attr['Value']
        
        return 'unknown@example.com'
        
    except Exception as e:
        print(f"Error getting benefactor email: {str(e)}")
        return 'unknown@example.com'


def send_access_granted_email(benefactor_email: str, legacy_maker_id: str) -> bool:
    """
    Send notification email to Benefactor when access is granted via manual release.
    
    Args:
        benefactor_email: Email address of the benefactor
        legacy_maker_id: Cognito user ID of the Legacy Maker
        
    Returns:
        bool: True if email sent successfully, False otherwise
    
    Requirements: 8.6, 13.5
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Email subject
        subject = "Legacy Content Access Granted"
        
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
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Legacy Content Access Granted</h2>
                    <p>Good news! A Legacy Maker has granted you access to their legacy content.</p>
                    <p>You can now view their videos, audio recordings, and text responses.</p>
                    <p>Click the button below to access the content:</p>
                    <a href="{os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard" class="button">View Legacy Content</a>
                    <p>Thank you for being a trusted Benefactor.</p>
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
        Legacy Content Access Granted
        
        Good news! A Legacy Maker has granted you access to their legacy content.
        
        You can now view their videos, audio recordings, and text responses.
        
        Visit your dashboard to access the content: {os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard
        
        Thank you for being a trusted Benefactor.
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [benefactor_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        
        print(f"Access granted email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending access granted email: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending access granted email: {str(e)}")
        return False

