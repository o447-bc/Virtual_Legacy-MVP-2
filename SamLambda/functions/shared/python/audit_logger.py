"""
Audit logging utility for data retention lifecycle events.

Writes anonymized audit records to the retention audit S3 bucket.
Each record contains a SHA-256 hashed user ID (no PII), event type,
timestamp, details, and initiator.

Requirements: 11.1, 11.3
"""
import hashlib
import json
import os
from datetime import datetime, timezone

import boto3

_s3 = boto3.client('s3')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')

VALID_EVENT_TYPES = [
    'export_requested',
    'export_completed',
    'export_failed',
    'deletion_requested',
    'deletion_canceled',
    'deletion_completed',
    'legacy_protection_activated',
    'legacy_protection_deactivated',
    'storage_tier_transition',
    'dormancy_email_sent',
    'benefactor_access_revoked',
    'glacier_retrieval_requested',
    'lifecycle_simulation',
    'test_scenario_executed',
]


def log_audit_event(event_type: str, user_id: str, details: dict,
                    initiator: str = 'system') -> None:
    """
    Log a data lifecycle event to the audit S3 bucket.

    Args:
        event_type: One of VALID_EVENT_TYPES.
        user_id: Raw Cognito sub — will be SHA-256 hashed before writing.
        details: Arbitrary dict describing the action taken.
        initiator: 'user', 'system', or 'admin'.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event type: {event_type}")

    anonymized_id = hashlib.sha256(user_id.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    record = {
        'eventType': event_type,
        'anonymizedUserId': anonymized_id,
        'timestamp': now.isoformat(),
        'details': details,
        'initiator': initiator,
    }

    key = (
        f"audit/{now.strftime('%Y/%m/%d')}/{event_type}/"
        f"{anonymized_id}_{now.strftime('%H%M%S%f')}.json"
    )

    _s3.put_object(
        Bucket=_AUDIT_BUCKET,
        Key=key,
        Body=json.dumps(record),
        ContentType='application/json',
    )
