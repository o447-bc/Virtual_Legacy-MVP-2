"""
StorageLifecycleManager Lambda Handler

Weekly reconciliation of per-user storage metrics, Glacier transitions
for legacy-protected content, reactivation restore handling, and
admin storage report endpoint.

Endpoints:
  GET /admin/storage-report (Cognito Auth + Admin)

Schedule:
  WeeklyReconciliation — rate(7 days)

Async invocation:
  Reactivation restore from StripeWebhookFunction

Requirements: 3.1–3.9, 10.1–10.4
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

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
_cloudwatch = boto3.client('cloudwatch')
_ssm = boto3.client('ssm')

_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')

# Cost rates per GB per month (approximate)
COST_RATES = {
    'STANDARD': 0.023,
    'INTELLIGENT_TIERING': 0.023,
    'GLACIER': 0.004,
    'DEEP_ARCHIVE': 0.00099,
    'GLACIER_IR': 0.01,
}


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code: int, body: dict, event: dict = None) -> dict:
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body, default=str),
    }


# ===================================================================
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route by event source: schedule, API, or async invocation."""

    # Handle scheduled event (WeeklyReconciliation)
    if event.get('source') == 'aws.events' or event.get('detail-type') == 'Scheduled Event':
        return handle_weekly_reconciliation(event)

    # Handle async reactivation restore invocation
    if event.get('source') == 'reactivation_restore':
        return handle_reactivation_restore(event)

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    try:
        if path == '/admin/storage-report' and method == 'GET':
            return handle_storage_report(event)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[STORAGE_LIFECYCLE] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Handler: Weekly reconciliation
# ===================================================================

def handle_weekly_reconciliation(event):
    """Reconcile per-user storage metrics and manage Glacier transitions."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    glacier_transition_days = get_config('glacier-transition-days')
    glacier_no_access_days = get_config('glacier-no-access-days')

    # Get all unique user prefixes from S3
    user_metrics = {}
    for prefix_type in ['conversations/', 'user-responses/']:
        paginator = _s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=prefix_type, Delimiter='/'):
            for common_prefix in page.get('CommonPrefixes', []):
                user_prefix = common_prefix['Prefix']
                # Extract userId from prefix like conversations/userId/
                parts = user_prefix.strip('/').split('/')
                if len(parts) >= 2:
                    user_id = parts[1]
                    if user_id not in user_metrics:
                        user_metrics[user_id] = {
                            'totalBytes': 0,
                            'bytesStandard': 0,
                            'bytesIntelligentTiering': 0,
                            'bytesGlacier': 0,
                            'contentItemCount': 0,
                        }

    # Calculate per-user metrics
    for user_id, metrics in user_metrics.items():
        for prefix_type in ['conversations/', 'user-responses/']:
            user_prefix = f'{prefix_type}{user_id}/'
            paginator = _s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=user_prefix):
                for obj in page.get('Contents', []):
                    size = obj.get('Size', 0)
                    storage_class = obj.get('StorageClass', 'STANDARD')
                    metrics['totalBytes'] += size
                    metrics['contentItemCount'] += 1
                    if storage_class in ('GLACIER', 'DEEP_ARCHIVE'):
                        metrics['bytesGlacier'] += size
                    elif storage_class == 'INTELLIGENT_TIERING':
                        metrics['bytesIntelligentTiering'] += size
                    else:
                        metrics['bytesStandard'] += size

    # Update storage_metrics records and handle Glacier transitions
    total_platform_bytes = 0
    total_platform_cost = 0.0

    for user_id, metrics in user_metrics.items():
        cost = _calculate_monthly_cost(metrics)
        total_platform_bytes += metrics['totalBytes']
        total_platform_cost += cost

        # Check legacy protection status for Glacier transitions
        legacy_record = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'legacy_protection'}
        ).get('Item', {})

        existing_metrics = retention_table.get_item(
            Key={'userId': user_id, 'recordType': 'storage_metrics'}
        ).get('Item', {})

        current_tier = 'STANDARD'
        if metrics['bytesGlacier'] > metrics['bytesStandard'] + metrics['bytesIntelligentTiering']:
            current_tier = 'DEEP_ARCHIVE'
        elif metrics['bytesIntelligentTiering'] > metrics['bytesStandard']:
            current_tier = 'INTELLIGENT_TIERING'

        # Glacier transition for legacy-protected content
        if legacy_record.get('status') == 'active':
            activated_at = legacy_record.get('activatedAt', '')
            last_access = existing_metrics.get('lastBenefactorAccessAt', '')
            if _should_transition_to_glacier(activated_at, last_access,
                                              glacier_transition_days,
                                              glacier_no_access_days, now):
                _transition_user_to_glacier(user_id)
                current_tier = 'DEEP_ARCHIVE'
                log_audit_event('storage_tier_transition', user_id,
                                {'fromTier': 'STANDARD', 'toTier': 'DEEP_ARCHIVE',
                                 'reason': 'legacy_protection_glacier_transition'})

        # Preserve simulated flag if present
        simulated = existing_metrics.get('simulated', False)
        if simulated:
            current_tier = existing_metrics.get('currentTier', current_tier)

        # Determine lifecycle status
        status = existing_metrics.get('status', 'active')

        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'storage_metrics',
            'status': status,
            'totalBytes': metrics['totalBytes'],
            'bytesStandard': metrics['bytesStandard'],
            'bytesIntelligentTiering': metrics['bytesIntelligentTiering'],
            'bytesGlacier': metrics['bytesGlacier'],
            'contentItemCount': metrics['contentItemCount'],
            'estimatedMonthlyCostUsd': Decimal(str(round(cost, 4))),
            'currentTier': current_tier,
            'simulated': simulated,
            'lastBenefactorAccessAt': existing_metrics.get('lastBenefactorAccessAt', ''),
            'lastReconciliationAt': now.isoformat(),
            'updatedAt': now.isoformat(),
        })

    # Publish CloudWatch metrics
    try:
        _cloudwatch.put_metric_data(
            Namespace='SoulReel/Storage',
            MetricData=[
                {
                    'MetricName': 'TotalStorageBytes',
                    'Value': total_platform_bytes,
                    'Unit': 'Bytes',
                },
                {
                    'MetricName': 'EstimatedMonthlyCostUsd',
                    'Value': total_platform_cost,
                    'Unit': 'None',
                },
                {
                    'MetricName': 'TrackedUserCount',
                    'Value': len(user_metrics),
                    'Unit': 'Count',
                },
            ],
        )
    except Exception as exc:
        logger.error('[STORAGE_LIFECYCLE] CloudWatch metric publish failed: %s', exc)

    logger.info('[STORAGE_LIFECYCLE] Reconciled %d users, total %d bytes, $%.4f/mo',
                len(user_metrics), total_platform_bytes, total_platform_cost)
    return {'usersProcessed': len(user_metrics), 'totalBytes': total_platform_bytes}


# ===================================================================
# Handler: GET /admin/storage-report
# ===================================================================

def handle_storage_report(event):
    """Return aggregate storage metrics for admin dashboard."""
    # Verify admin user
    admin_user = _verify_admin(event)
    if not admin_user:
        return cors_response(403, {'error': 'Forbidden: admin access required'}, event)

    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Scan all storage_metrics records
    items = []
    response = retention_table.scan(
        FilterExpression=Attr('recordType').eq('storage_metrics')
    )
    items.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = retention_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression=Attr('recordType').eq('storage_metrics')
        )
        items.extend(response.get('Items', []))

    # Aggregate metrics
    aggregate = {
        'totalBytesStored': 0,
        'totalBytesStandard': 0,
        'totalBytesIntelligentTiering': 0,
        'totalBytesGlacier': 0,
        'estimatedMonthlyCostUsd': 0.0,
        'totalUsers': len(items),
        'totalContentItems': 0,
    }

    by_state = {}
    for item in items:
        aggregate['totalBytesStored'] += int(item.get('totalBytes', 0))
        aggregate['totalBytesStandard'] += int(item.get('bytesStandard', 0))
        aggregate['totalBytesIntelligentTiering'] += int(item.get('bytesIntelligentTiering', 0))
        aggregate['totalBytesGlacier'] += int(item.get('bytesGlacier', 0))
        aggregate['estimatedMonthlyCostUsd'] += float(item.get('estimatedMonthlyCostUsd', 0))
        aggregate['totalContentItems'] += int(item.get('contentItemCount', 0))

        status = item.get('status', 'active')
        if status not in by_state:
            by_state[status] = {'userCount': 0, 'totalBytes': 0, 'estimatedCostUsd': 0.0}
        by_state[status]['userCount'] += 1
        by_state[status]['totalBytes'] += int(item.get('totalBytes', 0))
        by_state[status]['estimatedCostUsd'] += float(item.get('estimatedMonthlyCostUsd', 0))

    avg_bytes = (aggregate['totalBytesStored'] / aggregate['totalUsers']
                 if aggregate['totalUsers'] > 0 else 0)

    return cors_response(200, {
        'aggregate': aggregate,
        'byLifecycleState': by_state,
        'averageBytesPerUser': avg_bytes,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
    }, event)


# ===================================================================
# Handler: Reactivation restore (async invocation)
# ===================================================================

def handle_reactivation_restore(event):
    """Restore user content from Glacier after resubscription."""
    user_id = event.get('userId')
    if not user_id:
        logger.error('[STORAGE_LIFECYCLE] Reactivation restore missing userId')
        return {'error': 'Missing userId'}

    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
    now = datetime.now(timezone.utc)

    # List all user objects in Glacier/Deep Archive
    glacier_objects = []
    for prefix_type in ['conversations/', 'user-responses/']:
        user_prefix = f'{prefix_type}{user_id}/'
        paginator = _s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=user_prefix):
            for obj in page.get('Contents', []):
                sc = obj.get('StorageClass', 'STANDARD')
                if sc in ('GLACIER', 'DEEP_ARCHIVE', 'GLACIER_IR'):
                    glacier_objects.append(obj)

    if not glacier_objects:
        logger.info('[STORAGE_LIFECYCLE] No Glacier objects for user %s', user_id)
        return {'status': 'no_glacier_content'}

    total_objects = len(glacier_objects)

    # Create reactivation_restore record
    retention_table.put_item(Item={
        'userId': user_id,
        'recordType': 'reactivation_restore',
        'status': 'in_progress',
        'totalObjects': total_objects,
        'restoredCount': 0,
        'startedAt': now.isoformat(),
        'updatedAt': now.isoformat(),
    })

    # Initiate restore for each object
    restored = 0
    for obj in glacier_objects:
        try:
            _s3.restore_object(
                Bucket=_S3_BUCKET,
                Key=obj['Key'],
                RestoreRequest={
                    'Days': 7,
                    'GlacierJobParameters': {'Tier': 'Standard'},
                },
            )
            restored += 1
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'RestoreAlreadyInProgress':
                restored += 1
            else:
                logger.error('[STORAGE_LIFECYCLE] Restore failed for %s: %s',
                             obj['Key'], exc)

    # Update record
    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'reactivation_restore'},
        UpdateExpression='SET restoredCount = :rc, updatedAt = :now',
        ExpressionAttributeValues={
            ':rc': restored,
            ':now': now.isoformat(),
        },
    )

    log_audit_event('glacier_retrieval_requested', user_id,
                    {'type': 'reactivation_restore', 'totalObjects': total_objects,
                     'restoreInitiated': restored})

    logger.info('[STORAGE_LIFECYCLE] Reactivation restore for %s: %d/%d initiated',
                user_id, restored, total_objects)
    return {'status': 'in_progress', 'totalObjects': total_objects, 'initiated': restored}


# ===================================================================
# Helpers
# ===================================================================

def _verify_admin(event):
    """Verify the caller is an admin user via Cognito groups."""
    claims = (event.get('requestContext', {})
              .get('authorizer', {})
              .get('claims', {}))
    groups = claims.get('cognito:groups', '')
    if 'admin' in groups.lower():
        return claims.get('sub')
    return None


def _calculate_monthly_cost(metrics):
    """Calculate estimated monthly storage cost from per-tier bytes."""
    bytes_to_gb = 1 / (1024 ** 3)
    cost = 0.0
    cost += metrics.get('bytesStandard', 0) * bytes_to_gb * COST_RATES['STANDARD']
    cost += metrics.get('bytesIntelligentTiering', 0) * bytes_to_gb * COST_RATES['INTELLIGENT_TIERING']
    cost += metrics.get('bytesGlacier', 0) * bytes_to_gb * COST_RATES['DEEP_ARCHIVE']
    return cost


def _should_transition_to_glacier(activated_at, last_access, transition_days,
                                   no_access_days, now):
    """Check if legacy-protected content should transition to Glacier."""
    if not activated_at:
        return False

    try:
        activated_dt = datetime.fromisoformat(activated_at.replace('Z', '+00:00'))
        days_protected = (now - activated_dt).days
        if days_protected < transition_days:
            return False
    except (ValueError, TypeError):
        return False

    if last_access:
        try:
            last_access_dt = datetime.fromisoformat(last_access.replace('Z', '+00:00'))
            days_no_access = (now - last_access_dt).days
            if days_no_access < no_access_days:
                return False
        except (ValueError, TypeError):
            pass
    # No access recorded means no recent access — eligible
    return True


def _transition_user_to_glacier(user_id):
    """Transition all user S3 objects to Glacier Deep Archive."""
    for prefix_type in ['conversations/', 'user-responses/']:
        user_prefix = f'{prefix_type}{user_id}/'
        paginator = _s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=user_prefix):
            for obj in page.get('Contents', []):
                sc = obj.get('StorageClass', 'STANDARD')
                if sc not in ('GLACIER', 'DEEP_ARCHIVE'):
                    try:
                        _s3.copy_object(
                            Bucket=_S3_BUCKET,
                            Key=obj['Key'],
                            CopySource={'Bucket': _S3_BUCKET, 'Key': obj['Key']},
                            StorageClass='DEEP_ARCHIVE',
                        )
                    except ClientError as exc:
                        logger.error('[STORAGE_LIFECYCLE] Glacier transition failed for %s: %s',
                                     obj['Key'], exc)
