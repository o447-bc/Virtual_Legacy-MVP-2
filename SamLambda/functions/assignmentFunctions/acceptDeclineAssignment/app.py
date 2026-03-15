"""
AcceptDeclineAssignment Lambda Function

Allows Benefactors to accept or decline Legacy Maker assignments.
Updates relationship status and sends notification emails to Legacy Makers.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 12.2
"""
import json
import os
import sys
import boto3
import base64
from datetime import datetime
from botocore.exceptions import ClientError

# Add shared functions to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from assignment_dal import (
    get_assignment,
    update_relationship_status,
    get_user_by_email
)
from logging_utils import StructuredLogger


def lambda_handler(event, context):
    """
    Accept or decline a benefactor assignment.
    
    Request Body:
    {
        "action": "accept" | "decline",
        "initiator_id": "string"
    }
    
    Response:
    {
        "success": boolean,
        "message": "string"
    }
    """
    
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': ''
        }
    
    try:
        # Extract Benefactor ID from JWT token
        benefactor_id = extract_user_id_from_jwt(event)
        if not benefactor_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Unable to identify user from token'})
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', '').strip().lower()
        initiator_id = body.get('initiator_id', '').strip()
        
        # Validate required parameters
        if not action:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'action is required'})
            }
        
        if not initiator_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'initiator_id is required'})
            }
        
        # Validate action is one of the allowed values
        valid_actions = {'accept', 'decline'}
        if action not in valid_actions:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
                })
            }
        
        # Get the assignment to verify it exists
        success, assignment = get_assignment(initiator_id, benefactor_id)
        
        if not success:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'Failed to retrieve assignment',
                    'details': assignment.get('error') if assignment else None
                })
            }
        
        if not assignment:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Assignment not found'})
            }
        
        # Verify user is the assigned Benefactor (authorization check)
        if assignment.get('related_user_id') != benefactor_id:
            return {
                'statusCode': 403,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'You are not authorized to respond to this assignment'})
            }
        
        # Validate assignment status is "pending"
        current_status = assignment.get('status')
        if current_status != 'pending':
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': f'Cannot {action} assignment with status: {current_status}',
                    'current_status': current_status
                })
            }
        
        # Handle accept or decline action
        if action == 'accept':
            return handle_accept(initiator_id, benefactor_id, assignment)
        elif action == 'decline':
            return handle_decline(initiator_id, benefactor_id, assignment)
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def handle_accept(
    initiator_id: str,
    benefactor_id: str,
    assignment: dict
) -> dict:
    """
    Handle accept action.
    
    Requirements: 7.2, 7.4
    """
    # Update relationship status to "active"
    success, update_result = update_relationship_status(
        initiator_id,
        benefactor_id,
        'active'
    )
    
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to accept assignment',
                'details': update_result.get('error')
            })
        }
    
    # Log status change
    StructuredLogger.log_assignment_status_change(
        initiator_id=initiator_id,
        related_user_id=benefactor_id,
        old_status='pending',
        new_status='active',
        changed_by=benefactor_id,
        reason='accepted_by_benefactor'
    )
    
    # Send confirmation email to Legacy Maker
    email_sent = False
    try:
        # Get Legacy Maker email
        legacy_maker_email = get_user_email_by_id(initiator_id)
        
        if legacy_maker_email:
            email_sent = send_acceptance_email(
                legacy_maker_email=legacy_maker_email,
                benefactor_id=benefactor_id
            )
    except Exception as email_error:
        print(f"Warning: Failed to send acceptance email: {str(email_error)}")
        # Don't fail the request - assignment is accepted
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'success': True,
            'message': 'Assignment accepted successfully',
            'status': 'active',
            'notification_sent': email_sent
        })
    }


def handle_decline(
    initiator_id: str,
    benefactor_id: str,
    assignment: dict
) -> dict:
    """
    Handle decline action.
    
    Requirements: 7.3, 7.5
    """
    # Update relationship status to "declined"
    success, update_result = update_relationship_status(
        initiator_id,
        benefactor_id,
        'declined'
    )
    
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to decline assignment',
                'details': update_result.get('error')
            })
        }
    
    # Log status change
    StructuredLogger.log_assignment_status_change(
        initiator_id=initiator_id,
        related_user_id=benefactor_id,
        old_status='pending',
        new_status='declined',
        changed_by=benefactor_id,
        reason='declined_by_benefactor'
    )
    
    # Send notification email to Legacy Maker
    email_sent = False
    try:
        # Get Legacy Maker email
        legacy_maker_email = get_user_email_by_id(initiator_id)
        
        if legacy_maker_email:
            email_sent = send_decline_email(
                legacy_maker_email=legacy_maker_email,
                benefactor_id=benefactor_id
            )
    except Exception as email_error:
        print(f"Warning: Failed to send decline email: {str(email_error)}")
        # Don't fail the request - assignment is declined
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'success': True,
            'message': 'Assignment declined successfully',
            'status': 'declined',
            'notification_sent': email_sent
        })
    }


def extract_user_id_from_jwt(event):
    """
    Extract user ID from JWT token in Authorization header.
    
    Args:
        event: Lambda event containing headers with Authorization token
        
    Returns:
        str: User ID from JWT token, or None if extraction fails
    """
    try:
        # Get Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            print("No Bearer token found in Authorization header")
            return None
        
        # Extract JWT token (remove 'Bearer ' prefix)
        jwt_token = auth_header[7:]
        
        # Parse JWT payload (second part after first dot)
        # JWT format: header.payload.signature
        token_parts = jwt_token.split('.')
        if len(token_parts) != 3:
            print("Invalid JWT token format")
            return None
        
        # Decode payload (add padding if needed for base64 decoding)
        payload_b64 = token_parts[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        
        # Decode base64 payload
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        # Extract user ID from 'sub' claim (standard JWT claim for subject/user ID)
        user_id = payload.get('sub')
        if user_id:
            print(f"Extracted user ID from JWT: {user_id}")
            return user_id
        else:
            print("No 'sub' claim found in JWT payload")
            return None
            
    except Exception as e:
        print(f"Error extracting user ID from JWT: {str(e)}")
        return None


def get_user_email_by_id(user_id: str) -> str:
    """
    Get user email by Cognito user ID.
    
    Args:
        user_id: Cognito user ID
        
    Returns:
        str: User email or None if not found
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            print("USER_POOL_ID environment variable not set")
            return None
        
        # Get user by username (user_id)
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
        if e.response['Error']['Code'] == 'UserNotFoundException':
            print(f"User not found: {user_id}")
            return None
        print(f"Error getting user email: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"Unexpected error getting user email: {str(e)}")
        return None


def send_acceptance_email(legacy_maker_email: str, benefactor_id: str) -> bool:
    """
    Send acceptance confirmation email to Legacy Maker.
    
    Args:
        legacy_maker_email: Email address of the Legacy Maker
        benefactor_id: Cognito user ID of the Benefactor
        
    Returns:
        bool: True if email sent successfully, False otherwise
    
    Requirements: 7.4, 13.2
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Get benefactor name if available
        benefactor_name = get_user_name_by_id(benefactor_id)
        if not benefactor_name:
            benefactor_name = "A benefactor"
        
        # Email subject
        subject = "Benefactor Assignment Accepted"
        
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
                    <h2>Assignment Accepted</h2>
                    <p>{benefactor_name} has accepted your benefactor assignment.</p>
                    <p>They will now have access to your legacy content according to the access conditions you configured.</p>
                    <p>You can manage your benefactor assignments at any time from your dashboard.</p>
                    <a href="http://localhost:8080/manage-benefactors" class="button">Manage Benefactors</a>
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
        Assignment Accepted
        
        {benefactor_name} has accepted your benefactor assignment.
        
        They will now have access to your legacy content according to the access conditions you configured.
        
        You can manage your benefactor assignments at any time from your dashboard.
        
        Visit: http://localhost:8080/manage-benefactors
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [legacy_maker_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        
        print(f"Acceptance email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending acceptance email: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending acceptance email: {str(e)}")
        return False


def send_decline_email(legacy_maker_email: str, benefactor_id: str) -> bool:
    """
    Send decline notification email to Legacy Maker.
    
    Args:
        legacy_maker_email: Email address of the Legacy Maker
        benefactor_id: Cognito user ID of the Benefactor
        
    Returns:
        bool: True if email sent successfully, False otherwise
    
    Requirements: 7.5, 13.3
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Get benefactor name if available
        benefactor_name = get_user_name_by_id(benefactor_id)
        if not benefactor_name:
            benefactor_name = "A benefactor"
        
        # Email subject
        subject = "Benefactor Assignment Declined"
        
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
                    <h2>Assignment Declined</h2>
                    <p>{benefactor_name} has declined your benefactor assignment.</p>
                    <p>They will not have access to your legacy content.</p>
                    <p>You can manage your benefactor assignments or create new ones at any time from your dashboard.</p>
                    <a href="http://localhost:8080/manage-benefactors" class="button">Manage Benefactors</a>
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
        Assignment Declined
        
        {benefactor_name} has declined your benefactor assignment.
        
        They will not have access to your legacy content.
        
        You can manage your benefactor assignments or create new ones at any time from your dashboard.
        
        Visit: http://localhost:8080/manage-benefactors
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [legacy_maker_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        
        print(f"Decline email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending decline email: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending decline email: {str(e)}")
        return False


def get_user_name_by_id(user_id: str) -> str:
    """
    Get user's full name by Cognito user ID.
    
    Args:
        user_id: Cognito user ID
        
    Returns:
        str: User's full name or None if not found
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            return None
        
        # Get user by username (user_id)
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )
        
        # Extract name from user attributes
        first_name = None
        last_name = None
        
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'given_name':
                first_name = attr['Value']
            elif attr['Name'] == 'family_name':
                last_name = attr['Value']
        
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        
        return None
        
    except Exception as e:
        print(f"Error getting user name: {str(e)}")
        return None
