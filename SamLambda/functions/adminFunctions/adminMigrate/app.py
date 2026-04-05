"""
AdminMigrate Lambda — One-time migration to backfill new attributes on existing questions.

Route: POST /admin/migrate
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin


TABLE_NAME = os.environ.get('TABLE_ALL_QUESTIONS', 'allQuestionDB')

# Attributes to backfill and their default values
DEFAULTS = {
    'requiredLifeEvents': [],
    'isInstanceable': False,
    'instancePlaceholder': '',
    'lastModifiedBy': 'system-migration',
    # lastModifiedAt is set dynamically
}


def lambda_handler(event, context):
    print(f"[AdminMigrate] Event: {json.dumps(event, default=str)}")

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
        now = datetime.now(timezone.utc).isoformat()

        # Scan all questions
        all_questions = []
        response = table.scan()
        all_questions.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_questions.extend(response.get('Items', []))

        updated = 0
        skipped = 0

        for item in all_questions:
            # Check which attributes are missing
            missing = {}
            for attr, default_val in DEFAULTS.items():
                if attr not in item:
                    missing[attr] = default_val

            if 'lastModifiedAt' not in item:
                missing['lastModifiedAt'] = now

            if not missing:
                skipped += 1
                continue

            # Build update expression for missing attributes only
            update_parts = []
            expr_names = {}
            expr_values = {}

            for attr, val in missing.items():
                name_ph = f'#{attr}'
                val_ph = f':{attr}'
                update_parts.append(f'{name_ph} = {val_ph}')
                expr_names[name_ph] = attr
                expr_values[val_ph] = val

            table.update_item(
                Key={
                    'questionId': item['questionId'],
                    'questionType': item['questionType'],
                },
                UpdateExpression='SET ' + ', '.join(update_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            updated += 1

        print(f"[AdminMigrate] Migration complete: {updated} updated, {skipped} skipped")

        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'message': 'Migration complete',
                'updated': updated,
                'skipped': skipped,
            })
        }

    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
