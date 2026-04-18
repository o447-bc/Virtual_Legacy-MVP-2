"""
AdminSettings Lambda — System settings CRUD and Bedrock model listing.

Routes:
  GET  /admin/settings              — List all settings grouped by section
  PUT  /admin/settings/{settingKey} — Update a setting value with type validation
  GET  /admin/bedrock-models        — List Bedrock models with pricing info
"""
import os
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from cors import cors_headers
from responses import error_response
from admin_auth import verify_admin
from structured_logger import StructuredLog


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


TABLE_NAME = os.environ.get('TABLE_SYSTEM_SETTINGS', 'SystemSettingsDB')

# ---------------------------------------------------------------------------
# SSM path mapping — settings that must be synced back to SSM on save
# ---------------------------------------------------------------------------
SSM_PATH_MAP = {
    'CONVERSATION_BEDROCK_MODEL': '/virtuallegacy/conversation/llm-conversation-model',
    'CONVERSATION_SCORING_MODEL': '/virtuallegacy/conversation/llm-scoring-model',
    'SUMMARIZE_TRANSCRIPT_MODEL': '/life-story-app/llm-prompts/model-id',
    'MAX_CONVERSATION_TURNS': '/virtuallegacy/conversation/max-turns',
    'CONVERSATION_SCORE_GOAL': '/virtuallegacy/conversation/score-goal',
    'CONVERSATION_SYSTEM_PROMPT': '/virtuallegacy/conversation/system-prompt',
    'CONVERSATION_SCORING_PROMPT': '/virtuallegacy/conversation/scoring-prompt',
    'SUMMARIZE_TRANSCRIPT_PROMPT': '/life-story-app/llm-prompts/combined-prompt',
    'POLLY_VOICE_ID': '/virtuallegacy/conversation/polly-voice-id',
    'POLLY_ENGINE': '/virtuallegacy/conversation/polly-engine',
    'DORMANCY_THRESHOLD_1_DAYS': '/soulreel/data-retention/dormancy-threshold-1',
    'DORMANCY_THRESHOLD_2_DAYS': '/soulreel/data-retention/dormancy-threshold-2',
    'DORMANCY_THRESHOLD_3_DAYS': '/soulreel/data-retention/dormancy-threshold-3',
    'DELETION_GRACE_PERIOD_DAYS': '/soulreel/data-retention/deletion-grace-period',
    'LEGACY_PROTECTION_DORMANCY_DAYS': '/soulreel/data-retention/legacy-protection-dormancy-days',
    'LEGACY_PROTECTION_LAPSE_DAYS': '/soulreel/data-retention/legacy-protection-lapse-days',
    'GLACIER_TRANSITION_DAYS': '/soulreel/data-retention/glacier-transition-days',
    'GLACIER_NO_ACCESS_DAYS': '/soulreel/data-retention/glacier-no-access-days',
    'INTELLIGENT_TIERING_DAYS': '/soulreel/data-retention/intelligent-tiering-days',
    'EXPORT_RATE_LIMIT_DAYS': '/soulreel/data-retention/export-rate-limit-days',
    'EXPORT_LINK_EXPIRY_HOURS': '/soulreel/data-retention/export-link-expiry-hours',
    'DATA_RETENTION_TESTING_MODE': '/soulreel/data-retention/testing-mode',
    # Formerly hardcoded settings — now in SSM
    'PSYCH_PROFILE_BEDROCK_MODEL': '/soulreel/settings/psych-profile-bedrock-model',
    'BEDROCK_MAX_TOKENS': '/soulreel/settings/bedrock-max-tokens',
    'BEDROCK_TEMPERATURE': '/soulreel/settings/bedrock-temperature',
    'SUMMARIZE_MAX_TOKENS': '/soulreel/settings/summarize-max-tokens',
    'SUMMARIZE_TEMPERATURE': '/soulreel/settings/summarize-temperature',
    'ASSESSMENT_PROGRESS_TTL_DAYS': '/soulreel/settings/assessment-progress-ttl-days',
    'EXPORT_PRESIGNED_EXPIRY_SECONDS': '/soulreel/settings/export-presigned-expiry-seconds',
    'MAX_TRANSCRIPT_SIZE': '/soulreel/settings/max-transcript-size',
}

_ssm = boto3.client('ssm')

# ---------------------------------------------------------------------------
# Bedrock pricing lookup (static, maintained manually)
# ---------------------------------------------------------------------------
BEDROCK_PRICING = {
    'anthropic.claude-3-5-sonnet-20241022-v2:0': {'inputPricePerKToken': 0.003, 'outputPricePerKToken': 0.015},
    'anthropic.claude-3-5-sonnet-20240620-v1:0': {'inputPricePerKToken': 0.003, 'outputPricePerKToken': 0.015},
    'anthropic.claude-3-haiku-20240307-v1:0': {'inputPricePerKToken': 0.00025, 'outputPricePerKToken': 0.00125},
    'us.anthropic.claude-3-5-haiku-20241022-v1:0': {'inputPricePerKToken': 0.0008, 'outputPricePerKToken': 0.004},
    'anthropic.claude-3-sonnet-20240229-v1:0': {'inputPricePerKToken': 0.003, 'outputPricePerKToken': 0.015},
    'amazon.titan-text-express-v1': {'inputPricePerKToken': 0.0002, 'outputPricePerKToken': 0.0006},
    'amazon.titan-text-lite-v1': {'inputPricePerKToken': 0.00015, 'outputPricePerKToken': 0.0002},
    'meta.llama3-8b-instruct-v1:0': {'inputPricePerKToken': 0.0003, 'outputPricePerKToken': 0.0006},
    'meta.llama3-70b-instruct-v1:0': {'inputPricePerKToken': 0.00265, 'outputPricePerKToken': 0.0035},
    'mistral.mistral-7b-instruct-v0:2': {'inputPricePerKToken': 0.00015, 'outputPricePerKToken': 0.0002},
    'mistral.mixtral-8x7b-instruct-v0:1': {'inputPricePerKToken': 0.00045, 'outputPricePerKToken': 0.0007},
    'cohere.command-r-plus-v1:0': {'inputPricePerKToken': 0.003, 'outputPricePerKToken': 0.015},
    'cohere.command-r-v1:0': {'inputPricePerKToken': 0.0005, 'outputPricePerKToken': 0.0015},
    'ai21.jamba-instruct-v1:0': {'inputPricePerKToken': 0.0005, 'outputPricePerKToken': 0.0007},
}

# ---------------------------------------------------------------------------
# Bedrock model list cache (24-hour TTL)
# ---------------------------------------------------------------------------
_bedrock_cache = {
    'models': None,
    'fetched_at': 0,
}
_BEDROCK_CACHE_TTL = 86400  # 24 hours in seconds


def _get_known_model_ids():
    """Return the set of known Bedrock model IDs from the pricing dict."""
    return set(BEDROCK_PRICING.keys())


def lambda_handler(event, context):
    log = StructuredLog(event, context)
    log.info('AdminSettingsRequest', details={
        'httpMethod': event.get('httpMethod', ''),
        'resource': event.get('resource', ''),
    })

    # OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': ''
        }

    # Admin auth check
    admin = verify_admin(event)
    if not admin:
        return {
            'statusCode': 403,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Forbidden: admin access required'})
        }
    admin_email, admin_sub = admin

    method = event.get('httpMethod', '')
    resource = event.get('resource', '')

    try:
        if method == 'GET' and resource == '/admin/settings':
            return handle_get_settings(event)

        elif method == 'PUT' and '/admin/settings/' in resource:
            return handle_put_setting(event, admin_email, log)

        elif method == 'GET' and resource == '/admin/bedrock-models':
            return handle_get_bedrock_models(event)

        else:
            return {
                'statusCode': 400,
                'headers': cors_headers(event),
                'body': json.dumps({'error': f'Unsupported route: {method} {resource}'})
            }

    except ClientError as e:
        log.log_aws_error('DynamoDB', 'AdminSettings', e)
        return error_response(500, 'A server error occurred. Please try again.', e, event, log=log)
    except Exception as e:
        log.error('UnexpectedFailure', e)
        return error_response(500, 'An unexpected error occurred. Please try again.', e, event, log=log)


# ---------------------------------------------------------------------------
# GET /admin/settings — List all settings grouped by section
# ---------------------------------------------------------------------------
def handle_get_settings(event):
    """Scan SystemSettingsTable and return all settings grouped by section.
    
    For SSM-backed settings, reads the live value from SSM so the admin UI
    always shows what the app is actually using.
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    items = []
    response = table.scan()
    items.extend(response.get('Items', []))

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    # For SSM-backed settings, override the value with the live SSM value
    for item in items:
        ssm_path = SSM_PATH_MAP.get(item.get('settingKey'))
        if ssm_path:
            try:
                resp = _ssm.get_parameter(Name=ssm_path)
                item['value'] = resp['Parameter']['Value']
            except Exception:
                pass  # Keep DynamoDB value as fallback

    # Group by section
    grouped = {}
    for item in items:
        section = item.get('section', 'Other')
        if section not in grouped:
            grouped[section] = []
        grouped[section].append(item)

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'settings': grouped}, cls=DecimalEncoder)
    }


# ---------------------------------------------------------------------------
# PUT /admin/settings/{settingKey} — Update a setting value
# ---------------------------------------------------------------------------
def handle_put_setting(event, admin_email, log):
    """Validate type and update a setting in SystemSettingsTable."""
    setting_key = (event.get('pathParameters') or {}).get('settingKey')
    if not setting_key:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing settingKey in path'})
        }

    body = json.loads(event.get('body') or '{}')
    if 'value' not in body:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Missing required field: value'})
        }
    value = body['value']

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    # Check setting exists
    resp = table.get_item(Key={'settingKey': setting_key})
    existing = resp.get('Item')
    if not existing:
        return {
            'statusCode': 404,
            'headers': cors_headers(event),
            'body': json.dumps({'error': 'Setting not found'})
        }

    value_type = existing.get('valueType', 'string')

    # Validate value against valueType
    validation_error = _validate_value(value, value_type)
    if validation_error:
        return {
            'statusCode': 400,
            'headers': cors_headers(event),
            'body': json.dumps({'error': validation_error})
        }

    now = datetime.now(timezone.utc).isoformat()

    table.update_item(
        Key={'settingKey': setting_key},
        UpdateExpression='SET #val = :val, #ua = :ua, #ub = :ub',
        ExpressionAttributeNames={
            '#val': 'value',
            '#ua': 'updatedAt',
            '#ub': 'updatedBy',
        },
        ExpressionAttributeValues={
            ':val': str(value),
            ':ua': now,
            ':ub': admin_email,
        },
    )

    log.info('AdminSettingUpdated', details={'settingKey': setting_key, 'updatedBy': admin_email})

    # Sync to SSM if this setting has an SSM path
    ssm_path = SSM_PATH_MAP.get(setting_key)
    if ssm_path:
        try:
            _ssm.put_parameter(
                Name=ssm_path,
                Value=str(value),
                Type='String',
                Overwrite=True,
            )
            log.info('SettingSyncedToSSM', details={'settingKey': setting_key, 'ssmPath': ssm_path})
        except Exception as ssm_err:
            # Log but don't fail the request — DynamoDB is already updated
            log.warning('SSMSyncFailed', f'Failed to sync {setting_key} to SSM {ssm_path}: {ssm_err}',
                        details={'settingKey': setting_key, 'ssmPath': ssm_path})

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({
            'message': 'Setting updated',
            'updatedAt': now,
            'updatedBy': admin_email,
        })
    }


def _validate_value(value, value_type):
    """
    Validate a value against its valueType.
    Returns an error message string if invalid, or None if valid.
    """
    if value_type == 'integer':
        try:
            int(value)
        except (ValueError, TypeError):
            return f"Invalid value for integer type: '{value}' is not a valid integer"
        return None

    elif value_type == 'float':
        try:
            float(value)
        except (ValueError, TypeError):
            return f"Invalid value for float type: '{value}' is not a valid float"
        return None

    elif value_type == 'boolean':
        if value not in ('true', 'false'):
            return f"Invalid value for boolean type: '{value}' must be exactly 'true' or 'false'"
        return None

    elif value_type == 'string':
        if not value or not isinstance(value, str):
            return "Invalid value for string type: value cannot be empty"
        if '\n' in value or '\r' in value:
            return "Invalid value for string type: value must not contain newline characters"
        return None

    elif value_type == 'text':
        # Any string is valid for text
        return None

    elif value_type == 'model':
        if not value or not isinstance(value, str):
            return "Invalid value for model type: value cannot be empty"
        known_ids = _get_known_model_ids()
        if value not in known_ids:
            return f"Invalid value for model type: '{value}' is not a known Bedrock model ID"
        return None

    # Unknown valueType — accept by default
    return None


# ---------------------------------------------------------------------------
# GET /admin/bedrock-models — List Bedrock models with pricing
# ---------------------------------------------------------------------------
def handle_get_bedrock_models(event):
    """List available Bedrock foundation models with pricing info."""
    now = time.time()

    # Check cache
    if (_bedrock_cache['models'] is not None
            and now - _bedrock_cache['fetched_at'] < _BEDROCK_CACHE_TTL):
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps({'models': _bedrock_cache['models']})
        }

    try:
        bedrock_client = boto3.client('bedrock')
        response = bedrock_client.list_foundation_models()
    except Exception as e:
        return error_response(500, 'Failed to retrieve model list. Please try again.', e, event)

    model_summaries = response.get('modelSummaries', [])

    # Filter to ON_DEMAND models only
    on_demand_models = [
        m for m in model_summaries
        if 'ON_DEMAND' in m.get('inferenceTypesSupported', [])
    ]

    # Enrich with pricing and build response
    models = []
    for m in on_demand_models:
        model_id = m.get('modelId', '')
        pricing = BEDROCK_PRICING.get(model_id, {})
        models.append({
            'modelId': model_id,
            'modelName': m.get('modelName', ''),
            'providerName': m.get('providerName', ''),
            'inputPricePerKToken': pricing.get('inputPricePerKToken', None),
            'outputPricePerKToken': pricing.get('outputPricePerKToken', None),
        })

    # Sort by inputPricePerKToken descending; null-priced models sort to end
    models.sort(
        key=lambda x: (
            x['inputPricePerKToken'] is None,
            -(x['inputPricePerKToken'] or 0),
        )
    )

    # Update cache
    _bedrock_cache['models'] = models
    _bedrock_cache['fetched_at'] = now

    return {
        'statusCode': 200,
        'headers': cors_headers(event),
        'body': json.dumps({'models': models})
    }
