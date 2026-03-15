#!/usr/bin/env python3
"""
Comprehensive test script for getUserCompletedQuestionCount Lambda function
"""

import json
import boto3
from app import lambda_handler

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_options():
    print_section("TEST 1: OPTIONS Request (CORS Preflight)")
    event = {'httpMethod': 'OPTIONS'}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200, "OPTIONS should return 200"
    assert response['body'] == '', "OPTIONS should return empty body"
    assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header"
    
    print("✅ PASSED: OPTIONS returns correct CORS headers")

def test_missing_user_id():
    print_section("TEST 2: Missing userId Parameter")
    event = {'httpMethod': 'GET', 'queryStringParameters': {}}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400, "Should return 400 for missing userId"
    body = json.loads(response['body'])
    assert 'error' in body, "Should return error message"
    
    print("✅ PASSED: Handles missing userId correctly")

def test_with_user_id(user_id):
    print_section(f"TEST 3: GET Request with userId={user_id}")
    
    event = {
        'httpMethod': 'GET',
        'queryStringParameters': {'userId': user_id}
    }
    
    # First call (cache miss)
    print("\nFirst call (cache miss expected):")
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200, "Should return 200"
    body = json.loads(response['body'])
    
    assert 'count' in body, "Response should have 'count' field"
    assert 'cached' in body, "Response should have 'cached' field"
    assert 'userId' in body, "Response should have 'userId' field"
    assert isinstance(body['count'], int), "Count should be an integer"
    assert body['count'] >= 0, "Count should be non-negative"
    
    print(f"✅ Count: {body['count']}, Cached: {body['cached']}")
    
    # Second call (cache hit)
    print("\nSecond call (cache hit expected):")
    response = lambda_handler(event, None)
    body2 = json.loads(response['body'])
    
    assert body2['count'] == body['count'], "Count should be consistent"
    print(f"✅ Count: {body2['count']}, Cached: {body2['cached']}")
    
    return body['count']

def test_ssm_parameter(user_id):
    print_section("TEST 4: SSM Parameter Store")
    
    ssm = boto3.client('ssm')
    param_name = f'/virtuallegacy/user_completed_count/{user_id}'
    
    try:
        response = ssm.get_parameter(Name=param_name)
        cache_data = json.loads(response['Parameter']['Value'])
        
        assert 'count' in cache_data, "Cache should have 'count' field"
        assert 'timestamp' in cache_data, "Cache should have 'timestamp' field"
        
        print(f"✅ PASSED: SSM parameter exists and is valid")
        print(f"   Parameter: {param_name}")
        print(f"   Count: {cache_data['count']}")
        print(f"   Timestamp: {cache_data['timestamp']}")
        
    except ssm.exceptions.ParameterNotFound:
        print(f"⚠️  WARNING: SSM parameter not found (cache may be empty)")

def main():
    print("\n" + "=" * 70)
    print("  COMPREHENSIVE TEST SUITE: getUserCompletedQuestionCount")
    print("=" * 70)
    
    try:
        test_options()
        test_missing_user_id()
        
        test_user_id = input("\nEnter test userId: ").strip()
        if test_user_id:
            test_with_user_id(test_user_id)
            test_ssm_parameter(test_user_id)
        else:
            print("⚠️  No userId provided, skipping user-specific tests")
        
        print("\n" + "=" * 70)
        print("  ✅ ALL TESTS PASSED!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
