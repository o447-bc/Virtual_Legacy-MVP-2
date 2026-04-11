# Implementation Plan: Psychological Testing Framework

## Overview

This plan implements a data-driven psychological testing framework for Soul Reel's Section 3 ("Values and Emotions Deep Dive"). The implementation proceeds bottom-up: infrastructure (SAM template tables, Lambda definitions, IAM policies), then backend logic (schema validation, scoring engine, progress, export, admin import), then frontend (service layer, UI components, page integration), and finally the three initial test definition JSON files. Each task builds on the previous, and property-based tests are placed close to the code they validate.

## Tasks

- [x] 1. SAM Template: DynamoDB tables, global env vars, and shared schema
  - [x] 1.1 Add PsychTests, UserTestProgress, and UserTestResults DynamoDB tables to `SamLambda/template.yml`
    - Add `PsychTestsTable` with PK `testId` (S), SK `version` (S), GSI `status-index` (PK `status`, SK `createdAt`), PAY_PER_REQUEST, KMS encryption via `DataEncryptionKey`, PITR enabled
    - Add `UserTestProgressTable` with PK `userId` (S), SK `testId` (S), TTL on `expiresAt`, PAY_PER_REQUEST, KMS encryption via `DataEncryptionKey`, PITR enabled
    - Add `UserTestResultsTable` with PK `userId` (S), SK `testIdVersionTimestamp` (S), GSI `testId-index` (PK `testId`, SK `timestamp`), PAY_PER_REQUEST, KMS encryption via `DataEncryptionKey`, PITR enabled
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 8.1, 8.2, 8.3, 8.4_

  - [x] 1.2 Add global environment variables for new tables
    - Add `TABLE_PSYCH_TESTS: !Ref PsychTestsTable`, `TABLE_USER_TEST_PROGRESS: !Ref UserTestProgressTable`, `TABLE_USER_TEST_RESULTS: !Ref UserTestResultsTable` to `Globals.Function.Environment.Variables` in `SamLambda/template.yml`
    - _Requirements: 11.3, 11.4_

  - [x] 1.3 Add new DynamoDB tables to CloudTrail EventSelectors for audit logging
    - Update the `DataAccessTrail` resource's `EventSelectors` to include the three new tables (PsychTestsTable, UserTestProgressTable, UserTestResultsTable) in the DynamoDB data events list
    - This ensures all read/write operations on psych test data are captured in the audit trail
    - _Requirements: 4.3, 5.3, 8.3_

  - [x] 1.4 Create the Test Definition JSON Schema file at `SamLambda/schemas/psych-test-definition.schema.json`
    - Define all top-level fields: testId, testName, description, version, previousVersionMapping, estimatedMinutes, consentBlock, disclaimerText, questions, scoringRules, compositeRules, interpretationTemplates, bedrockConfig (optional), videoPromptTrigger, saveProgressEnabled, analyticsEnabled, exportFormats
    - Define question object schema with questionId, text, responseType (enum: likert5, bipolar5, multipleChoice), options, reverseScored, scoringKey, groupByFacet, pageBreakAfter, accessibilityHint, videoPromptFrequency (optional)
    - Define consentBlock schema with title, bodyText, requiredCheckboxLabel
    - Define scoringRules schema with formula, thresholds (array of {min, max, label}), lookupTables (optional)
    - Define compositeRules schema with sources (array of {testId, domain}) and formula
    - Define interpretationTemplates schema as mapping of score ranges to narrative strings
    - Define bedrockConfig schema with useBedrock, maxTokens, temperature, cacheResultsForDays
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.9_

  - [x] 1.5 Add `jsonschema` and `fpdf2` dependencies for Lambda functions
    - Add `jsonschema` to the SharedUtilsLayer or create a requirements.txt in the scorePsychTest and adminImportTest Lambda directories — needed for Test Definition validation
    - Add `fpdf2` to the exportTestResults Lambda's requirements.txt — needed for PDF export generation
    - Verify both packages are available at runtime in the Lambda execution environment
    - Create `__init__.py` files in `SamLambda/functions/psychTestFunctions/` and each sub-directory for Python module resolution

- [x] 2. Checkpoint — Validate SAM template
  - Run `sam validate --lint` from `SamLambda/` to ensure the template is valid with the new tables and env vars. Ensure all tests pass, ask the user if questions arise.

- [x] 3. Backend: ListPsychTests Lambda
  - [x] 3.1 Create `SamLambda/functions/psychTestFunctions/listPsychTests/app.py`
    - `import os` at top, import boto3, json, sys; add shared layer path
    - Import `cors_headers` from shared `cors` module, `error_response` from shared `responses` module
    - Handle OPTIONS preflight returning 200 with CORS headers
    - Extract userId from `event['requestContext']['authorizer']['claims']['sub']`
    - Implement path-based routing in `lambda_handler`: check `event['path']` and `event['httpMethod']` to dispatch to the correct handler
    - For `GET /psych-tests/list`: Query PsychTests table GSI `status-index` where `status = 'active'`, return list of {testId, testName, description, estimatedMinutes, status, version}. Also query UserTestResultsTable for the user's completed results and include a `completedAt` field for tests the user has already taken
    - For `GET /psych-tests/{testId}`: Extract testId from `event['pathParameters']['testId']`, fetch test definition JSON from S3 at `psych-tests/{testId}.json` and return it; return 404 if not found in S3
    - Include CORS headers on every response using `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')`
    - _Requirements: 11.2, 11.3_

  - [x] 3.2 Add ListPsychTests Lambda resource and API events to `SamLambda/template.yml`
    - Define `ListPsychTestsFunction` with CodeUri `functions/psychTestFunctions/listPsychTests/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`
    - Add SharedUtilsLayer
    - Add API events: `GET /psych-tests/list` with CognitoAuthorizer + OPTIONS, `GET /psych-tests/{testId}` with CognitoAuthorizer + OPTIONS
    - Add IAM policies: `dynamodb:Query` on PsychTestsTable and its `status-index` GSI, `dynamodb:Query` on UserTestResultsTable (to fetch user's completed results), `s3:GetObject` on `arn:aws:s3:::virtual-legacy/psych-tests/*`
    - Add KMS decrypt policy: `kms:Decrypt`, `kms:DescribeKey` on DataEncryptionKey
    - _Requirements: 11.1, 11.2_

  - [x] 3.3 Write property test for CORS headers on ListPsychTests responses
    - **Property 17: CORS headers on all responses**
    - **Validates: Requirements 11.2**
    - Create `SamLambda/tests/property/test_psych_cors.py`
    - For any Lambda response (success or error), verify `Access-Control-Allow-Origin` header equals `ALLOWED_ORIGIN` env var (defaulting to `https://www.soulreel.net`)
    - Use hypothesis to generate random event payloads (valid and invalid)
    - Tag: `Feature: psych-test-framework, Property 17: CORS headers on all responses`

- [x] 4. Backend: SaveTestProgress and GetTestProgress Lambdas
  - [x] 4.1 Create `SamLambda/functions/psychTestFunctions/saveTestProgress/app.py`
    - `import os` at top, import boto3, json, sys, time; add shared layer path
    - Import `cors_headers`, `error_response`
    - Handle OPTIONS preflight
    - Extract userId from Cognito claims
    - Parse request body: testId, responses (array of {questionId, answer}), currentQuestionIndex
    - Validate required fields, return 400 if missing
    - Calculate `expiresAt` as current Unix epoch + 2,592,000 seconds (30 days)
    - PutItem to UserTestProgress table with userId, testId, responses, currentQuestionIndex, updatedAt (ISO 8601), expiresAt
    - Return 200 with CORS headers
    - _Requirements: 5.1, 5.2, 5.4, 11.2_

  - [x] 4.2 Create `SamLambda/functions/psychTestFunctions/getTestProgress/app.py`
    - `import os` at top, import boto3, json, sys; add shared layer path
    - Import `cors_headers`, `error_response`
    - Handle OPTIONS preflight
    - Extract userId from Cognito claims
    - Extract testId from path parameters `event['pathParameters']['testId']`
    - GetItem from UserTestProgress table with userId + testId
    - If no item found, return 404 with message "No saved progress for test: {testId}"
    - If found, return 200 with responses, currentQuestionIndex, updatedAt
    - Include CORS headers on every response
    - _Requirements: 5.5, 11.2_

  - [x] 4.3 Add SaveTestProgress and GetTestProgress Lambda resources to `SamLambda/template.yml`
    - Define `SaveTestProgressFunction` with CodeUri `functions/psychTestFunctions/saveTestProgress/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`, SharedUtilsLayer
    - API event: `POST /psych-tests/progress/save` with CognitoAuthorizer + OPTIONS
    - IAM policies: `dynamodb:PutItem` on UserTestProgressTable, KMS encrypt/decrypt on DataEncryptionKey (`kms:Decrypt`, `kms:DescribeKey`, `kms:GenerateDataKey`)
    - Define `GetTestProgressFunction` with CodeUri `functions/psychTestFunctions/getTestProgress/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`, SharedUtilsLayer
    - API event: `GET /psych-tests/progress/{testId}` with CognitoAuthorizer + OPTIONS
    - IAM policies: `dynamodb:GetItem` on UserTestProgressTable, KMS decrypt on DataEncryptionKey (`kms:Decrypt`, `kms:DescribeKey`)
    - _Requirements: 11.1, 11.2_

  - [x] 4.4 Write property tests for progress TTL and round-trip
    - **Property 4: Progress TTL calculation**
    - **Validates: Requirements 5.2**
    - **Property 5: Progress save/load round-trip**
    - **Validates: Requirements 5.5**
    - Create `SamLambda/tests/property/test_psych_progress.py`
    - P4: For any saved progress record, verify `expiresAt` equals `updatedAt` timestamp + 2,592,000 seconds
    - P5: For any set of partial responses and currentQuestionIndex, verify save then load returns identical data
    - Use hypothesis to generate random responses arrays and question indices
    - Tag: `Feature: psych-test-framework, Property 4: Progress TTL calculation` and `Feature: psych-test-framework, Property 5: Progress save/load round-trip`

- [x] 5. Backend: ScorePsychTest Lambda — core scoring engine
  - [x] 5.1 Create `SamLambda/functions/psychTestFunctions/scorePsychTest/app.py` — request handling and validation
    - `import os` at top, import boto3, json, sys, jsonschema; add shared layer path
    - Import `cors_headers`, `error_response`
    - Handle OPTIONS preflight
    - Extract userId from Cognito claims
    - Parse request body: testId, responses (array of {questionId, answer}), optional progressId
    - Fetch Test Definition from S3 at `psych-tests/{testId}.json`; return 404 if not found
    - Load JSON Schema from the bundled `schemas/` directory (include the schema file in the Lambda's CodeUri by placing it at `SamLambda/functions/psychTestFunctions/scorePsychTest/schemas/psych-test-definition.schema.json` or by copying it during build)
    - Validate Test Definition against schema; return 400 with descriptive error if invalid
    - Cross-validate: check that all scoringRules reference questionIds present in questions array; return 400 if orphaned
    - Cross-validate: check that all compositeRules reference domains defined in scoringRules; return 400 if missing
    - Validate that all required questionIds have responses; return 400 listing missing questionIds
    - _Requirements: 1.8, 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.11_

  - [x] 5.2 Implement scoring logic in `scorePsychTest/app.py` — reverse scoring, domain scores, facet scores, thresholds, composites
    - Apply reverse scoring: for questions with `reverseScored: true` and Likert-5, scored value = (6 - answer)
    - Calculate domain scores: group scored responses by `scoringKey`, apply formula from scoringRules (support "mean" and "sum")
    - Calculate facet scores: group scored responses by `groupByFacet`, apply formula from scoringRules
    - Apply threshold classifications: for each domain/facet score, find matching threshold range (min ≤ score ≤ max) and assign label; "unclassified" if no match
    - Apply composite rules if present: combine domain/facet scores from one or more tests using the specified formula
    - Handle previousVersionMapping: if present and user has prior results, align questionIds for comparison
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.12_

  - [x] 5.3 Implement Bedrock narrative generation in `scorePsychTest/app.py`
    - If `bedrockConfig.useBedrock` is true in the Test Definition:
      - Check UserTestResults table for cached narrative (if `cacheResultsForDays > 0`)
      - If no cache hit, call `bedrock-runtime:InvokeModel` with scored results + interpretationTemplates as context
      - Use `maxTokens` and `temperature` from bedrockConfig
      - Store narrative with cacheExpiry timestamp
      - Set `narrativeSource: "bedrock"` in result
    - If Bedrock call fails: log error with Bedrock request ID, fall back to interpretationTemplates, set `narrativeSource: "template"`
    - If `useBedrock` is false: generate narrative from interpretationTemplates directly, set `narrativeSource: "template"`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 5.4 Implement result storage and progress cleanup in `scorePsychTest/app.py`
    - Store complete results in UserTestResults table: userId (PK), `{testId}#{version}#{timestamp}` (SK), testId, version, timestamp, domainScores, facetScores, compositeScores, thresholdClassifications, narrativeText, narrativeSource, rawResponses
    - Delete corresponding progress record from UserTestProgress table (userId + testId)
    - Return 200 response with full results JSON including domainScores, facetScores, compositeScores, thresholdClassifications, narrativeText, narrativeSource, exportFormats
    - Include CORS headers on every response
    - _Requirements: 5.6, 6.9, 8.4, 11.2_

  - [x] 5.5 Add ScorePsychTest Lambda resource to `SamLambda/template.yml`
    - Define `ScorePsychTestFunction` with CodeUri `functions/psychTestFunctions/scorePsychTest/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`, Timeout 30 (scoring + Bedrock may take longer), MemorySize 256
    - Add SharedUtilsLayer
    - API event: `POST /psych-tests/score` with CognitoAuthorizer + OPTIONS
    - IAM policies:
      - `s3:GetObject` on `arn:aws:s3:::virtual-legacy/psych-tests/*`
      - `dynamodb:GetItem`, `dynamodb:PutItem` on PsychTestsTable
      - `dynamodb:GetItem`, `dynamodb:PutItem` on UserTestResultsTable
      - `dynamodb:GetItem`, `dynamodb:DeleteItem` on UserTestProgressTable
      - `bedrock:InvokeModel` on `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*` (verify exact ARN format for the Bedrock model in use; may need `arn:aws:bedrock:*::foundation-model/*` for flexibility)
      - KMS: `kms:Decrypt`, `kms:DescribeKey`, `kms:GenerateDataKey` on DataEncryptionKey
    - _Requirements: 6.10, 7.5, 11.1_

  - [x] 5.6 Write property tests for schema validation and JSON round-trip
    - **Property 1: Schema conformance**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2**
    - **Property 2: Test Definition JSON round-trip**
    - **Validates: Requirements 1.10**
    - Create `SamLambda/tests/property/test_psych_schema.py`
    - P1: Generate valid Test Definition objects using hypothesis strategies; validate against schema — should pass. Generate invalid objects (missing required fields, wrong types) — should fail with descriptive error
    - P2: For any valid Test Definition, serialize to JSON then parse back — should produce equivalent object
    - Tag: `Feature: psych-test-framework, Property 1: Schema conformance` and `Feature: psych-test-framework, Property 2: Test Definition JSON round-trip`

  - [x] 5.7 Write property tests for scoring logic
    - **Property 7: Reverse scoring transformation**
    - **Validates: Requirements 6.3**
    - **Property 8: Domain and facet score calculation**
    - **Validates: Requirements 6.4, 6.5**
    - **Property 9: Threshold classification**
    - **Validates: Requirements 6.6**
    - **Property 10: Scoring idempotence**
    - **Validates: Requirements 6.12**
    - Create `SamLambda/tests/property/test_psych_scoring.py`
    - P7: For any Likert-5 value V (1–5) and reverseScored=true, scored value = (6 - V); for reverseScored=false, scored value = V
    - P8: For any set of responses and "mean" formula, domain score = arithmetic mean of scored responses grouped by scoringKey; facet score = arithmetic mean grouped by groupByFacet
    - P9: For any numeric score and non-overlapping contiguous thresholds, classification returns correct label; out-of-range returns "unclassified"
    - P10: For any valid responses, scoring twice produces identical results
    - Tag each property with its number and title

  - [x] 5.8 Write property test for progress cleanup after scoring
    - **Property 6: Progress cleanup after scoring**
    - **Validates: Requirements 5.6**
    - Add to `SamLambda/tests/property/test_psych_scoring.py`
    - For any completed test submission that is successfully scored, verify the progress record is deleted from UserTestProgress table
    - Tag: `Feature: psych-test-framework, Property 6: Progress cleanup after scoring`

- [x] 6. Checkpoint — Backend scoring engine validation
  - Ensure all tests pass, ask the user if questions arise. Run `sam validate --lint` from `SamLambda/`. Verify the scoring Lambda handles all error cases from the design's error handling table.

- [x] 7. Backend: ExportTestResults Lambda
  - [x] 7.1 Create `SamLambda/functions/psychTestFunctions/exportTestResults/app.py`
    - `import os` at top, import boto3, json, sys, csv, io; add shared layer path
    - Import `cors_headers`, `error_response`
    - Handle OPTIONS preflight
    - Extract userId from Cognito claims
    - Parse request body: testId, version, timestamp, format
    - Validate format is one of PDF, JSON, CSV; return 400 if unsupported
    - Fetch result from UserTestResults table using userId (PK) and `{testId}#{version}#{timestamp}` (SK); return 404 if not found
    - **JSON export**: Build JSON with domainScores, facetScores, compositeScores, thresholdClassifications, narrativeText — exclude rawResponses
    - **CSV export**: Build CSV with header row (name, raw_score, threshold_label, percentile) and one row per domain + facet
    - **PDF export**: Use `fpdf2` (lightweight, pure-Python PDF library — add to Lambda requirements.txt) to generate PDF with test name, date, domain scores with threshold labels, facet scores, narrative text. Avoid `reportlab` as it is too heavy for Lambda cold starts
    - Upload export file to S3 at `psych-exports/{userId}/{testId}/{timestamp}.{format_lower}`
    - Update exportPaths field in UserTestResults table
    - Generate pre-signed S3 URL with 24-hour expiry (86400 seconds)
    - Return 200 with downloadUrl and expiresIn
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [x] 7.2 Add ExportTestResults Lambda resource to `SamLambda/template.yml`
    - Define `ExportTestResultsFunction` with CodeUri `functions/psychTestFunctions/exportTestResults/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`, Timeout 30, MemorySize 256
    - Add SharedUtilsLayer
    - API event: `POST /psych-tests/export` with CognitoAuthorizer + OPTIONS
    - IAM policies:
      - `dynamodb:GetItem`, `dynamodb:UpdateItem` on UserTestResultsTable
      - `s3:PutObject`, `s3:GetObject` on `arn:aws:s3:::virtual-legacy/psych-exports/*`
      - KMS: `kms:Decrypt`, `kms:DescribeKey`, `kms:GenerateDataKey` on DataEncryptionKey
    - _Requirements: 9.6, 11.1_

  - [x] 7.3 Write property tests for export logic
    - **Property 11: Export path construction**
    - **Validates: Requirements 9.2**
    - **Property 12: JSON export excludes rawResponses**
    - **Validates: Requirements 9.4**
    - **Property 13: CSV export structure**
    - **Validates: Requirements 9.5**
    - Create `SamLambda/tests/property/test_psych_export.py`
    - P11: For any userId, testId, timestamp, format — constructed S3 path matches `psych-exports/{userId}/{testId}/{timestamp}.{format_lower}`
    - P12: For any test result, JSON export contains domainScores, facetScores, compositeScores, thresholdClassifications, narrativeText but NOT rawResponses
    - P13: For any result with D domains and F facets, CSV has exactly (D + F) data rows plus header, with columns name, raw_score, threshold_label, percentile
    - Tag each property with its number and title

- [x] 8. Backend: AdminImportTest Lambda
  - [x] 8.1 Create `SamLambda/functions/psychTestFunctions/adminImportTest/app.py`
    - `import os` at top, import boto3, json, sys, jsonschema; add shared layer path
    - Import `cors_headers`, `error_response`
    - Handle OPTIONS preflight
    - Extract userId from Cognito claims; verify admin group membership (check `cognito:groups` claim for `SoulReelAdmins`)
    - Parse request body containing the Test Definition JSON (or an S3 key pointing to an uploaded file)
    - Validate Test Definition against the JSON Schema; return 400 if invalid
    - Check PsychTests table for existing testId + version; return 409 if duplicate
    - Upload Test Definition to S3 at `psych-tests/{testId}.json`
    - Create metadata record in PsychTests table: testId, version, testName, description, estimatedMinutes, status="active", s3Path, previousVersionMapping (if present), createdAt
    - Generate question records in allQuestionDB: one record per question with questionType = testId, facet tag = groupByFacet
    - Return 200 with import summary (testId, version, questionCount)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 8.2 Add AdminImportTest Lambda resource to `SamLambda/template.yml`
    - Define `AdminImportTestFunction` with CodeUri `functions/psychTestFunctions/adminImportTest/`, Handler `app.lambda_handler`, Runtime `python3.12`, Architecture `arm64`, Timeout 30
    - Add SharedUtilsLayer
    - API event: `POST /psych-tests/admin/import` with CognitoAuthorizer + OPTIONS
    - IAM policies:
      - `s3:GetObject`, `s3:PutObject` on `arn:aws:s3:::virtual-legacy/psych-tests/*`
      - `dynamodb:PutItem`, `dynamodb:GetItem` on PsychTestsTable
      - `dynamodb:PutItem` on allQuestionDB table (`arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/allQuestionDB`)
      - KMS: `kms:Decrypt`, `kms:DescribeKey`, `kms:GenerateDataKey` on DataEncryptionKey
    - _Requirements: 11.1_

  - [x] 8.3 Write property test for admin import correctness
    - **Property 3: Admin import correctness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
    - Create `SamLambda/tests/property/test_psych_import.py`
    - For any valid Test Definition with N questions, importing produces exactly N question records in allQuestionDB where each has questionType = testId and facet tag = groupByFacet, plus a metadata record in PsychTests table with testId, version, status, s3Path, and previousVersionMapping (if present)
    - Tag: `Feature: psych-test-framework, Property 3: Admin import correctness`

- [x] 9. Checkpoint — Full backend validation
  - Ensure all tests pass, ask the user if questions arise. Run `sam validate --lint` from `SamLambda/`. Verify all 6 Lambda functions are defined with correct IAM policies, API events, and CORS configuration.

- [x] 10. Frontend: TypeScript types and API service layer
  - [x] 10.1 Create TypeScript type definitions at `FrontEndCode/src/types/psychTests.ts`
    - Define `TestDefinition` interface matching the JSON schema (testId, testName, description, version, previousVersionMapping, estimatedMinutes, consentBlock, disclaimerText, questions, scoringRules, compositeRules, interpretationTemplates, bedrockConfig, videoPromptTrigger, saveProgressEnabled, analyticsEnabled, exportFormats)
    - Define `Question` interface (questionId, text, responseType, options, reverseScored, scoringKey, groupByFacet, pageBreakAfter, accessibilityHint, videoPromptFrequency)
    - Define `ConsentBlock` interface (title, bodyText, requiredCheckboxLabel)
    - Define `ScoringRule`, `CompositeRule`, `InterpretationEntry` interfaces
    - Define `BedrockConfig` interface
    - Define `PsychTest` interface for list responses (testId, testName, description, estimatedMinutes, status, version)
    - Define `TestProgress` interface (responses, currentQuestionIndex, updatedAt)
    - Define `TestResult` interface (userId, testId, version, timestamp, domainScores, facetScores, compositeScores, thresholdClassifications, narrativeText, narrativeSource, exportFormats)
    - Define `ExportResponse` interface (downloadUrl, expiresIn)
    - Define `ScoreEntry` interface ({raw, normalized, label}) for domain/facet scores
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 10.2 Create API service at `FrontEndCode/src/services/psychTestService.ts`
    - Follow the pattern in existing services (e.g., `progressService.ts`): use `fetchAuthSession` for auth token, `buildApiUrl` for URL construction
    - Add new endpoints to `FrontEndCode/src/config/api.ts` in `API_CONFIG.ENDPOINTS`:
      - `PSYCH_TESTS_LIST: '/psych-tests/list'`
      - `PSYCH_TEST_DEFINITION: '/psych-tests'` (used as `/psych-tests/{testId}`)
      - `PSYCH_TESTS_SCORE: '/psych-tests/score'`
      - `PSYCH_TESTS_PROGRESS_SAVE: '/psych-tests/progress/save'`
      - `PSYCH_TESTS_PROGRESS_GET: '/psych-tests/progress'` (used as `/psych-tests/progress/{testId}`)
      - `PSYCH_TESTS_EXPORT: '/psych-tests/export'`
    - Implement `listPsychTests(): Promise<PsychTest[]>` — GET to list endpoint; response includes `completedAt` field for tests the user has already taken
    - Implement `getTestDefinition(testId: string): Promise<TestDefinition>` — GET to `/{testId}` endpoint
    - Implement `saveTestProgress(testId: string, responses: Response[], currentIndex: number): Promise<void>` — POST to progress save endpoint
    - Implement `getTestProgress(testId: string): Promise<TestProgress | null>` — GET to progress get endpoint, return null on 404
    - Implement `scoreTest(testId: string, responses: Response[]): Promise<TestResult>` — POST to score endpoint
    - Implement `exportResults(testId: string, version: string, timestamp: string, format: string): Promise<ExportResponse>` — POST to export endpoint
    - _Requirements: 10.1, 10.7, 10.9_

- [x] 11. Frontend: TestTakingUI component
  - [x] 11.1 Create `FrontEndCode/src/components/psych-tests/TestTakingUI.tsx`
    - Accept props: testDefinition (TestDefinition), onComplete (callback with TestResult), onBack (callback), savedProgress (TestProgress | null, optional — for resuming)
    - Implement consent screen: render consentBlock title, bodyText, requiredCheckboxLabel as a checkbox; disable "Begin Test" button until checkbox is checked
    - If `savedProgress` is provided, skip consent screen and initialize responses and currentQuestionIndex from saved progress
    - Implement question renderer that switches on `responseType`:
      - `likert5`: render 5-point Likert scale with labeled radio buttons (Strongly Disagree to Strongly Agree)
      - `bipolar5`: render 5-point bipolar scale with endpoint labels from options array
      - `multipleChoice`: render radio buttons for each option
    - Render each question with `accessibilityHint` as `aria-describedby` attribute for screen reader support
    - Group questions by `groupByFacet` under facet headings
    - Handle `pageBreakAfter`: show page transition between question groups
    - Display progress bar: `Math.round((answeredCount / totalQuestions) * 100)`%
    - Implement video prompt trigger: when question index % `videoPromptFrequency` === 0, show video recording prompt using `VideoRecorder` component with `videoPromptTrigger` template text
    - Mobile-first responsive layout using Tailwind CSS breakpoints
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 10.11, 10.12_

  - [x] 11.2 Implement auto-save and submission logic in TestTakingUI
    - When `saveProgressEnabled` is true: auto-save responses every 30 seconds via `saveTestProgress` API call
    - Also auto-save on `visibilitychange` event (when user switches tabs or minimizes)
    - Auto-save errors: silent retry with exponential backoff (3 attempts); show toast only after all retries fail (per design error handling spec)
    - Use `useEffect` with interval and visibility change listener; clean up on unmount
    - On "Submit" button click: POST all responses to `scoreTest` API, show loading spinner during scoring
    - On scoring success: call `onComplete` callback with the TestResult
    - On scoring failure: show error toast with retry button, preserve responses in local state
    - On test definition fetch failure: show error card with retry button
    - _Requirements: 10.7, 10.9_

  - [x] 11.3 Create `FrontEndCode/src/components/psych-tests/TestResultsView.tsx`
    - Accept props: result (TestResult), testDefinition (TestDefinition), onExport (callback with format), onBack (callback)
    - Display test name and completion date
    - Render domain scores as cards/bars with raw score, normalized score, and threshold label
    - Render facet scores grouped under their parent domain
    - Display narrative text (from Bedrock or template)
    - Render export buttons for each format in `testDefinition.exportFormats` (PDF, JSON, CSV)
    - On export button click: call `onExport` with the selected format
    - Handle export loading state and error toast on failure
    - Mobile-first responsive layout using Tailwind CSS
    - _Requirements: 10.10_

  - [x] 11.4 Write frontend property tests for UI logic
    - **Property 14: Progress percentage calculation**
    - **Validates: Requirements 10.3**
    - Create `FrontEndCode/src/__tests__/psych-test-progress.property.test.ts`
    - For any total T > 0 and answered A where 0 ≤ A ≤ T, progress = Math.round((A / T) * 100)
    - Tag: `Feature: psych-test-framework, Property 14: Progress percentage calculation`

  - [x] 11.5 Write frontend property test for question facet grouping
    - **Property 15: Question facet grouping**
    - **Validates: Requirements 10.5**
    - Create `FrontEndCode/src/__tests__/psych-test-grouping.property.test.ts`
    - For any array of questions, grouping by groupByFacet produces groups where every question shares the same groupByFacet value, and total count across groups equals original array length
    - Tag: `Feature: psych-test-framework, Property 15: Question facet grouping`

  - [x] 11.6 Write frontend property test for video prompt trigger logic
    - **Property 16: Video prompt trigger logic**
    - **Validates: Requirements 10.8**
    - Create `FrontEndCode/src/__tests__/psych-test-video-prompt.property.test.ts`
    - For any question index I ≥ 0 and videoPromptFrequency F > 0, video prompt shown iff I % F === 0
    - Tag: `Feature: psych-test-framework, Property 16: Video prompt trigger logic`

  - [x] 11.7 Write frontend property test for response type control rendering
    - **Property 18: Response type renders correct control**
    - **Validates: Requirements 10.2**
    - Create `FrontEndCode/src/__tests__/psych-test-controls.property.test.ts`
    - For any question with responseType R, the rendered control type is: Likert scale for "likert5", bipolar scale for "bipolar5", radio buttons for "multipleChoice"
    - Tag: `Feature: psych-test-framework, Property 18: Response type renders correct control`

- [x] 12. Frontend: PersonalInsights page integration
  - [x] 12.1 Replace the "Coming Soon" placeholder in `FrontEndCode/src/pages/PersonalInsights.tsx`
    - Keep existing Header, Back to Dashboard button, and OverallProgressSection
    - Add state management: `view` state (list | taking | results), `selectedTestId`, `testDefinition`, `testResult`, `availableTests`, `completedResults`
    - On mount: call `listPsychTests()` to fetch available tests; also fetch any completed results for the user
    - **List view**: render cards for each available test showing testName, description, estimatedMinutes, and a "Start Test" / "Resume" button (show "Resume" if progress exists)
    - **Taking view**: render `TestTakingUI` with the fetched test definition; on load, check for saved progress via `getTestProgress` and pass it to TestTakingUI for resume
    - **Results view**: render `TestResultsView` with the scored result; handle export via `exportResults` API
    - Handle navigation between views using local state (not router)
    - Show completed test results in the list view with "View Results" button
    - _Requirements: 10.1, 10.13, 5.5_

- [x] 13. Checkpoint — Frontend integration validation
  - Ensure all tests pass, ask the user if questions arise. Verify the PersonalInsights page renders correctly with mock data. Verify all API service functions are wired to correct endpoints. Verify CORS endpoints match between frontend config and SAM template.

- [x] 14. Test Definition JSON files for initial tests
  - [x] 14.1 Create IPIP-NEO-60 Test Definition at `SamLambda/psych-tests/ipip-neo-60.json`
    - 60 questions measuring Big Five personality domains: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism
    - Each domain has 12 questions with 2 facets per domain (6 facets total per domain = 30 facets)
    - Include scoringRules with "mean" formula for each domain and facet
    - Include thresholds: Low (1.0–2.5), Average (2.5–3.5), High (3.5–5.0) for each domain
    - Include interpretationTemplates for each domain at each threshold level
    - Set responseType to "likert5" for all questions
    - Mark appropriate questions as reverseScored
    - Include consentBlock with IPIP-NEO-60 specific consent text
    - Set saveProgressEnabled: true, exportFormats: ["PDF", "JSON", "CSV"]
    - Include videoPromptTrigger template and videoPromptFrequency on select questions
    - Include accessibilityHint for each question
    - _Requirements: 12.1, 12.5_

  - [x] 14.2 Create OEJTS Test Definition at `SamLambda/psych-tests/oejts.json`
    - 60 items producing 16-type personality classification (Jungian types)
    - 4 dimensions: Extraversion/Introversion, Sensing/Intuition, Thinking/Feeling, Judging/Perceiving
    - Include scoringRules with appropriate formula for bipolar dimensions
    - Include thresholds for type classification
    - Include interpretationTemplates for each of the 16 types
    - Set responseType to "bipolar5" for dimension items
    - Include consentBlock, saveProgressEnabled, exportFormats
    - _Requirements: 12.2, 12.5_

  - [x] 14.3 Create Personality-Based EI Test Definition at `SamLambda/psych-tests/personality-ei.json`
    - Questions from Open Source Psychometrics Personality-Based Emotional Intelligence Test
    - Include scoringRules for EI dimensions
    - Include thresholds and interpretationTemplates
    - Include consentBlock, saveProgressEnabled, exportFormats
    - _Requirements: 12.3, 12.5_

  - [x] 14.4 Add compositeRules for Legacy Portrait generation
    - In each of the three test definitions, add compositeRules that reference domains from the other tests
    - The IPIP-NEO-60 compositeRules should reference OEJTS dimensions and EI scores
    - Define a combining formula that produces a unified Legacy Portrait score
    - Ensure the ScorePsychTest Lambda can apply these rules when all three tests are scored
    - _Requirements: 12.4_

  - [x] 14.5 Validate all three test definition JSON files against the schema
    - Load each JSON file and validate against `SamLambda/schemas/psych-test-definition.schema.json` using `jsonschema`
    - Fix any validation errors before proceeding
    - Verify cross-references: all scoringRules reference valid questionIds, all compositeRules reference valid domains
    - _Requirements: 1.8, 2.1, 2.3, 2.4_

  - [x] 14.6 Configure S3 deployment for test definition files
    - Ensure the `SamLambda/psych-tests/` directory contents are uploaded to S3 at `virtual-legacy/psych-tests/` during deployment
    - This can be done via a post-deploy script, a custom SAM resource, or by documenting a manual `aws s3 sync` command in the deployment process
    - Also bundle the JSON Schema file with the adminImportTest Lambda (copy `SamLambda/schemas/psych-test-definition.schema.json` to `SamLambda/functions/psychTestFunctions/adminImportTest/schemas/`)
    - _Requirements: 12.5_

- [x] 15. Checkpoint — End-to-end validation
  - Ensure all tests pass, ask the user if questions arise. Verify all three test definition JSON files validate against the schema. Verify the SAM template is valid. Verify frontend types match backend response shapes. Verify all 18 correctness properties have corresponding test tasks.

- [x] 16. Final wiring and cleanup
  - [x] 16.1 Verify all Lambda functions include `import os` and use `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')` for CORS
    - Check each of the 6 Lambda files: listPsychTests, saveTestProgress, getTestProgress, scorePsychTest, exportTestResults, adminImportTest
    - Verify each handles OPTIONS preflight correctly
    - Verify each returns CORS headers on success AND error responses
    - _Requirements: 6.11, 11.2_

  - [x] 16.2 Verify all IAM policies in `SamLambda/template.yml` match the AWS API calls in each Lambda
    - Cross-reference each Lambda's boto3 calls against its IAM policy statements
    - Ensure no missing permissions (especially: dynamodb:Query for GSI access, s3:GetObject vs s3:PutObject, bedrock:InvokeModel)
    - Verify KMS permissions are present for all Lambdas that read/write encrypted tables
    - _Requirements: 6.10, 7.5, 9.6_

  - [x] 16.3 Verify frontend API endpoint paths match SAM template API event paths
    - Cross-reference `API_CONFIG.ENDPOINTS` in `FrontEndCode/src/config/api.ts` against the API events in `SamLambda/template.yml`
    - Ensure path parameters ({testId}) are correctly constructed in the service layer
    - _Requirements: 11.1_

- [x] 17. Final checkpoint — Complete validation
  - Ensure all tests pass, ask the user if questions arise. Run `sam validate --lint`. Verify the complete feature is ready for deployment.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All Lambda functions follow existing project patterns: arm64, python3.12, SharedUtilsLayer, CORS via shared module
- Frontend follows existing patterns: fetchAuthSession for auth, buildApiUrl for URLs, Tailwind CSS for styling, toast notifications for errors
- The `jsonschema` Python package must be added to the Lambda layer or bundled with the scoring and admin import Lambdas
- The `fpdf2` Python package must be added to the export Lambda's requirements for PDF generation
- The JSON Schema file at `SamLambda/schemas/` is the canonical source; copies must be bundled with both the scorePsychTest and adminImportTest Lambdas
- Test definition JSON files in `SamLambda/psych-tests/` must be deployed to S3 separately from the SAM stack (SAM deploys Lambda code, not arbitrary S3 objects)
- The existing `getQuestionTypes` Lambda (task 3.1 pattern reference) is missing `import os` — do not copy this bug into new Lambdas
- All new Lambda handlers must use the shared `cors_headers(event)` helper from the shared layer, not inline CORS header construction
