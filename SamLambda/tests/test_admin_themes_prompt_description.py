"""
Unit and property tests for AdminThemes Lambda promptDescription handling.
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5

Tests cover:
- promptDescription included in UpdateExpression when present
- promptDescription omitted from UpdateExpression when absent
- Empty string accepted as valid promptDescription
- Validation rejects strings exceeding 1000 characters
- Boundary tests at exactly 1000 and 1001 characters
- Property 1: promptDescription length validation
"""
import json
import sys
import os
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Import the AdminThemes app module
# ---------------------------------------------------------------------------
_ADMIN_THEMES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'adminFunctions', 'adminThemes')
)
_SHARED_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'shared', 'python')
)

for _d in [_ADMIN_THEMES_DIR, _SHARED_DIR]:
    if _d not in sys.path:
        sys.path.insert(0, _d)

import app as admin_themes_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(question_type='childhood', body=None, admin=True):
    """Build a minimal API Gateway event for the AdminThemes Lambda."""
    event = {
        'httpMethod': 'PUT',
        'pathParameters': {'questionType': question_type},
        'body': json.dumps(body or {}),
        'headers': {'origin': 'https://www.soulreel.net'},
    }
    if admin:
        event['requestContext'] = {
            'authorizer': {
                'claims': {
                    'cognito:groups': 'SoulReelAdmins',
                    'email': 'admin@test.com',
                    'sub': 'admin-sub-1',
                }
            }
        }
    return event


def _mock_dynamodb_resource(items=None):
    """Return a mock boto3 DynamoDB resource with scan and update_item."""
    if items is None:
        items = [{'questionId': 'childhood-1'}, {'questionId': 'childhood-2'}]

    mock_table = MagicMock()
    mock_table.scan.return_value = {'Items': items}
    mock_table.update_item.return_value = {}

    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    return mock_resource, mock_table


# ---------------------------------------------------------------------------
# Unit tests — Task 5.3
# ---------------------------------------------------------------------------

class TestPromptDescriptionIncludedWhenPresent:
    """Test that promptDescription is included in UpdateExpression when present in request body."""

    @patch('app.boto3')
    def test_prompt_description_in_update_expression(self, mock_boto3):
        mock_resource, mock_table = _mock_dynamodb_resource()
        mock_boto3.resource.return_value = mock_resource

        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': 'Focus on early memories',
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 200
        # Verify update_item was called with promptDescription in the expression
        call_kwargs = mock_table.update_item.call_args[1]
        assert 'promptDescription = :pd' in call_kwargs['UpdateExpression']
        assert call_kwargs['ExpressionAttributeValues'][':pd'] == 'Focus on early memories'


class TestPromptDescriptionOmittedWhenAbsent:
    """Test that promptDescription is omitted from UpdateExpression when absent from request body."""

    @patch('app.boto3')
    def test_no_prompt_description_in_update_expression(self, mock_boto3):
        mock_resource, mock_table = _mock_dynamodb_resource()
        mock_boto3.resource.return_value = mock_resource

        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 200
        call_kwargs = mock_table.update_item.call_args[1]
        assert 'promptDescription' not in call_kwargs['UpdateExpression']
        assert ':pd' not in call_kwargs['ExpressionAttributeValues']


class TestEmptyStringAccepted:
    """Test that empty string is accepted as valid promptDescription (clears the description)."""

    @patch('app.boto3')
    def test_empty_string_is_valid(self, mock_boto3):
        mock_resource, mock_table = _mock_dynamodb_resource()
        mock_boto3.resource.return_value = mock_resource

        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': '',
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 200
        call_kwargs = mock_table.update_item.call_args[1]
        assert 'promptDescription = :pd' in call_kwargs['UpdateExpression']
        assert call_kwargs['ExpressionAttributeValues'][':pd'] == ''


class TestPromptDescriptionValidation:
    """Test promptDescription length validation."""

    def test_exceeding_1000_chars_returns_400(self):
        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': 'x' * 1001,
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert 'promptDescription' in response_body['error']
        assert '1000' in response_body['error']

    @patch('app.boto3')
    def test_exactly_1000_chars_accepted(self, mock_boto3):
        mock_resource, mock_table = _mock_dynamodb_resource()
        mock_boto3.resource.return_value = mock_resource

        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': 'x' * 1000,
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 200

    def test_exactly_1001_chars_rejected(self):
        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': 'x' * 1001,
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)

        assert result['statusCode'] == 400
        response_body = json.loads(result['body'])
        assert '1000' in response_body['error']


# ---------------------------------------------------------------------------
# Property test — Task 5.4
# Feature: theme-aware-ai-prompts, Property 1: promptDescription Length Validation
# **Validates: Requirements 1.1, 1.4, 1.5**
# ---------------------------------------------------------------------------

from hypothesis import given, settings as h_settings, HealthCheck
import hypothesis.strategies as st


@given(s=st.text(min_size=0, max_size=2000))
@h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_property_prompt_description_length_validation(s):
    """Property 1: promptDescription Length Validation.

    For any string s, the validation logic SHALL accept s if and only if
    len(s) <= 1000; strings longer than 1000 SHALL be rejected with 400.

    **Validates: Requirements 1.1, 1.4, 1.5**
    """
    # We test the validation logic directly rather than calling the full handler,
    # to avoid needing DynamoDB mocks for the acceptance path.
    # The validation logic is: if prompt_description is not None and len(prompt_description) > 1000
    prompt_description = s
    should_reject = len(prompt_description) > 1000

    if should_reject:
        # Calling the handler should return 400 before any DynamoDB writes
        body = {
            'requiredLifeEvents': [],
            'isInstanceable': False,
            'instancePlaceholder': '',
            'promptDescription': prompt_description,
        }
        event = _make_event(body=body)
        result = admin_themes_app.lambda_handler(event, None)
        assert result['statusCode'] == 400, f"Expected 400 for len={len(s)}, got {result['statusCode']}"
        response_body = json.loads(result['body'])
        assert '1000' in response_body['error']
    else:
        # For accepted strings, we verify the validation does NOT reject.
        # We need to mock DynamoDB since the handler will proceed to scan/update.
        with patch('app.boto3') as mock_boto3:
            mock_resource, _ = _mock_dynamodb_resource()
            mock_boto3.resource.return_value = mock_resource

            body = {
                'requiredLifeEvents': [],
                'isInstanceable': False,
                'instancePlaceholder': '',
                'promptDescription': prompt_description,
            }
            event = _make_event(body=body)
            result = admin_themes_app.lambda_handler(event, None)
            assert result['statusCode'] == 200, f"Expected 200 for len={len(s)}, got {result['statusCode']}"
