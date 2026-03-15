import json
import unittest
import app

class TestValidateAccess(unittest.TestCase):
    def test_self_access(self):
        """Test self-access validation"""
        
        # Test data - same user ID
        test_event = {
            'queryStringParameters': {
                'requestingUserId': 'test-user-123',
                'targetUserId': 'test-user-123'
            }
        }
        
        # Test Lambda handler
        response = app.lambda_handler(test_event, {})
        
        print(f"Self-access response: {response}")
        self.assertEqual(response['statusCode'], 200)
        
        body = json.loads(response['body'])
        self.assertTrue(body['hasAccess'])
        self.assertEqual(body['reason'], 'self_access')
        
    def test_relationship_access(self):
        """Test relationship-based access validation"""
        
        # Test data - different users
        test_event = {
            'queryStringParameters': {
                'requestingUserId': 'test-initiator-123',
                'targetUserId': 'test-related-456'
            }
        }
        
        # Test Lambda handler
        response = app.lambda_handler(test_event, {})
        
        print(f"Relationship access response: {response}")
        self.assertEqual(response['statusCode'], 200)
        
        body = json.loads(response['body'])
        self.assertIn('hasAccess', body)
        self.assertIn('reason', body)
        
    def test_missing_parameters(self):
        """Test with missing parameters"""
        
        test_event = {
            'queryStringParameters': {
                'requestingUserId': 'test-user-123'
                # Missing targetUserId
            }
        }
        
        response = app.lambda_handler(test_event, {})
        
        print(f"Error response: {response}")
        self.assertEqual(response['statusCode'], 400)

if __name__ == '__main__':
    unittest.main()