import json
import os
import boto3
from botocore.exceptions import ClientError

cognito = boto3.client('cognito-idp')
USER_POOL_ID = os.environ.get('USER_POOL_ID', '')

def lambda_handler(event, context):
    print(f"[AUTHORIZER] Event received: {json.dumps(event)}")
    print(f"[AUTHORIZER] User Pool ID: {USER_POOL_ID}")
    
    token = event.get('queryStringParameters', {}).get('token')
    print(f"[AUTHORIZER] Token present: {token is not None}")
    
    if not token:
        print("[AUTHORIZER] No token provided - DENY")
        return generate_policy('user', 'Deny', event['methodArn'])
    
    print(f"[AUTHORIZER] Token length: {len(token)}")
    print(f"[AUTHORIZER] Token preview: {token[:20]}...{token[-20:]}")
    
    try:
        print("[AUTHORIZER] Calling Cognito get_user...")
        response = cognito.get_user(AccessToken=token)
        user_id = response['Username']
        print(f"[AUTHORIZER] User authenticated: {user_id}")
        
        policy = generate_policy(user_id, 'Allow', event['methodArn'], {
            'userId': user_id
        })
        print(f"[AUTHORIZER] Returning ALLOW policy for user: {user_id}")
        return policy
        
    except ClientError as e:
        print(f"[AUTHORIZER] Cognito error: {e.response['Error']['Code']}")
        print(f"[AUTHORIZER] Error message: {e.response['Error']['Message']}")
        print("[AUTHORIZER] Returning DENY policy")
        return generate_policy('user', 'Deny', event['methodArn'])
    except Exception as e:
        print(f"[AUTHORIZER] Unexpected error: {type(e).__name__}: {e}")
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id, effect, resource, context=None):
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }
    if context:
        policy['context'] = context
    return policy
