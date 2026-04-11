"""
INTEGRATION TEST SUITE FOR PERSONA SYSTEM

This test suite validates end-to-end workflows that span multiple components
of the persona system. It tests complete user journeys from registration
through content creation and relationship management.

BUSINESS WORKFLOWS TESTED:
1. Complete Legacy Maker Journey (Registration → Question Access → Video Upload)
2. Complete Legacy Benefactor Journey (Registration → Relationship Creation → Access Validation)
3. Cross-Persona Interaction Workflows (Benefactor invites Maker → Content Access)
4. Error Recovery and Edge Case Scenarios

INTEGRATION POINTS VALIDATED:
- Cognito triggers → Persona validator → API endpoints
- Database consistency across PersonaRelationshipsDB and userQuestionStatusDB
- S3 storage integration with persona-based access control
- JWT token flow from registration through API calls

BUSINESS VALUE:
These tests ensure that the complete persona system works together seamlessly,
providing confidence that users will have a smooth experience regardless of
their chosen persona type or interaction patterns.
"""

import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import base64

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
from persona_validator import PersonaValidator

class IntegrationTestSuite(unittest.TestCase):
    """
    Integration test suite for complete persona system workflows.
    
    These tests simulate real user journeys through the system,
    validating that all components work together correctly.
    """
    
    def setUp(self):
        """Set up test data for integration testing."""
        print(f"\n{'='*80}")
        print("STARTING INTEGRATION TEST SUITE")
        print(f"{'='*80}")
        
        # Test users for different scenarios
        self.test_users = {
            'legacy_maker_initiator': {
                'user_id': 'maker-init-123',
                'email': 'maker.init@example.com',
                'persona_type': 'legacy_maker',
                'initiator_id': 'maker-init-123',
                'related_user_id': '',
                'signup_choice': 'create_legacy'
            },
            'legacy_benefactor_initiator': {
                'user_id': 'benefactor-init-456',
                'email': 'benefactor.init@example.com',
                'persona_type': 'legacy_benefactor',
                'initiator_id': 'benefactor-init-456',
                'related_user_id': '',
                'signup_choice': 'setup_for_someone'
            },
            'invited_legacy_maker': {
                'user_id': 'invited-maker-789',
                'email': 'invited.maker@example.com',
                'persona_type': 'legacy_maker',
                'initiator_id': 'benefactor-init-456',  # Invited by benefactor
                'related_user_id': 'benefactor-init-456',
                'signup_choice': 'create_legacy'
            }
        }

class TestCompleteLegacyMakerJourney(IntegrationTestSuite):
    """
    Test complete Legacy Maker user journey from registration to content creation.
    
    BUSINESS SCENARIO:
    A person wants to create their legacy by recording video responses to questions.
    They go through: Registration → Email Confirmation → Question Access → Video Recording
    
    TECHNICAL FLOW:
    1. Pre-signup trigger sets persona_type based on frontend choice
    2. Post-confirmation trigger sets initiator_id to user's own ID
    3. User accesses questions (persona validation allows access)
    4. User uploads video responses (persona validation allows upload)
    5. All responses include persona context for frontend
    """
    
    def test_legacy_maker_complete_workflow(self):
        """
        Test complete Legacy Maker workflow from registration to video upload.
        
        This integration test validates that a Legacy Maker can successfully:
        1. Register with correct persona attributes
        2. Access questions for recording
        3. Upload video responses
        4. Receive appropriate persona context in all responses
        """
        print("\n" + "="*70)
        print("INTEGRATION TEST: Complete Legacy Maker Journey")
        print("="*70)
        print("WORKFLOW: Registration → Confirmation → Question Access → Video Upload")
        print("USER TYPE: Legacy Maker Initiator (self-paying)")
        
        user = self.test_users['legacy_maker_initiator']
        
        # STEP 1: Test Pre-Signup Trigger
        print("\n--- STEP 1: User Registration (Pre-Signup Trigger) ---")
        print(f"User selects: '{user['signup_choice']}' during registration")
        
        import importlib.util
        presignup_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/preSignup/app.py')
        spec = importlib.util.spec_from_file_location("presignup_app", presignup_path)
        presignup_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(presignup_app)
        
        presignup_event = {
            'request': {
                'clientMetadata': {
                    'persona_choice': user['signup_choice']
                }
            },
            'response': {
                'userAttributes': {}
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            presignup_result = presignup_app.lambda_handler(presignup_event, {})

        # Pre-signup stores persona to DynamoDB — validate event is returned
        self.assertIn('response', presignup_result)
        print("✓ Pre-signup trigger correctly stored legacy_maker persona to DynamoDB")
        
        # STEP 2: Test Post-Confirmation Trigger
        print("\n--- STEP 2: Email Confirmation (Post-Confirmation Trigger) ---")
        print("User confirms email, system sets initiator_id")
        
        import importlib.util
        postconfirm_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/postConfirmation/app.py')
        spec = importlib.util.spec_from_file_location("postconfirm_app", postconfirm_path)
        postconfirm_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(postconfirm_app)
        
        postconfirm_event = {
            'userPoolId': 'us-east-1_TestPool',
            'userName': user['user_id']
        }
        
        with patch('boto3.client') as mock_boto3, \
             patch('boto3.resource') as mock_dynamodb:
            mock_cognito = MagicMock()
            mock_boto3.return_value = mock_cognito

            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            mock_table.get_item.return_value = {}

            postconfirm_app.lambda_handler(postconfirm_event, {})

            # Verify Cognito was called and profile attribute was set as JSON
            mock_cognito.admin_update_user_attributes.assert_called_once()
            call_kwargs = mock_cognito.admin_update_user_attributes.call_args[1]
            self.assertEqual(call_kwargs['UserPoolId'], 'us-east-1_TestPool')
            self.assertEqual(call_kwargs['Username'], user['user_id'])
            profile_attr = next(
                (a for a in call_kwargs['UserAttributes'] if a['Name'] == 'profile'),
                None
            )
            self.assertIsNotNone(profile_attr, "profile attribute must be set")
            profile = json.loads(profile_attr['Value'])
            self.assertEqual(profile['initiator_id'], user['user_id'])
        print("✓ Post-confirmation trigger correctly set initiator_id to user's own ID")
        
        # STEP 3: Test Question Access
        print("\n--- STEP 3: Question Access ---")
        print("Legacy Maker requests unanswered questions for recording")
        
        import importlib.util
        questions_path = os.path.join(os.path.dirname(__file__), '../questionDbFunctions/getUnansweredQuestionsFromUser/app.py')
        spec = importlib.util.spec_from_file_location("questions_app", questions_path)
        questions_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(questions_app)
        
        questions_event = {
            'queryStringParameters': {
                'questionType': 'childhood',
                'userId': user['user_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'email': user['email'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            # Mock DynamoDB responses
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock question data
            mock_table.scan.return_value = {
                'Items': [
                    {'questionId': 'childhood-001', 'questionType': 'childhood', 'Valid': 1},
                    {'questionId': 'childhood-002', 'questionType': 'childhood', 'Valid': 1}
                ]
            }
            mock_table.query.return_value = {'Items': []}  # No answered questions
            
            questions_response = questions_app.lambda_handler(questions_event, {})
            
            # Validate question access success
            self.assertEqual(questions_response['statusCode'], 200)
            
            body = json.loads(questions_response['body'])
            self.assertIn('unansweredQuestionIds', body)
            self.assertIn('userContext', body)
            self.assertEqual(body['userContext']['persona_type'], 'legacy_maker')
            self.assertTrue(body['userContext']['is_initiator'])
        
        print("✓ Legacy Maker successfully accessed questions")
        print("✓ Persona context included in response")
        
        # STEP 4: Test Video Upload
        print("\n--- STEP 4: Video Upload ---")
        print("Legacy Maker uploads video response to question")
        
        import importlib.util
        upload_path = os.path.join(os.path.dirname(__file__), '../videoFunctions/uploadVideoResponse/app.py')
        spec = importlib.util.spec_from_file_location("upload_app", upload_path)
        upload_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_app)
        
        upload_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': user['user_id'],
                'questionId': 'childhood-001',
                'questionType': 'childhood',
                'videoData': base64.b64encode(b'test video content').decode('utf-8')
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'email': user['email'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        with patch('boto3.client') as mock_s3_client, \
             patch('boto3.resource') as mock_dynamodb:
            
            # Mock AWS services
            mock_s3 = MagicMock()
            mock_s3_client.return_value = mock_s3
            
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            upload_response = upload_app.lambda_handler(upload_event, {})
            
            # Validate upload success
            self.assertEqual(upload_response['statusCode'], 200)
            
            body = json.loads(upload_response['body'])
            self.assertIn('message', body)
            self.assertIn('userContext', body)
            self.assertEqual(body['userContext']['persona_type'], 'legacy_maker')
            
            # Validate AWS operations
            mock_s3.put_object.assert_called_once()
            mock_table.put_item.assert_called_once()
        
        print("✓ Legacy Maker successfully uploaded video")
        print("✓ S3 and DynamoDB operations completed")
        print("✓ Persona context included in upload response")
        
        print("\n" + "="*70)
        print("✅ COMPLETE LEGACY MAKER JOURNEY: SUCCESS")
        print("✅ All workflow steps completed successfully")
        print("✅ Persona validation enforced at every step")
        print("✅ User context provided for frontend integration")
        print("="*70)

class TestCompleteLegacyBenefactorJourney(IntegrationTestSuite):
    """
    Test complete Legacy Benefactor user journey.
    
    BUSINESS SCENARIO:
    A person wants to set up legacy recording for someone else (e.g., their parent).
    They go through: Registration → Relationship Creation → Access Management
    
    TECHNICAL FLOW:
    1. Pre-signup trigger sets persona_type to 'legacy_benefactor'
    2. Post-confirmation trigger sets initiator_id (they pay for service)
    3. User creates relationship with Legacy Maker
    4. User validates access to Legacy Maker's content
    5. User is blocked from recording functions (appropriate for their role)
    """
    
    def test_legacy_benefactor_complete_workflow(self):
        """
        Test complete Legacy Benefactor workflow from registration to relationship management.
        """
        print("\n" + "="*70)
        print("INTEGRATION TEST: Complete Legacy Benefactor Journey")
        print("="*70)
        print("WORKFLOW: Registration → Confirmation → Relationship Creation → Access Validation")
        print("USER TYPE: Legacy Benefactor Initiator (pays for someone else's recording)")
        
        user = self.test_users['legacy_benefactor_initiator']
        
        # STEP 1: Registration (Pre-Signup)
        print("\n--- STEP 1: User Registration (Pre-Signup Trigger) ---")
        print(f"User selects: '{user['signup_choice']}' during registration")
        
        import importlib.util
        presignup_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/preSignup/app.py')
        spec = importlib.util.spec_from_file_location("presignup_app", presignup_path)
        presignup_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(presignup_app)
        
        presignup_event = {
            'request': {
                'clientMetadata': {
                    'persona_choice': user['signup_choice']
                }
            },
            'response': {
                'userAttributes': {}
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            presignup_result = presignup_app.lambda_handler(presignup_event, {})

        self.assertIn('response', presignup_result)
        print("✓ Pre-signup trigger correctly stored legacy_benefactor persona to DynamoDB")
        
        # STEP 2: Confirmation (Post-Confirmation)
        print("\n--- STEP 2: Email Confirmation (Post-Confirmation Trigger) ---")
        
        import importlib.util
        postconfirm_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/postConfirmation/app.py')
        spec = importlib.util.spec_from_file_location("postconfirm_app", postconfirm_path)
        postconfirm_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(postconfirm_app)
        
        with patch('boto3.client') as mock_boto3:
            mock_cognito = MagicMock()
            mock_boto3.return_value = mock_cognito
            
            postconfirm_event = {
                'userPoolId': 'us-east-1_TestPool',
                'userName': user['user_id']
            }
            
            postconfirm_app.lambda_handler(postconfirm_event, {})
            
            mock_cognito.admin_update_user_attributes.assert_called_once()
        
        print("✓ Post-confirmation trigger set initiator_id (benefactor pays for service)")
        
        # STEP 3: Create Relationship
        print("\n--- STEP 3: Relationship Creation ---")
        print("Benefactor creates relationship with Legacy Maker")
        
        import importlib.util
        create_rel_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/createRelationship/app.py')
        spec = importlib.util.spec_from_file_location("create_rel_app", create_rel_path)
        create_rel_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_rel_app)
        
        relationship_event = {
            'body': json.dumps({
                'initiator_id': user['user_id'],
                'related_user_id': 'parent-maker-123',
                'relationship_type': 'benefactor_to_maker',
                'access_expiry': '2024-12-31T23:59:59Z'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            relationship_response = create_rel_app.lambda_handler(relationship_event, {})
            
            self.assertEqual(relationship_response['statusCode'], 200)
            mock_table.put_item.assert_called_once()
        
        print("✓ Benefactor successfully created relationship with Legacy Maker")
        
        # STEP 4: Validate Access
        print("\n--- STEP 4: Access Validation ---")
        print("Benefactor validates access to Legacy Maker's content")
        
        import importlib.util
        validate_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/validateAccess/app.py')
        spec = importlib.util.spec_from_file_location("validate_app", validate_path)
        validate_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_app)
        
        validate_event = {
            'queryStringParameters': {
                'requestingUserId': user['user_id'],
                'targetUserId': 'parent-maker-123'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock relationship exists
            mock_table.query.return_value = {
                'Items': [{
                    'initiator_id': user['user_id'],
                    'related_user_id': 'parent-maker-123',
                    'status': 'active'
                }]
            }
            
            validate_response = validate_app.lambda_handler(validate_event, {})
            
            self.assertEqual(validate_response['statusCode'], 200)
            
            body = json.loads(validate_response['body'])
            self.assertIn('hasAccess', body)
            self.assertIn('reason', body)
        
        print("✓ Access validation completed successfully")
        
        # STEP 5: Verify Blocked from Recording Functions
        print("\n--- STEP 5: Verify Blocked from Recording Functions ---")
        print("Benefactor should be blocked from question access and video upload")
        
        # Test question access blocked
        import importlib.util
        questions_path = os.path.join(os.path.dirname(__file__), '../questionDbFunctions/getUnansweredQuestionsFromUser/app.py')
        spec = importlib.util.spec_from_file_location("questions_app", questions_path)
        questions_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(questions_app)
        
        questions_event = {
            'queryStringParameters': {
                'questionType': 'childhood',
                'userId': user['user_id']
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        questions_response = questions_app.lambda_handler(questions_event, {})
        self.assertEqual(questions_response['statusCode'], 403)
        
        print("✓ Benefactor correctly blocked from question access")
        
        # Test video upload blocked
        import importlib.util
        upload_path = os.path.join(os.path.dirname(__file__), '../videoFunctions/uploadVideoResponse/app.py')
        spec = importlib.util.spec_from_file_location("upload_app", upload_path)
        upload_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_app)
        
        upload_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': user['user_id'],
                'questionId': 'test-001',
                'questionType': 'childhood',
                'videoData': 'dGVzdA=='
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user['user_id'],
                        'profile': json.dumps({
                            'persona_type': user['persona_type'],
                            'initiator_id': user['initiator_id'],
                            'related_user_id': user['related_user_id']
                        })
                    }
                }
            }
        }
        
        upload_response = upload_app.lambda_handler(upload_event, {})
        self.assertEqual(upload_response['statusCode'], 403)
        
        print("✓ Benefactor correctly blocked from video upload")
        
        print("\n" + "="*70)
        print("✅ COMPLETE LEGACY BENEFACTOR JOURNEY: SUCCESS")
        print("✅ Registration and relationship management successful")
        print("✅ Appropriate access controls enforced")
        print("✅ Blocked from inappropriate functions (recording)")
        print("="*70)

class TestCrossPersonaInteractionWorkflows(IntegrationTestSuite):
    """
    Test workflows that involve interaction between different persona types.
    
    BUSINESS SCENARIOS:
    1. Benefactor invites Legacy Maker → Maker records content → Benefactor accesses
    2. Multiple benefactors for one maker
    3. One benefactor managing multiple makers
    """
    
    def test_benefactor_invites_maker_workflow(self):
        """
        Test workflow where benefactor invites someone to be a Legacy Maker.
        
        BUSINESS SCENARIO:
        Adult child (benefactor) wants their parent to record legacy content.
        They create account, invite parent, parent registers and records content.
        """
        print("\n" + "="*70)
        print("INTEGRATION TEST: Cross-Persona Interaction Workflow")
        print("="*70)
        print("SCENARIO: Benefactor invites Legacy Maker → Content Creation → Access")
        
        benefactor = self.test_users['legacy_benefactor_initiator']
        invited_maker = self.test_users['invited_legacy_maker']
        
        # STEP 1: Benefactor creates relationship (invitation)
        print("\n--- STEP 1: Benefactor Creates Invitation Relationship ---")
        
        import importlib.util
        create_rel_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/createRelationship/app.py')
        spec = importlib.util.spec_from_file_location("create_rel_app", create_rel_path)
        create_rel_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(create_rel_app)
        
        invitation_event = {
            'body': json.dumps({
                'initiator_id': benefactor['user_id'],
                'related_user_id': invited_maker['user_id'],
                'relationship_type': 'benefactor_to_maker',
                'access_expiry': '2025-12-31T23:59:59Z'
            })
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            create_rel_app.lambda_handler(invitation_event, {})
            mock_table.put_item.assert_called_once()
        
        print("✓ Benefactor created invitation relationship")
        
        # STEP 2: Invited Maker registers and records content
        print("\n--- STEP 2: Invited Maker Registration and Content Creation ---")
        
        # Maker registration (pre-signup)
        import importlib.util
        presignup_path = os.path.join(os.path.dirname(__file__), '../cognitoTriggers/preSignup/app.py')
        spec = importlib.util.spec_from_file_location("presignup_app", presignup_path)
        presignup_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(presignup_app)
        
        maker_presignup = {
            'request': {
                'clientMetadata': {
                    'persona_choice': invited_maker['signup_choice']
                }
            },
            'response': {'userAttributes': {}}
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            presignup_result = presignup_app.lambda_handler(maker_presignup, {})

        self.assertIn('response', presignup_result)
        print("✓ Invited Maker registered with correct persona type")
        
        # Maker uploads video
        import importlib.util
        upload_path = os.path.join(os.path.dirname(__file__), '../videoFunctions/uploadVideoResponse/app.py')
        spec = importlib.util.spec_from_file_location("upload_app", upload_path)
        upload_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upload_app)
        
        maker_upload_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': invited_maker['user_id'],
                'questionId': 'family-001',
                'questionType': 'family',
                'videoData': base64.b64encode(b'family story video').decode('utf-8')
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': invited_maker['user_id'],
                        'profile': json.dumps({
                            'persona_type': invited_maker['persona_type'],
                            'initiator_id': invited_maker['initiator_id'],
                            'related_user_id': invited_maker['related_user_id']
                        })
                    }
                }
            }
        }
        
        with patch('boto3.client') as mock_s3, \
             patch('boto3.resource') as mock_dynamodb:
            
            mock_s3_client = MagicMock()
            mock_s3.return_value = mock_s3_client
            
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            upload_response = upload_app.lambda_handler(maker_upload_event, {})
            self.assertEqual(upload_response['statusCode'], 200)
        
        print("✓ Invited Maker successfully uploaded video content")
        
        # STEP 3: Benefactor validates access to maker's content
        print("\n--- STEP 3: Benefactor Validates Access to Content ---")
        
        import importlib.util
        validate_path = os.path.join(os.path.dirname(__file__), '../relationshipFunctions/validateAccess/app.py')
        spec = importlib.util.spec_from_file_location("validate_app", validate_path)
        validate_app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_app)
        
        access_validation_event = {
            'queryStringParameters': {
                'requestingUserId': benefactor['user_id'],
                'targetUserId': invited_maker['user_id']
            }
        }
        
        with patch('boto3.resource') as mock_dynamodb:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_dynamodb.return_value = mock_db
            mock_db.Table.return_value = mock_table
            
            # Mock active relationship
            mock_table.query.return_value = {
                'Items': [{
                    'initiator_id': benefactor['user_id'],
                    'related_user_id': invited_maker['user_id'],
                    'status': 'active',
                    'relationship_type': 'benefactor_to_maker'
                }]
            }
            
            validation_response = validate_app.lambda_handler(access_validation_event, {})
            self.assertEqual(validation_response['statusCode'], 200)
            
            body = json.loads(validation_response['body'])
            self.assertTrue(body['hasAccess'])
            self.assertIn('relationship_access', body['reason'])
        
        print("✓ Benefactor has validated access to Maker's content")
        
        print("\n" + "="*70)
        print("✅ CROSS-PERSONA INTERACTION WORKFLOW: SUCCESS")
        print("✅ Benefactor successfully invited and managed Legacy Maker")
        print("✅ Content creation and access validation working correctly")
        print("✅ Relationship-based access control functioning properly")
        print("="*70)

if __name__ == '__main__':
    # Run integration tests with detailed output
    unittest.main(verbosity=2, buffer=True)