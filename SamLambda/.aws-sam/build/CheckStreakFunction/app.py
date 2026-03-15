"""GET /streak/check - Enhanced streak endpoint with status calculation.

PURPOSE:
- Provides streak data with calculated status (active/at_risk/broken)
- Includes days since last video for UI display
- Optimized for caching with ETag and Cache-Control headers

STREAK STATUS:
- active: Uploaded today or yesterday (streak intact)
- at_risk: Missed a day but freeze available (can recover)
- broken: Missed a day without freeze (streak lost)

CACHING:
- 1 hour cache duration (Cache-Control: max-age=3600)
- ETag based on lastVideoDate for conditional requests
- Reduces API calls while maintaining accuracy

AUTHENTICATION:
- Requires valid Cognito JWT token
- User ID extracted from token 'sub' claim
"""
import json
import boto3
import sys
import os

# Import shared timezone utilities (copied during deployment)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

try:
    from timezone_utils import get_user_timezone, get_current_date_in_timezone, calculate_days_between
    TIMEZONE_ENABLED = True
except ImportError:
    # Graceful degradation: Status calculation disabled if imports fail
    TIMEZONE_ENABLED = False

def lambda_handler(event, context):
    """Handle GET /streak/check requests with status calculation.""
    
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
    
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if not user_id:
        return {
            'statusCode': 401,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Unauthorized'})
        }
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('EngagementDB')
        
        response = table.get_item(Key={'userId': user_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'max-age=300'
                },
                'body': json.dumps({
                    'streakCount': 0,
                    'streakFreezeAvailable': True,
                    'lastVideoDate': None
                })
            }
        
        item = response['Item']
        last_video_date = item.get('lastVideoDate')
        
        # CALCULATE STREAK STATUS based on days since last video
        # Requires timezone utilities for accurate date calculations
        streak_status = 'active'
        days_since = 0
        
        if TIMEZONE_ENABLED and last_video_date:
            # Get user's timezone and calculate days elapsed
            timezone = get_user_timezone(user_id)
            current_date = get_current_date_in_timezone(timezone)
            days_since = calculate_days_between(last_video_date, current_date)
            
            # Determine status based on business rules
            if days_since <= 1:
                streak_status = 'active'  # Uploaded today or yesterday
            elif days_since > 1 and item.get('streakFreezeAvailable', True):
                streak_status = 'at_risk'  # Can use freeze to recover
            else:
                streak_status = 'broken'  # Streak lost
        
        # Return enhanced streak data with caching headers
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'max-age=3600',  # Cache for 1 hour
                'ETag': f'"{last_video_date}"'  # Enable conditional requests
            },
            'body': json.dumps({
                'streakCount': int(item.get('streakCount', 0)),
                'streakFreezeAvailable': item.get('streakFreezeAvailable', True),
                'lastVideoDate': last_video_date,
                'streakStatus': streak_status,  # active/at_risk/broken
                'daysSinceLastVideo': days_since  # For UI display
            })
        }
        
    except Exception as e:
        print(f"Error checking streak: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
