"""
LegacyProtectionFunction Lambda Handler

Handles manual benefactor requests for legacy protection and weekly
auto-evaluation of flagged accounts. Provides deactivation when
a legacy-protected user returns.

Endpoints:
  POST /legacy/protection-request (Cognito Auth)

Schedule:
  WeeklyAutoEvaluation — rate(7 days)

Requirements: 8.1–8.9
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Add shared layer to path
sys.path.append('/opt/python')

from cors import cors_headers
from responses import error_response
from email_utils import send_email_with_retry
from audit_logger import log_audit_event
from retention_config import get_config, get_current_time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_ssm = boto3.client('ssm')

_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_TABLE_USER_STATUS = os.environ.get('TABLE_USER_STATUS', 'userStatusDB')
_TABLE_SUBSCRIPTIONS = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')
_TABLE_RELATIONSHIPS = os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code: int, body: dict, event: dict = None) -> dict:
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body),
    }


# ===================================================================
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route by event source: schedule, API, or deactivation invocation."""

    # Handle scheduled event (WeeklyAutoEvaluation)
    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        return handle_auto_evaluation(event)

    # Handle deactivation invocation (from admin or resubscription)
    if event.get('source') == 'deactivate_legacy_protection':
        user_id = event.get('userId')
        if user_id:
            return deactivate_legacy_protection(user_id)
        return {'error': 'Missing userId'}

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # Authenticated endpoints
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        if path == '/legacy/protection-request' and method == 'POST':
            return handle_protection_request(event, user_id)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[LEGACY_PROTECTION] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Handler: POST /legacy/protection-request
# ===================================================================

def handle_protection_request(event, requester_id):
    """Manual legacy protection request from a benefactor."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
    relationships_table = _dynamodb.Table(_TABLE_RELATIONSHIPS)

    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    maker_id = body.get('legacyMakerId')
    reason = body.get('reason', '')

    if not maker_id:
        return cors_response(400, {'error': 'legacyMakerId is required'}, event)

    # Verify requester is a benefactor of the maker
    try:
        response = relationships_table.query(
            KeyConditionExpression=Key('initiatorId').eq(maker_id),
            FilterExpression=Attr('visitorId').eq(requester_id),
        )
        if not response.get('Items'):
            return cors_response(403, {
                'error': 'You are not an authorized benefactor of this legacy maker'
            }, event)
    except ClientError as exc:
        logger.error('[LEGACY_PROTECTION] Relationship check failed: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)

    # Check if already legacy_protected
    existing = retention_table.get_item(
        Key={'userId': maker_id, 'recordType': 'legacy_protection'}
    ).get('Item', {})

    if existing.get('status') == 'active':
        return cors_response(409, {
            'error': 'This account is already in Legacy Protection mode'
        }, event)

    # Count benefactors
    ben_response = relationships_table.query(
        KeyConditionExpression=Key('initiatorId').eq(maker_id),
    )
    benefactor_count = len(ben_response.get('Items', []))

    # Create legacy_protection record
    retention_table.put_item(Item={
        'userId': maker_id,
        'recordType': 'legacy_protection',
        'status': 'active',
        'activationType': 'manual',
        'requestedBy': requester_id,
        'reason': reason,
        'activatedAt': now.isoformat(),
        'benefactorCount': benefactor_count,
        'updatedAt': now.isoformat(),
    })

    # Send email to all benefactors
    benefactors = ben_response.get('Items', [])
    _notify_benefactors_protection_activated(benefactors, maker_id)

    log_audit_event('legacy_protection_activated', maker_id,
                    {'activationType': 'manual', 'requestedBy': requester_id,
                     'benefactorCount': benefactor_count, 'reason': reason},
                    initiator='user')

    return cors_response(200, {
        'status': 'activated',
        'message': 'Legacy protection has been activated. All benefactors have been notified.',
    }, event)


# ===================================================================
# Handler: Weekly auto-evaluation
# ===================================================================

def handle_auto_evaluation(event):
    """Auto-evaluate flagged accounts for legacy protection activation."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
    subscriptions_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)
    relationships_table = _dynamodb.Table(_TABLE_RELATIONSHIPS)

    dormancy_days = get_config('dormancy-threshold-3')  # 730 days
    lapse_days = get_config('legacy-protection-lapse-days')  # 365 days

    # Query flagged accounts from DataRetentionDB
    flagged_items = []
    response = retention_table.scan(
        FilterExpression=(
            Attr('recordType').eq('dormancy_state') &
            Attr('status').eq('flagged_for_legacy_protection')
        )
    )
    flagged_items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = retention_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression=(
                Attr('recordType').eq('dormancy_state') &
                Attr('status').eq('flagged_for_legacy_protection')
            )
        )
        flagged_items.extend(response.get('Items', []))

    activated = 0
    for item in flagged_items:
        user_id = item.get('userId')
        if not user_id:
            continue

        # Skip if already protected
        existing = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'legacy_protection'}
        ).get('Item', {})
        if existing.get('status') == 'active':
            continue

        # Verify subscription lapsed >= lapse_days
        sub_record = subscriptions_table.get_item(
            Key={'userId': user_id}
        ).get('Item', {})
        lapsed_at = sub_record.get('subscriptionLapsedAt') or sub_record.get('canceledAt')
        if lapsed_at:
            try:
                lapsed_dt = datetime.fromisoformat(lapsed_at.replace('Z', '+00:00'))
                if (now - lapsed_dt).days < lapse_days:
                    continue
            except (ValueError, TypeError):
                continue
        else:
            status = sub_record.get('subscriptionStatus', '')
            if status in ('active', 'trialing', 'comped'):
                continue

        # Verify benefactors exist
        ben_response = relationships_table.query(
            KeyConditionExpression=Key('initiatorId').eq(user_id),
            Limit=1,
        )
        if not ben_response.get('Items'):
            continue

        # Get full benefactor list for notification
        all_bens = relationships_table.query(
            KeyConditionExpression=Key('initiatorId').eq(user_id),
        )
        benefactors = all_bens.get('Items', [])
        benefactor_count = len(benefactors)

        # Activate legacy protection
        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'legacy_protection',
            'status': 'active',
            'activationType': 'automatic',
            'requestedBy': 'system',
            'activatedAt': now.isoformat(),
            'benefactorCount': benefactor_count,
            'updatedAt': now.isoformat(),
        })

        _notify_benefactors_protection_activated(benefactors, user_id)

        log_audit_event('legacy_protection_activated', user_id,
                        {'activationType': 'automatic',
                         'benefactorCount': benefactor_count})
        activated += 1

    logger.info('[LEGACY_PROTECTION] Auto-evaluation: %d flagged, %d activated',
                len(flagged_items), activated)
    return {'flaggedCount': len(flagged_items), 'activatedCount': activated}


# ===================================================================
# Deactivation (called on user return)
# ===================================================================

def deactivate_legacy_protection(user_id):
    """Deactivate legacy protection when user returns."""
    now = datetime.now(timezone.utc)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Check if actually protected
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'legacy_protection'}
    ).get('Item', {})

    if existing.get('status') != 'active':
        return {'status': 'not_protected'}

    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'legacy_protection'},
        UpdateExpression='SET #s = :s, deactivatedAt = :now, updatedAt = :now',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':s': 'deactivated',
            ':now': now.isoformat(),
        },
    )

    log_audit_event('legacy_protection_deactivated', user_id,
                    {'reason': 'user_returned'})

    # Send welcome-back email
    _send_welcome_back_email(user_id)

    logger.info('[LEGACY_PROTECTION] Deactivated for user %s (user returned)', user_id)
    return {'status': 'deactivated'}


# ===================================================================
# Helpers
# ===================================================================

def _notify_benefactors_protection_activated(benefactors, maker_id):
    """Send legacy protection activation email to all benefactors."""
    for ben in benefactors:
        email = ben.get('visitorEmail', '')
        name = ben.get('visitorName', ben.get('visitorId', 'Friend'))
        if not email:
            continue
        try:
            send_email_with_retry(
                destination=email,
                subject='Legacy Protection Activated',
                html_body=(
                    f'<h2>Hi {name},</h2>'
                    f'<p>Legacy Protection has been activated for a SoulReel account '
                    f'you are connected to as a benefactor.</p>'
                    f'<p>This means their stories and memories will be preserved '
                    f'indefinitely for you and other benefactors to access.</p>'
                    f'<p>You can continue to view their content at any time by visiting '
                    f'<a href="{_FRONTEND_URL}/dashboard">{_FRONTEND_URL}</a>.</p>'
                    f'<p>Warm regards,<br>The SoulReel Team</p>'
                ),
                text_body=(
                    f'Hi {name},\n\n'
                    f'Legacy Protection has been activated for a SoulReel account '
                    f'you are connected to as a benefactor.\n\n'
                    f'Their stories and memories will be preserved indefinitely.\n\n'
                    f'Visit {_FRONTEND_URL}/dashboard to view their content.\n\n'
                    f'Warm regards,\nThe SoulReel Team'
                ),
                sender_email=_SENDER_EMAIL,
            )
        except Exception as exc:
            logger.error('[LEGACY_PROTECTION] Failed to notify benefactor %s: %s',
                         email, exc)


def _send_welcome_back_email(user_id):
    """Send welcome-back email when legacy protection is deactivated."""
    user_status_table = _dynamodb.Table(_TABLE_USER_STATUS)
    try:
        user = user_status_table.get_item(
            Key={'userId': user_id}
        ).get('Item', {})
        email = user.get('email', '')
        name = user.get('firstName', 'there')
        if not email:
            return

        send_email_with_retry(
            destination=email,
            subject='Welcome Back to SoulReel',
            html_body=(
                f'<h2>Welcome back, {name}!</h2>'
                f'<p>Your account has been restored from Legacy Protection mode. '
                f'All your content is accessible and your account is fully active.</p>'
                f'<p><a href="{_FRONTEND_URL}/dashboard">Continue your journey</a>.</p>'
                f'<p>Warm regards,<br>The SoulReel Team</p>'
            ),
            text_body=(
                f'Welcome back, {name}!\n\n'
                f'Your account has been restored from Legacy Protection mode. '
                f'All your content is accessible and your account is fully active.\n\n'
                f'Visit {_FRONTEND_URL}/dashboard to continue your journey.\n\n'
                f'Warm regards,\nThe SoulReel Team'
            ),
            sender_email=_SENDER_EMAIL,
        )
    except Exception as exc:
        logger.error('[LEGACY_PROTECTION] Failed to send welcome-back email: %s', exc)
