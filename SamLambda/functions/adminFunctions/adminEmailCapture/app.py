"""
Admin Email Capture — Cognito-authorized admin endpoints

Provides metrics, email list, test send, config management, and A/B test results
for the email capture nurture system.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Key, Attr

sys.path.insert(0, '/opt/python')

from cors import cors_headers
from admin_auth import verify_admin
from referral_utils import generate_referral_hash, generate_unsubscribe_token

TABLE_EMAIL_CAPTURE = os.environ.get('TABLE_EMAIL_CAPTURE', 'EmailCaptureDB')
SES_CONFIG_SET = os.environ.get('SES_CONFIGURATION_SET', 'soulreel-nurture')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')

dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')
ssm_client = boto3.client('ssm')
email_capture_table = dynamodb.Table(TABLE_EMAIL_CAPTURE)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _json_response(status_code, body, event):
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body, cls=DecimalEncoder),
    }


def _scan_all():
    """Scan entire EmailCapture table."""
    items = []
    last_key = None
    while True:
        kwargs = {}
        if last_key:
            kwargs['ExclusiveStartKey'] = last_key
        resp = email_capture_table.scan(**kwargs)
        items.extend(resp.get('Items', []))
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
    return items


def handle_get_metrics(event):
    """GET /admin/email-capture/metrics — aggregated metrics."""
    items = _scan_all()
    total = len(items)

    # Status breakdown
    status_counts = defaultdict(int)
    stage_counts = defaultdict(int)
    conversion_by_stage = defaultdict(int)
    conversion_by_source = defaultdict(lambda: {'total': 0, 'converted': 0})
    time_to_convert = []

    for item in items:
        status = item.get('statusGsi', 'active')
        status_counts[status] += 1

        stage = item.get('reminderStage', 0)
        if status == 'active':
            stage_counts[stage] += 1

        source = item.get('source', 'unknown')
        conversion_by_source[source]['total'] += 1

        if item.get('convertedAt'):
            conv_stage = item.get('convertedAtStage', 0)
            conversion_by_stage[conv_stage] += 1
            conversion_by_source[source]['converted'] += 1

            # Time to convert
            try:
                captured = datetime.fromisoformat(item['capturedAt'].replace('Z', '+00:00'))
                converted = datetime.fromisoformat(item['convertedAt'].replace('Z', '+00:00'))
                days = (converted - captured).total_seconds() / 86400
                time_to_convert.append(days)
            except Exception:
                pass

    converted_count = status_counts.get('converted', 0)
    conversion_rate = (converted_count / total * 100) if total > 0 else 0

    # Time to convert stats
    avg_ttc = sum(time_to_convert) / len(time_to_convert) if time_to_convert else 0
    sorted_ttc = sorted(time_to_convert)
    median_ttc = sorted_ttc[len(sorted_ttc) // 2] if sorted_ttc else 0

    # Weekly histogram
    ttc_histogram = defaultdict(int)
    for days in time_to_convert:
        week = int(days // 7) + 1
        ttc_histogram[f'Week {week}'] += 1

    # Bounce rate
    bounced = sum(1 for i in items if i.get('bounceStatus') == 'hard')
    bounce_rate = (bounced / total * 100) if total > 0 else 0

    # Referral stats
    referred = sum(1 for i in items if i.get('referredBy'))
    referred_converted = sum(1 for i in items if i.get('referredBy') and i.get('convertedAt'))

    # Source conversion rates
    source_rates = {}
    for src, data in conversion_by_source.items():
        rate = (data['converted'] / data['total'] * 100) if data['total'] > 0 else 0
        source_rates[src] = {'total': data['total'], 'converted': data['converted'], 'rate': round(rate, 1)}

    return _json_response(200, {
        'total': total,
        'conversionRate': round(conversion_rate, 1),
        'statusCounts': dict(status_counts),
        'stageCounts': dict(stage_counts),
        'conversionByStage': dict(conversion_by_stage),
        'conversionBySource': source_rates,
        'timeToConvert': {
            'average': round(avg_ttc, 1),
            'median': round(median_ttc, 1),
            'histogram': dict(ttc_histogram),
        },
        'bounceRate': round(bounce_rate, 1),
        'bouncedCount': bounced,
        'referrals': {
            'total': referred,
            'converted': referred_converted,
            'rate': round((referred_converted / referred * 100) if referred > 0 else 0, 1),
        },
    }, event)


def handle_get_emails(event):
    """GET /admin/email-capture/emails — paginated email list."""
    params = event.get('queryStringParameters') or {}
    status_filter = params.get('status')
    limit = int(params.get('limit', '50'))
    start_key = params.get('startKey')

    scan_kwargs = {'Limit': limit}
    if start_key:
        scan_kwargs['ExclusiveStartKey'] = json.loads(start_key)
    if status_filter:
        scan_kwargs['FilterExpression'] = Attr('statusGsi').eq(status_filter)

    resp = email_capture_table.scan(**scan_kwargs)

    return _json_response(200, {
        'items': resp.get('Items', []),
        'lastKey': resp.get('LastEvaluatedKey'),
        'count': resp.get('Count', 0),
    }, event)


def handle_test_send(event):
    """POST /admin/email-capture/test-send — manual reminder send."""
    body = json.loads(event.get('body') or '{}')
    email = body.get('email', '')

    if not email:
        return _json_response(400, {'error': 'Email is required'}, event)

    resp = email_capture_table.get_item(Key={'email': email})
    item = resp.get('Item')
    if not item:
        return _json_response(404, {'error': 'Email not found'}, event)

    stage = item.get('reminderStage', 0)
    variant = item.get('variant', 'A')

    try:
        secret = ssm_client.get_parameter(
            Name='/soulreel/email-nurture/unsubscribe-secret', WithDecryption=True
        )['Parameter']['Value']

        unsub_token = generate_unsubscribe_token(email, secret)
        ref_hash = generate_referral_hash(email, secret)
        api_base = os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')

        template_name = f'soulreel-nurture-stage-{stage}-{variant}'

        ses_client.send_templated_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [email]},
            Template=template_name,
            TemplateData=json.dumps({
                'email': email,
                'unsubscribe_url': f'{api_base}/email-capture/unsubscribe?token={unsub_token}',
                'signup_url': f'{api_base}/?signup=create-legacy',
                'referral_url': f'{api_base}/?ref={ref_hash}',
            }),
            # ConfigurationSetName temporarily disabled
            # ConfigurationSetName=SES_CONFIG_SET,
        )
        return _json_response(200, {'success': True, 'stage': stage, 'variant': variant}, event)
    except Exception as e:
        return _json_response(500, {'error': str(e)}, event)


def handle_update_config(event):
    """PUT /admin/email-capture/config — update SSM parameters."""
    body = json.loads(event.get('body') or '{}')

    if 'schedule' in body:
        ssm_client.put_parameter(
            Name='/soulreel/email-nurture/schedule',
            Value=json.dumps(body['schedule']),
            Type='String',
            Overwrite=True,
        )

    if 'paused' in body:
        ssm_client.put_parameter(
            Name='/soulreel/email-nurture/paused',
            Value='true' if body['paused'] else 'false',
            Type='String',
            Overwrite=True,
        )

    return _json_response(200, {'success': True}, event)


def handle_get_ab_results(event):
    """GET /admin/email-capture/ab-results — A/B test performance."""
    items = _scan_all()

    # Per-stage, per-variant stats
    stats = defaultdict(lambda: defaultdict(lambda: {
        'sent': 0, 'opened': 0, 'clicked': 0, 'converted': 0
    }))

    for item in items:
        variant = item.get('variant', 'A')
        stage = item.get('reminderStage', 0)
        stage_opens = item.get('stageOpens', {})
        stage_clicks = item.get('stageClicks', {})

        # Count sends per stage based on reminderStage
        for s in range(min(stage + 1, 6)):
            stats[str(s)][variant]['sent'] += 1

        # Count opens/clicks per stage
        for s, count in stage_opens.items():
            stats[s][variant]['opened'] += 1 if count > 0 else 0

        for s, count in stage_clicks.items():
            stats[s][variant]['clicked'] += 1 if count > 0 else 0

        # Conversion attribution
        if item.get('convertedAt'):
            conv_stage = str(item.get('convertedAtStage', 0))
            stats[conv_stage][variant]['converted'] += 1

    # Compute rates
    results = {}
    for stage_num, variants in stats.items():
        results[stage_num] = {}
        for v, data in variants.items():
            sent = data['sent']
            results[stage_num][v] = {
                'sent': sent,
                'openRate': round(data['opened'] / sent * 100, 1) if sent > 0 else 0,
                'clickRate': round(data['clicked'] / sent * 100, 1) if sent > 0 else 0,
                'conversionRate': round(data['converted'] / sent * 100, 1) if sent > 0 else 0,
            }

    return _json_response(200, {'stages': results}, event)


def lambda_handler(event, context):
    """Route requests based on HTTP method and path."""
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': '',
        }

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    try:
        if path.endswith('/metrics') and method == 'GET':
            return handle_get_metrics(event)
        elif path.endswith('/emails') and method == 'GET':
            return handle_get_emails(event)
        elif path.endswith('/test-send') and method == 'POST':
            return handle_test_send(event)
        elif path.endswith('/config') and method == 'PUT':
            return handle_update_config(event)
        elif path.endswith('/ab-results') and method == 'GET':
            return handle_get_ab_results(event)
        else:
            return _json_response(404, {'error': 'Not found'}, event)
    except Exception as e:
        print(f'[ERROR] Admin email capture handler failed: {e}')
        return _json_response(500, {'error': 'Internal server error'}, event)
