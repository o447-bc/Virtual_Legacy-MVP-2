"""
Unit tests for PostConfirmation trigger enhancement to handle assignment invitations.

Tests verify that the trigger correctly:
1. Processes maker-initiated assignment invitations
2. Links new user registrations to pending assignments
3. Sends assignment notification emails
4. Maintains backward compatibility with benefactor-initiated invites

Requirements: 6.4, 6.5
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the lambda handler
from functions.cognitoTriggers.postConfirmation.app import (
    lambda_handler,
    send_assignment_notification_to_new_user,
    format_access_conditions_html
)


class TestPostConfirmationAssignmentInvitations:
    """Test suite for assignment invitation handling in PostConfirmation trigger"""
    
    @patch('functions.cognitoTriggers.postConfirmation.app.boto3')
    @patch('functions.cognitoTriggers.postConfirmation.app.link_registration_to_assignment')
    def test_maker_assignment_invitation_success(self, mock_link_registration, mock_boto3):
        """
        Test successful processing of maker-initiated assignment invitation.
        
        Verifies:
        - Invitation token is retrieved and validated
        - link_registration_to_assignment is called with correct parameters
        - Assignment notification email is sent
        - User attributes are updated
        
        Requirements: 6.4, 6.5
        """
        # Setup mock event
        event = {
            'userPoolId': 'us-east-1_test123',
            'userName': 'new-user-id-123',
            'request': {
                'userAttributes': {
                    'email': 'benefactor@example.com'
                }
            }
        }
        
        # Setup mock DynamoDB responses
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        
        mock_temp_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_temp_table
        
        # Mock persona data retrieval
        mock_temp_table.get_item.side_effect = [
            # First call: get persona data for username
            {
                'Item': {
                    'userName': 'new-user-id-123',
                    'persona_type': 'legacy_benefactor',
                    'invite_token': 'invite-token-456',
                    'first_name': 'John',
                    'last_name': 'Doe'
                }
            },
            # Second call: get invite data for token
            {
                'Item': {
                    'userName': 'invite-token-456',
                    'invite_type': 'maker_assignment',
                    'initiator_id': 'legacy-maker-789',
                    'benefactor_email': 'benefactor@example.com',
                    'assignment_details': {
                        'access_conditions': [
                            {'condition_type': 'immediate'}
                        ]
                    }
                }
            }
        ]
        
        # Mock link_registration_to_assignment success
        mock_link_registration.return_value = (True, {
            'relationship_created': True,
            'initiator_id': 'legacy-maker-789',
            'related_user_id': 'new-user-id-123',
            'access_conditions_created': 1
        })
        
        # Mock Cognito client
        mock_cognito = MagicMock()
        mock_boto3.client.return_value = mock_cognito
        
        # Mock SES for email sending
        mock_ses = MagicMock()
        
        def client_side_effect(service, **kwargs):
            if service == 'cognito-idp':
                return mock_cognito
            elif service == 'ses':
                return mock_ses
            return MagicMock()
        
        mock_boto3.client.side_effect = client_side_effect
        
        # Execute lambda handler
        result = lambda_handler(event, None)
        
        # Verify link_registration_to_assignment was called
        mock_link_registration.assert_called_once_with(
            invite_token='invite-token-456',
            new_user_id='new-user-id-123',
            user_email='benefactor@example.com'
        )
        
        # Verify user attributes were updated
        mock_cognito.admin_update_user_attributes.assert_called_once()
        
        # Verify event is returned unchanged
        assert result == event
    
    @patch('functions.cognitoTriggers.postConfirmation.app.boto3')
    @patch('functions.cognitoTriggers.postConfirmation.app.link_registration_to_assignment')
    def test_benefactor_invite_backward_compatibility(self, mock_link_registration, mock_boto3):
        """
        Test backward compatibility with existing benefactor-initiated invites.
        
        Verifies:
        - Old benefactor invite flow still works
        - link_registration_to_assignment is NOT called for old invites
        - create_benefactor_relationship is called instead
        
        Requirements: 6.4
        """
        # Setup mock event
        event = {
            'userPoolId': 'us-east-1_test123',
            'userName': 'new-maker-id-456',
            'request': {
                'userAttributes': {
                    'email': 'maker@example.com'
                }
            }
        }
        
        # Setup mock DynamoDB
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        
        mock_temp_table = MagicMock()
        mock_relationships_table = MagicMock()
        
        def table_side_effect(table_name):
            if table_name == 'PersonaSignupTempDB':
                return mock_temp_table
            elif table_name == 'PersonaRelationshipsDB':
                return mock_relationships_table
            return MagicMock()
        
        mock_dynamodb.Table.side_effect = table_side_effect
        
        # Mock persona data with old-style benefactor invite
        mock_temp_table.get_item.side_effect = [
            # First call: get persona data
            {
                'Item': {
                    'userName': 'new-maker-id-456',
                    'persona_type': 'legacy_maker',
                    'invite_token': 'old-invite-token-789'
                }
            },
            # Second call: get old-style invite data
            {
                'Item': {
                    'userName': 'old-invite-token-789',
                    'benefactor_id': 'benefactor-123',
                    'invitee_email': 'maker@example.com'
                    # No invite_type field (old format)
                }
            }
        ]
        
        # Mock Cognito client
        mock_cognito = MagicMock()
        mock_boto3.client.return_value = mock_cognito
        
        # Execute lambda handler
        result = lambda_handler(event, None)
        
        # Verify link_registration_to_assignment was NOT called
        mock_link_registration.assert_not_called()
        
        # Verify old relationship creation was called
        mock_relationships_table.put_item.assert_called_once()
        call_args = mock_relationships_table.put_item.call_args
        assert call_args[1]['Item']['initiator_id'] == 'benefactor-123'
        assert call_args[1]['Item']['related_user_id'] == 'new-maker-id-456'
        
        # Verify event is returned
        assert result == event
    
    def test_format_access_conditions_html(self):
        """
        Test HTML formatting of access conditions for email display.
        
        Verifies all condition types are formatted correctly.
        """
        conditions = [
            {'condition_type': 'immediate'},
            {'condition_type': 'time_delayed', 'activation_date': '2026-12-31T00:00:00Z'},
            {'condition_type': 'inactivity_trigger', 'inactivity_months': 6},
            {'condition_type': 'manual_release'}
        ]
        
        html = format_access_conditions_html(conditions)
        
        # Verify all condition types are present
        assert 'Immediate Access' in html
        assert 'Time-Delayed Access' in html
        assert '2026-12-31T00:00:00Z' in html
        assert 'Inactivity Trigger' in html
        assert '6 months' in html
        assert 'Manual Release' in html
        assert '<ul>' in html
        assert '</ul>' in html
    
    def test_format_access_conditions_html_empty(self):
        """Test HTML formatting with no access conditions"""
        html = format_access_conditions_html([])
        assert 'No specific access conditions' in html
    
    @patch('functions.cognitoTriggers.postConfirmation.app.boto3')
    def test_send_assignment_notification_success(self, mock_boto3):
        """
        Test successful sending of assignment notification email.
        
        Verifies:
        - Access conditions are queried from database
        - Email is sent via SES with correct content
        
        Requirements: 6.5
        """
        # Setup mocks
        mock_dynamodb = MagicMock()
        mock_ses = MagicMock()
        
        def resource_or_client(service, **kwargs):
            if service == 'dynamodb':
                return mock_dynamodb
            elif service == 'ses':
                return mock_ses
            return MagicMock()
        
        mock_boto3.resource.side_effect = resource_or_client
        mock_boto3.client.side_effect = resource_or_client
        
        # Mock access conditions table
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        mock_table.query.return_value = {
            'Items': [
                {'condition_type': 'immediate'},
                {'condition_type': 'time_delayed', 'activation_date': '2026-12-31'}
            ]
        }
        
        # Call function
        result = send_assignment_notification_to_new_user(
            benefactor_email='test@example.com',
            initiator_id='maker-123',
            new_user_id='benefactor-456'
        )
        
        # Verify success
        assert result is True
        
        # Verify SES send_email was called
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args
        
        # Verify email content
        assert call_args[1]['Destination']['ToAddresses'] == ['test@example.com']
        assert 'Welcome to Virtual Legacy' in call_args[1]['Message']['Subject']['Data']
        assert 'Immediate Access' in call_args[1]['Message']['Body']['Html']['Data']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
