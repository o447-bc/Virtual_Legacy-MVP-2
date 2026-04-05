"""
AdminSimulate Lambda — Simulate question assignment for a set of life events.

Route: POST /admin/simulate
"""
import json
import os
from decimal import Decimal
from collections import defaultdict

import boto3

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_NAME = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')


def lambda_handler(event, context):
    print(f"[AdminSimulate] Event: {json.dumps(event, default=str)}")

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(event), 'body': ''}

    admin = verify_admin(event)
    if not admin:
        return {
            'statusCode': 403,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Forbidden: admin access required'})
        }

    try:
        body = json.loads(event.get('body') or '{}')
        selected_events = body.get('selectedLifeEvents', [])

        if not isinstance(selected_events, list):
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'selectedLifeEvents must be an array'})
            }

        selected_set = set(selected_events)

        # Scan all questions
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)

        all_questions = []
        response = table.scan()
        all_questions.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_questions.extend(response.get('Items', []))

        # Filter: same logic as Question_Assignment_Service
        assigned = []
        for q in all_questions:
            if not q.get('active', False):
                continue
            required = q.get('requiredLifeEvents', [])
            if not required:
                # Universal question — always included
                assigned.append(q)
            elif all(key in selected_set for key in required):
                assigned.append(q)

        # Group by questionType
        by_type = defaultdict(list)
        for q in assigned:
            by_type[q.get('questionType', 'Unknown')].append(q)

        result = {}
        for qtype, questions in sorted(by_type.items()):
            result[qtype] = {
                'count': len(questions),
                'questions': questions,
            }

        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'totalCount': len(assigned),
                'byQuestionType': result,
            }, cls=DecimalEncoder)
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
