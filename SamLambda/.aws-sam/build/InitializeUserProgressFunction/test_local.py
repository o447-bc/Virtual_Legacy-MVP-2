#!/usr/bin/env python3
"""
Local test for InitializeUserProgress Lambda function
"""

import json
import sys
import os

# Add the function directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import lambda_handler

def test_initialize_progress():
    """Test the initialize progress function"""
    
    # Mock event with JWT claims
    event = {
        'httpMethod': 'POST',
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'test-user-id-12345',
                    'profile': json.dumps({
                        'persona_type': 'legacy_maker'
                    })
                }
            }
        }
    }
    
    # Mock context
    context = {}
    
    print("Testing InitializeUserProgress function...")
    print(f"Event: {json.dumps(event, indent=2)}")
    
    try:
        response = lambda_handler(event, context)
        print(f"Response: {json.dumps(response, indent=2)}")
        
        if response['statusCode'] == 200:
            print("✅ Test passed!")
        else:
            print("❌ Test failed!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    test_initialize_progress()