import os
import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

CORS_HEADERS = {
    'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,OPTIONS'
}

def lambda_handler(event, context):
    """Validate if a user has access to another user's content"""

    # Handle CORS preflight OPTIONS request FIRST
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    try:
        # Extract parameters
        params = event.get('queryStringParameters') or {}
        requesting_user_id = params.get('requestingUserId')
        target_user_id = params.get('targetUserId')

        if not all([requesting_user_id, target_user_id]):
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Missing required parameters'})
            }

        # Validate access
        access_result = validate_user_access(requesting_user_id, target_user_id)

        print(f"Access validation: requesting={requesting_user_id} target={target_user_id} "
              f"hasAccess={access_result.get('hasAccess')} reason={access_result.get('reason')}")

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(access_result)
        }

    except Exception as e:
        print(f"Error in validateAccess: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }


def validate_user_access(requesting_user_id, target_user_id):
    """Check if requesting user has access to target user's content"""

    # Self-access is always allowed
    if requesting_user_id == target_user_id:
        return {'hasAccess': True, 'reason': 'self_access'}

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PersonaRelationshipsDB')

    try:
        # Check if there's an active relationship
        response = table.query(
            KeyConditionExpression='initiator_id = :init_id AND related_user_id = :rel_id',
            ExpressionAttributeValues={
                ':init_id': requesting_user_id,
                ':rel_id': target_user_id
            }
        )

        for item in response['Items']:
            if item.get('status') == 'active':
                # Check expiry if set (legacy field)
                if 'access_expiry' in item:
                    expiry = datetime.fromisoformat(item['access_expiry'].replace('Z', '+00:00'))
                    if datetime.now(expiry.tzinfo) > expiry:
                        return {'hasAccess': False, 'reason': 'expired'}

                # Check access conditions for maker-initiated assignments
                conditions_result = check_access_conditions(requesting_user_id, target_user_id)
                if conditions_result:
                    return conditions_result

                return {'hasAccess': True, 'reason': 'relationship_access'}

        # Check reverse relationship using GSI
        response = table.query(
            IndexName='RelatedUserIndex',
            KeyConditionExpression='related_user_id = :rel_id',
            FilterExpression='initiator_id = :init_id',
            ExpressionAttributeValues={
                ':init_id': target_user_id,
                ':rel_id': requesting_user_id
            }
        )

        for item in response['Items']:
            if item.get('status') == 'active':
                # Check access conditions for reverse relationships
                conditions_result = check_access_conditions(target_user_id, requesting_user_id)
                if conditions_result:
                    return conditions_result

                return {'hasAccess': True, 'reason': 'reverse_relationship_access'}

        return {'hasAccess': False, 'reason': 'no_relationship'}

    except ClientError as e:
        return {'hasAccess': False, 'reason': 'database_error', 'error': str(e)}


def get_access_conditions(initiator_id, related_user_id):
    """Query AccessConditionsDB for all access conditions for a relationship."""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('AccessConditionsDB')
        relationship_key = f"{initiator_id}#{related_user_id}"
        response = table.query(
            KeyConditionExpression='relationship_key = :rkey',
            ExpressionAttributeValues={':rkey': relationship_key}
        )
        return response.get('Items', [])
    except Exception:
        return []


def evaluate_access_conditions(conditions):
    """Evaluate all access conditions to determine if access should be granted."""
    if not conditions:
        return True, []

    unmet_conditions = []
    current_time = datetime.now(timezone.utc)

    for condition in conditions:
        condition_type = condition.get('condition_type')
        condition_status = condition.get('status', 'pending')

        if condition_type == 'immediate':
            continue

        elif condition_type == 'time_delayed':
            activation_date_str = condition.get('activation_date')
            if not activation_date_str:
                unmet_conditions.append({'condition_type': 'time_delayed', 'reason': 'Missing activation date'})
                continue
            try:
                activation_date = datetime.fromisoformat(activation_date_str.replace('Z', '+00:00'))
                if current_time < activation_date:
                    unmet_conditions.append({
                        'condition_type': 'time_delayed',
                        'reason': 'Access will be granted after the specified date',
                        'activation_date': activation_date_str
                    })
            except (ValueError, AttributeError):
                unmet_conditions.append({'condition_type': 'time_delayed', 'reason': 'Invalid activation date format'})

        elif condition_type == 'inactivity_trigger':
            if condition_status != 'activated':
                unmet_conditions.append({
                    'condition_type': 'inactivity_trigger',
                    'reason': 'Waiting for inactivity trigger to activate',
                    'inactivity_months': condition.get('inactivity_months')
                })

        elif condition_type == 'manual_release':
            if not condition.get('released_at'):
                unmet_conditions.append({
                    'condition_type': 'manual_release',
                    'reason': 'Waiting for manual release by Legacy Maker'
                })

    return len(unmet_conditions) == 0, unmet_conditions


def check_access_conditions(initiator_id, related_user_id):
    """Check access conditions and return denial dict or None if satisfied."""
    conditions = get_access_conditions(initiator_id, related_user_id)
    if not conditions:
        return None
    all_satisfied, unmet_conditions = evaluate_access_conditions(conditions)
    if all_satisfied:
        return None
    return {
        'hasAccess': False,
        'reason': 'conditions_not_met',
        'unmet_conditions': unmet_conditions
    }
