"""
SurveyFunction Lambda — Life-events survey submission and status.

Routes:
  GET  /survey/status  — Check if user has completed the survey
  POST /survey/submit  — Submit survey and assign personalized questions
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from cors import cors_headers
from responses import error_response
from life_event_registry import (
    LIFE_EVENT_KEYS,
    INSTANCEABLE_KEYS,
    INSTANCEABLE_KEY_TO_PLACEHOLDER,
    validate_life_event_keys,
)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_USER_STATUS = os.environ.get('TABLE_USER_STATUS', 'userStatusDB')
TABLE_ALL_QUESTIONS = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')
TABLE_QUESTION_PROGRESS = os.environ.get('TABLE_QUESTION_PROGRESS', 'userQuestionLevelProgressDB')
TABLE_USER_QUESTION_STATUS = os.environ.get('TABLE_USER_QUESTION_STATUS', 'userQuestionStatusDB')

# Status-derived key mapping: status_key -> (base_event_key, required_status)
STATUS_KEY_MAP = {
    'spouse_divorced': ('got_married', 'divorced'),
    'spouse_deceased': ('got_married', 'deceased'),
    'spouse_still_married': ('got_married', 'married'),
}

VALID_MARRIAGE_STATUSES = {'married', 'divorced', 'deceased'}


def lambda_handler(event, context):
    print(f"[Survey] Event: {json.dumps(event, default=str)}")

    # OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(event), 'body': ''}

    # Extract authenticated user ID
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return {
            'statusCode': 401,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Unauthorized'})
        }

    method = event.get('httpMethod', '')
    resource = event.get('resource', '')

    try:
        if method == 'GET' and '/survey/status' in resource:
            return handle_status(event, user_id)
        elif method == 'POST' and '/survey/submit' in resource:
            return handle_submit(event, user_id)
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
# GET /survey/status
# ---------------------------------------------------------------------------
def handle_status(event, user_id):
    """Return the user's survey completion status."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_USER_STATUS)

    response = table.get_item(Key={'userId': user_id})
    item = response.get('Item', {})

    # Calculate assigned question count if available
    assigned_question_count = None
    assigned = item.get('assignedQuestions')
    if assigned:
        count = len(assigned.get('standard', []))
        for group in assigned.get('instanced', []):
            count += len(group.get('questionIds', []))
        assigned_question_count = count

    # --- Instanced progress: query userQuestionStatusDB for answered instanced keys ---
    instanced_progress = {'answeredKeys': []}
    question_details = {}

    if assigned and assigned.get('instanced'):
        # Query userQuestionStatusDB for all answered questions for this user
        uqs_table = dynamodb.Table(TABLE_USER_QUESTION_STATUS)
        answered_keys = []
        uqs_response = uqs_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ProjectionExpression='questionId',
        )
        for uqs_item in uqs_response.get('Items', []):
            qid = uqs_item.get('questionId', '')
            if '#' in qid:
                answered_keys.append(qid)
        while 'LastEvaluatedKey' in uqs_response:
            uqs_response = uqs_table.query(
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ProjectionExpression='questionId',
                ExclusiveStartKey=uqs_response['LastEvaluatedKey'],
            )
            for uqs_item in uqs_response.get('Items', []):
                qid = uqs_item.get('questionId', '')
                if '#' in qid:
                    answered_keys.append(qid)
        instanced_progress['answeredKeys'] = answered_keys

        # Collect unique instanced question IDs for BatchGetItem
        instanced_qids = set()
        for group in assigned.get('instanced', []):
            for qid in group.get('questionIds', []):
                instanced_qids.add(qid)

        # BatchGetItem from allQuestionDB for question metadata
        if instanced_qids:
            question_details = _batch_get_question_details(dynamodb, list(instanced_qids))

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'hasCompletedSurvey': item.get('hasCompletedSurvey', False),
            'selectedLifeEvents': item.get('selectedLifeEvents'),
            'surveyCompletedAt': item.get('surveyCompletedAt'),
            'lifeEventInstances': item.get('lifeEventInstances'),
            'assignedQuestionCount': assigned_question_count,
            'assignedQuestions': assigned,
            'instancedProgress': instanced_progress,
            'questionDetails': question_details,
        }, cls=DecimalEncoder)
    }


def _batch_get_question_details(dynamodb, question_ids):
    """
    Query allQuestionDB for the given question IDs.
    Returns a dict of questionId -> { text, difficulty, questionType }.

    allQuestionDB has a composite key (questionId HASH + questionType RANGE),
    so we query by partition key to get the first matching item per questionId.
    """
    details = {}
    table = dynamodb.Table(TABLE_ALL_QUESTIONS)
    for qid in question_ids:
        if qid in details:
            continue
        try:
            resp = table.query(
                KeyConditionExpression='questionId = :qid',
                ExpressionAttributeValues={':qid': qid},
                ProjectionExpression='questionId, questionText, difficulty, questionType',
                Limit=1,
            )
            items = resp.get('Items', [])
            if items:
                q_item = items[0]
                details[qid] = {
                    'text': q_item.get('questionText', ''),
                    'difficulty': q_item.get('difficulty', 0),
                    'questionType': q_item.get('questionType', ''),
                }
        except Exception as e:
            print(f"[Survey] Error querying question {qid}: {e}")
    return details


# ---------------------------------------------------------------------------
# POST /survey/submit
# ---------------------------------------------------------------------------
def handle_submit(event, user_id):
    """Validate survey, assign questions, persist everything."""
    body = json.loads(event.get('body') or '{}')

    # --- Validation ---
    selected_events = body.get('selectedLifeEvents')
    if selected_events is None or not isinstance(selected_events, list):
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: selectedLifeEvents'})
        }

    # Validate each key
    for key in selected_events:
        if not isinstance(key, str):
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'selectedLifeEvents must contain strings, got: {type(key).__name__}'})
            }
        if key != 'other' and key not in LIFE_EVENT_KEYS:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Invalid life event key: {key}'})
            }

    # Validate lifeEventInstances
    life_event_instances = body.get('lifeEventInstances', [])
    if not isinstance(life_event_instances, list):
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'lifeEventInstances must be an array'})
        }

    for inst_group in life_event_instances:
        event_key = inst_group.get('eventKey', '')
        if event_key not in INSTANCEABLE_KEYS:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Invalid instanceable event key: {event_key}'})
            }
        instances = inst_group.get('instances', [])
        if not instances:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Instances array is empty for event: {event_key}'})
            }
        for inst in instances:
            name = inst.get('name', '').strip()
            if not name:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(event),
                    'body': json.dumps({'error': 'Instance name cannot be empty'})
                }
            ordinal = inst.get('ordinal')
            if not isinstance(ordinal, int) or ordinal < 1:
                return {
                    'statusCode': 400,
                    'headers': cors_headers(event),
                    'body': json.dumps({'error': f'Instance ordinal must be a positive integer, got: {ordinal}'})
                }
            # Validate got_married status
            if event_key == 'got_married':
                status = inst.get('status')
                if not status or status not in VALID_MARRIAGE_STATUSES:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers(event),
                        'body': json.dumps({
                            'error': f'got_married instances require a status field (married, divorced, or deceased). Got: {status}'
                        })
                    }

    custom_life_event = body.get('customLifeEvent', '')

    # --- Derive status-aware keys from got_married instances ---
    effective_events = set(selected_events)
    for inst_group in life_event_instances:
        if inst_group['eventKey'] == 'got_married':
            for inst in inst_group['instances']:
                status = inst.get('status')
                if status == 'divorced':
                    effective_events.add('spouse_divorced')
                elif status == 'deceased':
                    effective_events.add('spouse_deceased')
                elif status == 'married':
                    effective_events.add('spouse_still_married')

    # --- Scan all valid questions ---
    dynamodb = boto3.resource('dynamodb')
    all_q_table = dynamodb.Table(TABLE_ALL_QUESTIONS)

    all_questions = []
    scan_resp = all_q_table.scan()
    all_questions.extend(scan_resp.get('Items', []))
    while 'LastEvaluatedKey' in scan_resp:
        scan_resp = all_q_table.scan(ExclusiveStartKey=scan_resp['LastEvaluatedKey'])
        all_questions.extend(scan_resp.get('Items', []))

    # --- Run assignment logic ---
    assigned = assign_questions(effective_events, life_event_instances, all_questions)

    # Count total assigned
    assigned_count = len(assigned['standard'])
    for group in assigned['instanced']:
        assigned_count += len(group['questionIds'])

    # --- Persist to userStatusDB ---
    now = datetime.now(timezone.utc).isoformat()
    user_status_table = dynamodb.Table(TABLE_USER_STATUS)

    # Check if this is a retake (user already completed the survey)
    existing_record = user_status_table.get_item(Key={'userId': user_id}).get('Item', {})
    is_retake = existing_record.get('hasCompletedSurvey', False)
    old_assigned = existing_record.get('assignedQuestions') if is_retake else None

    try:
        user_status_table.update_item(
            Key={'userId': user_id},
            UpdateExpression=(
                'SET hasCompletedSurvey = :hcs, '
                'selectedLifeEvents = :sle, '
                'surveyCompletedAt = :sca, '
                'lifeEventInstances = :lei, '
                'assignedQuestions = :aq, '
                'customLifeEvent = :cle'
            ),
            ExpressionAttributeValues={
                ':hcs': True,
                ':sle': selected_events,
                ':sca': now,
                ':lei': life_event_instances,
                ':aq': assigned,
                ':cle': custom_life_event,
            },
        )
    except ClientError as e:
        return error_response(500, 'Failed to save survey. Please try again.', e, event)

    # --- Reinitialize or diff-update progress ---
    try:
        if is_retake and old_assigned:
            diff_update_progress(user_id, old_assigned, assigned, all_questions, dynamodb)
            print(f"[Survey] Diff-based progress update for retake, user {user_id}")
        else:
            reinitialize_progress(user_id, assigned, all_questions, dynamodb)
            print(f"[Survey] Full progress initialization, user {user_id}")
    except Exception as e:
        print(f"[Survey] Progress reinitialization failed: {e}")
        # Survey data is saved — progress can be fixed later
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'message': 'Survey saved but progress initialization failed. Please refresh.',
                'assignedQuestionCount': assigned_count,
            })
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'message': 'Survey completed',
            'assignedQuestionCount': assigned_count,
        })
    }


# ---------------------------------------------------------------------------
# Question Assignment Logic
# ---------------------------------------------------------------------------
def assign_questions(effective_events, life_event_instances, all_questions):
    """
    Filter questions and build the assignedQuestions structure.

    Returns:
        dict with 'standard' (list of questionId) and 'instanced' (list of instance groups)
    """
    # Build instance lookup: eventKey -> [instances]
    instance_map = {}
    for inst_group in life_event_instances:
        instance_map[inst_group['eventKey']] = inst_group['instances']

    standard = []
    # Key: (eventKey, ordinal) -> { eventKey, instanceName, instanceOrdinal, questionIds }
    instanced = {}

    for q in all_questions:
        if not (q.get('Valid') == 1 if 'Valid' in q else q.get('active', False)):
            continue

        required = q.get('requiredLifeEvents', [])

        # Check if question matches user's events
        if required and not all(k in effective_events for k in required):
            continue

        # Question matches — route to standard or instanced
        if not q.get('isInstanceable', False):
            standard.append(q['questionId'])
        else:
            # Find matching instances for this instanceable question
            matching = _get_matching_instances(q, instance_map)
            for inst in matching:
                key = (inst['eventKey'], inst['ordinal'])
                if key not in instanced:
                    instanced[key] = {
                        'eventKey': inst['eventKey'],
                        'instanceName': inst['name'],
                        'instanceOrdinal': inst['ordinal'],
                        'questionIds': [],
                    }
                instanced[key]['questionIds'].append(q['questionId'])

    # Sort instanced groups by eventKey then ordinal
    sorted_instanced = sorted(
        instanced.values(),
        key=lambda g: (g['eventKey'], g['instanceOrdinal'])
    )

    return {'standard': standard, 'instanced': sorted_instanced}


def _get_matching_instances(question, instance_map):
    """
    For an instanceable question, determine which instances it applies to.
    Handles status-aware keys for got_married.
    """
    required = question.get('requiredLifeEvents', [])

    for req_key in required:
        # Check status-derived keys first
        if req_key in STATUS_KEY_MAP:
            base_key, required_status = STATUS_KEY_MAP[req_key]
            instances = instance_map.get(base_key, [])
            return [
                {'eventKey': base_key, **i}
                for i in instances
                if i.get('status') == required_status
            ]

        # Check base instanceable keys
        if req_key in instance_map:
            return [
                {'eventKey': req_key, **i}
                for i in instance_map[req_key]
            ]

    return []


# ---------------------------------------------------------------------------
# Progress Reinitialization
# ---------------------------------------------------------------------------
def reinitialize_progress(user_id, assigned, all_questions, dynamodb):
    """
    Delete existing progress records and create new ones for assigned
    difficulty-1 questions, grouped by questionType.
    """
    progress_table = dynamodb.Table(TABLE_QUESTION_PROGRESS)

    # Delete existing progress records for this user
    existing = progress_table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id},
    )
    for item in existing.get('Items', []):
        progress_table.delete_item(
            Key={
                'userId': user_id,
                'questionType': item['questionType'],
            }
        )
    # Handle pagination
    while 'LastEvaluatedKey' in existing:
        existing = progress_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ExclusiveStartKey=existing['LastEvaluatedKey'],
        )
        for item in existing.get('Items', []):
            progress_table.delete_item(
                Key={
                    'userId': user_id,
                    'questionType': item['questionType'],
                }
            )

    # Build a lookup: questionId -> question record (for text and type)
    q_lookup = {}
    for q in all_questions:
        q_lookup[q['questionId']] = q

    # Group assigned difficulty-1 questions by questionType
    # Standard questions
    by_type = {}  # questionType -> { ids: [], texts: [] }

    for qid in assigned['standard']:
        q = q_lookup.get(qid)
        if not q:
            continue
        diff = int(q.get('difficulty', 0))
        if diff != 1:
            continue
        qtype = q.get('questionType', 'unknown')
        if qtype not in by_type:
            by_type[qtype] = {'ids': [], 'texts': []}
        by_type[qtype]['ids'].append(qid)
        by_type[qtype]['texts'].append(q.get('questionText', ''))

    # Instanced questions — each instance copy counts separately
    for group in assigned['instanced']:
        for qid in group['questionIds']:
            q = q_lookup.get(qid)
            if not q:
                continue
            diff = int(q.get('difficulty', 0))
            if diff != 1:
                continue
            qtype = q.get('questionType', 'unknown')
            if qtype not in by_type:
                by_type[qtype] = {'ids': [], 'texts': []}
            # Use composite key for instanced
            instance_key = f"{group['eventKey']}:{group['instanceOrdinal']}"
            composite_id = f"{qid}#{instance_key}"
            # Replace placeholder in text with instance name
            text = q.get('questionText', '')
            placeholder = q.get('instancePlaceholder', '')
            if placeholder and group.get('instanceName'):
                text = text.replace(placeholder, group['instanceName'])
            by_type[qtype]['ids'].append(composite_id)
            by_type[qtype]['texts'].append(text)

    # Create progress records for each questionType
    for qtype, data in by_type.items():
        total_for_type = len(data['ids'])
        progress_table.put_item(Item={
            'userId': user_id,
            'questionType': qtype,
            'currentQuestLevel': 1,
            'numQuestComplete': 0,
            'totalQuestAtCurrLevel': total_for_type,
            'remainQuestAtCurrLevel': data['ids'],
            'remainQuestTextAtCurrLevel': data['texts'],
        })

    print(f"[Survey] Progress initialized: {len(by_type)} question types, user {user_id}")


# ---------------------------------------------------------------------------
# Diff-Based Progress Update (for retakes)
# ---------------------------------------------------------------------------
def diff_update_progress(user_id, old_assigned, new_assigned, all_questions, dynamodb):
    """
    Diff old and new assignedQuestions. Kept questions retain progress,
    added questions are inserted as unanswered, removed questions are
    dropped from assignedQuestions but video responses are preserved.
    """
    progress_table = dynamodb.Table(TABLE_QUESTION_PROGRESS)

    # Build sets of all question identifiers (questionId for standard, questionId#instanceKey for instanced)
    def build_id_set(assigned):
        ids = set()
        if isinstance(assigned, list):
            # Legacy flat list
            return set(assigned)
        for qid in assigned.get('standard', []):
            ids.add(qid)
        for group in assigned.get('instanced', []):
            instance_key = f"{group['eventKey']}:{group['instanceOrdinal']}"
            for qid in group['questionIds']:
                ids.add(f"{qid}#{instance_key}")
        return ids

    old_ids = build_id_set(old_assigned)
    new_ids = build_id_set(new_assigned)

    kept = old_ids & new_ids
    added = new_ids - old_ids
    removed = old_ids - new_ids

    print(f"[Survey] Diff: {len(kept)} kept, {len(added)} added, {len(removed)} removed")

    # For now, do a simple approach: if there are changes, reinitialize progress
    # but preserve completed question counts where possible.
    # A full diff-based update of individual progress records is complex —
    # the simple approach is safe and correct for the initial implementation.
    if added or removed:
        # Build lookup for question metadata
        q_lookup = {}
        for q in all_questions:
            q_lookup[q['questionId']] = q

        # Read existing progress to preserve completion counts
        existing_progress = {}
        resp = progress_table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id},
        )
        for item in resp.get('Items', []):
            existing_progress[item['questionType']] = item
        while 'LastEvaluatedKey' in resp:
            resp = progress_table.query(
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ExclusiveStartKey=resp['LastEvaluatedKey'],
            )
            for item in resp.get('Items', []):
                existing_progress[item['questionType']] = item

        # Reinitialize with new assigned questions, preserving numQuestComplete
        # where the question type still exists
        reinitialize_progress(user_id, new_assigned, all_questions, dynamodb)

        # Restore completion counts for kept question types
        for qtype, old_item in existing_progress.items():
            completed = int(old_item.get('numQuestComplete', 0))
            if completed > 0:
                try:
                    progress_table.update_item(
                        Key={'userId': user_id, 'questionType': qtype},
                        UpdateExpression='SET numQuestComplete = :nc',
                        ExpressionAttributeValues={':nc': completed},
                        ConditionExpression='attribute_exists(userId)',
                    )
                except Exception:
                    pass  # Question type might not exist in new progress
    else:
        print("[Survey] No changes in assigned questions — skipping progress update")
