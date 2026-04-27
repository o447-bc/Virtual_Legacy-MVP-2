"""
AdminThemes Lambda — Apply life event tags to all questions in a theme.

Route: PUT /admin/themes/{questionType}
"""
import json
import os
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
    print(f"[AdminThemes] Event: {json.dumps(event, default=str)}")

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(event), 'body': ''}

    admin = verify_admin(event)
    if not admin:
        return {
            'statusCode': 403,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Forbidden: admin access required'})
        }
    admin_email, _ = admin

    try:
        question_type = (event.get('pathParameters') or {}).get('questionType')
        if not question_type:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'Missing questionType in path'})
            }

        # URL-decode the questionType (spaces come as %20 or +)
        from urllib.parse import unquote
        question_type = unquote(question_type)

        body = json.loads(event.get('body') or '{}')
        required_events = body.get('requiredLifeEvents', [])
        is_instanceable = body.get('isInstanceable', False)
        instance_placeholder = body.get('instancePlaceholder', '')
        prompt_description = body.get('promptDescription')

        # Validate promptDescription length if present
        if prompt_description is not None and len(prompt_description) > 1000:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'promptDescription must be 1000 characters or fewer'})
            }

        # Validate life event keys
        invalid_keys = validate_life_event_keys(required_events)
        if invalid_keys:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Invalid life event keys: {", ".join(invalid_keys)}'})
            }

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        now = datetime.now(timezone.utc).isoformat()

        # Find all questions with this questionType
        all_questions = []
        response = table.scan(
            FilterExpression='questionType = :qt',
            ExpressionAttributeValues={':qt': question_type},
            ProjectionExpression='questionId',
        )
        all_questions.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='questionType = :qt',
                ExpressionAttributeValues={':qt': question_type},
                ProjectionExpression='questionId',
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            all_questions.extend(response.get('Items', []))

        if not all_questions:
            return {
                'statusCode': 404,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'No questions found for type: {question_type}'})
            }

        # Build dynamic UpdateExpression
        update_parts = [
            'requiredLifeEvents = :rle',
            'isInstanceable = :inst',
            'instancePlaceholder = :ph',
            'lastModifiedBy = :by',
            'lastModifiedAt = :at',
        ]
        expr_values = {
            ':rle': required_events,
            ':inst': is_instanceable,
            ':ph': instance_placeholder,
            ':by': admin_email,
            ':at': now,
        }

        if prompt_description is not None:
            update_parts.append('promptDescription = :pd')
            expr_values[':pd'] = prompt_description

        update_expression = 'SET ' + ', '.join(update_parts)

        # Update each question individually
        updated = 0
        for item in all_questions:
            qid = item['questionId']
            table.update_item(
                Key={
                    'questionId': qid,
                    'questionType': question_type,
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expr_values,
            )
            updated += 1

        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'message': 'Theme updated',
                'questionsUpdated': updated,
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
