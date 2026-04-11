"""
ExportTestResults Lambda Handler

Endpoint:
  POST /psych-tests/export  (Cognito Auth) — Generate PDF/JSON/CSV exports
  and return pre-signed download URLs.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 11.2
"""
import os
import json
import sys
import csv
import io
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

_TABLE_USER_TEST_RESULTS = os.environ.get('TABLE_USER_TEST_RESULTS', 'UserTestResultsDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')

_SUPPORTED_FORMATS = {'PDF', 'JSON', 'CSV'}
_PRESIGNED_EXPIRY = 86400  # 24 hours


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
# Decimal conversion helper
# ===================================================================

def _decimal_to_native(obj):
    """Recursively convert Decimal values to int/float for serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_native(i) for i in obj]
    return obj


# ===================================================================
# Request handler
# ===================================================================

def lambda_handler(event, context):
    """Handle POST /psych-tests/export."""

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
        return _handle_export(event, user_id)
    except Exception as exc:
        logger.error('[EXPORT_TEST_RESULTS] Unhandled error: %s', exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


def _handle_export(event, user_id):
    """Core export flow: validate → fetch result → generate → upload → presign."""

    # --- Parse request body ---
    body = event.get('body')
    if not body:
        return cors_response(400, {'error': 'Missing request body'}, event)

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid JSON in request body'}, event)

    test_id = data.get('testId')
    version = data.get('version')
    timestamp = data.get('timestamp')
    export_format = data.get('format')

    # Validate required fields
    missing = []
    if not test_id:
        missing.append('testId')
    if not version:
        missing.append('version')
    if not timestamp:
        missing.append('timestamp')
    if not export_format:
        missing.append('format')
    if missing:
        return cors_response(
            400,
            {'error': f'Missing required fields: {", ".join(missing)}'},
            event,
        )

    # Validate format
    export_format_upper = export_format.upper()
    if export_format_upper not in _SUPPORTED_FORMATS:
        return cors_response(400, {
            'error': f'Unsupported export format: {export_format}. Supported: PDF, JSON, CSV'
        }, event)

    # --- Fetch result from UserTestResults table ---
    result = _fetch_result(user_id, test_id, version, timestamp)
    if result is None:
        return cors_response(404, {
            'error': f'No results found for test: {test_id}'
        }, event)

    # --- Generate export content ---
    format_lower = export_format_upper.lower()
    if export_format_upper == 'JSON':
        content_bytes, content_type = _generate_json_export(result)
    elif export_format_upper == 'CSV':
        content_bytes, content_type = _generate_csv_export(result)
    elif export_format_upper == 'PDF':
        content_bytes, content_type = _generate_pdf_export(result)
    else:
        return cors_response(400, {
            'error': f'Unsupported export format: {export_format}'
        }, event)

    # --- Upload to S3 ---
    s3_key = f'psych-exports/{user_id}/{test_id}/{timestamp}.{format_lower}'
    _s3.put_object(
        Bucket=_S3_BUCKET,
        Key=s3_key,
        Body=content_bytes,
        ContentType=content_type,
    )

    # --- Update exportPaths in UserTestResults table ---
    _update_export_paths(user_id, test_id, version, timestamp, format_lower, s3_key)

    # --- Generate pre-signed URL ---
    download_url = _s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': _S3_BUCKET, 'Key': s3_key},
        ExpiresIn=_PRESIGNED_EXPIRY,
    )

    logger.info(
        '[EXPORT_TEST_RESULTS] Exported %s for user=%s test=%s',
        export_format_upper, user_id, test_id,
    )

    return cors_response(200, {
        'downloadUrl': download_url,
        'expiresIn': _PRESIGNED_EXPIRY,
    }, event)


# ===================================================================
# DynamoDB helpers
# ===================================================================

def _fetch_result(user_id, test_id, version, timestamp):
    """Fetch a test result from UserTestResults table.

    PK: userId, SK: {testId}#{version}#{timestamp}
    Returns the item dict or None.
    """
    table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)
    sk = f'{test_id}#{version}#{timestamp}'
    try:
        response = table.get_item(Key={
            'userId': user_id,
            'testIdVersionTimestamp': sk,
        })
        return response.get('Item')
    except ClientError as exc:
        logger.error('[EXPORT_TEST_RESULTS] DynamoDB error: %s', exc)
        return None


def _update_export_paths(user_id, test_id, version, timestamp, format_lower, s3_key):
    """Update the exportPaths map in the UserTestResults record."""
    table = _dynamodb.Table(_TABLE_USER_TEST_RESULTS)
    sk = f'{test_id}#{version}#{timestamp}'
    try:
        table.update_item(
            Key={
                'userId': user_id,
                'testIdVersionTimestamp': sk,
            },
            UpdateExpression='SET exportPaths.#fmt = :path',
            ExpressionAttributeNames={'#fmt': format_lower},
            ExpressionAttributeValues={':path': s3_key},
        )
    except ClientError:
        # If exportPaths doesn't exist yet, create it
        try:
            table.update_item(
                Key={
                    'userId': user_id,
                    'testIdVersionTimestamp': sk,
                },
                UpdateExpression='SET exportPaths = :paths',
                ExpressionAttributeValues={
                    ':paths': {format_lower: s3_key},
                },
            )
        except ClientError as exc:
            logger.warning(
                '[EXPORT_TEST_RESULTS] Failed to update exportPaths: %s', exc
            )


# ===================================================================
# Export generators
# ===================================================================

def _generate_json_export(result):
    """Build JSON export — include all result fields except rawResponses.

    Returns (bytes, content_type).
    """
    native = _decimal_to_native(result)
    export_data = {
        'testId': native.get('testId', ''),
        'version': native.get('version', ''),
        'timestamp': native.get('timestamp', ''),
        'domainScores': native.get('domainScores', {}),
        'facetScores': native.get('facetScores', {}),
        'compositeScores': native.get('compositeScores', {}),
        'thresholdClassifications': native.get('thresholdClassifications', {}),
        'narrativeText': native.get('narrativeText', ''),
    }
    content = json.dumps(export_data, indent=2, ensure_ascii=False)
    return content.encode('utf-8'), 'application/json'


def _generate_csv_export(result):
    """Build CSV export with header row and one row per domain + facet.

    Columns: name, raw_score, threshold_label, percentile
    Returns (bytes, content_type).
    """
    native = _decimal_to_native(result)
    domain_scores = native.get('domainScores', {})
    facet_scores = native.get('facetScores', {})
    threshold_classifications = native.get('thresholdClassifications', {})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['name', 'raw_score', 'threshold_label', 'percentile'])

    for name, entry in domain_scores.items():
        raw = entry.get('raw', 0) if isinstance(entry, dict) else entry
        label = threshold_classifications.get(name, entry.get('label', '')) if isinstance(entry, dict) else threshold_classifications.get(name, '')
        normalized = entry.get('normalized', '') if isinstance(entry, dict) else ''
        writer.writerow([name, raw, label, normalized])

    for name, entry in facet_scores.items():
        raw = entry.get('raw', 0) if isinstance(entry, dict) else entry
        label = threshold_classifications.get(name, entry.get('label', '')) if isinstance(entry, dict) else threshold_classifications.get(name, '')
        normalized = entry.get('normalized', '') if isinstance(entry, dict) else ''
        writer.writerow([name, raw, label, normalized])

    content = output.getvalue()
    return content.encode('utf-8'), 'text/csv'


def _generate_pdf_export(result):
    """Build PDF export using fpdf2.

    Contains: test name, date, domain scores with threshold labels,
    facet scores, and narrative text.
    Returns (bytes, content_type).
    """
    from fpdf import FPDF

    native = _decimal_to_native(result)
    test_id = native.get('testId', 'Unknown Test')
    timestamp = native.get('timestamp', '')
    domain_scores = native.get('domainScores', {})
    facet_scores = native.get('facetScores', {})
    threshold_classifications = native.get('thresholdClassifications', {})
    narrative_text = native.get('narrativeText', '')

    def _safe(text):
        """Encode text to latin-1 safe characters for built-in PDF fonts."""
        if not isinstance(text, str):
            text = str(text)
        return text.encode('latin-1', errors='replace').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 12, _safe(f'Test Results: {test_id}'), new_x='LMARGIN', new_y='NEXT')

    # Date
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, _safe(f'Date: {timestamp}'), new_x='LMARGIN', new_y='NEXT')
    pdf.ln(6)

    # Domain Scores
    if domain_scores:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Domain Scores', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 11)
        for name, entry in domain_scores.items():
            if isinstance(entry, dict):
                raw = entry.get('raw', 0)
                label = threshold_classifications.get(name, entry.get('label', ''))
            else:
                raw = entry
                label = threshold_classifications.get(name, '')
            pdf.cell(0, 7, _safe(f'  {name}: {raw} ({label})'), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)

    # Facet Scores
    if facet_scores:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Facet Scores', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 11)
        for name, entry in facet_scores.items():
            if isinstance(entry, dict):
                raw = entry.get('raw', 0)
                label = threshold_classifications.get(name, entry.get('label', ''))
            else:
                raw = entry
                label = threshold_classifications.get(name, '')
            pdf.cell(0, 7, _safe(f'  {name}: {raw} ({label})'), new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)

    # Narrative Text
    if narrative_text:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Narrative Interpretation', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(0, 6, _safe(narrative_text))

    content = pdf.output()
    return bytes(content), 'application/pdf'
