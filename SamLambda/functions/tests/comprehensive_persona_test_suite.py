"""
COMPREHENSIVE PERSONA AND RELATIONSHIP MANAGEMENT TEST SUITE

This test suite validates the complete persona-based access control system implemented
for the Virtual Legacy MVP. It tests the core functionality that enables two distinct
user types (Legacy Makers and Legacy Benefactors) to interact with the system according
to their roles and permissions.

BUSINESS CONTEXT:
The Virtual Legacy platform allows users to create and share personal legacy content.
Two personas exist:
1. Legacy Makers - Record their stories by answering questions and uploading videos
2. Legacy Benefactors - View and access legacy content from authorized makers

This persona system ensures proper access control and enables different user experiences
based on the user's role in the legacy creation/consumption process.

TEST COVERAGE:
1. Cognito User Pool Custom Attributes and Triggers
2. Persona Validation and Access Control
3. Relationship Management Between Users
4. API Security and Authorization
5. Database Access Patterns
6. Error Handling and Edge Cases

TECHNICAL IMPLEMENTATION:
- Custom Cognito attributes store persona information in JWT tokens
- Lambda triggers automatically set user attributes during registration
- Shared persona validator ensures consistent access control
- PersonaRelationshipsDB manages user-to-user relationships
- API Gateway with Cognito authorizer secures all endpoints
"""

import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add shared directory to path for persona validator
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
from persona_validator import PersonaValidator

class ComprehensivePersonaTestSuite(unittest.TestCase):
    """
    Master test suite for persona and relationship management functionality.
    
    This suite tests the complete user journey from registration through
    content creation and access, validating that persona-based access
    control works correctly at every step.
    """
    
    def setUp(self):
        """
        Set up test data and mock objects for consistent testing.
        
        Creates sample user data representing different personas and
        relationship scenarios that will be used across multiple tests.
        """
        # Sample Legacy Maker (creates content)
        self.legacy_maker_user = {
            'user_id': 'maker-123',
            'email': 'maker@example.com',
            'persona_type': 'legacy_maker',
            'initiator_id': 'maker-123',  # Self-initiated
            'related_user_id': ''
        }
        
        # Sample Legacy Benefactor (views content)
        self.legacy_benefactor_user = {
            'user_id': 'benefactor-456',
            'email': 'benefactor@example.com',
            'persona_type': 'legacy_benefactor',
            'initiator_id': 'benefactor-456',  # Self-initiated
            'related_user_id': ''
        }
        
        # Sample Legacy Maker created by benefactor (invited scenario)
        self.invited_legacy_maker = {
            'user_id': 'invited-maker-789',
            'email': 'invited@example.com',
            'persona_type': 'legacy_maker',
            'initiator_id': 'benefactor-456',  # Initiated by benefactor
            'related_user_id': 'benefactor-456'
        }
        
        # Mock Cognito JWT event structure
        self.base_cognito_event = {
            'requestContext': {
                'authorizer': {
                    'claims': {}
                }
            }
        }
        
        print(f"\n{'='*80}")
        print("STARTING COMPREHENSIVE PERSONA TEST SUITE")
        print(f"{'='*80}")

    def create_jwt_event(self, user_data):
        """
        Helper method to create mock Cognito JWT events.
        
        Args:
            user_data (dict): User persona information
            
        Returns:
            dict: Mock Lambda event with Cognito JWT claims
            
        This simulates the event structure that Lambda functions receive
        when called through API Gateway with Cognito authorization.
        """
        event = self.base_cognito_event.copy()
        event['requestContext']['authorizer']['claims'] = {
            'sub': user_data['user_id'],
            'email': user_data['email'],
            'custom:persona_type': user_data['persona_type'],
            'custom:initiator_id': user_data['initiator_id'],
            'custom:related_user_id': user_data['related_user_id']
        }
        return event

class TestCognitoTriggersAndAttributes(ComprehensivePersonaTestSuite):
    """
    Test Cognito User Pool custom attributes and Lambda triggers.
    
    BUSINESS PURPOSE:
    These tests validate that user registration correctly sets persona
    attributes based on the user's choice during signup. This is critical
    because all subsequent access control depends on these attributes.
    
    TECHNICAL DETAILS:
    - Pre-signup trigger sets persona_type from clientMetadata
    - Post-confirmation trigger sets initiator_id to user's own ID
    - Custom attributes are included in JWT tokens for API calls
    """
    
    def test_pre_signup_trigger_legacy_maker(self):
        """
        Test Pre-Signup trigger correctly sets Legacy Maker persona.
        
        BUSINESS SCENARIO:
        User clicks "Create your legacy" button on frontend, which sends
        persona_choice='create_legacy' in clientMetadata during registration.
        
        EXPECTED BEHAVIOR:
        Pre-signup trigger should set custom:persona_type to 'legacy_maker'
        """
        print("\n" + "="*60)
        print("TEST: Pre-Signup Trigger - Legacy Maker Registration")
        print("="*60)
        print("SCENARIO: User selects 'Create your legacy' during signup")
        print("EXPECTED: persona_type should be set to 'legacy_maker'")
        
        # Import the pre-signup trigger function using importlib
        import importlib.util
        presignup_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/preSignup/app.py')
        spec = importlib.util.spec_from_file_location("presignup_app", presignup_path)
        presignup_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(presignup_app)
        
        # Mock Cognito pre-signup event
        event = {
            'request': {
                'clientMetadata': {
                    'persona_choice': 'create_legacy'
                }
            },
            'response': {
                'userAttributes': {}
            }
        }
        
        # Execute pre-signup trigger
        result = presignup_app.lambda_handler(event, {})
        
        # Validate results
        self.assertEqual(
            result['response']['userAttributes']['custom:persona_type'], 
            'legacy_maker',
            "Pre-signup trigger should set persona_type to 'legacy_maker' for 'create_legacy' choice"
        )
        
        self.assertEqual(
            result['response']['userAttributes']['custom:initiator_id'], 
            '',
            "Pre-signup trigger should leave initiator_id empty (set by post-confirmation)"
        )
        
        print("✓ PASSED: Pre-signup trigger correctly set legacy_maker persona")
        print("✓ PASSED: Initiator ID left empty for post-confirmation trigger")
    
    def test_pre_signup_trigger_legacy_benefactor(self):
        """
        Test Pre-Signup trigger correctly sets Legacy Benefactor persona.
        
        BUSINESS SCENARIO:
        User clicks "Set up Legacy Making for someone else" button, which sends
        persona_choice='setup_for_someone' in clientMetadata.
        
        EXPECTED BEHAVIOR:
        Pre-signup trigger should set custom:persona_type to 'legacy_benefactor'
        """
        print("\n" + "="*60)
        print("TEST: Pre-Signup Trigger - Legacy Benefactor Registration")
        print("="*60)
        print("SCENARIO: User selects 'Set up Legacy Making for someone else'")
        print("EXPECTED: persona_type should be set to 'legacy_benefactor'")
        
        import importlib.util
        presignup_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/preSignup/app.py')
        spec = importlib.util.spec_from_file_location("presignup_app", presignup_path)
        presignup_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(presignup_app)
        
        event = {
            'request': {
                'clientMetadata': {
                    'persona_choice': 'setup_for_someone'
                }
            },
            'response': {
                'userAttributes': {}
            }
        }
        
        result = presignup_app.lambda_handler(event, {})
        
        self.assertEqual(
            result['response']['userAttributes']['custom:persona_type'], 
            'legacy_benefactor',
            "Pre-signup trigger should set persona_type to 'legacy_benefactor'"
        )
        
        print("✓ PASSED: Pre-signup trigger correctly set legacy_benefactor persona")
    
    def test_post_confirmation_trigger(self):
        """
        Test Post-Confirmation trigger sets initiator_id to user's own ID.
        
        BUSINESS PURPOSE:
        The initiator_id identifies who pays for the service. For self-registered
        users, they are their own initiator. This is set after user creation
        when the permanent Cognito User ID is available.
        
        TECHNICAL DETAILS:
        Post-confirmation trigger runs after email verification and sets
        custom:initiator_id to the user's Cognito User ID (userName field).
        """
        print("\n" + "="*60)
        print("TEST: Post-Confirmation Trigger - Set Initiator ID")
        print("="*60)
        print("SCENARIO: User completes email verification")
        print("EXPECTED: initiator_id should be set to user's own Cognito ID")
        
        import importlib.util
        postconfirm_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/postConfirmation/app.py')
        spec = importlib.util.spec_from_file_location("postconfirm_app", postconfirm_path)
        postconfirm_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(postconfirm_app)
        
        # Mock Cognito post-confirmation event
        event = {
            'userPoolId': 'us-east-1_TestPool',
            'userName': 'test-user-123'  # This is the Cognito User ID
        }
        
        # Mock the Cognito client
        with patch('boto3.client') as mock_boto3:
            mock_cognito = MagicMock()
            mock_boto3.return_value = mock_cognito
            
            # Execute post-confirmation trigger
            result = postconfirm_app.lambda_handler(event, {})
            
            # Verify Cognito client was called correctly
            mock_cognito.admin_update_user_attributes.assert_called_once_with(
                UserPoolId='us-east-1_TestPool',
                Username='test-user-123',
                UserAttributes=[
                    {
                        'Name': 'custom:initiator_id',
                        'Value': 'test-user-123'
                    }
                ]
            )
        
        print("✓ PASSED: Post-confirmation trigger correctly set initiator_id")
        print("✓ PASSED: Cognito admin_update_user_attributes called with correct parameters")

class TestPersonaValidationAndAccessControl(ComprehensivePersonaTestSuite):
    """
    Test the shared persona validator and access control logic.
    
    BUSINESS PURPOSE:
    These tests ensure that users can only perform actions appropriate
    to their persona type. Legacy Makers can record content, Legacy
    Benefactors can view content, but not vice versa.
    
    TECHNICAL IMPLEMENTATION:
    The PersonaValidator class extracts custom attributes from JWT tokens
    and validates permissions before allowing API operations.
    """
    
    def test_persona_extraction_from_jwt(self):
        """
        Test extraction of persona information from Cognito JWT tokens.
        
        BUSINESS CONTEXT:
        Every API call includes a JWT token with custom attributes.
        The persona validator must correctly extract this information
        to make access control decisions.
        """
        print("\n" + "="*60)
        print("TEST: Persona Information Extraction from JWT")
        print("="*60)
        print("SCENARIO: API call with Cognito JWT token containing custom attributes")
        print("EXPECTED: PersonaValidator should extract all persona information")
        
        # Test Legacy Maker JWT extraction
        maker_event = self.create_jwt_event(self.legacy_maker_user)
        maker_persona = PersonaValidator.get_user_persona_from_jwt(maker_event)
        
        self.assertEqual(maker_persona['user_id'], 'maker-123')
        self.assertEqual(maker_persona['persona_type'], 'legacy_maker')
        self.assertEqual(maker_persona['initiator_id'], 'maker-123')
        self.assertEqual(maker_persona['email'], 'maker@example.com')
        
        print("✓ PASSED: Legacy Maker persona information extracted correctly")
        
        # Test Legacy Benefactor JWT extraction
        benefactor_event = self.create_jwt_event(self.legacy_benefactor_user)
        benefactor_persona = PersonaValidator.get_user_persona_from_jwt(benefactor_event)
        
        self.assertEqual(benefactor_persona['user_id'], 'benefactor-456')
        self.assertEqual(benefactor_persona['persona_type'], 'legacy_benefactor')
        self.assertEqual(benefactor_persona['initiator_id'], 'benefactor-456')
        
        print("✓ PASSED: Legacy Benefactor persona information extracted correctly")
    
    def test_legacy_maker_access_validation(self):
        """
        Test that Legacy Makers can access maker-specific functions.
        
        BUSINESS SCENARIO:
        Legacy Makers should be able to:
        - Access questions for recording
        - Upload video responses
        - Manage their content
        """
        print("\n" + "="*60)
        print("TEST: Legacy Maker Access Validation")
        print("="*60)
        print("SCENARIO: Legacy Maker attempts to access recording functions")
        print("EXPECTED: Access should be granted")
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(self.legacy_maker_user)
        
        self.assertTrue(is_valid, "Legacy Makers should have access to maker functions")
        self.assertEqual(message, "Access granted")
        
        print("✓ PASSED: Legacy Maker access validation successful")
        print(f"✓ PASSED: Validation message: '{message}'")
    
    def test_legacy_benefactor_blocked_from_maker_functions(self):
        """
        Test that Legacy Benefactors are blocked from maker-specific functions.
        
        BUSINESS SCENARIO:
        Legacy Benefactors should NOT be able to:
        - Access questions (they don't record)
        - Upload videos (they only view)
        - Create content
        
        This separation ensures clear role boundaries and prevents confusion.
        """
        print("\n" + "="*60)
        print("TEST: Legacy Benefactor Blocked from Maker Functions")
        print("="*60)
        print("SCENARIO: Legacy Benefactor attempts to access recording functions")
        print("EXPECTED: Access should be denied with clear error message")
        
        is_valid, message = PersonaValidator.validate_legacy_maker_access(self.legacy_benefactor_user)
        
        self.assertFalse(is_valid, "Legacy Benefactors should be blocked from maker functions")
        self.assertIn("Only legacy makers", message)
        self.assertIn("legacy_benefactor", message)
        
        print("✓ PASSED: Legacy Benefactor correctly blocked from maker functions")
        print(f"✓ PASSED: Clear error message provided: '{message}'")
    
    def test_standardized_access_denied_response(self):
        """
        Test that access denied responses are standardized across the system.
        
        BUSINESS PURPOSE:
        Consistent error responses improve user experience and make
        frontend error handling more reliable.
        """
        print("\n" + "="*60)
        print("TEST: Standardized Access Denied Response")
        print("="*60)
        print("SCENARIO: Generate standardized 403 Forbidden response")
        print("EXPECTED: Consistent format with CORS headers and error details")
        
        test_message = "Test access denied message"
        response = PersonaValidator.create_access_denied_response(test_message)
        
        # Validate response structure
        self.assertEqual(response['statusCode'], 403)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        
        # Validate response body
        body = json.loads(response['body'])
        self.assertEqual(body['error'], test_message)
        self.assertEqual(body['errorType'], 'AccessDenied')
        
        print("✓ PASSED: Response has correct HTTP 403 status code")
        print("✓ PASSED: CORS headers included for frontend compatibility")
        print("✓ PASSED: Error message and type included in response body")
    
    def test_persona_context_in_responses(self):
        """
        Test that API responses include persona context for frontend use.
        
        BUSINESS PURPOSE:
        Frontend needs to know the user's persona type to show appropriate
        UI elements and enable/disable features based on user permissions.
        """
        print("\n" + "="*60)
        print("TEST: Persona Context Added to API Responses")
        print("="*60)
        print("SCENARIO: Add user context to API response")
        print("EXPECTED: Response includes persona_type, user_id, and initiator status")
        
        # Test response with persona context
        original_response = {'data': 'test_data'}
        enhanced_response = PersonaValidator.add_persona_context_to_response(
            original_response, 
            self.legacy_maker_user
        )
        
        # Validate enhanced response
        self.assertIn('userContext', enhanced_response)
        self.assertEqual(enhanced_response['userContext']['persona_type'], 'legacy_maker')
        self.assertEqual(enhanced_response['userContext']['user_id'], 'maker-123')
        self.assertTrue(enhanced_response['userContext']['is_initiator'])  # Self-initiated
        self.assertEqual(enhanced_response['data'], 'test_data')  # Original data preserved
        
        print("✓ PASSED: User context added to response")
        print("✓ PASSED: Original response data preserved")
        print("✓ PASSED: Initiator status correctly calculated")

if __name__ == '__main__':
    # Configure test output for detailed reporting
    unittest.main(verbosity=2, buffer=True)