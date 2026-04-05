"""
AdminStats Lambda — Dashboard summary statistics.

Route: GET /admin/stats
"""
import json
import os
from decimal import Decimal
from collections import defaultdict

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
    print(f"[AdminStats] Event: {json.dumps(event, default=str)}")

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

        total = len(all_questions)
        valid_count = 0
        invalid_count = 0
        question_types = set()
        difficulty_levels = set()
        instanceable_count = 0

        # Grid: questionType -> difficulty -> count (valid only)
        grid = defaultdict(lambda: defaultdict(int))

        # Coverage tracking for zero-coverage count
        covered_keys = set()

        for q in all_questions:
            is_valid = q.get('active', False)
            qtype = q.get('questionType', 'Unknown')
            diff = int(q.get('difficulty', 0))

            question_types.add(qtype)
            if diff > 0:
                difficulty_levels.add(diff)

            if is_valid:
                valid_count += 1
                grid[qtype][diff] += 1
                if q.get('isInstanceable', False):
                    instanceable_count += 1
                for key in q.get('requiredLifeEvents', []):
                    covered_keys.add(key)
            else:
                invalid_count += 1

        # Count life event keys with zero coverage
        zero_coverage = len([k for k in LIFE_EVENT_KEYS if k not in covered_keys])

        # Build grid with row and column totals
        grid_output = {}
        difficulty_totals = defaultdict(int)

        for qtype in sorted(grid.keys()):
            row = {}
            row_total = 0
            for d in range(1, 11):
                count = grid[qtype].get(d, 0)
                row[str(d)] = count
                row_total += count
                difficulty_totals[str(d)] += count
            row['total'] = row_total
            grid_output[qtype] = row

        grand_total = sum(difficulty_totals.values())

        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({
                'totalQuestions': total,
                'validQuestions': valid_count,
                'invalidQuestions': invalid_count,
                'questionTypes': len(question_types),
                'difficultyLevels': len(difficulty_levels),
                'zeroCoverageKeys': zero_coverage,
                'instanceableQuestions': instanceable_count,
                'grid': grid_output,
                'difficultyTotals': dict(difficulty_totals),
                'grandTotal': grand_total,
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', e, event)
