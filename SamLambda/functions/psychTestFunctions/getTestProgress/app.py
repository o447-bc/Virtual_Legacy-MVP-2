"""
GetTestProgress Lambda Handler

Endpoint:
  GET /psych-tests/progress/{testId}  (Cognito Auth) — Retrieve saved test progress

Requirements: 5.5, 11.2
"""
import os
import json
import sys
import logging
from decimal import Decimal

import boto3

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS clients (module-level — reused across warm invocations)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')

_TABLE_USER_TEST_PROGRESS = os.environ.get('TABLE_USER_TEST_PROGRESS', 'UserTestProgressDB')


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
    """Handle GET /psych-tests/progress/{testId}."""

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
        # Extract testId from path parameters
        test_id = (event.get('pathParameters') or {}).get('testId')
        if not test_id:
            return cors_response(400, {'error': 'Missing testId parameter'}, event)

        # GetItem from UserTestProgress table
        table = _dynamodb.Table(_TABLE_USER_TEST_PROGRESS)
        response = table.get_item(
            Key={
                'userId': user_id,
                'testId': test_id,
            }
        )

        item = response.get('Item')
        if not item:
            return cors_response(
                200,
                {'responses': [], 'currentQuestionIndex': 0, 'updatedAt': '', 'found': False},
                event,
            )

        # Return progress data
        return cors_response(200, {
            'responses': item.get('responses', []),
            'currentQuestionIndex': item.get('currentQuestionIndex', 0),
            'updatedAt': item.get('updatedAt', ''),
            'found': True,
        }, event)

    except Exception as exc:
        logger.error('[GET_TEST_PROGRESS] Unhandled error: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)
