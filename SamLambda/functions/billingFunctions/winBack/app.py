"""
WinBackFunction Lambda Handler

EventBridge-triggered daily. Scans UserSubscriptionsDB for users whose trial
expired 3-4 days ago (status=expired, trialExpiresAt between 3 and 4 days ago).

For each match:
  1. Auto-generates a single-use percentage coupon code
  2. Creates the coupon in SSM at /soulreel/coupons/{code}
  3. Creates a corresponding Stripe Coupon via stripe.Coupon.create()
  4. Sends an SES email with the coupon code and link to /pricing

Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6
"""
import os
import json
import logging
import time
from datetime import datetime, timezone, timedelta

import boto3
import stripe
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_dynamodb = boto3.resource('dynamodb')
_ssm = boto3.client('ssm')
_ses = boto3.client('ses')

_TABLE_NAME = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')

# Module-level Stripe key cache
_stripe_key_cache: dict = {}


def _get_stripe_key() -> str:
    """Retrieve the Stripe secret key from SSM (cached)."""
    if 'secret_key' not in _stripe_key_cache:
        resp = _ssm.get_parameter(
            Name='/soulreel/stripe/secret-key',
            WithDecryption=True,
        )
        _stripe_key_cache['secret_key'] = resp['Parameter']['Value']
    return _stripe_key_cache['secret_key']


def lambda_handler(event, context):
    """Entry point for the daily win-back job."""
    now = datetime.now(timezone.utc)
    logger.info('[WINBACK] Starting win-back scan at %s', now.isoformat())

    table = _dynamodb.Table(_TABLE_NAME)

    # Find users whose trial expired 3-4 days ago
    target_users = _scan_winback_cohort(table, now)
    logger.info('[WINBACK] Found %d users in win-back window', len(target_users))

    sent = 0
    failed = 0
    for user in target_users:
        try:
            _process_winback_user(user, now)
            sent += 1
        except Exception as exc:
            logger.error(
                '[WINBACK] Failed to process userId=%s: %s',
                user.get('userId'), exc,
            )
            failed += 1

    logger.info('[WINBACK] Completed: %d sent, %d failed', sent, failed)
    return {'sent': sent, 'failed': failed}


def _scan_winback_cohort(table, now: datetime) -> list[dict]:
    """Scan for status=expired with trialExpiresAt between 3 and 4 days ago."""
    three_days_ago = (now - timedelta(days=4)).isoformat()
    four_days_upper = (now - timedelta(days=3)).isoformat()

    users: list[dict] = []
    params = {
        'FilterExpression': (
            Attr('status').eq('expired')
            & Attr('trialExpiresAt').gte(three_days_ago)
            & Attr('trialExpiresAt').lt(four_days_upper)
        ),
    }

    while True:
        resp = table.scan(**params)
        users.extend(resp.get('Items', []))
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        params['ExclusiveStartKey'] = last_key

    return users


def _process_winback_user(user: dict, now: datetime) -> None:
    """Generate coupon, create in SSM + Stripe, send email."""
    user_id = user['userId']
    user_email = user.get('email', '')

    # If no email on the subscription record, we can't send — skip
    if not user_email:
        logger.warning('[WINBACK] No email for userId=%s, skipping', user_id)
        return

    # 1. Generate coupon code
    ts = int(time.time())
    coupon_code = f'WINBACK-{user_id[:8]}-{ts}'
    expires_at = (now + timedelta(hours=48)).isoformat()

    # 2. Create coupon in SSM
    coupon_data = {
        'code': coupon_code,
        'type': 'percentage',
        'percentOff': 50,
        'durationMonths': 1,
        'stripeCouponId': coupon_code,
        'maxRedemptions': 1,
        'currentRedemptions': 0,
        'expiresAt': expires_at,
        'createdBy': 'system-winback',
    }
    _ssm.put_parameter(
        Name=f'/soulreel/coupons/{coupon_code}',
        Value=json.dumps(coupon_data),
        Type='String',
        Overwrite=False,
    )
    logger.info('[WINBACK] Created SSM coupon %s for userId=%s', coupon_code, user_id)

    # 3. Create corresponding Stripe Coupon
    stripe.api_key = _get_stripe_key()
    stripe.Coupon.create(
        id=coupon_code,
        percent_off=50,
        duration='repeating',
        duration_in_months=1,
        max_redemptions=1,
        redeem_by=int((now + timedelta(hours=48)).timestamp()),
    )
    logger.info('[WINBACK] Created Stripe coupon %s', coupon_code)

    # 4. Send SES email
    pricing_url = f'{_FRONTEND_URL}/pricing'
    _send_winback_email(user_email, coupon_code, pricing_url)
    logger.info('[WINBACK] Sent win-back email to userId=%s', user_id)


def _send_winback_email(to_email: str, coupon_code: str, pricing_url: str) -> None:
    """Send the win-back email via SES."""
    subject = 'Your SoulReel stories are waiting'
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>We miss you at SoulReel</h2>
        <p>During your trial, you started preserving the moments that matter most.
        Your stories are safe, but you can't add new ones to Life Events or
        Values &amp; Emotions until you upgrade.</p>
        <p>Here's a special offer just for you:</p>
        <p style="font-size: 18px; font-weight: bold; color: #6B46C1;">
            50% off your first month with code: {coupon_code}
        </p>
        <p>This offer expires in 48 hours.</p>
        <p>
            <a href="{pricing_url}" style="display: inline-block; padding: 12px 24px;
               background-color: #6B46C1; color: white; text-decoration: none;
               border-radius: 6px;">
                Subscribe Now
            </a>
        </p>
        <p style="font-size: 12px; color: #888;">
            If you no longer wish to receive these emails, you can ignore this message.
        </p>
    </body>
    </html>
    """
    text_body = (
        f'We miss you at SoulReel! '
        f'Get 50% off your first month with code: {coupon_code}. '
        f'This offer expires in 48 hours. '
        f'Subscribe now: {pricing_url}'
    )

    _ses.send_email(
        Source=_SENDER_EMAIL,
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            'Body': {
                'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                'Text': {'Data': text_body, 'Charset': 'UTF-8'},
            },
        },
    )
