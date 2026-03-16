"""
CreateAssignment Lambda Function

Creates a new Legacy Maker to Benefactor assignment with access conditions.
Handles both registered and unregistered Benefactors, sending appropriate
invitation or notification emails.

Requirements: 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 6.1, 6.2, 6.3, 6.8
# v2 - updated email copy
"""
import json
import os
import sys
import boto3
from datetime import datetime
from urllib.parse import quote
from botocore.exceptions import ClientError

# Add shared functions to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from validation_utils import validate_access_conditions
from assignment_dal import (
    create_assignment_record,
    create_access_conditions,
    check_duplicate_assignment,
    get_user_by_email
)
from invitation_utils import create_invitation_token
from assignment_dal import delete_assignment
from logging_utils import StructuredLogger
from cors import cors_headers
from responses import error_response



def lambda_handler(event, context):
    """
    Create a new benefactor assignment with access conditions.

    Request Body:
    {
        "benefactor_email": "string",
        "access_conditions": [
            {
                "condition_type": "immediate" | "time_delayed" | "inactivity_trigger" | "manual_release",
                "activation_date": "ISO 8601 string (optional)",
                "inactivity_months": number (optional)",
                "check_in_interval_days": number (optional)
            }
        ]
    }

    Response:
    {
        "assignment_id": "string",
        "status": "pending",
        "invitation_sent": boolean,
        "message": "string"
    }
    """

    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
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

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        benefactor_email = body.get('benefactor_email', '').strip()
        access_conditions = body.get('access_conditions', [])

        # Validate required parameters
        if not benefactor_email:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'benefactor_email is required'})
            }

        # Validate access conditions
        is_valid, error_msg = validate_access_conditions(access_conditions)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': error_msg})
            }

        # Lookup benefactor email in Cognito
        user_found, user_data = get_user_by_email(benefactor_email)

        # Handle errors from Cognito lookup
        if user_data and 'error' in user_data:
            print(f"Warning: Cognito lookup error: {user_data['error']}")
            # Continue with invitation flow for unregistered user
            user_found = False

        # Determine benefactor user ID
        if user_found:
            benefactor_id = user_data['user_id']
        else:
            # Use pending# prefix for unregistered users
            benefactor_id = f"pending#{benefactor_email}"

        # Check for duplicate assignment
        duplicate_exists, existing_record = check_duplicate_assignment(legacy_maker_id, benefactor_id)
        if duplicate_exists:
            return {
                'statusCode': 409,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({
                    'error': f'Assignment already exists for benefactor {benefactor_email}'
                })
            }

        # Create assignment record in PersonaRelationshipsDB
        success, assignment_record = create_assignment_record(
            initiator_id=legacy_maker_id,
            related_user_id=benefactor_id,
            relationship_type='legacy_maker_benefactor',
            created_via='maker_assignment'
        )
        
        if not success:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': assignment_record.get('error', 'Failed to create assignment')})
            }

        # Create access conditions in AccessConditionsDB
        success, conditions_result = create_access_conditions(
            initiator_id=legacy_maker_id,
            related_user_id=benefactor_id,
            access_conditions=access_conditions
        )

        if not success:
            # Rollback: remove the relationship record we just created
            delete_assignment(legacy_maker_id, benefactor_id)
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': conditions_result.get('error', 'Failed to create access conditions')})
            }

        # Send invitation or notification email.
        # IMPORTANT: if email fails, rollback ALL DB writes so no orphaned records are left.
        invitation_sent = False
        invitation_token = None

        if not user_found:
            # Create invitation token
            assignment_details = {
                'access_conditions': access_conditions,
                'relationship_type': 'legacy_maker_benefactor',
                'created_via': 'maker_assignment'
            }
            token_success, token_result = create_invitation_token(
                initiator_id=legacy_maker_id,
                benefactor_email=benefactor_email,
                assignment_details=assignment_details
            )

            if not token_success:
                # Rollback DB writes
                delete_assignment(legacy_maker_id, benefactor_id)
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                    'body': json.dumps({'error': token_result.get('error', 'Failed to create invitation token')})
                }

            invitation_token = token_result.get('invite_token')

            # Send invitation email via SES
            email_sent = send_assignment_invitation_email(
                benefactor_email=benefactor_email,
                legacy_maker_id=legacy_maker_id,
                invitation_token=invitation_token,
                access_conditions=access_conditions
            )
            if not email_sent:
                # Rollback: remove relationship, conditions, and invitation token
                delete_assignment(legacy_maker_id, benefactor_id)
                boto3.resource('dynamodb').Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB')).delete_item(
                    Key={'userName': invitation_token}
                )
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                    'body': json.dumps({'error': 'Failed to send invitation email. No assignment was created.'})
                }

            invitation_sent = True
        else:
            # Send notification email to registered benefactor
            email_sent = send_assignment_notification_email(
                benefactor_email=benefactor_email,
                legacy_maker_id=legacy_maker_id,
                access_conditions=access_conditions
            )

            if not email_sent:
                # Rollback: remove relationship and conditions
                delete_assignment(legacy_maker_id, benefactor_id)
                return {
                    'statusCode': 500,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                    'body': json.dumps({'error': 'Failed to send notification email. No assignment was created.'})
                }

            invitation_sent = True

        # Return success response
        # Generate a composite assignment_id from the relationship
        assignment_id = f"{legacy_maker_id}#{benefactor_id}"
        
        response_body = {
            'message': 'Assignment created successfully',
            'assignment_id': assignment_id,
            'status': 'pending',
            'benefactor_registered': user_found,
            'invitation_sent': invitation_sent,
            'conditions_created': len(conditions_result) if isinstance(conditions_result, list) else 0
        }

        if invitation_token:
            response_body['invitation_token'] = invitation_token

        return {
            'statusCode': 201,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps(response_body)
        }

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }



def get_legacy_maker_name(legacy_maker_id):
    """
    Look up the Legacy Maker's display name from Cognito by user ID.

    Args:
        legacy_maker_id: Cognito sub / username of the Legacy Maker

    Returns:
        str: "First Last" if available, otherwise "Someone who cares about you"
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        if not user_pool_id:
            return "Someone who cares about you"

        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=legacy_maker_id
        )

        first_name = ''
        last_name = ''
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'given_name':
                first_name = attr['Value']
            elif attr['Name'] == 'family_name':
                last_name = attr['Value']

        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else "Someone who cares about you"

    except Exception as e:
        print(f"Warning: could not fetch legacy maker name: {str(e)}")
        return "Someone who cares about you"


def send_assignment_invitation_email(benefactor_email, legacy_maker_id, invitation_token, access_conditions):
    """
    Send invitation email to unregistered benefactor.
    
    Args:
        benefactor_email: Email address of the benefactor being invited
        legacy_maker_id: Cognito user ID of the Legacy Maker
        invitation_token: Unique invitation token for registration
        access_conditions: List of access condition dictionaries
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')

        # Look up legacy maker's name
        legacy_maker_name = get_legacy_maker_name(legacy_maker_id)

        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
        
        # Format access conditions for email
        conditions_text = format_access_conditions_for_email(access_conditions)
        
        # Email subject
        subject = f"{legacy_maker_name} wants to share their story with you on SoulReel"
        
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
                .button {{ display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .conditions {{ background-color: white; padding: 15px; border-left: 4px solid #6366f1; margin: 20px 0; border-radius: 4px; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SoulReel</h1>
                </div>
                <div class="content">
                    <h2>{legacy_maker_name} wants to share their story with you</h2>
                    <p>Hi there,</p>
                    <p><strong>{legacy_maker_name}</strong> has named you as a Benefactor on SoulReel.</p>
                    <p>SoulReel is where people record their life stories, memories, and personal wisdom to share with the people they love. As their Benefactor, you'll be given access to what they've recorded — their voice, their stories, their legacy — when the conditions they've set are met.</p>
                    <div class="conditions">
                        <h3>When you'll receive access:</h3>
                        {conditions_text}
                    </div>
                    <p>To accept this gift and create your free SoulReel account, click the button below. This invitation expires in 30 days.</p>
                    <p style="text-align: center;">
                        <a href="https://www.soulreel.net/signup?invite={invitation_token}&email={quote(benefactor_email)}" class="button">Accept & Create Account</a>
                    </p>
                </div>
                <div class="footer">
                    <p>This invitation was sent on behalf of {legacy_maker_name}</p>
                    <p>SoulReel — Preserving memories for future generations</p>
                    <p>If you weren't expecting this, you can safely ignore it — no account will be created without your action.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        {legacy_maker_name} wants to share their story with you on SoulReel

        Hi there,

        {legacy_maker_name} has named you as a Benefactor on SoulReel.

        SoulReel is where people record their life stories, memories, and personal wisdom to share with the people they love. As their Benefactor, you'll be given access to what they've recorded — their voice, their stories, their legacy — when the conditions they've set are met.

        When you'll receive access:
        {conditions_text}

        To accept this gift and create your free SoulReel account, visit:
        https://www.soulreel.net/signup?invite={invitation_token}&email={quote(benefactor_email)}

        This invitation expires in 30 days.

        If you weren't expecting this, you can safely ignore it — no account will be created without your action.

        This invitation was sent on behalf of {legacy_maker_name}
        SoulReel — Preserving memories for future generations
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
        
        print(f"Invitation email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending invitation: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending invitation email: {str(e)}")
        return False


def send_assignment_notification_email(benefactor_email, legacy_maker_id, access_conditions):
    """
    Send notification email to registered benefactor.
    
    Args:
        benefactor_email: Email address of the registered benefactor
        legacy_maker_id: Cognito user ID of the Legacy Maker
        access_conditions: List of access condition dictionaries
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        ses_client = boto3.client('ses', region_name='us-east-1')

        # Look up legacy maker's name
        legacy_maker_name = get_legacy_maker_name(legacy_maker_id)
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
        
        # Format access conditions for email
        conditions_text = format_access_conditions_for_email(access_conditions)
        
        # Email subject
        subject = f"{legacy_maker_name} has chosen you to receive their SoulReel legacy"
        
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
                .button {{ display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .conditions {{ background-color: white; padding: 15px; border-left: 4px solid #6366f1; margin: 20px 0; border-radius: 4px; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SoulReel</h1>
                </div>
                <div class="content">
                    <h2>{legacy_maker_name} has chosen you to receive their SoulReel legacy</h2>
                    <p>Hi there,</p>
                    <p><strong>{legacy_maker_name}</strong> has named you as a Benefactor on SoulReel.</p>
                    <p>SoulReel is where people record their life stories, memories, and personal wisdom to share with the people they love. As their Benefactor, you'll be given access to what they've recorded — their voice, their stories, their legacy — when the conditions they've set are met.</p>
                    <div class="conditions">
                        <h3>When you'll receive access:</h3>
                        {conditions_text}
                    </div>
                    <p>Log in to your SoulReel account to review and respond to this assignment.</p>
                    <p style="text-align: center;">
                        <a href="https://www.soulreel.net/dashboard" class="button">View My Assignments</a>
                    </p>
                </div>
                <div class="footer">
                    <p>SoulReel — Preserving memories for future generations</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        {legacy_maker_name} has chosen you to receive their SoulReel legacy

        Hi there,

        {legacy_maker_name} has named you as a Benefactor on SoulReel.

        SoulReel is where people record their life stories, memories, and personal wisdom to share with the people they love. As their Benefactor, you'll be given access to what they've recorded — their voice, their stories, their legacy — when the conditions they've set are met.

        When you'll receive access:
        {conditions_text}

        Log in to your SoulReel account to review and respond to this assignment:
        https://www.soulreel.net/dashboard

        SoulReel — Preserving memories for future generations
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
        
        print(f"Notification email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending notification: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending notification email: {str(e)}")
        return False


def format_access_conditions_for_email(access_conditions):
    """
    Format access conditions into human-readable text for email.
    
    Args:
        access_conditions: List of access condition dictionaries
        
    Returns:
        str: Formatted HTML string describing the access conditions
    """
    if not access_conditions:
        return "<p>No specific conditions - access will be granted upon acceptance.</p>"
    
    conditions_html = "<ul>"
    
    for condition in access_conditions:
        condition_type = condition.get('condition_type')
        
        if condition_type == 'immediate':
            conditions_html += "<li><strong>Immediate Access:</strong> Content will be accessible immediately upon acceptance</li>"
        
        elif condition_type == 'time_delayed':
            activation_date = condition.get('activation_date', 'Not specified')
            conditions_html += f"<li><strong>Time-Delayed Access:</strong> Content will become accessible on {activation_date}</li>"
        
        elif condition_type == 'inactivity_trigger':
            months = condition.get('inactivity_months', 'Not specified')
            conditions_html += f"<li><strong>Inactivity Trigger:</strong> Content will become accessible if the Legacy Maker is inactive for {months} months</li>"
        
        elif condition_type == 'manual_release':
            conditions_html += "<li><strong>Manual Release:</strong> Content will become accessible when the Legacy Maker manually releases it</li>"
    
    conditions_html += "</ul>"
    return conditions_html
