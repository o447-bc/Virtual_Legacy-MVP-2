"""
AdminQuestions Lambda — CRUD + batch operations on allQuestionDB.

Routes:
  GET  /admin/questions              — List all questions
  POST /admin/questions              — Create single question
  PUT  /admin/questions/{questionId} — Update question
  POST /admin/questions/batch        — Batch import
"""
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin
from life_event_registry import validate_life_event_keys


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_NAME = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')


def lambda_handler(event, context):
    print(f"[AdminQuestions] Event: {json.dumps(event, default=str)}")

    # OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': ''
        }

    # Admin auth check
    admin = verify_admin(event)
    if not admin:
        return {
            'statusCode': 403,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Forbidden: admin access required'})
        }
    admin_email, admin_sub = admin

    method = event.get('httpMethod', '')
    resource = event.get('resource', '')

    try:
        if method == 'GET' and resource == '/admin/questions':
            return handle_list_questions(event)
        elif method == 'POST' and resource == '/admin/questions/batch':
            return handle_batch_import(event, admin_email)

        elif method == 'POST' and resource == '/admin/questions':
            return handle_create_question(event, admin_email)

        elif method == 'PUT' and '/admin/questions/' in resource:
            return handle_update_question(event, admin_email)

        else:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Unsupported route: {method} {resource}'})
            }

    except ClientError as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
    except Exception as e:
        return error_response(500, 'An unexpected error occurred. Please try again.', e, event)


# ---------------------------------------------------------------------------
# GET /admin/questions — List all questions
# ---------------------------------------------------------------------------
def handle_list_questions(event):
    """Scan allQuestionDB and return all questions."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    items = []
    response = table.scan()
    items.extend(response.get('Items', []))

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    # Normalize missing new attributes to defaults
    for item in items:
        item.setdefault('requiredLifeEvents', [])
        item.setdefault('isInstanceable', False)
        item.setdefault('instancePlaceholder', '')
        item.setdefault('lastModifiedBy', '')
        item.setdefault('lastModifiedAt', '')
        item.setdefault('themeName', '')

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'questions': items}, cls=DecimalEncoder)
    }


# ---------------------------------------------------------------------------
# POST /admin/questions — Create single question
# ---------------------------------------------------------------------------
def handle_create_question(event, admin_email):
    """Create a new question with auto-generated legacy-format questionId."""
    body = json.loads(event.get('body') or '{}')

    question_text = body.get('questionText', '').strip()
    question_type = body.get('questionType', '').strip()
    theme_name = body.get('themeName', '').strip()

    if not question_text:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: questionText'})
        }
    if not question_type:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: questionType'})
        }

    required_events = body.get('requiredLifeEvents', [])
    invalid_keys = validate_life_event_keys(required_events)
    if invalid_keys:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': f'Invalid life event keys: {", ".join(invalid_keys)}'})
        }

    is_instanceable = body.get('isInstanceable', False)
    instance_placeholder = body.get('instancePlaceholder', '')
    difficulty = body.get('difficulty', 1)

    # Validate difficulty range
    if not isinstance(difficulty, (int, float)) or difficulty < 1 or difficulty > 10:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Difficulty must be between 1 and 10'})
        }

    # Generate legacy-format questionId
    question_id = _generate_question_id(question_type)
    now = datetime.now(timezone.utc).isoformat()

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    table.put_item(Item={
        'questionId': question_id,
        'questionType': question_type,
        'themeName': theme_name or question_type,
        'difficulty': int(difficulty),
        'active': True,
        'questionText': question_text,
        'requiredLifeEvents': required_events,
        'isInstanceable': is_instanceable,
        'instancePlaceholder': instance_placeholder,
        'lastModifiedBy': admin_email,
        'lastModifiedAt': now,
    })

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'questionId': question_id,
            'message': 'Question created'
        })
    }


# ---------------------------------------------------------------------------
# PUT /admin/questions/{questionId} — Update question
# ---------------------------------------------------------------------------
def handle_update_question(event, admin_email):
    """Update an existing question's attributes."""
    question_id = (event.get('pathParameters') or {}).get('questionId')
    if not question_id:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing questionId in path'})
        }

    body = json.loads(event.get('body') or '{}')

    # questionType is required as part of the composite key
    question_type = body.get('questionType', '').strip()
    if not question_type:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: questionType (needed for composite key)'})
        }

    # Validate life event keys if provided
    required_events = body.get('requiredLifeEvents')
    if required_events is not None:
        invalid_keys = validate_life_event_keys(required_events)
        if invalid_keys:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Invalid life event keys: {", ".join(invalid_keys)}'})
            }

    # Build update expression dynamically from provided fields
    updatable_fields = {
        'themeName': 'themeName',
        'difficulty': 'difficulty',
        'active': 'active',
        'questionText': 'questionText',
        'requiredLifeEvents': 'requiredLifeEvents',
        'isInstanceable': 'isInstanceable',
        'instancePlaceholder': 'instancePlaceholder',
    }

    update_parts = []
    expr_names = {}
    expr_values = {}

    for body_key, db_key in updatable_fields.items():
        if body_key in body:
            placeholder = f':{body_key}'
            name_placeholder = f'#{body_key}'
            update_parts.append(f'{name_placeholder} = {placeholder}')
            expr_names[name_placeholder] = db_key
            expr_values[placeholder] = body[body_key]

    if not update_parts:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'No fields to update'})
        }

    # Always update audit fields
    now = datetime.now(timezone.utc).isoformat()
    update_parts.append('#lastModifiedBy = :lastModifiedBy')
    update_parts.append('#lastModifiedAt = :lastModifiedAt')
    expr_names['#lastModifiedBy'] = 'lastModifiedBy'
    expr_names['#lastModifiedAt'] = 'lastModifiedAt'
    expr_values[':lastModifiedBy'] = admin_email
    expr_values[':lastModifiedAt'] = now

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    try:
        table.update_item(
            Key={
                'questionId': question_id,
                'questionType': question_type,
            },
            UpdateExpression='SET ' + ', '.join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression='attribute_exists(questionId)',
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Question not found: {question_id}'})
            }
        raise

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'message': 'Question updated',
            'questionId': question_id
        })
    }


# ---------------------------------------------------------------------------
# POST /admin/questions/batch — Batch import
# ---------------------------------------------------------------------------
def handle_batch_import(event, admin_email):
    """Batch import multiple questions. Atomic — all or nothing."""
    body = json.loads(event.get('body') or '{}')

    question_type = body.get('questionType', '').strip()
    difficulty = body.get('difficulty', 1)
    theme_name = body.get('themeName', '').strip()
    required_events = body.get('requiredLifeEvents', [])
    is_instanceable = body.get('isInstanceable', False)
    instance_placeholder = body.get('instancePlaceholder', '')
    questions = body.get('questions', [])

    if not question_type:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: questionType'})
        }

    if not questions or not isinstance(questions, list):
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing or empty questions array'})
        }

    if not isinstance(difficulty, (int, float)) or difficulty < 1 or difficulty > 10:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Difficulty must be between 1 and 10'})
        }

    # Validate life event keys
    invalid_keys = validate_life_event_keys(required_events)
    if invalid_keys:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': f'Invalid life event keys: {", ".join(invalid_keys)}'})
        }

    # Validate each question text
    errors = []
    for i, q in enumerate(questions):
        text = q.strip() if isinstance(q, str) else (q.get('question', '') if isinstance(q, dict) else '')
        if not text.strip():
            errors.append(f'Question at index {i} is empty')
    if errors:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Validation failed', 'details': errors})
        }

    # Generate sequential IDs
    prefix = _make_id_prefix(question_type)
    max_num = _find_max_sequence_number(prefix)
    now = datetime.now(timezone.utc).isoformat()

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    items = []
    question_ids = []
    for i, q in enumerate(questions):
        text = q.strip() if isinstance(q, str) else q.get('question', '').strip()
        seq = max_num + 1 + i
        qid = f'{prefix}-{seq:05d}'
        question_ids.append(qid)
        items.append({
            'questionId': qid,
            'questionType': question_type,
            'themeName': theme_name or question_type,
            'difficulty': int(difficulty),
            'active': True,
            'questionText': text,
            'requiredLifeEvents': required_events,
            'isInstanceable': is_instanceable,
            'instancePlaceholder': instance_placeholder,
            'lastModifiedBy': admin_email,
            'lastModifiedAt': now,
        })

    # Write in batches of 25 (DynamoDB BatchWriteItem limit)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'message': 'Batch import complete',
            'imported': len(items),
            'questionIds': question_ids
        })
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_id_prefix(question_type):
    """
    Convert a questionType to a lowercase hyphenated prefix for questionId.
    e.g., 'Childhood Memories' -> 'childhood-memories'
         'Divorce' -> 'divorce'
    """
    # Lowercase, replace spaces and underscores with hyphens, strip non-alphanumeric
    prefix = question_type.lower().strip()
    prefix = re.sub(r'[\s_]+', '-', prefix)
    prefix = re.sub(r'[^a-z0-9\-]', '', prefix)
    prefix = re.sub(r'-+', '-', prefix).strip('-')
    return prefix


def _find_max_sequence_number(prefix):
    """
    Scan allQuestionDB for the highest sequential number with the given prefix.
    Returns 0 if no matching questions exist.
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    max_num = 0
    response = table.scan(
        ProjectionExpression='questionId',
    )

    for item in response.get('Items', []):
        qid = item.get('questionId', '')
        num = _extract_sequence_number(qid, prefix)
        if num is not None and num > max_num:
            max_num = num

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ProjectionExpression='questionId',
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        for item in response.get('Items', []):
            qid = item.get('questionId', '')
            num = _extract_sequence_number(qid, prefix)
            if num is not None and num > max_num:
                max_num = num

    return max_num


def _extract_sequence_number(question_id, prefix):
    """
    Extract the numeric suffix from a questionId matching the given prefix.
    e.g., 'divorce-00023' with prefix 'divorce' -> 23
    Returns None if the questionId doesn't match the prefix pattern.
    """
    pattern = f'^{re.escape(prefix)}-(\d+)$'
    match = re.match(pattern, question_id)
    if match:
        return int(match.group(1))
    return None


def _generate_question_id(question_type):
    """Generate the next sequential questionId for a given questionType."""
    prefix = _make_id_prefix(question_type)
    max_num = _find_max_sequence_number(prefix)
    return f'{prefix}-{max_num + 1:05d}'
