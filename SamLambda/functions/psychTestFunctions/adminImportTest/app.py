"""
AdminImportTest Lambda Handler

Endpoint:
  POST /psych-tests/admin/import  (Cognito Auth, Admin-only)

Parses a Test Definition JSON, validates it against the JSON Schema,
creates metadata in PsychTests table, uploads the definition to S3,
and generates question records in allQuestionDB for the admin interface.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.2
"""
import os
import json
import sys
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

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
_TABLE_ALL_QUESTIONS = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

# Path to bundled JSON Schema (inside Lambda CodeUri)
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schemas',
                            'psych-test-definition.schema.json')


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
# Schema loading (lazy, cached)
# ===================================================================

_cached_schema = None


def _load_schema():
    """Load and cache the Test Definition JSON Schema."""
    global _cached_schema
    if _cached_schema is None:
        with open(_SCHEMA_PATH, 'r') as f:
            _cached_schema = json.load(f)
    return _cached_schema


# ===================================================================
# Request handler
# ===================================================================

def lambda_handler(event, context):
    """Handle POST /psych-tests/admin/import."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    # Extract userId from Cognito claims
    claims = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
    )
    user_id = claims.get('sub')
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    # Verify admin group membership
    if not _is_admin(claims):
        return error_response(403, 'Forbidden: admin access required', event=event)

    try:
        return _handle_import(event, user_id)
    except Exception as exc:
        logger.error('[ADMIN_IMPORT_TEST] Unhandled error: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


def _is_admin(claims):
    """Check if the user belongs to the SoulReelAdmins group.

    The cognito:groups claim can be a string (comma-separated) or a list.
    """
    groups = claims.get('cognito:groups', '')
    if isinstance(groups, list):
        return 'SoulReelAdmins' in groups
    if isinstance(groups, str):
        return 'SoulReelAdmins' in [g.strip() for g in groups.split(',')]
    return False


def _handle_import(event, user_id):
    """Core import flow: parse → validate → check duplicate → upload → metadata → questions."""

    # --- Parse request body ---
    body = event.get('body')
    if not body:
        return cors_response(400, {'error': 'Missing request body'}, event)

    try:
        test_def = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid JSON in request body'}, event)

    # --- Validate Test Definition against JSON Schema ---
    validation_error = _validate_test_definition(test_def)
    if validation_error:
        return cors_response(400, {'error': f'Invalid test definition: {validation_error}'}, event)

    test_id = test_def['testId']
    version = test_def['version']

    # --- Check for duplicate testId + version ---
    if _check_duplicate(test_id, version):
        return cors_response(409, {
            'error': f'Test {test_id} version {version} already exists'
        }, event)

    # --- Upload Test Definition to S3 ---
    s3_key = f'psych-tests/{test_id}.json'
    _upload_to_s3(s3_key, test_def)

    # --- Create metadata record in PsychTests table ---
    created_at = datetime.now(timezone.utc).isoformat()
    _create_metadata(test_def, s3_key, created_at)

    # --- Generate question records in allQuestionDB ---
    question_count = _generate_question_records(test_def)

    logger.info(
        '[ADMIN_IMPORT_TEST] Imported test=%s version=%s questions=%d by user=%s',
        test_id, version, question_count, user_id,
    )

    return cors_response(200, {
        'testId': test_id,
        'version': version,
        'questionCount': question_count,
    }, event)


# ===================================================================
# Validation
# ===================================================================

def _validate_test_definition(test_def):
    """Validate Test Definition against JSON Schema. Returns error string or None."""
    try:
        import jsonschema
    except ImportError:
        logger.warning('[ADMIN_IMPORT_TEST] jsonschema not available, skipping validation')
        return None

    schema = _load_schema()
    try:
        jsonschema.validate(instance=test_def, schema=schema)
        return None
    except jsonschema.ValidationError as exc:
        return f'{exc.json_path}: {exc.message}'


# ===================================================================
# DynamoDB helpers
# ===================================================================

def _check_duplicate(test_id, version):
    """Check if a test with the same testId + version already exists.

    Returns True if duplicate found, False otherwise.
    """
    table = _dynamodb.Table(_TABLE_PSYCH_TESTS)
    try:
        response = table.get_item(
            Key={'testId': test_id, 'version': version},
            ProjectionExpression='testId',
        )
        return 'Item' in response
    except ClientError as exc:
        logger.error('[ADMIN_IMPORT_TEST] DynamoDB error checking duplicate: %s', exc)
        raise


def _create_metadata(test_def, s3_path, created_at):
    """Create a metadata record in the PsychTests table."""
    table = _dynamodb.Table(_TABLE_PSYCH_TESTS)

    item = {
        'testId': test_def['testId'],
        'version': test_def['version'],
        'testName': test_def['testName'],
        'description': test_def['description'],
        'estimatedMinutes': test_def['estimatedMinutes'],
        'status': 'active',
        's3Path': s3_path,
        'createdAt': created_at,
    }

    # Include previousVersionMapping if present
    previous_mapping = test_def.get('previousVersionMapping')
    if previous_mapping:
        item['previousVersionMapping'] = previous_mapping

    table.put_item(Item=item)
    logger.info(
        '[ADMIN_IMPORT_TEST] Created metadata for test=%s version=%s',
        test_def['testId'], test_def['version'],
    )


def _generate_question_records(test_def):
    """Generate question records in allQuestionDB — one per question.

    Each record has questionType = testId and facet tag = groupByFacet.
    Returns the number of question records created.
    """
    table = _dynamodb.Table(_TABLE_ALL_QUESTIONS)
    test_id = test_def['testId']
    questions = test_def.get('questions', [])

    for question in questions:
        item = {
            'questionType': test_id,
            'questionId': question['questionId'],
            'text': question['text'],
            'responseType': question['responseType'],
            'options': question['options'],
            'reverseScored': question['reverseScored'],
            'scoringKey': question['scoringKey'],
            'groupByFacet': question['groupByFacet'],
            'facet': question['groupByFacet'],
            'pageBreakAfter': question['pageBreakAfter'],
            'accessibilityHint': question['accessibilityHint'],
        }

        # Include optional videoPromptFrequency if present
        if 'videoPromptFrequency' in question:
            item['videoPromptFrequency'] = question['videoPromptFrequency']

        table.put_item(Item=item)

    logger.info(
        '[ADMIN_IMPORT_TEST] Generated %d question records for test=%s',
        len(questions), test_id,
    )
    return len(questions)


# ===================================================================
# S3 helpers
# ===================================================================

def _upload_to_s3(s3_key, test_def):
    """Upload the Test Definition JSON to S3."""
    _s3.put_object(
        Bucket=_S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(test_def, ensure_ascii=False),
        ContentType='application/json',
    )
    logger.info('[ADMIN_IMPORT_TEST] Uploaded test definition to s3://%s/%s', _S3_BUCKET, s3_key)
