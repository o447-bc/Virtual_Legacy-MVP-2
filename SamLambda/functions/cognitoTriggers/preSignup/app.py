import json
import boto3
import os
import time

def lambda_handler(event, context):
    """
    Cognito Pre-signup trigger to set custom:persona_type based on user choice
    """
    print(f"Pre-signup event: {json.dumps(event)}")
    
    # Get client metadata from signup form
    client_metadata = event.get('request', {}).get('clientMetadata', {})
    print(f"Client metadata: {client_metadata}")
    
    # Get persona choice from frontend
    persona_choice = client_metadata.get('persona_choice', '')
    print(f"Persona choice: {persona_choice}")
    
    # Map frontend choice to persona_type
    if persona_choice == 'create_legacy':
        persona_type = 'legacy_maker'
    elif persona_choice == 'create_legacy_invited':
        persona_type = 'legacy_maker'
    elif persona_choice == 'setup_for_someone':
        persona_type = 'legacy_benefactor'
    elif persona_choice == 'benefactor_invited':
        persona_type = 'legacy_benefactor'
    else:
        # Check if persona_type was passed directly (fallback)
        direct_type = client_metadata.get('persona_type', '')
        if direct_type in ('legacy_benefactor', 'legacy_maker'):
            persona_type = direct_type
        else:
            # Default to legacy_maker if no choice provided
            persona_type = 'legacy_maker'
    
    print(f"Mapped persona_type: {persona_type}")
    
    # Store persona data in DynamoDB for PostConfirmation to read
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB'))
        
        username = event.get('userName', '')
        ttl = int(time.time()) + 3600  # Expire in 1 hour
        
        # Prepare item data
        item_data = {
            'userName': username,
            'persona_type': persona_type,
            'persona_choice': persona_choice,
            'ttl': ttl
        }
        
        # Add first and last name if provided
        first_name = client_metadata.get('first_name')
        last_name = client_metadata.get('last_name')
        if first_name:
            item_data['first_name'] = first_name
        if last_name:
            item_data['last_name'] = last_name
        
        # Add invite token if provided
        invite_token = client_metadata.get('invite_token')
        if invite_token:
            item_data['invite_token'] = invite_token
            print(f"Storing invite token for user: {username}")
        
        table.put_item(Item=item_data)
        print(f"Stored persona data for user: {username}")
    except Exception as e:
        print(f"Error storing persona data: {str(e)}")
        # Don't fail signup if DynamoDB write fails
    
    # If user is signing up via an invitation, auto-confirm and auto-verify their email.
    # Their email was already validated when the legacy maker sent the invite to that address.
    invite_token = client_metadata.get('invite_token')
    if invite_token:
        print(f"Invite token present — auto-confirming and auto-verifying email for: {username}")
        event['response']['autoConfirmUser'] = True
        event['response']['autoVerifyEmail'] = True

    print(f"Final event: {json.dumps(event)}")
    return event