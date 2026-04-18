# Admin System Settings — Editable Configuration Management

**Date**: April 12–18, 2026
**Feature**: Admin System Settings (`admin-system-settings`)
**Spec**: `.kiro/specs/admin-system-settings/`

---

## Goal

Replace the read-only System Settings page in the admin console (`/admin/settings`) with a fully editable configuration management system. Enable runtime changes to system configuration without redeploying the SAM stack.

## Problem Statement

All system configuration was scattered across three sources with no unified admin interface:
- **Environment variables** in `template.yml` — baked in at deploy time, require `sam deploy` to change
- **SSM Parameter Store** — runtime-configurable but only via AWS Console or CLI
- **Hardcoded constants** in Lambda source code — require code changes and redeploy

The admin console had a read-only settings page showing 4 placeholder values. No way for admins to change any configuration at runtime.

---

## Architecture Decisions

### Storage Strategy (Revised Mid-Implementation)

**Initial approach**: New DynamoDB `SystemSettingsTable` as the single source of truth for all settings, with a `get_setting()` shared utility providing a fallback chain (DynamoDB → env var → default).

**Problem discovered during testing**: Settings saved to DynamoDB weren't reflected in the app because consuming Lambdas still read from SSM or env vars. The DynamoDB table was a parallel store that nothing actually read from.

**Final approach** (after user feedback):
- **30 settings backed by SSM** — admin UI reads live SSM values on GET, writes to both DynamoDB (metadata/audit) and SSM (runtime value) on PUT. Consuming Lambdas read from SSM as before.
- **3 frontend-only settings** — stay in DynamoDB only (retake cooldown, auto-save interval, video duration). Frontend reads via the settings API.
- **8 read-only settings** — env vars that require redeploy (CORS origin, sender email, etc.). Shown in admin UI but not editable.

### SSM Path Mapping

Every editable setting has a defined SSM path. The admin Lambda's PUT handler writes to SSM after updating DynamoDB. The GET handler reads live SSM values to ensure the admin UI always shows what the app is actually using.

```
SSM_PATH_MAP = {
    'CONVERSATION_BEDROCK_MODEL': '/virtuallegacy/conversation/llm-conversation-model',
    'CONVERSATION_SCORE_GOAL': '/virtuallegacy/conversation/score-goal',
    'DORMANCY_THRESHOLD_1_DAYS': '/soulreel/data-retention/dormancy-threshold-1',
    'PSYCH_PROFILE_BEDROCK_MODEL': '/soulreel/settings/psych-profile-bedrock-model',
    ... (30 total)
}
```

---

## What Was Built

### Backend

1. **SystemSettingsTable** (DynamoDB) — PAY_PER_REQUEST, KMS encryption, PITR enabled. Stores metadata: settingKey, value, valueType, section, label, description, updatedAt, updatedBy.

2. **AdminSettings Lambda** (`SamLambda/functions/adminFunctions/adminSettings/app.py`)
   - `GET /admin/settings` — scans DynamoDB for metadata, overrides values with live SSM reads for SSM-backed settings, groups by section
   - `PUT /admin/settings/{settingKey}` — validates type, updates DynamoDB, syncs to SSM if SSM-backed
   - `GET /admin/bedrock-models` — calls `ListFoundationModels`, filters to ON_DEMAND, enriches with static pricing map, sorts by cost descending, 24h cache

3. **Settings Reader** (`SamLambda/functions/shared/python/settings.py`) — shared utility with 5-min TTL cache and fallback chain. Used by migrated Lambdas.

4. **Seed Script** (`SamLambda/functions/adminFunctions/adminSettings/seed.py`) — CLI script populating 41 settings across 7 sections. Idempotent via `attribute_not_exists` condition. Reads SSM for initial values.

5. **Lambda Migrations** — Updated `scorePsychTest`, `saveTestProgress`, `exportTestResults`, `summarizeTranscript`, `processTranscript` to read from SSM instead of hardcoded values. Reverted `dormantDetector` to use `retention_config.get_config()` (already SSM-backed).

6. **8 New SSM Parameters** created under `/soulreel/settings/*` for formerly-hardcoded values.

### Frontend

1. **SystemSettings.tsx** — complete rewrite of the admin settings page:
   - Collapsible sections (default collapsed) with setting count badges
   - Type-aware input controls: number inputs (integer/float), text inputs, toggle switches (boolean), textareas (text/prompts), Select dropdowns (model picker, Polly voice, Polly engine)
   - Fixed "Save Changes" bar at top with pending change count, Save and Discard buttons
   - Client-side validation with red borders and inline error messages
   - Toast notifications for success/error
   - "Last updated by {email} at {timestamp}" metadata per setting
   - Click-to-expand pattern for long text/prompt fields
   - Model picker dropdown showing "{provider} — {model} ($X/1K in, $Y/1K out)" ordered by cost

2. **Service Functions** added to `adminService.ts`: `fetchSettings()`, `updateSetting()`, `fetchBedrockModels()`

3. **API Endpoints** added to `api.ts`: `ADMIN_SETTINGS`, `ADMIN_BEDROCK_MODELS`

### Testing

- **33 backend property tests** (pytest + hypothesis) covering: fallback chain precedence, cache TTL, error resilience, type validation, CORS headers, section grouping, PUT metadata, seed idempotency, seed completeness, Bedrock filtering/sorting/fields
- **18 frontend property tests** (vitest + fast-check) covering: validation logic, save visibility, numeric rejection, model picker format, model pre-selection

---

## Settings Inventory (41 total)

### AI & Models (8)
PSYCH_PROFILE_BEDROCK_MODEL, CONVERSATION_BEDROCK_MODEL, CONVERSATION_SCORING_MODEL, SUMMARIZE_TRANSCRIPT_MODEL, BEDROCK_MAX_TOKENS, BEDROCK_TEMPERATURE, SUMMARIZE_MAX_TOKENS, SUMMARIZE_TEMPERATURE

### Assessments (4)
ASSESSMENT_RETAKE_COOLDOWN_DAYS, ASSESSMENT_PROGRESS_TTL_DAYS, ASSESSMENT_AUTO_SAVE_INTERVAL_MS, EXPORT_PRESIGNED_EXPIRY_SECONDS

### Conversations (8)
MAX_CONVERSATION_TURNS, CONVERSATION_SCORE_GOAL, CONVERSATION_SYSTEM_PROMPT, CONVERSATION_SCORING_PROMPT, SUMMARIZE_TRANSCRIPT_PROMPT, ENFORCE_PERSONA_VALIDATION, POLLY_VOICE_ID, POLLY_ENGINE

### Video & Media (3)
MAX_VIDEO_DURATION_SECONDS, VIDEO_TRANSCRIPTION_ENABLED, MAX_TRANSCRIPT_SIZE

### Engagement & Notifications (4)
STREAK_RESET_HOUR_UTC, SENDER_EMAIL, FRONTEND_URL, APP_BASE_URL

### Data Retention (12)
DORMANCY_THRESHOLD_1_DAYS, DORMANCY_THRESHOLD_2_DAYS, DORMANCY_THRESHOLD_3_DAYS, DELETION_GRACE_PERIOD_DAYS, LEGACY_PROTECTION_DORMANCY_DAYS, LEGACY_PROTECTION_LAPSE_DAYS, GLACIER_TRANSITION_DAYS, GLACIER_NO_ACCESS_DAYS, INTELLIGENT_TIERING_DAYS, EXPORT_RATE_LIMIT_DAYS, EXPORT_LINK_EXPIRY_HOURS, DATA_RETENTION_TESTING_MODE

### Security (2)
ALLOWED_ORIGIN, SESSION_TIMEOUT_MINUTES

---

## IAM Permissions Added

| Lambda | New Permissions |
|--------|----------------|
| AdminSettingsFunction | dynamodb:Scan/GetItem/PutItem/UpdateItem on SystemSettingsTable, kms:Decrypt/DescribeKey/GenerateDataKey, bedrock:ListFoundationModels, ssm:GetParameter/GetParameters/PutParameter on /virtuallegacy/*, /soulreel/*, /life-story-app/* |
| ScorePsychTestFunction | ssm:GetParameter on /soulreel/settings/* |
| SaveTestProgressFunction | ssm:GetParameter on /soulreel/settings/* |
| ExportTestResultsFunction | ssm:GetParameter on /soulreel/settings/* |
| SummarizeTranscriptFunction | ssm:GetParameter on /soulreel/settings/* |
| ProcessTranscriptFunction | ssm:GetParameter on /soulreel/settings/* |

---

## Bugs Fixed During Implementation

1. **Bedrock ListFoundationModels IAM** — resource ARN was `foundation-model/*`, needs `*` (service-level action)
2. **DynamoDB UpdateItem IAM** — PUT handler uses `update_item()` but policy only had `PutItem`
3. **Survey dismiss persistence** — `surveyDismissed` state reset on navigation. Fixed with `sessionStorage`, cleared on logout
4. **ProtectedRoute redirect loop** — redirected to dashboard on every navigation when survey not completed. Added `sessionStorage` check
5. **ESLint empty catch block** — `catch {}` fails `no-empty` rule. Added comment
6. **Missing files in git** — `toastError.ts` and `errorReporter.ts` created locally but not committed. Caused build failures in CI
7. **Sticky bar positioning** — `sticky top-0` doesn't work inside `overflow-auto` containers. Changed to `fixed` with sidebar offset

---

## Known Limitations

- **Cold start caching**: All Lambdas cache SSM values at cold start. Changes take effect on next cold start (~15 min idle or next deploy). This is a pre-existing pattern across the codebase.
- **Bedrock pricing**: Static lookup map in Lambda code. Needs manual update when AWS changes pricing.
- **Frontend-only settings** (retake cooldown, auto-save interval, video duration): Currently in DynamoDB but the frontend components still use hardcoded values. A future task should update those components to fetch from the settings API.
- **Read-only settings** (CORS origin, sender email, etc.): Shown in admin UI but changes require template.yml update + redeploy.

---

## Files Changed

### New Files
- `SamLambda/functions/adminFunctions/adminSettings/app.py`
- `SamLambda/functions/adminFunctions/adminSettings/seed.py`
- `SamLambda/functions/shared/python/settings.py`
- `SamLambda/tests/property/test_admin_settings.py`
- `FrontEndCode/src/__tests__/admin-settings.property.test.ts`
- `FrontEndCode/src/utils/toastError.ts`
- `FrontEndCode/src/services/errorReporter.ts`
- `.kiro/specs/admin-system-settings/` (requirements.md, design.md, tasks.md, .config.kiro)

### Modified Files
- `SamLambda/template.yml` — SystemSettingsTable, AdminSettingsFunction, IAM policies for 5 Lambdas
- `SamLambda/functions/psychTestFunctions/scorePsychTest/app.py` — SSM read for model ID
- `SamLambda/functions/psychTestFunctions/saveTestProgress/app.py` — SSM read for TTL
- `SamLambda/functions/psychTestFunctions/exportTestResults/app.py` — SSM read for presigned expiry
- `SamLambda/functions/videoFunctions/summarizeTranscript/app.py` — SSM read for max_tokens/temperature
- `SamLambda/functions/videoFunctions/processTranscript/app.py` — SSM read for MAX_TRANSCRIPT_SIZE
- `SamLambda/functions/dataRetentionFunctions/dormantDetector/app.py` — reverted to retention_config
- `FrontEndCode/src/pages/admin/SystemSettings.tsx` — complete rewrite
- `FrontEndCode/src/services/adminService.ts` — settings types and service functions
- `FrontEndCode/src/config/api.ts` — settings and bedrock-models endpoints
- `FrontEndCode/src/pages/Dashboard.tsx` — survey dismiss sessionStorage
- `FrontEndCode/src/components/ProtectedRoute.tsx` — survey dismiss check
- `FrontEndCode/src/contexts/AuthContext.tsx` — clear sessionStorage on logout
