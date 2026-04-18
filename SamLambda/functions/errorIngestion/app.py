"""
ErrorIngestion Lambda Handler

Endpoint:
  POST /log-error  (Cognito Auth) — Accept error reports from the frontend

Receives structured error details from the frontend Error Reporter,
validates required fields, and writes a structured JSON log entry to
CloudWatch Logs with source="frontend". This enables centralized
viewing of both frontend and backend errors via Logs Insights.

Requirements: 2.1–2.8, 7.2, 7.4
"""
import os
import json
import sys
import logging

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response
from structured_logger import StructuredLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Max request body size (10 KB)
_MAX_BODY_SIZE = 10240

# Max stack trace length before truncation
_MAX_STACK_TRACE_LEN = 4096

_REQUIRED_FIELDS = ('errorMessage', 'component', 'url')


def lambda_handler(event, context):
    """Route POST /log-error requests."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': '',
        }

    log = StructuredLog(event, context)

    # --- Parse and validate body ---
    raw_body = event.get('body', '')
    if not raw_body:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing request body'}),
        }

    if len(raw_body) > _MAX_BODY_SIZE:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Request body too large'}),
        }

    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Invalid JSON body'}),
        }

    # --- Validate required fields ---
    missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({
                'error': f'Missing required field(s): {", ".join(missing)}'
            }),
        }

    # --- Truncate stack trace if needed ---
    stack_trace = data.get('stackTrace', '')
    if isinstance(stack_trace, str) and len(stack_trace) > _MAX_STACK_TRACE_LEN:
        stack_trace = stack_trace[:_MAX_STACK_TRACE_LEN] + '[truncated]'

    # --- Extract userId from JWT claims ---
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    # --- Extract correlation ID ---
    headers = event.get('headers') or {}
    correlation_id = (
        headers.get('X-Correlation-ID', '')
        or headers.get('x-correlation-id', '')
    )

    # --- Build and emit the structured frontend error log entry ---
    frontend_entry = {
        'timestamp': __import__('datetime').datetime.now(
            __import__('datetime').timezone.utc
        ).isoformat(),
        'level': 'ERROR',
        'source': 'frontend',
        'operation': 'ErrorIngestion',
        'correlationId': correlation_id,
        'userId': user_id,
        'errorMessage': data['errorMessage'],
        'component': data['component'],
        'url': data['url'],
        'errorType': data.get('errorType', 'Error'),
        'stackTrace': stack_trace,
        'metadata': data.get('metadata', {}),
    }

    # Emit as single-line JSON — CloudWatch Logs Insights can parse this
    logger.error(json.dumps(frontend_entry, default=str))

    log.info('FrontendErrorIngested', details={
        'component': data['component'],
        'errorType': data.get('errorType', 'Error'),
    })

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'status': 'logged'}),
    }
