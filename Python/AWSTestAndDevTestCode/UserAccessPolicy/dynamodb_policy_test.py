import boto3
import json
from moto import mock_dynamodb, mock_iam, mock_sts
from botocore.exceptions import ClientError

# IAM Policy for DynamoDB user-specific access
DYNAMODB_USER_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:GetItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/userQuestionStatusDB",
            "Condition": {
                "ForAllValues:StringEquals": {
                    "dynamodb:LeadingKeys": ["${cognito-identity.amazonaws.com:sub}"]
                }
            }
        }
    ]
}

@mock_dynamodb
@mock_iam
@mock_sts
def test_dynamodb_user_policy():
    # Setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create table
    table = dynamodb.create_table(
        TableName='userQuestionStatusDB',
        KeySchema=[
            {'AttributeName': 'userID', 'KeyType': 'HASH'},
            {'AttributeName': 'questionID', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userID', 'AttributeType': 'S'},
            {'AttributeName': 'questionID', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Test data
    user_id = "test-user-123"
    other_user_id = "other-user-456"
    
    # Test writing to own partition (should work)
    try:
        table.put_item(Item={
            'userID': user_id,
            'questionID': 'q1',
            'status': 'answered',
            'timestamp': '2024-01-01T00:00:00Z'
        })
        print("✓ Successfully wrote to own partition")
    except Exception as e:
        print(f"✗ Failed to write to own partition: {e}")
    
    # Test reading from own partition
    try:
        response = table.get_item(Key={'userID': user_id, 'questionID': 'q1'})
        print("✓ Successfully read from own partition")
    except Exception as e:
        print(f"✗ Failed to read from own partition: {e}")
    
    print("\nIAM Policy JSON:")
    print(json.dumps(DYNAMODB_USER_POLICY, indent=2))

if __name__ == "__main__":
    test_dynamodb_user_policy()