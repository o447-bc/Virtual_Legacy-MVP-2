import os
import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from cors import cors_headers
from responses import error_response


# Constants
SSM_PARAM_PREFIX = '/virtuallegacy/user_completed_count/'
CACHE_TTL_SECONDS = 86400  # 24 hours
DYNAMODB_TABLE = 'userQuestionStatusDB'

# Initialize clients (reused across warm Lambda invocations)
ssm_client = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')

def get_cached_count(user_id):
    """Retrieve cached count from SSM Parameter Store if valid"""
    try:
        param_name = f"{SSM_PARAM_PREFIX}{user_id}"
        response = ssm_client.get_parameter(Name=param_name)
        cache_data = json.loads(response['Parameter']['Value'])
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age = datetime.now() - cache_time
        
        if age < timedelta(seconds=CACHE_TTL_SECONDS):
            print(f"Cache hit: userId={user_id}, count={cache_data['count']}, age={age.total_seconds()}s")
            return cache_data['count']
        else:
            print(f"Cache expired: age={age.total_seconds()}s")
            return None
    except ssm_client.exceptions.ParameterNotFound:
        print(f"Cache miss: parameter not found for userId={user_id}")
        return None
    except Exception as e:
        print(f"Cache read error: {str(e)}")
        return None

def set_cached_count(user_id, count):
    """Store count in SSM Parameter Store with timestamp"""
    try:
        param_name = f"{SSM_PARAM_PREFIX}{user_id}"
        cache_data = {
            'count': count,
            'timestamp': datetime.now().isoformat()
        }
        ssm_client.put_parameter(
            Name=param_name,
            Value=json.dumps(cache_data),
            Type='String',
            Overwrite=True
        )
        print(f"Cache updated: userId={user_id}, count={count}")
    except Exception as e:
        print(f"Cache write error: {str(e)}")

def get_completed_count_from_db(user_id):
    """Query DynamoDB to count all completed questions for user"""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id},
            Select='COUNT'
        )
        
        total_count = response['Count']
        print(f"Initial query: {total_count} items")
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id},
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            total_count += response['Count']
            print(f"Pagination query: +{response['Count']} items, total={total_count}")
        
        print(f"Final count: {total_count} completed questions for userId={user_id}")
        return total_count
    except ClientError as e:
        print(f"DynamoDB error: {str(e)}")
        raise

def lambda_handler(event, context):
    """Main Lambda handler with caching logic"""
    print(f"Event: {json.dumps(event)}")
    
    # CORS headers (consistent with project pattern)
    headers = {
        'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    # Handle OPTIONS for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Extract userId from query parameters
    user_id = None
    if event.get('queryStringParameters'):
        user_id = event['queryStringParameters'].get('userId')
    
    if not user_id:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Missing required parameter: userId'
            })
        }
    
    try:
        # Try cache first
        cached_count = get_cached_count(user_id)
        
        if cached_count is not None:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'count': cached_count,
                    'cached': True,
                    'userId': user_id
                })
            }
        
        # Cache miss - query database
        count = get_completed_count_from_db(user_id)
        
        # Update cache
        set_cached_count(user_id, count)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'count': count,
                'cached': False,
                'userId': user_id
            })
        }
        
    except ClientError as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'A server error occurred. Please try again.'
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'A server error occurred. Please try again.'
            })
        }
