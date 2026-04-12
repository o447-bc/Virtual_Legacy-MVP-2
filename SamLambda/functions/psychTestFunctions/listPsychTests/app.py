"""
ListPsychTests Lambda Handler

Endpoints:
  GET /psych-tests/list     (Cognito Auth) — List all active psychological tests
  GET /psych-tests/{testId} (Cognito Auth) — Get test definition JSON from S3

Requirements: 11.2, 11.3
"""
import os
import json
import sys
import logging
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

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
_s3 = boto3.client('s3')

_TABLE_PSYCH_TESTS = os.environ.get('TABLE_PSYCH_TESTS', 'PsychTestsDB')
_TABLE_USER_TEST_RESULTS = os.environ.get('TABLE_USER_TEST_RESULTS', 'UserTestResultsDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')


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
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route requests by path + httpMethod."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # All endpoints require authentication
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        if path == '/psych-tests/list' and method == 'GET':
            return handle_list_tests(event, user_id)
        elif path.startswith('/psych-tests/results/') and method == 'GET':
            # Extract testId from path: /psych-tests/results/{testId}
            parts = path.rstrip('/').split('/')
            test_id = parts[-1] if len(parts) >= 4 else None
            if not test_id:
                return cors_response(400, {'error': 'Missing testId parameter'}, event)
            return handle_get_results(event, user_id, test_id)
        elif path.startswith('/psych-tests/') and method == 'GET':
            # Extract testId from path: /psych-tests/{testId}
            test_id = (event.get('pathParameters') or {}).get('testId')
            if not test_id:
                return cors_response(400, {'error': 'Missing testId parameter'}, event)
            return handle_get_test_definition(event, test_id)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[LIST_PSYCH_TESTS] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Handler: GET /psych-tests/list
# ===================================================================

def handle_list_tests(event, user_id):
    """Query active tests from PsychTests table and enrich with user completion data."""
    psych_tests_table = _dynamodb.Table(_TABLE_PSYCH_TESTS)
    results_table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)

    # Query GSI status-index for active tests
    response = psych_tests_table.query(
        IndexName='status-index',
        KeyConditionExpression=Key('status').eq('active'),
    )
    tests = response.get('Items', [])

    # Query user's completed test results
    completed_map = _get_user_completed_tests(results_table, user_id)

    # Build response list
    test_list = []
    for test in tests:
        test_entry = {
            'testId': test.get('testId'),
            'testName': test.get('testName'),
            'description': test.get('description'),
            'estimatedMinutes': test.get('estimatedMinutes'),
            'status': test.get('status'),
            'version': test.get('version'),
        }
        # Add completedAt if user has taken this test
        test_id = test.get('testId')
        if test_id in completed_map:
            test_entry['completedAt'] = completed_map[test_id]
        test_list.append(test_entry)

    return cors_response(200, {'tests': test_list}, event)


def _get_user_completed_tests(results_table, user_id):
    """Query UserTestResults table for the user's completed results.

    Returns a dict mapping testId -> most recent timestamp (completedAt).
    """
    completed_map = {}
    try:
        response = results_table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
        )
        for item in response.get('Items', []):
            test_id = item.get('testId')
            timestamp = item.get('timestamp')
            if test_id and timestamp:
                # Keep the most recent completion
                if test_id not in completed_map or timestamp > completed_map[test_id]:
                    completed_map[test_id] = timestamp
    except ClientError as exc:
        logger.warning('[LIST_PSYCH_TESTS] Failed to query user results: %s', exc)
    return completed_map


# ===================================================================
# Handler: GET /psych-tests/{testId}
# ===================================================================

def handle_get_test_definition(event, test_id):
    """Fetch test definition JSON from S3."""
    s3_key = f'psych-tests/{test_id}.json'

    try:
        response = _s3.get_object(Bucket=_S3_BUCKET, Key=s3_key)
        body = response['Body'].read().decode('utf-8')
        test_definition = json.loads(body)
        return cors_response(200, test_definition, event)
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'NoSuchKey':
            return cors_response(404, {'error': f'Test definition not found: {test_id}'}, event)
        logger.error('[LIST_PSYCH_TESTS] S3 error fetching %s: %s', s3_key, exc)
        return error_response(500, 'Failed to retrieve test definition', exception=exc, event=event)


# ===================================================================
# Handler: GET /psych-tests/results/{testId}
# ===================================================================

def handle_get_results(event, user_id, test_id):
    """Fetch the user's most recent result for a test."""
    results_table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)

    try:
        response = results_table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            FilterExpression='testId = :tid',
            ExpressionAttributeValues={':tid': test_id},
            ScanIndexForward=False,
        )
        items = response.get('Items', [])
        if not items:
            return cors_response(404, {'error': f'No results found for test: {test_id}'}, event)

        # Return the most recent result (exclude rawResponses for size)
        result = items[0]
        result.pop('rawResponses', None)
        return cors_response(200, result, event)
    except ClientError as exc:
        logger.error('[LIST_PSYCH_TESTS] Error fetching results for %s: %s', test_id, exc)
        return error_response(500, 'Failed to retrieve results', exception=exc, event=event)
