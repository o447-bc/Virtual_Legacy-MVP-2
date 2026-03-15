import boto3
import json

# Check exact table schema
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')

try:
    response = table.meta.client.describe_table(TableName='allQuestionDB')
    
    print("=== ACTUAL TABLE SCHEMA ===")
    key_schema = response['Table']['KeySchema']
    for key in key_schema:
        key_type = "Partition Key" if key['KeyType'] == 'HASH' else "Sort Key"
        print(f"{key_type}: {key['AttributeName']}")
    
    # Test with sample data
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket='virtual-legacy', Key='questions/questionsInJSON/childhood.json')
    body = response['Body'].read().decode('utf-8')
    data = json.loads(body)
    
    print("\n=== SAMPLE DATA ===")
    sample_item = data[0] if isinstance(data, list) else data
    print("Available fields:", list(sample_item.keys()))
    print("Sample item:", json.dumps(sample_item, indent=2))
    
except Exception as e:
    print(f"Error: {e}")