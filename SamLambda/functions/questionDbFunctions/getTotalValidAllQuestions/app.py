import os
import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from cors import cors_headers
from responses import error_response


# Constants
SSM_PARAM_NAME = '/virtuallegacy/total_valid_questions_cache'
CACHE_TTL_SECONDS = 86400  # 24 hours
DYNAMODB_TABLE = 'allQuestionDB'

# Initialize clients (reused across warm Lambda invocations)
ssm_client = boto3.client('ssm')
dynamodb = boto3.resource('dynamodb')

def get_cached_count():
    """Retrieve cached count from SSM Parameter Store if valid"""
    try:
        response = ssm_client.get_parameter(Name=SSM_PARAM_NAME)
        cache_data = json.loads(response['Parameter']['Value'])
        
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age = datetime.now() - cache_time
        
        if age < timedelta(seconds=CACHE_TTL_SECONDS):
            print(f"Cache hit: count={cache_data['count']}, age={age.total_seconds()}s")
            return cache_data['count']
        else:
            print(f"Cache expired: age={age.total_seconds()}s")
            return None
    except ssm_client.exceptions.ParameterNotFound:
        print("Cache miss: parameter not found")
        return None
    except Exception as e:
        print(f"Cache read error: {str(e)}")
        return None

def set_cached_count(count):
    """Store count in SSM Parameter Store with timestamp"""
    try:
        cache_data = {
            'count': count,
            'timestamp': datetime.now().isoformat()
        }
        ssm_client.put_parameter(
            Name=SSM_PARAM_NAME,
            Value=json.dumps(cache_data),
            Type='String',
            Overwrite=True
        )
        print(f"Cache updated: count={count}")
    except Exception as e:
        print(f"Cache write error: {str(e)}")

def get_total_valid_questions_from_db():
    """Scan DynamoDB to count all valid questions"""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Support both new structure (active=True) and legacy (Valid=1)
        response = table.scan(
            FilterExpression='active = :active_true OR Valid = :valid',
            ExpressionAttributeValues={
                ':active_true': True,
                ':valid': 1
            },
            Select='COUNT'
        )
        
        total_count = response['Count']
        print(f"Initial scan: {total_count} items")
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='active = :active_true OR Valid = :valid',
                ExpressionAttributeValues={
                    ':active_true': True,
                    ':valid': 1
                },
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            total_count += response['Count']
            print(f"Pagination scan: +{response['Count']} items, total={total_count}")
        
        print(f"Final count: {total_count} valid questions")
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
    
    try:
        # Try cache first
        cached_count = get_cached_count()
        
        if cached_count is not None:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'count': cached_count,
                    'cached': True
                })
            }
        
        # Cache miss - query database
        count = get_total_valid_questions_from_db()
        
        # Update cache
        set_cached_count(count)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'count': count,
                'cached': False
            })
        }
        
    except ClientError as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Database error. Please try again.'
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'An unexpected error occurred. Please try again.'
            })
        }
