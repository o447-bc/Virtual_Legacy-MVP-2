import json
import unittest
import app

class TestCreateRelationship(unittest.TestCase):
    def test_create_relationship(self):
        """Test creating a relationship"""
        
        # Test data
        test_event = {
            'body': json.dumps({
                'initiator_id': 'test-initiator-123',
                'related_user_id': 'test-related-456',
                'relationship_type': 'maker_to_benefactor',
                'access_expiry': '2024-12-31T23:59:59Z'
            })
        }
        
        # Test Lambda handler
        response = app.lambda_handler(test_event, {})
        
        print(f"Response: {response}")
        self.assertEqual(response['statusCode'], 200)
        
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertIn('relationship', body)
        
    def test_missing_parameters(self):
        """Test with missing parameters"""
        
        test_event = {
            'body': json.dumps({
                'initiator_id': 'test-initiator-123'
                # Missing required fields
            })
        }
        
        response = app.lambda_handler(test_event, {})
        
        print(f"Error response: {response}")
        self.assertEqual(response['statusCode'], 400)

if __name__ == '__main__':
    unittest.main()