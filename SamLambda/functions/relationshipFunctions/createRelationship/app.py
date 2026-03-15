import os
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """Create a new persona relationship"""
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract parameters
        initiator_id = body.get('initiator_id')
        related_user_id = body.get('related_user_id')
        relationship_type = body.get('relationship_type')
        access_expiry = body.get('access_expiry')
        
        if not all([initiator_id, related_user_id, relationship_type]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Create relationship
        result = create_relationship(initiator_id, related_user_id, relationship_type, access_expiry)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')},
            'body': json.dumps({'error': str(e)})
        }

def create_relationship(initiator_id, related_user_id, relationship_type, access_expiry=None):
    """Create relationship in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PersonaRelationshipsDB')
    
    item = {
        'initiator_id': initiator_id,
        'related_user_id': related_user_id,
        'relationship_type': relationship_type,
        'status': 'active',
        'created_at': datetime.now().isoformat()
    }
    
    if access_expiry:
        item['access_expiry'] = access_expiry
    
    table.put_item(Item=item)
    
    return {'message': 'Relationship created successfully', 'relationship': item}