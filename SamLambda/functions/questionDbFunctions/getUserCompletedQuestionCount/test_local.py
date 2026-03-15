import json
from app import lambda_handler

print("=" * 60)
print("Test 1: OPTIONS Request (CORS Preflight)")
print("=" * 60)
options_event = {'httpMethod': 'OPTIONS'}
response = lambda_handler(options_event, None)
print(f"Status: {response['statusCode']}")
print(f"Headers: {json.dumps(response['headers'], indent=2)}")

print("\n" + "=" * 60)
print("Test 2: GET Request (provide test userId)")
print("=" * 60)
test_user_id = input("Enter test userId: ").strip()

if test_user_id:
    print("\nFirst call (cache miss expected):")
    get_event = {
        'httpMethod': 'GET',
        'queryStringParameters': {'userId': test_user_id}
    }
    response = lambda_handler(get_event, None)
    print(f"Status: {response['statusCode']}")
    body = json.loads(response['body'])
    print(f"Response: {json.dumps(body, indent=2)}")
    
    print("\nSecond call (cache hit expected):")
    response = lambda_handler(get_event, None)
    body = json.loads(response['body'])
    print(f"Response: {json.dumps(body, indent=2)}")
else:
    print("No userId provided, skipping GET tests")
