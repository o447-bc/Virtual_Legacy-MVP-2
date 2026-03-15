import json
import unittest
import app

class TestGetRelationships(unittest.TestCase):
    def test_get_relationships(self):
        """Test getting relationships for a user"""
        
        # Test data
        test_event = {
            'queryStringParameters': {
                'userId': 'test-initiator-123'
            }
        }
        
        # Test Lambda handler
        response = app.lambda_handler(test_event, {})
        
        print(f"Response: {response}")
        self.assertEqual(response['statusCode'], 200)
        
        body = json.loads(response['body'])
        self.assertIn('relationships', body)
        self.assertIsInstance(body['relationships'], list)
        
    def test_missing_user_id(self):
        """Test with missing userId parameter"""
        
        test_event = {
            'queryStringParameters': {}
        }
        
        response = app.lambda_handler(test_event, {})
        
        print(f"Error response: {response}")
        self.assertEqual(response['statusCode'], 400)

if __name__ == '__main__':
    unittest.main()