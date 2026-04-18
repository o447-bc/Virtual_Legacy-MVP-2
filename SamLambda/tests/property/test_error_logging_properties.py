"""
Property-based tests for the Structured Logger.

Feature: error-logging-monitoring
Property 1: ERROR-level log entries contain all required fields
Property 2: INFO-level log entries contain all required fields
Property 3: PII redaction removes all PII patterns from log data
Property 4: Correlation ID propagation
Property 11: AWS SDK error logging includes error code and redacted params

**Validates: Requirements 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 4.2, 8.1, 8.2, 8.3**
"""
import json
import os
import sys
import re
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings as h_settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Path setup — add shared layer to path
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from structured_logger import StructuredLog, redact_pii

# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

# Generate realistic email addresses
email_st = st.from_regex(
    r'[a-zA-Z][a-zA-Z0-9_.+\-]{0,20}@[a-zA-Z][a-zA-Z0-9\-]{1,10}\.[a-zA-Z]{2,5}',
    fullmatch=True,
)

# Known PII field names
pii_field_names_st = st.sampled_from([
    'email', 'phone', 'phonenumber', 'phone_number', 'phoneNumber',
    'name', 'fullname', 'full_name', 'fullName',
    'firstName', 'first_name', 'lastname', 'last_name', 'lastName',
    'address', 'ssn', 'dateOfBirth', 'date_of_birth',
])

# Non-PII field names
safe_field_names_st = st.sampled_from([
    'testId', 'userId', 'operation', 'status', 'count',
    'timestamp', 'version', 'correlationId', 'level',
    'tableName', 'bucketName', 'key', 'method',
])

# Generate Lambda event dicts with optional JWT claims
def make_event(user_id='', correlation_id='', http_method='GET', path='/test', body=None):
    event = {
        'httpMethod': http_method,
        'path': path,
        'resource': path,
        'headers': {},
        'requestContext': {
            'authorizer': {
                'claims': {}
            }
        },
    }
    if user_id:
        event['requestContext']['authorizer']['claims']['sub'] = user_id
    if correlation_id:
        event['headers']['X-Correlation-ID'] = correlation_id
    if body is not None:
        event['body'] = json.dumps(body) if isinstance(body, dict) else body
    return event


def make_context(function_name='TestFunction', memory_mb=128):
    ctx = MagicMock()
    ctx.function_name = function_name
    ctx.memory_limit_in_mb = memory_mb
    return ctx


# ===========================================================================
# Property 3: PII redaction removes all PII patterns from log data
# Feature: error-logging-monitoring, Property 3
# Validates: Requirements 1.5
# ===========================================================================

class TestPIIRedaction:
    """Property 3: PII redaction removes all PII patterns from log data."""

    @given(email=email_st)
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_emails_redacted_from_string_values(self, email):
        """Any string containing an email address must have it redacted."""
        data = {'message': f'Error for user {email} in processing'}
        result = redact_pii(data)
        assert email not in result['message'], (
            f'Email {email!r} was not redacted from string value'
        )
        assert '[REDACTED_EMAIL]' in result['message']

    @given(email=email_st)
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_emails_redacted_as_standalone_values(self, email):
        """An email as a dict value must be redacted."""
        data = {'contact': email}
        result = redact_pii(data)
        assert email not in result['contact']
        assert '[REDACTED_EMAIL]' in result['contact']

    @given(field_name=pii_field_names_st, value=st.text(min_size=1, max_size=50))
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_known_pii_field_names_redacted(self, field_name, value):
        """Any dict key matching a known PII field name must have its value redacted."""
        data = {field_name: value, 'safeField': 'keep-this'}
        result = redact_pii(data)
        assert result[field_name] == '[REDACTED]', (
            f'PII field {field_name!r} was not redacted'
        )
        assert result['safeField'] == 'keep-this'

    @given(
        email=email_st,
        depth=st.integers(min_value=1, max_value=8),
    )
    @h_settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_nested_structures_redacted(self, email, depth):
        """Emails nested inside dicts/lists at arbitrary depth must be redacted."""
        # Build a nested structure: {'a': [{'b': [{'c': email}]}]}
        data = {'contact': email}
        for i in range(depth):
            data = {f'level_{i}': [data]}

        result = redact_pii(data)
        serialized = json.dumps(result)
        assert email not in serialized, (
            f'Email {email!r} survived redaction at depth {depth}'
        )

    @given(
        safe_key=safe_field_names_st,
        safe_value=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
            min_size=1,
            max_size=30,
        ),
    )
    @h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_non_pii_data_preserved(self, safe_key, safe_value):
        """Non-PII field names with non-email, non-phone values must be preserved."""
        # Ensure the value doesn't accidentally look like an email
        assume('@' not in safe_value)
        assume(not re.search(r'\d{7,}', safe_value))
        data = {safe_key: safe_value}
        result = redact_pii(data)
        assert result[safe_key] == safe_value, (
            f'Non-PII value was incorrectly redacted: {safe_key}={safe_value!r}'
        )

    def test_none_and_numbers_pass_through(self):
        """None, int, float values must pass through unchanged."""
        data = {'count': 42, 'rate': 3.14, 'nothing': None}
        result = redact_pii(data)
        assert result == data

    def test_empty_structures(self):
        """Empty dicts, lists, and strings must pass through unchanged."""
        assert redact_pii({}) == {}
        assert redact_pii([]) == []
        assert redact_pii('') == ''

    def test_original_not_mutated(self):
        """redact_pii must not mutate the original data."""
        original = {'email': 'test@example.com', 'nested': {'phone': '555-1234'}}
        import copy
        frozen = copy.deepcopy(original)
        redact_pii(original)
        assert original == frozen

    def test_depth_limit_prevents_stack_overflow(self):
        """Deeply nested structures beyond the limit must not crash."""
        data = {'value': 'test@example.com'}
        for _ in range(50):
            data = {'nested': data}
        # Should not raise RecursionError
        result = redact_pii(data)
        assert result is not None
