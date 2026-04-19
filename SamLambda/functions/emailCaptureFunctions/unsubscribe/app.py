"""
Unsubscribe Endpoint — GET /email-capture/unsubscribe

Handles one-click unsubscribe from nurture emails via HMAC-signed token.
"""
import os
import sys
import time
from datetime import datetime, timezone

import boto3

sys.path.insert(0, '/opt/python')

from cors import cors_headers
from referral_utils import verify_unsubscribe_token

TABLE_EMAIL_CAPTURE = os.environ.get('TABLE_EMAIL_CAPTURE', 'EmailCaptureDB')

dynamodb = boto3.resource('dynamodb')
ssm_client = boto3.client('ssm')
email_capture_table = dynamodb.Table(TABLE_EMAIL_CAPTURE)

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


def _html_page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — SoulReel</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f9fafb; color: #1a1f2c; }}
        .card {{ text-align: center; padding: 3rem 2rem; max-width: 400px; }}
        h1 {{ color: #7c6bc4; font-size: 1.5rem; margin-bottom: 1rem; }}
        p {{ color: #6b7280; line-height: 1.6; }}
        a {{ color: #7c6bc4; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>SoulReel</h1>
        <h2>{title}</h2>
        <p>{message}</p>
        <p><a href="https://www.soulreel.net">Return to SoulReel</a></p>
    </div>
</body>
</html>"""


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': '',
        }

    headers = cors_headers(event)
    headers['Content-Type'] = 'text/html'

    # Get token from query parameters
    params = event.get('queryStringParameters') or {}
    token = params.get('token', '')

    if not token:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': _html_page('Invalid Link', 'This unsubscribe link is invalid or has expired.'),
        }

    # Verify token
    secret = _get_ssm_param('/soulreel/email-nurture/unsubscribe-secret')
    if not secret:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': _html_page('Something Went Wrong', 'Please try again later.'),
        }

    email = verify_unsubscribe_token(token, secret)
    if not email:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': _html_page('Invalid Link', 'This unsubscribe link is invalid or has expired.'),
        }

    # Mark as unsubscribed — UpdateItem creates a record if key doesn't exist,
    # but we return success regardless to prevent email enumeration (Req 6.4).
    try:
        email_capture_table.update_item(
            Key={'email': email},
            UpdateExpression='SET unsubscribedAt = :now, statusGsi = :status',
            ExpressionAttributeValues={
                ':now': datetime.now(timezone.utc).isoformat(),
                ':status': 'unsubscribed',
            },
        )
    except Exception:
        pass  # Silently succeed even if update fails

    return {
        'statusCode': 200,
        'headers': headers,
        'body': _html_page(
            "You've Been Unsubscribed",
            "You won't receive any more emails from us. If you change your mind, you can always sign up again at soulreel.net."
        ),
    }
