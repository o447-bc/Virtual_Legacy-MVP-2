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
print("Test 2: GET Request (First Call - Cache Miss)")
print("=" * 60)
get_event = {'httpMethod': 'GET'}
response = lambda_handler(get_event, None)
print(f"Status: {response['statusCode']}")
body = json.loads(response['body'])
print(f"Response: {json.dumps(body, indent=2)}")

print("\n" + "=" * 60)
print("Test 3: GET Request (Second Call - Cache Hit)")
print("=" * 60)
response = lambda_handler(get_event, None)
body = json.loads(response['body'])
print(f"Response: {json.dumps(body, indent=2)}")
