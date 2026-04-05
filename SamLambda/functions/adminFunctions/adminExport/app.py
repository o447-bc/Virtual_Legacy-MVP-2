"""
AdminExport Lambda — Export questions as CSV or JSON.

Route: GET /admin/export?format=csv|json
"""
import json
import os
import csv
import io
from decimal import Decimal

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

CSV_COLUMNS = [
    'questionId', 'questionType', 'themeName', 'difficulty', 'active', 'questionText',
    'requiredLifeEvents', 'isInstanceable', 'instancePlaceholder',
    'lastModifiedBy', 'lastModifiedAt',
]


def lambda_handler(event, context):
    print(f"[AdminExport] Event: {json.dumps(event, default=str)}")

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
        params = event.get('queryStringParameters') or {}
        export_format = params.get('format', 'json').lower()

        if export_format not in ('csv', 'json'):
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'format must be csv or json'})
            }

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)

        all_questions = []
        response = table.scan()
        all_questions.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_questions.extend(response.get('Items', []))

        # Normalize missing attributes
        for q in all_questions:
            q.setdefault('requiredLifeEvents', [])
            q.setdefault('isInstanceable', False)
            q.setdefault('instancePlaceholder', '')
            q.setdefault('lastModifiedBy', '')
            q.setdefault('lastModifiedAt', '')

        headers = cors_headers(event)

        if export_format == 'json':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'questions': all_questions}, cls=DecimalEncoder)
            }

        # CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_COLUMNS)

        for q in all_questions:
            row = []
            for col in CSV_COLUMNS:
                val = q.get(col, '')
                if col == 'requiredLifeEvents':
                    val = ';'.join(val) if isinstance(val, list) else str(val)
                elif isinstance(val, bool):
                    val = 'TRUE' if val else 'FALSE'
                elif isinstance(val, Decimal):
                    val = int(val) if val % 1 == 0 else float(val)
                row.append(val)
            writer.writerow(row)

        headers['Content-Type'] = 'text/csv'
        headers['Content-Disposition'] = 'attachment; filename="questions_export.csv"'

        return {
            'statusCode': 200,
            'headers': headers,
            'body': output.getvalue()
        }

    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
