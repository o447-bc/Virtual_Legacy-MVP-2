"""
AdminFeedback Lambda — CRUD for feedback reports (admin only).

Routes:
  GET    /admin/feedback              — List all reports (newest first)
  GET    /admin/feedback/{reportId}   — Get a single report
  PATCH  /admin/feedback/{reportId}   — Update report status (active/archived)
  DELETE /admin/feedback/{reportId}   — Permanently delete a report

Requirements: 12.1–12.7
"""
import os
import json
import sys
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Add shared layer to path
sys.path.insert(0, '/opt/python')

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin
from structured_logger import StructuredLog


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


TABLE_NAME = os.environ.get('TABLE_FEEDBACK_REPORTS', 'FeedbackReportsDB')
GSI_NAME = 'submittedAt-index'
_VALID_STATUSES = ('active', 'archived')


def lambda_handler(event, context):
    log = StructuredLog(event, context)
    log.info('AdminFeedbackRequest', details={
        'httpMethod': event.get('httpMethod', ''),
        'resource': event.get('resource', ''),
    })

    # OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': '',
        }

    # Admin auth check
    admin = verify_admin(event)
    if not admin:
        return {
            'statusCode': 403,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Forbidden: admin access required'}),
        }

    method = event.get('httpMethod', '')
    resource = event.get('resource', '')
    path_params = event.get('pathParameters') or {}

    try:
        # GET /admin/feedback — list all
        if method == 'GET' and resource == '/admin/feedback':
            return _handle_list(event, log)

        # GET /admin/feedback/{reportId} — single report
        if method == 'GET' and 'reportId' in path_params:
            return _handle_get(event, path_params['reportId'], log)

        # PATCH /admin/feedback/{reportId} — update status
        if method == 'PATCH' and 'reportId' in path_params:
            return _handle_patch(event, path_params['reportId'], log)

        # DELETE /admin/feedback/{reportId} — delete
        if method == 'DELETE' and 'reportId' in path_params:
            return _handle_delete(event, path_params['reportId'], log)

        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': f'Unsupported route: {method} {resource}'}),
        }

    except ClientError as e:
        log.log_aws_error('DynamoDB', 'AdminFeedback', e)
        return error_response(500, 'A server error occurred. Please try again.', e, event, log=log)
    except Exception as e:
        log.error('UnexpectedFailure', e)
        return error_response(500, 'An unexpected error occurred. Please try again.', e, event, log=log)


def _handle_list(event, log):
    """GET /admin/feedback — Query GSI for all reports, newest first."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    items = []
    response = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=boto3.dynamodb.conditions.Key('gsiPk').eq('ALL'),
        ScanIndexForward=False,  # descending by submittedAt
    )
    items.extend(response.get('Items', []))

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('gsiPk').eq('ALL'),
            ScanIndexForward=False,
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'reports': items}, cls=DecimalEncoder),
    }


def _handle_get(event, report_id, log):
    """GET /admin/feedback/{reportId} — Retrieve a single report."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    resp = table.get_item(Key={'reportId': report_id})
    item = resp.get('Item')

    if not item:
        return {
            'statusCode': 404,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Report not found'}),
        }

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'report': item}, cls=DecimalEncoder),
    }


def _handle_patch(event, report_id, log):
    """PATCH /admin/feedback/{reportId} — Update report status."""
    body = json.loads(event.get('body') or '{}')
    new_status = body.get('status')

    if new_status not in _VALID_STATUSES:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': "Invalid status. Must be 'active' or 'archived'"}),
        }

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    try:
        table.update_item(
            Key={'reportId': report_id},
            UpdateExpression='SET #s = :s',
            ConditionExpression='attribute_exists(reportId)',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': new_status},
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'Report not found'}),
            }
        raise

    log.info('FeedbackStatusUpdated', details={
        'reportId': report_id,
        'newStatus': new_status,
    })

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'message': 'Status updated'}),
    }


def _handle_delete(event, report_id, log):
    """DELETE /admin/feedback/{reportId} — Permanently delete a report."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    try:
        table.delete_item(
            Key={'reportId': report_id},
            ConditionExpression='attribute_exists(reportId)',
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'headers': cors_headers(event),
                'body': json.dumps({'error': 'Report not found'}),
            }
        raise

    log.info('FeedbackDeleted', details={'reportId': report_id})

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'message': 'Report deleted'}),
    }
