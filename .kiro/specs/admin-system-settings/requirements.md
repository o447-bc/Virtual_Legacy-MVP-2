# Requirements Document

## Introduction

The Admin System Settings feature replaces the current read-only settings display with a fully editable configuration management system. It introduces a DynamoDB-backed settings store, a CRUD API for admin users, a shared reader utility with caching for all Lambdas, a seed mechanism for initial values, and an interactive frontend settings page. This enables runtime configuration changes without redeploying the SAM stack.

## Glossary

- **Settings_Table**: The `SystemSettingsTable` DynamoDB table that stores all configurable system settings as key-value pairs with metadata (section, label, description, valueType, updatedAt, updatedBy).
- **Settings_API**: The Lambda function handling `GET /admin/settings` and `PUT /admin/settings/{settingKey}` endpoints, restricted to the SoulReelAdmins Cognito group.
- **Settings_Reader**: The shared Python utility (`get_setting()`) available to all Lambda functions via the shared layer, providing cached reads from the Settings_Table with fallback to environment variables and hardcoded defaults.
- **Settings_Page**: The React/TypeScript admin page at `/admin/settings` (`SystemSettings.tsx`) that renders grouped, editable settings with inline save.
- **Seed_Script**: An idempotent script or Lambda that populates the Settings_Table with initial setting values derived from environment variables and SSM parameters across the codebase.
- **Setting_Item**: A single record in the Settings_Table containing: `settingKey` (partition key), `value`, `valueType`, `section`, `label`, `description`, `updatedAt`, `updatedBy`.
- **Value_Type**: One of six supported types for a setting value: `string`, `integer`, `float`, `boolean`, `text`, `model`.
- **Model_Picker**: A dropdown control for settings with `valueType` "model" that lists available Bedrock foundation models with their display name and pricing, ordered from highest to lowest cost.
- **Admin_User**: A Cognito user belonging to the `SoulReelAdmins` group, verified via JWT claims by the `verify_admin()` shared utility.

## Requirements

### Requirement 1: DynamoDB Settings Table

**User Story:** As a platform operator, I want a dedicated DynamoDB table for system settings, so that configuration values persist independently of Lambda deployments.

#### Acceptance Criteria

1. THE Settings_Table SHALL use `settingKey` (String) as the partition key with no sort key.
2. THE Settings_Table SHALL use PAY_PER_REQUEST billing mode.
3. THE Settings_Table SHALL use KMS encryption via the existing `DataEncryptionKey` with SSEType KMS.
4. THE Settings_Table SHALL have Point-in-Time Recovery enabled.
5. WHEN the SAM template is deployed, THE Settings_Table SHALL be referenced as `TABLE_SYSTEM_SETTINGS` in the `Globals.Function.Environment.Variables` section.
6. THE Settings_Table SHALL store each setting with the attributes: `settingKey`, `value` (S), `valueType` (S), `section` (S), `label` (S), `description` (S), `updatedAt` (S), `updatedBy` (S).

### Requirement 2: Settings GET Endpoint

**User Story:** As an admin user, I want to retrieve all system settings grouped by section, so that I can view the current configuration state.

#### Acceptance Criteria

1. WHEN an authenticated Admin_User sends a GET request to `/admin/settings`, THE Settings_API SHALL return all Setting_Items from the Settings_Table grouped by `section`.
2. WHEN a non-admin user sends a GET request to `/admin/settings`, THE Settings_API SHALL return HTTP 403 with the message "Forbidden: admin access required".
3. WHEN the Settings_Table scan fails, THE Settings_API SHALL return HTTP 500 with a generic error message and log the full exception to CloudWatch.
4. THE Settings_API SHALL include CORS headers on all responses using the shared `cors_headers()` utility.
5. WHEN an OPTIONS preflight request is received, THE Settings_API SHALL return HTTP 200 with CORS headers.

### Requirement 3: Settings PUT Endpoint

**User Story:** As an admin user, I want to update individual setting values with type validation, so that I can change system behavior at runtime without redeploying.

#### Acceptance Criteria

1. WHEN an authenticated Admin_User sends a PUT request to `/admin/settings/{settingKey}` with a valid `value`, THE Settings_API SHALL update the Setting_Item in the Settings_Table with the new value, the current ISO 8601 timestamp as `updatedAt`, and the admin email as `updatedBy`.
2. WHEN the `settingKey` does not exist in the Settings_Table, THE Settings_API SHALL return HTTP 404 with the message "Setting not found".
3. WHEN the provided `value` does not match the Setting_Item `valueType`, THE Settings_API SHALL return HTTP 400 with a descriptive validation error message.
4. THE Settings_API SHALL validate `integer` values by confirming the value parses as a Python `int`.
5. THE Settings_API SHALL validate `float` values by confirming the value parses as a Python `float`.
6. THE Settings_API SHALL validate `boolean` values by confirming the value is exactly "true" or "false" (case-sensitive).
7. THE Settings_API SHALL validate `string` values by confirming the value is a non-empty single-line string (no newline characters).
8. THE Settings_API SHALL accept `text` values as any string including multiline content.
9. THE Settings_API SHALL validate `model` values by confirming the value is a non-empty string matching a known Bedrock foundation model ID.
10. WHEN a non-admin user sends a PUT request, THE Settings_API SHALL return HTTP 403.
11. THE Settings_API SHALL include CORS headers on all responses.

### Requirement 4: Settings API IAM and Template Configuration

**User Story:** As a platform operator, I want the Settings Lambda to have correct IAM permissions and API Gateway routing, so that the endpoints function without access errors.

#### Acceptance Criteria

1. THE Settings_API Lambda resource in `template.yml` SHALL have IAM policies granting `dynamodb:Scan`, `dynamodb:GetItem`, and `dynamodb:PutItem` on the Settings_Table.
2. THE Settings_API Lambda resource SHALL have IAM policies granting `kms:Decrypt`, `kms:DescribeKey`, and `kms:GenerateDataKey` on the DataEncryptionKey.
3. THE Settings_API Lambda resource SHALL use the shared layer for access to `cors`, `responses`, and `admin_auth` modules.
4. THE Settings_API Lambda resource SHALL define API Gateway events for `GET /admin/settings` and `PUT /admin/settings/{settingKey}` with CognitoAuthorizer auth.
5. THE Settings_API source file SHALL include `import os` at the top.

### Requirement 5: Settings Reader Utility

**User Story:** As a developer, I want a shared utility that reads settings from DynamoDB with caching and fallback, so that any Lambda can access runtime-configurable values without direct DynamoDB calls on every invocation.

#### Acceptance Criteria

1. THE Settings_Reader SHALL first check the Settings_Table for the requested `settingKey`.
2. WHEN the `settingKey` is not found in the Settings_Table, THE Settings_Reader SHALL fall back to `os.environ.get()` for the same key.
3. WHEN the `settingKey` is not found in the Settings_Table or environment variables, THE Settings_Reader SHALL return the provided `default` parameter value.
4. THE Settings_Reader SHALL cache retrieved settings in a module-level dictionary with a 5-minute TTL.
5. WHEN the cache TTL has expired for a setting, THE Settings_Reader SHALL re-fetch the value from the Settings_Table on the next call.
6. WHEN the DynamoDB read fails, THE Settings_Reader SHALL fall back to `os.environ.get()` and then to the provided default without raising an exception.
7. THE Settings_Reader SHALL be located at `SamLambda/functions/shared/python/settings.py` and accessible via the shared Lambda layer.

### Requirement 6: Seed Script

**User Story:** As a platform operator, I want an idempotent seed mechanism that populates the Settings_Table with initial values from the existing codebase, so that all known configurable values are available in the admin UI from day one.

#### Acceptance Criteria

1. THE Seed_Script SHALL populate the Settings_Table with initial Setting_Items for all configurable values listed in the sections below.
2. THE Seed_Script SHALL be idempotent: it SHALL use a conditional write (attribute_not_exists) so that existing Setting_Items are not overwritten.
3. THE Seed_Script SHALL assign each Setting_Item a `valueType` of `string`, `integer`, `float`, `boolean`, `text`, or `model` matching the expected data type.
4. THE Seed_Script SHALL assign each Setting_Item a human-readable `label` and `description`.

#### Section: AI & Models

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `PSYCH_PROFILE_BEDROCK_MODEL` | Psych Profile Bedrock Model | model | `anthropic.claude-3-haiku-20240307-v1:0` | `template.yml` Globals env var | `scorePsychTest` |
| `CONVERSATION_BEDROCK_MODEL` | Conversation Bedrock Model | model | `anthropic.claude-3-5-sonnet-20241022-v2:0` | SSM `/virtuallegacy/conversation/llm-conversation-model` | `wsDefault` (conversation) |
| `CONVERSATION_SCORING_MODEL` | Conversation Scoring Model | model | `anthropic.claude-3-haiku-20240307-v1:0` | SSM `/virtuallegacy/conversation/llm-scoring-model` | `wsDefault` (conversation) |
| `SUMMARIZE_TRANSCRIPT_MODEL` | Transcript Summarization Model | model | *(SSM `/life-story-app/llm-prompts/model-id`)* | SSM parameter | `summarizeTranscript` |
| `BEDROCK_MAX_TOKENS` | Max Tokens for AI Responses | integer | `1024` | hardcoded in `scorePsychTest` `bedrockConfig.maxTokens` | `scorePsychTest` |
| `BEDROCK_TEMPERATURE` | Temperature for AI Generation | float | `0.7` | hardcoded in `scorePsychTest` `bedrockConfig.temperature` | `scorePsychTest` |
| `SUMMARIZE_MAX_TOKENS` | Max Tokens for Transcript Summarization | integer | `2048` | hardcoded in `summarizeTranscript` | `summarizeTranscript` |
| `SUMMARIZE_TEMPERATURE` | Temperature for Transcript Summarization | float | `0.7` | hardcoded in `summarizeTranscript` | `summarizeTranscript` |

#### Section: Assessments

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `ASSESSMENT_RETAKE_COOLDOWN_DAYS` | Assessment Retake Cooldown (days) | integer | `30` | hardcoded `daysSince >= 30` in `PersonalInsights.tsx`; also shown in `SystemSettings.tsx` read-only display | `PersonalInsights.tsx` (frontend) |
| `ASSESSMENT_PROGRESS_TTL_DAYS` | In-Progress Assessment Expiry (days) | integer | `30` | hardcoded `_TTL_SECONDS = 2_592_000` (30 days) in `saveTestProgress/app.py` | `saveTestProgress` |
| `ASSESSMENT_AUTO_SAVE_INTERVAL_MS` | Auto-Save Interval (ms) | integer | `30000` | hardcoded `AUTO_SAVE_INTERVAL_MS = 30_000` in `TestTakingUI.tsx` | `TestTakingUI.tsx` (frontend) |
| `EXPORT_PRESIGNED_EXPIRY_SECONDS` | Test Export Download Link Expiry (seconds) | integer | `86400` | hardcoded `_PRESIGNED_EXPIRY = 86400` in `exportTestResults/app.py` | `exportTestResults` |

#### Section: Conversations

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `MAX_CONVERSATION_TURNS` | Max Conversation Turns | integer | `20` | SSM `/virtuallegacy/conversation/max-turns` | `wsDefault` |
| `CONVERSATION_SCORE_GOAL` | Conversation Score Goal | integer | `12` | SSM `/virtuallegacy/conversation/score-goal` | `wsDefault` |
| `CONVERSATION_SYSTEM_PROMPT` | Conversation System Prompt | text | *(stored in SSM `/virtuallegacy/conversation/system-prompt`)* | SSM parameter | `wsDefault` |
| `CONVERSATION_SCORING_PROMPT` | Conversation Scoring Prompt | text | *(stored in SSM `/virtuallegacy/conversation/scoring-prompt`)* | SSM parameter | `wsDefault` |
| `SUMMARIZE_TRANSCRIPT_PROMPT` | Transcript Summarization Prompt | text | *(stored in SSM `/life-story-app/llm-prompts/combined-prompt`)* | SSM parameter | `summarizeTranscript` |
| `ENFORCE_PERSONA_VALIDATION` | Enforce Persona Validation | boolean | `false` | `template.yml` Globals env var | all Lambdas (global) |
| `POLLY_VOICE_ID` | Polly Voice ID | string | `Joanna` | SSM `/virtuallegacy/conversation/polly-voice-id` | `wsDefault` |
| `POLLY_ENGINE` | Polly Engine | string | `neural` | SSM `/virtuallegacy/conversation/polly-engine` | `wsDefault` |

#### Section: Video & Media

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `MAX_VIDEO_DURATION_SECONDS` | Max Video Recording Duration (seconds) | integer | `120` | hardcoded `MAX_RECORDING_TIME = 120` in `VideoMemoryRecorder.tsx` | `VideoMemoryRecorder.tsx` (frontend) |
| `VIDEO_TRANSCRIPTION_ENABLED` | Auto-Transcribe Videos | boolean | `true` | per-user `allowTranscription` flag in `userStatusDB`; checked in `startTranscription/app.py` and `processVideo/app.py` | `startTranscription`, `processVideo` |
| `MAX_TRANSCRIPT_SIZE` | Max Transcript Size (bytes) | integer | `300000` | hardcoded `MAX_TRANSCRIPT_SIZE = 300000` in `processTranscript/app.py` | `processTranscript` |

#### Section: Engagement & Notifications

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `STREAK_RESET_HOUR_UTC` | Streak Reset Hour (UTC, 0-23) | integer | `0` | hardcoded via `cron(0 0 1 * ? *)` in `template.yml` MonthlyResetFunction schedule | `monthlyReset` (scheduled job) |
| `SENDER_EMAIL` | System Sender Email Address | string | `noreply@soulreel.net` | env var on multiple Lambdas | `stripeWebhook`, `accountDeletion`, `dataExport`, `winBack`, `checkInSender`, `manualRelease`, `acceptDeclineAssignment` |
| `FRONTEND_URL` | Frontend URL for Email Links | string | `https://www.soulreel.net` | env var `FRONTEND_URL` on billing/retention Lambdas | `billing`, `stripeWebhook`, `accountDeletion`, `dataExport`, `winBack` |
| `APP_BASE_URL` | Application Base URL | string | `https://www.soulreel.net` | `template.yml` Globals env var | `checkInSender`, `inactivityProcessor` |

#### Section: Data Retention

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `DORMANCY_THRESHOLD_1_DAYS` | Dormancy Threshold 1 — First Email (days) | integer | `180` | SSM `/soulreel/data-retention/dormancy-threshold-1`, fallback in `retention_config.py` | `dormantDetector` |
| `DORMANCY_THRESHOLD_2_DAYS` | Dormancy Threshold 2 — Second Email (days) | integer | `365` | SSM `/soulreel/data-retention/dormancy-threshold-2`, fallback in `retention_config.py` | `dormantDetector` |
| `DORMANCY_THRESHOLD_3_DAYS` | Dormancy Threshold 3 — Legacy Protection Flag (days) | integer | `730` | SSM `/soulreel/data-retention/dormancy-threshold-3`, fallback in `retention_config.py` | `dormantDetector`, `legacyProtection` |
| `DELETION_GRACE_PERIOD_DAYS` | Account Deletion Grace Period (days) | integer | `30` | SSM `/soulreel/data-retention/deletion-grace-period`, fallback in `retention_config.py` | `accountDeletion` |
| `LEGACY_PROTECTION_DORMANCY_DAYS` | Legacy Protection Dormancy Threshold (days) | integer | `730` | SSM `/soulreel/data-retention/legacy-protection-dormancy-days`, fallback in `retention_config.py` | `legacyProtection` |
| `LEGACY_PROTECTION_LAPSE_DAYS` | Legacy Protection Subscription Lapse (days) | integer | `365` | SSM `/soulreel/data-retention/legacy-protection-lapse-days`, fallback in `retention_config.py` | `dormantDetector`, `legacyProtection` |
| `GLACIER_TRANSITION_DAYS` | S3 Glacier Transition (days) | integer | `365` | SSM `/soulreel/data-retention/glacier-transition-days`, fallback in `retention_config.py` | `storageLifecycle` |
| `GLACIER_NO_ACCESS_DAYS` | Glacier No-Access Threshold (days) | integer | `180` | SSM `/soulreel/data-retention/glacier-no-access-days`, fallback in `retention_config.py` | `storageLifecycle` |
| `INTELLIGENT_TIERING_DAYS` | S3 Intelligent-Tiering Transition (days) | integer | `30` | SSM `/soulreel/data-retention/intelligent-tiering-days`, fallback in `retention_config.py` | `storageLifecycle` |
| `EXPORT_RATE_LIMIT_DAYS` | Data Export Rate Limit (days between exports) | integer | `30` | SSM `/soulreel/data-retention/export-rate-limit-days`, fallback in `retention_config.py` | `dataExport` |
| `EXPORT_LINK_EXPIRY_HOURS` | Data Export Download Link Expiry (hours) | integer | `72` | SSM `/soulreel/data-retention/export-link-expiry-hours`, fallback in `retention_config.py` | `dataExport` |
| `DATA_RETENTION_TESTING_MODE` | Data Retention Testing Mode | string | `disabled` | SSM `/soulreel/data-retention/testing-mode`, fallback in `retention_config.py` | `adminLifecycle`, all retention Lambdas |

#### Section: Security

| settingKey | label | valueType | default | source | used by |
|---|---|---|---|---|---|
| `ALLOWED_ORIGIN` | CORS Allowed Origin | string | `https://www.soulreel.net` | `template.yml` Globals env var | all Lambdas (CORS headers) |
| `SESSION_TIMEOUT_MINUTES` | Session Timeout (minutes) | integer | `60` | Cognito token expiry; no explicit code reference — managed by Cognito config | frontend session management |

### Requirement 7: Frontend Settings Page — Data Fetching and Display

**User Story:** As an admin user, I want to see all system settings organized by section with their current values, so that I can understand the current system configuration at a glance.

#### Acceptance Criteria

1. WHEN the Settings_Page loads, THE Settings_Page SHALL fetch all settings via `GET /admin/settings` using an authenticated request (fetchAuthSession).
2. THE Settings_Page SHALL group settings by `section` and render each section with a collapsible header.
3. THE Settings_Page SHALL display each setting with its `label`, `description`, current `value` in an appropriate input control, and "last updated by {updatedBy} at {updatedAt}" metadata.
4. WHEN the API request fails, THE Settings_Page SHALL display an error toast notification.
5. WHILE settings are loading, THE Settings_Page SHALL display a loading indicator.

### Requirement 8: Frontend Settings Page — Input Controls by Value Type

**User Story:** As an admin user, I want each setting to use an input control appropriate to its data type, so that I can edit values intuitively and avoid type errors.

#### Acceptance Criteria

1. WHEN a setting has `valueType` "integer", THE Settings_Page SHALL render an `<input type="number" step="1">` control.
2. WHEN a setting has `valueType` "float", THE Settings_Page SHALL render an `<input type="number" step="0.01">` control.
3. WHEN a setting has `valueType` "boolean", THE Settings_Page SHALL render a toggle switch control.
4. WHEN a setting has `valueType` "string", THE Settings_Page SHALL render an `<input type="text">` control.
5. WHEN a setting has `valueType` "text", THE Settings_Page SHALL render a `<textarea>` control for multiline content.
6. WHEN a setting has `valueType` "model", THE Settings_Page SHALL render a Model_Picker dropdown control.

### Requirement 9: Frontend Settings Page — Inline Save and Validation

**User Story:** As an admin user, I want to save individual settings inline with client-side validation, so that I get immediate feedback on invalid values and can update settings one at a time.

#### Acceptance Criteria

1. WHEN a setting value is modified from its original value, THE Settings_Page SHALL display a save icon button next to the input.
2. WHEN the admin clicks the save icon, THE Settings_Page SHALL send a PUT request to `/admin/settings/{settingKey}` with the new value.
3. WHEN the PUT request succeeds, THE Settings_Page SHALL display a success toast and update the displayed `updatedAt` and `updatedBy` metadata.
4. WHEN the PUT request fails, THE Settings_Page SHALL display an error toast with the error message from the API.
5. WHEN an integer setting value does not parse as a whole number, THE Settings_Page SHALL display a red border on the input and an inline error message before sending the request.
6. WHEN a float setting value does not parse as a number, THE Settings_Page SHALL display a red border on the input and an inline error message before sending the request.
7. WHEN a string setting value is empty, THE Settings_Page SHALL display a red border on the input and an inline error message before sending the request.

### Requirement 10: Lambda Migration to Settings Reader

**User Story:** As a developer, I want key Lambda functions to read configurable values via the Settings_Reader utility, so that admin-changed settings take effect at runtime without redeployment.

#### Acceptance Criteria

1. THE `scorePsychTest` Lambda SHALL read `PSYCH_PROFILE_BEDROCK_MODEL` via the Settings_Reader `get_setting()` function instead of direct `os.environ.get()`.
2. THE `saveTestProgress` Lambda SHALL read the progress TTL value via the Settings_Reader `get_setting()` function instead of a hardcoded constant.
3. THE `dormantDetector` Lambda SHALL read dormancy threshold values via the Settings_Reader `get_setting()` function instead of the existing `retention_config.get_config()` for the thresholds that are now in the Settings_Table.
4. WHEN the Settings_Table does not contain a requested setting, THE migrated Lambdas SHALL continue to function using the Settings_Reader fallback chain (environment variable, then hardcoded default).

### Requirement 11: Bedrock Models List Endpoint

**User Story:** As an admin user, I want to see all available Bedrock foundation models with their pricing when selecting an AI model, so that I can make informed cost/capability decisions when switching models.

#### Acceptance Criteria

1. WHEN an authenticated Admin_User sends a GET request to `/admin/bedrock-models`, THE Settings_API SHALL call the Bedrock `ListFoundationModels` API to retrieve all available models in the current AWS region.
2. THE Settings_API SHALL filter the results to only include models with `ON_DEMAND` inference type support.
3. THE Settings_API SHALL return each model with at minimum: `modelId`, `modelName`, `providerName`, and `inputPricePerKToken` and `outputPricePerKToken` (from a maintained pricing lookup).
4. THE Settings_API SHALL order the returned models from highest cost to lowest cost (by input price per 1K tokens).
5. THE Settings_API SHALL cache the Bedrock model list for 24 hours to avoid repeated API calls.
6. THE Settings_API Lambda resource SHALL have IAM policies granting `bedrock:ListFoundationModels` in the current region.
7. WHEN the Bedrock API call fails, THE Settings_API SHALL return HTTP 500 with a generic error message and log the full exception.
8. THE Settings_API SHALL include CORS headers on the response.

### Requirement 12: Frontend Model Picker Control

**User Story:** As an admin user, I want a dropdown selector for AI model settings that shows model names with pricing, so that I can quickly compare costs and switch to newer or cheaper models as they become available.

#### Acceptance Criteria

1. WHEN the Settings_Page renders a setting with `valueType` "model", THE Settings_Page SHALL fetch the available models via `GET /admin/bedrock-models` and render a `<select>` dropdown.
2. THE dropdown SHALL display each option as "{providerName} — {modelName} (${inputPricePerKToken}/1K input, ${outputPricePerKToken}/1K output)".
3. THE dropdown options SHALL be ordered from highest cost to lowest cost, matching the API response order.
4. THE dropdown SHALL pre-select the option matching the current setting value (modelId).
5. WHEN the current setting value does not match any model in the dropdown, THE Settings_Page SHALL display the current value as a text label with a warning indicator that the model may no longer be available.
6. THE Settings_Page SHALL cache the bedrock models list for the duration of the page session to avoid redundant API calls when multiple model settings are displayed.

### Requirement 13: Settings Precedence and Consistency

**User Story:** As a platform operator, I want a clear precedence order for configuration values, so that DynamoDB settings override environment variables and the system behaves predictably.

#### Acceptance Criteria

1. THE Settings_Reader SHALL apply the following precedence order: Settings_Table value (highest), then `os.environ` value, then hardcoded default (lowest).
2. THE Seed_Script SHALL preserve existing Setting_Items in the Settings_Table and only insert new ones, ensuring manual admin changes are not overwritten on re-seeding.
3. THE Settings_API SHALL validate the SAM template with `sam validate --lint` without errors after all template changes are applied.
