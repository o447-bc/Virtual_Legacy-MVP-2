import os
import json
import boto3
import uuid
import time

from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from cors import cors_headers
from responses import error_response


def lambda_handler(event, context):
    """Send invitation email via SES"""
    
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
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract parameters and normalize to lowercase
        benefactor_email = body.get('benefactor_email', '').lower()
        invitee_email = body.get('invitee_email', '').lower()
        
        if not all([benefactor_email, invitee_email]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Extract benefactor_id from Cognito authorizer claims
        benefactor_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
        if not benefactor_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Unable to identify benefactor from token'})
            }
        
        # Generate invite token
        invite_token = str(uuid.uuid4())
        
        # Store invite data (non-blocking - continue if this fails)
        try:
            store_invite_token(invite_token, benefactor_id, invitee_email)
        except Exception as store_error:
            print(f"Warning: Failed to store invite token: {str(store_error)}")
        
        # Send email (this is the critical operation)
        try:
            result = send_invite_email(benefactor_email, invitee_email, invite_token)
        except Exception as email_error:
            print(f"SES Error Details: {str(email_error)}")
            raise Exception(f"Email sending failed: {str(email_error)}")
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({
                'message': 'Invitation sent successfully',
                'invite_token': invite_token,
                'sent_to': invitee_email
            })
        }
        
    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'A server error occurred. Please try again.'})
        }

def send_invite_email(benefactor_email, invitee_email, invite_token):
    """Send invitation email using SES"""
    
    ses_client = boto3.client('ses', region_name='us-east-1')
    
    # Professional no-reply sender - production domain
    sender = 'Virtual Legacy <noreply@soulreel.net>'
    
    # Email content
    subject = "You're invited to create your Virtual Legacy"
    
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
                <h2>You're invited to preserve your legacy</h2>
                <p>Someone who cares about you has invited you to create your Virtual Legacy account.</p>
                <p>Virtual Legacy helps you record your memories, stories, and wisdom to share with future generations.</p>
                <p>Click the button below to get started:</p>
                <a href="https://soulreel.net/signup-create-legacy?invite={invite_token}" class="button">Create Your Legacy</a>
                <p><strong>What you'll be able to do:</strong></p>
                <ul>
                    <li>Record video responses to thoughtful questions</li>
                    <li>Share your life experiences and wisdom</li>
                    <li>Create a lasting digital legacy for your loved ones</li>
                </ul>
                <p>This invitation will expire in 7 days.</p>
            </div>
            <div class="footer">
                <p>This invitation was sent by {benefactor_email}</p>
                <p>Virtual Legacy - Preserving memories for future generations</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    You're invited to create your Virtual Legacy!
    
    Someone who cares about you has invited you to create your Virtual Legacy account.
    
    Virtual Legacy helps you record your memories, stories, and wisdom to share with future generations.
    
    Visit this link to get started: https://soulreel.net/signup-create-legacy?invite={invite_token}
    
    What you'll be able to do:
    - Record video responses to thoughtful questions
    - Share your life experiences and wisdom  
    - Create a lasting digital legacy for your loved ones
    
    This invitation will expire in 7 days.
    
    This invitation was sent by {benefactor_email}
    Virtual Legacy - Preserving memories for future generations
    """
    
    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [invitee_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        
        print(f"Email sent successfully. MessageId: {response['MessageId']}")
        return response
        
    except ClientError as e:
        print(f"SES Error: {e.response['Error']['Message']}")
        raise e

def store_invite_token(invite_token, benefactor_id, invitee_email):
    """
    Store invite token data in PersonaSignupTempDB for processing during signup.
    
    Args:
        invite_token: Unique invite token (UUID)
        benefactor_id: Cognito user ID of the benefactor who sent the invite
        invitee_email: Email address of the person being invited
    """
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB'))
        
        # Calculate expiration time (7 days from now)
        expiration_time = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days in seconds
        
        # Store invite data using invite_token as the key
        table.put_item(
            Item={
                'userName': invite_token,  # Using invite_token as primary key
                'benefactor_id': benefactor_id,  # Who sent the invite
                'invitee_email': invitee_email,  # Who was invited
                'invite_type': 'legacy_maker_invite',  # Type of invite
                'created_at': datetime.now().isoformat(),  # When invite was created
                'ttl': expiration_time  # Auto-delete after 7 days
            }
        )
        
        print(f"Stored invite token {invite_token} for benefactor {benefactor_id} -> {invitee_email}")
        
    except Exception as e:
        print(f"Error storing invite token: {str(e)}")
        # Don't fail the entire invite process if storage fails
        # The email will still be sent, but relationship won't be auto-created
        raise e