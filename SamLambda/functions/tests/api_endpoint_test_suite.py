"""
API ENDPOINT PERSONA ACCESS CONTROL TEST SUITE

This test suite validates that all API endpoints correctly enforce persona-based
access control. It tests the integration between Cognito JWT tokens, the shared
persona validator, and the actual Lambda functions that handle API requests.

BUSINESS CONTEXT:
Each API endpoint must validate that the requesting user has the appropriate
persona type for the operation. This prevents unauthorized access and ensures
users only see functionality relevant to their role.

ENDPOINTS TESTED:
1. Video Upload (POST /functions/videoFunctions/upload) - Legacy Makers only
2. Get Unanswered Questions (GET /functions/questionDbFunctions/unanswered) - Legacy Makers only
3. Get Questions with Text (GET /functions/questionDbFunctions/unansweredwithtext) - Legacy Makers only
4. Relationship Management (POST/GET /relationships) - Both personas with different permissions
5. Access Validation (GET /relationships/validate) - Both personas

SECURITY VALIDATION:
- JWT token validation and custom attribute extraction
- Persona-based access control enforcement
- Proper error responses for unauthorized access
- CORS header inclusion for frontend compatibility
"""

import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import base64

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
from persona_validator import PersonaValidator

class APIEndpointTestSuite(unittest.TestCase):
    """
    Test suite for API endpoint persona access control.
    
    This suite simulates real API calls with different persona types
    to ensure proper access control is enforced at the endpoint level.
    """
    
    def setUp(self):
        """Set up test data for API endpoint testing."""
        # Legacy Maker user data
        self.legacy_maker = {
            'user_id': 'maker-123',
            'email': 'maker@example.com',
            'persona_type': 'legacy_maker',
            'initiator_id': 'maker-123',
            'related_user_id': ''
        }
        
        # Legacy Benefactor user data
        self.legacy_benefactor = {
            'user_id': 'benefactor-456',
            'email': 'benefactor@example.com',
            'persona_type': 'legacy_benefactor',
            'initiator_id': 'benefactor-456',
            'related_user_id': ''
        }
        
        print(f"\n{'='*80}")
        print("STARTING API ENDPOINT ACCESS CONTROL TESTS")
        print(f"{'='*80}")
    
    def create_api_event(self, user_data, method='GET', path='/', body=None, query_params=None):
        """
        Create mock API Gateway event with Cognito authorization.
        
        Args:
            user_data (dict): User persona information
            method (str): HTTP method
            path (str): API path
            body (dict): Request body
            query_params (dict): Query string parameters
            
        Returns:
            dict: Mock API Gateway event
        """
        event = {
            'httpMethod': method,
            'path': path,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_data['user_id'],
                        'email': user_data['email'],
                        'profile': json.dumps({
                            'persona_type': user_data['persona_type'],
                            'initiator_id': user_data['initiator_id'],
                            'related_user_id': user_data['related_user_id']
                        })
                    }
                }
            },
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        if body:
            event['body'] = json.dumps(body)
        
        if query_params:
            event['queryStringParameters'] = query_params
        
        return event

class TestVideoUploadEndpoint(APIEndpointTestSuite):
    """
    Test video upload endpoint persona access control.
    
    BUSINESS PURPOSE:
    Only Legacy Makers should be able to upload video responses to questions.
    Legacy Benefactors are viewers only and should not have upload capabilities.
    
    ENDPOINT: POST /functions/videoFunctions/upload
    AUTHORIZATION: Cognito JWT with Legacy Maker persona required
    """
    
    def test_legacy_maker_can_upload_video(self):
        """
        Test that Legacy Makers can successfully upload videos.
        
        BUSINESS SCENARIO:
        Legacy Maker has answered a question and wants to upload their
        video response. This should succeed with proper persona validation.
        """
        print("\n" + "="*60)
        print("TEST: Legacy Maker Video Upload - Success Case")
        print("="*60)
        print("SCENARIO: Legacy Maker uploads video response to question")
        print("EXPECTED: Upload succeeds with persona context in response")
        
        # Import video upload function
        import importlib.util
        upload_path = os.path.join(os.path.dirname(__file__), '../videoFunctions/uploadVideoResponse/app.py')
        spec = importlib.util.spec_from_file_location("upload_app", upload_path)
        upload_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_app)
        
        # Create test video upload request
        upload_request = {
            'userId': self.legacy_maker['user_id'],
            'questionId': 'childhood-001',
            'questionType': 'childhood',
            'videoData': base64.b64encode(b'test video data').decode('utf-8')
        }
        
        event = self.create_api_event(
            self.legacy_maker,
            method='POST',
            path='/functions/videoFunctions/upload',
            body=upload_request
        )
        
        # Mock AWS services
        with patch('boto3.client') as mock_s3_client, \
             patch('boto3.resource') as mock_dynamodb:
            
            # Mock S3 client
            mock_s3 = MagicMock()
            mock_s3_client.return_value = mock_s3
            
            # Mock DynamoDB resource
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Execute upload
            response = upload_app.lambda_handler(event, {})
            
            # Validate successful response
            self.assertEqual(response['statusCode'], 200)
            
            # Validate response includes persona context
            body = json.loads(response['body'])
            self.assertIn('userContext', body)
            self.assertEqual(body['userContext']['persona_type'], 'legacy_maker')
            self.assertTrue(body['userContext']['is_initiator'])
            
            # Validate S3 upload was attempted
            mock_s3.put_object.assert_called_once()
            
            # Validate DynamoDB update was attempted
            mock_table.put_item.assert_called_once()
        
        print("✓ PASSED: Legacy Maker successfully uploaded video")
        print("✓ PASSED: Persona context included in response")
        print("✓ PASSED: S3 and DynamoDB operations executed")
    
    def test_legacy_benefactor_blocked_from_video_upload(self):
        """
        Test that Legacy Benefactors are blocked from uploading videos.
        
        BUSINESS SCENARIO:
        Legacy Benefactor attempts to upload a video, which should be
        blocked because benefactors are viewers only, not content creators.
        """
        print("\n" + "="*60)
        print("TEST: Legacy Benefactor Video Upload - Blocked")
        print("="*60)
        print("SCENARIO: Legacy Benefactor attempts to upload video")
        print("EXPECTED: 403 Forbidden with clear error message")
        
        import importlib.util
        upload_path = os.path.join(os.path.dirname(__file__), '../videoFunctions/uploadVideoResponse/app.py')
        spec = importlib.util.spec_from_file_location("upload_app", upload_path)
        upload_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_app)
        
        upload_request = {
            'userId': self.legacy_benefactor['user_id'],
            'questionId': 'childhood-001',
            'questionType': 'childhood',
            'videoData': base64.b64encode(b'test video data').decode('utf-8')
        }
        
        event = self.create_api_event(
            self.legacy_benefactor,
            method='POST',
            body=upload_request
        )
        
        # Mock AWS services (should not be called)
        with patch('boto3.client') as mock_s3_client, \
             patch('boto3.resource') as mock_dynamodb:
            
            response = upload_app.lambda_handler(event, {})
            
            # Validate blocked response
            self.assertEqual(response['statusCode'], 403)
            
            body = json.loads(response['body'])
            self.assertIn('error', body)
            self.assertIn('Only legacy makers', body['error'])
            self.assertEqual(body['errorType'], 'AccessDenied')
            
            # Validate AWS services were not called
            mock_s3_client.assert_not_called()
            mock_dynamodb.assert_not_called()
        
        print("✓ PASSED: Legacy Benefactor blocked from video upload")
        print("✓ PASSED: Clear error message provided")
        print("✓ PASSED: AWS services not called (no unauthorized operations)")

class TestQuestionAccessEndpoints(APIEndpointTestSuite):
    """
    Test question access endpoints persona validation.
    
    BUSINESS PURPOSE:
    Only Legacy Makers should access questions because they are the ones
    who record responses. Legacy Benefactors view the recorded content,
    not the questions themselves.
    
    ENDPOINTS:
    - GET /functions/questionDbFunctions/unanswered
    - GET /functions/questionDbFunctions/unansweredwithtext
    """
    
    def test_legacy_maker_can_access_questions(self):
        """
        Test Legacy Makers can access unanswered questions.
        
        BUSINESS SCENARIO:
        Legacy Maker wants to see what questions they haven't answered
        yet so they can continue recording their legacy.
        """
        print("\n" + "="*60)
        print("TEST: Legacy Maker Question Access - Success")
        print("="*60)
        print("SCENARIO: Legacy Maker requests unanswered questions")
        print("EXPECTED: Questions returned with persona context")
        
        # Test unanswered questions endpoint
        import importlib.util
        questions_path = os.path.join(os.path.dirname(__file__), '../questionDbFunctions/getUnansweredQuestionsFromUser/app.py')
        spec = importlib.util.spec_from_file_location("questions_app", questions_path)
        questions_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(questions_app)
        
        event = self.create_api_event(
            self.legacy_maker,
            query_params={
                'questionType': 'childhood',
                'userId': self.legacy_maker['user_id']
            }
        )
        
        # Mock DynamoDB
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock database responses
            mock_table.scan.return_value = {'Items': []}
            mock_table.query.return_value = {'Items': []}
            
            response = questions_app.lambda_handler(event, {})
            
            # Validate successful response
            self.assertEqual(response['statusCode'], 200)
            
            body = json.loads(response['body'])
            self.assertIn('unansweredQuestionIds', body)
            self.assertIn('userContext', body)
            self.assertEqual(body['userContext']['persona_type'], 'legacy_maker')
        
        print("✓ PASSED: Legacy Maker successfully accessed questions")
        print("✓ PASSED: Persona context included in response")
    
    def test_legacy_benefactor_blocked_from_questions(self):
        """
        Test Legacy Benefactors are blocked from accessing questions.
        
        BUSINESS SCENARIO:
        Legacy Benefactor attempts to access questions, which should be
        blocked because benefactors view recorded content, not questions.
        """
        print("\n" + "="*60)
        print("TEST: Legacy Benefactor Question Access - Blocked")
        print("="*60)
        print("SCENARIO: Legacy Benefactor attempts to access questions")
        print("EXPECTED: 403 Forbidden response")
        
        import importlib.util
        questions_path = os.path.join(os.path.dirname(__file__), '../questionDbFunctions/getUnansweredQuestionsFromUser/app.py')
        spec = importlib.util.spec_from_file_location("questions_app", questions_path)
        questions_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(questions_app)
        
        event = self.create_api_event(
            self.legacy_benefactor,
            query_params={
                'questionType': 'childhood',
                'userId': self.legacy_benefactor['user_id']
            }
        )
        
        # Mock DynamoDB (should not be called)
        with patch('boto3.resource') as mock_dynamodb:
            response = questions_app.lambda_handler(event, {})
            
            # Validate blocked response
            self.assertEqual(response['statusCode'], 403)
            
            body = json.loads(response['body'])
            self.assertIn('error', body)
            self.assertIn('Only legacy makers', body['error'])
            
            # Validate database not accessed
            mock_dynamodb.assert_not_called()
        
        print("✓ PASSED: Legacy Benefactor blocked from question access")
        print("✓ PASSED: Database operations prevented")

class TestRelationshipManagementEndpoints(APIEndpointTestSuite):
    """
    Test relationship management endpoints.
    
    BUSINESS PURPOSE:
    Both persona types need to manage relationships, but with different
    permissions. Initiators create relationships, related users participate.
    
    ENDPOINTS:
    - POST /relationships (create relationship)
    - GET /relationships (get user relationships)
    - GET /relationships/validate (validate access)
    """
    
    def test_create_relationship_success(self):
        """
        Test successful relationship creation.
        
        BUSINESS SCENARIO:
        Legacy Benefactor initiator wants to set up legacy recording
        for their parent, creating a relationship between them.
        """
        print("\n" + "="*60)
        print("TEST: Relationship Creation - Success")
        print("="*60)
        print("SCENARIO: Benefactor creates relationship with Legacy Maker")
        print("EXPECTED: Relationship created successfully")
        
        import importlib.util
        create_rel_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/createRelationship/app.py')
        spec = importlib.util.spec_from_file_location("create_rel_app", create_rel_path)
        create_rel_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_rel_app)
        
        relationship_data = {
            'initiator_id': self.legacy_benefactor['user_id'],
            'related_user_id': 'parent-maker-789',
            'relationship_type': 'benefactor_to_maker',
            'access_expiry': '2024-12-31T23:59:59Z'
        }
        
        event = self.create_api_event(
            self.legacy_benefactor,
            method='POST',
            body=relationship_data
        )
        
        # Mock DynamoDB
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            response = create_rel_app.lambda_handler(event, {})
            
            # Validate successful creation
            self.assertEqual(response['statusCode'], 200)
            
            body = json.loads(response['body'])
            self.assertIn('message', body)
            self.assertIn('relationship', body)
            
            # Validate database write
            mock_table.put_item.assert_called_once()
        
        print("✓ PASSED: Relationship created successfully")
        print("✓ PASSED: Database write operation executed")
    
    def test_get_relationships_for_user(self):
        """
        Test retrieving relationships for a user.
        
        BUSINESS SCENARIO:
        User wants to see all their relationships (as initiator or participant)
        to understand their legacy connections.
        """
        print("\n" + "="*60)
        print("TEST: Get User Relationships")
        print("="*60)
        print("SCENARIO: User requests their relationship list")
        print("EXPECTED: All relationships returned")
        
        import importlib.util
        get_rel_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/getRelationships/app.py')
        spec = importlib.util.spec_from_file_location("get_rel_app", get_rel_path)
        get_rel_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(get_rel_app)
        
        event = self.create_api_event(
            self.legacy_benefactor,
            query_params={'userId': self.legacy_benefactor['user_id']}
        )
        
        # Mock DynamoDB
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock query responses
            mock_table.query.return_value = {'Items': []}
            
            response = get_rel_app.lambda_handler(event, {})
            
            # Validate successful response
            self.assertEqual(response['statusCode'], 200)
            
            body = json.loads(response['body'])
            self.assertIn('relationships', body)
            self.assertIsInstance(body['relationships'], list)
        
        print("✓ PASSED: Relationships retrieved successfully")
    
    def test_validate_access_between_users(self):
        """
        Test access validation between users.
        
        BUSINESS SCENARIO:
        Before allowing a benefactor to view a maker's content,
        validate that a proper relationship exists between them.
        """
        print("\n" + "="*60)
        print("TEST: Access Validation Between Users")
        print("="*60)
        print("SCENARIO: Validate benefactor access to maker's content")
        print("EXPECTED: Access validation result returned")
        
        import importlib.util
        validate_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/validateAccess/app.py')
        spec = importlib.util.spec_from_file_location("validate_app", validate_path)
        validate_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_app)
        
        event = self.create_api_event(
            self.legacy_benefactor,
            query_params={
                'requestingUserId': self.legacy_benefactor['user_id'],
                'targetUserId': 'maker-789'
            }
        )
        
        # Mock DynamoDB
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock query responses
            mock_table.query.return_value = {'Items': []}
            
            response = validate_app.lambda_handler(event, {})
            
            # Validate response structure
            self.assertEqual(response['statusCode'], 200)
            
            body = json.loads(response['body'])
            self.assertIn('hasAccess', body)
            self.assertIn('reason', body)
        
        print("✓ PASSED: Access validation completed")
        print("✓ PASSED: Validation result structure correct")

class TestErrorHandlingAndEdgeCases(APIEndpointTestSuite):
    """
    Test error handling and edge cases in persona validation.
    
    BUSINESS PURPOSE:
    Robust error handling ensures good user experience and prevents
    security vulnerabilities from unexpected inputs or states.
    """
    
    def test_missing_persona_type_in_jwt(self):
        """
        Test handling of JWT tokens missing persona_type attribute.
        
        BUSINESS SCENARIO:
        User has an old JWT token from before persona system was implemented,
        or there's a configuration issue with custom attributes.
        """
        print("\n" + "="*60)
        print("TEST: Missing Persona Type in JWT")
        print("="*60)
        print("SCENARIO: JWT token missing custom:persona_type attribute")
        print("EXPECTED: Graceful handling with appropriate error")
        
        # Create event with missing persona_type
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'user@example.com'
                        # Missing custom:persona_type
                    }
                }
            }
        }
        
        persona_info = PersonaValidator.get_user_persona_from_jwt(event)
        
        # Should handle missing attribute gracefully
        self.assertEqual(persona_info['persona_type'], '')
        self.assertEqual(persona_info['user_id'], 'user-123')
        
        # Validation should fail appropriately
        is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
        self.assertFalse(is_valid)
        
        print("✓ PASSED: Missing persona_type handled gracefully")
        print("✓ PASSED: Access validation correctly failed")
    
    def test_invalid_persona_type_value(self):
        """
        Test handling of invalid persona_type values.
        
        BUSINESS SCENARIO:
        Database corruption or manual modification results in
        invalid persona_type value in JWT token.
        """
        print("\n" + "="*60)
        print("TEST: Invalid Persona Type Value")
        print("="*60)
        print("SCENARIO: JWT contains invalid persona_type value")
        print("EXPECTED: Access denied with clear error message")
        
        invalid_user = {
            'user_id': 'user-123',
            'persona_type': 'invalid_persona',
            'initiator_id': 'user-123',
            'related_user_id': ''
        }
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(invalid_user)
        
        self.assertFalse(is_valid)
        self.assertIn('Only legacy makers', message)
        self.assertIn('invalid_persona', message)
        
        print("✓ PASSED: Invalid persona type correctly rejected")
        print("✓ PASSED: Error message includes actual persona type for debugging")
    
    def test_missing_user_id_in_jwt(self):
        """
        Test handling of JWT tokens missing user ID.
        
        BUSINESS SCENARIO:
        Malformed or corrupted JWT token missing the 'sub' claim
        which contains the Cognito User ID.
        """
        print("\n" + "="*60)
        print("TEST: Missing User ID in JWT")
        print("="*60)
        print("SCENARIO: JWT token missing 'sub' claim (user ID)")
        print("EXPECTED: Access denied due to missing user identification")
        
        invalid_user = {
            'user_id': None,  # Missing user ID
            'persona_type': 'legacy_maker',
            'initiator_id': 'user-123',
            'related_user_id': ''
        }
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(invalid_user)
        
        self.assertFalse(is_valid)
        self.assertEqual(message, "No user ID found")
        
        print("✓ PASSED: Missing user ID correctly handled")
        print("✓ PASSED: Clear error message for missing user identification")

if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2, buffer=True)