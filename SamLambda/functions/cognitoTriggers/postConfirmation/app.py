import json
import boto3
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

from invitation_utils import link_registration_to_assignment
from logging_utils import StructuredLogger

def lambda_handler(event, context):
    """
    Cognito Post-confirmation trigger to set persona attributes and handle invites
    """
    print(f"Post-confirmation event: {json.dumps(event)}")
    
    # Get user details
    user_pool_id = event['userPoolId']
    username = event['userName']  # This is the Cognito User ID
    
    print(f"Processing user: {username}")
    
    # Initialize Cognito client early
    cognito_client = boto3.client('cognito-idp')
    
    # Get persona data from DynamoDB (stored by PreSignup)
    persona_type = 'legacy_maker'  # Default
    invite_token = None
    invite_data = None
    first_name = None
    last_name = None
    
    try:
        dynamodb = boto3.resource('dynamodb')
        temp_table = dynamodb.Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB'))
        
        # Get persona data using username (stored by PreSignup)
        response = temp_table.get_item(Key={'userName': username})
        if 'Item' in response:
            persona_data = response['Item']
            persona_type = persona_data.get('persona_type', 'legacy_maker')
            invite_token = persona_data.get('invite_token')  # Get invite token from stored data
            first_name = persona_data.get('first_name')
            last_name = persona_data.get('last_name')
            
            print(f"Retrieved persona_type from username: {persona_type}")
            print(f"Retrieved invite_token from stored data: {invite_token}")
            print(f"Retrieved names: {first_name} {last_name}")
            
            # Clean up the temporary record
            temp_table.delete_item(Key={'userName': username})
            print(f"Cleaned up temp record for user: {username}")
        
        # If we have an invite token, get invite data
        if invite_token:
            print(f"Processing invite token: {invite_token}")
            invite_response = temp_table.get_item(Key={'userName': invite_token})
            if 'Item' in invite_response:
                invite_data = invite_response['Item']
                invite_type = invite_data.get('invite_type', 'benefactor_invite')  # Default to old type
                print(f"Found invite data with type: {invite_type}")
                
                # Get user email for verification
                user_email = event.get('request', {}).get('userAttributes', {}).get('email', '').lower()
                
                # Handle maker-initiated assignment invitations (NEW)
                if invite_type == 'maker_assignment':
                    print(f"Processing maker assignment invitation for: {user_email}")
                    
                    # Use invitation_utils to link registration to assignment
                    success, result = link_registration_to_assignment(
                        invite_token=invite_token,
                        new_user_id=username,
                        user_email=user_email
                    )
                    
                    if success:
                        print(f"Successfully linked registration to assignment: {result}")
                        
                        # Log invitation acceptance
                        StructuredLogger.log_invitation_accepted(
                            initiator_id=result.get('initiator_id'),
                            related_user_id=username,
                            invitation_token=invite_token,
                            new_user_registered=True
                        )
                        
                        # Send assignment notification email to new benefactor
                        try:
                            send_assignment_notification_to_new_user(
                                benefactor_email=user_email,
                                initiator_id=result.get('initiator_id'),
                                new_user_id=username
                            )
                            print(f"Sent assignment notification email to: {user_email}")
                        except Exception as email_error:
                            print(f"Failed to send assignment notification email: {str(email_error)}")
                            # Don't fail signup if email fails
                    else:
                        print(f"Failed to link registration to assignment: {result}")
                        # Don't fail signup process
                
                # Handle benefactor-initiated invitations (EXISTING)
                elif invite_type == 'benefactor_invite' or 'benefactor_id' in invite_data:
                    print(f"Processing benefactor-initiated invitation")
                    
                    # Verify the email matches (security check) - normalize to lowercase
                    invite_email = invite_data.get('invitee_email', '').lower()
                    
                    if user_email == invite_email:
                        print(f"Email verification passed: {user_email}")
                        # Create relationship between benefactor and new legacy maker
                        create_benefactor_relationship(invite_data.get('benefactor_id'), username)
                        
                        # Clean up invite token
                        temp_table.delete_item(Key={'userName': invite_token})
                        print(f"Cleaned up invite token: {invite_token}")
                    else:
                        print(f"Email mismatch: user={user_email}, invite={invite_email}")
                else:
                    print(f"Unknown invite type: {invite_type}")
            else:
                print(f"No invite data found for token: {invite_token}")
        
    except Exception as e:
        print(f"Error processing persona/invite data: {str(e)}")
    
    print(f"Setting persona_type: {persona_type} for user: {username}")
    
    try:
        # Set persona attributes using AdminUpdateUserAttributes
        # Using profile field to store persona data as JSON since custom attributes aren't in schema
        persona_data = {
            'persona_type': persona_type,
            'initiator_id': username,
            'related_user_id': ''
        }
        
        # Prepare user attributes list
        user_attributes = [
            {
                'Name': 'profile',
                'Value': json.dumps(persona_data)
            }
        ]
        
        # Add first and last name if available
        if first_name:
            user_attributes.append({
                'Name': 'given_name',
                'Value': first_name
            })
        if last_name:
            user_attributes.append({
                'Name': 'family_name',
                'Value': last_name
            })
        
        # Retry loop — transient Cognito errors can cause permanent persona loss
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                cognito_client.admin_update_user_attributes(
                    UserPoolId=user_pool_id,
                    Username=username,
                    UserAttributes=user_attributes
                )
                print(f"Successfully set persona attributes for user: {username}")
                break
            except Exception as retry_error:
                print(f"Attempt {attempt}/{max_retries} failed to update user attributes: {str(retry_error)}")
                if attempt < max_retries:
                    time.sleep(0.5 * attempt)  # 0.5s, 1s backoff
                else:
                    # CRITICAL: All retries exhausted — user has no persona set.
                    # This will cause them to default to legacy_maker on next login.
                    print(f"CRITICAL: Failed to set persona for user {username} after {max_retries} attempts. "
                          f"Persona type was: {persona_type}. Error: {str(retry_error)}")
        
    except Exception as e:
        print(f"CRITICAL: Error preparing persona attributes for user {username}: {str(e)}")
        # Don't fail the signup process
    
    return event

def create_benefactor_relationship(benefactor_id, legacy_maker_id):
    """
    Create relationship between benefactor and legacy maker in PersonaRelationshipsDB
    
    Args:
        benefactor_id: Cognito user ID of the benefactor
        legacy_maker_id: Cognito user ID of the new legacy maker
    """
    try:
        print(f"Creating relationship: benefactor={benefactor_id} -> legacy_maker={legacy_maker_id}")
        
        dynamodb = boto3.resource('dynamodb')
        relationships_table = dynamodb.Table(os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB'))
        
        # Create relationship record
        relationships_table.put_item(
            Item={
                'initiator_id': benefactor_id,  # The benefactor who sent the invite
                'related_user_id': legacy_maker_id,  # The new legacy maker
                'relationship_type': 'benefactor_to_legacy_maker',  # Type of relationship
                'status': 'active',  # Relationship status
                'created_at': datetime.now().isoformat(),  # When relationship was created
                'created_via': 'invite_acceptance'  # How the relationship was created
            }
        )
        
        print(f"Successfully created relationship between {benefactor_id} and {legacy_maker_id}")
        
    except Exception as e:
        print(f"Error creating relationship: {str(e)}")
        # Don't fail the signup process if relationship creation fails
        pass


def send_assignment_notification_to_new_user(
    benefactor_email: str,
    initiator_id: str,
    new_user_id: str
) -> bool:
    """
    Send assignment notification email to newly registered benefactor.
    
    This function is called after a new user registers via an assignment invitation
    to notify them about the pending assignment that needs their acceptance.
    
    Args:
        benefactor_email: Email address of the newly registered benefactor
        initiator_id: Cognito user ID of the Legacy Maker who created the assignment
        new_user_id: Cognito user ID of the newly registered benefactor
        
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Requirements: 6.5
    """
    try:
        # Get access conditions for this assignment
        dynamodb = boto3.resource('dynamodb')
        access_conditions_table = dynamodb.Table(os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB'))
        
        relationship_key = f"{initiator_id}#{new_user_id}"
        
        # Query access conditions
        response = access_conditions_table.query(
            KeyConditionExpression='relationship_key = :rk',
            ExpressionAttributeValues={
                ':rk': relationship_key
            }
        )
        
        access_conditions = response.get('Items', [])
        
        # Format access conditions for email
        conditions_html = format_access_conditions_html(access_conditions)
        
        # Send email via SES
        ses_client = boto3.client('ses', region_name='us-east-1')
        sender_email = os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')
        
        subject = "Welcome to Virtual Legacy - Assignment Awaiting Your Response"
        
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
                    <h1>Welcome to Virtual Legacy</h1>
                </div>
                <div class="content">
                    <h2>Your account has been created successfully!</h2>
                    <p>You've been assigned as a Benefactor to access a Legacy Maker's content.</p>
                    <p>A pending assignment is waiting for your review. Please log in to accept or decline this assignment.</p>
                    <div class="conditions">
                        <h3>Access Conditions:</h3>
                        {conditions_html}
                    </div>
                    <p>Click the button below to view and respond to your assignment:</p>
                    <a href="{os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard" class="button">View Assignment</a>
                </div>
                <div class="footer">
                    <p>Virtual Legacy - Preserving memories for future generations</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to Virtual Legacy!
        
        Your account has been created successfully.
        
        You've been assigned as a Benefactor to access a Legacy Maker's content.
        A pending assignment is waiting for your review.
        
        Please log in to your account to accept or decline this assignment.
        
        Visit: {os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')}/dashboard
        
        Virtual Legacy - Preserving memories for future generations
        """
        
        ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [benefactor_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }
        )
        
        print(f"Successfully sent assignment notification email to: {benefactor_email}")
        return True
        
    except Exception as e:
        print(f"Error sending assignment notification email: {str(e)}")
        return False


def format_access_conditions_html(access_conditions: list) -> str:
    """
    Format access conditions as HTML for email display.
    
    Args:
        access_conditions: List of access condition dictionaries
        
    Returns:
        str: HTML formatted access conditions
    """
    if not access_conditions:
        return "<p>No specific access conditions</p>"
    
    html_parts = ["<ul>"]
    
    for condition in access_conditions:
        condition_type = condition.get('condition_type', 'unknown')
        
        if condition_type == 'immediate':
            html_parts.append("<li><strong>Immediate Access:</strong> Content available immediately upon acceptance</li>")
        
        elif condition_type == 'time_delayed':
            activation_date = condition.get('activation_date', 'Not specified')
            html_parts.append(f"<li><strong>Time-Delayed Access:</strong> Content available after {activation_date}</li>")
        
        elif condition_type == 'inactivity_trigger':
            months = condition.get('inactivity_months', 'Not specified')
            html_parts.append(f"<li><strong>Inactivity Trigger:</strong> Content available after {months} months of Legacy Maker inactivity</li>")
        
        elif condition_type == 'manual_release':
            html_parts.append("<li><strong>Manual Release:</strong> Content available when Legacy Maker manually releases it</li>")
    
    html_parts.append("</ul>")
    return "".join(html_parts)