# Admin System Settings — Editable Configuration Management

## Context

This is a Soul Reel application built with AWS SAM (Python Lambdas), DynamoDB, S3, API Gateway with Cognito auth, and a React/TypeScript frontend. The admin console is at `/admin` and requires the `SoulReelAdmins` Cognito group.

Currently, all system configuration lives in environment variables defined in `SamLambda/template.yml` under `Globals.Function.Environment.Variables`. These get baked into Lambda at deploy time and are overwritten on every `sam deploy`. There is no way to change settings at runtime without redeploying.

The admin console already has a "System > Settings" page at `/admin/settings` (`FrontEndCode/src/pages/admin/SystemSettings.tsx`) that currently shows settings as read-only text. This needs to become a fully editable settings management system.

## What to Build

### 1. DynamoDB Settings Table

Create a `SystemSettingsTable` in `SamLambda/template.yml`:
- Partition key: `settingKey` (S)
- No sort key needed
- PAY_PER_REQUEST billing, KMS encryption via `DataEncryptionKey`, PITR enabled
- Each item stores: `settingKey`, `value` (S), `valueType` (S: "string" | "integer" | "float" | "boolean" | "text"), `section` (S), `label` (S), `description` (S), `updatedAt` (S), `updatedBy` (S)

Add `TABLE_SYSTEM_SETTINGS: !Ref SystemSettingsTable` to the Globals environment variables.

### 2. Settings CRUD Lambda

Create `SamLambda/functions/adminFunctions/systemSettings/app.py`:
- `GET /admin/settings` — returns all settings grouped by section
- `PUT /admin/settings/{settingKey}` — updates a single setting value with validation
- Both require admin auth (SoulReelAdmins group)
- Validate value against `valueType` before saving:
  - `integer`: must parse as int
  - `float`: must parse as float
  - `boolean`: must be "true" or "false"
  - `string`: any non-empty string, single line
  - `text`: any string, can be multiline (for prompts)
- Return 400 with clear error if validation fails
- Include CORS headers, `import os`, follow existing Lambda patterns

Add the Lambda to `template.yml` with IAM policies for `dynamodb:Scan`, `dynamodb:GetItem`, `dynamodb:PutItem` on SystemSettingsTable, plus KMS.

### 3. Settings Reader Utility

Create a shared utility at `SamLambda/functions/shared/python/settings.py`:
```python
def get_setting(setting_key, default=None):
    """Read a setting from SystemSettings DynamoDB table.
    Falls back to os.environ, then to the provided default.
    Caches settings for 5 minutes to reduce DynamoDB reads."""
```

This utility should be used by ALL Lambdas that need configurable values. The pattern is:
1. Check DynamoDB SystemSettings table first
2. If not found, fall back to `os.environ.get()`
3. If not found, use the hardcoded default
4. Cache results in a module-level dict with TTL

### 4. Seed the Settings Table

Create a seed script or Lambda that populates the SystemSettings table with initial values. Do a thorough sweep of `SamLambda/template.yml` to find ALL environment variables and configurable values. Organize them into these sections:

**AI & Models**
- `PSYCH_PROFILE_BEDROCK_MODEL` — AI model for assessment narratives (string, default: `anthropic.claude-3-haiku-20240307-v1:0`)
- `CONVERSATION_BEDROCK_MODEL` — AI model for conversations (string, check WebSocketDefaultFunction for current value)
- `BEDROCK_MAX_TOKENS` — Max tokens for AI responses (integer)
- `BEDROCK_TEMPERATURE` — Temperature for AI generation (float, 0-1)

**Assessments**
- `ASSESSMENT_RETAKE_COOLDOWN_DAYS` — Days before retake allowed (integer, default: 30)
- `ASSESSMENT_PROGRESS_TTL_DAYS` — Days before in-progress saves expire (integer, default: 30)
- `ASSESSMENT_AUTO_SAVE_INTERVAL_MS` — Auto-save interval in milliseconds (integer, default: 30000)

**Conversations**
- `MAX_CONVERSATION_TURNS` — Max turns per conversation (integer, check wsDefault Lambda)
- `CONVERSATION_SYSTEM_PROMPT` — System prompt for conversation AI (text, check wsDefault Lambda)
- `ENFORCE_PERSONA_VALIDATION` — Whether to enforce persona validation (boolean)

**Video & Media**
- `MAX_VIDEO_DURATION_SECONDS` — Max video recording length (integer)
- `VIDEO_TRANSCRIPTION_ENABLED` — Whether to auto-transcribe videos (boolean)

**Engagement & Notifications**
- `STREAK_RESET_HOUR_UTC` — Hour (UTC) when streaks reset (integer)
- `INACTIVITY_THRESHOLD_DAYS` — Days before inactivity notification (integer)
- `DORMANT_THRESHOLD_DAYS` — Days before account is considered dormant (integer)

**Data Retention**
- `DATA_RETENTION_DAYS` — Default data retention period (integer)
- `GLACIER_TRANSITION_DAYS` — Days before S3 objects move to Glacier (integer)
- `ACCOUNT_DELETION_GRACE_DAYS` — Grace period before permanent deletion (integer)

**Security**
- `ALLOWED_ORIGIN` — CORS allowed origin (string, default: `https://www.soulreel.net`)
- `SESSION_TIMEOUT_MINUTES` — Session timeout (integer)

**NOTE**: Do a thorough scan of ALL Lambda files and the template.yml to find every `os.environ.get()` call and every environment variable. The list above is a starting point — there will be more. Include ALL of them.

### 5. Update the Frontend Settings Page

Replace the current read-only `SystemSettings.tsx` with a fully editable form:

- Fetch all settings via `GET /admin/settings`
- Group settings by `section` with collapsible section headers
- Each setting shows: label, description, current value in an appropriate input
- Input types based on `valueType`:
  - `integer` → `<input type="number" step="1">` with integer validation
  - `float` → `<input type="number" step="0.01">` with float validation
  - `boolean` → toggle switch
  - `string` → `<input type="text">`
  - `text` → `<textarea>` (for prompts, multi-line)
- Inline save: each setting has a small save icon that appears when the value changes
- On save, call `PUT /admin/settings/{settingKey}` with the new value
- Show success/error toast
- Show "last updated by {email} at {timestamp}" under each setting
- Validate before sending: show red border and error text if type doesn't match

### 6. Migrate Existing Lambdas

Update the key Lambdas to use the new `get_setting()` utility instead of direct `os.environ.get()` for the settings that are now in the table. Start with:
- `scorePsychTest/app.py` — read `PSYCH_PROFILE_BEDROCK_MODEL` from settings
- `saveTestProgress/app.py` — read TTL from settings
- `dormantDetector/app.py` — read threshold from settings

Don't migrate ALL Lambdas at once — just the ones with the most impactful settings. The `get_setting()` utility falls back to env vars, so unmigrated Lambdas still work.

## Important Constraints

- Settings in DynamoDB take precedence over env vars in template.yml
- The `get_setting()` utility must cache to avoid DynamoDB reads on every Lambda invocation
- The seed script should be idempotent — don't overwrite existing values
- All Lambda files must have `import os` at the top
- CORS headers on all responses
- SAM template must validate with `sam validate --lint`
- Follow existing patterns: Card components, toast notifications, fetchAuthSession for auth
- The settings page should feel like a proper admin panel — clean, organized, professional

## Steering Rules

- Lambda IAM permissions must be updated in template.yml when adding new AWS API calls
- CORS headers must be consistent across SAM template and Lambda responses
- GitHub Actions CI/CD deploys on push to master (backend.yml for SamLambda/**, frontend.yml for FrontEndCode/**)
- The W3660 cfn-lint warning is suppressed via `.cfnlintrc` — don't remove it

## Approach

Build requirements from this prompt. Be meticulous. Before each step, critique your approach, update as needed, then code. After implementation, do a holistic review.
