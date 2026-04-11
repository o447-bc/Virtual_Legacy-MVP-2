import json
import unittest
import sys
import os
from unittest.mock import patch
import app

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from persona_validator import PersonaValidator

class TestQuestionPersonaValidation(unittest.TestCase):
    
    def test_legacy_maker_can_access_questions(self):
        """Test that legacy makers can access questions"""
        
        # Mock event with legacy maker persona — uses production 'profile' JSON structure
        test_event = {
            'queryStringParameters': {
                'questionType': 'childhood',
                'userId': 'test-user-123'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123',
                        'profile': json.dumps({
                            'persona_type': 'legacy_maker',
                            'initiator_id': 'test-user-123',
                            'related_user_id': ''
                        })
                    }
                }
            }
        }
        
        # Test persona extraction
        persona_info = PersonaValidator.get_user_persona_from_jwt(test_event)
        self.assertEqual(persona_info['persona_type'], 'legacy_maker')
        
        # Test validation
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        self.assertTrue(is_valid)
        
    def test_legacy_benefactor_cannot_access_questions(self):
        """Test that legacy benefactors cannot access questions"""
        
        # Mock event with legacy benefactor persona — uses production 'profile' JSON structure
        test_event = {
            'queryStringParameters': {
                'questionType': 'childhood',
                'userId': 'test-user-456'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-456',
                        'profile': json.dumps({
                            'persona_type': 'legacy_benefactor',
                            'initiator_id': 'test-user-456',
                            'related_user_id': ''
                        })
                    }
                }
            }
        }
        
        # Test persona extraction
        persona_info = PersonaValidator.get_user_persona_from_jwt(test_event)
        self.assertEqual(persona_info['persona_type'], 'legacy_benefactor')
        
        # Test validation
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        self.assertFalse(is_valid)
        self.assertIn("Only legacy makers", message)
        
    @patch('app.get_unanswered_questions')
    def test_questions_blocked_for_benefactor(self, mock_get_questions):
        """Test that question access is blocked for legacy benefactors"""
        
        test_event = {
            'queryStringParameters': {
                'questionType': 'childhood',
                'userId': 'test-benefactor-789'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-benefactor-789',
                        'profile': json.dumps({
                            'persona_type': 'legacy_benefactor',
                            'initiator_id': 'test-benefactor-789',
                            'related_user_id': ''
                        })
                    }
                }
            }
        }
        
        response = app.lambda_handler(test_event, {})
        
        # Should return 403 Forbidden
        self.assertEqual(response['statusCode'], 403)
        
        body = json.loads(response['body'])
        self.assertIn('error', body)
        self.assertIn('Only legacy makers', body['error'])
        
        # Database should not be called
        mock_get_questions.assert_not_called()

if __name__ == '__main__':
    unittest.main()