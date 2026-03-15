"""
Assignment Data Access Layer for Legacy Maker Benefactor Assignment feature.

Provides data access functions for creating and managing benefactor assignments,
including relationship records, access conditions, and Cognito user lookups.

Requirements: 1.1, 1.5, 6.1, 9.1, 9.5, 10.1, 10.2, 10.3
"""
import os
import uuid
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from botocore.exceptions import ClientError
from datetime import timezone


def create_assignment_record(
    initiator_id: str,
    related_user_id: str,
    relationship_type: str = "maker_to_benefactor",
    created_via: str = "maker_assignment"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create a new assignment record in PersonaRelationshipsDB.
    
    This function creates a relationship record where the Legacy Maker is the initiator
    and the Benefactor is the related user. The relationship starts with status "pending"
    until the Benefactor accepts it.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID (or temporary ID for unregistered)
        relationship_type: Type of relationship (default: "maker_to_benefactor")
        created_via: How the relationship was created (default: "maker_assignment")
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, relationship_record)
        - On failure: (False, {'error': error_message})
    
    Requirements: 1.1, 9.1, 10.1
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaRelationshipsDB')
        
        # Create relationship record with pending status
        current_time = datetime.now(timezone.utc).isoformat()
        
        item = {
            'initiator_id': initiator_id,
            'related_user_id': related_user_id,
            'relationship_type': relationship_type,
            'status': 'pending',
            'created_at': current_time,
            'updated_at': current_time,
            'created_via': created_via
        }
        
        # Use put_item to create the record
        table.put_item(Item=item)
        
        return True, item
        
    except ClientError as e:
        error_msg = f"Failed to create assignment record: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error creating assignment record: {str(e)}"}


def create_access_conditions(
    initiator_id: str,
    related_user_id: str,
    access_conditions: List[Dict[str, Any]]
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Create access condition records in AccessConditionsDB.
    
    Each access condition is stored as a separate record with a unique condition_id.
    The relationship_key is a composite of initiator_id and related_user_id.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID
        access_conditions: List of access condition dictionaries, each containing:
            - condition_type: 'immediate' | 'time_delayed' | 'inactivity_trigger' | 'manual_release'
            - activation_date: (optional) ISO 8601 string for time_delayed
            - inactivity_months: (optional) integer for inactivity_trigger
            - check_in_interval_days: (optional) integer for inactivity_trigger
    
    Returns:
        Tuple of (success: bool, result: list or dict)
        - On success: (True, list_of_created_conditions)
        - On failure: (False, {'error': error_message})
    
    Requirements: 10.2, 10.3
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('AccessConditionsDB')
        
        # Create composite relationship key
        relationship_key = f"{initiator_id}#{related_user_id}"
        current_time = datetime.now(timezone.utc).isoformat()
        
        created_conditions = []
        
        for condition in access_conditions:
            condition_type = condition.get('condition_type')
            
            # Generate unique condition ID
            condition_id = str(uuid.uuid4())
            
            # Base condition record
            item = {
                'relationship_key': relationship_key,
                'condition_id': condition_id,
                'condition_type': condition_type,
                'status': 'pending',
                'created_at': current_time
            }
            
            # Add type-specific fields
            if condition_type == 'time_delayed':
                item['activation_date'] = condition.get('activation_date')
            
            elif condition_type == 'inactivity_trigger':
                item['inactivity_months'] = condition.get('inactivity_months')
                item['check_in_interval_days'] = condition.get('check_in_interval_days', 30)
                item['consecutive_missed_check_ins'] = 0
                # Initialize last_check_in to current time
                item['last_check_in'] = current_time
            
            # manual_release and immediate don't need additional fields
            
            # Store in DynamoDB
            table.put_item(Item=item)
            created_conditions.append(item)
        
        return True, created_conditions
        
    except ClientError as e:
        error_msg = f"Failed to create access conditions: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error creating access conditions: {str(e)}"}


def check_duplicate_assignment(
    initiator_id: str,
    related_user_id: str
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if an assignment already exists between Legacy Maker and Benefactor.
    
    Checks both directions to prevent duplicate assignments:
    1. Maker → Benefactor (maker_assignment)
    2. Benefactor → Maker (benefactor_invite)
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID or email
    
    Returns:
        Tuple of (exists: bool, existing_record: dict or None)
        - If duplicate exists: (True, existing_relationship_record)
        - If no duplicate: (False, None)
        - On error: (False, {'error': error_message})
    
    Requirements: 1.5, 9.5
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaRelationshipsDB')
        
        # Check 1: Maker → Benefactor (current direction)
        try:
            response = table.get_item(
                Key={
                    'initiator_id': initiator_id,
                    'related_user_id': related_user_id
                }
            )
            if 'Item' in response:
                return True, response['Item']
        except ClientError:
            pass
        
        # Check 2: Benefactor → Maker (reverse direction)
        try:
            response = table.get_item(
                Key={
                    'initiator_id': related_user_id,
                    'related_user_id': initiator_id
                }
            )
            if 'Item' in response:
                return True, response['Item']
        except ClientError:
            pass
        
        # No duplicate found
        return False, None
        
    except Exception as e:
        return False, {'error': f"Error checking for duplicate assignment: {str(e)}"}


def get_user_by_email(email: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Look up a Cognito user by email address.
    
    Searches the Cognito User Pool for a user with the specified email.
    Uses pagination to handle large user pools efficiently.
    
    Args:
        email: Email address to search for (case-insensitive)
    
    Returns:
        Tuple of (found: bool, user_data: dict or None)
        - If user found: (True, user_data_dict) containing:
            - user_id: Cognito Username (sub)
            - email: User's email
            - first_name: User's given name (if available)
            - last_name: User's family name (if available)
            - user_status: Cognito user status
        - If user not found: (False, None)
        - On error: (False, {'error': error_message})
    
    Requirements: 6.1
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            return False, {'error': 'USER_POOL_ID environment variable not set'}
        
        # Normalize email to lowercase for comparison
        email_lower = email.lower().strip()
        
        # Use paginator to handle large user pools
        paginator = cognito.get_paginator('list_users')
        
        for page in paginator.paginate(UserPoolId=user_pool_id):
            for user in page.get('Users', []):
                # Check email attribute
                user_email = None
                user_first_name = None
                user_last_name = None
                
                for attr in user.get('Attributes', []):
                    if attr['Name'] == 'email':
                        user_email = attr['Value']
                    elif attr['Name'] == 'given_name':
                        user_first_name = attr['Value']
                    elif attr['Name'] == 'family_name':
                        user_last_name = attr['Value']
                
                # Check if email matches (case-insensitive)
                if user_email and user_email.lower() == email_lower:
                    user_data = {
                        'user_id': user['Username'],  # Cognito Username is the user_id (sub)
                        'email': user_email,
                        'first_name': user_first_name,
                        'last_name': user_last_name,
                        'user_status': user.get('UserStatus', 'UNKNOWN')
                    }
                    return True, user_data
        
        # User not found
        return False, None
        
    except ClientError as e:
        error_msg = f"Failed to lookup user in Cognito: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error looking up user: {str(e)}"}


def get_assignment(
    initiator_id: str,
    related_user_id: str
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Get an assignment record from PersonaRelationshipsDB.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID
    
    Returns:
        Tuple of (success: bool, result: dict or None)
        - On success: (True, relationship_record)
        - If not found: (True, None)
        - On failure: (False, {'error': error_message})
    
    Requirements: 5.3, 5.4, 12.1
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaRelationshipsDB')
        
        response = table.get_item(
            Key={
                'initiator_id': initiator_id,
                'related_user_id': related_user_id
            }
        )
        
        if 'Item' in response:
            return True, response['Item']
        else:
            return True, None
        
    except ClientError as e:
        error_msg = f"Failed to get assignment: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error getting assignment: {str(e)}"}


def update_relationship_status(
    initiator_id: str,
    related_user_id: str,
    new_status: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Update the status of a relationship in PersonaRelationshipsDB.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID
        new_status: New status value ('active', 'revoked', 'declined', etc.)
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, updated_record)
        - On failure: (False, {'error': error_message})
    
    Requirements: 5.5, 5.8
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaRelationshipsDB')
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        response = table.update_item(
            Key={
                'initiator_id': initiator_id,
                'related_user_id': related_user_id
            },
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': new_status,
                ':updated_at': current_time
            },
            ReturnValues='ALL_NEW'
        )
        
        return True, response.get('Attributes', {})
        
    except ClientError as e:
        error_msg = f"Failed to update relationship status: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error updating relationship status: {str(e)}"}


def delete_access_conditions(
    initiator_id: str,
    related_user_id: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Delete all access conditions for a relationship from AccessConditionsDB.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, {'deleted_count': number})
        - On failure: (False, {'error': error_message})
    
    Requirements: 5.7, 5.10
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('AccessConditionsDB')
        
        # Create composite relationship key
        relationship_key = f"{initiator_id}#{related_user_id}"
        
        # Query all conditions for this relationship
        response = table.query(
            KeyConditionExpression=Key('relationship_key').eq(relationship_key)
        )
        
        conditions = response.get('Items', [])
        deleted_count = 0
        print(f"delete_access_conditions: relationship_key={relationship_key}, found {len(conditions)} conditions")
        
        # Delete each condition
        for condition in conditions:
            table.delete_item(
                Key={
                    'relationship_key': relationship_key,
                    'condition_id': condition['condition_id']
                }
            )
            deleted_count += 1
        
        return True, {'deleted_count': deleted_count}
        
    except ClientError as e:
        error_msg = f"Failed to delete access conditions: {e.response['Error']['Message']}"
        print(f"ClientError in delete_access_conditions: {error_msg}")
        return False, {'error': error_msg}
    except Exception as e:
        import traceback
        print(f"Exception in delete_access_conditions: {str(e)}\n{traceback.format_exc()}")
        return False, {'error': f"Unexpected error deleting access conditions: {str(e)}"}


def delete_assignment(
    initiator_id: str,
    related_user_id: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Delete an assignment and all its access conditions.
    
    This function deletes both the relationship record and all associated
    access conditions. Should only be used for pending assignments.
    
    Args:
        initiator_id: Legacy Maker's Cognito user ID
        related_user_id: Benefactor's Cognito user ID
    
    Returns:
        Tuple of (success: bool, result: dict)
        - On success: (True, {'deleted': True})
        - On failure: (False, {'error': error_message})
    
    Requirements: 5.10
    """
    try:
        # First delete access conditions
        success, result = delete_access_conditions(initiator_id, related_user_id)
        if not success:
            return False, result
        
        # Then delete relationship record
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PersonaRelationshipsDB')
        
        table.delete_item(
            Key={
                'initiator_id': initiator_id,
                'related_user_id': related_user_id
            }
        )
        
        return True, {'deleted': True, 'conditions_deleted': result.get('deleted_count', 0)}
        
    except ClientError as e:
        error_msg = f"Failed to delete assignment: {e.response['Error']['Message']}"
        return False, {'error': error_msg}
    except Exception as e:
        return False, {'error': f"Unexpected error deleting assignment: {str(e)}"}
