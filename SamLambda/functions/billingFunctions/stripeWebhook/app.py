"""
StripeWebhookFunction Lambda Handler

Unauthenticated endpoint that receives webhook events from Stripe and
updates subscription state in DynamoDB. Verifies Stripe signature before
processing any event.

Handled events:
  - checkout.session.completed
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.payment_failed

Requirements: 5.1-5.12
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone

import boto3
import stripe

# Add shared layer to path
sys.path.append('/opt/python')

from cors import cors_headers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_ssm = boto3.client('ssm')
_lambda_client = boto3.client('lambda')
_ses = boto3.client('ses', region_name='us-east-1')

_TABLE_NAME = os.environ.get('SUBSCRIPTIONS_TABLE', 'UserSubscriptionsDB')
_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_DATA_EXPORT_FUNCTION = os.environ.get('DATA_EXPORT_FUNCTION', '')
_STORAGE_LIFECYCLE_FUNCTION = os.environ.get('STORAGE_LIFECYCLE_FUNCTION', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')

# ---------------------------------------------------------------------------
# Module-level SSM caches (survive warm Lambda invocations)
# ---------------------------------------------------------------------------
_ssm_cache: dict = {}

# ---------------------------------------------------------------------------
# Price-to-plan mapping (Stripe Price IDs → internal plan IDs)
# ---------------------------------------------------------------------------
PRICE_PLAN_MAP = {
    'price_1TL03V6hMyNf0PnbOaSd399o': 'premium',  # Premium Monthly
    'price_1TL06w6hMyNf0PnbCgehYyZB': 'premium',   # Premium Annual
}


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
# SSM helpers
# ===================================================================

def _get_ssm_secure(name: str) -> str:
    """Retrieve a SecureString SSM parameter (cached)."""
    if name not in _ssm_cache:
        resp = _ssm.get_parameter(Name=name, WithDecryption=True)
        _ssm_cache[name] = resp['Parameter']['Value']
    return _ssm_cache[name]


def _get_stripe_key() -> str:
    return _get_ssm_secure('/soulreel/stripe/secret-key')


def _get_webhook_secret() -> str:
    return _get_ssm_secure('/soulreel/stripe/webhook-secret')


# ===================================================================
# GSI lookup helper
# ===================================================================

def _lookup_user_by_customer_id(customer_id: str) -> dict | None:
    """Query the stripeCustomerId GSI. Returns the item or None."""
    table = _dynamodb.Table(_TABLE_NAME)
    resp = table.query(
        IndexName='stripeCustomerId-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('stripeCustomerId').eq(customer_id),
        Limit=1,
    )
    items = resp.get('Items', [])
    if not items:
        return None
    return items[0]


# ===================================================================
# Request handler
# ===================================================================

def lambda_handler(event, context):
    """Verify Stripe signature, route by event type."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    # Extract payload and signature
    payload = event.get('body', '')
    headers = event.get('headers') or {}
    sig_header = headers.get('Stripe-Signature') or headers.get('stripe-signature')

    if not sig_header:
        logger.warning('[WEBHOOK] Missing Stripe-Signature header')
        return cors_response(400, {'error': 'Invalid signature'}, event)

    # Verify signature
    webhook_secret = _get_webhook_secret()
    try:
        stripe_event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning('[WEBHOOK] Signature verification failed: %s', exc)
        return cors_response(400, {'error': 'Invalid signature'}, event)
    except Exception as exc:
        logger.error('[WEBHOOK] Error constructing event: %s', exc)
        return cors_response(400, {'error': 'Invalid signature'}, event)

    event_id = getattr(stripe_event, 'id', 'unknown')
    event_type = getattr(stripe_event, 'type', 'unknown')
    logger.info('[WEBHOOK] Processing event %s type=%s', event_id, event_type)

    # Set Stripe API key for any API calls we need to make
    stripe.api_key = _get_stripe_key()

    try:
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(stripe_event, event)
        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(stripe_event, event)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(stripe_event, event)
        elif event_type == 'invoice.payment_failed':
            _handle_payment_failed(stripe_event, event)
        else:
            logger.info('[WEBHOOK] Unhandled event type: %s', event_type)
    except Exception as exc:
        logger.error('[WEBHOOK] Error processing %s event %s: %s', event_type, event_id, exc)
        # Return 500 so Stripe retries
        return cors_response(500, {'error': 'Processing error'}, event)

    return cors_response(200, {'received': True}, event)


# ===================================================================
# Event handlers
# ===================================================================

def _handle_checkout_completed(stripe_event, api_event):
    """
    Handle checkout.session.completed.

    Uses userId from session metadata (PK lookup, NOT GSI) to avoid
    GSI eventual consistency issues right after checkout.
    """
    session = stripe_event.data.object
    user_id = (getattr(session, 'metadata', None) or {}).get('userId')

    if not user_id:
        logger.warning('[WEBHOOK] checkout.session.completed without userId in metadata, event=%s',
                        getattr(stripe_event, 'id', 'unknown'))
        return

    logger.info('[WEBHOOK] checkout.session.completed userId=%s', user_id)

    customer_id = getattr(session, 'customer', None)
    subscription_id = getattr(session, 'subscription', None)

    # Retrieve subscription details from Stripe
    plan_id = 'premium'
    current_period_end = None
    if subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            current_period_end = datetime.fromtimestamp(
                sub.current_period_end, tz=timezone.utc
            ).isoformat()
            # Determine plan from price ID
            if hasattr(sub, 'items') and sub.items and sub.items.data:
                price_id = sub.items.data[0].price.id if sub.items.data[0].price else ''
                plan_id = PRICE_PLAN_MAP.get(price_id, 'premium')
        except Exception as exc:
            logger.error('[WEBHOOK] Error retrieving subscription %s: %s', subscription_id, exc)

    now_iso = datetime.now(timezone.utc).isoformat()
    table = _dynamodb.Table(_TABLE_NAME)

    # Use UpdateExpression to preserve benefactorCount from existing record
    table.update_item(
        Key={'userId': user_id},
        UpdateExpression=(
            'SET planId = :plan, #st = :status, '
            'stripeCustomerId = :cid, stripeSubscriptionId = :sid, '
            'currentPeriodEnd = :cpe, updatedAt = :now, '
            'createdAt = if_not_exists(createdAt, :now), '
            'benefactorCount = if_not_exists(benefactorCount, :zero) '
            'REMOVE trialExpiresAt'
        ),
        ExpressionAttributeNames={
            '#st': 'status',
        },
        ExpressionAttributeValues={
            ':plan': plan_id,
            ':status': 'active',
            ':cid': customer_id,
            ':sid': subscription_id,
            ':cpe': current_period_end,
            ':now': now_iso,
            ':zero': 0,
        },
    )

    # --- Check for Glacier content and trigger reactivation restore (Req 3.6) ---
    _check_and_trigger_reactivation_restore(user_id)


def _handle_subscription_updated(stripe_event, api_event):
    """
    Handle customer.subscription.updated.

    GSI lookup by stripeCustomerId, update status/planId/currentPeriodEnd.
    """
    subscription = stripe_event.data.object
    customer_id = getattr(subscription, 'customer', None)

    if not customer_id:
        logger.warning('[WEBHOOK] subscription.updated without customer, event=%s',
                        getattr(stripe_event, 'id', 'unknown'))
        return

    item = _lookup_user_by_customer_id(customer_id)
    if not item:
        logger.warning('[WEBHOOK] No user found for stripeCustomerId=%s, event=%s',
                        customer_id, getattr(stripe_event, 'id', 'unknown'))
        return

    user_id = item['userId']
    logger.info('[WEBHOOK] customer.subscription.updated userId=%s', user_id)

    # Determine plan from price
    plan_id = 'premium'
    if hasattr(subscription, 'items') and subscription.items and subscription.items.data:
        price_id = subscription.items.data[0].price.id if subscription.items.data[0].price else ''
        plan_id = PRICE_PLAN_MAP.get(price_id, 'premium')

    stripe_status = getattr(subscription, 'status', 'active')
    # Map Stripe status to our internal status
    status_map = {
        'active': 'active',
        'past_due': 'past_due',
        'canceled': 'canceled',
        'unpaid': 'past_due',
        'trialing': 'trialing',
        'incomplete': 'past_due',
        'incomplete_expired': 'canceled',
    }
    status = status_map.get(stripe_status, 'active')

    current_period_end = None
    if getattr(subscription, 'current_period_end', None):
        current_period_end = datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        ).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()
    table = _dynamodb.Table(_TABLE_NAME)

    # Use UpdateExpression to preserve benefactorCount
    table.update_item(
        Key={'userId': user_id},
        UpdateExpression=(
            'SET planId = :plan, #st = :status, '
            'currentPeriodEnd = :cpe, updatedAt = :now'
        ),
        ExpressionAttributeNames={
            '#st': 'status',
        },
        ExpressionAttributeValues={
            ':plan': plan_id,
            ':status': status,
            ':cpe': current_period_end,
            ':now': now_iso,
        },
    )


def _handle_subscription_deleted(stripe_event, api_event):
    """
    Handle customer.subscription.deleted.

    GSI lookup, set planId=free, status=canceled.
    Send lapse reassurance email (Req 9.4) and trigger auto-export (Req 2.1).
    """
    subscription = stripe_event.data.object
    customer_id = getattr(subscription, 'customer', None)

    if not customer_id:
        logger.warning('[WEBHOOK] subscription.deleted without customer, event=%s',
                        getattr(stripe_event, 'id', 'unknown'))
        return

    item = _lookup_user_by_customer_id(customer_id)
    if not item:
        logger.warning('[WEBHOOK] No user found for stripeCustomerId=%s, event=%s',
                        customer_id, getattr(stripe_event, 'id', 'unknown'))
        return

    user_id = item['userId']
    logger.info('[WEBHOOK] customer.subscription.deleted userId=%s', user_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    table = _dynamodb.Table(_TABLE_NAME)

    # Use UpdateExpression to preserve benefactorCount
    table.update_item(
        Key={'userId': user_id},
        UpdateExpression=(
            'SET planId = :plan, #st = :status, updatedAt = :now'
        ),
        ExpressionAttributeNames={
            '#st': 'status',
        },
        ExpressionAttributeValues={
            ':plan': 'free',
            ':status': 'canceled',
            ':now': now_iso,
        },
    )

    # --- Lapse reassurance email (Req 9.4) ---
    _send_lapse_reassurance_email(item)

    # --- Trigger async auto-export (Req 2.1) ---
    _trigger_auto_export(user_id)


def _handle_payment_failed(stripe_event, api_event):
    """
    Handle invoice.payment_failed.

    GSI lookup, set status=past_due.
    """
    invoice = stripe_event.data.object
    customer_id = getattr(invoice, 'customer', None)

    if not customer_id:
        logger.warning('[WEBHOOK] payment_failed without customer, event=%s',
                        getattr(stripe_event, 'id', 'unknown'))
        return

    item = _lookup_user_by_customer_id(customer_id)
    if not item:
        logger.warning('[WEBHOOK] No user found for stripeCustomerId=%s, event=%s',
                        customer_id, getattr(stripe_event, 'id', 'unknown'))
        return

    user_id = item['userId']
    logger.info('[WEBHOOK] invoice.payment_failed userId=%s', user_id)

    now_iso = datetime.now(timezone.utc).isoformat()
    table = _dynamodb.Table(_TABLE_NAME)

    # Use UpdateExpression to preserve benefactorCount
    table.update_item(
        Key={'userId': user_id},
        UpdateExpression=(
            'SET #st = :status, updatedAt = :now'
        ),
        ExpressionAttributeNames={
            '#st': 'status',
        },
        ExpressionAttributeValues={
            ':status': 'past_due',
            ':now': now_iso,
        },
    )


# ===================================================================
# Data retention lifecycle helpers
# ===================================================================

def _send_lapse_reassurance_email(user_item: dict) -> None:
    """Send reassurance email when subscription lapses (Req 9.4)."""
    email = user_item.get('email') or user_item.get('userEmail', '')
    if not email:
        logger.warning('[WEBHOOK] No email found for user %s, skipping lapse reassurance',
                        user_item.get('userId', 'unknown'))
        return

    try:
        subject = 'Your SoulReel Content Is Safe'
        html_body = (
            '<h2>Your subscription has ended, but your stories are safe</h2>'
            '<p>We wanted to reassure you that all your recordings, transcripts, '
            'and AI conversation summaries remain fully accessible to your benefactors. '
            'Nothing has been deleted or archived.</p>'
            '<p>Your content is always yours — all recordings remain accessible '
            'regardless of your plan.</p>'
            f'<p><a href="{_FRONTEND_URL}/pricing">Resubscribe anytime</a> to unlock '
            'Premium features like data export.</p>'
            '<p>Warm regards,<br/>The SoulReel Team</p>'
        )
        text_body = (
            'Your subscription has ended, but your stories are safe.\n\n'
            'All your recordings, transcripts, and AI conversation summaries '
            'remain fully accessible to your benefactors. Nothing has been deleted.\n\n'
            'Your content is always yours — all recordings remain accessible '
            'regardless of your plan.\n\n'
            f'Resubscribe anytime at {_FRONTEND_URL}/pricing to unlock Premium features.\n\n'
            'Warm regards,\nThe SoulReel Team'
        )
        _ses.send_email(
            Source=_SENDER_EMAIL,
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body},
                },
            },
        )
        logger.info('[WEBHOOK] Lapse reassurance email sent to %s', email)
    except Exception as exc:
        logger.error('[WEBHOOK] Failed to send lapse reassurance email: %s', exc)


def _trigger_auto_export(user_id: str) -> None:
    """Trigger async auto-export via DataExportFunction (Req 2.1)."""
    if not _DATA_EXPORT_FUNCTION:
        logger.warning('[WEBHOOK] DATA_EXPORT_FUNCTION not configured, skipping auto-export')
        return

    try:
        payload = json.dumps({
            'source': 'auto_export_on_cancellation',
            'userId': user_id,
        })
        _lambda_client.invoke(
            FunctionName=_DATA_EXPORT_FUNCTION,
            InvocationType='Event',  # async
            Payload=payload,
        )
        logger.info('[WEBHOOK] Auto-export triggered for userId=%s', user_id)
    except Exception as exc:
        logger.error('[WEBHOOK] Failed to trigger auto-export for userId=%s: %s',
                      user_id, exc)


def _check_and_trigger_reactivation_restore(user_id: str) -> None:
    """Check for Glacier content and trigger reactivation restore (Req 3.6)."""
    if not _STORAGE_LIFECYCLE_FUNCTION:
        logger.warning('[WEBHOOK] STORAGE_LIFECYCLE_FUNCTION not configured, '
                        'skipping reactivation restore check')
        return

    try:
        # Check DataRetentionDB for storage_metrics to see if user has Glacier content
        retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
        resp = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'storage_metrics'},
        )
        metrics = resp.get('Item')
        if not metrics:
            logger.info('[WEBHOOK] No storage metrics for userId=%s, no restore needed', user_id)
            return

        # Check if any content is in Glacier or Deep Archive
        glacier_bytes = int(metrics.get('glacierBytes', 0) or 0)
        deep_archive_bytes = int(metrics.get('deepArchiveBytes', 0) or 0)
        simulated_tier = metrics.get('simulatedTier', '')

        needs_restore = (
            glacier_bytes > 0
            or deep_archive_bytes > 0
            or simulated_tier in ('GLACIER', 'DEEP_ARCHIVE')
        )

        if not needs_restore:
            logger.info('[WEBHOOK] No Glacier content for userId=%s, no restore needed', user_id)
            return

        # Trigger reactivation restore via StorageLifecycleManager
        payload = json.dumps({
            'source': 'reactivation_restore',
            'userId': user_id,
        })
        _lambda_client.invoke(
            FunctionName=_STORAGE_LIFECYCLE_FUNCTION,
            InvocationType='Event',  # async
            Payload=payload,
        )
        logger.info('[WEBHOOK] Reactivation restore triggered for userId=%s', user_id)
    except Exception as exc:
        logger.error('[WEBHOOK] Failed to check/trigger reactivation restore for userId=%s: %s',
                      user_id, exc)
