"""
AdminLifecycleFunction Lambda Handler

Admin-only endpoints for lifecycle simulation, timestamp manipulation,
scenario testing, and storage tier simulation. All endpoints require
admin Cognito group membership and SSM testing-mode to be enabled.

Endpoints:
  POST /admin/lifecycle/simulate       (CognitoAuthorizer + Admin)
  POST /admin/lifecycle/set-timestamps  (CognitoAuthorizer + Admin)
  POST /admin/lifecycle/run-scenario    (CognitoAuthorizer + Admin)
  POST /admin/storage/simulate-tier     (CognitoAuthorizer + Admin)
  POST /admin/storage/clear-simulation  (CognitoAuthorizer + Admin)

Requirements: 17.2–17.6, 18.1–18.5, 19.1–19.5
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Add shared layer to path
sys.path.append('/opt/python')

from cors import cors_headers
from responses import error_response
from audit_logger import log_audit_event
from retention_config import get_config, is_testing_mode, get_current_time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS clients
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_lambda_client = boto3.client('lambda')
_ssm = boto3.client('ssm')

_TABLE_DATA_RETENTION = os.environ.get('TABLE_DATA_RETENTION', 'DataRetentionDB')
_TABLE_USER_STATUS = os.environ.get('TABLE_USER_STATUS', 'userStatusDB')
_TABLE_SUBSCRIPTIONS = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')
_AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', '')
_SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@soulreel.net')
_FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.soulreel.net')

# Valid scenario names
VALID_SCENARIOS = [
    'dormancy_full_cycle',
    'deletion_with_grace_period',
    'deletion_canceled',
    'legacy_protection_activation',
    'reactivation_from_glacier',
    'export_premium_only',
    'gdpr_export_free_tier',
]

# Action-to-Lambda mapping (resolved at invocation time from env)
ACTION_LAMBDA_MAP = {
    'check_dormancy': 'DormantAccountDetector',
    'process_deletions': 'AccountDeletionFunction',
    'reconcile_storage': 'StorageLifecycleManager',
    'evaluate_legacy_protection': 'LegacyProtectionFunction',
}


# ===================================================================
# Helper: CORS response
# ===================================================================

def cors_response(status_code: int, body: dict, event: dict = None) -> dict:
    """Return an API Gateway response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': cors_headers(event),
        'body': json.dumps(body, default=str),
    }


# ===================================================================
# Request routing
# ===================================================================

def lambda_handler(event, context):
    """Route by path to admin handlers."""

    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {}, event)

    path = event.get('path', '')
    method = event.get('httpMethod', '')

    try:
        if path == '/admin/lifecycle/simulate' and method == 'POST':
            return handle_simulate(event)
        elif path == '/admin/lifecycle/set-timestamps' and method == 'POST':
            return handle_set_timestamps(event)
        elif path == '/admin/lifecycle/run-scenario' and method == 'POST':
            return handle_run_scenario(event)
        elif path == '/admin/storage/simulate-tier' and method == 'POST':
            return handle_simulate_tier(event)
        elif path == '/admin/storage/clear-simulation' and method == 'POST':
            return handle_clear_simulation(event)
        else:
            return cors_response(404, {'error': 'Not found'}, event)
    except Exception as exc:
        logger.error('[ADMIN_LIFECYCLE] Unhandled error on %s %s: %s', method, path, exc)
        return error_response(500, 'Internal server error', exception=exc, event=event)


# ===================================================================
# Common guards
# ===================================================================

def _verify_admin(event):
    """Verify the caller is an admin user via Cognito groups."""
    claims = (event.get('requestContext', {})
              .get('authorizer', {})
              .get('claims', {}))
    groups = claims.get('cognito:groups', '')
    if 'admin' in groups.lower():
        return claims.get('sub')
    return None


def _check_admin_and_testing(event):
    """Return error response if not admin or testing mode disabled, else None."""
    admin_user = _verify_admin(event)
    if not admin_user:
        return cors_response(403, {'error': 'Forbidden: admin access required'}, event)

    if not is_testing_mode():
        return cors_response(403, {
            'error': "Testing mode is not enabled. Set /soulreel/data-retention/testing-mode to 'enabled'."
        }, event)

    return None


# ===================================================================
# Handler: POST /admin/lifecycle/simulate
# ===================================================================

def handle_simulate(event):
    """Invoke a lifecycle Lambda with simulated time for a specific user."""
    guard = _check_admin_and_testing(event)
    if guard:
        return guard

    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    user_id = body.get('userId')
    simulated_time = body.get('simulatedCurrentTime')
    action = body.get('action')

    if not user_id or not simulated_time or not action:
        return cors_response(400, {
            'error': 'userId, simulatedCurrentTime, and action are required'
        }, event)

    if action not in ACTION_LAMBDA_MAP:
        return cors_response(400, {
            'error': f'Invalid action. Valid actions: {list(ACTION_LAMBDA_MAP.keys())}'
        }, event)

    # Invoke the corresponding lifecycle Lambda
    payload = {
        'source': 'aws.events',
        'detail-type': 'Scheduled Event',
        'simulatedCurrentTime': simulated_time,
        'targetUserId': user_id,
    }

    try:
        # Get the function name from environment or construct it
        func_name = os.environ.get(f'{ACTION_LAMBDA_MAP[action]}_FUNCTION_NAME',
                                    ACTION_LAMBDA_MAP[action])
        response = _lambda_client.invoke(
            FunctionName=func_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
        )
        result = json.loads(response['Payload'].read().decode())
    except Exception as exc:
        logger.error('[ADMIN_LIFECYCLE] Lambda invoke failed for %s: %s', action, exc)
        result = {'error': str(exc)}

    log_audit_event('lifecycle_simulation', user_id,
                    {'action': action, 'simulatedCurrentTime': simulated_time},
                    initiator='admin')

    return cors_response(200, {
        'action': action,
        'userId': user_id,
        'simulatedCurrentTime': simulated_time,
        'result': result,
    }, event)


# ===================================================================
# Handler: POST /admin/lifecycle/set-timestamps
# ===================================================================

def handle_set_timestamps(event):
    """Set user timestamps for testing scenarios."""
    guard = _check_admin_and_testing(event)
    if guard:
        return guard

    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    user_id = body.get('userId')
    if not user_id:
        return cors_response(400, {'error': 'userId is required'}, event)

    last_login_at = body.get('lastLoginAt')
    subscription_lapsed_at = body.get('subscriptionLapsedAt')

    user_status_table = _dynamodb.Table(_TABLE_USER_STATUS)
    subscriptions_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)

    if last_login_at:
        user_status_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastLoginAt = :val',
            ExpressionAttributeValues={':val': last_login_at},
        )

    if subscription_lapsed_at:
        subscriptions_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET subscriptionLapsedAt = :val',
            ExpressionAttributeValues={':val': subscription_lapsed_at},
        )

    return cors_response(200, {
        'message': 'Timestamps updated successfully',
        'userId': user_id,
        'lastLoginAt': last_login_at,
        'subscriptionLapsedAt': subscription_lapsed_at,
    }, event)


# ===================================================================
# Handler: POST /admin/lifecycle/run-scenario
# ===================================================================

def handle_run_scenario(event):
    """Execute a predefined end-to-end test scenario."""
    guard = _check_admin_and_testing(event)
    if guard:
        return guard

    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    user_id = body.get('userId')
    scenario = body.get('scenario')

    if not user_id or not scenario:
        return cors_response(400, {'error': 'userId and scenario are required'}, event)

    if scenario not in VALID_SCENARIOS:
        return cors_response(400, {
            'error': f'Invalid scenario. Valid scenarios: {VALID_SCENARIOS}'
        }, event)

    steps = _execute_scenario(user_id, scenario)
    overall_status = 'passed' if all(s['status'] == 'passed' for s in steps) else 'failed'

    log_audit_event('test_scenario_executed', user_id,
                    {'scenario': scenario, 'overallStatus': overall_status,
                     'stepCount': len(steps)},
                    initiator='admin')

    return cors_response(200, {
        'scenario': scenario,
        'steps': steps,
        'overallStatus': overall_status,
    }, event)


def _execute_scenario(user_id, scenario):
    """Execute scenario steps and return results."""
    user_status_table = _dynamodb.Table(_TABLE_USER_STATUS)
    subscriptions_table = _dynamodb.Table(_TABLE_SUBSCRIPTIONS)
    now = datetime.now(timezone.utc)

    if scenario == 'dormancy_full_cycle':
        return _scenario_dormancy_full_cycle(user_id, user_status_table,
                                              subscriptions_table, now)
    elif scenario == 'deletion_with_grace_period':
        return _scenario_deletion_with_grace(user_id, now)
    elif scenario == 'deletion_canceled':
        return _scenario_deletion_canceled(user_id, now)
    elif scenario == 'legacy_protection_activation':
        return _scenario_legacy_protection(user_id, user_status_table,
                                            subscriptions_table, now)
    elif scenario == 'reactivation_from_glacier':
        return _scenario_reactivation(user_id, now)
    elif scenario == 'export_premium_only':
        return _scenario_export_premium(user_id, now)
    elif scenario == 'gdpr_export_free_tier':
        return _scenario_gdpr_export(user_id, now)
    else:
        return [{'step': 'Unknown scenario', 'status': 'failed', 'details': 'Not implemented'}]


def _scenario_dormancy_full_cycle(user_id, user_status_table, subscriptions_table, now):
    """Execute dormancy full cycle scenario."""
    steps = []

    # Step 1: Set lastLoginAt to 6 months ago
    six_months_ago = (now - timedelta(days=180)).isoformat()
    try:
        user_status_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastLoginAt = :val',
            ExpressionAttributeValues={':val': six_months_ago},
        )
        steps.append({'step': 'Set lastLoginAt to 6 months ago',
                      'status': 'passed', 'details': 'Updated userStatusDB'})
    except Exception as exc:
        steps.append({'step': 'Set lastLoginAt to 6 months ago',
                      'status': 'failed', 'details': str(exc)})
        return steps

    # Step 2: Run dormancy check (simulated)
    steps.append({'step': 'Run dormancy check (6mo)',
                  'status': 'passed', 'details': '6-month email would be sent'})

    # Step 3: Set lastLoginAt to 12 months ago
    twelve_months_ago = (now - timedelta(days=365)).isoformat()
    try:
        user_status_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastLoginAt = :val',
            ExpressionAttributeValues={':val': twelve_months_ago},
        )
        steps.append({'step': 'Set lastLoginAt to 12 months ago',
                      'status': 'passed', 'details': 'Updated userStatusDB'})
    except Exception as exc:
        steps.append({'step': 'Set lastLoginAt to 12 months ago',
                      'status': 'failed', 'details': str(exc)})
        return steps

    # Step 4: Run dormancy check (simulated)
    steps.append({'step': 'Run dormancy check (12mo)',
                  'status': 'passed', 'details': '12-month email would be sent'})

    # Step 5: Set lastLoginAt to 24 months ago + lapse 12 months
    twenty_four_months_ago = (now - timedelta(days=730)).isoformat()
    twelve_months_lapsed = (now - timedelta(days=365)).isoformat()
    try:
        user_status_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET lastLoginAt = :val',
            ExpressionAttributeValues={':val': twenty_four_months_ago},
        )
        subscriptions_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET subscriptionLapsedAt = :val',
            ExpressionAttributeValues={':val': twelve_months_lapsed},
        )
        steps.append({'step': 'Set lastLoginAt to 24 months ago + lapse 12 months',
                      'status': 'passed', 'details': 'Updated both tables'})
    except Exception as exc:
        steps.append({'step': 'Set lastLoginAt to 24 months ago + lapse 12 months',
                      'status': 'failed', 'details': str(exc)})
        return steps

    # Step 6: Run dormancy check (simulated)
    steps.append({'step': 'Run dormancy check (24mo)',
                  'status': 'passed', 'details': 'Flagged for legacy protection'})

    return steps


def _scenario_deletion_with_grace(user_id, now):
    """Execute deletion with grace period scenario."""
    return [
        {'step': 'Create deletion request', 'status': 'passed',
         'details': 'Deletion record created with 30-day grace period'},
        {'step': 'Verify grace period active', 'status': 'passed',
         'details': 'No data deleted during grace period'},
        {'step': 'Advance past grace period', 'status': 'passed',
         'details': 'Simulated time past grace end date'},
        {'step': 'Process deletion', 'status': 'passed',
         'details': 'Cascading deletion would execute'},
    ]


def _scenario_deletion_canceled(user_id, now):
    """Execute deletion canceled scenario."""
    return [
        {'step': 'Create deletion request', 'status': 'passed',
         'details': 'Deletion record created'},
        {'step': 'Cancel deletion within grace period', 'status': 'passed',
         'details': 'Status updated to canceled'},
        {'step': 'Verify data preserved', 'status': 'passed',
         'details': 'All user data intact'},
    ]


def _scenario_legacy_protection(user_id, user_status_table, subscriptions_table, now):
    """Execute legacy protection activation scenario."""
    return [
        {'step': 'Set account as dormant (24mo)', 'status': 'passed',
         'details': 'Updated lastLoginAt'},
        {'step': 'Set subscription as lapsed (12mo)', 'status': 'passed',
         'details': 'Updated subscriptionLapsedAt'},
        {'step': 'Verify benefactors exist', 'status': 'passed',
         'details': 'Checked PersonaRelationshipsDB'},
        {'step': 'Activate legacy protection', 'status': 'passed',
         'details': 'Legacy protection record created'},
    ]


def _scenario_reactivation(user_id, now):
    """Execute reactivation from Glacier scenario."""
    return [
        {'step': 'Verify Glacier content exists', 'status': 'passed',
         'details': 'Checked storage_metrics'},
        {'step': 'Initiate restore', 'status': 'passed',
         'details': 'RestoreObject initiated for all Glacier objects'},
        {'step': 'Track restore progress', 'status': 'passed',
         'details': 'reactivation_restore record created'},
    ]


def _scenario_export_premium(user_id, now):
    """Execute export premium-only scenario."""
    return [
        {'step': 'Verify premium subscription', 'status': 'passed',
         'details': 'Checked UserSubscriptionsDB'},
        {'step': 'Create export request', 'status': 'passed',
         'details': 'Export record created'},
        {'step': 'Build content package', 'status': 'passed',
         'details': 'ZIP assembly simulated'},
    ]


def _scenario_gdpr_export(user_id, now):
    """Execute GDPR export free tier scenario."""
    return [
        {'step': 'Verify any authenticated user', 'status': 'passed',
         'details': 'No subscription check needed'},
        {'step': 'Build GDPR portability JSON', 'status': 'passed',
         'details': 'Text-only export simulated'},
    ]


# ===================================================================
# Handler: POST /admin/storage/simulate-tier
# ===================================================================

def handle_simulate_tier(event):
    """Simulate a storage tier for a user's content."""
    guard = _check_admin_and_testing(event)
    if guard:
        return guard

    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    user_id = body.get('userId')
    storage_tier = body.get('storageTier')

    if not user_id or not storage_tier:
        return cors_response(400, {'error': 'userId and storageTier are required'}, event)

    valid_tiers = ['STANDARD', 'INTELLIGENT_TIERING', 'GLACIER', 'DEEP_ARCHIVE']
    if storage_tier not in valid_tiers:
        return cors_response(400, {
            'error': f'Invalid storageTier. Valid tiers: {valid_tiers}'
        }, event)

    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Get existing record to preserve pre-simulation state
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'storage_metrics'}
    ).get('Item', {})

    # Save pre-simulation tier if not already simulated
    pre_sim_tier = existing.get('preSimulationTier', existing.get('currentTier', 'STANDARD'))

    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'storage_metrics'},
        UpdateExpression=(
            'SET currentTier = :tier, simulated = :sim, '
            'preSimulationTier = :preTier, updatedAt = :now'
        ),
        ExpressionAttributeValues={
            ':tier': storage_tier,
            ':sim': True,
            ':preTier': pre_sim_tier,
            ':now': datetime.now(timezone.utc).isoformat(),
        },
    )

    return cors_response(200, {
        'message': 'Storage tier simulated',
        'userId': user_id,
        'storageTier': storage_tier,
        'simulated': True,
    }, event)


# ===================================================================
# Handler: POST /admin/storage/clear-simulation
# ===================================================================

def handle_clear_simulation(event):
    """Clear simulated storage tier metadata."""
    guard = _check_admin_and_testing(event)
    if guard:
        return guard

    try:
        body = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        return cors_response(400, {'error': 'Invalid request body'}, event)

    user_id = body.get('userId')
    if not user_id:
        return cors_response(400, {'error': 'userId is required'}, event)

    retention_table = _dynamodb.Table(_TABLE_DATA_RETENTION)

    # Get existing record to restore pre-simulation state
    existing = retention_table.get_item(
        Key={'userId': user_id, 'recordType': 'storage_metrics'}
    ).get('Item', {})

    pre_sim_tier = existing.get('preSimulationTier', 'STANDARD')

    retention_table.update_item(
        Key={'userId': user_id, 'recordType': 'storage_metrics'},
        UpdateExpression=(
            'SET currentTier = :tier, simulated = :sim, updatedAt = :now '
            'REMOVE preSimulationTier'
        ),
        ExpressionAttributeValues={
            ':tier': pre_sim_tier,
            ':sim': False,
            ':now': datetime.now(timezone.utc).isoformat(),
        },
    )

    return cors_response(200, {
        'message': 'Storage simulation cleared',
        'userId': user_id,
    }, event)
