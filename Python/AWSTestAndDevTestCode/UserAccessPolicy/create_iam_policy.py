import boto3
import json

def create_iam_policy():
    iam = boto3.client('iam')
    
    policy_document = {
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
    
    try:
        response = iam.create_policy(
            PolicyName='DynamoDBUserQuestionAccess',
            PolicyDocument=json.dumps(policy_document),
            Description='Allows users to access only their own records in userQuestionStatusDB'
        )
        print(f"✓ Created policy: {response['Policy']['Arn']}")
        return response['Policy']['Arn']
    except Exception as e:
        print(f"✗ Error creating policy: {e}")

if __name__ == "__main__":
    create_iam_policy()