import os
import boto3
from structured_logger import StructuredLog


def lambda_handler(event, context):
    log = StructuredLog(event, context)
    log.info('MetricsCollectionStarted')

    cloudwatch = boto3.client('cloudwatch')
    dynamodb = boto3.resource('dynamodb')

    user_status_table = dynamodb.Table(os.environ.get('TABLE_USER_STATUS', 'userStatusDB'))
    subscriptions_table = dynamodb.Table(os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB'))

    metrics = []

    # --- Registered Legacy Makers ---
    try:
        legacy_makers = _count_by_attribute(user_status_table, 'personaType', 'legacy_maker')
        metrics.append(('RegisteredLegacyMakers', legacy_makers))
        log.info('MetricCollected', details={'metric': 'RegisteredLegacyMakers', 'value': legacy_makers})
    except Exception as e:
        log.error('MetricCollectionFailed', e, details={'metric': 'RegisteredLegacyMakers'})

    # --- Registered Legacy Benefactors ---
    try:
        legacy_benefactors = _count_by_attribute(user_status_table, 'personaType', 'legacy_benefactor')
        metrics.append(('RegisteredLegacyBenefactors', legacy_benefactors))
        log.info('MetricCollected', details={'metric': 'RegisteredLegacyBenefactors', 'value': legacy_benefactors})
    except Exception as e:
        log.error('MetricCollectionFailed', e, details={'metric': 'RegisteredLegacyBenefactors'})

    # --- Trial Subscriptions ---
    try:
        trial_count = _count_by_attribute(subscriptions_table, 'status', 'trialing')
        metrics.append(('TrialSubscriptions', trial_count))
        log.info('MetricCollected', details={'metric': 'TrialSubscriptions', 'value': trial_count})
    except Exception as e:
        log.error('MetricCollectionFailed', e, details={'metric': 'TrialSubscriptions'})

    # --- Paid Subscriptions ---
    try:
        paid_count = _count_paid_subscriptions(subscriptions_table)
        metrics.append(('PaidSubscriptions', paid_count))
        log.info('MetricCollected', details={'metric': 'PaidSubscriptions', 'value': paid_count})
    except Exception as e:
        log.error('MetricCollectionFailed', e, details={'metric': 'PaidSubscriptions'})

    # --- Publish all collected metrics ---
    if metrics:
        try:
            metric_data = [
                {
                    'MetricName': name,
                    'Value': value,
                    'Unit': 'Count'
                }
                for name, value in metrics
            ]
            cloudwatch.put_metric_data(
                Namespace='SoulReel/BusinessMetrics',
                MetricData=metric_data
            )
            log.info('MetricsPublished', details={'count': len(metrics)})
        except Exception as e:
            log.error('MetricsPublishFailed', e)

    log.info('MetricsCollectionComplete', details={'metricsCollected': len(metrics)})


def _count_by_attribute(table, attr_name, attr_value):
    """Scan a DynamoDB table and count items where attr_name == attr_value."""
    count = 0
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            if item.get(attr_name) == attr_value:
                count += 1
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        scan_kwargs['ExclusiveStartKey'] = last_key
    return count


def _count_paid_subscriptions(table):
    """Scan UserSubscriptionsDB and count where status='active' and planId='premium'."""
    count = 0
    scan_kwargs = {}
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            if item.get('status') == 'active' and item.get('planId') == 'premium':
                count += 1
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        scan_kwargs['ExclusiveStartKey'] = last_key
    return count
