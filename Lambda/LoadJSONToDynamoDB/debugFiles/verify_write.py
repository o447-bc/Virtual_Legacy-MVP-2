import boto3
import json

# Check what's actually in DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')

try:
    # Scan the table to see all items
    response = table.scan()
    items = response['Items']
    
    print(f"Found {len(items)} items in allQuestionDB:")
    for item in items:
        print(json.dumps(item, indent=2, default=str))
        
    # Also check table info
    print(f"\nTable region: {dynamodb.meta.client.meta.region_name}")
    print(f"Table status: {table.table_status}")
    
except Exception as e:
    print(f"Error accessing table: {e}")