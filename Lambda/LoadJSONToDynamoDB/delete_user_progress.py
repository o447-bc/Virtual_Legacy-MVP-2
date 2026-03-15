#!/usr/bin/env python3
import boto3
import sys

# Get user ID from command line or use default
user_id = sys.argv[1] if len(sys.argv) > 1 else None

if not user_id:
    print("Usage: python delete_user_progress.py <user_id>")
    print("\nOr delete ALL user progress:")
    print("python delete_user_progress.py ALL")
    sys.exit(1)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('userQuestionLevelProgressDB')

if user_id == "ALL":
    print("Deleting ALL user progress records...")
    response = table.scan()
    items = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    print(f"Found {len(items)} progress records to delete")
    
    deleted_count = 0
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'userId': item['userId'],
                    'questionType': item['questionType']
                }
            )
            deleted_count += 1
            if deleted_count % 50 == 0:
                print(f"Deleted {deleted_count} records...")
    
    print(f"Successfully deleted {deleted_count} progress records")
else:
    print(f"Deleting progress records for user: {user_id}")
    
    # Query for this specific user
    response = table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    
    items = response['Items']
    print(f"Found {len(items)} progress records for this user")
    
    # Delete each record
    deleted_count = 0
    for item in items:
        table.delete_item(
            Key={
                'userId': item['userId'],
                'questionType': item['questionType']
            }
        )
        deleted_count += 1
        print(f"Deleted: {item['questionType']}")
    
    print(f"\nSuccessfully deleted {deleted_count} progress records for user {user_id}")
