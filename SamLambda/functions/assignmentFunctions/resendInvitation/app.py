"""
ResendInvitation Lambda Function

Allows Legacy Makers to resend invitation emails to Benefactors who haven't registered yet.
Validates ownership and assignment status before generating a new invitation token.

Requirements: 5.11, 6.7
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

from invitation_utils import create_invitation_token


def lambda_handler(event, context):
    """
    Resend invitation email to an unregistered Benefactor.
    
    Request Body:
    {
        "related_user_id": "string (optional - pending#email format)",
        "benefactor_email": "string (optional - if related_user_id not provided)"
    }
    
    Response:
    {
        "success": boolean,
        "message": "string",
        "invitation_token": "string (optional)"
    }
    """
    
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
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
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({'error': 'Unable to identify user from token'})
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        related_user_id = body.get('related_user_id', '').strip()
        benefactor_email = body.get('benefactor_email', '').strip()
        
        # Validate that at least one identifier is provided
        if not related_user_id and not benefactor_email:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({'error': 'Either related_user_id or benefactor_email is required'})
            }
        
        # If related_user_id is provided, extract email from it
        if related_user_id:
            # Check if it's in pending format (pending#email)
            if related_user_id.startswith('pending#'):
                benefactor_email = related_user_id.split('#', 1)[1]
            else:
                # User has already registered
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                    'body': json.dumps({
                        'error': 'Cannot resend invitation to registered user',
                        'message': 'This benefactor has already registered'
                    })
                }
        
        # Construct related_user_id if not provided
        if not related_user_id:
            related_user_id = f"pending#{benefactor_email.lower()}"
        
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        relationships_table = dynamodb.Table('PersonaRelationshipsDB')
        
        # Verify assignment exists and user owns it
        try:
            response = relationships_table.get_item(
                Key={
                    'initiator_id': legacy_maker_id,
                    'related_user_id': related_user_id
                }
            )
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                    'body': json.dumps({
                        'error': 'Assignment not found',
                        'message': 'No assignment found for this benefactor'
                    })
                }
            
            assignment = response['Item']
            
        except ClientError as e:
            print(f"Error retrieving assignment: {e.response['Error']['Message']}")
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({
                    'error': 'Failed to retrieve assignment',
                    'details': e.response['Error']['Message']
                })
            }
        
        # Verify assignment status is "pending"
        assignment_status = assignment.get('status', '')
        if assignment_status != 'pending':
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({
                    'error': 'Cannot resend invitation',
                    'message': f'Assignment status is "{assignment_status}". Can only resend for pending assignments.',
                    'current_status': assignment_status
                })
            }
        
        # Verify benefactor hasn't registered (related_user_id should still be in pending format)
        if not related_user_id.startswith('pending#'):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({
                    'error': 'Cannot resend invitation',
                    'message': 'Benefactor has already registered'
                })
            }
        
        # Get access conditions for this assignment
        access_conditions_table = dynamodb.Table('AccessConditionsDB')
        relationship_key = f"{legacy_maker_id}#{related_user_id}"
        
        try:
            conditions_response = access_conditions_table.query(
                KeyConditionExpression='relationship_key = :rk',
                ExpressionAttributeValues={
                    ':rk': relationship_key
                }
            )
            
            access_conditions = []
            for item in conditions_response.get('Items', []):
                condition = {
                    'condition_type': item.get('condition_type')
                }
                
                # Add type-specific fields
                if item.get('activation_date'):
                    condition['activation_date'] = item['activation_date']
                if item.get('inactivity_months'):
                    condition['inactivity_months'] = item['inactivity_months']
                if item.get('check_in_interval_days'):
                    condition['check_in_interval_days'] = item['check_in_interval_days']
                
                access_conditions.append(condition)
            
        except ClientError as e:
            print(f"Error retrieving access conditions: {e.response['Error']['Message']}")
            # Continue with empty conditions - not critical for resend
            access_conditions = []
        
        # Generate new invitation token
        assignment_details = {
            'access_conditions': access_conditions,
            'relationship_type': assignment.get('relationship_type', 'maker_to_benefactor'),
            'created_via': assignment.get('created_via', 'maker_assignment')
        }
        
        success, token_result = create_invitation_token(
            legacy_maker_id,
            benefactor_email,
            assignment_details
        )
        
        if not success:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({
                    'error': 'Failed to create invitation token',
                    'details': token_result.get('error')
                })
            }
        
        invitation_token = token_result.get('invite_token')
        
        # Send invitation email
        email_sent = False
        try:
            email_sent = send_invitation_email(
                benefactor_email=benefactor_email,
                legacy_maker_id=legacy_maker_id,
                invitation_token=invitation_token,
                access_conditions=access_conditions
            )
        except Exception as email_error:
            print(f"Warning: Failed to send email: {str(email_error)}")
            # Don't fail the request - token is created
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
            'body': json.dumps({
                'success': True,
                'message': 'Invitation resent successfully',
                'invitation_token': invitation_token,
                'email_sent': email_sent,
                'benefactor_email': benefactor_email
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
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


def send_invitation_email(benefactor_email, legacy_maker_id, invitation_token, access_conditions):
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
        
        # Get sender email from environment or use default
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        # Format access conditions for email
        conditions_text = format_access_conditions_for_email(access_conditions)
        
        # Email subject
        subject = "Reminder: You've been assigned access to a Virtual Legacy"
        
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
                .conditions {{ background-color: white; padding: 15px; border-left: 4px solid #6366f1; margin: 20px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Reminder: You've been assigned access to a Virtual Legacy</h2>
                    <p>This is a reminder that a Legacy Maker has assigned you as a Benefactor to access their legacy content.</p>
                    <p>To accept this assignment and view their content, you'll need to create a Virtual Legacy account.</p>
                    <div class="conditions">
                        <h3>Access Conditions:</h3>
                        {conditions_text}
                    </div>
                    <p>Click the button below to register and accept this assignment:</p>
                    <a href="http://localhost:8080/signup?invite={invitation_token}" class="button">Register & Accept Assignment</a>
                    <p>This invitation will expire in 30 days.</p>
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
        Reminder: You've been assigned access to a Virtual Legacy
        
        This is a reminder that a Legacy Maker has assigned you as a Benefactor to access their legacy content.
        
        To accept this assignment and view their content, you'll need to create a Virtual Legacy account.
        
        Access Conditions:
        {conditions_text}
        
        Visit this link to register and accept: http://localhost:8080/signup?invite={invitation_token}
        
        This invitation will expire in 30 days.
        
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
        
        print(f"Invitation email sent successfully. MessageId: {response['MessageId']}")
        return True
        
    except ClientError as e:
        print(f"SES Error sending invitation: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Error sending invitation email: {str(e)}")
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
