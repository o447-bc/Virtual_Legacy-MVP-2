# Implementation Plan: Feedback Report Modal

## Overview

Implement a user-facing feedback submission flow (bug reports and feature requests) and an admin management interface. The work spans SAM infrastructure (DynamoDB table, two Lambda functions), frontend components (FeedbackDialog, AdminFeedbackPage), and wiring into existing patterns (UserMenu, AdminLayout, App.tsx, api.ts, adminService.ts).

## Tasks

- [x] 1. Add DynamoDB table and Lambda definitions to SAM template
  - [x] 1.1 Define FeedbackReportsTable in template.yml
    - Add AWS::DynamoDB::Table with `reportId` (String) partition key, PAY_PER_REQUEST billing, PointInTimeRecoveryEnabled, SSE with DataEncryptionKey
    - Add GSI `submittedAt-index` with partition key `gsiPk` (fixed "ALL" value) and sort key `submittedAt` (String)
    - Add `TABLE_FEEDBACK_REPORTS` environment variable to SAM Globals pointing to the table
    - _Requirements: 7.7, 7.8_

  - [x] 1.2 Define FeedbackIngestionFunction in template.yml
    - Python 3.12 runtime, CognitoAuthorizer, SharedUtilsLayer
    - POST /feedback event + OPTIONS event
    - IAM policies: DynamoDB PutItem on FeedbackReportsTable, Bedrock InvokeModel on `anthropic.claude-3-haiku-*` (wildcard to cover both v1 and v1:0 variants), KMS Decrypt/DescribeKey on DataEncryptionKey
    - Timeout set to 15 seconds
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

  - [x] 1.3 Define AdminFeedbackFunction in template.yml
    - Python 3.12 runtime, CognitoAuthorizer, SharedUtilsLayer
    - Events: GET /admin/feedback, GET /admin/feedback/{reportId}, PATCH /admin/feedback/{reportId}, DELETE /admin/feedback/{reportId}, OPTIONS for each path
    - IAM policies: DynamoDB GetItem, UpdateItem, DeleteItem, Scan on FeedbackReportsTable, DynamoDB Query on FeedbackReportsTable GSI (`table/*/index/*` resource ARN), KMS Decrypt/DescribeKey on DataEncryptionKey
    - _Requirements: 7.9_

- [x] 2. Implement feedback ingestion Lambda
  - [x] 2.1 Create `SamLambda/functions/feedbackIngestion/app.py`
    - `import os` at top, use shared cors.py, responses.py, structured_logger
    - Handle OPTIONS preflight with cors_headers(event)
    - Validate body size ≤ 20 KB, parse JSON
    - Validate required fields: reportType ("bug" or "feature"), subject, description
    - Truncate description to 5000 chars + "[truncated]" if over limit
    - Extract userId from JWT claims (event.requestContext.authorizer.claims.sub)
    - Generate UUID reportId, ISO 8601 submittedAt timestamp
    - Invoke Bedrock Claude Haiku for classification + summary (try/except with fallback to "unclassified" / "")
    - Write record to FeedbackReportsTable with gsiPk="ALL" for GSI
    - Log structured JSON entry to CloudWatch
    - Return `{ status: "submitted" }` with HTTP 200
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13_

  - [ ]* 2.2 Write property test for description truncation (Python/Hypothesis)
    - **Property 5: Description truncation**
    - **Validates: Requirements 5.13**

  - [ ]* 2.3 Write property test for valid submission produces correct stored record (Python/Hypothesis)
    - **Property 3: Valid submission produces correct stored record**
    - **Validates: Requirements 5.1, 5.3, 5.5, 5.10**

  - [ ]* 2.4 Write property test for Bedrock failure graceful degradation (Python/Hypothesis)
    - **Property 4: Bedrock failure graceful degradation**
    - **Validates: Requirements 5.6**

- [x] 3. Implement admin feedback Lambda
  - [x] 3.1 Create `SamLambda/functions/adminFunctions/adminFeedback/app.py`
    - `import os` at top, use shared cors.py, responses.py, structured_logger, admin_auth.py
    - Handle OPTIONS preflight with cors_headers(event)
    - verify_admin(event) check on all non-OPTIONS requests, return 403 if not admin
    - GET /admin/feedback: Query GSI `submittedAt-index` with gsiPk="ALL", ScanIndexForward=False for descending sort, return reports list
    - GET /admin/feedback/{reportId}: GetItem by reportId, return 404 if not found
    - PATCH /admin/feedback/{reportId}: Validate status is "active" or "archived", UpdateItem, return 404 if not found
    - DELETE /admin/feedback/{reportId}: DeleteItem by reportId, return 404 if not found
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

  - [ ]* 3.2 Write property test for archive/unarchive round trip (Python/Hypothesis)
    - **Property 8: Archive/unarchive round trip**
    - **Validates: Requirements 10.3, 12.3**

  - [ ]* 3.3 Write property test for delete then retrieve returns 404 (Python/Hypothesis)
    - **Property 10: Delete then retrieve returns 404**
    - **Validates: Requirements 12.4, 12.6**

- [x] 4. Checkpoint — Ensure backend builds and deploys cleanly
  - Ensure `sam validate --lint` passes from `SamLambda/`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add frontend API config and service functions
  - [x] 5.1 Add feedback endpoints to `FrontEndCode/src/config/api.ts`
    - Add SUBMIT_FEEDBACK: '/feedback'
    - Add ADMIN_FEEDBACK: '/admin/feedback'
    - _Requirements: 7.4, 12.8_

  - [x] 5.2 Add feedback types and service functions to `FrontEndCode/src/services/adminService.ts`
    - Add FeedbackReport interface
    - Add submitFeedback() — POST to SUBMIT_FEEDBACK with auth headers
    - Add fetchFeedbackReports() — GET to ADMIN_FEEDBACK_LIST
    - Add fetchFeedbackReport(reportId) — GET to ADMIN_FEEDBACK_DETAIL/{reportId}
    - Add updateFeedbackStatus(reportId, status) — PATCH to ADMIN_FEEDBACK_UPDATE/{reportId}
    - Add deleteFeedbackReport(reportId) — DELETE to ADMIN_FEEDBACK_DELETE/{reportId}
    - Follow existing getAuthHeaders() + error handling pattern
    - _Requirements: 4.1, 10.2, 10.3, 10.4, 12.1, 12.2, 12.3, 12.4_

- [x] 6. Implement FeedbackDialog component
  - [x] 6.1 Create `FrontEndCode/src/components/FeedbackDialog.tsx`
    - shadcn/ui Dialog with DialogContent width sm:max-w-[540px]
    - DialogTitle: "Report a Bug or Suggest a Feature"
    - DialogDescription: warm, encouraging copy
    - Form fields: Report Type (Select, required), Subject (Input, required, max 200), Description (Textarea, required, min 10, max 5000)
    - Read-only pre-filled email from useAuth(), read-only name with fallback to "Anonymous"
    - Inline validation errors with aria-describedby and aria-invalid
    - Submit button with Loader2 spinner and "Submitting..." text while loading
    - Disable close button and Escape during submission (onOpenChange guarded by isSubmitting)
    - On success: show thank-you message with checkmark icon, auto-close after 2.5s
    - On error: toastError() with user-friendly message, form preserved
    - Reset all fields on open via useEffect
    - Full keyboard navigation, ARIA attributes, min-h-[44px] touch targets
    - _Requirements: 2.1–2.7, 3.1–3.8, 4.1–4.7, 6.1–6.6_

  - [ ]* 6.2 Write property test for form pre-fill with name fallback
    - **Property 1: Form pre-fill with name fallback**
    - Test file: `FrontEndCode/src/__tests__/feedback-modal.property.test.ts`
    - **Validates: Requirements 2.6, 3.5**

  - [ ]* 6.3 Write property test for form validation rejects invalid submissions
    - **Property 2: Form validation rejects invalid submissions**
    - Test file: `FrontEndCode/src/__tests__/feedback-modal.property.test.ts`
    - **Validates: Requirements 3.6, 5.8, 5.9**

  - [ ]* 6.4 Write property test for description truncation (frontend)
    - **Property 5: Description truncation**
    - Test file: `FrontEndCode/src/__tests__/feedback-modal.property.test.ts`
    - **Validates: Requirements 5.13**

  - [ ]* 6.5 Write property test for date formatting
    - **Property 6: Date formatting produces human-readable output**
    - Test file: `FrontEndCode/src/__tests__/feedback-modal.property.test.ts`
    - **Validates: Requirements 9.2**

- [x] 7. Wire FeedbackDialog into UserMenu
  - [x] 7.1 Modify `FrontEndCode/src/components/UserMenu.tsx`
    - Import FeedbackDialog and a lucide-react icon (Bug or Lightbulb)
    - Add `showFeedbackDialog` state (useState)
    - Add DropdownMenuItem "Report a Bug or Suggest a Feature" between "Your Data" and disabled "Settings" items
    - Style with min-h-[44px], text-sm text-legacy-navy, legacy-purple icon, hover:bg-legacy-purple/10
    - onClick sets showFeedbackDialog(true)
    - Render `<FeedbackDialog open={showFeedbackDialog} onOpenChange={setShowFeedbackDialog} />` alongside existing dialogs
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 8. Checkpoint — Ensure frontend feedback submission flow works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement AdminFeedbackPage
  - [x] 9.1 Create `FrontEndCode/src/pages/admin/AdminFeedbackPage.tsx` — table and sorting
    - Page title "Bugs and Feature Requests"
    - Fetch reports via fetchFeedbackReports() on mount
    - Loading state with spinner, error state with retry, empty state with friendly message
    - Sortable table with columns: AI Classification (colored badge), AI Summary, Date Submitted (formatted), Status (badge), User Name, User Email, Actions
    - Default sort: submittedAt descending
    - Column header click toggles ascending/descending sort
    - AI Classification badge: "Bug" red/orange, "Feature" blue/purple
    - Status badge: "Active" green, "Archived" gray
    - _Requirements: 8.3, 9.1–9.8_

  - [x] 9.2 Add archive/delete actions to AdminFeedbackPage
    - Archive/Unarchive button per row (PATCH updateFeedbackStatus), toggles between active/archived
    - Delete button per row with confirmation dialog (DELETE deleteFeedbackReport)
    - In-place row updates on archive/delete without full page reload
    - toastError() on any failed action
    - _Requirements: 10.1–10.7_

  - [x] 9.3 Add detail dialog to AdminFeedbackPage
    - On row click (excluding action buttons): open detail Dialog showing all fields (reportType, subject, description with preserved whitespace, email, name, date, aiClassification, aiSummary)
    - Detail dialog: user-selected Report_Type and AI_Classification side by side
    - Date Submitted prominently at top
    - Close button and Escape key support
    - _Requirements: 11.1–11.6_

  - [ ]* 9.4 Write property test for table sorting correctness
    - **Property 7: Table sorting correctness**
    - Test file: `FrontEndCode/src/__tests__/feedback-admin.property.test.ts`
    - **Validates: Requirements 9.3, 12.1**

  - [ ]* 9.5 Write property test for report display contains all required fields
    - **Property 11: Report display contains all required fields**
    - Test file: `FrontEndCode/src/__tests__/feedback-admin.property.test.ts`
    - **Validates: Requirements 9.1, 11.1**

- [x] 10. Wire AdminFeedbackPage into admin routes
  - [x] 10.1 Modify `FrontEndCode/src/components/AdminLayout.tsx`
    - Import MessageSquare (or Bug) from lucide-react
    - Add new FEEDBACK nav section between ASSESSMENTS and SYSTEM sections
    - Single item: `{ to: "/admin/feedback", label: "Bugs & Requests", icon: MessageSquare }`
    - _Requirements: 8.1_

  - [x] 10.2 Modify `FrontEndCode/src/App.tsx`
    - Import AdminFeedbackPage
    - Add `<Route path="feedback" element={<AdminFeedbackPage />} />` inside the admin route group
    - _Requirements: 8.2, 8.4_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Verify SAM template validates cleanly
  - Verify frontend builds without lint or type errors

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Backend Lambdas must include `import os` at top and use `cors_headers(event)` on every response per project CORS rules
- IAM policies must match all DynamoDB and Bedrock API calls per project IAM rules
