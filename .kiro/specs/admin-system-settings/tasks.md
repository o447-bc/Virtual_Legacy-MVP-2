# Implementation Plan: Admin System Settings

## Overview

Replace the read-only SystemSettings page with a fully editable, DynamoDB-backed configuration management system. Implementation proceeds bottom-up: DynamoDB table and SAM config → shared settings reader → admin Lambda API → seed script → frontend service layer → frontend UI → Lambda migration to use the settings reader.

## Tasks

- [x] 1. Create SystemSettingsTable and update SAM template globals
  - [x] 1.1 Add SystemSettingsTable DynamoDB resource to `SamLambda/template.yml`
    - Partition key: `settingKey` (S), no sort key
    - PAY_PER_REQUEST billing
    - KMS encryption via `DataEncryptionKey` with SSEType KMS
    - Point-in-Time Recovery enabled
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 1.2 Add `TABLE_SYSTEM_SETTINGS` to `Globals.Function.Environment.Variables` referencing the new table
    - _Requirements: 1.5_

- [x] 2. Implement Settings Reader shared utility
  - [x] 2.1 Create `SamLambda/functions/shared/python/settings.py`
    - Implement `get_setting(key, default)` with fallback chain: module-level cache (5-min TTL) → DynamoDB `SystemSettingsTable` → `os.environ.get(key)` → provided default
    - Must include `import os` at the top
    - Never raise exceptions — log and fall back silently on DynamoDB errors
    - Do not cache fallback values (so next call retries DynamoDB)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 13.1_
  - [x]* 2.2 Write property test: Settings Reader fallback chain precedence
    - **Property 2: Settings Reader fallback chain precedence**
    - **Validates: Requirements 5.1, 5.2, 5.3, 10.4, 13.1**
  - [x]* 2.3 Write property test: Settings Reader cache TTL behavior
    - **Property 3: Settings Reader cache TTL behavior**
    - **Validates: Requirements 5.4, 5.5**
  - [x]* 2.4 Write property test: Settings Reader error resilience
    - **Property 4: Settings Reader error resilience**
    - **Validates: Requirements 5.6**

- [x] 3. Checkpoint — Ensure settings reader tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement AdminSettings Lambda with GET, PUT, and Bedrock models endpoints
  - [x] 4.1 Create `SamLambda/functions/adminFunctions/adminSettings/app.py`
    - Follow `adminQuestions/app.py` pattern: OPTIONS preflight, `verify_admin()`, method/resource routing, `try/except` with `error_response()`
    - Must include `import os` at the top
    - Implement `handle_get_settings`: scan `SystemSettingsTable`, group items by `section`, return JSON
    - Implement `handle_put_setting`: validate `settingKey` exists (404 if not), validate `value` against `valueType` (400 if invalid), update item with `updatedAt` (ISO 8601) and `updatedBy` (admin email)
    - Type validation: `integer` → parseable as `int`; `float` → parseable as `float`; `boolean` → exactly `"true"` or `"false"`; `string` → non-empty, no newlines; `text` → any string; `model` → non-empty, in known model ID set
    - Implement `handle_get_bedrock_models`: module-level 24h cache, call `bedrock.list_foundation_models()`, filter to `ON_DEMAND`, enrich with static `BEDROCK_PRICING` dict, sort by `inputPricePerKToken` descending, null-priced models sort to end
    - All responses must include CORS headers via `cors_headers(event)`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 4.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.7, 11.8_
  - [x] 4.2 Add AdminSettingsFunction resource to `SamLambda/template.yml`
    - SharedUtilsLayer, arm64, CognitoAuthorizer
    - IAM policies: `dynamodb:Scan`, `dynamodb:GetItem`, `dynamodb:PutItem` on SystemSettingsTable; `kms:Decrypt`, `kms:DescribeKey`, `kms:GenerateDataKey` on DataEncryptionKey; `bedrock:ListFoundationModels` (region-scoped)
    - API events: GET `/admin/settings`, PUT `/admin/settings/{settingKey}`, GET `/admin/bedrock-models`, plus OPTIONS events for all three paths
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 11.6_
  - [x] 4.3 Write property test: Type validation accepts valid values and rejects invalid values
    - **Property 1: Type validation accepts valid values and rejects invalid values**
    - **Validates: Requirements 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
  - [x] 4.4 Write property test: CORS headers on all API responses
    - **Property 5: CORS headers on all API responses**
    - **Validates: Requirements 2.4, 3.11, 11.8**
  - [x] 4.5 Write property test: GET settings groups items by section
    - **Property 6: GET settings groups items by section**
    - **Validates: Requirements 2.1**
  - [x] 4.6 Write property test: PUT setting updates metadata correctly
    - **Property 7: PUT setting updates metadata correctly**
    - **Validates: Requirements 3.1**
  - [x] 4.7 Write property test: Bedrock models filtered to ON_DEMAND only
    - **Property 13: Bedrock models filtered to ON_DEMAND only**
    - **Validates: Requirements 11.2**
  - [x] 4.8 Write property test: Bedrock models sorted by cost descending
    - **Property 14: Bedrock models sorted by cost descending**
    - **Validates: Requirements 11.4**
  - [x] 4.9 Write property test: Bedrock model response contains required fields
    - **Property 15: Bedrock model response contains required fields**
    - **Validates: Requirements 11.3**

- [x] 5. Checkpoint — Ensure backend tests pass and SAM template validates
  - Ensure all tests pass, run `sam validate --lint` from `SamLambda/`, ask the user if questions arise.

- [x] 6. Implement seed script
  - [x] 6.1 Create `SamLambda/functions/adminFunctions/adminSettings/seed.py`
    - Standalone CLI script (not a Lambda)
    - Populate SystemSettingsTable with all settings from requirements tables (AI & Models, Assessments, Conversations, Video & Media, Engagement & Notifications, Data Retention, Security)
    - Use `put_item` with `ConditionExpression='attribute_not_exists(settingKey)'` for idempotency
    - Each item must have all required attributes: `settingKey`, `value`, `valueType`, `section`, `label`, `description`, `updatedAt`, `updatedBy` (set to `"seed-script"`)
    - For SSM-sourced values, attempt SSM read and fall back to hardcoded default
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 1.6_
  - [x] 6.2 Write property test: Seed script idempotency
    - **Property 8: Seed script idempotency**
    - **Validates: Requirements 6.2, 13.2**
  - [x] 6.3 Write property test: Seed item completeness
    - **Property 9: Seed item completeness**
    - **Validates: Requirements 1.6, 6.3, 6.4**

- [x] 7. Checkpoint — Ensure seed script tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Add frontend API endpoints and service functions
  - [x] 8.1 Add settings and bedrock-models endpoints to `FrontEndCode/src/config/api.ts`
    - Add `ADMIN_SETTINGS: '/admin/settings'` and `ADMIN_BEDROCK_MODELS: '/admin/bedrock-models'` to `API_CONFIG.ENDPOINTS`
    - _Requirements: 7.1, 11.1_
  - [x] 8.2 Add settings types and service functions to `FrontEndCode/src/services/adminService.ts`
    - Add `SettingItem`, `SettingsResponse`, `UpdateSettingResponse`, `BedrockModel` interfaces
    - Add `fetchSettings()`, `updateSetting(settingKey, value)`, `fetchBedrockModels()` functions
    - Use existing `getAuthHeaders()` helper and `buildApiUrl()` pattern
    - _Requirements: 7.1, 9.2, 12.1_

- [x] 9. Implement SystemSettings page
  - [x] 9.1 Rewrite `FrontEndCode/src/pages/admin/SystemSettings.tsx`
    - Replace read-only display with fully editable settings page
    - Fetch settings on mount via `fetchSettings()` with `fetchAuthSession` for auth
    - Group settings by section with collapsible headers (Collapsible from shadcn/ui)
    - Display each setting with label, description, type-appropriate input control, and "last updated by {updatedBy} at {updatedAt}" metadata
    - Loading skeleton while fetching; error toast on fetch failure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x] 9.2 Implement type-aware input controls
    - `integer` → `<input type="number" step="1">`
    - `float` → `<input type="number" step="0.01">`
    - `boolean` → toggle switch (Switch component)
    - `string` → `<input type="text">`
    - `text` → `<textarea>`
    - `model` → `<select>` dropdown (Model Picker)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  - [x] 9.3 Implement inline save with client-side validation
    - Show save icon (Save from lucide-react) when value differs from original
    - On save click, send PUT to `/admin/settings/{settingKey}`
    - Success toast ("Setting updated") + update displayed metadata
    - Error toast with API error message on failure
    - Client-side validation: integer must be whole number, float must be valid number, string must be non-empty — red border + inline error message
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  - [x] 9.4 Implement Model Picker dropdown
    - Fetch Bedrock models via `fetchBedrockModels()` once on mount (cached for session)
    - Display format: "{providerName} — {modelName} (${inputPricePerKToken}/1K input, ${outputPricePerKToken}/1K output)"
    - Options ordered highest cost to lowest cost
    - Pre-select option matching current setting value
    - If current value not in list, show value as text with warning indicator (AlertTriangle icon)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  - [x] 9.5 Write property test: Input control type matches valueType
    - **Property 10: Input control type matches valueType**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**
  - [x] 9.6 Write property test: Save icon visibility on value change
    - **Property 11: Save icon visibility on value change**
    - **Validates: Requirements 9.1**
  - [x] 9.7 Write property test: Client-side validation rejects invalid numeric inputs
    - **Property 12: Client-side validation rejects invalid numeric inputs**
    - **Validates: Requirements 9.5, 9.6**
  - [x] 9.8 Write property test: Model picker display format
    - **Property 16: Model picker display format**
    - **Validates: Requirements 12.2**
  - [x] 9.9 Write property test: Model picker pre-selects current value
    - **Property 17: Model picker pre-selects current value**
    - **Validates: Requirements 12.4**

- [x] 10. Checkpoint — Ensure frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Migrate key Lambdas to use Settings Reader
  - [x] 11.1 Update `scorePsychTest` Lambda to read `PSYCH_PROFILE_BEDROCK_MODEL` via `get_setting()` instead of `os.environ.get()`
    - Import `from settings import get_setting`
    - Replace `os.environ.get('PSYCH_PROFILE_BEDROCK_MODEL', ...)` with `get_setting('PSYCH_PROFILE_BEDROCK_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')`
    - _Requirements: 10.1, 10.4_
  - [x] 11.2 Update `saveTestProgress` Lambda to read progress TTL via `get_setting()` instead of hardcoded constant
    - Import `from settings import get_setting`
    - Replace hardcoded `_TTL_SECONDS = 2_592_000` with `int(get_setting('ASSESSMENT_PROGRESS_TTL_DAYS', '30')) * 86400`
    - _Requirements: 10.2, 10.4_
  - [x] 11.3 Update `dormantDetector` Lambda to read dormancy thresholds via `get_setting()` for settings now in the Settings_Table
    - Import `from settings import get_setting`
    - Replace `retention_config.get_config('dormancy-threshold-1')` etc. with `int(get_setting('DORMANCY_THRESHOLD_1_DAYS', '180'))` for the thresholds that are now in the Settings_Table
    - _Requirements: 10.3, 10.4_

- [x] 12. Final checkpoint — Ensure all tests pass and SAM template validates
  - Ensure all tests pass, run `sam validate --lint` from `SamLambda/`, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Backend property tests go in `SamLambda/tests/property/test_admin_settings.py` using pytest + hypothesis
- Frontend property tests go in `FrontEndCode/src/__tests__/admin-settings.property.test.ts` using vitest + fast-check
- All Lambda files must have `import os` at the top per CORS rules
- IAM permissions must be updated in `template.yml` whenever new AWS API calls are added
- The W3660 cfn-lint warning is suppressed via `.cfnlintrc` — do not remove it
