"""
FeedbackIngestion Lambda Handler

Endpoint:
  POST /feedback  (Cognito Auth) — Accept feedback reports from users

Receives structured feedback (bug reports or feature requests) from the
frontend, validates required fields, stores the record in DynamoDB, and
invokes Claude Haiku via Bedrock to classify and summarise the report.

If Bedrock fails, the record is still saved with aiClassification="unclassified"
and aiSummary="" — the user always gets a success response.

Requirements: 5.1–5.13, 7.1–7.6
"""
import os
import json
import sys
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response
from structured_logger import StructuredLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Max request body size (20 KB)
_MAX_BODY_SIZE = 20480

# Max description length before truncation
_MAX_DESCRIPTION_LEN = 5000

_REQUIRED_FIELDS = ('reportType', 'subject', 'description')
_VALID_REPORT_TYPES = ('bug', 'feature')

TABLE_NAME = os.environ.get('TABLE_FEEDBACK_REPORTS', 'FeedbackReportsDB')
BEDROCK_MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'


def _classify_with_bedrock(report_type, subject, description):
    """
    Invoke Claude Haiku to classify the feedback and generate a one-sentence summary.

    Returns (classification, summary) on success, or ("unclassified", "") on failure.
    """
    prompt = (
        "You are classifying user feedback for a web application called SoulReel.\n\n"
        "Given the following feedback submission:\n"
        f"- Report Type (user-selected): {report_type}\n"
        f"- Subject: {subject}\n"
        f"- Description: {description[:2000]}\n\n"
        "Respond with ONLY a JSON object (no markdown, no explanation):\n"
        '{"classification": "bug" or "feature_request", "summary": "One sentence summary"}'
    )

    try:
        bedrock = boto3.client('bedrock-runtime')
        body = json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 256,
            'messages': [{'role': 'user', 'content': prompt}],
        })

        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=body,
        )

        result = json.loads(response['body'].read())
        text = result.get('content', [{}])[0].get('text', '')

        # Parse the JSON response from the model
        parsed = json.loads(text)
        classification = parsed.get('classification', 'unclassified')
        summary = parsed.get('summary', '')

        # Validate classification value
        if classification not in ('bug', 'feature_request'):
            classification = 'unclassified'

        return classification, summary

    except Exception as e:
        logger.warning(f'Bedrock classification failed: {e}')
        return 'unclassified', ''


def lambda_handler(event, context):
    """Route POST /feedback requests."""

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

    # --- Validate reportType ---
    report_type = data['reportType']
    if report_type not in _VALID_REPORT_TYPES:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({
                'error': "Invalid reportType. Must be 'bug' or 'feature'"
            }),
        }

    # --- Truncate description if needed ---
    description = data['description']
    if len(description) > _MAX_DESCRIPTION_LEN:
        description = description[:_MAX_DESCRIPTION_LEN] + '[truncated]'

    subject = data['subject']
    user_email = data.get('userEmail', '')
    user_name = data.get('userName', 'Anonymous')

    # --- Extract userId from JWT claims ---
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    # --- Generate identifiers ---
    report_id = str(uuid.uuid4())
    submitted_at = datetime.now(timezone.utc).isoformat()

    # --- Classify with Bedrock ---
    ai_classification, ai_summary = _classify_with_bedrock(
        report_type, subject, description
    )

    # --- Write to DynamoDB ---
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)

        table.put_item(Item={
            'reportId': report_id,
            'gsiPk': 'ALL',
            'reportType': report_type,
            'subject': subject,
            'description': description,
            'userEmail': user_email,
            'userName': user_name,
            'userId': user_id,
            'submittedAt': submitted_at,
            'status': 'active',
            'aiClassification': ai_classification,
            'aiSummary': ai_summary,
        })
    except ClientError as e:
        log.log_aws_error('DynamoDB', 'PutItem', e, {'TableName': TABLE_NAME})
        return error_response(500, 'A server error occurred. Please try again.', e, event, log=log)

    # --- Log structured entry ---
    log.info('FeedbackSubmitted', details={
        'reportId': report_id,
        'reportType': report_type,
        'aiClassification': ai_classification,
    })

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'status': 'submitted'}),
    }
