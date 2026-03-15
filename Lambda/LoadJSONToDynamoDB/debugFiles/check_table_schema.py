import boto3
import json

# Check the table schema
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')

try:
    # Get table description
    response = table.meta.client.describe_table(TableName='allQuestionDB')
    
    print("=== TABLE SCHEMA ===")
    key_schema = response['Table']['KeySchema']
    attribute_definitions = response['Table']['AttributeDefinitions']
    
    print("Primary Key Schema:")
    for key in key_schema:
        key_type = "Partition Key" if key['KeyType'] == 'HASH' else "Sort Key"
        print(f"  {key_type}: {key['AttributeName']}")
    
    print("\nAttribute Types:")
    for attr in attribute_definitions:
        print(f"  {attr['AttributeName']}: {attr['AttributeType']}")
    
except Exception as e:
    print(f"Error: {e}")

# Also check what's in your S3 file
s3 = boto3.client('s3')
try:
    print("\n=== S3 FILE SAMPLE ===")
    response = s3.get_object(Bucket='virtual-legacy', Key='questions/questionsInJSON/childhood.json')
    body = response['Body'].read().decode('utf-8')
    data = json.loads(body)
    
    if isinstance(data, list) and len(data) > 0:
        print("First item structure:")
        print(json.dumps(data[0], indent=2))
    else:
        print("Single item structure:")
        print(json.dumps(data, indent=2))
        
except Exception as e:
    print(f"S3 Error: {e}")