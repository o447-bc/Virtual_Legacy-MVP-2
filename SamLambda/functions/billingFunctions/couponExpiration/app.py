"""
CouponExpirationFunction Lambda Handler

EventBridge-triggered daily. Scans UserSubscriptionsDB for:
  1. Expired trials: status=trialing AND trialExpiresAt < now
  2. Expired time-limited coupons: couponType=time_limited AND couponExpiresAt < now

For each match, sets planId=free and status=expired.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""
import os
import logging
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_dynamodb = boto3.resource('dynamodb')
_TABLE_NAME = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')


def lambda_handler(event, context):
    """Entry point for the daily coupon/trial expiration job."""
    now = datetime.now(timezone.utc).isoformat()
    logger.info('[EXPIRATION] Starting expiration scan at %s', now)

    table = _dynamodb.Table(_TABLE_NAME)

    expired_trials = _scan_expired_trials(table, now)
    expired_coupons = _scan_expired_coupons(table, now)

    total = len(expired_trials) + len(expired_coupons)
    logger.info(
        '[EXPIRATION] Found %d expired trials and %d expired coupons (%d total)',
        len(expired_trials), len(expired_coupons), total,
    )

    failed = 0
    for user_id in expired_trials:
        if not _expire_record(table, user_id, 'trial'):
            failed += 1

    for user_id in expired_coupons:
        if not _expire_record(table, user_id, 'coupon'):
            failed += 1

    logger.info(
        '[EXPIRATION] Completed: %d transitioned, %d failed',
        total - failed, failed,
    )
    return {'expired': total - failed, 'failed': failed}


def _scan_expired_trials(table, now_iso: str) -> list[str]:
    """Scan for status=trialing with trialExpiresAt < now."""
    user_ids: list[str] = []
    params = {
        'FilterExpression': (
            Attr('status').eq('trialing') & Attr('trialExpiresAt').lt(now_iso)
        ),
        'ProjectionExpression': 'userId',
    }

    while True:
        resp = table.scan(**params)
        for item in resp.get('Items', []):
            user_ids.append(item['userId'])
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        params['ExclusiveStartKey'] = last_key

    return user_ids


def _scan_expired_coupons(table, now_iso: str) -> list[str]:
    """Scan for couponType=time_limited with couponExpiresAt < now."""
    user_ids: list[str] = []
    params = {
        'FilterExpression': (
            Attr('couponType').eq('time_limited') & Attr('couponExpiresAt').lt(now_iso)
        ),
        'ProjectionExpression': 'userId',
    }

    while True:
        resp = table.scan(**params)
        for item in resp.get('Items', []):
            user_ids.append(item['userId'])
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        params['ExclusiveStartKey'] = last_key

    return user_ids


def _expire_record(table, user_id: str, reason: str) -> bool:
    """Update a single record to planId=free, status=expired. Returns True on success."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET planId = :free, #s = :expired, updatedAt = :now',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':free': 'free',
                ':expired': 'expired',
                ':now': now,
            },
        )
        logger.info('[EXPIRATION] Expired %s for userId=%s', reason, user_id)
        return True
    except Exception as exc:
        logger.error('[EXPIRATION] Failed to expire %s for userId=%s: %s', reason, user_id, exc)
        return False
