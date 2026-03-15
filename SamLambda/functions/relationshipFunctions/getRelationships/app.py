import json
import os
import boto3
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor

def lambda_handler(event, context):
    """Get relationships for a user"""

    try:
        user_id = event.get('queryStringParameters', {}).get('userId')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
                'body': json.dumps({'error': 'Missing userId parameter'})
            }

        relationships = get_user_relationships(user_id)

        # Enrich with Cognito user attributes in parallel
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')

        def enrich(rel):
            related_id = rel.get('related_user_id', '')
            # Skip pending (uninvited) users — they have no Cognito account yet
            if related_id.startswith('pending#'):
                return rel
            try:
                response = cognito.admin_get_user(
                    UserPoolId=user_pool_id,
                    Username=related_id
                )
                for attr in response.get('UserAttributes', []):
                    if attr['Name'] == 'email':
                        rel['related_user_email'] = attr['Value']
                    elif attr['Name'] == 'given_name':
                        rel['related_user_first_name'] = attr['Value']
                    elif attr['Name'] == 'family_name':
                        rel['related_user_last_name'] = attr['Value']
            except ClientError:
                pass  # User not found or throttled — return rel as-is
            return rel

        if relationships:
            with ThreadPoolExecutor(max_workers=min(10, len(relationships))) as executor:
                relationships = list(executor.map(enrich, relationships))

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'relationships': relationships})
        }

    except Exception as e:
        print(f"[ERROR] getRelationships: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
            'body': json.dumps({'error': 'Failed to retrieve relationships. Please try again.'})
        }


def _query_all_pages(table, **kwargs):
    """Query DynamoDB handling pagination automatically."""
    items = []
    while True:
        response = table.query(**kwargs)
        items.extend(response.get('Items', []))
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        kwargs['ExclusiveStartKey'] = last_key
    return items


def get_user_relationships(user_id):
    """Get all relationships for a user (as initiator or related user), with pagination."""

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PersonaRelationshipsDB')

    relationships = []

    # Query as initiator (paginated)
    try:
        relationships.extend(_query_all_pages(
            table,
            KeyConditionExpression='initiator_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        ))
    except ClientError as e:
        print(f"[ERROR] getRelationships initiator query: {e}")

    # Query as related user via GSI (paginated)
    try:
        relationships.extend(_query_all_pages(
            table,
            IndexName='RelatedUserIndex',
            KeyConditionExpression='related_user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        ))
    except ClientError as e:
        print(f"[ERROR] getRelationships related_user query: {e}")

    return relationships
