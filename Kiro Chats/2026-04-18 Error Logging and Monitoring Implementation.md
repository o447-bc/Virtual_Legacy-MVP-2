# Error Logging & Monitoring Implementation — 2026-04-18

## What Was Built

A production-grade "Error Telescope" for SoulReel — a unified error logging and monitoring system that captures structured errors from both frontend and backend, stores them in CloudWatch Logs, provides dashboards and queries for analysis, and alerts via email when error rates spike.

## Architecture

```
Frontend (React) → POST /log-error → ErrorIngestionFunction (Lambda) → CloudWatch Logs
                                                                          ↓
Backend (Lambdas) → StructuredLog → CloudWatch Logs                   Metric Filters
                                                                          ↓
                                                                    CloudWatch Alarms
                                                                          ↓
                                                                    SNS → Email (admin@o447.net)
                                                                          
CloudWatch Logs → Dashboards (SoulReel-Metrics, SoulReel-Errors)
```

## Components Created

### Backend

1. **StructuredLog class** (`SamLambda/functions/shared/python/structured_logger.py`)
   - Per-invocation logger initialized with Lambda event + context
   - Auto-extracts userId from Cognito JWT claims
   - Auto-reads X-Correlation-ID header for session correlation
   - Methods: `info()`, `warning()`, `error()`, `log_aws_error()`
   - PII redaction: emails → `[REDACTED_EMAIL]`, phones → `[REDACTED_PHONE]`, known field names → `[REDACTED]`
   - Outputs single-line JSON for CloudWatch Logs Insights parsing

2. **ErrorIngestionFunction** (`SamLambda/functions/errorIngestion/app.py`)
   - POST /log-error endpoint with Cognito auth
   - Validates required fields: errorMessage, component, url
   - Truncates stackTrace to 4096 chars
   - Writes structured JSON with `source: "frontend"`
   - Returns `{"status": "logged"}`

3. **MetricsCollectorFunction** (`SamLambda/functions/metricsCollector/app.py`)
   - Runs daily via CloudWatch Events schedule
   - Scans userStatusDB and UserSubscriptionsDB
   - Publishes to `SoulReel/BusinessMetrics` namespace: RegisteredLegacyMakers, RegisteredLegacyBenefactors, TrialSubscriptions, PaidSubscriptions

4. **Updated responses.py** — `error_response()` now accepts optional `log=` parameter for structured logging, backward compatible

5. **Updated cors.py** — Added `X-Correlation-ID` to allowed headers

### Frontend

1. **errorReporter.ts** (`FrontEndCode/src/services/errorReporter.ts`)
   - Session-scoped UUID correlation ID
   - `reportError()` — fire-and-forget POST to /log-error
   - Rate limiter: max 10 reports per 60-second sliding window
   - Silent failure: never throws, never shows UI errors
   - Auth-gated: only sends when valid Cognito session exists

2. **toastError.ts** (`FrontEndCode/src/utils/toastError.ts`)
   - Wraps Sonner `toast.error()` + calls `reportError()`
   - Migrated across 15+ components

3. **Updated ErrorBoundary.tsx** — calls `reportError()` on React render errors

4. **Updated ConversationInterface.tsx** — reports WebSocket errors (close, parse, connection)

5. **Updated authFetch** in psychTestService.ts and dataRetentionService.ts — adds X-Correlation-ID header

6. **Updated api.ts** — added `LOG_ERROR: '/log-error'` endpoint

### Infrastructure (template.yml)

1. **ErrorIngestionFunction** — Lambda with CognitoAuthorizer, SharedUtilsLayer
2. **ErrorIngestionLogGroup** — explicit log group with 30-day retention
3. **ErrorAlertTopic** — SNS topic `soulreel-error-alerts`
4. **FrontendErrorMetricFilter** — counts frontend errors
5. **FrontendErrorAlarm** — triggers at 20 errors / 5 minutes
6. **BackendErrorAlarm** — triggers at 10 errors / 5 minutes
7. **MetricsCollectorFunction** — daily cron Lambda
8. **SoulReel-Metrics dashboard** — 19 widgets across 7 rows
9. **SoulReel-Errors dashboard** — 6 widgets across 4 rows

### CloudWatch Logs Insights Queries (`SamLambda/cloudwatch-queries/`)

- `all-recent-errors.txt` — all errors in last 24 hours
- `frontend-errors.txt` — frontend-only errors
- `errors-by-component.txt` — error frequency by component/operation
- `errors-by-user.txt` — errors for a specific userId
- `correlation-trace.txt` — cross-source trace by correlationId
- `error-frequency.txt` — error count over time in 5-min buckets
- `top-error-types.txt` — top error types by frequency
- `success-failure-rate.txt` — success vs failure rate per operation

### Steering Files

- `.kiro/steering/structured-logging.md` — how to use StructuredLog in new Lambdas, how to add toastError, how to add correlation IDs, PII rules
- `.kiro/steering/spec-self-review.md` — auto-critique after each spec phase

### Property Tests

- **Backend** (`SamLambda/tests/property/test_error_logging_properties.py`): 9 tests covering PII redaction (caught a real bug — case-insensitive field name matching)
- **Frontend** (`FrontEndCode/src/__tests__/error-reporter.property.test.ts`): 3 tests covering rate limiter and correlation ID

## What Gets Logged

### Backend (StructuredLog)

**ERROR level** — every exception in migrated Lambdas:
- timestamp, level, source="backend", operation, correlationId, userId
- errorType (exception class), message, stackTrace
- httpMethod, path, environment (functionName, memoryMB, region)
- inputParams (PII-redacted)

**INFO level** — significant successful operations:
- timestamp, level, source="backend", operation, correlationId, userId
- status, durationMs, details (operation-specific context)

Currently migrated Lambdas: scorePsychTest, billing, adminSettings

### Frontend (errorReporter)

Every `toastError()` call and ErrorBoundary catch sends:
- errorMessage, component, url, errorType, stackTrace
- metadata: userAgent, buildHash, route
- X-Correlation-ID header for session correlation

### Business Metrics (daily)

RegisteredLegacyMakers, RegisteredLegacyBenefactors, TrialSubscriptions, PaidSubscriptions

## How to Access the Logs

### Dashboards (daily overview)

- **Metrics**: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/SoulReel-Metrics
- **Errors**: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/SoulReel-Errors

### Logs Insights (ad-hoc queries)

1. Go to https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:logs-insights
2. Select log group(s) — search for `ErrorIngestion` or `ScorePsychTest`
3. Paste a query from `SamLambda/cloudwatch-queries/`

### Common queries

**All recent errors:**
```
fields @timestamp, source, component, errorMessage, userId, correlationId
| filter level = "ERROR"
| sort @timestamp desc
| limit 200
```

**Errors for a specific user:**
```
fields @timestamp, source, component, errorMessage, correlationId
| filter level = "ERROR" and userId = "USER_ID_HERE"
| sort @timestamp desc
```

**Session trace by correlation ID:**
```
SOURCE '/aws/lambda/ErrorIngestionFunction-xxx' | SOURCE '/aws/lambda/ScorePsychTestFunction-xxx'
| fields @timestamp, level, source, operation, component, errorMessage, userId
| filter correlationId = "CORRELATION_ID_HERE"
| sort @timestamp asc
```

**Success/failure rate:**
```
fields operation, level
| filter source = "backend"
| stats count(*) as total, sum(level = "ERROR") as errors by operation
| sort errors desc
```

### Email Alerts

SNS subscription confirmed for admin@o447.net on `soulreel-error-alerts` topic. Alarms fire when:
- Frontend: >20 errors in 5 minutes
- Backend: >10 errors in 5 minutes

## Bugs Found and Fixed During Implementation

1. **PII redaction case sensitivity** — property test caught that `firstName` wasn't being redacted because the field name set used camelCase but the comparison lowercased the key. Fixed by normalizing the set to all lowercase.

2. **bedrockPromptTemplate not in JSON Schema** — the scoring Lambda code reads this field but the schema had `additionalProperties: false` without listing it. Caused "Additional properties are not allowed" 400 error on test scoring. Fixed by adding the field to all 3 copies of the schema.

3. **CloudFormation log group race condition** — metric filter referenced the ErrorIngestionFunction log group, but Lambda log groups are only created on first invocation. Fixed by adding an explicit `AWS::Logs::LogGroup` resource.

4. **GitHub Actions OIDC role missing CloudWatch permissions** — the `soulreel-github-actions-oidc` role didn't have `logs:DescribeMetricFilters`. Added CloudWatchLogsFullAccess, CloudWatchFullAccess, and AmazonSNSFullAccess policies.

5. **Dashboard multi-log-group syntax** — used a `logGroupNames` array property that doesn't exist in the CloudWatch Dashboard spec. The correct syntax per AWS docs is `SOURCE 'group1' | SOURCE 'group2' | <query>` within the query string.

## Remaining Work

- Migrate remaining ~30 Lambda functions to StructuredLog (Tier 2 in tasks.md)
- Add `reportError()` to components that use `setError()` state instead of `toast.error()` (e.g., RecordConversation, RecordResponse)
- Consider centralizing the two duplicate `authFetch` functions into a shared module
- Add metric filters for newly migrated Lambdas as they're updated
