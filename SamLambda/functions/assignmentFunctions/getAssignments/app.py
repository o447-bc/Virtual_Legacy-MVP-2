"""
GetAssignments Lambda Function

Retrieves all benefactor assignments for a Legacy Maker, including assignment
status, access conditions, and benefactor account information.

Requirements: 5.1, 5.2, 5.3, 5.4
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


def lambda_handler(event, context):
    """
    Get all assignments for a Legacy Maker.
    
    Query Parameters:
    - userId: Legacy Maker user ID (optional, extracted from JWT if not provided)
    
    Response:
    {
        "assignments": [
            {
                "initiator_id": "string",
                "related_user_id": "string",
                "benefactor_email": "string",
                "benefactor_first_name": "string",
                "benefactor_last_name": "string",
                "account_status": "registered" | "invitation_pending",
                "assignment_status": "pending" | "active" | "declined" | "revoked",
                "access_conditions": [...],
                "created_at": "string"
            }
        ]
    }
    """
    
    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': ''
        }
    
    try:
        # Extract Legacy Maker ID from JWT token
        legacy_maker_id = extract_user_id_from_jwt(event)
        if not legacy_maker_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Unable to identify user from token'})
            }
        
        # Check if querying as beneficiary
        query_params = event.get('queryStringParameters') or {}
        as_beneficiary = query_params.get('asBeneficiary', '').lower() == 'true'
        
        if as_beneficiary:
            # Query assignments where user is the benefactor
            assignments = get_assignments_as_beneficiary(legacy_maker_id)
        else:
            # Allow override from query parameter (for admin purposes or testing)
            user_id = query_params.get('userId', legacy_maker_id)
            # Query PersonaRelationshipsDB for all assignments where initiator_id = userId
            assignments = get_assignments_for_user(user_id)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'assignments': assignments,
                'count': len(assignments)
            })
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
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


def get_assignments_for_user(user_id):
    """
    Get all assignments for a Legacy Maker.
    
    Queries PersonaRelationshipsDB for relationships where initiator_id = user_id,
    then enriches each assignment with access conditions and benefactor details.
    
    Args:
        user_id: Legacy Maker's Cognito user ID
        
    Returns:
        list: List of assignment dictionaries with full details
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        relationships_table = dynamodb.Table('PersonaRelationshipsDB')
        
        # Query for all relationships where this user is the initiator
        response = relationships_table.query(
            KeyConditionExpression='initiator_id = :uid',
            ExpressionAttributeValues={
                ':uid': user_id
            }
        )
        
        relationships = response.get('Items', [])
        
        # Filter for maker-to-benefactor assignments only
        assignments = []
        for relationship in relationships:
            # Only include maker_assignment relationships
            if relationship.get('created_via') == 'maker_assignment':
                assignment = enrich_assignment(relationship)
                assignments.append(assignment)
        
        return assignments
        
    except ClientError as e:
        print(f"Error querying relationships: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"Unexpected error getting assignments: {str(e)}")
        return []


def get_assignments_as_beneficiary(user_id):
    """
    Get all assignments where the user is the benefactor.
    
    Queries PersonaRelationshipsDB using RelatedUserIndex GSI where related_user_id = user_id,
    then enriches each assignment with access conditions and Legacy Maker details.
    
    Args:
        user_id: Benefactor's Cognito user ID
        
    Returns:
        list: List of assignment dictionaries with full details (from Legacy Maker perspective)
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        relationships_table = dynamodb.Table('PersonaRelationshipsDB')
        
        # Query using RelatedUserIndex GSI for all relationships where this user is the benefactor
        response = relationships_table.query(
            IndexName='RelatedUserIndex',
            KeyConditionExpression='related_user_id = :uid',
            ExpressionAttributeValues={
                ':uid': user_id
            }
        )
        
        relationships = response.get('Items', [])
        
        # Filter for maker-to-benefactor assignments only
        assignments = []
        for relationship in relationships:
            # Only include maker_assignment relationships
            if relationship.get('created_via') == 'maker_assignment':
                assignment = enrich_beneficiary_assignment(relationship, user_id)
                assignments.append(assignment)
        
        return assignments
        
    except ClientError as e:
        print(f"Error querying relationships as beneficiary: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"Unexpected error getting assignments as beneficiary: {str(e)}")
        return []


def enrich_beneficiary_assignment(relationship, beneficiary_id):
    """
    Enrich a relationship record with access conditions and Legacy Maker details.
    This is for the beneficiary view where we show Legacy Maker information.
    
    Args:
        relationship: Relationship record from PersonaRelationshipsDB
        beneficiary_id: The benefactor's user ID
        
    Returns:
        dict: Enriched assignment with Legacy Maker details
    """
    initiator_id = relationship.get('initiator_id')  # This is the Legacy Maker
    related_user_id = relationship.get('related_user_id')  # This is the Benefactor
    
    # Base assignment structure
    assignment = {
        'initiator_id': initiator_id,
        'related_user_id': related_user_id,
        'assignment_status': relationship.get('status', 'unknown'),
        'relationship_type': relationship.get('relationship_type'),
        'created_at': relationship.get('created_at'),
        'updated_at': relationship.get('updated_at')
    }
    
    # Get Legacy Maker details from Cognito
    maker_data = get_benefactor_details(initiator_id)  # Reusing function, works for any user
    assignment['maker_email'] = maker_data.get('email', 'Unknown')
    assignment['maker_first_name'] = maker_data.get('first_name')
    assignment['maker_last_name'] = maker_data.get('last_name')
    
    # Get access conditions
    access_conditions = get_access_conditions(initiator_id, related_user_id)
    assignment['access_conditions'] = access_conditions
    
    return assignment


def enrich_assignment(relationship):
    """
    Enrich a relationship record with access conditions and benefactor details.
    
    Args:
        relationship: Relationship record from PersonaRelationshipsDB
        
    Returns:
        dict: Enriched assignment with all details
    """
    initiator_id = relationship.get('initiator_id')
    related_user_id = relationship.get('related_user_id')
    
    # Base assignment structure
    assignment = {
        'initiator_id': initiator_id,
        'related_user_id': related_user_id,
        'assignment_status': relationship.get('status', 'unknown'),
        'relationship_type': relationship.get('relationship_type'),
        'created_at': relationship.get('created_at'),
        'updated_at': relationship.get('updated_at')
    }
    
    # Determine account status and get benefactor details
    if related_user_id.startswith('pending#'):
        # Unregistered benefactor - extract email from ID
        benefactor_email = related_user_id.replace('pending#', '')
        assignment['account_status'] = 'invitation_pending'
        assignment['benefactor_email'] = benefactor_email
        assignment['benefactor_first_name'] = None
        assignment['benefactor_last_name'] = None
    else:
        # Registered benefactor - lookup in Cognito
        assignment['account_status'] = 'registered'
        benefactor_data = get_benefactor_details(related_user_id)
        assignment['benefactor_email'] = benefactor_data.get('email', 'Unknown')
        assignment['benefactor_first_name'] = benefactor_data.get('first_name')
        assignment['benefactor_last_name'] = benefactor_data.get('last_name')
    
    # Get access conditions
    access_conditions = get_access_conditions(initiator_id, related_user_id)
    assignment['access_conditions'] = access_conditions
    
    return assignment


def get_benefactor_details(user_id):
    """
    Get benefactor details from Cognito.
    
    Args:
        user_id: Cognito user ID
        
    Returns:
        dict: User details (email, first_name, last_name)
    """
    try:
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        if not user_pool_id:
            print("USER_POOL_ID environment variable not set")
            return {'email': 'Unknown'}
        
        # Get user details from Cognito
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )
        
        # Extract attributes
        user_data = {'email': 'Unknown'}
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                user_data['email'] = attr['Value']
            elif attr['Name'] == 'given_name':
                user_data['first_name'] = attr['Value']
            elif attr['Name'] == 'family_name':
                user_data['last_name'] = attr['Value']
        
        return user_data
        
    except ClientError as e:
        print(f"Error getting user from Cognito: {e.response['Error']['Message']}")
        return {'email': 'Unknown'}
    except Exception as e:
        print(f"Unexpected error getting benefactor details: {str(e)}")
        return {'email': 'Unknown'}


def get_access_conditions(initiator_id, related_user_id):
    """
    Get access conditions for an assignment from AccessConditionsDB.
    
    Args:
        initiator_id: Legacy Maker's user ID
        related_user_id: Benefactor's user ID
        
    Returns:
        list: List of access condition dictionaries
    """
    try:
        dynamodb = boto3.resource('dynamodb')
        conditions_table = dynamodb.Table('AccessConditionsDB')
        
        # Create composite relationship key
        relationship_key = f"{initiator_id}#{related_user_id}"
        
        # Query for all conditions for this relationship
        response = conditions_table.query(
            KeyConditionExpression='relationship_key = :rkey',
            ExpressionAttributeValues={
                ':rkey': relationship_key
            }
        )
        
        conditions = response.get('Items', [])
        
        # Format conditions for response
        formatted_conditions = []
        for condition in conditions:
            formatted_condition = {
                'condition_id': condition.get('condition_id'),
                'condition_type': condition.get('condition_type'),
                'status': condition.get('status')
            }
            
            # Add type-specific fields
            if condition.get('condition_type') == 'time_delayed':
                formatted_condition['activation_date'] = condition.get('activation_date')
            
            elif condition.get('condition_type') == 'inactivity_trigger':
                formatted_condition['inactivity_months'] = condition.get('inactivity_months')
                formatted_condition['check_in_interval_days'] = condition.get('check_in_interval_days')
                formatted_condition['last_check_in'] = condition.get('last_check_in')
                formatted_condition['consecutive_missed_check_ins'] = condition.get('consecutive_missed_check_ins', 0)
            
            elif condition.get('condition_type') == 'manual_release':
                formatted_condition['released_at'] = condition.get('released_at')
                formatted_condition['released_by'] = condition.get('released_by')
            
            formatted_conditions.append(formatted_condition)
        
        return formatted_conditions
        
    except ClientError as e:
        print(f"Error querying access conditions: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"Unexpected error getting access conditions: {str(e)}")
        return []
