"""
SaveTestProgress Lambda Handler

Endpoint:
  POST /psych-tests/progress/save  (Cognito Auth) — Save in-progress test responses

Requirements: 5.1, 5.2, 5.4, 11.2
"""
import os
import json
import sys
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response
from settings import get_setting

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS clients (module-level — reused across warm invocations)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')

_TABLE_USER_TEST_PROGRESS = os.environ.get('TABLE_USER_TEST_PROGRESS', 'UserTestProgressDB')

# Configurable TTL via Settings_Table (default 30 days)
_TTL_DAYS = int(get_setting('ASSESSMENT_PROGRESS_TTL_DAYS', '30'))
_TTL_SECONDS = _TTL_DAYS * 86400


# ===================================================================
# JSON encoder for DynamoDB Decimal types
# ===================================================================

class DecimalEncoder(json.JSONEncoder):
    """Convert Decimal values to int or float for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code, body, event=None):
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body, cls=DecimalEncoder),
    }


# ===================================================================
# Request handler
# ===================================================================

def lambda_handler(event, context):
    """Handle POST /psych-tests/progress/save."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    # Extract userId from Cognito claims
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        # Parse request body
        body = event.get('body')
        if not body:
            return cors_response(400, {'error': 'Missing request body'}, event)

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, TypeError) as exc:
            return cors_response(400, {'error': 'Invalid JSON in request body'}, event)

        test_id = data.get('testId')
        responses = data.get('responses')
        current_question_index = data.get('currentQuestionIndex')

        # Validate required fields
        missing = []
        if not test_id:
            missing.append('testId')
        if responses is None:
            missing.append('responses')
        if current_question_index is None:
            missing.append('currentQuestionIndex')

        if missing:
            return cors_response(
                400,
                {'error': f'Missing required fields: {", ".join(missing)}'},
                event,
            )

        if not isinstance(responses, list):
            return cors_response(400, {'error': 'responses must be an array'}, event)

        # Calculate TTL: current epoch + 30 days
        now_epoch = int(time.time())
        expires_at = now_epoch + _TTL_SECONDS
        updated_at = datetime.now(timezone.utc).isoformat()

        # PutItem to UserTestProgress table
        table = _dynamodb.Table(_TABLE_USER_TEST_PROGRESS)
        table.put_item(
            Item={
                'userId': user_id,
                'testId': test_id,
                'responses': responses,
                'currentQuestionIndex': current_question_index,
                'updatedAt': updated_at,
                'expiresAt': expires_at,
            }
        )

        logger.info(
            '[SAVE_TEST_PROGRESS] Saved progress for user=%s test=%s questions=%d',
            user_id, test_id, len(responses),
        )

        return cors_response(200, {'message': 'Progress saved successfully'}, event)

    except Exception as exc:
        logger.error('[SAVE_TEST_PROGRESS] Unhandled error: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)
