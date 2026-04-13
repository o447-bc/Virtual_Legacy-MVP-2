"""
DormantAccountDetector Lambda Handler

Weekly scheduled function that identifies dormant accounts and sends
escalating re-engagement emails at 6/12/24 month thresholds.
Skips legacy_protected accounts. Flags accounts for legacy protection
evaluation when criteria are met.

Schedule:
  WeeklyDormancyScan — rate(7 days)

Requirements: 7.1–7.9
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
    """Handle weekly scheduled dormancy scan."""

    # Handle scheduled event (WeeklyDormancyScan)
    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        return handle_dormancy_scan(event)

    # Handle OPTIONS preflight (safe pattern even for schedule-only)
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    return cors_response(404, {'error': 'Not found'}, event)


# ===================================================================
# Handler: Weekly dormancy scan
# ===================================================================

def handle_dormancy_scan(event):
    """Scan userStatusDB for dormant accounts and send re-engagement emails."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
    user_status_table = _dynamodb.Table(_TABLE_USER_STATUS)
    subscriptions_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)

    # Get configurable thresholds from SSM via retention_config
    threshold_1 = get_config('dormancy-threshold-1')  # 180 days (6 months)
    threshold_2 = get_config('dormancy-threshold-2')  # 365 days (12 months)
    threshold_3 = get_config('dormancy-threshold-3')  # 730 days (24 months)
    lapse_days = get_config('legacy-protection-lapse-days')  # 365 days

    # Scan all users
    users = _scan_all_items(user_status_table)
    processed = 0
    emails_sent = 0
    flagged = 0

    for user in users:
        user_id = user.get('userId')
        last_login = user.get('lastLoginAt')
        if not user_id or not last_login:
            continue

        try:
            last_login_dt = datetime.fromisoformat(
                last_login.replace('Z', '+00:00')
            )
        except (ValueError, TypeError):
            continue

        dormancy_days = (now - last_login_dt).days
        if dormancy_days < threshold_1:
            continue  # Not dormant yet

        # Get existing dormancy state
        dormancy_record = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'dormancy_state'}
        ).get('Item', {})

        # Skip if legacy_protected
        legacy_record = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'legacy_protection'}
        ).get('Item', {})
        if legacy_record.get('status') == 'active':
            continue

        emails_already_sent = dormancy_record.get('emailsSent', {})
        user_email = user.get('email', '')

        # 6-month threshold
        if dormancy_days >= threshold_1 and '6mo' not in emails_already_sent:
            if user_email:
                _send_dormancy_email(user_email, '6mo', user.get('firstName', ''))
                emails_already_sent['6mo'] = now.isoformat()
                emails_sent += 1
                log_audit_event('dormancy_email_sent', user_id,
                                {'threshold': '6mo', 'dormancyDays': dormancy_days})

        # 12-month threshold
        if dormancy_days >= threshold_2 and '12mo' not in emails_already_sent:
            if user_email:
                _send_dormancy_email(user_email, '12mo', user.get('firstName', ''))
                emails_already_sent['12mo'] = now.isoformat()
                emails_sent += 1
                log_audit_event('dormancy_email_sent', user_id,
                                {'threshold': '12mo', 'dormancyDays': dormancy_days})

        # 24-month threshold: flag for legacy protection evaluation
        if dormancy_days >= threshold_3:
            should_flag = _check_legacy_protection_criteria(
                user_id, subscriptions_table, lapse_days, now
            )
            if should_flag:
                emails_already_sent['flagged'] = now.isoformat()
                flagged += 1

        # Update dormancy state record
        status = 'active'
        if dormancy_days >= threshold_3:
            status = 'flagged_for_legacy_protection' if flagged else 'dormant_24mo'
        elif dormancy_days >= threshold_2:
            status = 'dormant_12mo'
        elif dormancy_days >= threshold_1:
            status = 'dormant_6mo'

        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'dormancy_state',
            'status': status,
            'lastLoginAt': last_login,
            'emailsSent': emails_already_sent,
            'updatedAt': now.isoformat(),
        })
        processed += 1

    logger.info('[DORMANCY] Processed %d users, sent %d emails, flagged %d',
                processed, emails_sent, flagged)
    return {'processed': processed, 'emailsSent': emails_sent, 'flagged': flagged}


# ===================================================================
# Helpers
# ===================================================================

def _scan_all_items(table):
    """Scan a DynamoDB table, handling pagination."""
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    return items


def _check_legacy_protection_criteria(user_id, subscriptions_table, lapse_days, now):
    """Check if user meets criteria for legacy protection flagging."""
    # Check subscription lapsed >= lapse_days
    try:
        sub_record = subscriptions_table.get_item(
            Key={'userId': user_id}
        ).get('Item', {})
        lapsed_at = sub_record.get('subscriptionLapsedAt') or sub_record.get('canceledAt')
        if not lapsed_at:
            status = sub_record.get('subscriptionStatus', '')
            if status in ('active', 'trialing', 'comped'):
                return False  # Active subscription, don't flag
            # If no lapse date but not active, treat as lapsed from now
            return False
        lapsed_dt = datetime.fromisoformat(lapsed_at.replace('Z', '+00:00'))
        if (now - lapsed_dt).days < lapse_days:
            return False
    except Exception:
        return False

    # Check benefactors exist
    try:
        relationships_table = _dynamodb.Table(
            os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB')
        )
        response = relationships_table.query(
            KeyConditionExpression=Key('initiatorId').eq(user_id),
            Limit=1,
        )
        if not response.get('Items'):
            return False
    except Exception:
        return False

    return True


def _send_dormancy_email(email, threshold, first_name):
    """Send a dormancy re-engagement email."""
    name = first_name or 'there'

    if threshold == '6mo':
        subject = 'Your stories are waiting for you'
        html_body = (
            f'<h2>Hi {name},</h2>'
            f'<p>Your stories on SoulReel are waiting for you. '
            f'It\'s been a while since you last visited.</p>'
            f'<p>Your legacy content is safe and sound. '
            f'<a href="{_FRONTEND_URL}/dashboard">Come back and continue your journey</a>.</p>'
            f'<p>Warm regards,<br>The SoulReel Team</p>'
        )
        text_body = (
            f'Hi {name},\n\n'
            f'Your stories on SoulReel are waiting for you. '
            f'It\'s been a while since you last visited.\n\n'
            f'Your legacy content is safe and sound. '
            f'Visit {_FRONTEND_URL}/dashboard to continue your journey.\n\n'
            f'Warm regards,\nThe SoulReel Team'
        )
    else:
        subject = "Don't let your legacy go silent"
        html_body = (
            f'<h2>Hi {name},</h2>'
            f'<p>It\'s been over a year since you last visited SoulReel. '
            f'Your stories and memories are still preserved, but we miss you.</p>'
            f'<p>If you don\'t return, your account may eventually be placed '
            f'in Legacy Protection mode to preserve your content for your loved ones.</p>'
            f'<p><a href="{_FRONTEND_URL}/dashboard">Log in now</a> to keep your legacy alive.</p>'
            f'<p>Warm regards,<br>The SoulReel Team</p>'
        )
        text_body = (
            f'Hi {name},\n\n'
            f'It\'s been over a year since you last visited SoulReel. '
            f'Your stories and memories are still preserved, but we miss you.\n\n'
            f'If you don\'t return, your account may eventually be placed '
            f'in Legacy Protection mode to preserve your content for your loved ones.\n\n'
            f'Visit {_FRONTEND_URL}/dashboard to keep your legacy alive.\n\n'
            f'Warm regards,\nThe SoulReel Team'
        )

    try:
        send_email_with_retry(
            destination=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sender_email=_SENDER_EMAIL,
        )
    except Exception as exc:
        logger.error('[DORMANCY] Failed to send %s email to %s: %s',
                     threshold, email, exc)
