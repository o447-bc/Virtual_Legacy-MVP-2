"""
Property-based tests for CORS headers on ListPsychTests Lambda responses.

Feature: psych-test-framework, Property 17: CORS headers on all responses

Tests that every response from the ListPsychTests Lambda handler includes
the correct Access-Control-Allow-Origin header, regardless of the request
path, method, or whether the request succeeds or fails.

Uses hypothesis for property-based testing.

**Validates: Requirements 11.2**
"""
import json
import os
import sys
from unittest.mock import patch, MagicMock
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

# ---------------------------------------------------------------------------
# Ensure shared layer modules are importable in test environment
# ---------------------------------------------------------------------------
_SAMLAMBDA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_SHARED_PYTHON = os.path.join(_SAMLAMBDA_ROOT, 'functions', 'shared', 'python')
_LAMBDA_DIR = os.path.join(
    _SAMLAMBDA_ROOT, 'functions', 'psychTestFunctions', 'listPsychTests'
)

for _p in [_SHARED_PYTHON, _LAMBDA_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Set ALLOWED_ORIGIN before importing the handler
_TEST_ORIGIN = 'https://www.soulreel.net'
os.environ.setdefault('ALLOWED_ORIGIN', _TEST_ORIGIN)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

http_method_strategy = st.sampled_from([
    'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'HEAD',
])

path_strategy = st.sampled_from([
    '/psych-tests/list',
    '/psych-tests/ipip-neo-60',
    '/psych-tests/oejts',
    '/psych-tests/nonexistent-test',
    '/psych-tests/',
    '/unknown/path',
    '/psych-tests/list/extra',
    '',
])

user_id_strategy = st.one_of(
    st.just(None),
    st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
        min_size=5, max_size=40,
    ),
)

origin_strategy = st.sampled_from([
    'https://www.soulreel.net',
    'https://soulreel.net',
    'http://localhost:5173',
    'http://evil.example.com',
    '',
])


def _build_event(http_method, path, user_id, origin):
    """Build a minimal API Gateway proxy event."""
    event = {
        'httpMethod': http_method,
        'path': path,
        'headers': {'origin': origin} if origin else {},
        'requestContext': {},
        'pathParameters': None,
        'body': None,
    }
    if user_id:
        event['requestContext'] = {
            'authorizer': {
                'claims': {'sub': user_id}
            }
        }
    # Extract testId from path for /psych-tests/{testId} routes
    if path.startswith('/psych-tests/') and path != '/psych-tests/list':
        parts = path.rstrip('/').split('/')
        if len(parts) == 3 and parts[2]:
            event['pathParameters'] = {'testId': parts[2]}
    return event


# ===================================================================
# Property 17: CORS headers on all responses
# ===================================================================
# Feature: psych-test-framework, Property 17: CORS headers on all responses
# **Validates: Requirements 11.2**

class TestCorsHeadersOnAllResponses:
    """Property 17: Every Lambda response includes Access-Control-Allow-Origin."""

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        http_method=http_method_strategy,
        path=path_strategy,
        user_id=user_id_strategy,
        origin=origin_strategy,
    )
    @patch('app.boto3')
    def test_cors_header_present_on_all_responses(
        self, mock_boto3, http_method, path, user_id, origin
    ):
        """
        For any combination of HTTP method, path, user ID (or missing),
        and origin header, the response MUST include Access-Control-Allow-Origin.
        """
        # Mock DynamoDB and S3 to avoid real AWS calls
        mock_dynamodb = MagicMock()
        mock_s3 = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_boto3.client.return_value = mock_s3

        # Mock DynamoDB table query responses
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        mock_dynamodb.Table.return_value = mock_table

        # Mock S3 get_object to return a valid test definition
        mock_s3.get_object.return_value = {
            'Body': MagicMock(
                read=MagicMock(return_value=json.dumps({
                    'testId': 'test-1',
                    'testName': 'Test',
                }).encode('utf-8'))
            )
        }

        event = _build_event(http_method, path, user_id, origin)

        # Re-import to pick up mocked boto3
        import importlib
        import app as handler_module
        importlib.reload(handler_module)

        response = handler_module.lambda_handler(event, {})

        # PROPERTY: Every response must have headers with Access-Control-Allow-Origin
        assert 'headers' in response, (
            f'Response missing headers dict for {http_method} {path}'
        )
        headers = response['headers']
        assert 'Access-Control-Allow-Origin' in headers, (
            f'Response missing Access-Control-Allow-Origin for {http_method} {path}'
        )

        # The origin should be from the allowed list or the default
        allowed_origins = [
            'https://www.soulreel.net',
            'https://soulreel.net',
            'http://localhost:5173',
            'http://localhost:8080',
        ]
        actual_origin = headers['Access-Control-Allow-Origin']
        assert actual_origin in allowed_origins, (
            f'Unexpected origin {actual_origin} for {http_method} {path}'
        )
