import boto3
import json
import os
from botocore.exceptions import ClientError

# AWS credentials loaded from ~/.aws/credentials or environment
# Run: aws configure
# Or set: export AWS_PROFILE=your-profile

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

def test_real_dynamodb():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('userQuestionStatusDB')
    
    user_id = "849854f8-c011-70bd-4ce3-2ade792a904a"
    question_ids = ["childhood-00004"]
    
    # Add each questionID as separate record
    for qid in question_ids:
        try:
            table.put_item(Item={
                'userId': user_id,
                'questionId': str(qid),
                'questionType': 'childhood',
                'status': 'unanswered',
                'fileName': f'audio_{qid}.mp3',
                'location': 's3://bucket/audio/',
                'timestamp': '2024-01-01T00:00:00Z'
            })
            print(f"✓ Added question {qid}")
        except ClientError as e:
            print(f"✗ Failed question {qid}: {e}")
    
    # Query all questions for user
    try:
        response = table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        print(f"\n✓ Found {len(response['Items'])} questions for user")
    except ClientError as e:
        print(f"✗ Query failed: {e}")
    
    print("\nIAM Policy JSON:")
    print(json.dumps(DYNAMODB_USER_POLICY, indent=2))

if __name__ == "__main__":
    test_real_dynamodb()