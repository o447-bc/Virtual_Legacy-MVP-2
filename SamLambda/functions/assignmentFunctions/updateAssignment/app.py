"""
UpdateAssignment Lambda Function

Updates or manages existing Legacy Maker to Benefactor assignments.
Supports three actions: update_conditions, revoke, and delete.

Requirements: 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 12.1
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

from validation_utils import validate_access_conditions
from assignment_dal import (
    get_assignment,
    update_relationship_status,
    delete_access_conditions,
    create_access_conditions,
    delete_assignment,
    get_user_by_email
)
from logging_utils import StructuredLogger
from cors import cors_headers
from responses import error_response



def lambda_handler(event, context):
    """
    Update or manage an existing benefactor assignment.
    
    Request Body:
    {
        "action": "update_conditions" | "revoke" | "delete",
        "related_user_id": "string",
        "access_conditions": [...] (required for update_conditions)
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
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': ''
        }
    
    try:
        # Extract Legacy Maker ID from JWT token
        legacy_maker_id = extract_user_id_from_jwt(event)
        if not legacy_maker_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Unable to identify user from token'})
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', '').strip()
        related_user_id = body.get('related_user_id', '').strip()
        access_conditions = body.get('access_conditions', [])
        
        # Validate required parameters
        if not action:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'action is required'})
            }
        
        if not related_user_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'related_user_id is required'})
            }
        
        # Validate action is one of the allowed values
        valid_actions = {'update_conditions', 'revoke', 'delete'}
        if action not in valid_actions:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
                })
            }
        
        # Get the assignment to verify it exists and user is the creator
        success, assignment = get_assignment(legacy_maker_id, related_user_id)
        
        if not success:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'error': 'Failed to retrieve assignment',
                    'details': assignment.get('error') if assignment else None
                })
            }
        
        if not assignment:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Assignment not found'})
            }
        
        # Verify user is the assignment creator (authorization check)
        if assignment.get('initiator_id') != legacy_maker_id:
            return {
                'statusCode': 403,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'You are not authorized to modify this assignment'})
            }
        
        current_status = assignment.get('status')
        
        # Handle different actions
        if action == 'update_conditions':
            return handle_update_conditions(
                legacy_maker_id,
                related_user_id,
                current_status,
                access_conditions
            )
        
        elif action == 'revoke':
            return handle_revoke(
                legacy_maker_id,
                related_user_id,
                current_status,
                assignment
            )
        
        elif action == 'delete':
            return handle_delete(
                legacy_maker_id,
                related_user_id,
                current_status
            )
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }


def handle_update_conditions(
    initiator_id: str,
    related_user_id: str,
    current_status: str,
    access_conditions: list
) -> dict:
    """
    Handle update_conditions action.
    
    Requirements: 5.3, 5.7, 5.9
    """
    # Verify assignment status is "pending"
    if current_status != 'pending':
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Can only update conditions for pending assignments',
                'current_status': current_status
            })
        }
    
    # Validate access conditions
    is_valid, error_msg = validate_access_conditions(access_conditions)
    if not is_valid:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': error_msg})
        }
    
    # Delete existing access conditions
    success, delete_result = delete_access_conditions(initiator_id, related_user_id)
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Failed to delete existing access conditions',
                'details': delete_result.get('error')
            })
        }
    
    # Create new access conditions
    success, create_result = create_access_conditions(
        initiator_id,
        related_user_id,
        access_conditions
    )
    
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Failed to create new access conditions',
                'details': create_result.get('error')
            })
        }
    
    # Log access conditions update
    StructuredLogger.log_assignment_status_change(
        initiator_id=initiator_id,
        related_user_id=related_user_id,
        old_status=current_status,
        new_status=current_status,  # Status unchanged, conditions updated
        changed_by=initiator_id,
        reason='access_conditions_updated'
    )
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
        'body': json.dumps({
            'success': True,
            'message': 'Access conditions updated successfully',
            'conditions_deleted': delete_result.get('deleted_count', 0),
            'conditions_created': len(create_result) if isinstance(create_result, list) else 0
        })
    }


def handle_revoke(
    initiator_id: str,
    related_user_id: str,
    current_status: str,
    assignment: dict
) -> dict:
    """
    Handle revoke action.
    
    Requirements: 5.5, 5.6, 5.8
    """
    # Can only revoke active assignments (pending assignments should be deleted instead)
    if current_status not in ['active', 'pending']:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': f'Cannot revoke assignment with status: {current_status}',
                'current_status': current_status
            })
        }
    
    # Update relationship status to "revoked"
    success, update_result = update_relationship_status(
        initiator_id,
        related_user_id,
        'revoked'
    )
    
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Failed to revoke assignment',
                'details': update_result.get('error')
            })
        }
    
    # Log status change
    StructuredLogger.log_assignment_status_change(
        initiator_id=initiator_id,
        related_user_id=related_user_id,
        old_status=current_status,
        new_status='revoked',
        changed_by=initiator_id,
        reason='revoked_by_legacy_maker'
    )
    
    # Send notification email to Benefactor
    email_sent = False
    try:
        # Get benefactor email
        benefactor_email = None
        
        # Check if related_user_id is a pending email format
        if related_user_id.startswith('pending#'):
            benefactor_email = related_user_id.replace('pending#', '')
        else:
            # Look up user in Cognito
            user_found, user_data = get_user_by_email_or_id(related_user_id)
            if user_found and user_data:
                benefactor_email = user_data.get('email')
        
        if benefactor_email:
            email_sent = send_revocation_email(
                benefactor_email=benefactor_email,
                legacy_maker_id=initiator_id
            )
    except Exception as email_error:
        print(f"Warning: Failed to send revocation email: {str(email_error)}")
        # Don't fail the request - assignment is revoked
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
        'body': json.dumps({
            'success': True,
            'message': 'Assignment revoked successfully',
            'notification_sent': email_sent
        })
    }


def handle_delete(
    initiator_id: str,
    related_user_id: str,
    current_status: str
) -> dict:
    """
    Handle delete action.
    
    Requirements: 5.10
    """
    # Verify assignment status is "pending"
    if current_status != 'pending':
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Can only delete pending assignments',
                'current_status': current_status
            })
        }
    
    # Delete relationship and access condition records
    print(f"Attempting delete: initiator_id={initiator_id}, related_user_id={related_user_id}, current_status={current_status}")
    success, delete_result = delete_assignment(initiator_id, related_user_id)
    print(f"Delete result: success={success}, result={delete_result}")
    
    if not success:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'error': 'Failed to delete assignment',
                'details': delete_result.get('error')
            })
        }
    
    # Log assignment deletion
    StructuredLogger.log_assignment_deleted(
        initiator_id=initiator_id,
        related_user_id=related_user_id,
        deleted_by=initiator_id,
        conditions_deleted=delete_result.get('conditions_deleted', 0)
    )
    
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
        'body': json.dumps({
            'success': True,
            'message': 'Assignment deleted successfully',
            'conditions_deleted': delete_result.get('conditions_deleted', 0)
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


def get_user_by_email_or_id(user_id: str) -> tuple:
    """
    Get user information by user ID from Cognito.
    
    Args:
        user_id: Cognito user ID
        
    Returns:
        Tuple of (found: bool, user_data: dict or None)
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            return False, {'error': 'USER_POOL_ID environment variable not set'}
        
        # Get user by username (user_id)
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )
        
        # Extract user attributes
        user_email = None
        user_first_name = None
        user_last_name = None
        
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                user_email = attr['Value']
            elif attr['Name'] == 'given_name':
                user_first_name = attr['Value']
            elif attr['Name'] == 'family_name':
                user_last_name = attr['Value']
        
        user_data = {
            'user_id': response.get('Username'),
            'email': user_email,
            'first_name': user_first_name,
            'last_name': user_last_name,
            'user_status': response.get('UserStatus', 'UNKNOWN')
        }
        
        return True, user_data
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            return False, None
        print(f"Error getting user: {e.response['Error']['Message']}")
        return False, {'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"Unexpected error getting user: {str(e)}")
        return False, {'error': 'A server error occurred. Please try again.'}


def send_revocation_email(benefactor_email: str, legacy_maker_id: str) -> bool:
    """
    Send revocation notification email to benefactor.
    
    Args:
        benefactor_email: Email address of the benefactor
        legacy_maker_id: Cognito user ID of the Legacy Maker
        
    Returns:
        bool: True if email sent successfully, False otherwise
    
    Requirements: 5.8, 13.4
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Email subject
        subject = "Legacy Assignment Revoked"
        
        # HTML email body
        html_body = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #6366f1; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; background-color: #f9fafb; }
                .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Legacy Assignment Revoked</h2>
                    <p>A Legacy Maker has revoked your access to their legacy content.</p>
                    <p>You will no longer be able to view their content or receive updates.</p>
                    <p>If you have questions about this change, please contact the Legacy Maker directly.</p>
                </div>
                <div class="footer">
                    <p>Virtual Legacy - Preserving memories for future generations</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = """
        Legacy Assignment Revoked
        
        A Legacy Maker has revoked your access to their legacy content.
        
        You will no longer be able to view their content or receive updates.
        
        If you have questions about this change, please contact the Legacy Maker directly.
        
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
        
        print(f"Revocation email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending revocation email: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending revocation email: {str(e)}")
        return False
