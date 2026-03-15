#!/usr/bin/env python3
import boto3
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')

print("Scanning all items from allQuestionDB...")

# Scan all items
response = table.scan()
items = response['Items']

# Handle pagination if there are more items
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response['Items'])

print(f"Found {len(items)} items to delete")

# Delete items in batches
deleted_count = 0
with table.batch_writer() as batch:
    for item in items:
        batch.delete_item(
            Key={
                'questionId': item['questionId'],
                'questionType': item['questionType']
            }
        )
        deleted_count += 1
        if deleted_count % 50 == 0:
            print(f"Deleted {deleted_count} items...")

print(f"Successfully deleted {deleted_count} items from allQuestionDB")
