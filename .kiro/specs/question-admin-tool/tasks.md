# Implementation Plan: Question Management Admin Tool

## Overview

Incremental implementation of the admin tool for managing the SoulReel question bank. Backend uses Python 3.12 Lambdas behind the existing API Gateway with Cognito auth. Frontend uses React/TypeScript with shadcn/ui under the `/admin` route. Each task builds on the previous, starting with shared infrastructure and ending with integration wiring.

## Tasks

- [x] 1. Shared infrastructure: Canonical Life Event Registry and admin auth helper
  - [x] 1.1 Create the TypeScript Canonical Life Event Registry constant file
    - Create `FrontEndCode/src/constants/lifeEventRegistry.ts` with the full `LIFE_EVENT_REGISTRY` array, `ALL_LIFE_EVENT_KEYS`, `INSTANCEABLE_KEYS`, `VALID_PLACEHOLDERS`, and `INSTANCEABLE_KEY_TO_PLACEHOLDER` exports as specified in the design
    - Include all 42 Life_Event_Keys organized by category with `LifeEventKeyInfo` interface
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 Create the Python Canonical Life Event Registry in the SharedUtilsLayer
    - Create `SamLambda/functions/shared/python/life_event_registry.py` with `LIFE_EVENT_KEYS`, `INSTANCEABLE_KEYS`, `VALID_PLACEHOLDERS`, `INSTANCEABLE_KEY_TO_PLACEHOLDER`, and `validate_life_event_keys()` function
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.3 Create the admin auth helper in the SharedUtilsLayer
    - Create `SamLambda/functions/shared/python/admin_auth.py` with `verify_admin(event)` function that extracts `cognito:groups` from `requestContext.authorizer.claims` and verifies `SoulReelAdmins` membership, returning `(email, sub)` tuple or `None`
    - _Requirements: 2.4, 2.5, 2.6_

  - [ ]* 1.4 Write property test for life event key validation (Python)
    - **Property 5: Life event key validation rejects invalid keys**
    - **Validates: Requirements 4.10, 5.2, 6.7**

  - [ ]* 1.5 Write property test for life event key validation (TypeScript)
    - **Property 5: Life event key validation rejects invalid keys**
    - **Validates: Requirements 4.10, 5.2, 6.7**

- [x] 2. SAM template: Admin Lambda definitions and API Gateway events
  - [x] 2.1 Add AdminQuestions Lambda to SAM template
    - Define `AdminQuestionsFunction` in `SamLambda/template.yml` with `CodeUri: functions/adminFunctions/adminQuestions/`, `Handler: app.lambda_handler`, `Runtime: python3.12`, `Architectures: [arm64]`, SharedUtilsLayer
    - Add API events: `GET /admin/questions`, `POST /admin/questions`, `PUT /admin/questions/{questionId}`, `POST /admin/questions/batch` — all with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan`, `dynamodb:Query`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:GetItem`, `dynamodb:BatchWriteItem` on allQuestionDB; KMS decrypt on DataEncryptionKey
    - _Requirements: 12.1, 12.4, 12.8, 12.9, 12.10, 12.11_

  - [x] 2.2 Add AdminSimulate Lambda to SAM template
    - Define `AdminSimulateFunction` with `CodeUri: functions/adminFunctions/adminSimulate/`, SharedUtilsLayer
    - Add API event: `POST /admin/simulate` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan` on allQuestionDB; KMS decrypt
    - _Requirements: 12.2, 12.4_

  - [x] 2.3 Add AdminCoverage Lambda to SAM template
    - Define `AdminCoverageFunction` with `CodeUri: functions/adminFunctions/adminCoverage/`, SharedUtilsLayer
    - Add API event: `GET /admin/coverage` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan` on allQuestionDB; KMS decrypt
    - _Requirements: 12.5, 12.4_

  - [x] 2.4 Add AdminThemes Lambda to SAM template
    - Define `AdminThemesFunction` with `CodeUri: functions/adminFunctions/adminThemes/`, SharedUtilsLayer
    - Add API event: `PUT /admin/themes/{questionType}` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan`, `dynamodb:UpdateItem`, `dynamodb:BatchWriteItem` on allQuestionDB; KMS decrypt
    - _Requirements: 12.6, 12.4_

  - [x] 2.5 Add AdminStats Lambda to SAM template
    - Define `AdminStatsFunction` with `CodeUri: functions/adminFunctions/adminStats/`, SharedUtilsLayer
    - Add API event: `GET /admin/stats` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan` on allQuestionDB; KMS decrypt
    - _Requirements: 12.7, 12.4_

  - [x] 2.6 Add AdminExport Lambda to SAM template
    - Define `AdminExportFunction` with `CodeUri: functions/adminFunctions/adminExport/`, SharedUtilsLayer
    - Add API event: `GET /admin/export` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan` on allQuestionDB; KMS decrypt
    - _Requirements: 12.12, 12.4_

  - [x] 2.7 Add AdminMigrate Lambda to SAM template
    - Define `AdminMigrateFunction` with `CodeUri: functions/adminFunctions/adminMigrate/`, SharedUtilsLayer
    - Add API event: `POST /admin/migrate` with CognitoAuthorizer
    - Add IAM policies: `dynamodb:Scan`, `dynamodb:UpdateItem`, `dynamodb:BatchWriteItem` on allQuestionDB; KMS decrypt
    - _Requirements: 12.3, 12.4_

- [x] 3. Checkpoint — Validate SAM template
  - Ensure `sam validate --lint` passes from `SamLambda/`. Ensure all tests pass, ask the user if questions arise.

- [x] 4. Backend: AdminQuestions Lambda (CRUD + batch)
  - [x] 4.1 Implement AdminQuestions Lambda handler with GET (list all questions)
    - Create `SamLambda/functions/adminFunctions/adminQuestions/app.py`
    - Route `GET /admin/questions`: scan allQuestionDB, return all questions with `DecimalEncoder`
    - Include `import os`, `cors_headers(event)` on all responses, OPTIONS handling, `verify_admin()` check returning 403 if not admin
    - Handle missing new attributes gracefully (default `requiredLifeEvents` to `[]`, `isInstanceable` to `false`, `instancePlaceholder` to `""`)
    - _Requirements: 3.7, 3.8, 13.1, 13.2, 13.3, 13.4, 13.5, 14.1_

  - [x] 4.2 Add POST route to AdminQuestions Lambda (create single question)
    - Route `POST /admin/questions`: validate required fields (`Question`, `questionType`), validate `requiredLifeEvents` against registry, auto-generate `questionId` using `{type}-{00000}` format, set `Valid=1`, `lastModifiedBy`, `lastModifiedAt`, write to DynamoDB
    - Return 400 for missing fields or invalid life event keys
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 10.2_

  - [x] 4.3 Add PUT route to AdminQuestions Lambda (update question)
    - Route `PUT /admin/questions/{questionId}`: validate `requiredLifeEvents` against registry, update item in DynamoDB, set `lastModifiedBy` and `lastModifiedAt`
    - Return 400 for invalid life event keys, 404 if question not found
    - _Requirements: 4.7, 4.8, 4.9, 4.10, 7.5, 10.2_

  - [x] 4.4 Add POST batch route to AdminQuestions Lambda (batch import)
    - Route `POST /admin/questions/batch`: validate all questions (non-empty text, valid life event keys), reject entire batch on any failure (atomic), scan for max questionId prefix, generate sequential IDs, use `BatchWriteItem` with 25-item chunks
    - _Requirements: 8.6, 8.7, 8.8, 8.9, 8.10, 10.2_

  - [ ]* 4.5 Write property test for non-admin rejection (Python)
    - **Property 1: Non-admin requests are rejected**
    - **Validates: Requirements 2.4, 2.5**

  - [ ]* 4.6 Write property test for question ID generation (Python)
    - **Property 7: Question ID generation format and sequencing**
    - **Validates: Requirements 6.2, 8.6**

  - [ ]* 4.7 Write property test for batch atomicity (Python)
    - **Property 9: Batch import atomicity**
    - **Validates: Requirements 8.9**

  - [ ]* 4.8 Write property test for audit trail on mutations (Python)
    - **Property 6: Audit trail on all mutations**
    - **Validates: Requirements 4.8, 6.4, 7.5, 10.2, 16.8**

- [x] 5. Backend: AdminSimulate Lambda
  - [x] 5.1 Implement AdminSimulate Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminSimulate/app.py`
    - Route `POST /admin/simulate`: accept `selectedLifeEvents`, scan allQuestionDB for valid questions, apply assignment filtering logic (universal questions + questions where all `requiredLifeEvents` are in selected set), return results grouped by `questionType`
    - Include admin auth check, CORS headers, OPTIONS handling, DecimalEncoder
    - _Requirements: 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 5.2 Write property test for assignment simulation filtering (Python)
    - **Property 11: Assignment simulation filtering**
    - **Validates: Requirements 9.3**

- [x] 6. Backend: AdminCoverage, AdminStats, AdminExport Lambdas
  - [x] 6.1 Implement AdminCoverage Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminCoverage/app.py`
    - Route `GET /admin/coverage`: scan allQuestionDB, aggregate valid questions by `requiredLifeEvents` keys, count instanceable vs non-instanceable per key, count universal questions
    - _Requirements: 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [x] 6.2 Implement AdminStats Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminStats/app.py`
    - Route `GET /admin/stats`: scan allQuestionDB, compute total/valid/invalid counts, distinct questionTypes, difficulty levels, zero-coverage keys count, instanceable count, and the questionType × Difficulty grid with row/column/grand totals
    - _Requirements: 17.2, 17.3, 17.4, 17.5, 17.6, 17.9, 17.10_

  - [x] 6.3 Implement AdminExport Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminExport/app.py`
    - Route `GET /admin/export`: accept `format` query param (`csv` or `json`), scan allQuestionDB, return all questions in requested format with all attributes
    - CSV format: comma-separated with header row, `requiredLifeEvents` joined as semicolon-separated string
    - _Requirements: 18.2, 18.4, 18.5, 18.6_

  - [ ]* 6.4 Write property test for coverage aggregation (Python)
    - **Property 13: Coverage aggregation correctness**
    - **Validates: Requirements 15.2, 15.4, 15.5**

  - [ ]* 6.5 Write property test for stats grid computation (Python)
    - **Property 15: Stats grid computation**
    - **Validates: Requirements 17.3, 17.4, 17.5, 17.6**

  - [ ]* 6.6 Write property test for export JSON round-trip (Python)
    - **Property 16: Export JSON round-trip**
    - **Validates: Requirements 18.2, 18.6**

- [x] 7. Backend: AdminThemes and AdminMigrate Lambdas
  - [x] 7.1 Implement AdminThemes Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminThemes/app.py`
    - Route `PUT /admin/themes/{questionType}`: scan for all questions with matching questionType, update each with specified `requiredLifeEvents`, `isInstanceable`, `instancePlaceholder`, set `lastModifiedBy` and `lastModifiedAt` via individual `UpdateItem` calls
    - _Requirements: 16.3, 16.7, 16.8, 16.9, 16.10_

  - [x] 7.2 Implement AdminMigrate Lambda handler
    - Create `SamLambda/functions/adminFunctions/adminMigrate/app.py`
    - Route `POST /admin/migrate`: scan all questions, identify records missing new attributes, backfill defaults (`requiredLifeEvents: []`, `isInstanceable: false`, `instancePlaceholder: ""`, `lastModifiedBy: "system-migration"`, `lastModifiedAt: <timestamp>`), skip records that already have attributes, use `UpdateItem` in batches, return updated/skipped counts
    - _Requirements: 14.2, 14.4, 14.5, 14.6_

  - [ ]* 7.3 Write property test for theme bulk update (Python)
    - **Property 14: Theme bulk update applies to all questions in theme**
    - **Validates: Requirements 16.3**

  - [ ]* 7.4 Write property test for migration defaults and count invariant (Python)
    - **Property 12: Migration defaults and count invariant**
    - **Validates: Requirements 14.1, 14.2, 14.6**

- [x] 8. Checkpoint — Backend complete
  - Ensure all backend Lambda handlers are created with correct routing, admin auth, CORS, and error handling. Ensure all tests pass, ask the user if questions arise.


- [x] 9. Frontend: Admin routing, gate, and layout
  - [x] 9.1 Create AdminGate component
    - Create `FrontEndCode/src/components/AdminGate.tsx` that calls `fetchAuthSession()` from `aws-amplify/auth`, checks `payload['cognito:groups']` for `SoulReelAdmins`, redirects non-admins to `/dashboard` or `/benefactor-dashboard` with "Access denied" toast, redirects unauthenticated users to `/login`
    - _Requirements: 2.1, 2.2, 2.3, 11.6_

  - [x] 9.2 Create AdminLayout component with sidebar navigation
    - Create `FrontEndCode/src/components/AdminLayout.tsx` with sidebar nav linking to all admin sub-pages (dashboard, questions, create, batch, simulate, coverage, themes, export), display admin email in header, use existing shadcn/ui components and Tailwind with project color tokens
    - _Requirements: 11.3, 11.4, 11.5_

  - [x] 9.3 Add admin routes to App.tsx
    - Add `/admin/*` nested routes wrapped in `AdminGate` and `AdminLayout`, with sub-routes for each admin page: `/admin` (dashboard), `/admin/questions`, `/admin/create`, `/admin/batch`, `/admin/simulate`, `/admin/coverage`, `/admin/themes`, `/admin/export`
    - _Requirements: 11.1, 11.2_

  - [x] 9.4 Create admin API service module
    - Create `FrontEndCode/src/services/adminService.ts` with typed functions for all admin API calls: `fetchQuestions()`, `createQuestion()`, `updateQuestion()`, `batchImport()`, `simulate()`, `fetchCoverage()`, `fetchStats()`, `exportQuestions()`, `applyThemeDefaults()`, `runMigration()` — all using `buildApiUrl()` and `fetchAuthSession()` for auth headers
    - Add admin endpoint paths to `FrontEndCode/src/config/api.ts` ENDPOINTS object
    - _Requirements: 3.7, 6.3, 4.7, 8.7, 9.6, 15.6, 17.9, 18.4, 16.7, 14.2_

- [x] 10. Frontend: Admin Dashboard page
  - [x] 10.1 Implement AdminDashboard page
    - Create `FrontEndCode/src/pages/admin/AdminDashboard.tsx` with stat cards (total questions, valid, invalid, question types, difficulty levels, zero-coverage keys, instanceable count) and the questionType × Difficulty grid table with row/column/grand totals
    - Highlight zero-count cells, make cells clickable to navigate to `/admin/questions` pre-filtered
    - Display migration banner when questions are missing new attributes, with one-click "Initialize All Questions" button
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 14.3_

  - [ ]* 10.2 Write property test for stats grid computation (TypeScript)
    - **Property 15: Stats grid computation**
    - **Validates: Requirements 17.3, 17.4, 17.5, 17.6**

- [x] 11. Checkpoint — Read-only admin working (deploy and test)
  - At this point you can deploy and manually test: log in as admin, see the dashboard with stats grid, browse questions with filtering/sorting. No editing yet — this is the read-only smoke test. Create the `SoulReelAdmins` Cognito group and add your user to it. Deploy backend (`sam build && sam deploy`) and frontend (`npm run build`). Verify: admin login gate works, non-admins are blocked, dashboard loads with real data, question browse shows all questions from allQuestionDB, migration banner appears if questions are missing new attributes.

- [x] 12. Frontend: Question Browse page — detail view and shared components
  - [x] 12.1 Implement QuestionBrowse page
    - Create `FrontEndCode/src/pages/admin/QuestionBrowse.tsx` with paginated table showing `questionId`, `questionType`, `Difficulty`, `Valid`, truncated `Question` text, life event tag count
    - Add text search input (case-insensitive substring on `Question` field), dropdown filters for `questionType` and `Difficulty`, toggle filters for valid/invalid/tagged/untagged/instanceable
    - Add sorting by `questionType`, `Difficulty`, `Valid`, `lastModifiedAt`
    - Display total count of matching questions
    - Clicking a row opens the detail/edit panel
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 10.4_

  - [x] 12.2 Implement shared LifeEventTagEditor component
    - Create `FrontEndCode/src/components/admin/LifeEventTagEditor.tsx` — multi-select dropdown populated from the TypeScript Canonical Life Event Registry, grouped by category, preventing free-text entry
    - _Requirements: 4.3_

  - [x] 12.3 Implement shared QuestionValidationWarnings component
    - Create `FrontEndCode/src/components/admin/QuestionValidationWarnings.tsx` — displays inline warnings for: instanceable without placeholder in text, unrecognized life event keys, instanceable without matching life event key, placeholder set but not instanceable, duplicate question text, case-sensitive questionType mismatch
    - Use yellow/amber visual indicator, warnings are advisory not blocking
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 12.4 Write property test for question filtering correctness (TypeScript)
    - **Property 2: Question filtering correctness**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.6**

  - [ ]* 12.5 Write property test for question sorting stability (TypeScript)
    - **Property 3: Question sorting stability**
    - **Validates: Requirements 3.5, 10.4**

  - [ ]* 12.6 Write property test for validation warnings (TypeScript)
    - **Property 4: Question validation warnings**
    - **Validates: Requirements 4.5, 5.1, 5.3, 5.4**

  - [ ]* 12.7 Write property test for duplicate text detection (TypeScript)
    - **Property 18: Duplicate text detection**
    - **Validates: Requirements 5.6**

  - [ ]* 12.8 Write property test for case-sensitive questionType warning (TypeScript)
    - **Property 19: Case-sensitive questionType warning**
    - **Validates: Requirements 5.7**

- [x] 13. Frontend: Question Create and Edit pages
  - [x] 13.1 Implement QuestionCreate page
    - Create `FrontEndCode/src/pages/admin/QuestionCreate.tsx` with form: `questionType` (dropdown of existing types or free text), `Difficulty` (1–10), `Question` text (textarea, required), `requiredLifeEvents` (LifeEventTagEditor), `isInstanceable` toggle, `instancePlaceholder` dropdown (conditional)
    - Pre-populate life event fields from theme defaults when questionType is selected
    - Show QuestionValidationWarnings inline
    - Show confirmation dialog before submitting
    - _Requirements: 6.1, 4.5, 5.1, 5.3, 5.4, 5.5, 16.5_

  - [x] 13.2 Implement question detail/edit panel in QuestionBrowse
    - Add inline edit panel to QuestionBrowse showing all attributes: `questionId` (read-only), `questionType`, `Difficulty`, `Valid` toggle, `Question` textarea, `requiredLifeEvents` (LifeEventTagEditor), `isInstanceable` toggle, `instancePlaceholder` dropdown, `lastModifiedBy` (read-only), `lastModifiedAt` (read-only)
    - Show confirmation dialog with changed fields before saving
    - Include "Mark as Invalid" / "Mark as Valid" actions with confirmation dialog
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.1, 7.2, 7.3, 7.4, 10.3_

- [x] 14. Checkpoint — Core CRUD flow complete
  - Ensure admin can browse, create, edit, and soft-delete questions end-to-end. Ensure all tests pass, ask the user if questions arise.

- [x] 15. Frontend: Batch Import page
  - [x] 15.1 Implement BatchImport page
    - Create `FrontEndCode/src/pages/admin/BatchImport.tsx` with large textarea for pasting questions, shared `questionType` dropdown/free-text, `Difficulty` input (1–10), `requiredLifeEvents` multi-select (LifeEventTagEditor), `isInstanceable` toggle, `instancePlaceholder` dropdown
    - Parse plain text (one question per line, blank lines ignored) and JSON array (strings or objects with `question` field)
    - Preview table showing parsed questions with auto-generated IDs, count, and ability to remove individual rows
    - Pre-populate tag fields from theme defaults when questionType is selected
    - Highlight duplicate questions (within batch and against existing) with amber warning
    - "Import" button calls batch API endpoint
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.11, 8.12, 8.13_

  - [ ]* 15.2 Write property test for batch input parsing (TypeScript)
    - **Property 8: Batch input parsing**
    - **Validates: Requirements 8.2, 8.5**

  - [ ]* 15.3 Write property test for batch duplicate detection (TypeScript)
    - **Property 10: Batch duplicate detection**
    - **Validates: Requirements 8.12**

- [x] 16. Frontend: Assignment Simulator page
  - [x] 16.1 Implement AssignmentSimulator page
    - Create `FrontEndCode/src/pages/admin/AssignmentSimulator.tsx` with checkboxes for each Life_Event_Key organized by category from the registry
    - "Simulate" button calls POST `/admin/simulate`, displays results grouped by questionType with count per type and total
    - Visually distinguish instanceable questions and show placeholder info
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 16.2 Write property test for assignment simulation filtering (TypeScript)
    - **Property 11: Assignment simulation filtering**
    - **Validates: Requirements 9.3**

- [x] 17. Frontend: Coverage Report, Theme Settings, and Export pages
  - [x] 17.1 Implement CoverageReport page
    - Create `FrontEndCode/src/pages/admin/CoverageReport.tsx` listing every Life_Event_Key with count of valid tagged questions, highlight zero-coverage keys in red, show instanceable vs non-instanceable counts, show universal question count
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 17.2 Implement ThemeSettings page
    - Create `FrontEndCode/src/pages/admin/ThemeSettings.tsx` listing all distinct questionType values, allow setting `requiredLifeEvents`, `isInstanceable`, `instancePlaceholder` per theme, "Apply to All Questions in Theme" button with confirmation dialog showing affected count
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.6_

  - [x] 17.3 Implement ExportView page
    - Create `FrontEndCode/src/pages/admin/ExportView.tsx` with format selector (CSV/JSON), "Export Filtered" respecting current filters and "Export All" option, trigger file download
    - _Requirements: 18.1, 18.2, 18.3_

  - [ ]* 17.4 Write property test for export JSON round-trip (TypeScript)
    - **Property 16: Export JSON round-trip**
    - **Validates: Requirements 18.2, 18.6**

  - [ ]* 17.5 Write property test for export respects active filters (TypeScript)
    - **Property 17: Export respects active filters**
    - **Validates: Requirements 18.3**

- [x] 18. Checkpoint — All pages implemented
  - Ensure all admin pages render correctly, all API calls are wired, and all tests pass. Ask the user if questions arise.

- [ ] 19. Integration wiring and final verification
  - [ ] 19.1 Wire all admin pages into the route tree and verify navigation
    - Ensure all sidebar links navigate correctly, AdminGate blocks non-admins, breadcrumbs/back navigation works, dashboard grid cells link to pre-filtered browse view
    - _Requirements: 11.1, 11.2, 11.4, 17.8_

  - [ ] 19.2 Verify CORS and error handling consistency across all admin Lambdas
    - Ensure every Lambda includes `import os`, `cors_headers(event)` on all responses (200, 4xx, 5xx), OPTIONS handling, `DecimalEncoder` for DynamoDB responses, and `error_response()` for DynamoDB failures
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 20. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Backend Lambdas use Python 3.12 on arm64 with SharedUtilsLayer
- Frontend uses TypeScript/React with shadcn/ui, Tailwind, and fast-check for property tests
- All admin Lambdas must follow the CORS rules (import os, cors_headers, OPTIONS handling) and IAM permission rules from workspace guidelines
