"""
Shared settings reader for all Lambda functions.

Reads from SystemSettingsTable (DynamoDB) with module-level caching
and a fallback chain: cache → DynamoDB → os.environ → default.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 13.1
"""
import os
import time
import logging

import boto3

logger = logging.getLogger(__name__)

_dynamodb = boto3.resource('dynamodb')
_table_name = os.environ.get('TABLE_SYSTEM_SETTINGS', 'SystemSettingsDB')
_table = _dynamodb.Table(_table_name)

# Module-level cache: key → (value, fetch_timestamp)
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes in seconds


def get_setting(key: str, default: str = '') -> str:
    """
    Read a setting with fallback chain:
    1. Module-level cache (if TTL not expired)
    2. SystemSettingsTable DynamoDB lookup
    3. os.environ.get(key)
    4. Provided default

    Never raises — falls back silently on DynamoDB errors.
    Does not cache fallback values (so next call retries DynamoDB).
    """
    # 1. Check cache
    now = time.time()
    if key in _cache:
        cached_value, cached_at = _cache[key]
        if now - cached_at < _CACHE_TTL:
            return cached_value
        # TTL expired — remove stale entry
        del _cache[key]

    # 2. Try DynamoDB
    try:
        resp = _table.get_item(Key={'settingKey': key})
        item = resp.get('Item')
        if item and 'value' in item:
            value = item['value']
            _cache[key] = (value, now)
            return value
    except Exception as exc:
        logger.warning('DynamoDB read failed for key %s: %s', key, exc)

    # 3. Fall back to environment variable, then default
    # Do NOT cache fallback values so next call retries DynamoDB
    return os.environ.get(key, default)
