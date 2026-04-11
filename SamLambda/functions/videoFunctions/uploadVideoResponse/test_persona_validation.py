import json
import unittest
import sys
import os
from unittest.mock import patch
import app

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from persona_validator import PersonaValidator

class TestPersonaValidation(unittest.TestCase):
    
    def test_legacy_maker_can_upload(self):
        """Test that legacy makers can upload videos"""
        
        # Mock event with legacy maker persona — uses production 'profile' JSON structure
        test_event = {
            'httpMethod': 'POST',
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
            },
            'body': json.dumps({
                'userId': 'test-user-123',
                'questionId': 'test-question-1',
                'questionType': 'childhood',
                'videoData': 'dGVzdCB2aWRlbyBkYXRh'  # base64 encoded test data
            })
        }
        
        # Test persona extraction
        persona_info = PersonaValidator.get_user_persona_from_jwt(test_event)
        self.assertEqual(persona_info['persona_type'], 'legacy_maker')
        
        # Test validation
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        self.assertTrue(is_valid)
        self.assertEqual(message, "Access granted")
        
    def test_legacy_benefactor_cannot_upload(self):
        """Test that legacy benefactors cannot upload videos"""
        
        # Mock event with legacy benefactor persona — uses production 'profile' JSON structure
        test_event = {
            'httpMethod': 'POST',
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
            },
            'body': json.dumps({
                'userId': 'test-user-456',
                'questionId': 'test-question-1',
                'questionType': 'childhood',
                'videoData': 'dGVzdCB2aWRlbyBkYXRh'
            })
        }
        
        # Test persona extraction
        persona_info = PersonaValidator.get_user_persona_from_jwt(test_event)
        self.assertEqual(persona_info['persona_type'], 'legacy_benefactor')
        
        # Test validation
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        self.assertFalse(is_valid)
        self.assertIn("Only legacy makers", message)
        
    @patch('app.upload_to_s3')
    @patch('app.update_user_question_status')
    def test_upload_blocked_for_benefactor(self, mock_update_db, mock_upload_s3):
        """Test that upload is blocked for legacy benefactors"""
        
        test_event = {
            'httpMethod': 'POST',
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
            },
            'body': json.dumps({
                'userId': 'test-benefactor-789',
                'questionId': 'test-question-1',
                'questionType': 'childhood',
                'videoData': 'dGVzdCB2aWRlbyBkYXRh'
            })
        }
        
        response = app.lambda_handler(test_event, {})
        
        # Should return 403 Forbidden
        self.assertEqual(response['statusCode'], 403)
        
        body = json.loads(response['body'])
        self.assertIn('error', body)
        self.assertIn('Only legacy makers', body['error'])
        
        # S3 and DB should not be called
        mock_upload_s3.assert_not_called()
        mock_update_db.assert_not_called()

if __name__ == '__main__':
    unittest.main()