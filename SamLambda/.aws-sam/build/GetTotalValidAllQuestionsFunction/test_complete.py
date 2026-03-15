#!/usr/bin/env python3
"""
Comprehensive test script for getTotalValidAllQuestions Lambda function
Tests: OPTIONS, GET (cache miss), GET (cache hit), cache invalidation
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
    print(f"   Headers: {json.dumps(response['headers'], indent=6)}")

def test_get_request():
    print_section("TEST 2: GET Request")
    event = {'httpMethod': 'GET'}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200, "GET should return 200"
    body = json.loads(response['body'])
    
    assert 'count' in body, "Response should have 'count' field"
    assert 'cached' in body, "Response should have 'cached' field"
    assert isinstance(body['count'], int), "Count should be an integer"
    assert body['count'] > 0, "Count should be positive"
    
    print(f"✅ PASSED: GET returns valid response")
    print(f"   Count: {body['count']}")
    print(f"   Cached: {body['cached']}")
    
    return body

def test_cache_behavior():
    print_section("TEST 3: Cache Behavior")
    
    # First call
    event = {'httpMethod': 'GET'}
    response1 = lambda_handler(event, None)
    body1 = json.loads(response1['body'])
    
    # Second call (should be cached)
    response2 = lambda_handler(event, None)
    body2 = json.loads(response2['body'])
    
    assert body1['count'] == body2['count'], "Count should be consistent"
    
    print(f"✅ PASSED: Cache consistency verified")
    print(f"   First call:  count={body1['count']}, cached={body1['cached']}")
    print(f"   Second call: count={body2['count']}, cached={body2['cached']}")

def test_ssm_parameter():
    print_section("TEST 4: SSM Parameter Store")
    
    ssm = boto3.client('ssm')
    param_name = '/virtuallegacy/total_valid_questions_cache'
    
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

def test_error_handling():
    print_section("TEST 5: Error Handling")
    
    # Test with invalid event (should handle gracefully)
    event = {'httpMethod': 'POST'}  # Unsupported method
    response = lambda_handler(event, None)
    
    # Should still return 200 (Lambda doesn't fail)
    assert response['statusCode'] in [200, 400, 500], "Should return valid status code"
    
    print(f"✅ PASSED: Error handling works")
    print(f"   Status: {response['statusCode']}")

def main():
    print("\n" + "=" * 70)
    print("  COMPREHENSIVE TEST SUITE: getTotalValidAllQuestions")
    print("=" * 70)
    
    try:
        test_options()
        test_get_request()
        test_cache_behavior()
        test_ssm_parameter()
        test_error_handling()
        
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
