import json
import os
import time
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('WebSocketConnectionsDB')

def lambda_handler(event, context):
    print(f"[CONNECT] Event: {json.dumps(event)}")
    
    connection_id = event['requestContext']['connectionId']
    user_id = event['requestContext']['authorizer']['userId']
    
    print(f"[CONNECT] Connection ID: {connection_id}")
    print(f"[CONNECT] User ID: {user_id}")
    
    ttl = int(time.time()) + 7200  # 2 hours
    
    item = {
        'connectionId': connection_id,
        'userId': user_id,
        'connectedAt': int(time.time()),
        'ttl': ttl
    }
    
    print(f"[CONNECT] Storing connection in DynamoDB: {json.dumps(item)}")
    table.put_item(Item=item)
    print("[CONNECT] Connection stored successfully")
    
    return {'statusCode': 200, 'body': 'Connected'}
