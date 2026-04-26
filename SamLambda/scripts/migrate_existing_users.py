#!/usr/bin/env python3
"""
One-time migration script: Add V2 pricing fields to existing UserSubscriptionsDB records.

What it does:
  1. Scans all records in UserSubscriptionsDB
  2. For each record, adds missing V2 fields:
     - level1CompletionPercent (default 0)
     - totalQuestionsCompleted (default 0)
     - level1CompletedAt (default null)
  3. Converts expired trial users (status=trialing, trialExpiresAt in the past)
     to free plan (planId=free, status=expired)

Idempotent: Uses if_not_exists() for new fields so running multiple times
is safe. Does NOT overwrite existing values.

Usage:
  python3 scripts/migrate_existing_users.py [--dry-run]

  --dry-run: Print what would be done without making changes
"""
import argparse
import sys
from datetime import datetime, timezone

import boto3

TABLE_NAME = 'UserSubscriptionsDB'


def migrate(dry_run: bool = False):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(TABLE_NAME)

    print(f"{'[DRY RUN] ' if dry_run else ''}Scanning {TABLE_NAME}...")

    updated = 0
    expired_converted = 0
    skipped = 0
    errors = 0

    params = {}
    while True:
        resp = table.scan(**params)
        items = resp.get('Items', [])

        for item in items:
            user_id = item.get('userId')
            if not user_id:
                continue

            try:
                # Check if trial needs converting
                needs_trial_conversion = (
                    item.get('status') == 'trialing'
                    and item.get('trialExpiresAt')
                    and _is_expired(item['trialExpiresAt'])
                )

                if needs_trial_conversion:
                    if dry_run:
                        print(f"  [CONVERT] {user_id}: trialing → free/expired")
                    else:
                        table.update_item(
                            Key={'userId': user_id},
                            UpdateExpression=(
                                'SET planId = :free, #st = :expired, '
                                'level1CompletionPercent = if_not_exists(level1CompletionPercent, :zero), '
                                'totalQuestionsCompleted = if_not_exists(totalQuestionsCompleted, :zero), '
                                'updatedAt = :now'
                            ),
                            ExpressionAttributeNames={'#st': 'status'},
                            ExpressionAttributeValues={
                                ':free': 'free',
                                ':expired': 'expired',
                                ':zero': 0,
                                ':now': datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    expired_converted += 1
                else:
                    # Just add missing V2 fields
                    if dry_run:
                        print(f"  [UPDATE] {user_id}: add V2 fields (if missing)")
                    else:
                        table.update_item(
                            Key={'userId': user_id},
                            UpdateExpression=(
                                'SET '
                                'level1CompletionPercent = if_not_exists(level1CompletionPercent, :zero), '
                                'totalQuestionsCompleted = if_not_exists(totalQuestionsCompleted, :zero), '
                                'updatedAt = :now'
                            ),
                            ExpressionAttributeValues={
                                ':zero': 0,
                                ':now': datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    updated += 1

            except Exception as e:
                print(f"  [ERROR] {user_id}: {e}")
                errors += 1

        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        params['ExclusiveStartKey'] = last_key

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migration complete:")
    print(f"  Updated: {updated}")
    print(f"  Expired trials converted: {expired_converted}")
    print(f"  Errors: {errors}")


def _is_expired(iso_timestamp: str) -> bool:
    """Check if an ISO timestamp is in the past."""
    try:
        expiry = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return expiry < datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate existing users to V2 pricing fields')
    parser.add_argument('--dry-run', action='store_true', help='Print changes without applying')
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
