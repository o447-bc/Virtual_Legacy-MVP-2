import os
import json
import boto3

SSM_PARAM_NAME = '/virtuallegacy/total_valid_questions_cache'
ssm_client = boto3.client('ssm')

def lambda_handler(event, context):
    """Invalidate the total valid questions cache"""
    print(f"Invalidating cache: {SSM_PARAM_NAME}")
    
    headers = {
        'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'DELETE,OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        ssm_client.delete_parameter(Name=SSM_PARAM_NAME)
        print("Cache invalidated successfully")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Cache invalidated successfully'})
        }
    except ssm_client.exceptions.ParameterNotFound:
        print("Cache was already empty")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'Cache was already empty'})
        }
    except Exception as e:
        print(f"Error invalidating cache: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to invalidate cache. Please try again.'})
        }
