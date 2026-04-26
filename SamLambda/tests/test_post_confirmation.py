"""
Unit tests for PostConfirmation Lambda — subscription record creation.

Tests the subscription record created on new user signup. Does NOT test
the full Lambda handler (persona handling, invite processing, etc.) —
only the subscription record shape and idempotency.

Uses pytest + unittest.mock.
"""
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Mock event builder
# ---------------------------------------------------------------------------

def _make_cognito_event(username='test-user-123', email='test@example.com', persona_type='legacy_maker'):
    """Build a minimal Cognito post-confirmation event."""
    return {
        'version': '1',
        'triggerSource': 'PostConfirmation_ConfirmSignUp',
        'region': 'us-east-1',
        'userPoolId': 'us-east-1_TestPool',
        'userName': username,
        'request': {
            'userAttributes': {
                'sub': username,
                'email': email,
                'email_verified': 'true',
            },
        },
        'response': {},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPostConfirmationSubscription:
    """Tests for the subscription record created on signup."""

    @patch.dict(os.environ, {
        'TABLE_SUBSCRIPTIONS': 'UserSubscriptionsDB',
        'TABLE_SIGNUP_TEMP': 'PersonaSignupTempDB',
        'TABLE_EMAIL_CAPTURE': 'EmailCaptureDB',
    })
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_creates_free_plan_record(self, mock_resource, mock_client):
        """New user signup creates a record with planId=free, status=active."""
        # Setup mocks
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        # PersonaSignupTempDB returns no item (no invite)
        mock_table.get_item.return_value = {}

        # Cognito client mock
        mock_cognito = MagicMock()
        mock_client.return_value = mock_cognito

        # Import after patching to avoid import-time boto3 calls
        # Need to mock the sibling imports
        sys.modules.setdefault('invitation_utils', MagicMock())
        sys.modules.setdefault('logging_utils', MagicMock())

        # Add the function directory to path
        func_dir = os.path.join(
            os.path.dirname(__file__), '..', 'functions', 'cognitoTriggers', 'postConfirmation'
        )
        if func_dir not in sys.path:
            sys.path.insert(0, func_dir)

        # Force reimport to pick up mocks
        if 'app' in sys.modules:
            del sys.modules['app']

        import app
        event = _make_cognito_event(username='new-user-001')
        app.lambda_handler(event, {})

        # Find the put_item call for the subscriptions table
        put_item_calls = mock_table.put_item.call_args_list
        assert len(put_item_calls) >= 1, "Expected at least one put_item call"

        # Find the subscription record call (has planId field)
        sub_call = None
        for c in put_item_calls:
            item = c.kwargs.get('Item', c.args[0] if c.args else {})
            if isinstance(item, dict) and 'planId' in item:
                sub_call = item
                break

        assert sub_call is not None, "No subscription record put_item call found"
        assert sub_call['planId'] == 'free'
        assert sub_call['status'] == 'active'
        assert sub_call['benefactorCount'] == 0
        assert sub_call['level1CompletionPercent'] == 0
        assert sub_call['totalQuestionsCompleted'] == 0
        assert sub_call['userId'] == 'new-user-001'
        assert 'createdAt' in sub_call
        assert 'updatedAt' in sub_call

    @patch.dict(os.environ, {
        'TABLE_SUBSCRIPTIONS': 'UserSubscriptionsDB',
        'TABLE_SIGNUP_TEMP': 'PersonaSignupTempDB',
        'TABLE_EMAIL_CAPTURE': 'EmailCaptureDB',
    })
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_no_trial_fields_in_record(self, mock_resource, mock_client):
        """Record does NOT include trialExpiresAt or status=trialing."""
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        mock_client.return_value = MagicMock()

        sys.modules.setdefault('invitation_utils', MagicMock())
        sys.modules.setdefault('logging_utils', MagicMock())

        func_dir = os.path.join(
            os.path.dirname(__file__), '..', 'functions', 'cognitoTriggers', 'postConfirmation'
        )
        if func_dir not in sys.path:
            sys.path.insert(0, func_dir)
        if 'app' in sys.modules:
            del sys.modules['app']

        import app
        event = _make_cognito_event(username='new-user-002')
        app.lambda_handler(event, {})

        # Find subscription record
        for c in mock_table.put_item.call_args_list:
            item = c.kwargs.get('Item', c.args[0] if c.args else {})
            if isinstance(item, dict) and 'planId' in item:
                assert 'trialExpiresAt' not in item, "trialExpiresAt should not be in record"
                assert item['status'] != 'trialing', "status should not be trialing"
                assert item['planId'] != 'premium', "planId should not be premium for new signup"
                break

    @patch.dict(os.environ, {
        'TABLE_SUBSCRIPTIONS': 'UserSubscriptionsDB',
        'TABLE_SIGNUP_TEMP': 'PersonaSignupTempDB',
        'TABLE_EMAIL_CAPTURE': 'EmailCaptureDB',
    })
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_condition_expression_prevents_overwrite(self, mock_resource, mock_client):
        """put_item includes ConditionExpression to prevent overwriting existing records."""
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}
        mock_client.return_value = MagicMock()

        sys.modules.setdefault('invitation_utils', MagicMock())
        sys.modules.setdefault('logging_utils', MagicMock())

        func_dir = os.path.join(
            os.path.dirname(__file__), '..', 'functions', 'cognitoTriggers', 'postConfirmation'
        )
        if func_dir not in sys.path:
            sys.path.insert(0, func_dir)
        if 'app' in sys.modules:
            del sys.modules['app']

        import app
        event = _make_cognito_event(username='new-user-003')
        app.lambda_handler(event, {})

        # Find the subscription put_item call and verify ConditionExpression
        for c in mock_table.put_item.call_args_list:
            kwargs = c.kwargs if c.kwargs else {}
            item = kwargs.get('Item', {})
            if isinstance(item, dict) and 'planId' in item:
                assert 'ConditionExpression' in kwargs, \
                    "put_item should include ConditionExpression for idempotency"
                assert 'attribute_not_exists' in str(kwargs['ConditionExpression']), \
                    "ConditionExpression should use attribute_not_exists"
                break
