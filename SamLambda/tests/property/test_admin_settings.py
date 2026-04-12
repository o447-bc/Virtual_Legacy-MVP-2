"""
Property-based tests for the Settings Reader utility.

Feature: admin-system-settings, Property 2: Settings Reader fallback chain precedence
Feature: admin-system-settings, Property 3: Settings Reader cache TTL behavior
Feature: admin-system-settings, Property 4: Settings Reader error resilience

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.4, 13.1**
"""
import json
import os
import sys
import time
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings as h_settings, strategies as st, HealthCheck

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

os.environ.setdefault('TABLE_SYSTEM_SETTINGS', 'SystemSettingsDB')

# ---------------------------------------------------------------------------
# Import the settings module with mocked boto3 so it doesn't connect at import
# ---------------------------------------------------------------------------
_mock_dynamodb = MagicMock()
_mock_table = MagicMock()
_mock_dynamodb.Table.return_value = _mock_table

with patch('boto3.resource', return_value=_mock_dynamodb):
    import importlib
    import settings as settings_mod

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
_setting_key = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Nd'),
                           whitelist_characters='_'),
    min_size=1, max_size=40,
).filter(lambda s: '\x00' not in s)

_setting_value = st.text(min_size=0, max_size=200)

# Environment variables cannot contain null bytes or surrogates
_env_safe_value = st.text(
    alphabet=st.characters(blacklist_characters='\x00',
                           blacklist_categories=('Cs',)),
    min_size=0, max_size=200,
)


def _reset_cache():
    """Clear the module-level cache between tests."""
    settings_mod._cache.clear()


def _set_mock_table(mock_table):
    """Point the settings module at our mock table."""
    settings_mod._table = mock_table


# ===================================================================
# Property 2: Settings Reader fallback chain precedence
# Feature: admin-system-settings, Property 2
# **Validates: Requirements 5.1, 5.2, 5.3, 10.4, 13.1**
# ===================================================================

class TestFallbackChainPrecedence:
    """Property 2: DynamoDB value > env var > default."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        dynamo_val=_setting_value,
        env_val=_env_safe_value,
        default_val=_setting_value,
    )
    def test_dynamo_takes_precedence_over_env_and_default(
        self, key, dynamo_val, env_val, default_val
    ):
        """When DynamoDB has the key, its value is returned regardless of env/default."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {'settingKey': key, 'value': dynamo_val}
        }
        _set_mock_table(mock_table)

        with patch.dict(os.environ, {key: env_val}):
            result = settings_mod.get_setting(key, default_val)

        assert result == dynamo_val

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        env_val=_env_safe_value,
        default_val=_setting_value,
    )
    def test_env_takes_precedence_over_default_when_dynamo_missing(
        self, key, env_val, default_val
    ):
        """When DynamoDB has no item, env var is returned over default."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        _set_mock_table(mock_table)

        with patch.dict(os.environ, {key: env_val}):
            result = settings_mod.get_setting(key, default_val)

        assert result == env_val

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        default_val=_setting_value,
    )
    def test_default_returned_when_dynamo_and_env_missing(
        self, key, default_val
    ):
        """When DynamoDB has no item and env var is unset, default is returned."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        _set_mock_table(mock_table)

        # Ensure the key is NOT in os.environ
        env_copy = {k: v for k, v in os.environ.items() if k != key}
        with patch.dict(os.environ, env_copy, clear=True):
            result = settings_mod.get_setting(key, default_val)

        assert result == default_val


# ===================================================================
# Property 3: Settings Reader cache TTL behavior
# Feature: admin-system-settings, Property 3
# **Validates: Requirements 5.4, 5.5**
# ===================================================================

class TestCacheTTLBehavior:
    """Property 3: Cached value returned within TTL; re-fetched after TTL."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        val1=_setting_value,
        val2=_setting_value,
    )
    def test_cached_value_returned_within_ttl(self, key, val1, val2):
        """Within 5 minutes, get_setting returns cached value without querying DynamoDB."""
        _reset_cache()
        mock_table = MagicMock()
        _set_mock_table(mock_table)

        # First call — DynamoDB returns val1
        mock_table.get_item.return_value = {
            'Item': {'settingKey': key, 'value': val1}
        }
        result1 = settings_mod.get_setting(key, '')
        assert result1 == val1
        assert mock_table.get_item.call_count == 1

        # Change DynamoDB to return val2
        mock_table.get_item.return_value = {
            'Item': {'settingKey': key, 'value': val2}
        }

        # Second call within TTL — should return cached val1, no new DynamoDB call
        result2 = settings_mod.get_setting(key, '')
        assert result2 == val1
        assert mock_table.get_item.call_count == 1  # No additional call

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        val1=_setting_value,
        val2=_setting_value,
    )
    def test_cache_expired_triggers_refetch(self, key, val1, val2):
        """After 5 minutes, get_setting re-fetches from DynamoDB."""
        _reset_cache()
        mock_table = MagicMock()
        _set_mock_table(mock_table)

        # First call — DynamoDB returns val1
        mock_table.get_item.return_value = {
            'Item': {'settingKey': key, 'value': val1}
        }
        result1 = settings_mod.get_setting(key, '')
        assert result1 == val1

        # Simulate TTL expiry by backdating the cache timestamp
        if key in settings_mod._cache:
            old_val, _ = settings_mod._cache[key]
            settings_mod._cache[key] = (old_val, time.time() - 301)

        # Change DynamoDB to return val2
        mock_table.get_item.return_value = {
            'Item': {'settingKey': key, 'value': val2}
        }

        # Call after TTL — should re-fetch and return val2
        result2 = settings_mod.get_setting(key, '')
        assert result2 == val2
        assert mock_table.get_item.call_count == 2


# ===================================================================
# Property 4: Settings Reader error resilience
# Feature: admin-system-settings, Property 4
# **Validates: Requirements 5.6**
# ===================================================================

class TestErrorResilience:
    """Property 4: DynamoDB errors never propagate; fallback is used."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        env_val=_env_safe_value,
        default_val=_setting_value,
    )
    def test_dynamo_error_falls_back_to_env(self, key, env_val, default_val):
        """When DynamoDB raises, env var is returned without exception."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception('DynamoDB unavailable')
        _set_mock_table(mock_table)

        with patch.dict(os.environ, {key: env_val}):
            result = settings_mod.get_setting(key, default_val)

        assert result == env_val

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        default_val=_setting_value,
    )
    def test_dynamo_error_falls_back_to_default_when_no_env(
        self, key, default_val
    ):
        """When DynamoDB raises and env var is unset, default is returned."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception('DynamoDB unavailable')
        _set_mock_table(mock_table)

        env_copy = {k: v for k, v in os.environ.items() if k != key}
        with patch.dict(os.environ, env_copy, clear=True):
            result = settings_mod.get_setting(key, default_val)

        assert result == default_val

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        key=_setting_key,
        default_val=_setting_value,
    )
    def test_dynamo_error_does_not_cache_fallback(self, key, default_val):
        """Fallback values are NOT cached, so next call retries DynamoDB."""
        _reset_cache()
        mock_table = MagicMock()
        mock_table.get_item.side_effect = Exception('DynamoDB unavailable')
        _set_mock_table(mock_table)

        env_copy = {k: v for k, v in os.environ.items() if k != key}
        with patch.dict(os.environ, env_copy, clear=True):
            settings_mod.get_setting(key, default_val)

        # The key should NOT be in the cache
        assert key not in settings_mod._cache


# ---------------------------------------------------------------------------
# Path setup for adminSettings app module
# ---------------------------------------------------------------------------
_ADMIN_SETTINGS_DIR = os.path.join(
    _ROOT, 'functions', 'adminFunctions', 'adminSettings'
)
if _ADMIN_SETTINGS_DIR not in sys.path:
    sys.path.insert(0, _ADMIN_SETTINGS_DIR)

# Import _validate_value directly from app module
# We need the shared layer on the path too for cors, responses, admin_auth
from app import _validate_value, BEDROCK_PRICING


# ===================================================================
# Property 1: Type validation accepts valid values and rejects invalid values
# Feature: admin-system-settings, Property 1
# **Validates: Requirements 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
# ===================================================================

# Strategies for valid/invalid values per type
_valid_integers = st.integers(min_value=-10**9, max_value=10**9).map(str)
_invalid_integers = st.text(min_size=1, max_size=50).filter(
    lambda s: not _is_int(s)
)

_valid_floats = st.floats(
    allow_nan=False, allow_infinity=False,
    min_value=-1e9, max_value=1e9,
).map(str)
_invalid_floats = st.text(min_size=1, max_size=50).filter(
    lambda s: not _is_float(s)
)

_valid_booleans = st.sampled_from(['true', 'false'])
_invalid_booleans = st.text(min_size=1, max_size=50).filter(
    lambda s: s not in ('true', 'false')
)

_valid_strings = st.text(
    alphabet=st.characters(blacklist_characters='\n\r\x00'),
    min_size=1, max_size=200,
)
_invalid_strings_empty = st.just('')
_invalid_strings_newline = st.text(min_size=1, max_size=50).map(
    lambda s: s + '\n'
).filter(lambda s: len(s) > 0)

_valid_text = st.text(min_size=0, max_size=500)

_known_model_ids = list(BEDROCK_PRICING.keys())
_valid_models = st.sampled_from(_known_model_ids)
_invalid_models = st.text(min_size=1, max_size=100).filter(
    lambda s: s not in BEDROCK_PRICING
)


def _is_int(s):
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


def _is_float(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


class TestTypeValidation:
    """Property 1: Type validation accepts valid values and rejects invalid values."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_integers)
    def test_integer_valid_accepted(self, value):
        """Valid integer strings are accepted."""
        assert _validate_value(value, 'integer') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_invalid_integers)
    def test_integer_invalid_rejected(self, value):
        """Non-integer strings are rejected."""
        result = _validate_value(value, 'integer')
        assert result is not None
        assert 'integer' in result.lower()

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_floats)
    def test_float_valid_accepted(self, value):
        """Valid float strings are accepted."""
        assert _validate_value(value, 'float') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_invalid_floats)
    def test_float_invalid_rejected(self, value):
        """Non-float strings are rejected."""
        result = _validate_value(value, 'float')
        assert result is not None
        assert 'float' in result.lower()

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_booleans)
    def test_boolean_valid_accepted(self, value):
        """Exactly 'true' or 'false' are accepted."""
        assert _validate_value(value, 'boolean') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_invalid_booleans)
    def test_boolean_invalid_rejected(self, value):
        """Strings other than 'true'/'false' are rejected."""
        result = _validate_value(value, 'boolean')
        assert result is not None
        assert 'boolean' in result.lower()

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_strings)
    def test_string_valid_accepted(self, value):
        """Non-empty strings without newlines are accepted."""
        assert _validate_value(value, 'string') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_invalid_strings_newline)
    def test_string_with_newline_rejected(self, value):
        """Strings containing newlines are rejected."""
        result = _validate_value(value, 'string')
        assert result is not None
        assert 'string' in result.lower()

    def test_string_empty_rejected(self):
        """Empty string is rejected for string type."""
        result = _validate_value('', 'string')
        assert result is not None
        assert 'string' in result.lower()

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_text)
    def test_text_always_accepted(self, value):
        """Any string is accepted for text type."""
        assert _validate_value(value, 'text') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_valid_models)
    def test_model_valid_accepted(self, value):
        """Known Bedrock model IDs are accepted."""
        assert _validate_value(value, 'model') is None

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(value=_invalid_models)
    def test_model_invalid_rejected(self, value):
        """Unknown model IDs are rejected."""
        result = _validate_value(value, 'model')
        assert result is not None
        assert 'model' in result.lower()

    def test_model_empty_rejected(self):
        """Empty string is rejected for model type."""
        result = _validate_value('', 'model')
        assert result is not None
        assert 'model' in result.lower()


# ===================================================================
# Property 5: CORS headers on all API responses
# Feature: admin-system-settings, Property 5
# **Validates: Requirements 2.4, 3.11, 11.8**
# ===================================================================

_http_methods = st.sampled_from(['GET', 'PUT', 'POST', 'DELETE', 'OPTIONS', 'PATCH'])
_resources = st.sampled_from([
    '/admin/settings',
    '/admin/settings/{settingKey}',
    '/admin/bedrock-models',
    '/unknown/path',
])


def _make_event(method, resource, admin=False, body=None, path_params=None):
    """Build a minimal API Gateway event dict."""
    event = {
        'httpMethod': method,
        'resource': resource,
        'headers': {'Origin': 'https://www.soulreel.net'},
        'requestContext': {},
        'body': body,
        'pathParameters': path_params,
    }
    if admin:
        event['requestContext'] = {
            'authorizer': {
                'claims': {
                    'cognito:groups': 'SoulReelAdmins',
                    'email': 'admin@soulreel.net',
                    'sub': 'admin-sub-123',
                }
            }
        }
    return event


class TestCORSHeaders:
    """Property 5: CORS headers on all API responses."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(method=_http_methods, resource=_resources)
    def test_cors_headers_present_non_admin(self, method, resource):
        """Non-admin requests still get CORS headers in the response."""
        event = _make_event(method, resource, admin=False)

        with patch('app.boto3') as mock_boto:
            from app import lambda_handler
            response = lambda_handler(event, {})

        headers = response.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Headers' in headers
        assert 'Access-Control-Allow-Methods' in headers

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(method=_http_methods, resource=_resources)
    def test_cors_headers_present_admin(self, method, resource):
        """Admin requests also get CORS headers in the response."""
        event = _make_event(method, resource, admin=True)

        mock_dynamo_resource = MagicMock()
        mock_table = MagicMock()
        mock_dynamo_resource.Table.return_value = mock_table
        mock_table.scan.return_value = {'Items': []}
        mock_table.get_item.return_value = {}

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.list_foundation_models.return_value = {
            'modelSummaries': []
        }

        with patch('app.boto3') as mock_boto:
            mock_boto.resource.return_value = mock_dynamo_resource
            mock_boto.client.return_value = mock_bedrock_client
            from app import lambda_handler
            response = lambda_handler(event, {})

        headers = response.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Headers' in headers
        assert 'Access-Control-Allow-Methods' in headers


# ===================================================================
# Property 6: GET settings groups items by section
# Feature: admin-system-settings, Property 6
# **Validates: Requirements 2.1**
# ===================================================================

_section_names = st.sampled_from([
    'AI & Models', 'Assessments', 'Conversations',
    'Video & Media', 'Data Retention', 'Security',
    'Engagement & Notifications',
])

_setting_item_strategy = st.fixed_dictionaries({
    'settingKey': st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), whitelist_characters='_'),
        min_size=1, max_size=30,
    ),
    'value': st.text(min_size=1, max_size=50),
    'valueType': st.sampled_from(['string', 'integer', 'float', 'boolean', 'text', 'model']),
    'section': _section_names,
    'label': st.text(min_size=1, max_size=50),
    'description': st.text(min_size=1, max_size=100),
    'updatedAt': st.just('2025-01-15T10:30:00+00:00'),
    'updatedBy': st.just('admin@soulreel.net'),
})


class TestGetSettingsGrouping:
    """Property 6: GET settings groups items by section."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(items=st.lists(_setting_item_strategy, min_size=0, max_size=20))
    def test_items_grouped_by_section(self, items):
        """All items are grouped correctly by their section value."""
        event = _make_event('GET', '/admin/settings', admin=True)

        mock_dynamo_resource = MagicMock()
        mock_table = MagicMock()
        mock_dynamo_resource.Table.return_value = mock_table
        mock_table.scan.return_value = {'Items': items}

        with patch('app.boto3') as mock_boto:
            mock_boto.resource.return_value = mock_dynamo_resource
            from app import handle_get_settings
            response = handle_get_settings(event)

        body = json.loads(response['body'])
        grouped = body['settings']

        # Build expected grouping
        expected = {}
        for item in items:
            section = item.get('section', 'Other')
            if section not in expected:
                expected[section] = []
            expected[section].append(item['settingKey'])

        # Verify same sections
        assert set(grouped.keys()) == set(expected.keys())

        # Verify each section has the right items
        for section, keys in expected.items():
            actual_keys = [i['settingKey'] for i in grouped[section]]
            assert sorted(actual_keys) == sorted(keys)


# ===================================================================
# Property 7: PUT setting updates metadata correctly
# Feature: admin-system-settings, Property 7
# **Validates: Requirements 3.1**
# ===================================================================

_admin_emails = st.from_regex(r'[a-z]{3,10}@soulreel\.net', fullmatch=True)


class TestPutSettingMetadata:
    """Property 7: PUT setting updates metadata correctly."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        setting_key=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), whitelist_characters='_'),
            min_size=1, max_size=30,
        ),
        new_value=st.text(min_size=1, max_size=50),
        admin_email=_admin_emails,
    )
    def test_put_sets_updated_at_and_updated_by(self, setting_key, new_value, admin_email):
        """PUT updates updatedAt to ISO 8601 and updatedBy to admin email."""
        event = _make_event(
            'PUT',
            '/admin/settings/{settingKey}',
            admin=True,
            body=json.dumps({'value': new_value}),
            path_params={'settingKey': setting_key},
        )
        # Override the admin email in the event
        event['requestContext']['authorizer']['claims']['email'] = admin_email

        mock_dynamo_resource = MagicMock()
        mock_table = MagicMock()
        mock_dynamo_resource.Table.return_value = mock_table
        # Setting exists with valueType 'text' (always valid)
        mock_table.get_item.return_value = {
            'Item': {
                'settingKey': setting_key,
                'value': 'old',
                'valueType': 'text',
            }
        }

        with patch('app.boto3') as mock_boto:
            mock_boto.resource.return_value = mock_dynamo_resource
            from app import handle_put_setting
            response = handle_put_setting(event, admin_email)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        # updatedBy must be the admin email
        assert body['updatedBy'] == admin_email

        # updatedAt must be a valid ISO 8601 timestamp
        updated_at = body['updatedAt']
        from datetime import datetime as dt, timezone as tz
        parsed = dt.fromisoformat(updated_at)
        assert parsed.tzinfo is not None  # Must be timezone-aware

        # Should be within a reasonable window (last 60 seconds)
        now = dt.now(tz.utc)
        diff = abs((now - parsed).total_seconds())
        assert diff < 60


# ===================================================================
# Property 13: Bedrock models filtered to ON_DEMAND only
# Feature: admin-system-settings, Property 13
# **Validates: Requirements 11.2**
# ===================================================================

_inference_types = st.sampled_from(['ON_DEMAND', 'PROVISIONED', 'INFERENCE_PROFILE'])

_mock_model_summary = st.fixed_dictionaries({
    'modelId': st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='.-:'),
        min_size=5, max_size=50,
    ),
    'modelName': st.text(min_size=1, max_size=30),
    'providerName': st.sampled_from(['Anthropic', 'Amazon', 'Meta', 'Mistral', 'Cohere']),
    'inferenceTypesSupported': st.lists(_inference_types, min_size=1, max_size=3),
})


class TestBedrockOnDemandFilter:
    """Property 13: Bedrock models filtered to ON_DEMAND only."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(model_summaries=st.lists(_mock_model_summary, min_size=0, max_size=15))
    def test_only_on_demand_models_returned(self, model_summaries):
        """Only models with ON_DEMAND in inferenceTypesSupported are returned."""
        import app as app_mod

        # Clear the bedrock cache to force a fresh fetch
        app_mod._bedrock_cache['models'] = None
        app_mod._bedrock_cache['fetched_at'] = 0

        event = _make_event('GET', '/admin/bedrock-models', admin=True)

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.list_foundation_models.return_value = {
            'modelSummaries': model_summaries
        }

        with patch('app.boto3') as mock_boto:
            mock_boto.client.return_value = mock_bedrock_client
            response = app_mod.handle_get_bedrock_models(event)

        body = json.loads(response['body'])
        returned_ids = {m['modelId'] for m in body['models']}

        # Expected: only models with ON_DEMAND
        expected_ids = {
            m['modelId'] for m in model_summaries
            if 'ON_DEMAND' in m.get('inferenceTypesSupported', [])
        }

        assert returned_ids == expected_ids


# ===================================================================
# Property 14: Bedrock models sorted by cost descending
# Feature: admin-system-settings, Property 14
# **Validates: Requirements 11.4**
# ===================================================================

_price = st.one_of(
    st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
    st.none(),
)

_priced_model = st.fixed_dictionaries({
    'modelId': st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='.-:'),
        min_size=5, max_size=50,
    ),
    'modelName': st.text(min_size=1, max_size=30),
    'providerName': st.sampled_from(['Anthropic', 'Amazon', 'Meta']),
    'inputPricePerKToken': _price,
    'outputPricePerKToken': _price,
})


class TestBedrockSortOrder:
    """Property 14: Bedrock models sorted by cost descending."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(models=st.lists(_priced_model, min_size=0, max_size=20))
    def test_models_sorted_descending_nulls_at_end(self, models):
        """Models are sorted by inputPricePerKToken descending, nulls at end."""
        import app as app_mod

        # Clear cache
        app_mod._bedrock_cache['models'] = None
        app_mod._bedrock_cache['fetched_at'] = 0

        # Build mock Bedrock response: all ON_DEMAND so they pass the filter
        summaries = []
        # Build a custom pricing dict for this test
        test_pricing = {}
        for m in models:
            summaries.append({
                'modelId': m['modelId'],
                'modelName': m['modelName'],
                'providerName': m['providerName'],
                'inferenceTypesSupported': ['ON_DEMAND'],
            })
            if m['inputPricePerKToken'] is not None:
                test_pricing[m['modelId']] = {
                    'inputPricePerKToken': m['inputPricePerKToken'],
                    'outputPricePerKToken': m['outputPricePerKToken'],
                }

        event = _make_event('GET', '/admin/bedrock-models', admin=True)

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.list_foundation_models.return_value = {
            'modelSummaries': summaries
        }

        with patch('app.boto3') as mock_boto, \
             patch.dict('app.BEDROCK_PRICING', test_pricing, clear=True):
            mock_boto.client.return_value = mock_bedrock_client
            response = app_mod.handle_get_bedrock_models(event)

        body = json.loads(response['body'])
        result_models = body['models']

        # Verify ordering: priced models descending, then null-priced
        priced = [m for m in result_models if m['inputPricePerKToken'] is not None]
        nulls = [m for m in result_models if m['inputPricePerKToken'] is None]

        # All priced models come before null models
        if priced and nulls:
            priced_indices = [i for i, m in enumerate(result_models) if m['inputPricePerKToken'] is not None]
            null_indices = [i for i, m in enumerate(result_models) if m['inputPricePerKToken'] is None]
            assert max(priced_indices) < min(null_indices)

        # Priced models are in descending order
        for i in range(len(priced) - 1):
            assert priced[i]['inputPricePerKToken'] >= priced[i + 1]['inputPricePerKToken']


# ===================================================================
# Property 15: Bedrock model response contains required fields
# Feature: admin-system-settings, Property 15
# **Validates: Requirements 11.3**
# ===================================================================

class TestBedrockResponseFields:
    """Property 15: Bedrock model response contains required fields."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(model_summaries=st.lists(_mock_model_summary, min_size=1, max_size=15))
    def test_all_models_have_required_fields(self, model_summaries):
        """Every model in the response has modelId, modelName, providerName, and pricing fields."""
        import app as app_mod

        # Clear cache
        app_mod._bedrock_cache['models'] = None
        app_mod._bedrock_cache['fetched_at'] = 0

        event = _make_event('GET', '/admin/bedrock-models', admin=True)

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.list_foundation_models.return_value = {
            'modelSummaries': model_summaries
        }

        with patch('app.boto3') as mock_boto:
            mock_boto.client.return_value = mock_bedrock_client
            response = app_mod.handle_get_bedrock_models(event)

        body = json.loads(response['body'])
        for model in body['models']:
            # Required fields must be present
            assert 'modelId' in model
            assert 'modelName' in model
            assert 'providerName' in model
            assert 'inputPricePerKToken' in model
            assert 'outputPricePerKToken' in model

            # modelId, modelName, providerName must be strings
            assert isinstance(model['modelId'], str)
            assert isinstance(model['modelName'], str)
            assert isinstance(model['providerName'], str)

            # Pricing must be number or null
            assert model['inputPricePerKToken'] is None or isinstance(model['inputPricePerKToken'], (int, float))
            assert model['outputPricePerKToken'] is None or isinstance(model['outputPricePerKToken'], (int, float))


# ---------------------------------------------------------------------------
# Path setup for seed module
# ---------------------------------------------------------------------------
_SEED_DIR = os.path.join(
    _ROOT, 'functions', 'adminFunctions', 'adminSettings'
)
if _SEED_DIR not in sys.path:
    sys.path.insert(0, _SEED_DIR)

from seed import SEED_SETTINGS, run_seed


# ===================================================================
# Property 8: Seed script idempotency
# Feature: admin-system-settings, Property 8
# **Validates: Requirements 6.2, 13.2**
# ===================================================================

class TestSeedIdempotency:
    """Property 8: Pre-existing items are never overwritten by the seed script."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(
        pre_existing_indices=st.lists(
            st.integers(min_value=0, max_value=len(SEED_SETTINGS) - 1),
            min_size=1,
            max_size=min(10, len(SEED_SETTINGS)),
            unique=True,
        ),
        custom_value=st.text(min_size=1, max_size=100),
        custom_updated_by=st.text(min_size=1, max_size=50),
    )
    def test_existing_items_not_overwritten(
        self, pre_existing_indices, custom_value, custom_updated_by
    ):
        """
        When some settings already exist in the table, running the seed
        script does not modify those items' value, updatedAt, or updatedBy.
        """
        # Track what was written via put_item
        written_items = {}
        pre_existing_keys = {
            SEED_SETTINGS[i]['settingKey'] for i in pre_existing_indices
        }

        mock_table = MagicMock()

        def fake_put_item(Item, ConditionExpression=None):
            key = Item['settingKey']
            if key in pre_existing_keys:
                # Simulate ConditionalCheckFailedException for existing items
                error_response = {
                    'Error': {
                        'Code': 'ConditionalCheckFailedException',
                        'Message': 'The conditional request failed',
                    }
                }
                raise ClientError(error_response, 'PutItem')
            written_items[key] = Item

        mock_table.put_item = fake_put_item

        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        with patch('seed.boto3') as mock_boto, \
             patch('seed._read_ssm', side_effect=lambda path, fb: fb):
            mock_boto.resource.return_value = mock_dynamodb
            run_seed('TestTable')

        # Pre-existing items must NOT appear in written_items
        for key in pre_existing_keys:
            assert key not in written_items, (
                f"Pre-existing key '{key}' was overwritten by seed script"
            )

        # All non-pre-existing items should have been written
        non_existing_keys = {
            s['settingKey'] for s in SEED_SETTINGS
        } - pre_existing_keys
        for key in non_existing_keys:
            assert key in written_items, (
                f"New key '{key}' was not seeded"
            )


# ===================================================================
# Property 9: Seed item completeness
# Feature: admin-system-settings, Property 9
# **Validates: Requirements 1.6, 6.3, 6.4**
# ===================================================================

_REQUIRED_ATTRIBUTES = {
    'settingKey', 'value', 'valueType', 'section', 'label', 'description',
}
_VALID_VALUE_TYPES = {'string', 'integer', 'float', 'boolean', 'text', 'model'}


class TestSeedItemCompleteness:
    """Property 9: Every seed item has all required attributes and valid valueType."""

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(index=st.integers(min_value=0, max_value=len(SEED_SETTINGS) - 1))
    def test_seed_item_has_all_required_attributes(self, index):
        """Each SEED_SETTINGS entry has settingKey, value, valueType, section, label, description."""
        item = SEED_SETTINGS[index]
        for attr in _REQUIRED_ATTRIBUTES:
            assert attr in item, f"Missing attribute '{attr}' in seed item '{item.get('settingKey', '?')}'"

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(index=st.integers(min_value=0, max_value=len(SEED_SETTINGS) - 1))
    def test_seed_item_has_valid_value_type(self, index):
        """Each SEED_SETTINGS entry has a valueType from the six valid types."""
        item = SEED_SETTINGS[index]
        assert item['valueType'] in _VALID_VALUE_TYPES, (
            f"Invalid valueType '{item['valueType']}' for '{item['settingKey']}'"
        )

    @h_settings(max_examples=100, deadline=None,
                suppress_health_check=[HealthCheck.too_slow])
    @given(index=st.integers(min_value=0, max_value=len(SEED_SETTINGS) - 1))
    def test_seed_item_has_non_empty_label_and_description(self, index):
        """Each SEED_SETTINGS entry has non-empty label and description."""
        item = SEED_SETTINGS[index]
        assert isinstance(item['label'], str) and len(item['label']) > 0, (
            f"Empty label for '{item['settingKey']}'"
        )
        assert isinstance(item['description'], str) and len(item['description']) > 0, (
            f"Empty description for '{item['settingKey']}'"
        )

    def test_run_seed_writes_complete_items(self):
        """
        When run_seed executes, every item written to DynamoDB contains all
        required attributes including updatedAt and updatedBy.
        """
        written_items = {}
        mock_table = MagicMock()

        def fake_put_item(Item, ConditionExpression=None):
            written_items[Item['settingKey']] = Item

        mock_table.put_item = fake_put_item

        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        with patch('seed.boto3') as mock_boto, \
             patch('seed._read_ssm', side_effect=lambda path, fb: fb):
            mock_boto.resource.return_value = mock_dynamodb
            run_seed('TestTable')

        full_required = _REQUIRED_ATTRIBUTES | {'updatedAt', 'updatedBy'}

        for key, item in written_items.items():
            for attr in full_required:
                assert attr in item, (
                    f"Written item '{key}' missing attribute '{attr}'"
                )
            assert item['updatedBy'] == 'seed-script'
            assert item['valueType'] in _VALID_VALUE_TYPES
