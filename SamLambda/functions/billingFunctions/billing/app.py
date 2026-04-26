"""
BillingFunction Lambda Handler

Single Lambda handling all authenticated billing endpoints plus the public
/billing/plans endpoint. Routes by path + httpMethod.

Endpoints:
  POST /billing/create-checkout-session  (Cognito Auth)
  GET  /billing/status                   (Cognito Auth)
  GET  /billing/portal                   (Cognito Auth)
  POST /billing/apply-coupon             (Cognito Auth)
  GET  /billing/plans                    (No Auth — public)

Requirements: 4.1-4.8, 6.1-6.4, 7.1-7.4, 8.1-8.10, 12.4, 12.5, 12.7
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

import boto3
import stripe

# Add shared layer to path
sys.path.append('/opt/python')

from cors import cors_headers
from responses import error_response
from structured_logger import StructuredLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_ssm = boto3.client('ssm')

_TABLE_NAME = os.environ.get('SUBSCRIPTIONS_TABLE', 'UserSubscriptionsDB')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')

# ---------------------------------------------------------------------------
# Module-level SSM caches (survive warm Lambda invocations)
# ---------------------------------------------------------------------------
_stripe_key_cache: dict = {}
_plan_cache: dict = {}
_plans_loaded: bool = False


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

def _get_stripe_key() -> str:
    """Retrieve the Stripe secret key from SSM (cached)."""
    if 'secret_key' not in _stripe_key_cache:
        resp = _ssm.get_parameter(
            Name='/soulreel/stripe/secret-key',
            WithDecryption=True,
        )
        _stripe_key_cache['secret_key'] = resp['Parameter']['Value']
    return _stripe_key_cache['secret_key']


def _load_all_plans() -> None:
    """Batch-load free + premium plan definitions from SSM in one call."""
    global _plans_loaded
    if _plans_loaded:
        return
    try:
        resp = _ssm.get_parameters(
            Names=['/soulreel/plans/free', '/soulreel/plans/premium'],
        )
        for param in resp.get('Parameters', []):
            plan_id = param['Name'].split('/')[-1]
            _plan_cache[plan_id] = json.loads(param['Value'])
        _plans_loaded = True
    except Exception as exc:
        logger.error('[BILLING] Failed to load plan definitions from SSM: %s', exc)


def _get_plan_definition(plan_id: str) -> dict:
    """Return the plan definition for *plan_id*, falling back to a minimal free default."""
    _load_all_plans()
    if plan_id in _plan_cache:
        return _plan_cache[plan_id]
    return {
        'planId': 'free',
        'maxLevel': 1,
        'allowedQuestionCategories': ['life_story_reflections'],
        'maxBenefactors': 1,
        'accessConditionTypes': ['immediate'],
        'features': ['basic'],
    }


def _get_coupon(code: str) -> dict | None:
    """Read a coupon definition from SSM. Returns None if not found."""
    try:
        resp = _ssm.get_parameter(Name=f'/soulreel/coupons/{code}')
        return json.loads(resp['Parameter']['Value'])
    except _ssm.exceptions.ParameterNotFound:
        return None
    except Exception as exc:
        logger.error('[BILLING] Error reading coupon %s from SSM: %s', code, exc)
        return None


def _increment_coupon_redemptions(code: str, coupon_data: dict) -> None:
    """Increment currentRedemptions for a coupon in SSM."""
    try:
        coupon_data['currentRedemptions'] = coupon_data.get('currentRedemptions', 0) + 1
        _ssm.put_parameter(
            Name=f'/soulreel/coupons/{code}',
            Value=json.dumps(coupon_data),
            Type='String',
            Overwrite=True,
        )
    except Exception as exc:
        logger.error('[BILLING] Failed to increment redemptions for coupon %s: %s', code, exc)


# ===================================================================
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route requests by path + httpMethod."""
    log = StructuredLog(event, context)

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # Public endpoint — no auth required
    if path == '/billing/plans' and method == 'GET':
        return handle_get_plans(event)

    # All other endpoints require authentication
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event, log=log)

    try:
        if path == '/billing/create-checkout-session' and method == 'POST':
            return handle_create_checkout(event, user_id, log)
        elif path == '/billing/status' and method == 'GET':
            return handle_status(event, user_id)
        elif path == '/billing/portal' and method == 'GET':
            return handle_portal(event, user_id)
        elif path == '/billing/apply-coupon' and method == 'POST':
            return handle_apply_coupon(event, user_id, log)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[BILLING] Unhandled error on %s %s: %s', method, path, exc)
        log.error('UnexpectedFailure', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event, log=log)


# ===================================================================
# Handler: POST /billing/create-checkout-session
# ===================================================================

def handle_create_checkout(event, user_id, log):
    """Create a Stripe Checkout Session for subscription upgrade."""
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, TypeError):
        body = {}

    price_id = body.get('priceId')
    if not price_id:
        return cors_response(400, {'error': 'Missing priceId'}, event)

    stripe.api_key = _get_stripe_key()
    table = _dynamodb.Table(_TABLE_NAME)

    # Check for existing Stripe Customer
    record = table.get_item(Key={'userId': user_id}).get('Item', {})
    customer_id = record.get('stripeCustomerId')

    if not customer_id:
        # Create a new Stripe Customer
        customer = stripe.Customer.create(
            metadata={'userId': user_id},
        )
        customer_id = customer.id

        # Store the customer ID
        now_iso = datetime.now(timezone.utc).isoformat()
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET stripeCustomerId = :cid, updatedAt = :now',
            ExpressionAttributeValues={
                ':cid': customer_id,
                ':now': now_iso,
            },
        )

    # Create Checkout Session
    checkout_params = dict(
        customer=customer_id,
        mode='subscription',
        line_items=[{'price': price_id, 'quantity': 1}],
        success_url=f'{_FRONTEND_URL}/dashboard?checkout=success',
        cancel_url=f'{_FRONTEND_URL}/pricing?checkout=canceled',
        metadata={'userId': user_id},
        allow_promotion_codes=True,
    )

    # Apply coupon discount if provided (e.g., founding member pricing)
    coupon_id = body.get('couponId')
    if coupon_id:
        checkout_params['discounts'] = [{'coupon': coupon_id}]
        # Disable promotion codes when a specific coupon is applied
        checkout_params['allow_promotion_codes'] = False

    session = stripe.checkout.Session.create(**checkout_params)

    log.info('CheckoutSessionCreated', details={'priceId': price_id})

    return cors_response(200, {'sessionUrl': session.url}, event)


# ===================================================================
# Handler: GET /billing/status
# ===================================================================

def handle_status(event, user_id):
    """Return the user's subscription status with plan limits."""
    table = _dynamodb.Table(_TABLE_NAME)
    resp = table.get_item(Key={'userId': user_id})
    item = resp.get('Item')

    # Always load plan definitions so we can return freePlanLimits
    free_plan_def = _get_plan_definition('free')

    if not item:
        # No subscription record — return free plan defaults
        return cors_response(200, {
            'planId': 'free',
            'status': 'active',
            'currentPeriodEnd': None,
            'couponCode': None,
            'couponExpiresAt': None,
            'billingInterval': None,
            'benefactorCount': 0,
            'level1CompletionPercent': 0,
            'level1CompletedAt': None,
            'totalQuestionsCompleted': 0,
            'planLimits': free_plan_def,
            'freePlanLimits': free_plan_def,
        }, event)

    plan_id = item.get('planId', 'free')
    plan_def = _get_plan_definition(plan_id)

    return cors_response(200, {
        'planId': plan_id,
        'status': item.get('status', 'active'),
        'currentPeriodEnd': item.get('currentPeriodEnd'),
        'couponCode': item.get('couponCode'),
        'couponExpiresAt': item.get('couponExpiresAt'),
        'billingInterval': item.get('billingInterval'),
        'benefactorCount': int(item.get('benefactorCount', 0)),
        'level1CompletionPercent': int(item.get('level1CompletionPercent', 0)),
        'level1CompletedAt': item.get('level1CompletedAt'),
        'totalQuestionsCompleted': int(item.get('totalQuestionsCompleted', 0)),
        'planLimits': plan_def,
        'freePlanLimits': free_plan_def,
    }, event)


# ===================================================================
# Handler: GET /billing/portal
# ===================================================================

def handle_portal(event, user_id):
    """Create a Stripe Billing Portal Session and return the URL."""
    table = _dynamodb.Table(_TABLE_NAME)
    resp = table.get_item(Key={'userId': user_id})
    item = resp.get('Item', {})

    customer_id = item.get('stripeCustomerId')
    if not customer_id:
        return cors_response(400, {'error': 'No billing account found'}, event)

    stripe.api_key = _get_stripe_key()

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f'{_FRONTEND_URL}/dashboard',
    )

    return cors_response(200, {'portalUrl': session.url}, event)


# ===================================================================
# Handler: POST /billing/apply-coupon
# ===================================================================

def handle_apply_coupon(event, user_id, log):
    """Validate and apply a coupon code."""
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, TypeError):
        body = {}

    code = body.get('code', '').strip()
    if not code:
        return cors_response(400, {'error': 'Missing coupon code'}, event)

    # Read coupon from SSM
    coupon = _get_coupon(code)
    if not coupon:
        return cors_response(400, {'error': 'Invalid coupon code'}, event)

    # Validate expiration
    expires_at = coupon.get('expiresAt')
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expiry < datetime.now(timezone.utc):
                return cors_response(400, {'error': 'This coupon has expired'}, event)
        except (ValueError, AttributeError):
            pass

    # Validate redemption limit
    max_redemptions = coupon.get('maxRedemptions', 0)
    current_redemptions = coupon.get('currentRedemptions', 0)
    if max_redemptions > 0 and current_redemptions >= max_redemptions:
        return cors_response(400, {'error': 'This coupon has reached its redemption limit'}, event)

    # Check if user already has an active premium plan
    table = _dynamodb.Table(_TABLE_NAME)
    resp = table.get_item(Key={'userId': user_id})
    item = resp.get('Item', {})

    if item.get('status') == 'active' and item.get('planId') == 'premium':
        return cors_response(400, {'error': 'You already have an active plan'}, event)

    coupon_type = coupon.get('type')
    now_iso = datetime.now(timezone.utc).isoformat()

    if coupon_type == 'forever_free':
        table.put_item(Item={
            'userId': user_id,
            'planId': 'premium',
            'status': 'comped',
            'couponCode': code,
            'couponType': 'forever_free',
            'benefactorCount': int(item.get('benefactorCount', 0)),
            'createdAt': item.get('createdAt', now_iso),
            'updatedAt': now_iso,
            # Preserve existing Stripe fields if present
            **({k: item[k] for k in ('stripeCustomerId', 'stripeSubscriptionId') if k in item}),
        })
        _increment_coupon_redemptions(code, coupon)
        log.info('CouponApplied', details={'code': code, 'type': 'forever_free'})
        return cors_response(200, {
            'success': True,
            'type': 'forever_free',
            'planId': 'premium',
            'message': 'You have lifetime Premium access',
        }, event)

    elif coupon_type == 'time_limited':
        duration_days = coupon.get('durationDays', 30)
        expires = datetime.now(timezone.utc) + timedelta(days=duration_days)
        coupon_expires_iso = expires.isoformat()

        table.put_item(Item={
            'userId': user_id,
            'planId': 'premium',
            'status': 'trialing',
            'couponCode': code,
            'couponType': 'time_limited',
            'couponExpiresAt': coupon_expires_iso,
            'benefactorCount': int(item.get('benefactorCount', 0)),
            'createdAt': item.get('createdAt', now_iso),
            'updatedAt': now_iso,
            **({k: item[k] for k in ('stripeCustomerId', 'stripeSubscriptionId') if k in item}),
        })
        _increment_coupon_redemptions(code, coupon)
        log.info('CouponApplied', details={'code': code, 'type': 'time_limited', 'durationDays': duration_days})
        return cors_response(200, {
            'success': True,
            'type': 'time_limited',
            'planId': 'premium',
            'expiresAt': coupon_expires_iso,
            'message': f'{duration_days} days of free Premium access',
        }, event)

    elif coupon_type == 'percentage':
        # No DB write — return the Stripe coupon ID for frontend to use at checkout
        return cors_response(200, {
            'success': True,
            'type': 'percentage',
            'stripeCouponId': coupon.get('stripeCouponId', ''),
            'message': f"{coupon.get('percentOff', 0)}% off — apply at checkout",
        }, event)

    else:
        return cors_response(400, {'error': 'Invalid coupon type'}, event)


# ===================================================================
# Handler: GET /billing/plans (public — no auth required)
# ===================================================================

def handle_get_plans(event):
    """Return plan definitions and founding member availability for the public pricing page."""
    _load_all_plans()

    plans = {}
    for plan_id in ('free', 'premium'):
        plans[plan_id] = _get_plan_definition(plan_id)

    # Check founding member coupon availability
    founding_member_available = False
    founding_member_slots_remaining = 0
    premium_def = plans.get('premium', {})
    founding_code = premium_def.get('foundingMemberCouponCode')

    if founding_code:
        coupon = _get_coupon(founding_code)
        if coupon:
            max_r = coupon.get('maxRedemptions', 0)
            cur_r = coupon.get('currentRedemptions', 0)
            if max_r > 0 and cur_r < max_r:
                founding_member_available = True
                founding_member_slots_remaining = max_r - cur_r

    return cors_response(200, {
        'plans': plans,
        'foundingMemberAvailable': founding_member_available,
        'foundingMemberSlotsRemaining': founding_member_slots_remaining,
    }, event)
