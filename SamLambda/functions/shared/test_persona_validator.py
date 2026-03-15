import json
import unittest
import sys
import os

# Add the shared directory to the path for testing
sys.path.append(os.path.join(os.path.dirname(__file__)))
from persona_validator import PersonaValidator

class TestPersonaValidator(unittest.TestCase):
    
    def test_extract_legacy_maker_persona(self):
        """Test extracting legacy maker persona from JWT"""
        
        test_event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'email': 'test@example.com',
                        'custom:persona_type': 'legacy_maker',
                        'custom:initiator_id': 'test-user-123',
                        'custom:related_user_id': ''
                    }
                }
            }
        }
        
        persona_info = PersonaValidator.get_user_persona_from_jwt(test_event)
        
        self.assertEqual(persona_info['user_id'], 'test-user-123')
        self.assertEqual(persona_info['email'], 'test@example.com')
        self.assertEqual(persona_info['persona_type'], 'legacy_maker')
        self.assertEqual(persona_info['initiator_id'], 'test-user-123')
        
    def test_validate_legacy_maker_access_success(self):
        """Test successful legacy maker validation"""
        
        persona_info = {
            'user_id': 'test-user-123',
            'persona_type': 'legacy_maker'
        }
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "Access granted")
        
    def test_validate_legacy_maker_access_failure(self):
        """Test failed legacy maker validation"""
        
        persona_info = {
            'user_id': 'test-user-456',
            'persona_type': 'legacy_benefactor'
        }
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        
        self.assertFalse(is_valid)
        self.assertIn("Only legacy makers", message)
        
    def test_validate_legacy_benefactor_access_success(self):
        """Test successful legacy benefactor validation"""
        
        persona_info = {
            'user_id': 'test-user-456',
            'persona_type': 'legacy_benefactor'
        }
        
        is_valid, message = PersonaValidator.validate_legacy_benefactor_access(persona_info)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "Access granted")
        
    def test_create_access_denied_response(self):
        """Test creating standardized access denied response"""
        
        response = PersonaValidator.create_access_denied_response("Test error message")
        
        self.assertEqual(response['statusCode'], 403)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        
        body = json.loads(response['body'])
        self.assertEqual(body['error'], "Test error message")
        self.assertEqual(body['errorType'], "AccessDenied")
        
    def test_add_persona_context_to_response(self):
        """Test adding persona context to response"""
        
        response_body = {'data': 'test'}
        persona_info = {
            'user_id': 'test-user-123',
            'persona_type': 'legacy_maker',
            'initiator_id': 'test-user-123'
        }
        
        updated_body = PersonaValidator.add_persona_context_to_response(response_body, persona_info)
        
        self.assertIn('userContext', updated_body)
        self.assertEqual(updated_body['userContext']['persona_type'], 'legacy_maker')
        self.assertEqual(updated_body['userContext']['user_id'], 'test-user-123')
        self.assertTrue(updated_body['userContext']['is_initiator'])

if __name__ == '__main__':
    unittest.main()