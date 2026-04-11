"""
Configuration loader for data retention thresholds.

Reads from SSM Parameter Store with module-level caching.
Falls back to hardcoded DEFAULTS when SSM is unreachable.

Requirements: 17.1, 17.2, 17.5
"""
import json
import os
from datetime import datetime, timezone

import boto3

_ssm = boto3.client('ssm')
_config_cache: dict = {}

DEFAULTS = {
    'dormancy-threshold-1': 180,
    'dormancy-threshold-2': 365,
    'dormancy-threshold-3': 730,
    'deletion-grace-period': 30,
    'legacy-protection-dormancy-days': 730,
    'legacy-protection-lapse-days': 365,
    'glacier-transition-days': 365,
    'glacier-no-access-days': 180,
    'intelligent-tiering-days': 30,
    'export-rate-limit-days': 30,
    'export-link-expiry-hours': 72,
    'testing-mode': 'disabled',
}


def get_config(key: str):
    """
    Get a data retention config value from SSM, with caching and defaults.

    Numeric values are automatically parsed to int. String values (like
    testing-mode) are returned as-is.
    """
    if key not in _config_cache:
        try:
            resp = _ssm.get_parameter(
                Name=f'/soulreel/data-retention/{key}'
            )
            value = resp['Parameter']['Value']
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
            _config_cache[key] = value
        except Exception:
            _config_cache[key] = DEFAULTS.get(key, '')
    return _config_cache[key]


def is_testing_mode() -> bool:
    """Check if testing mode is enabled via SSM."""
    return get_config('testing-mode') == 'enabled'


def get_current_time(event: dict = None) -> datetime:
    """
    Get current time, respecting simulatedCurrentTime when testing mode is on.

    In testing mode, accepts simulatedCurrentTime from:
      - Top-level event key (for EventBridge / async invocations)
      - Parsed JSON body (for API Gateway requests)
    """
    if event and is_testing_mode():
        simulated = (
            event.get('simulatedCurrentTime')
            or _parse_body_field(event, 'simulatedCurrentTime')
        )
        if simulated:
            return datetime.fromisoformat(simulated.replace('Z', '+00:00'))
    return datetime.now(timezone.utc)


def _parse_body_field(event: dict, field: str):
    """Safely extract a field from the JSON-encoded event body."""
    body = event.get('body')
    if body:
        try:
            return json.loads(body).get(field)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    return None
