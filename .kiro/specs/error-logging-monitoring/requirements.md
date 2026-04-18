# Requirements Document

## Introduction

SoulReel currently lacks centralized error observability. Backend Lambda functions use inconsistent print() statements, frontend errors are shown to users via Sonner toast notifications but never captured server-side, and there is no alerting when production issues occur. This feature introduces a production-grade "Error Telescope" — a unified error logging and monitoring system that captures structured errors from both frontend and backend, stores them in CloudWatch Logs, provides ready-to-use search queries and dashboards, and alerts the team when error rates spike. The system stays fully serverless, uses only native AWS services (CloudWatch, SNS), and follows the existing SAM + Python Lambda patterns.

## Glossary

- **Structured_Logger**: The shared Python utility module that formats all Lambda log output as JSON with consistent fields (timestamp, level, userId, operation, errorType, message, correlationId, etc.)
- **Error_Ingestion_Endpoint**: The POST /log-error API Gateway endpoint that accepts error reports from the frontend and writes them to CloudWatch Logs using the same structured format as backend errors
- **Error_Reporter**: The frontend TypeScript module that intercepts toast error notifications and React ErrorBoundary catches, then silently sends error details to the Error_Ingestion_Endpoint
- **CloudWatch_Dashboard**: The CloudWatch dashboard resource that displays error metrics, recent errors, and error rate trends for both frontend and backend sources
- **Error_Alarm**: A CloudWatch Alarm that monitors error log frequency via metric filters and triggers SNS notifications when thresholds are exceeded
- **Correlation_ID**: A unique identifier (UUID) generated per user session on the frontend and passed through API requests, enabling correlation of frontend errors with backend errors across the same session
- **PII_Filter**: Logic within the Structured_Logger that strips or redacts personally identifiable information (email addresses, phone numbers, full names) from log payloads before writing to CloudWatch
- **Log_Group**: A CloudWatch Logs log group that collects log streams from one or more Lambda functions; this system organizes log groups by function category with a shared prefix for cross-group querying
- **Metric_Filter**: A CloudWatch Logs metric filter that extracts numeric metrics (e.g., error count) from structured JSON log entries and publishes them as CloudWatch metrics for alarming

## Requirements

### Requirement 1: Structured Backend Logging

**User Story:** As a developer, I want all Lambda functions to emit structured JSON logs with consistent fields, so that I can search, filter, and correlate errors across the entire backend.

#### Acceptance Criteria

1. THE Structured_Logger SHALL output every log entry as a single-line JSON object containing the fields: timestamp (ISO 8601 UTC), level (INFO, WARNING, ERROR), operation (Lambda function name or logical operation), correlationId, and message
2. WHEN a Lambda function logs at ERROR level, THE Structured_Logger SHALL include additional fields: errorType (exception class name), stackTrace (full Python traceback), userId (if available from JWT claims), and httpMethod and path (from the API Gateway event)
3. WHEN a Lambda function logs at INFO level for a significant operation, THE Structured_Logger SHALL include the fields: userId, operation, and a details object with operation-specific context (e.g., videoId for uploads, testId for psych tests)
4. THE Structured_Logger SHALL provide a drop-in replacement for the existing error_response() pattern so that each Lambda function requires minimal code changes to adopt structured logging
5. WHEN the Structured_Logger receives log data containing potential PII (email addresses, phone numbers, full names), THE PII_Filter SHALL redact those values before writing the log entry
6. THE Structured_Logger SHALL extract userId from Cognito JWT claims in the API Gateway event requestContext without requiring each Lambda function to parse claims manually
7. WHILE a Lambda function is processing a request that includes an X-Correlation-ID header, THE Structured_Logger SHALL include that correlationId value in every log entry for that invocation

### Requirement 2: Frontend Error Ingestion Endpoint

**User Story:** As a developer, I want a backend API endpoint that accepts error reports from the frontend, so that client-side errors are captured in the same centralized log store as backend errors.

#### Acceptance Criteria

1. THE Error_Ingestion_Endpoint SHALL accept POST requests at the path /log-error with a JSON body containing: errorMessage (string, required), component (string, required), url (string, required), stackTrace (string, optional), errorType (string, optional), and metadata (object, optional)
2. WHEN the Error_Ingestion_Endpoint receives a valid request, THE Error_Ingestion_Endpoint SHALL write a structured JSON log entry to CloudWatch Logs with source set to "frontend", the userId extracted from the Cognito JWT, and all provided fields
3. WHEN the Error_Ingestion_Endpoint receives a request missing required fields (errorMessage, component, or url), THE Error_Ingestion_Endpoint SHALL return HTTP 400 with a descriptive validation error
4. THE Error_Ingestion_Endpoint SHALL require a valid Cognito JWT via the CognitoAuthorizer, consistent with all other authenticated endpoints in the API
5. IF the Error_Ingestion_Endpoint receives a stackTrace longer than 4096 characters, THEN THE Error_Ingestion_Endpoint SHALL truncate the stackTrace to 4096 characters and append "[truncated]"
6. WHEN the Error_Ingestion_Endpoint receives a request with an X-Correlation-ID header, THE Error_Ingestion_Endpoint SHALL include that correlationId in the structured log entry
7. THE Error_Ingestion_Endpoint SHALL return HTTP 200 with a JSON body containing {status: "logged"} for every successfully processed error report
8. THE Error_Ingestion_Endpoint SHALL complete processing within 3 seconds to avoid blocking the frontend caller

### Requirement 3: Frontend Error Reporter

**User Story:** As a developer, I want the frontend to automatically report errors to the backend whenever a toast error is shown or a React error boundary catches an error, so that no user-facing error goes unrecorded.

#### Acceptance Criteria

1. WHEN the application calls toast.error() with an error message, THE Error_Reporter SHALL send the error details (message, component name, current URL, correlationId) to the Error_Ingestion_Endpoint
2. WHEN the ErrorBoundary catches a React render error, THE Error_Reporter SHALL send the error details (error message, stack trace, component tree info, current URL, correlationId) to the Error_Ingestion_Endpoint
3. THE Error_Reporter SHALL generate a unique Correlation_ID (UUID v4) at session start and include it in every error report and every outgoing API request via the X-Correlation-ID header
4. THE Error_Reporter SHALL send error reports asynchronously without blocking the user interface or delaying the toast notification display
5. IF the Error_Reporter fails to send an error report (network failure, endpoint unavailable), THEN THE Error_Reporter SHALL silently discard the failure without showing additional error messages to the user
6. THE Error_Reporter SHALL rate-limit error reports to a maximum of 10 reports per 60-second window per session to prevent flooding the endpoint during cascading failures
7. THE Error_Reporter SHALL not include any user-entered content (form field values, video transcripts, question responses) in error reports sent to the Error_Ingestion_Endpoint
8. WHEN the user is not authenticated (no valid Cognito session), THE Error_Reporter SHALL queue error reports and discard them rather than sending unauthenticated requests

### Requirement 4: Centralized Log Organization

**User Story:** As a developer, I want all frontend and backend error logs organized in CloudWatch with a consistent structure, so that I can query across all error sources from a single interface.

#### Acceptance Criteria

1. THE Log_Group for the Error_Ingestion_Endpoint SHALL use the naming convention /aws/lambda/SoulReel-ErrorIngestion so that frontend-reported errors are identifiable by log group name
2. THE Structured_Logger SHALL tag every log entry with a source field set to "backend" for Lambda-originated logs, enabling filtering alongside frontend-sourced entries
3. THE system SHALL provide a set of ready-to-use CloudWatch Logs Insights queries stored in the repository: all recent errors (last 24 hours), frontend-only errors, errors filtered by component or operation, errors filtered by userId, and errors filtered by correlationId
4. THE system SHALL provide at least 5 CloudWatch Logs Insights queries that cover: error frequency over time, top error types, top failing components, errors for a specific user, and cross-source correlation by correlationId
5. WHEN a developer runs a correlationId-based query, THE query SHALL return both frontend and backend log entries for that session in chronological order across all log groups

### Requirement 5: CloudWatch Dashboard

**User Story:** As a developer, I want a CloudWatch dashboard that gives me a quick visual overview of system health and error trends, so that I can spot problems without writing queries manually.

#### Acceptance Criteria

1. THE CloudWatch_Dashboard SHALL be defined as a CloudFormation resource in template.yml so that it is created and updated automatically on every SAM deploy
2. THE CloudWatch_Dashboard SHALL display widgets for: total error count (last 1 hour), error rate over time (line graph, 5-minute intervals), top 10 error types, frontend vs backend error split, and recent error log entries
3. THE CloudWatch_Dashboard SHALL include a widget showing errors grouped by operation/component to identify which parts of the system are failing most frequently
4. THE CloudWatch_Dashboard SHALL include a widget showing error counts per unique userId to identify users experiencing repeated failures

### Requirement 6: Error Rate Alerting

**User Story:** As a developer, I want to be notified via email when error rates spike in production, so that I can respond to incidents before users report them.

#### Acceptance Criteria

1. THE system SHALL create a Metric_Filter on the Error_Ingestion_Endpoint log group that counts log entries where level equals "ERROR" and source equals "frontend"
2. THE system SHALL create a Metric_Filter on backend Lambda log groups that counts log entries where level equals "ERROR" and source equals "backend"
3. WHEN the frontend error metric exceeds 20 errors in a 5-minute period, THE Error_Alarm SHALL transition to ALARM state and publish a notification to the SNS alert topic
4. WHEN the backend error metric exceeds 10 errors in a 5-minute period, THE Error_Alarm SHALL transition to ALARM state and publish a notification to the SNS alert topic
5. THE system SHALL create an SNS topic with an email subscription (using the existing SecurityAlertEmail parameter) for delivering alarm notifications
6. WHEN an Error_Alarm transitions to ALARM state, THE SNS notification SHALL include the alarm name, metric value, threshold, and a direct link to the CloudWatch_Dashboard
7. WHEN the error rate drops below the threshold for 3 consecutive evaluation periods, THE Error_Alarm SHALL transition back to OK state

### Requirement 7: Infrastructure and Deployment

**User Story:** As a developer, I want the entire error logging system defined in the SAM template and deployable with a single sam deploy, so that it follows the same infrastructure-as-code pattern as the rest of the application.

#### Acceptance Criteria

1. THE Error_Ingestion_Endpoint Lambda function SHALL be defined in template.yml with the CognitoAuthorizer, the SharedUtilsLayer, and appropriate IAM permissions for CloudWatch Logs
2. THE Error_Ingestion_Endpoint Lambda function SHALL use the same Python 3.12 runtime, CORS configuration, and shared layer pattern as all other Lambda functions in the project
3. THE template.yml SHALL define all CloudWatch Metric Filters, Alarms, SNS Topic, and Dashboard as CloudFormation resources that are created on deploy
4. THE Error_Ingestion_Endpoint SHALL include CORS headers from the shared cors.py utility on every response, consistent with all other endpoints
5. THE system SHALL operate within the AWS Free Tier where possible (CloudWatch Logs first 5GB ingestion free, first 10 custom metrics free, first 3 dashboards free)
6. THE repository SHALL include deployment instructions documenting: SAM build and deploy commands, SNS email subscription confirmation step, and how to verify the dashboard after deploy

### Requirement 8: AI-Ready Log Fidelity

**User Story:** As a developer, I want logs to contain enough structured context that an AI agent can analyze error patterns and suggest fixes, so that debugging is accelerated beyond manual log reading.

#### Acceptance Criteria

1. THE Structured_Logger SHALL include in every ERROR-level entry: the full function input parameters (with PII redacted), the exact exception type and message, the full stack trace, and the environment context (function name, memory allocated, region, stage)
2. THE Structured_Logger SHALL include in every INFO-level entry for significant operations: the operation duration in milliseconds, the input parameters summary, and the output status (success/failure with result summary)
3. WHEN a Lambda function makes a call to an external AWS service (DynamoDB, S3, Cognito) that fails, THE Structured_Logger SHALL log the AWS error code, error message, and the request parameters (with PII redacted) as a separate ERROR-level entry before the function returns its error response
4. THE Error_Reporter SHALL include in every frontend error report: the browser user agent, the React component hierarchy path to the error source, the current route path, and the application version or build hash

### Requirement 9: Logging Standards Steering File

**User Story:** As a developer, I want a steering file that documents how to implement structured logging in any new Lambda function or frontend component, so that future development automatically follows the established logging patterns.

#### Acceptance Criteria

1. THE system SHALL include a steering file at .kiro/steering/structured-logging.md that is automatically included in all Kiro sessions
2. THE steering file SHALL document how to import and initialize the Structured_Logger in a new Python Lambda function, including the required import statement and initialization pattern
3. THE steering file SHALL list which operations qualify as "significant" for INFO-level success logging (e.g., video upload, test scoring, data export, account actions) and provide a code example for each pattern
4. THE steering file SHALL document the required fields for ERROR-level and INFO-level log entries, with copy-pasteable code examples for both backend (Python) and frontend (TypeScript) error reporting
5. THE steering file SHALL document PII handling rules: which fields are automatically redacted, how to mark additional fields for redaction, and what constitutes PII in the SoulReel context
6. THE steering file SHALL document how to add the X-Correlation-ID header when creating a new frontend service function using the authFetch pattern
7. THE steering file SHALL document how to wire up error reporting when adding a new toast notification or error handler in a React component
