"""
AccountDeletionFunction Lambda Handler

Handles account deletion requests with a configurable grace period,
cancellation during grace, status queries, and daily processing of
expired deletions with cascading cleanup.

Endpoints:
  POST /account/delete-request   (Cognito Auth) — Request account deletion
  POST /account/cancel-deletion  (Cognito Auth) — Cancel pending deletion
  GET  /account/deletion-status  (Cognito Auth) — Check deletion status

Schedule:
  DailyDeletionScan — Process pending deletions past grace period

Requirements: 5.1–5.10, 14.1–14.4, 16.2
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
_s3 = boto3.client('s3')
_cognito = boto3.client('cognito-idp')
_ssm = boto3.client('ssm')

_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_TABLE_SUBSCRIPTIONS = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')
_TABLE_QUESTION_STATUS = os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB')
_TABLE_QUESTION_PROGRESS = os.environ.get('TABLE_QUESTION_PROGRESS', 'userQuestionLevelProgressDB')
_TABLE_USER_STATUS = os.environ.get('TABLE_USER_STATUS', 'userStatusDB')
_TABLE_RELATIONSHIPS = os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB')
_TABLE_ENGAGEMENT = os.environ.get('TABLE_ENGAGEMENT', 'EngagementDB')
_TABLE_ACCESS_CONDITIONS = os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB')
_TABLE_CONVERSATION_STATE = os.environ.get('CONVERSATION_STATE_TABLE', 'ConversationStateDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')
_COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')


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
    """Route requests by path + httpMethod, or handle scheduled events."""

    # Handle scheduled event (DailyDeletionScan)
    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        return handle_process_deletions(event)

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # All endpoints require authentication
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        if path == '/account/delete-request' and method == 'POST':
            return handle_delete_request(event, user_id)
        elif path == '/account/cancel-deletion' and method == 'POST':
            return handle_cancel_deletion(event, user_id)
        elif path == '/account/deletion-status' and method == 'GET':
            return handle_deletion_status(event, user_id)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[ACCOUNT_DELETION] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Handler: POST /account/delete-request
# ===================================================================

def handle_delete_request(event, user_id):
    """Create a new account deletion request with grace period."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # 1. Rate limit check (one deletion request per N days)
    rate_limit_days = get_config('export-rate-limit-days')
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'deletion_request'}
    ).get('Item')

    if existing:
        last_requested = existing.get('requestedAt', '')
        if last_requested:
            last_dt = datetime.fromisoformat(last_requested.replace('Z', '+00:00'))
            if (now - last_dt).days < rate_limit_days:
                return cors_response(429, {
                    'error': f'Deletion rate limit: one request per {rate_limit_days} days',
                    'nextAvailable': (last_dt + timedelta(days=rate_limit_days)).isoformat(),
                }, event)

        # 2. Check for existing pending deletion
        existing_status = existing.get('status', '')
        if existing_status == 'pending':
            return cors_response(409, {
                'error': 'A deletion request is already pending',
                'graceEndDate': existing.get('graceEndDate', ''),
                'status': 'pending',
            }, event)

    # 3. Calculate grace period end date
    grace_days = get_config('deletion-grace-period')
    grace_end = now + timedelta(days=grace_days)

    # 4. Create deletion record
    retention_table.put_item(Item={
        'userId': user_id,
        'recordType': 'deletion_request',
        'status': 'pending',
        'requestedAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'graceEndDate': grace_end.isoformat(),
    })

    # 5. Send confirmation email
    user_email = _get_user_email(user_id)
    if user_email:
        send_email_with_retry(
            destination=user_email,
            subject='SoulReel — Account Deletion Request Received',
            html_body=_build_deletion_request_email_html(grace_end, grace_days),
            text_body=(
                f'Your account deletion request has been received.\n'
                f'Your data will be permanently deleted on {grace_end.strftime("%B %d, %Y")}.\n'
                f'You have {grace_days} days to cancel this request.\n'
                f'To cancel: {_FRONTEND_URL}/your-data'
            ),
            sender_email=_SENDER_EMAIL,
        )

    # 6. Audit log
    log_audit_event('deletion_requested', user_id, {
        'graceEndDate': grace_end.isoformat(),
        'graceDays': grace_days,
    }, initiator='user')

    return cors_response(200, {
        'status': 'pending',
        'graceEndDate': grace_end.isoformat(),
        'message': f'Account deletion scheduled. You have {grace_days} days to cancel.',
    }, event)


# ===================================================================
# Handler: POST /account/cancel-deletion
# ===================================================================

def handle_cancel_deletion(event, user_id):
    """Cancel a pending account deletion during the grace period."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'deletion_request'}
    ).get('Item')

    if not existing:
        return cors_response(404, {
            'error': 'No deletion request found',
        }, event)

    current_status = existing.get('status', '')

    if current_status == 'completed':
        return cors_response(410, {
            'error': 'Deletion has already been completed and cannot be reversed',
        }, event)

    if current_status != 'pending':
        return cors_response(404, {
            'error': 'No active deletion request found',
        }, event)

    # Check if still within grace period
    grace_end_str = existing.get('graceEndDate', '')
    if grace_end_str:
        grace_end = datetime.fromisoformat(grace_end_str.replace('Z', '+00:00'))
        if now >= grace_end:
            return cors_response(410, {
                'error': 'Grace period has expired. Deletion may already be in progress.',
            }, event)

    # Cancel the deletion
    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'deletion_request'},
        UpdateExpression='SET #s = :s, updatedAt = :u, canceledAt = :c',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':s': 'canceled',
            ':u': now.isoformat(),
            ':c': now.isoformat(),
        },
    )

    # Send confirmation email
    user_email = _get_user_email(user_id)
    if user_email:
        send_email_with_retry(
            destination=user_email,
            subject='SoulReel — Account Deletion Canceled',
            html_body=_build_deletion_canceled_email_html(),
            text_body=(
                'Your account deletion has been canceled.\n'
                'Your content is safe and your account remains active.\n'
            ),
            sender_email=_SENDER_EMAIL,
        )

    # Audit log
    log_audit_event('deletion_canceled', user_id, {
        'canceledAt': now.isoformat(),
    }, initiator='user')

    return cors_response(200, {
        'status': 'canceled',
        'message': 'Account deletion has been canceled. Your content is safe.',
    }, event)


# ===================================================================
# Handler: GET /account/deletion-status
# ===================================================================

def handle_deletion_status(event, user_id):
    """Return the current deletion status for the user."""
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    resp = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'deletion_request'}
    )
    item = resp.get('Item')

    if not item:
        return cors_response(200, {
            'status': 'none',
            'message': 'No deletion request found',
        }, event)

    result = {
        'status': item.get('status', 'unknown'),
        'requestedAt': item.get('requestedAt', ''),
        'updatedAt': item.get('updatedAt', ''),
    }

    if item.get('graceEndDate'):
        result['graceEndDate'] = item['graceEndDate']
    if item.get('canceledAt'):
        result['canceledAt'] = item['canceledAt']
    if item.get('completedAt'):
        result['completedAt'] = item['completedAt']

    return cors_response(200, result, event)


# ===================================================================
# Handler: Scheduled — Process pending deletions past grace period
# ===================================================================

def handle_process_deletions(event):
    """Process all pending deletions whose grace period has expired."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Query status-index for pending deletions
    resp = retention_table.query(
        IndexName='status-index',
        KeyConditionExpression=Key('status').eq('pending'),
    )

    processed = 0
    errors = 0

    for item in resp.get('Items', []):
        grace_end_str = item.get('graceEndDate', '')
        if not grace_end_str:
            continue

        grace_end = datetime.fromisoformat(grace_end_str.replace('Z', '+00:00'))
        if now < grace_end:
            continue  # Still within grace period

        # Only process deletion_request records
        if item.get('recordType') != 'deletion_request':
            continue

        user_id = item.get('userId')
        if not user_id:
            continue

        try:
            _execute_deletion(user_id, now, retention_table)
            processed += 1
        except Exception as exc:
            logger.error('[ACCOUNT_DELETION] Failed to delete user %s: %s', user_id, exc)
            errors += 1

    # Handle pagination
    while resp.get('LastEvaluatedKey'):
        resp = retention_table.query(
            IndexName='status-index',
            KeyConditionExpression=Key('status').eq('pending'),
            ExclusiveStartKey=resp['LastEvaluatedKey'],
        )
        for item in resp.get('Items', []):
            grace_end_str = item.get('graceEndDate', '')
            if not grace_end_str:
                continue
            grace_end = datetime.fromisoformat(grace_end_str.replace('Z', '+00:00'))
            if now < grace_end:
                continue
            if item.get('recordType') != 'deletion_request':
                continue
            user_id = item.get('userId')
            if not user_id:
                continue
            try:
                _execute_deletion(user_id, now, retention_table)
                processed += 1
            except Exception as exc:
                logger.error('[ACCOUNT_DELETION] Failed to delete user %s: %s', user_id, exc)
                errors += 1

    logger.info('[ACCOUNT_DELETION] Processed %d deletions, %d errors', processed, errors)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed,
            'errors': errors,
        }),
    }


def _execute_deletion(user_id, now, retention_table):
    """Execute cascading deletion for a single user."""

    # 1. Cancel Stripe subscription (best-effort)
    _cancel_stripe_subscription(user_id)

    # 2. Delete S3 objects
    _delete_s3_objects(user_id)

    # 3. Delete DynamoDB records from all tables
    _delete_dynamodb_records(user_id)

    # 4. Notify affected benefactors
    _notify_benefactors(user_id)

    # 5. Delete Cognito user
    _delete_cognito_user(user_id)

    # 6. Update deletion record to completed
    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'deletion_request'},
        UpdateExpression='SET #s = :s, updatedAt = :u, completedAt = :c',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':s': 'completed',
            ':u': now.isoformat(),
            ':c': now.isoformat(),
        },
    )

    # 7. Audit log
    log_audit_event('deletion_completed', user_id, {
        'completedAt': now.isoformat(),
        'dataCategories': [
            's3_content', 'question_responses', 'question_progress',
            'user_status', 'subscriptions', 'conversation_state',
            'engagement', 'access_conditions', 'relationships', 'cognito_account',
        ],
    }, initiator='system')


def _cancel_stripe_subscription(user_id):
    """Cancel Stripe subscription for the user (best-effort)."""
    try:
        import stripe

        # Get Stripe API key from SSM
        stripe_key_resp = _ssm.get_parameter(
            Name='/soulreel/stripe/secret-key',
            WithDecryption=True,
        )
        stripe.api_key = stripe_key_resp['Parameter']['Value']

        # Get subscription info
        sub_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)
        sub_resp = sub_table.get_item(Key={'userId': user_id})
        sub_item = sub_resp.get('Item', {})
        stripe_sub_id = sub_item.get('stripeSubscriptionId', '')

        if stripe_sub_id and sub_item.get('status') in ('active', 'trialing', 'past_due'):
            stripe.Subscription.cancel(stripe_sub_id)
            logger.info('[ACCOUNT_DELETION] Canceled Stripe subscription %s for %s',
                        stripe_sub_id, user_id)
    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to cancel Stripe subscription for %s: %s',
                       user_id, exc)


def _delete_s3_objects(user_id):
    """Delete all S3 objects for the user."""
    for prefix in [f'conversations/{user_id}/', f'user-responses/{user_id}/']:
        try:
            paginator = _s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=prefix):
                objects = page.get('Contents', [])
                if objects:
                    delete_keys = [{'Key': obj['Key']} for obj in objects]
                    _s3.delete_objects(
                        Bucket=_S3_BUCKET,
                        Delete={'Objects': delete_keys},
                    )
        except ClientError as exc:
            logger.warning('[ACCOUNT_DELETION] Failed to delete S3 objects for %s prefix %s: %s',
                           user_id, prefix, exc)


def _delete_dynamodb_records(user_id):
    """Delete user records from all DynamoDB tables."""
    # Tables with simple userId key
    _delete_from_table(_TABLE_QUESTION_STATUS, 'UserId', user_id, is_query=True)
    _delete_from_table(_TABLE_QUESTION_PROGRESS, 'UserId', user_id, is_query=True)
    _delete_from_table(_TABLE_USER_STATUS, 'UserId', user_id, is_single=True)
    _delete_from_table(_TABLE_SUBSCRIPTIONS, 'userId', user_id, is_single=True)
    _delete_from_table(_TABLE_ENGAGEMENT, 'userId', user_id, is_single=True)

    # ConversationState — query by userId
    _delete_from_table(_TABLE_CONVERSATION_STATE, 'userId', user_id, is_query=True)

    # PersonaRelationships — query by makerId
    _delete_relationships(user_id)

    # AccessConditions — query by makerId
    _delete_access_conditions(user_id)

    # DataRetentionDB — delete all records EXCEPT the deletion_request record
    _delete_retention_records(user_id)


def _delete_from_table(table_name, pk_name, pk_value, is_single=False, is_query=False):
    """Delete records from a DynamoDB table."""
    try:
        table = _dynamodb.Table(table_name)
        if is_single:
            table.delete_item(Key={pk_name: pk_value})
        elif is_query:
            resp = table.query(
                KeyConditionExpression=Key(pk_name).eq(pk_value)
            )
            for item in resp.get('Items', []):
                key = {k: item[k] for k in table.key_schema
                       if item.get(k) is not None} if hasattr(table, 'key_schema') else {pk_name: pk_value}
                # Build key from the item's actual key attributes
                table.delete_item(Key=_extract_key(table, item))
            while resp.get('LastEvaluatedKey'):
                resp = table.query(
                    KeyConditionExpression=Key(pk_name).eq(pk_value),
                    ExclusiveStartKey=resp['LastEvaluatedKey'],
                )
                for item in resp.get('Items', []):
                    table.delete_item(Key=_extract_key(table, item))
    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to delete from %s: %s', table_name, exc)


def _extract_key(table, item):
    """Extract the key attributes from a DynamoDB item based on table schema."""
    key = {}
    for schema in table.key_schema:
        attr_name = schema['AttributeName']
        if attr_name in item:
            key[attr_name] = item[attr_name]
    return key


def _delete_relationships(user_id):
    """Delete PersonaRelationships records where user is the maker."""
    try:
        table = _dynamodb.Table(_TABLE_RELATIONSHIPS)
        resp = table.query(
            KeyConditionExpression=Key('makerId').eq(user_id)
        )
        for item in resp.get('Items', []):
            table.delete_item(Key=_extract_key(table, item))
        while resp.get('LastEvaluatedKey'):
            resp = table.query(
                KeyConditionExpression=Key('makerId').eq(user_id),
                ExclusiveStartKey=resp['LastEvaluatedKey'],
            )
            for item in resp.get('Items', []):
                table.delete_item(Key=_extract_key(table, item))
    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to delete relationships for %s: %s',
                       user_id, exc)


def _delete_access_conditions(user_id):
    """Delete AccessConditions records for the user."""
    try:
        table = _dynamodb.Table(_TABLE_ACCESS_CONDITIONS)
        resp = table.query(
            KeyConditionExpression=Key('makerId').eq(user_id)
        )
        for item in resp.get('Items', []):
            table.delete_item(Key=_extract_key(table, item))
        while resp.get('LastEvaluatedKey'):
            resp = table.query(
                KeyConditionExpression=Key('makerId').eq(user_id),
                ExclusiveStartKey=resp['LastEvaluatedKey'],
            )
            for item in resp.get('Items', []):
                table.delete_item(Key=_extract_key(table, item))
    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to delete access conditions for %s: %s',
                       user_id, exc)


def _delete_retention_records(user_id):
    """Delete DataRetentionDB records except the deletion_request."""
    try:
        table = _dynamodb.Table(_TABLE_DATA_RETENTION)
        resp = table.query(
            KeyConditionExpression=Key('userId').eq(user_id)
        )
        for item in resp.get('Items', []):
            if item.get('recordType') != 'deletion_request':
                table.delete_item(Key={
                    'userId': user_id,
                    'recordType': item['recordType'],
                })
        while resp.get('LastEvaluatedKey'):
            resp = table.query(
                KeyConditionExpression=Key('userId').eq(user_id),
                ExclusiveStartKey=resp['LastEvaluatedKey'],
            )
            for item in resp.get('Items', []):
                if item.get('recordType') != 'deletion_request':
                    table.delete_item(Key={
                        'userId': user_id,
                        'recordType': item['recordType'],
                    })
    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to delete retention records for %s: %s',
                       user_id, exc)


def _notify_benefactors(user_id):
    """Notify all benefactors that the maker's account has been deleted."""
    try:
        table = _dynamodb.Table(_TABLE_RELATIONSHIPS)
        resp = table.query(
            KeyConditionExpression=Key('makerId').eq(user_id)
        )
        benefactors = resp.get('Items', [])

        for ben in benefactors:
            ben_email = ben.get('visitorEmail', '')
            maker_name = ben.get('makerName', 'a legacy maker')
            if ben_email:
                try:
                    send_email_with_retry(
                        destination=ben_email,
                        subject='SoulReel — Shared Content No Longer Available',
                        html_body=_build_benefactor_notification_email_html(maker_name),
                        text_body=(
                            f'{maker_name} has deleted their SoulReel account.\n'
                            f'The shared content is no longer available.\n'
                            f'We understand this may be difficult. If you have questions, '
                            f'please contact support@soulreel.net'
                        ),
                        sender_email=_SENDER_EMAIL,
                    )
                except Exception as exc:
                    logger.warning('[ACCOUNT_DELETION] Failed to notify benefactor %s: %s',
                                   ben.get('visitorId', ''), exc)

            # Audit log for each benefactor access revocation
            log_audit_event('benefactor_access_revoked', user_id, {
                'benefactorId': ben.get('visitorId', ''),
                'reason': 'account_deletion',
            }, initiator='system')

    except Exception as exc:
        logger.warning('[ACCOUNT_DELETION] Failed to notify benefactors for %s: %s',
                       user_id, exc)


def _delete_cognito_user(user_id):
    """Delete the Cognito user account."""
    if not _COGNITO_USER_POOL_ID:
        logger.warning('[ACCOUNT_DELETION] COGNITO_USER_POOL_ID not set, skipping Cognito deletion')
        return

    try:
        _cognito.admin_delete_user(
            UserPoolId=_COGNITO_USER_POOL_ID,
            Username=user_id,
        )
        logger.info('[ACCOUNT_DELETION] Deleted Cognito user %s', user_id)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'UserNotFoundException':
            logger.info('[ACCOUNT_DELETION] Cognito user %s already deleted', user_id)
        else:
            logger.warning('[ACCOUNT_DELETION] Failed to delete Cognito user %s: %s',
                           user_id, exc)


# ===================================================================
# Shared helpers
# ===================================================================

def _get_user_email(user_id):
    """Get user email from Cognito."""
    try:
        resp = _cognito.admin_get_user(
            UserPoolId=_COGNITO_USER_POOL_ID,
            Username=user_id,
        )
        for attr in resp.get('UserAttributes', []):
            if attr['Name'] == 'email':
                return attr['Value']
        return ''
    except Exception as e:
        logger.warning('Failed to get user email for %s: %s', user_id, e)
        return ''


# ===================================================================
# Email templates
# ===================================================================

def _build_deletion_request_email_html(grace_end, grace_days):
    """Build HTML email for deletion request confirmation."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Account Deletion Request Received</h2>
<p>We've received your request to delete your SoulReel account.</p>
<p><strong>Your data will be permanently deleted on {grace_end.strftime('%B %d, %Y')}.</strong></p>
<p>You have <strong>{grace_days} days</strong> to change your mind. During this time:</p>
<ul>
<li>Your account and content remain fully accessible</li>
<li>Your benefactors can still view your shared content</li>
<li>You can cancel the deletion at any time</li>
</ul>
<p><a href="{_FRONTEND_URL}/your-data" style="display: inline-block; padding: 12px 24px;
background-color: #e74c3c; color: white; text-decoration: none; border-radius: 6px;">
Cancel Deletion</a></p>
<p style="color: #666;"><strong>After the grace period:</strong></p>
<ul style="color: #666;">
<li>All your recordings, transcripts, and summaries will be permanently deleted</li>
<li>Your benefactors will lose access to your shared content</li>
<li>This action cannot be undone</li>
</ul>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""


def _build_deletion_canceled_email_html():
    """Build HTML email for deletion cancellation confirmation."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Account Deletion Canceled</h2>
<p>Your account deletion has been canceled. Your content is safe.</p>
<p>All your recordings, stories, and shared content remain exactly as they were.
Your benefactors continue to have access to your shared legacy.</p>
<p><a href="{_FRONTEND_URL}" style="display: inline-block; padding: 12px 24px;
background-color: #4A90D9; color: white; text-decoration: none; border-radius: 6px;">
Return to SoulReel</a></p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""


def _build_benefactor_notification_email_html(maker_name):
    """Build HTML email notifying benefactors of account deletion."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Shared Content No Longer Available</h2>
<p>{maker_name} has chosen to delete their SoulReel account.</p>
<p>The recordings and stories that were shared with you are no longer available
on the platform.</p>
<p>We understand this may be difficult. The decision to delete was made by the
content creator, and we respect their right to manage their own data.</p>
<p>If you have any questions, please contact us at
<a href="mailto:support@soulreel.net">support@soulreel.net</a>.</p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""
