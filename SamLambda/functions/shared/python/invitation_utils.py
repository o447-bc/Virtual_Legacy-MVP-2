"""
Invitation Token Management for Legacy Maker Benefactor Assignment feature.

Provides functions for creating, validating, and processing invitation tokens
when Legacy Makers assign Benefactors who don't have accounts yet.

Requirements: 6.2, 6.4, 6.5, 6.6, 6.7
"""
import uuid
import time
import boto3
from datetime import datetime
from typing import Dict, Tuple, Optional, Any
from botocore.exceptions import ClientError
from datetime import timezone


def create_invitation_token(
    initiator_id: str,
    benefactor_email: str,
    assignment_details: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create an invitation token for an unregistered Benefactor.
    
    Stores the invitation token in PersonaSignupTempDB with a 30-day TTL.
    The token will be used during registration to automatically link the new
    user to the pending assignment.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID who created the assignment
        benefactor_email: Email address of the Benefactor being invited (normalized to lowercase)
        assignment_details: Dictionary containing assignment information:
            - access_conditions: List of access condition dictionaries
            - relationship_type: Type of relationship (default: "maker_to_benefactor")
            - created_via: How assignment was created (default: "maker_assignment")
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, {'invite_token': token_string, 'expiration_time': timestamp})
        - On failure: (False, {'error': error_message})
    
    Requirements: 6.2, 6.6
    """
    try:
        # Generate unique invitation token
        invite_token = str(uuid.uuid4())
        
        # Normalize email to lowercase for consistency
        benefactor_email_lower = benefactor_email.lower().strip()
        
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaSignupTempDB')
        
        # Calculate expiration time (30 days from now as per Requirement 6.6)
        expiration_time = int(time.time()) + (30 * 24 * 60 * 60)  # 30 days in seconds
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Store invitation data using invite_token as the key
        item = {
            'userName': invite_token,  # Primary key (invite token)
            'initiator_id': initiator_id,  # Legacy Maker who created assignment
            'benefactor_email': benefactor_email_lower,  # Who was invited
            'invite_type': 'maker_assignment',  # Type of invite
            'assignment_details': assignment_details,  # Access conditions and other details
            'created_at': current_time,  # When invite was created
            'ttl': expiration_time  # Auto-delete after 30 days
        }
        
        table.put_item(Item=item)
        
        return True, {
            'invite_token': invite_token,
            'expiration_time': expiration_time,
            'created_at': current_time
        }
        
    except ClientError as e:
        error_msg = f"Failed to create invitation token: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error creating invitation token: {str(e)}"}


def validate_invitation_token(
    invite_token: str,
    benefactor_email: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate an invitation token and retrieve associated data.
    
    Checks if the token exists in PersonaSignupTempDB and optionally verifies
    that the email matches the invited email (security check).
    
    Args:
        invite_token: The invitation token UUID to validate
        benefactor_email: (Optional) Email to verify against the invitation.
                         If provided, must match the invited email (case-insensitive)
    
    Returns:
        Tuple of (valid: bool, data: dict or None)
        - If valid: (True, invitation_data_dict) containing:
            - initiator_id: Legacy Maker who created the assignment
            - benefactor_email: Email of invited Benefactor
            - assignment_details: Access conditions and assignment info
            - created_at: When invitation was created
            - ttl: Expiration timestamp
        - If invalid/not found: (False, None)
        - If email mismatch: (False, {'error': 'email_mismatch'})
        - On error: (False, {'error': error_message})
    
    Requirements: 6.4, 6.5
    """
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaSignupTempDB')
        
        # Retrieve invitation data
        response = table.get_item(Key={'userName': invite_token})
        
        if 'Item' not in response:
            # Token not found or expired (TTL removed it)
            return False, None
        
        invite_data = response['Item']
        
        # Verify this is a maker_assignment invite (not other invite types)
        if invite_data.get('invite_type') != 'maker_assignment':
            return False, {'error': 'invalid_invite_type'}
        
        # If email provided, verify it matches (security check)
        if benefactor_email:
            benefactor_email_lower = benefactor_email.lower().strip()
            invite_email = invite_data.get('benefactor_email', '').lower()
            
            if benefactor_email_lower != invite_email:
                return False, {'error': 'email_mismatch'}
        
        # Check if token has expired (manual check in case TTL hasn't processed yet)
        current_time = int(time.time())
        ttl = invite_data.get('ttl', 0)
        
        if current_time > ttl:
            # Token has expired, clean it up
            table.delete_item(Key={'userName': invite_token})
            return False, {'error': 'token_expired'}
        
        return True, invite_data
        
    except ClientError as e:
        error_msg = f"Failed to validate invitation token: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error validating invitation token: {str(e)}"}


def link_registration_to_assignment(
    invite_token: str,
    new_user_id: str,
    user_email: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Link a new user registration to a pending assignment via invitation token.
    
    This function is called during the registration process (typically from
    postConfirmation trigger) to:
    1. Validate the invitation token
    2. Verify the email matches
    3. Create the relationship record in PersonaRelationshipsDB
    4. Create access condition records in AccessConditionsDB
    5. Clean up the invitation token
    
    Args:
        invite_token: The invitation token used during registration
        new_user_id: Cognito user ID of the newly registered Benefactor
        user_email: Email address of the newly registered user (for verification)
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, {
            'relationship_created': True,
            'initiator_id': legacy_maker_id,
            'related_user_id': new_user_id,
            'access_conditions_created': count
          })
        - On failure: (False, {'error': error_message})
    
    Requirements: 6.4, 6.5, 6.7
    """
    try:
        # Step 1: Validate invitation token and verify email
        valid, invite_data = validate_invitation_token(invite_token, user_email)
        
        if not valid:
            if invite_data and 'error' in invite_data:
                return False, invite_data
            return False, {'error': 'invalid_or_expired_token'}
        
        # Extract assignment details
        initiator_id = invite_data.get('initiator_id')
        assignment_details = invite_data.get('assignment_details', {})
        access_conditions = assignment_details.get('access_conditions', [])
        relationship_type = assignment_details.get('relationship_type', 'maker_to_benefactor')
        created_via = assignment_details.get('created_via', 'maker_assignment')
        
        # Step 2: Create relationship record in PersonaRelationshipsDB
        dynamodb = boto3.resource('dynamodb')
        relationships_table = dynamodb.Table('PersonaRelationshipsDB')
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        relationship_item = {
            'initiator_id': initiator_id,  # Legacy Maker
            'related_user_id': new_user_id,  # New Benefactor
            'relationship_type': relationship_type,
            'status': 'pending',  # Awaiting Benefactor acceptance
            'created_at': current_time,
            'updated_at': current_time,
            'created_via': created_via
        }
        
        relationships_table.put_item(Item=relationship_item)
        
        # Step 3: Create access condition records in AccessConditionsDB
        access_conditions_table = dynamodb.Table('AccessConditionsDB')
        relationship_key = f"{initiator_id}#{new_user_id}"
        conditions_created = 0
        
        for condition in access_conditions:
            condition_type = condition.get('condition_type')
            condition_id = str(uuid.uuid4())
            
            # Base condition record
            condition_item = {
                'relationship_key': relationship_key,
                'condition_id': condition_id,
                'condition_type': condition_type,
                'status': 'pending',
                'created_at': current_time
            }
            
            # Add type-specific fields
            if condition_type == 'time_delayed':
                condition_item['activation_date'] = condition.get('activation_date')
            
            elif condition_type == 'inactivity_trigger':
                condition_item['inactivity_months'] = condition.get('inactivity_months')
                condition_item['check_in_interval_days'] = condition.get('check_in_interval_days', 30)
                condition_item['consecutive_missed_check_ins'] = 0
                condition_item['last_check_in'] = current_time
            
            # Store condition
            access_conditions_table.put_item(Item=condition_item)
            conditions_created += 1
        
        # Step 4: Clean up invitation token
        temp_table = dynamodb.Table('PersonaSignupTempDB')
        temp_table.delete_item(Key={'userName': invite_token})
        
        return True, {
            'relationship_created': True,
            'initiator_id': initiator_id,
            'related_user_id': new_user_id,
            'access_conditions_created': conditions_created,
            'status': 'pending'
        }
        
    except ClientError as e:
        error_msg = f"Failed to link registration to assignment: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error linking registration: {str(e)}"}
