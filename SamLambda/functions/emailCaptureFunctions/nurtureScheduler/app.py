"""
Nurture Scheduler — Daily cron-triggered Lambda

Processes the email nurture sequence: advances stages, sends reminder emails,
handles expiry, and sends win-back emails at 6 months.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Attr

sys.path.insert(0, '/opt/python')

from referral_utils import generate_referral_hash, generate_unsubscribe_token

TABLE_EMAIL_CAPTURE = os.environ.get('TABLE_EMAIL_CAPTURE', 'EmailCaptureDB')
SES_CONFIG_SET = os.environ.get('SES_CONFIGURATION_SET', 'soulreel-nurture')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')

dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')
ssm_client = boto3.client('ssm')

email_capture_table = dynamodb.Table(TABLE_EMAIL_CAPTURE)

# Default schedule: days from capture for each stage transition
DEFAULT_SCHEDULE = {'stage1': 7, 'stage2': 14, 'stage3': 28, 'stage4': 56}
WINBACK_DAYS = 180

_ssm_cache = {}
_SSM_CACHE_TTL = 300


def _get_ssm_param(name: str) -> str:
    now = time.time()
    if name in _ssm_cache and now - _ssm_cache[name]['ts'] < _SSM_CACHE_TTL:
        return _ssm_cache[name]['value']
    try:
        resp = ssm_client.get_parameter(Name=name, WithDecryption=True)
        value = resp['Parameter']['Value']
        _ssm_cache[name] = {'value': value, 'ts': now}
        return value
    except Exception:
        return _ssm_cache.get(name, {}).get('value', '')


def _get_schedule() -> dict:
    """Read schedule intervals from SSM, falling back to defaults."""
    try:
        raw = _get_ssm_param('/soulreel/email-nurture/schedule')
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        pass
    return DEFAULT_SCHEDULE


def _is_paused() -> bool:
    return _get_ssm_param('/soulreel/email-nurture/paused') == 'true'


def _days_since(iso_timestamp: str) -> float:
    captured = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    return (datetime.now(timezone.utc) - captured).total_seconds() / 86400


def _send_email(email: str, stage: int, variant: str, secret: str):
    """Send a nurture email for the given stage and variant."""
    unsub_token = generate_unsubscribe_token(email, secret)
    ref_hash = generate_referral_hash(email, secret)

    api_base = os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')

    template_name = f'soulreel-nurture-stage-{stage}-{variant}'
    unsub_url = f'{api_base}/email-capture/unsubscribe?token={unsub_token}'
    signup_url = f'{api_base}/?signup=create-legacy'
    referral_url = f'{api_base}/?ref={ref_hash}'

    try:
        ses_client.send_templated_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [email]},
            Template=template_name,
            TemplateData=json.dumps({
                'email': email,
                'unsubscribe_url': unsub_url,
                'signup_url': signup_url,
                'referral_url': referral_url,
            }),
            ConfigurationSetName=SES_CONFIG_SET,
        )
        return True
    except ses_client.exceptions.TemplateDoesNotExistException:
        # B variant doesn't exist, fall back to A
        if variant == 'B':
            fallback = f'soulreel-nurture-stage-{stage}-A'
            try:
                ses_client.send_templated_email(
                    Source=SENDER_EMAIL,
                    Destination={'ToAddresses': [email]},
                    Template=fallback,
                    TemplateData=json.dumps({
                        'email': email,
                        'unsubscribe_url': unsub_url,
                        'signup_url': signup_url,
                        'referral_url': referral_url,
                    }),
                    ConfigurationSetName=SES_CONFIG_SET,
                )
                return True
            except Exception as e:
                print(f'[ERROR] Failed to send fallback email to {email} stage {stage}: {e}')
                return False
        print(f'[ERROR] Template {template_name} does not exist')
        return False
    except Exception as e:
        print(f'[ERROR] Failed to send email to {email} stage {stage}: {e}')
        return False


def _process_active_records(schedule: dict, secret: str):
    """Pass 1: Process active records for stage 0-4 transitions."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Scan for active records
    scan_kwargs = {
        'FilterExpression': (
            Attr('convertedAt').eq(None) &
            Attr('expiredAt').eq(None) &
            Attr('unsubscribedAt').eq(None) &
            (Attr('bounceStatus').eq(None) | Attr('bounceStatus').ne('hard'))
        ),
    }

    processed = 0
    last_key = None

    while True:
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = email_capture_table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            email = item['email']
            stage = item.get('reminderStage', 0)
            variant = item.get('variant', 'A')
            captured_at = item.get('capturedAt', '')

            if not captured_at:
                continue

            days = _days_since(captured_at)

            # Determine if a stage transition is needed
            new_stage = None
            if stage == 0 and days >= schedule.get('stage1', 7):
                new_stage = 1
            elif stage == 1 and days >= schedule.get('stage2', 14):
                new_stage = 2
            elif stage == 2 and days >= schedule.get('stage3', 28):
                new_stage = 3
            elif stage == 3 and days >= schedule.get('stage4', 56):
                new_stage = 4
            elif stage == 4:
                # Past stage 4 threshold — expire the record
                email_capture_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET expiredAt = :now, statusGsi = :status',
                    ExpressionAttributeValues={
                        ':now': now_iso,
                        ':status': 'expired',
                    },
                )
                processed += 1
                continue

            if new_stage is not None:
                # Send email and advance stage
                if _send_email(email, new_stage, variant, secret):
                    email_capture_table.update_item(
                        Key={'email': email},
                        UpdateExpression='SET reminderStage = :stage',
                        ExpressionAttributeValues={':stage': new_stage},
                    )
                    processed += 1

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f'[INFO] Pass 1 (active): processed {processed} records')


def _process_winback_records(secret: str):
    """Pass 2: Process expired records for win-back (stage 5)."""
    # Scan for win-back candidates
    scan_kwargs = {
        'FilterExpression': (
            Attr('expiredAt').ne(None) &
            Attr('reminderStage').eq(4) &
            Attr('convertedAt').eq(None) &
            Attr('unsubscribedAt').eq(None) &
            (Attr('bounceStatus').eq(None) | Attr('bounceStatus').ne('hard'))
        ),
    }

    processed = 0
    last_key = None

    while True:
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = email_capture_table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            email = item['email']
            variant = item.get('variant', 'A')
            captured_at = item.get('capturedAt', '')

            if not captured_at:
                continue

            days = _days_since(captured_at)
            if days < WINBACK_DAYS:
                continue

            # Send win-back email (stage 5)
            if _send_email(email, 5, variant, secret):
                email_capture_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET reminderStage = :stage',
                    ExpressionAttributeValues={':stage': 5},
                )
                processed += 1

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f'[INFO] Pass 2 (win-back): processed {processed} records')


def lambda_handler(event, context):
    """Daily scheduled handler for nurture email processing."""
    print('[INFO] Nurture scheduler started')

    # Check pause flag
    if _is_paused():
        print('[INFO] Nurture scheduler is paused, exiting')
        return {'statusCode': 200, 'body': 'Paused'}

    # Read configuration
    schedule = _get_schedule()
    secret = _get_ssm_param('/soulreel/email-nurture/unsubscribe-secret')

    if not secret:
        print('[ERROR] Unsubscribe secret not configured, exiting')
        return {'statusCode': 500, 'body': 'Missing configuration'}

    try:
        # Pass 1: Active records
        _process_active_records(schedule, secret)

        # Pass 2: Win-back candidates
        _process_winback_records(secret)

        print('[INFO] Nurture scheduler completed')
        return {'statusCode': 200, 'body': 'OK'}

    except Exception as e:
        print(f'[ERROR] Nurture scheduler failed: {e}')
        raise  # Let CloudWatch alarm catch repeated failures
