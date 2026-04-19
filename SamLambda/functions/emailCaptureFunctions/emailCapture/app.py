"""
Email Capture API — POST /email-capture

Captures visitor email addresses from the landing page, stores them in DynamoDB,
and sends an immediate welcome email via SES.
"""
import os
import json
import re
import random
import sys
import time
from datetime import datetime, timezone

import boto3

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from referral_utils import generate_referral_hash, generate_unsubscribe_token
from structured_logger import StructuredLog

# Environment variables
TABLE_EMAIL_CAPTURE = os.environ.get('TABLE_EMAIL_CAPTURE', 'EmailCaptureDB')
TABLE_RATE_LIMIT = os.environ.get('TABLE_RATE_LIMIT', 'EmailCaptureRateLimitDB')
SES_CONFIG_SET = os.environ.get('SES_CONFIGURATION_SET', 'soulreel-nurture')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')

dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')
ssm_client = boto3.client('ssm')

email_capture_table = dynamodb.Table(TABLE_EMAIL_CAPTURE)
rate_limit_table = dynamodb.Table(TABLE_RATE_LIMIT)

# SSM parameter cache
_ssm_cache = {}
_SSM_CACHE_TTL = 300  # 5 minutes


def _get_ssm_param(name: str, log=None) -> str:
    """Read an SSM parameter with caching."""
    now = time.time()
    if name in _ssm_cache and now - _ssm_cache[name]['ts'] < _SSM_CACHE_TTL:
        return _ssm_cache[name]['value']
    try:
        resp = ssm_client.get_parameter(Name=name, WithDecryption=True)
        value = resp['Parameter']['Value']
        _ssm_cache[name] = {'value': value, 'ts': now}
        return value
    except Exception as e:
        if log:
            log.warning('SSMReadFailed', f'Failed to read SSM parameter {name}')
        return _ssm_cache.get(name, {}).get('value', '')


def _validate_email(email: str) -> bool:
    """Basic RFC 5322 email format validation."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def _check_rate_limit(ip: str, log=None) -> bool:
    """Check and increment rate limit for an IP. Returns True if allowed, False if rate limited."""
    now = int(time.time())
    window_ttl = now + 3600  # 1 hour from now

    try:
        resp = rate_limit_table.update_item(
            Key={'ipAddress': ip},
            UpdateExpression='SET requestCount = if_not_exists(requestCount, :zero) + :inc, '
                           'windowStart = if_not_exists(windowStart, :now), '
                           'ttl = if_not_exists(#ttl_attr, :ttl)',
            ExpressionAttributeNames={'#ttl_attr': 'ttl'},
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':now': datetime.now(timezone.utc).isoformat(),
                ':ttl': window_ttl,
            },
            ReturnValues='ALL_NEW',
        )
        count = resp['Attributes'].get('requestCount', 1)
        return count <= 5
    except Exception as e:
        if log:
            log.warning('RateLimitCheckFailed', 'Rate limit check failed, allowing request')
        return True


def _is_disposable_domain(email: str, log=None) -> bool:
    """Check if the email domain is in the disposable domain blocklist."""
    try:
        blocklist_json = _get_ssm_param('/soulreel/email-nurture/disposable-domains', log)
        if not blocklist_json:
            return False
        blocklist = json.loads(blocklist_json)
        domain = email.split('@')[1].lower()
        return domain in blocklist
    except Exception:
        return False


def _compute_captured_week(dt: datetime) -> str:
    """Compute ISO week string like '2025-W28'."""
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _send_welcome_email(email: str, variant: str, log=None):
    """Send the Stage 0 welcome email via SES."""
    try:
        secret = _get_ssm_param('/soulreel/email-nurture/unsubscribe-secret', log)
        unsub_token = generate_unsubscribe_token(email, secret)
        ref_hash = generate_referral_hash(email, secret)

        api_base = os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')
        api_url = os.environ.get('VITE_API_BASE_URL', '')

        template_name = f'soulreel-nurture-stage-0-{variant}'
        unsub_url = f'{api_url}/email-capture/unsubscribe?token={unsub_token}'
        signup_url = f'{api_base}/?signup=create-legacy'
        referral_url = f'{api_base}/?ref={ref_hash}'

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
        if log:
            log.info('WelcomeEmailSent', details={'variant': variant})
    except Exception as e:
        if log:
            log.error('WelcomeEmailFailed', e)


def lambda_handler(event, context):
    """Handle POST /email-capture requests."""
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': '',
        }

    log = StructuredLog(event, context)
    headers = cors_headers(event)

    try:
        # Parse request body
        body = json.loads(event.get('body') or '{}')
        email = (body.get('email') or '').strip().lower()
        source = body.get('source', 'landing-page')
        referred_by = body.get('referredBy')

        # Validate email
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'success': False, 'error': 'Email is required.'}),
            }

        if not _validate_email(email):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'success': False, 'error': 'Please enter a valid email address.'}),
            }

        # Check disposable domain
        if _is_disposable_domain(email, log):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'success': False, 'error': 'Please use a permanent email address.'}),
            }

        # Rate limiting
        source_ip = (event.get('requestContext', {}).get('identity', {}).get('sourceIp')
                     or event.get('headers', {}).get('X-Forwarded-For', '').split(',')[0].strip()
                     or 'unknown')

        if not _check_rate_limit(source_ip, log):
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({'success': False, 'error': 'Too many requests. Please try again later.'}),
            }

        # Check if email already exists (for re-capture logic)
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        captured_week = _compute_captured_week(now)

        existing = email_capture_table.get_item(Key={'email': email}).get('Item')

        if existing:
            # Re-capture: reset capturedAt and reminderStage, preserve variant
            variant = existing.get('variant', 'A')
            email_capture_table.update_item(
                Key={'email': email},
                UpdateExpression='SET capturedAt = :now, reminderStage = :zero, '
                               'capturedWeek = :week, statusGsi = :status, '
                               '#src = :source, sourceIp = :ip',
                ExpressionAttributeNames={'#src': 'source'},
                ExpressionAttributeValues={
                    ':now': now_iso,
                    ':zero': 0,
                    ':week': captured_week,
                    ':status': 'active',
                    ':source': source,
                    ':ip': source_ip,
                },
            )
            log.info('EmailRecaptured', details={'source': source})
        else:
            # New capture
            variant = random.choice(['A', 'B'])
            item = {
                'email': email,
                'capturedAt': now_iso,
                'reminderStage': 0,
                'convertedAt': None,
                'convertedAtStage': None,
                'expiredAt': None,
                'unsubscribedAt': None,
                'source': source,
                'variant': variant,
                'openCount': 0,
                'clickCount': 0,
                'lastOpenedAt': None,
                'lastClickedAt': None,
                'bounceStatus': None,
                'referredBy': referred_by,
                'sourceIp': source_ip,
                'statusGsi': 'active',
                'capturedWeek': captured_week,
                'stageOpens': {},
                'stageClicks': {},
            }
            email_capture_table.put_item(Item=item)
            log.info('NewEmailCaptured', details={
                'variant': variant,
                'source': source,
            })

        # Send welcome email (both new and re-capture)
        _send_welcome_email(email, variant, log)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'success': True}),
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'success': False, 'error': 'Invalid request body.'}),
        }
    except Exception as e:
        log.error('EmailCaptureFailed', e)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'success': False, 'error': 'Internal server error'}),
        }
