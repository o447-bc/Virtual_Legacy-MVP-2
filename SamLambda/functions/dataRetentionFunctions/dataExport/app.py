"""
DataExportFunction Lambda Handler

Handles data export requests: full Content_Package (Premium) and
lightweight GDPR portability export (all users).

Endpoints:
  POST /data/export-request   (Cognito Auth) — Full Content_Package export
  POST /data/gdpr-export      (Cognito Auth) — Lightweight GDPR text-only export
  GET  /data/export-status    (Cognito Auth) — Check export status

Also handles async invocation from StripeWebhookFunction for auto-export
on subscription cancellation.

Requirements: 1.1–1.9, 2.1–2.4, 6.1–6.7, 16.1
"""
import io
import json
import os
import sys
import zipfile
import logging
from datetime import datetime, timezone, timedelta

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

# Add shared layer to path
sys.path.append('/opt/python')

from cors import cors_headers
from responses import error_response
from email_utils import send_email_with_retry
from audit_logger import log_audit_event
from retention_config import get_config, get_current_time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS clients (module-level — reused across warm invocations)
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_s3 = boto3.client('s3', config=Config(signature_version='s3v4'))
_cognito = boto3.client('cognito-idp')

_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_TABLE_SUBSCRIPTIONS = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')
_TABLE_QUESTION_STATUS = os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB')
_TABLE_USER_STATUS = os.environ.get('TABLE_USER_STATUS', 'userStatusDB')
_TABLE_RELATIONSHIPS = os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB')
_S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
_EXPORTS_BUCKET = os.environ.get('EXPORTS_BUCKET', '')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')
_COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code: int, body: dict, event: dict = None) -> dict:
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body),
    }


# ===================================================================
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route requests by path + httpMethod, or handle async invocations."""

    # Handle async invocation from StripeWebhookFunction (auto-export on cancellation)
    if event.get('source') == 'auto_export_on_cancellation':
        return handle_auto_export(event)

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    # All endpoints require authentication
    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub')
    )
    if not user_id:
        return error_response(401, 'Unauthorized', event=event)

    try:
        if path == '/data/export-request' and method == 'POST':
            return handle_export_request(event, user_id)
        elif path == '/data/gdpr-export' and method == 'POST':
            return handle_gdpr_export(event, user_id)
        elif path == '/data/export-status' and method == 'GET':
            return handle_export_status(event, user_id)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[DATA_EXPORT] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Handler: POST /data/export-request (Premium full Content_Package)
# ===================================================================

def handle_export_request(event, user_id):
    """Create a full Content_Package export for Premium users."""
    now = get_current_time(event)

    # 1. Check subscription — Premium required
    sub_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)
    sub_resp = sub_table.get_item(Key={'userId': user_id})
    sub_item = sub_resp.get('Item', {})
    plan_id = sub_item.get('planId', 'free')
    status = sub_item.get('status', '')

    if plan_id != 'premium' or status not in ('active', 'trialing', 'comped'):
        return cors_response(403, {
            'error': 'Data export requires an active Premium subscription',
            'upgradeUrl': '/pricing',
        }, event)

    # 2. Check rate limit (one export per N days)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)
    rate_limit_days = get_config('export-rate-limit-days')

    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'export_request'}
    ).get('Item')

    if existing:
        active_status = existing.get('status', '')

        # Allow re-export if previous export failed or is stale pending_retrieval
        if active_status == 'processing':
            return cors_response(409, {
                'error': 'An export is already in progress',
                'status': active_status,
            }, event)

        # Only enforce rate limit if last export succeeded (status == 'ready')
        if active_status == 'ready':
            last_requested = existing.get('requestedAt', '')
            if last_requested:
                last_dt = datetime.fromisoformat(last_requested.replace('Z', '+00:00'))
                if (now - last_dt).days < rate_limit_days:
                    return cors_response(429, {
                        'error': f'Export rate limit: one export per {rate_limit_days} days',
                        'nextAvailable': (last_dt + timedelta(days=rate_limit_days)).isoformat(),
                    }, event)

        # pending_retrieval and failed statuses are allowed to re-export

    # 4. List all user content from S3
    content_objects = _list_user_content(user_id)

    # 7. Size check — prevent Lambda crash on very large content sets (>5GB)
    total_size = sum(obj.get('Size', 0) for obj in content_objects)
    max_export_size = 5 * 1024 * 1024 * 1024  # 5GB
    if total_size > max_export_size:
        return cors_response(413, {
            'error': 'Your content exceeds the maximum export size (5GB). '
                     'Please contact support@soulreel.net for assistance.',
            'totalSizeBytes': total_size,
        }, event)

    # 5. Check for Glacier content
    glacier_objects = [
        obj for obj in content_objects
        if obj.get('StorageClass', 'STANDARD') in (
            'GLACIER', 'DEEP_ARCHIVE', 'GLACIER_IR'
        )
    ]

    if glacier_objects:
        # Initiate retrieval for Glacier objects
        for obj in glacier_objects:
            tier = 'Standard'
            if obj['StorageClass'] == 'GLACIER_IR':
                tier = 'Expedited'
            try:
                _s3.restore_object(
                    Bucket=_S3_BUCKET,
                    Key=obj['Key'],
                    RestoreRequest={'Days': 7, 'GlacierJobParameters': {'Tier': tier}},
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'RestoreAlreadyInProgress':
                    raise

        # Update record to pending_retrieval
        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'export_request',
            'status': 'pending_retrieval',
            'requestedAt': now.isoformat(),
            'updatedAt': now.isoformat(),
            'exportType': 'content_package',
            'glacierObjectCount': len(glacier_objects),
        })

        log_audit_event('export_requested', user_id, {
            'exportType': 'content_package',
            'status': 'pending_retrieval',
            'glacierObjects': len(glacier_objects),
        }, initiator='user')

        # Notify user about retrieval delay
        user_email = _get_user_email(user_id)
        if user_email:
            send_email_with_retry(
                destination=user_email,
                subject='Your SoulReel Export — Retrieval in Progress',
                html_body=_build_retrieval_email_html(len(glacier_objects)),
                text_body=f'Some of your content is being retrieved from our archive. '
                          f'We will email you when your export is ready.',
                sender_email=_SENDER_EMAIL,
            )

        return cors_response(202, {
            'status': 'pending_retrieval',
            'message': 'Some content is being retrieved from archive. '
                       'We will email you when your export is ready.',
            'glacierObjectCount': len(glacier_objects),
        }, event)

    # TODO (Issue 8): A separate mechanism (S3 event notification or polling Lambda)
    # is needed to detect Glacier restore completion and automatically trigger the
    # ZIP build. For now, the user can manually re-trigger the export after the
    # restore completes — the rate limit logic allows re-export when the previous
    # status was 'pending_retrieval'.

    # 6. All content accessible — build ZIP
    return _build_and_upload_export(event, user_id, content_objects, now, retention_table)


def _build_and_upload_export(event, user_id, content_objects, now, retention_table):
    """Build ZIP archive, upload to exports-temp, generate presigned URL."""
    # Update status to processing
    retention_table.put_item(Item={
        'userId': user_id,
        'recordType': 'export_request',
        'status': 'processing',
        'requestedAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'exportType': 'content_package',
    })

    try:
        # Build data-portability.json
        portability_data = _build_data_portability(user_id)

        # Build manifest
        manifest = {
            'exportDate': now.isoformat(),
            'userId': user_id,
            'exportType': 'content_package',
            'schemaVersion': '1.0',
            'items': [],
        }

        # Create ZIP in memory (using /tmp for large files)
        zip_path = f'/tmp/export_{user_id}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add README.txt
            zf.writestr('README.txt', _build_readme_text())

            # Add data-portability.json
            zf.writestr('data-portability.json',
                        json.dumps(portability_data, indent=2, default=str))

            # Add all S3 content
            for obj in content_objects:
                key = obj['Key']
                try:
                    s3_obj = _s3.get_object(Bucket=_S3_BUCKET, Key=key)
                    content = s3_obj['Body'].read()
                    # Preserve directory structure in ZIP
                    zf.writestr(key, content)
                    manifest['items'].append({
                        'filename': key,
                        'size': len(content),
                        'lastModified': obj.get('LastModified', ''),
                        'storageClass': obj.get('StorageClass', 'STANDARD'),
                    })
                except ClientError as e:
                    logger.warning('Failed to get S3 object %s: %s', key, e)

            # Add manifest.json (after all items are collected)
            manifest['totalItems'] = len(manifest['items'])
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, default=str))

        # Upload ZIP to exports-temp bucket
        export_key = f'exports/{user_id}/{now.strftime("%Y%m%d_%H%M%S")}_content_package.zip'
        with open(zip_path, 'rb') as f:
            _s3.put_object(
                Bucket=_EXPORTS_BUCKET,
                Key=export_key,
                Body=f,
                ContentType='application/zip',
            )

        # Clean up temp file
        try:
            os.remove(zip_path)
        except OSError:
            pass

        # Generate presigned URL
        expiry_hours = get_config('export-link-expiry-hours')
        download_url = _s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': _EXPORTS_BUCKET, 'Key': export_key},
            ExpiresIn=expiry_hours * 3600,
        )

        # Calculate TTL for auto-cleanup (7 days from now)
        expires_at = int((now + timedelta(days=7)).timestamp())

        # Update record to ready
        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'export_request',
            'status': 'ready',
            'requestedAt': now.isoformat(),
            'updatedAt': now.isoformat(),
            'exportType': 'content_package',
            'downloadUrl': download_url,
            'expiresAt': expires_at,
            'exportKey': export_key,
        })

        log_audit_event('export_completed', user_id, {
            'exportType': 'content_package',
            'itemCount': len(manifest['items']),
            'exportKey': export_key,
        }, initiator='user')

        # Send email with download link
        user_email = _get_user_email(user_id)
        if user_email:
            send_email_with_retry(
                destination=user_email,
                subject='Your SoulReel Legacy — Export Ready',
                html_body=_build_export_ready_email_html(download_url, expiry_hours),
                text_body=f'Your SoulReel export is ready! Download it here: {download_url}\n'
                          f'This link expires in {expiry_hours} hours.',
                sender_email=_SENDER_EMAIL,
            )

        return cors_response(200, {
            'status': 'ready',
            'downloadUrl': download_url,
            'expiresIn': f'{expiry_hours} hours',
        }, event)

    except Exception as exc:
        # Update record to failed
        retention_table.update_item(
            Key={'userId': user_id, 'recordType': 'export_request'},
            UpdateExpression='SET #s = :s, updatedAt = :u',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'failed',
                ':u': now.isoformat(),
            },
        )
        log_audit_event('export_failed', user_id, {
            'exportType': 'content_package',
            'error': str(exc),
        }, initiator='user')
        raise


# ===================================================================
# Handler: POST /data/gdpr-export (lightweight text-only, all users)
# ===================================================================

def handle_gdpr_export(event, user_id):
    """Create a lightweight GDPR data portability export (text only, no videos)."""
    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Rate limit check (same window as full export)
    rate_limit_days = get_config('export-rate-limit-days')
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'export_request'}
    ).get('Item')

    if existing:
        active_status = existing.get('status', '')

        # Allow re-export if previous export failed or is stale pending_retrieval
        if active_status == 'processing':
            return cors_response(409, {
                'error': 'An export is already in progress',
                'status': active_status,
            }, event)

        # Only enforce rate limit if last export succeeded (status == 'ready')
        if active_status == 'ready':
            last_requested = existing.get('requestedAt', '')
            if last_requested:
                last_dt = datetime.fromisoformat(last_requested.replace('Z', '+00:00'))
                if (now - last_dt).days < rate_limit_days:
                    return cors_response(429, {
                        'error': f'Export rate limit: one export per {rate_limit_days} days',
                        'nextAvailable': (last_dt + timedelta(days=rate_limit_days)).isoformat(),
                    }, event)

        # pending_retrieval and failed statuses are allowed to re-export

    # Update status to processing
    retention_table.put_item(Item={
        'userId': user_id,
        'recordType': 'export_request',
        'status': 'processing',
        'requestedAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'exportType': 'gdpr_portability',
    })

    try:
        # Build data-portability.json (text data only — no videos)
        portability_data = _build_data_portability(user_id)

        # Upload JSON to exports-temp bucket
        export_key = f'exports/{user_id}/{now.strftime("%Y%m%d_%H%M%S")}_gdpr_portability.json'
        _s3.put_object(
            Bucket=_EXPORTS_BUCKET,
            Key=export_key,
            Body=json.dumps(portability_data, indent=2, default=str),
            ContentType='application/json',
        )

        # Generate presigned URL
        expiry_hours = get_config('export-link-expiry-hours')
        download_url = _s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': _EXPORTS_BUCKET, 'Key': export_key},
            ExpiresIn=expiry_hours * 3600,
        )

        expires_at = int((now + timedelta(days=7)).timestamp())

        # Update record to ready
        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'export_request',
            'status': 'ready',
            'requestedAt': now.isoformat(),
            'updatedAt': now.isoformat(),
            'exportType': 'gdpr_portability',
            'downloadUrl': download_url,
            'expiresAt': expires_at,
            'exportKey': export_key,
        })

        log_audit_event('export_completed', user_id, {
            'exportType': 'gdpr_portability',
            'exportKey': export_key,
        }, initiator='user')

        # Send email with download link
        user_email = _get_user_email(user_id)
        if user_email:
            send_email_with_retry(
                destination=user_email,
                subject='Your SoulReel Data Export — Ready',
                html_body=_build_gdpr_export_email_html(download_url, expiry_hours),
                text_body=f'Your SoulReel data export is ready! Download it here: {download_url}\n'
                          f'This link expires in {expiry_hours} hours.',
                sender_email=_SENDER_EMAIL,
            )

        return cors_response(200, {
            'status': 'ready',
            'downloadUrl': download_url,
            'expiresIn': f'{expiry_hours} hours',
        }, event)

    except Exception as exc:
        retention_table.update_item(
            Key={'userId': user_id, 'recordType': 'export_request'},
            UpdateExpression='SET #s = :s, updatedAt = :u',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'failed',
                ':u': now.isoformat(),
            },
        )
        log_audit_event('export_failed', user_id, {
            'exportType': 'gdpr_portability',
            'error': str(exc),
        }, initiator='user')
        raise


# ===================================================================
# Handler: GET /data/export-status
# ===================================================================

def handle_export_status(event, user_id):
    """Return the current export status for the user."""
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    resp = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'export_request'}
    )
    item = resp.get('Item')

    if not item:
        return cors_response(200, {
            'status': 'none',
            'message': 'No export request found',
        }, event)

    result = {
        'status': item.get('status', 'unknown'),
        'exportType': item.get('exportType', ''),
        'requestedAt': item.get('requestedAt', ''),
        'updatedAt': item.get('updatedAt', ''),
    }

    if item.get('downloadUrl'):
        result['downloadUrl'] = item['downloadUrl']
    if item.get('glacierObjectCount'):
        result['glacierObjectCount'] = item['glacierObjectCount']

    return cors_response(200, result, event)


# ===================================================================
# Handler: Auto-export on subscription cancellation
# ===================================================================

def handle_auto_export(event):
    """Handle async invocation from StripeWebhookFunction for auto-export."""
    user_id = event.get('userId')
    if not user_id:
        logger.error('[DATA_EXPORT] Auto-export invoked without userId')
        return {'statusCode': 400, 'body': 'Missing userId'}

    now = get_current_time(event)
    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Skip if user already exported within 24 hours
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'export_request'}
    ).get('Item')

    if existing:
        last_requested = existing.get('requestedAt', '')
        if last_requested:
            last_dt = datetime.fromisoformat(last_requested.replace('Z', '+00:00'))
            if (now - last_dt).total_seconds() < 86400:  # 24 hours
                logger.info('[DATA_EXPORT] Skipping auto-export for %s — recent export exists', user_id)
                return {'statusCode': 200, 'body': 'Skipped — recent export exists'}

        active_status = existing.get('status', '')
        if active_status in ('processing', 'pending_retrieval'):
            logger.info('[DATA_EXPORT] Skipping auto-export for %s — export in progress', user_id)
            return {'statusCode': 200, 'body': 'Skipped — export in progress'}

    # List content and build export
    content_objects = _list_user_content(user_id)

    # Check for Glacier content
    glacier_objects = [
        obj for obj in content_objects
        if obj.get('StorageClass', 'STANDARD') in (
            'GLACIER', 'DEEP_ARCHIVE', 'GLACIER_IR'
        )
    ]

    if glacier_objects:
        # For auto-export, initiate retrieval and mark pending
        for obj in glacier_objects:
            tier = 'Standard'
            if obj['StorageClass'] == 'GLACIER_IR':
                tier = 'Expedited'
            try:
                _s3.restore_object(
                    Bucket=_S3_BUCKET,
                    Key=obj['Key'],
                    RestoreRequest={'Days': 7, 'GlacierJobParameters': {'Tier': tier}},
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'RestoreAlreadyInProgress':
                    logger.warning('Failed to restore %s: %s', obj['Key'], e)

        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'export_request',
            'status': 'pending_retrieval',
            'requestedAt': now.isoformat(),
            'updatedAt': now.isoformat(),
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'glacierObjectCount': len(glacier_objects),
        })

        log_audit_event('export_requested', user_id, {
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'status': 'pending_retrieval',
        }, initiator='system')

        return {'statusCode': 202, 'body': 'Pending retrieval'}

    # All content accessible — build and upload
    return _build_and_upload_auto_export(user_id, content_objects, now, retention_table)


def _build_and_upload_auto_export(user_id, content_objects, now, retention_table):
    """Build and upload auto-export Content_Package (no API Gateway event)."""
    retention_table.put_item(Item={
        'userId': user_id,
        'recordType': 'export_request',
        'status': 'processing',
        'requestedAt': now.isoformat(),
        'updatedAt': now.isoformat(),
        'exportType': 'content_package',
        'source': 'auto_export_on_cancellation',
    })

    try:
        portability_data = _build_data_portability(user_id)

        manifest = {
            'exportDate': now.isoformat(),
            'userId': user_id,
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'schemaVersion': '1.0',
            'items': [],
        }

        zip_path = f'/tmp/export_{user_id}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('README.txt', _build_readme_text())
            zf.writestr('data-portability.json',
                        json.dumps(portability_data, indent=2, default=str))

            for obj in content_objects:
                key = obj['Key']
                try:
                    s3_obj = _s3.get_object(Bucket=_S3_BUCKET, Key=key)
                    content = s3_obj['Body'].read()
                    zf.writestr(key, content)
                    manifest['items'].append({
                        'filename': key,
                        'size': len(content),
                        'lastModified': obj.get('LastModified', ''),
                        'storageClass': obj.get('StorageClass', 'STANDARD'),
                    })
                except ClientError as e:
                    logger.warning('Failed to get S3 object %s: %s', key, e)

            manifest['totalItems'] = len(manifest['items'])
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, default=str))

        export_key = f'exports/{user_id}/{now.strftime("%Y%m%d_%H%M%S")}_content_package.zip'
        with open(zip_path, 'rb') as f:
            _s3.put_object(
                Bucket=_EXPORTS_BUCKET,
                Key=export_key,
                Body=f,
                ContentType='application/zip',
            )

        try:
            os.remove(zip_path)
        except OSError:
            pass

        expiry_hours = get_config('export-link-expiry-hours')
        download_url = _s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': _EXPORTS_BUCKET, 'Key': export_key},
            ExpiresIn=expiry_hours * 3600,
        )

        expires_at = int((now + timedelta(days=7)).timestamp())

        retention_table.put_item(Item={
            'userId': user_id,
            'recordType': 'export_request',
            'status': 'ready',
            'requestedAt': now.isoformat(),
            'updatedAt': now.isoformat(),
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'downloadUrl': download_url,
            'expiresAt': expires_at,
            'exportKey': export_key,
        })

        log_audit_event('export_completed', user_id, {
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'itemCount': len(manifest['items']),
        }, initiator='system')

        # Send cancellation export email
        user_email = _get_user_email(user_id)
        if user_email:
            send_email_with_retry(
                destination=user_email,
                subject='Your SoulReel Legacy — Download Your Stories',
                html_body=_build_cancellation_export_email_html(download_url, expiry_hours),
                text_body=(
                    f'Your SoulReel content export is ready! Download it here: {download_url}\n'
                    f'This link expires in {expiry_hours} hours.\n\n'
                    f'All your content remains accessible on the platform.\n'
                    f'Ready to come back? {_FRONTEND_URL}/pricing'
                ),
                sender_email=_SENDER_EMAIL,
            )

        return {'statusCode': 200, 'body': 'Export completed'}

    except Exception as exc:
        retention_table.update_item(
            Key={'userId': user_id, 'recordType': 'export_request'},
            UpdateExpression='SET #s = :s, updatedAt = :u',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': 'failed',
                ':u': now.isoformat(),
            },
        )
        log_audit_event('export_failed', user_id, {
            'exportType': 'content_package',
            'source': 'auto_export_on_cancellation',
            'error': str(exc),
        }, initiator='system')
        raise


# ===================================================================
# Shared helpers
# ===================================================================

def _list_user_content(user_id):
    """List all S3 objects for a user under conversations/ and user-responses/.

    Uses StorageClass from list_objects_v2 response directly (no HeadObject calls).
    If StorageClass is absent in the list response, defaults to STANDARD.
    """
    objects = []
    for prefix in [f'conversations/{user_id}/', f'user-responses/{user_id}/']:
        paginator = _s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=prefix):
            for obj in page.get('Contents', []):
                objects.append({
                    'Key': obj['Key'],
                    'Size': obj.get('Size', 0),
                    'LastModified': obj['LastModified'].isoformat()
                    if hasattr(obj.get('LastModified'), 'isoformat')
                    else str(obj.get('LastModified', '')),
                    'StorageClass': obj.get('StorageClass', 'STANDARD'),
                })
    return objects


def _get_user_email(user_id):
    """Get user email from Cognito."""
    try:
        resp = _cognito.admin_get_user(
            UserPoolId=_COGNITO_USER_POOL_ID,
            Username=user_id,
        )
        for attr in resp.get('UserAttributes', []):
            if attr['Name'] == 'email':
                return attr['Value']
        return ''
    except Exception as e:
        logger.warning('Failed to get user email for %s: %s', user_id, e)
        return ''


def _build_data_portability(user_id):
    """Build the data-portability.json structure with all text data."""
    data = {
        'schemaVersion': '1.0',
        'exportDate': datetime.now(timezone.utc).isoformat(),
        'userId': user_id,
        'profile': {},
        'questionResponses': [],
        'benefactors': [],
        'subscriptionHistory': {},
    }

    # User profile from Cognito
    try:
        resp = _cognito.admin_get_user(
            UserPoolId=_COGNITO_USER_POOL_ID,
            Username=user_id,
        )
        attrs = {a['Name']: a['Value'] for a in resp.get('UserAttributes', [])}
        profile_json = attrs.get('profile', '{}')
        try:
            profile_data = json.loads(profile_json)
        except (json.JSONDecodeError, TypeError):
            profile_data = {}
        # Issue 9: Convert Cognito UserCreateDate datetime to ISO string
        user_create_date = resp.get('UserCreateDate')
        account_created_at = (
            user_create_date.isoformat()
            if hasattr(user_create_date, 'isoformat')
            else str(user_create_date or '')
        )
        data['profile'] = {
            'firstName': attrs.get('given_name', ''),
            'lastName': attrs.get('family_name', ''),
            'email': attrs.get('email', ''),
            'personaType': profile_data.get('persona_type', ''),
            'accountCreatedAt': account_created_at,
        }
    except Exception as e:
        logger.warning('Failed to get user profile: %s', e)

    # Question responses from userQuestionStatusDB
    try:
        qs_table = _dynamodb.Table(_TABLE_QUESTION_STATUS)
        resp = qs_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
        )
        for item in resp.get('Items', []):
            data['questionResponses'].append({
                'questionId': item.get('questionId', ''),
                'responseType': item.get('responseType', ''),
                'audioOneSentence': item.get('audioOneSentence', ''),
                'audioDetailedSummary': item.get('audioDetailedSummary', ''),
                'completedAt': item.get('completedAt', ''),
                'status': item.get('status', ''),
            })
        # Handle pagination
        while resp.get('LastEvaluatedKey'):
            resp = qs_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id),
                ExclusiveStartKey=resp['LastEvaluatedKey'],
            )
            for item in resp.get('Items', []):
                data['questionResponses'].append({
                    'questionId': item.get('questionId', ''),
                    'responseType': item.get('responseType', ''),
                    'audioOneSentence': item.get('audioOneSentence', ''),
                    'audioDetailedSummary': item.get('audioDetailedSummary', ''),
                    'completedAt': item.get('completedAt', ''),
                    'status': item.get('status', ''),
                })
    except Exception as e:
        logger.warning('Failed to get question responses: %s', e)

    # Benefactors from PersonaRelationshipsDB
    try:
        rel_table = _dynamodb.Table(_TABLE_RELATIONSHIPS)
        resp = rel_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('initiator_id').eq(user_id)
        )
        for item in resp.get('Items', []):
            benefactor_id = item.get('related_user_id', '')
            benefactor_info = {
                'benefactorId': benefactor_id,
                'relationshipType': item.get('relationship_type', ''),
                'status': item.get('status', ''),
                'createdAt': item.get('created_at', ''),
            }
            # Look up benefactor name/email from Cognito (skip pending invites)
            if benefactor_id and not benefactor_id.startswith('pending#'):
                try:
                    cog_resp = _cognito.admin_get_user(
                        UserPoolId=_COGNITO_USER_POOL_ID,
                        Username=benefactor_id,
                    )
                    cog_attrs = {a['Name']: a['Value'] for a in cog_resp.get('UserAttributes', [])}
                    benefactor_info['name'] = f"{cog_attrs.get('given_name', '')} {cog_attrs.get('family_name', '')}".strip()
                    benefactor_info['email'] = cog_attrs.get('email', '')
                except Exception:
                    pass  # Cognito lookup failed — skip name/email
            data['benefactors'].append(benefactor_info)
    except Exception as e:
        logger.warning('Failed to get benefactors: %s', e)

    # Subscription history from UserSubscriptionsDB
    try:
        sub_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)
        resp = sub_table.get_item(Key={'userId': user_id})
        item = resp.get('Item', {})
        if item:
            data['subscriptionHistory'] = {
                'planId': item.get('planId', ''),
                'status': item.get('status', ''),
                'createdAt': item.get('createdAt', ''),
                'updatedAt': item.get('updatedAt', ''),
            }
    except Exception as e:
        logger.warning('Failed to get subscription history: %s', e)

    return data


# ===================================================================
# Email templates
# ===================================================================

def _build_readme_text():
    """Build the README.txt content for the Content_Package."""
    return """SoulReel Content Export
======================

This archive contains your complete SoulReel legacy content.

Contents:
- manifest.json        — Index of all included files with metadata
- data-portability.json — Your profile, responses, and text data (JSON)
- conversations/       — Your AI conversation recordings
- user-responses/      — Your video question responses

File Formats:
- Video files are in their original recorded format (WebM or MP4)
- Text data is in JSON format, readable by any text editor
- No transcoding or quality reduction has been applied

For questions, contact support@soulreel.net
"""


def _build_retrieval_email_html(glacier_count):
    """Build HTML email for Glacier retrieval notification."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Your Export Is Being Prepared</h2>
<p>Some of your content ({glacier_count} item{'s' if glacier_count != 1 else ''})
is stored in our long-term archive and needs to be retrieved before we can
package your export.</p>
<p>We'll email you as soon as your export is ready to download.
This typically takes a few hours.</p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""


def _build_export_ready_email_html(download_url, expiry_hours):
    """Build HTML email for export ready notification."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Your SoulReel Export Is Ready</h2>
<p>Your content export has been prepared and is ready to download.</p>
<p><a href="{download_url}" style="display: inline-block; padding: 12px 24px;
background-color: #4A90D9; color: white; text-decoration: none; border-radius: 6px;">
Download Your Export</a></p>
<p style="color: #666;">This link expires in {expiry_hours} hours.</p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""


def _build_gdpr_export_email_html(download_url, expiry_hours):
    """Build HTML email for GDPR export ready notification."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Your Data Export Is Ready</h2>
<p>Your data portability export has been prepared and is ready to download.</p>
<p><a href="{download_url}" style="display: inline-block; padding: 12px 24px;
background-color: #4A90D9; color: white; text-decoration: none; border-radius: 6px;">
Download Your Data</a></p>
<p style="color: #666;">This link expires in {expiry_hours} hours.
Your export contains your profile, responses, and text data in JSON format.</p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""


def _build_cancellation_export_email_html(download_url, expiry_hours):
    """Build HTML email for auto-export on subscription cancellation."""
    return f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<h2 style="color: #333;">Your SoulReel Legacy — Download Your Stories</h2>
<p>We've prepared a complete export of your SoulReel content as a courtesy.</p>
<p><a href="{download_url}" style="display: inline-block; padding: 12px 24px;
background-color: #4A90D9; color: white; text-decoration: none; border-radius: 6px;">
Download Your Stories</a></p>
<p style="color: #666;">This link expires in {expiry_hours} hours.</p>
<p><strong>Your content remains safe.</strong> All your recordings and stories
are still accessible on SoulReel. Your benefactors can continue viewing
your shared content.</p>
<p>Ready to come back? <a href="{_FRONTEND_URL}/pricing">Resubscribe here</a></p>
<p style="color: #666; font-size: 14px;">— The SoulReel Team</p>
</body></html>
"""
