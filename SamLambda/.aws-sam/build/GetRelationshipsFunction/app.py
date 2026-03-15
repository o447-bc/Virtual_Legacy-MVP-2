import json
import boto3
import os
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """Get relationships for a user"""
    
    try:
        # Extract user ID from query parameters
        user_id = event.get('queryStringParameters', {}).get('userId')
        
        if not user_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing userId parameter'})
            }
        
        # Get relationships
        relationships = get_user_relationships(user_id)
        
        # Enrich with user emails
        cognito = boto3.client('cognito-idp')
        user_pool_id = os.environ.get('USER_POOL_ID')
        
        for rel in relationships:
            try:
                response = cognito.admin_get_user(
                    UserPoolId=user_pool_id,
                    Username=rel['related_user_id']
                )
                for attr in response.get('UserAttributes', []):
                    if attr['Name'] == 'email':
                        rel['related_user_email'] = attr['Value']
                    elif attr['Name'] == 'given_name':
                        rel['related_user_first_name'] = attr['Value']
                    elif attr['Name'] == 'family_name':
                        rel['related_user_last_name'] = attr['Value']
            except ClientError:
                pass
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'relationships': relationships})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def get_user_relationships(user_id):
    """Get all relationships for a user (as initiator or related user)"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PersonaRelationshipsDB')
    
    relationships = []
    
    # Query as initiator
    try:
        response = table.query(
            KeyConditionExpression='initiator_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        relationships.extend(response['Items'])
    except ClientError:
        pass
    
    # Query as related user using GSI
    try:
        response = table.query(
            IndexName='RelatedUserIndex',
            KeyConditionExpression='related_user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        relationships.extend(response['Items'])
    except ClientError:
        pass
    
    return relationships