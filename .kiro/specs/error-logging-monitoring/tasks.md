pl# Implementation Plan: Error Logging & Monitoring

## Overview

Implement a unified error observability system for SoulReel. The plan builds incrementally: first the shared structured logger module, then the error ingestion Lambda, then the frontend error reporter, then CloudWatch infrastructure (metric filters, alarms, dashboard), then the steering file, and finally migration of existing Lambda functions. Property-based tests are placed close to each implementation step.

## Tasks

- [-] 1. Implement structured_logger.py in SharedUtilsLayer
  - [x] 1.1 Create `SamLambda/functions/shared/python/structured_logger.py` with the `StructuredLog` class
    - Implement `__init__(self, event, context)` that extracts userId from `event.requestContext.authorizer.claims.sub`, reads `X-Correlation-ID` header, captures function_name/memory/region from context and env
    - Implement `info(operation, details, duration_ms, status)` emitting single-line JSON with all required INFO fields (timestamp, level, source="backend", operation, correlationId, userId, details, durationMs, status)
    - Implement `warning(operation, message, details)` emitting WARNING-level JSON
    - Implement `error(operation, exception, details)` emitting ERROR-level JSON with errorType, stackTrace, userId, httpMethod, path, environment context, and PII-redacted inputParams
    - Implement `log_aws_error(service, operation, error, request_params)` for logging failed boto3 calls with error code, message, and redacted params
    - Implement `redact_pii(data)` static method that recursively walks dicts/lists and redacts email addresses (`[REDACTED_EMAIL]`), phone numbers (`[REDACTED_PHONE]`), and known PII field names (`[REDACTED]`)
    - Handle graceful fallback: if event is malformed, fall back to basic Python logging without crashing
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 8.1, 8.2, 8.3_

  - [ ] 1.2 Write property test: ERROR-level log entries contain all required fields
    - **Property 1: ERROR-level log entries contain all required fields**
    - Generate random events (with/without JWT claims, various HTTP methods/paths) and random exceptions, verify ERROR log JSON has all required fields
    - Create `SamLambda/tests/property/test_error_logging_properties.py`
    - **Validates: Requirements 1.1, 1.2, 1.6, 4.2, 8.1**

  - [ ] 1.3 Write property test: INFO-level log entries contain all required fields
    - **Property 2: INFO-level log entries contain all required fields**
    - Generate random events and operation details, verify INFO log JSON has all required fields
    - **Validates: Requirements 1.1, 1.3, 4.2, 8.2**

  - [x] 1.4 Write property test: PII redaction removes all PII patterns
    - **Property 3: PII redaction removes all PII patterns from log data**
    - Generate random dicts with embedded emails, phone numbers, PII field names, verify `redact_pii()` removes all PII
    - This test is REQUIRED — PII leaking into logs is a compliance risk for a platform storing deeply personal video content
    - **Validates: Requirements 1.5**

  - [ ] 1.5 Write property test: Correlation ID propagation
    - **Property 4: Correlation ID propagation**
    - Generate random UUID correlation IDs, set as X-Correlation-ID header, verify all log entries include it
    - **Validates: Requirements 1.7, 2.6**

  - [ ] 1.6 Write property test: AWS SDK error logging
    - **Property 11: AWS SDK error logging includes error code and redacted params**
    - Generate random ClientError exceptions with various error codes and request params containing PII, verify log entry structure and PII redaction
    - **Validates: Requirements 8.3**

- [x] 2. Update responses.py for backward-compatible structured logging
  - [x] 2.1 Update `SamLambda/functions/shared/python/responses.py` to accept optional `log` parameter
    - Add optional `log` parameter to `error_response()` function signature
    - When `log` is provided and exception is not None, call `log.error()` instead of `print()`
    - When `log` is not provided, keep existing `print()` behavior for backward compatibility
    - Update both copies: `SamLambda/functions/shared/responses.py` and `SamLambda/functions/shared/python/responses.py`
    - _Requirements: 1.4_

- [x] 3. Checkpoint - Ensure structured logger and responses are correct
  - Run `cd SamLambda && python -m pytest tests/property/test_error_logging_properties.py -v` and verify all tests pass
  - If any PII redaction tests fail, fix before proceeding — this is a compliance-critical path
  - Ask the user if questions arise

- [-] 4. Implement ErrorIngestionFunction Lambda
  - [x] 4.1 Create `SamLambda/functions/errorIngestion/app.py` Lambda handler
    - Implement POST /log-error handler using StructuredLog
    - Validate required fields: errorMessage, component, url — return 400 with descriptive error if missing
    - Truncate stackTrace to 4096 chars + "[truncated]" if exceeding limit
    - Extract userId from Cognito JWT claims, correlationId from X-Correlation-ID header
    - Write structured JSON log entry with `source: "frontend"` and all provided fields
    - Return `{"status": "logged"}` with 200 and CORS headers on success
    - Handle OPTIONS preflight, invalid JSON body, body exceeding 10KB
    - Use `cors_headers(event)` from shared cors.py and `error_response()` from shared responses.py
    - Ensure `import os` is present at top of file (per CORS rules)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 7.2, 7.4_

  - [x] 4.2 Add ErrorIngestionFunction to `SamLambda/template.yml`
    - Define Lambda function with Python 3.12 runtime, SharedUtilsLayer, CognitoAuthorizer
    - Add POST /log-error API event with CognitoAuthorizer
    - Add IAM policy for CloudWatch Logs (logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents)
    - IMPORTANT: Update `Globals.Api.Cors.AllowHeaders` to include `X-Correlation-ID` in the allowed headers list — without this, the browser preflight will reject the custom header and correlation IDs will never reach the backend
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 4.3 Validate template.yml after changes
    - Run `cd SamLambda && sam validate --lint` to catch YAML/CloudFormation errors before proceeding
    - Fix any lint errors (the .cfnlintrc file suppresses W3660 which is expected)
    - _Requirements: 7.1_

  - [ ] 4.4 Write property test: Valid error ingestion produces correct log and response
    - **Property 5: Valid error ingestion produces correct log and response**
    - Generate random valid payloads (errorMessage, component, url + optional fields), verify handler returns 200 with correct body and log entry has source="frontend"
    - Add to `SamLambda/tests/property/test_error_logging_properties.py`
    - **Validates: Requirements 2.1, 2.2, 2.7, 7.4**

  - [ ] 4.5 Write property test: Missing required fields returns 400
    - **Property 6: Missing required fields returns 400**
    - Generate payloads with random subsets of required fields missing, verify handler returns 400
    - **Validates: Requirements 2.3**

  - [ ] 4.6 Write property test: Stack trace truncation
    - **Property 7: Stack trace truncation**
    - Generate random strings of varying lengths (0 to 10000 chars), verify truncation behavior at the 4096 boundary
    - **Validates: Requirements 2.5**

- [x] 5. Checkpoint - Ensure backend Lambda and property tests pass
  - Run `cd SamLambda && python -m pytest tests/property/test_error_logging_properties.py -v` and verify all tests pass
  - Run `cd SamLambda && sam validate --lint` and verify no errors
  - Ask the user if questions arise

- [-] 6. Implement frontend errorReporter module
  - [x] 6.1 Create `FrontEndCode/src/services/errorReporter.ts`
    - Generate session-level UUID v4 correlation ID on module load (with `crypto.randomUUID()` fallback for older browsers)
    - Export `getCorrelationId()` function
    - Export `reportError(report: ErrorReport)` — fire-and-forget POST to `/log-error` with auth token
    - Implement rate limiter: max 10 reports per 60-second sliding window, silently drop excess
    - Silent failure: catch all network errors without surfacing them
    - Auth check: only send when valid Cognito session exists, discard otherwise
    - PII guard: do not include form field values or user-generated content
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 6.2 Add `/log-error` endpoint to `FrontEndCode/src/config/api.ts`
    - Add `LOG_ERROR: '/log-error'` to the ENDPOINTS object
    - _Requirements: 2.1_

  - [x] 6.3 Update `FrontEndCode/src/components/ErrorBoundary.tsx` to call reportError
    - Import `reportError` from errorReporter
    - In `componentDidCatch`, call `reportError()` with error message, stack trace, component tree info, current URL, and metadata (userAgent, buildHash, route)
    - Keep existing `console.error()` call
    - _Requirements: 3.2, 8.4_

  - [x] 6.4 Create `toastError` helper wrapper
    - Create `FrontEndCode/src/utils/toastError.ts` that wraps Sonner's `toast.error()` and the shadcn `toast({variant: "destructive"})` pattern, calling `reportError()` with message, component, and current URL
    - Export both `toastError(message, component)` for Sonner-style and `toastDestructive(title, description, component)` for shadcn-style
    - _Requirements: 3.1_

  - [x] 6.5 Update authFetch in ALL service files to include X-Correlation-ID header
    - Update `FrontEndCode/src/services/psychTestService.ts` — add `'X-Correlation-ID': getCorrelationId()` to the authFetch headers
    - Update `FrontEndCode/src/services/dataRetentionService.ts` — add `'X-Correlation-ID': getCorrelationId()` to the authFetch headers
    - Note: Both files define their own local `authFetch` function. Both must be updated independently.
    - _Requirements: 3.3_

  - [x] 6.6 Migrate existing toast.error() calls to use toastError wrapper
    - Replace `toast.error()` calls in these files with `toastError()`, passing the component name:
      - `FrontEndCode/src/contexts/AuthContext.tsx` (login, signup, verification errors)
      - `FrontEndCode/src/pages/PricingPage.tsx` (checkout, billing portal errors)
      - `FrontEndCode/src/pages/BenefactorDashboard.tsx` (invite, relationship, assignment errors)
      - `FrontEndCode/src/pages/ManageBenefactors.tsx` (assignment management errors)
      - `FrontEndCode/src/pages/admin/AdminDashboard.tsx` (stats, migration errors)
      - `FrontEndCode/src/pages/admin/SystemSettings.tsx` (settings load/save errors)
      - `FrontEndCode/src/pages/admin/AssessmentManager.tsx` (test load/import/save errors)
      - `FrontEndCode/src/pages/admin/QuestionCreate.tsx`, `BatchImport.tsx`, `QuestionBrowse.tsx`, `ExportView.tsx`, `ThemeSettings.tsx`, `CoverageReport.tsx`, `AssignmentSimulator.tsx`
      - `FrontEndCode/src/components/PasswordDialog.tsx` (password change errors)
    - Replace `toast({variant: "destructive"})` calls in `FrontEndCode/src/pages/YourData.tsx` with `toastDestructive()`
    - Without this migration, the toastError wrapper exists but nothing uses it — frontend errors remain invisible
    - _Requirements: 3.1_

  - [x] 6.7 Write property test: Rate limiter caps reports
    - **Property 9: Rate limiter caps reports**
    - Generate sequences of N reports (N from 1 to 50), verify only first 10 in any 60-second window trigger fetch calls
    - This test is REQUIRED — without it, a cascading failure could flood the /log-error endpoint and create a secondary outage
    - Create `FrontEndCode/src/__tests__/error-reporter.property.test.ts`
    - **Validates: Requirements 3.6**

  - [ ] 6.8 Write property test: Frontend error report payload contains all required metadata
    - **Property 8: Frontend error report payload contains all required metadata**
    - Generate random error objects and component names, verify payload contains all required metadata fields
    - **Validates: Requirements 3.1, 3.2, 8.4**

  - [ ] 6.9 Write property test: Error reporter silently handles failures
    - **Property 10: Error reporter silently handles failures and unauthenticated state**
    - Generate random error reports with simulated network failures, verify no exceptions thrown
    - **Validates: Requirements 3.5, 3.8**

- [x] 7. Checkpoint - Ensure frontend error reporter and tests pass
  - Run `cd FrontEndCode && npx vitest run src/__tests__/error-reporter.property.test.ts` and verify all tests pass
  - Run `cd FrontEndCode && npm run lint` to verify no lint errors from the toast migration
  - Ask the user if questions arise

- [x] 8. Add CloudWatch infrastructure to template.yml
  - [x] 8.1 Add ErrorAlertTopic SNS resource and metric filters
    - Define `ErrorAlertTopic` SNS topic (`soulreel-error-alerts`) with email subscription using existing `SecurityAlertEmail` parameter (conditional on HasSecurityAlertEmail, same pattern as SecurityAlertEmailSubscription)
    - Define `FrontendErrorMetricFilter` on the ErrorIngestionFunction log group matching `{ $.level = "ERROR" && $.source = "frontend" }`, publishing to `SoulReel/Errors/Frontend` metric
    - For backend errors: define a metric filter on the ErrorIngestionFunction log group matching `{ $.level = "ERROR" && $.source = "backend" }` — this works because backend Lambdas log to their own log groups, but the metric filter approach requires one filter per log group. Instead, start with metric filters on the 3 highest-traffic Lambda log groups (WebSocketDefaultFunction, ScorePsychTestFunction, BillingFunction) and the ErrorIngestionFunction. Additional Lambdas can be added incrementally as they are migrated to StructuredLog.
    - _Requirements: 6.1, 6.2, 6.5_

  - [x] 8.2 Add CloudWatch Alarms
    - Define `FrontendErrorAlarm` — threshold 20 errors in 5-minute period, notifies ErrorAlertTopic, returns to OK after 3 consecutive periods below threshold
    - Define `BackendErrorAlarm` — threshold 10 errors in 5-minute period, notifies ErrorAlertTopic, returns to OK after 3 consecutive periods below threshold
    - _Requirements: 6.3, 6.4, 6.6, 6.7_

  - [x] 8.3 Add CloudWatch Dashboard
    - Define `ErrorMonitoringDashboard` as CloudFormation resource with widgets for: total error count (last 1 hour), error rate over time (line graph, 5-min intervals), top 10 error types, frontend vs backend error split, errors by operation/component, errors by userId, and recent error log entries
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 8.4 Validate template.yml after CloudWatch additions
    - Run `cd SamLambda && sam validate --lint` to catch any CloudFormation errors in the new resources
    - Fix any lint errors before proceeding
    - _Requirements: 7.1_

- [x] 9. Create CloudWatch Logs Insights queries
  - [x] 9.1 Create query files in `SamLambda/cloudwatch-queries/`
    - Create `all-recent-errors.txt` — all errors in last 24 hours across all log groups
    - Create `frontend-errors.txt` — frontend-only errors filtered by `source = "frontend"`
    - Create `errors-by-component.txt` — error frequency grouped by component/operation
    - Create `errors-by-user.txt` — errors filtered by a specific userId
    - Create `correlation-trace.txt` — cross-source trace by correlationId in chronological order
    - Create `error-frequency.txt` — error count over time in 5-minute buckets
    - Create `top-error-types.txt` — top error types by frequency
    - Create `success-failure-rate.txt` — success vs failure rate per operation (uses INFO + ERROR entries)
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 10. Create steering file for structured logging standards
  - [x] 10.1 Create `.kiro/steering/structured-logging.md`
    - Document how to import and initialize `StructuredLog` in a new Python Lambda function
    - List which operations qualify as "significant" for INFO-level success logging with code examples
    - Document required fields for ERROR-level and INFO-level log entries with copy-pasteable code examples for both Python and TypeScript
    - Document PII handling rules: which fields are auto-redacted, how to mark additional fields, what constitutes PII in SoulReel
    - Document how to add X-Correlation-ID header when creating a new frontend service function using authFetch
    - Document how to wire up error reporting when adding a new toast notification or error handler in a React component
    - Document how to add a metric filter for a newly migrated Lambda function
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [-] 11. Migrate existing Lambda functions to use StructuredLog
  - [x] 11.1 Migrate high-impact Lambda functions (Tier 1 — user-facing critical paths)
    - `SamLambda/functions/conversationFunctions/wsDefault/app.py` — WebSocket conversation handler (highest traffic, most complex, handles video/audio/transcription)
    - `SamLambda/functions/billingFunctions/billing/app.py` — billing operations (checkout, subscription status, portal — money path)
    - `SamLambda/functions/psychTestFunctions/scorePsychTest/app.py` — test scoring engine (complex, calls S3 + Bedrock + DynamoDB)
    - For each: initialize StructuredLog at handler entry, replace print() with log.info()/log.error(), pass log to error_response()
    - _Requirements: 1.4, 4.2_

  - [ ] 11.2 Migrate medium-impact Lambda functions (Tier 2 — admin and data operations)
    - `SamLambda/functions/adminFunctions/adminSettings/app.py` — admin settings CRUD
    - `SamLambda/functions/psychTestFunctions/exportTestResults/app.py` — test result export
    - `SamLambda/functions/assignmentFunctions/createAssignment/app.py` — benefactor assignment creation
    - For each: initialize StructuredLog at handler entry, replace print() with log.info()/log.error(), pass log to error_response()
    - _Requirements: 1.4, 4.2_

- [ ] 12. Deployment verification
  - [x] 12.1 Run `cd SamLambda && sam build && sam validate --lint` to verify the full build succeeds
  - [x] 12.2 After deploying (`sam deploy --no-confirm-changeset`), verify the system end-to-end:
    - POST a test error to `/log-error` with a valid JWT and verify 200 response with `{"status": "logged"}`
    - Check CloudWatch Logs for the ErrorIngestionFunction log group — verify the structured JSON entry appears
    - Open the CloudWatch Dashboard — verify widgets load and display data
    - Confirm the SNS email subscription by clicking the confirmation link in the email
    - Run the `correlation-trace.txt` Logs Insights query with the test correlation ID — verify it returns the entry
    - _Requirements: 7.6_

- [x] 13. Final checkpoint - Ensure all tests pass and system is wired together
  - Run `cd SamLambda && python -m pytest tests/property/ -v` to verify all backend property tests pass
  - Run `cd FrontEndCode && npx vitest run src/__tests__/error-reporter.property.test.ts` to verify frontend tests pass
  - Run `cd FrontEndCode && npm run lint` to verify no lint errors
  - Run `cd SamLambda && sam validate --lint` to verify template is valid
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional property tests that can be skipped for faster MVP
- Tasks 1.4 (PII redaction) and 6.7 (rate limiter) are REQUIRED property tests — these cover compliance-critical and stability-critical paths
- Each task references specific requirements for traceability
- Checkpoints include concrete test commands to run
- The structured_logger.py goes in `SamLambda/functions/shared/python/` alongside existing shared modules (cors.py, responses.py, etc.)
- The ErrorIngestionFunction needs IAM permissions for CloudWatch Logs — follow the lambda-iam-permissions steering rule
- All Lambda responses must include CORS headers via `cors_headers(event)` — follow the cors-lambda steering rule
- The X-Correlation-ID header must be added to `Globals.Api.Cors.AllowHeaders` in template.yml (task 4.2)
- Backend metric filters start on 3 high-traffic Lambdas + ErrorIngestionFunction; the steering file (task 10) documents how to add more as Lambdas are migrated
- Two service files define their own local authFetch: psychTestService.ts and dataRetentionService.ts — both must be updated independently for correlation IDs
