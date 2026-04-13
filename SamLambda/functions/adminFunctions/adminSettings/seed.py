"""
Seed script for SystemSettingsTable.

Standalone CLI script — run with: python seed.py

Populates the SystemSettingsTable with ALL settings from the requirements
tables. Uses conditional writes for idempotency: existing items are never
overwritten.

Usage:
    python seed.py                          # uses TABLE_SYSTEM_SETTINGS env var
    TABLE_SYSTEM_SETTINGS=MyTable python seed.py
"""
import os
import json
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# SSM helper
# ---------------------------------------------------------------------------
_ssm = boto3.client('ssm')


def _read_ssm(path: str, fallback: str) -> str:
    """Attempt to read an SSM parameter; return *fallback* on any error."""
    try:
        resp = _ssm.get_parameter(Name=path)
        return resp['Parameter']['Value']
    except Exception:
        return fallback


# ---------------------------------------------------------------------------
# Seed settings definitions
# ---------------------------------------------------------------------------

SEED_SETTINGS = [
    # ── AI & Models ──────────────────────────────────────────────────────
    {
        'settingKey': 'PSYCH_PROFILE_BEDROCK_MODEL',
        'value': 'anthropic.claude-3-haiku-20240307-v1:0',
        'valueType': 'model',
        'section': 'AI & Models',
        'label': 'Psych Profile Bedrock Model',
        'description': 'AI model used for psychological assessment narrative generation.',
        'ssm_path': '/soulreel/settings/psych-profile-bedrock-model',
    },
    {
        'settingKey': 'CONVERSATION_BEDROCK_MODEL',
        'value': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        'valueType': 'model',
        'section': 'AI & Models',
        'label': 'Conversation Bedrock Model',
        'description': 'AI model used for interactive conversation sessions.',
        'ssm_path': '/virtuallegacy/conversation/llm-conversation-model',
    },
    {
        'settingKey': 'CONVERSATION_SCORING_MODEL',
        'value': 'anthropic.claude-3-haiku-20240307-v1:0',
        'valueType': 'model',
        'section': 'AI & Models',
        'label': 'Conversation Scoring Model',
        'description': 'AI model used for scoring conversation quality.',
        'ssm_path': '/virtuallegacy/conversation/llm-scoring-model',
    },
    {
        'settingKey': 'SUMMARIZE_TRANSCRIPT_MODEL',
        'value': 'anthropic.claude-3-haiku-20240307-v1:0',
        'valueType': 'model',
        'section': 'AI & Models',
        'label': 'Transcript Summarization Model',
        'description': 'AI model used for summarizing video transcripts.',
        'ssm_path': '/life-story-app/llm-prompts/model-id',
    },
    {
        'settingKey': 'BEDROCK_MAX_TOKENS',
        'value': '1024',
        'valueType': 'integer',
        'section': 'AI & Models',
        'label': 'Max Tokens for AI Responses',
        'description': 'Maximum number of tokens the AI model can generate per response.',
        'ssm_path': '/soulreel/settings/bedrock-max-tokens',
    },
    {
        'settingKey': 'BEDROCK_TEMPERATURE',
        'value': '0.7',
        'valueType': 'float',
        'section': 'AI & Models',
        'label': 'Temperature for AI Generation',
        'description': 'Controls randomness in AI responses. Lower values are more deterministic.',
        'ssm_path': '/soulreel/settings/bedrock-temperature',
    },
    {
        'settingKey': 'SUMMARIZE_MAX_TOKENS',
        'value': '2048',
        'valueType': 'integer',
        'section': 'AI & Models',
        'label': 'Max Tokens for Transcript Summarization',
        'description': 'Maximum number of tokens for transcript summarization output.',
        'ssm_path': '/soulreel/settings/summarize-max-tokens',
    },
    {
        'settingKey': 'SUMMARIZE_TEMPERATURE',
        'value': '0.7',
        'valueType': 'float',
        'section': 'AI & Models',
        'label': 'Temperature for Transcript Summarization',
        'description': 'Controls randomness in transcript summarization output.',
        'ssm_path': '/soulreel/settings/summarize-temperature',
    },

    # ── Assessments ──────────────────────────────────────────────────────
    {
        'settingKey': 'ASSESSMENT_RETAKE_COOLDOWN_DAYS',
        'value': '30',
        'valueType': 'integer',
        'section': 'Assessments',
        'label': 'Assessment Retake Cooldown (days)',
        'description': 'Number of days a user must wait before retaking an assessment.',
    },
    {
        'settingKey': 'ASSESSMENT_PROGRESS_TTL_DAYS',
        'value': '30',
        'valueType': 'integer',
        'section': 'Assessments',
        'label': 'In-Progress Assessment Expiry (days)',
        'description': 'Number of days before an in-progress assessment expires.',
        'ssm_path': '/soulreel/settings/assessment-progress-ttl-days',
    },
    {
        'settingKey': 'ASSESSMENT_AUTO_SAVE_INTERVAL_MS',
        'value': '30000',
        'valueType': 'integer',
        'section': 'Assessments',
        'label': 'Auto-Save Interval (ms)',
        'description': 'Interval in milliseconds between automatic saves of assessment progress.',
    },
    {
        'settingKey': 'EXPORT_PRESIGNED_EXPIRY_SECONDS',
        'value': '86400',
        'valueType': 'integer',
        'section': 'Assessments',
        'label': 'Test Export Download Link Expiry (seconds)',
        'description': 'How long a presigned URL for test export downloads remains valid.',
        'ssm_path': '/soulreel/settings/export-presigned-expiry-seconds',
    },

    # ── Conversations ────────────────────────────────────────────────────
    {
        'settingKey': 'MAX_CONVERSATION_TURNS',
        'value': '20',
        'valueType': 'integer',
        'section': 'Conversations',
        'label': 'Max Conversation Turns',
        'description': 'Maximum number of back-and-forth turns allowed in a conversation.',
        'ssm_path': '/virtuallegacy/conversation/max-turns',
    },
    {
        'settingKey': 'CONVERSATION_SCORE_GOAL',
        'value': '12',
        'valueType': 'integer',
        'section': 'Conversations',
        'label': 'Conversation Score Goal',
        'description': 'Target score for a conversation to be considered complete.',
        'ssm_path': '/virtuallegacy/conversation/score-goal',
    },
    {
        'settingKey': 'CONVERSATION_SYSTEM_PROMPT',
        'value': '',
        'valueType': 'text',
        'section': 'Conversations',
        'label': 'Conversation System Prompt',
        'description': 'System prompt used to guide the AI during conversations.',
        'ssm_path': '/virtuallegacy/conversation/system-prompt',
    },
    {
        'settingKey': 'CONVERSATION_SCORING_PROMPT',
        'value': '',
        'valueType': 'text',
        'section': 'Conversations',
        'label': 'Conversation Scoring Prompt',
        'description': 'Prompt used by the AI to score conversation quality.',
        'ssm_path': '/virtuallegacy/conversation/scoring-prompt',
    },
    {
        'settingKey': 'SUMMARIZE_TRANSCRIPT_PROMPT',
        'value': '',
        'valueType': 'text',
        'section': 'Conversations',
        'label': 'Transcript Summarization Prompt',
        'description': 'Prompt used by the AI to summarize video transcripts.',
        'ssm_path': '/life-story-app/llm-prompts/combined-prompt',
    },
    {
        'settingKey': 'ENFORCE_PERSONA_VALIDATION',
        'value': 'false',
        'valueType': 'boolean',
        'section': 'Conversations',
        'label': 'Enforce Persona Validation',
        'description': 'Whether to enforce persona validation checks globally.',
    },
    {
        'settingKey': 'POLLY_VOICE_ID',
        'value': 'Joanna',
        'valueType': 'string',
        'section': 'Conversations',
        'label': 'Polly Voice ID',
        'description': 'Amazon Polly voice used for text-to-speech in conversations.',
        'ssm_path': '/virtuallegacy/conversation/polly-voice-id',
    },
    {
        'settingKey': 'POLLY_ENGINE',
        'value': 'neural',
        'valueType': 'string',
        'section': 'Conversations',
        'label': 'Polly Engine',
        'description': 'Amazon Polly engine type (standard or neural) for text-to-speech.',
        'ssm_path': '/virtuallegacy/conversation/polly-engine',
    },

    # ── Video & Media ────────────────────────────────────────────────────
    {
        'settingKey': 'MAX_VIDEO_DURATION_SECONDS',
        'value': '120',
        'valueType': 'integer',
        'section': 'Video & Media',
        'label': 'Max Video Recording Duration (seconds)',
        'description': 'Maximum allowed duration for a single video recording.',
    },
    {
        'settingKey': 'VIDEO_TRANSCRIPTION_ENABLED',
        'value': 'true',
        'valueType': 'boolean',
        'section': 'Video & Media',
        'label': 'Auto-Transcribe Videos',
        'description': 'Whether uploaded videos are automatically transcribed.',
    },
    {
        'settingKey': 'MAX_TRANSCRIPT_SIZE',
        'value': '300000',
        'valueType': 'integer',
        'section': 'Video & Media',
        'label': 'Max Transcript Size (bytes)',
        'description': 'Maximum allowed size in bytes for a video transcript.',
        'ssm_path': '/soulreel/settings/max-transcript-size',
    },

    # ── Engagement & Notifications ───────────────────────────────────────
    {
        'settingKey': 'STREAK_RESET_HOUR_UTC',
        'value': '0',
        'valueType': 'integer',
        'section': 'Engagement & Notifications',
        'label': 'Streak Reset Hour (UTC, 0-23)',
        'description': 'Hour of the day (UTC) when user streaks are evaluated and reset.',
    },
    {
        'settingKey': 'SENDER_EMAIL',
        'value': 'noreply@soulreel.net',
        'valueType': 'string',
        'section': 'Engagement & Notifications',
        'label': 'System Sender Email Address',
        'description': 'Email address used as the sender for all system-generated emails.',
    },
    {
        'settingKey': 'FRONTEND_URL',
        'value': 'https://www.soulreel.net',
        'valueType': 'string',
        'section': 'Engagement & Notifications',
        'label': 'Frontend URL for Email Links',
        'description': 'Base URL used in email links that direct users to the frontend.',
    },
    {
        'settingKey': 'APP_BASE_URL',
        'value': 'https://www.soulreel.net',
        'valueType': 'string',
        'section': 'Engagement & Notifications',
        'label': 'Application Base URL',
        'description': 'Base URL of the application used for generating links.',
    },

    # ── Data Retention ───────────────────────────────────────────────────
    {
        'settingKey': 'DORMANCY_THRESHOLD_1_DAYS',
        'value': '180',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Dormancy Threshold 1 — First Email (days)',
        'description': 'Days of inactivity before the first dormancy warning email is sent.',
        'ssm_path': '/soulreel/data-retention/dormancy-threshold-1',
    },
    {
        'settingKey': 'DORMANCY_THRESHOLD_2_DAYS',
        'value': '365',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Dormancy Threshold 2 — Second Email (days)',
        'description': 'Days of inactivity before the second dormancy warning email is sent.',
        'ssm_path': '/soulreel/data-retention/dormancy-threshold-2',
    },
    {
        'settingKey': 'DORMANCY_THRESHOLD_3_DAYS',
        'value': '730',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Dormancy Threshold 3 — Legacy Protection Flag (days)',
        'description': 'Days of inactivity before the legacy protection flag is applied.',
        'ssm_path': '/soulreel/data-retention/dormancy-threshold-3',
    },
    {
        'settingKey': 'DELETION_GRACE_PERIOD_DAYS',
        'value': '30',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Account Deletion Grace Period (days)',
        'description': 'Days after deletion request before account data is permanently removed.',
        'ssm_path': '/soulreel/data-retention/deletion-grace-period',
    },
    {
        'settingKey': 'LEGACY_PROTECTION_DORMANCY_DAYS',
        'value': '730',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Legacy Protection Dormancy Threshold (days)',
        'description': 'Days of inactivity before legacy protection eligibility is evaluated.',
        'ssm_path': '/soulreel/data-retention/legacy-protection-dormancy-days',
    },
    {
        'settingKey': 'LEGACY_PROTECTION_LAPSE_DAYS',
        'value': '365',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Legacy Protection Subscription Lapse (days)',
        'description': 'Days after subscription lapse before legacy protection is revoked.',
        'ssm_path': '/soulreel/data-retention/legacy-protection-lapse-days',
    },
    {
        'settingKey': 'GLACIER_TRANSITION_DAYS',
        'value': '365',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'S3 Glacier Transition (days)',
        'description': 'Days before objects are transitioned to S3 Glacier storage.',
        'ssm_path': '/soulreel/data-retention/glacier-transition-days',
    },
    {
        'settingKey': 'GLACIER_NO_ACCESS_DAYS',
        'value': '180',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Glacier No-Access Threshold (days)',
        'description': 'Days without access before Glacier objects are flagged for review.',
        'ssm_path': '/soulreel/data-retention/glacier-no-access-days',
    },
    {
        'settingKey': 'INTELLIGENT_TIERING_DAYS',
        'value': '30',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'S3 Intelligent-Tiering Transition (days)',
        'description': 'Days before objects are moved to S3 Intelligent-Tiering.',
        'ssm_path': '/soulreel/data-retention/intelligent-tiering-days',
    },
    {
        'settingKey': 'EXPORT_RATE_LIMIT_DAYS',
        'value': '30',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Data Export Rate Limit (days between exports)',
        'description': 'Minimum number of days a user must wait between data exports.',
        'ssm_path': '/soulreel/data-retention/export-rate-limit-days',
    },
    {
        'settingKey': 'EXPORT_LINK_EXPIRY_HOURS',
        'value': '72',
        'valueType': 'integer',
        'section': 'Data Retention',
        'label': 'Data Export Download Link Expiry (hours)',
        'description': 'Hours before a data export download link expires.',
        'ssm_path': '/soulreel/data-retention/export-link-expiry-hours',
    },
    {
        'settingKey': 'DATA_RETENTION_TESTING_MODE',
        'value': 'disabled',
        'valueType': 'string',
        'section': 'Data Retention',
        'label': 'Data Retention Testing Mode',
        'description': 'Enable testing mode for data retention workflows (enabled/disabled).',
        'ssm_path': '/soulreel/data-retention/testing-mode',
    },

    # ── Security ─────────────────────────────────────────────────────────
    {
        'settingKey': 'ALLOWED_ORIGIN',
        'value': 'https://www.soulreel.net',
        'valueType': 'string',
        'section': 'Security',
        'label': 'CORS Allowed Origin',
        'description': 'Origin allowed for cross-origin requests (CORS).',
    },
    {
        'settingKey': 'SESSION_TIMEOUT_MINUTES',
        'value': '60',
        'valueType': 'integer',
        'section': 'Security',
        'label': 'Session Timeout (minutes)',
        'description': 'Minutes of inactivity before a user session expires.',
    },
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def run_seed(table_name: str | None = None):
    """
    Populate SystemSettingsTable with all seed settings.

    For SSM-sourced settings, attempts to read the current SSM value and uses
    it as the initial value. Falls back to the hardcoded default on any error.

    Uses conditional writes so existing items are never overwritten.
    """
    table_name = table_name or os.environ.get(
        'TABLE_SYSTEM_SETTINGS', 'SystemSettingsDB'
    )
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    now = datetime.now(timezone.utc).isoformat()

    seeded = 0
    skipped = 0

    for setting in SEED_SETTINGS:
        # Resolve value — try SSM if an ssm_path is defined
        value = setting['value']
        ssm_path = setting.get('ssm_path')
        if ssm_path:
            value = _read_ssm(ssm_path, value)

        item = {
            'settingKey': setting['settingKey'],
            'value': str(value),
            'valueType': setting['valueType'],
            'section': setting['section'],
            'label': setting['label'],
            'description': setting['description'],
            'updatedAt': now,
            'updatedBy': 'seed-script',
        }

        try:
            table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(settingKey)',
            )
            print(f"Seeded: {setting['settingKey']}")
            seeded += 1
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Skipped (exists): {setting['settingKey']}")
                skipped += 1
            else:
                raise

    print(f"\nDone. Seeded: {seeded}, Skipped: {skipped}, Total: {seeded + skipped}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    run_seed()
