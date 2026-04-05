"""
AdminCoverage Lambda — Life event coverage report.

Route: GET /admin/coverage
"""
import json
import os
from decimal import Decimal

import boto3

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin
from life_event_registry import LIFE_EVENT_KEYS


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_NAME = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')


def lambda_handler(event, context):
    print(f"[AdminCoverage] Event: {json.dumps(event, default=str)}")

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
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)

        all_questions = []
        response = table.scan()
        all_questions.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_questions.extend(response.get('Items', []))

        # Initialize coverage for every key
        coverage = {}
        for key in LIFE_EVENT_KEYS:
            coverage[key] = {'total': 0, 'instanceable': 0, 'nonInstanceable': 0}

        universal_count = 0

        for q in all_questions:
            if q.get('Valid') != 1:
                continue

            required = q.get('requiredLifeEvents', [])
            is_inst = q.get('isInstanceable', False)

            if not required:
                universal_count += 1
                continue

            for key in required:
                if key in coverage:
                    coverage[key]['total'] += 1
                    if is_inst:
                        coverage[key]['instanceable'] += 1
                    else:
                        coverage[key]['nonInstanceable'] += 1

        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'coverage': coverage,
                'universalCount': universal_count,
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
