"""GET /streak - Fast read-only endpoint for current streak data.

PURPOSE:
- Provides quick access to user's current streak count and freeze status
- Optimized for speed with no calculations or business logic
- Used by frontend for initial streak display on Dashboard

RESPONSE:
- streakCount: Current consecutive day streak
- streakFreezeAvailable: Whether monthly freeze is available
- lastVideoDate: Date of last video upload (ISO format)

AUTHENTICATION:
- Requires valid Cognito JWT token
- User ID extracted from token 'sub' claim
"""
import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Handle GET /streak requests for current streak data."""
    
    logger.info(f"Event: {json.dumps(event)}")
    
    # Handle CORS preflight requests
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
    
    # Extract user ID from Cognito JWT token
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    logger.info(f"Extracted user_id: {user_id}")
    
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        # Fetch streak data from EngagementDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('EngagementDB')
        
        logger.info(f"Querying EngagementDB for user_id: {user_id}")
        response = table.get_item(Key={'userId': user_id})
        
        # New user with no streak record - return defaults
        if 'Item' not in response:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'streakCount': 0,
                    'streakFreezeAvailable': True
                })
            }
        
        # Return current streak data
        item = response['Item']
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'streakCount': int(item.get('streakCount', 0)),
                'streakFreezeAvailable': item.get('streakFreezeAvailable', True),
                'lastVideoDate': item.get('lastVideoDate')
            })
        }
        
    except Exception as e:
        logger.error(f"Error in getStreak: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
