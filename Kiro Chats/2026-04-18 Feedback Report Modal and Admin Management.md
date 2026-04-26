# Feedback Report Modal and Admin Management Implementation

**Date:** April 18, 2026  
**Spec:** `.kiro/specs/feedback-report-modal/`  
**Commit:** `82a1e5e` on `master`

## What Was Built

A complete in-app feedback system allowing SoulReel users to report bugs or suggest features, with an AI-powered admin console for reviewing and managing submissions.

## Feature Overview

### User-Facing: Feedback Submission Modal
- New "Report a Bug or Suggest a Feature" menu item added to the UserMenu dropdown (between "Your Data" and "Settings")
- Uses a Lightbulb icon, visible to all authenticated users regardless of persona type
- Opens a shadcn/ui Dialog (540px wide on desktop, responsive on mobile) with:
  - Report Type selector (Bug Report / Feature Request)
  - Subject field (required, max 200 chars)
  - Description field (required, min 10 chars, max 5000 chars)
  - Pre-filled read-only user name and email from AuthContext
  - Inline validation errors with ARIA attributes for accessibility
  - Loading spinner during submission, disabled close during submit
  - Warm thank-you message on success, auto-closes after 2.5 seconds
  - Toast error on failure with form input preserved

### Backend: Feedback Ingestion Lambda
- **Endpoint:** `POST /feedback` (Cognito authenticated)
- **File:** `SamLambda/functions/feedbackIngestion/app.py`
- Validates request body (≤20 KB), required fields, reportType enum
- Truncates descriptions over 5000 chars with "[truncated]" suffix
- Invokes **Claude Haiku via Bedrock** to:
  - Classify the submission as "bug" or "feature_request"
  - Generate a one-sentence AI summary
- Graceful fallback: if Bedrock fails, saves with `aiClassification: "unclassified"` and empty summary — user still gets HTTP 200
- Stores record in DynamoDB with UUID reportId, ISO 8601 timestamp, status "active"
- Logs structured JSON entry to CloudWatch

### Backend: Admin Feedback Lambda
- **Endpoints:** `GET/PATCH/DELETE /admin/feedback` and `/admin/feedback/{reportId}` (Cognito + SoulReelAdmins group)
- **File:** `SamLambda/functions/adminFunctions/adminFeedback/app.py`
- `GET /admin/feedback` — Queries GSI for all reports sorted by date descending
- `GET /admin/feedback/{reportId}` — Single report retrieval
- `PATCH /admin/feedback/{reportId}` — Toggle status between "active" and "archived" (conditional update, 404 if not found)
- `DELETE /admin/feedback/{reportId}` — Permanent deletion (conditional delete, 404 if not found)
- Uses `verify_admin()` server-side check, shared CORS/logging/error utilities

### Infrastructure: DynamoDB Table
- **Table:** `FeedbackReportsDB` (defined in `template.yml`)
- Partition key: `reportId` (String)
- GSI `submittedAt-index`: partition key `gsiPk` (fixed "ALL"), sort key `submittedAt` — enables efficient date-sorted queries
- PAY_PER_REQUEST billing (zero cost when idle)
- KMS encryption (DataEncryptionKey), Point-in-Time Recovery enabled
- `TABLE_FEEDBACK_REPORTS` env var added to SAM Globals

### Admin Console: Bugs and Feature Requests Page
- **File:** `FrontEndCode/src/pages/admin/AdminFeedbackPage.tsx`
- **Route:** `/admin/feedback` (nested under AdminGate + AdminLayout)
- New "FEEDBACK" nav section in AdminLayout sidebar (between ASSESSMENTS and SYSTEM)
- Sortable table with columns: AI Classification (colored badge), AI Summary, Date Submitted, Status (badge), User Name, User Email, Actions
- Default sort: newest first (submittedAt descending)
- Click any column header to sort ascending/descending
- Classification badges: Bug (red), Feature (purple), Unclassified (gray)
- Status badges: Active (green), Archived (gray)
- Archive/Restore button per row (toggles status in place)
- Delete button per row with confirmation dialog
- Click any row to open detail dialog showing all fields:
  - Subject, description (preserved whitespace), date prominently displayed
  - User-selected report type and AI classification shown side by side
  - User name and email
- Empty state, loading spinner, toast errors on failed actions

## Files Created
| File | Purpose |
|------|---------|
| `SamLambda/functions/feedbackIngestion/app.py` | Feedback ingestion Lambda with Bedrock AI classification |
| `SamLambda/functions/adminFunctions/adminFeedback/app.py` | Admin CRUD Lambda for feedback reports |
| `FrontEndCode/src/components/FeedbackDialog.tsx` | User-facing feedback submission modal |
| `FrontEndCode/src/pages/admin/AdminFeedbackPage.tsx` | Admin feedback management page |
| `.kiro/specs/feedback-report-modal/requirements.md` | 12 requirements with acceptance criteria |
| `.kiro/specs/feedback-report-modal/design.md` | Architecture, data models, correctness properties |
| `.kiro/specs/feedback-report-modal/tasks.md` | 11-task implementation plan |
| `.kiro/specs/feedback-report-modal/.config.kiro` | Spec configuration |

## Files Modified
| File | Change |
|------|--------|
| `SamLambda/template.yml` | Added FeedbackReportsTable, FeedbackIngestionFunction, AdminFeedbackFunction with IAM policies |
| `FrontEndCode/src/config/api.ts` | Added SUBMIT_FEEDBACK and ADMIN_FEEDBACK endpoint constants |
| `FrontEndCode/src/services/adminService.ts` | Added FeedbackReport interface and 5 service functions |
| `FrontEndCode/src/components/UserMenu.tsx` | Added feedback menu item and FeedbackDialog integration |
| `FrontEndCode/src/components/AdminLayout.tsx` | Added FEEDBACK nav section with MessageSquare icon |
| `FrontEndCode/src/App.tsx` | Added /admin/feedback route |

## IAM Permissions Added
- **FeedbackIngestionFunction:** DynamoDB PutItem on FeedbackReportsTable, Bedrock InvokeModel (wildcard), KMS Decrypt/DescribeKey/GenerateDataKey
- **AdminFeedbackFunction:** DynamoDB GetItem/UpdateItem/DeleteItem/Scan on FeedbackReportsTable, DynamoDB Query on GSI, KMS Decrypt/DescribeKey

## Validation Results
- `sam validate --lint` — passes
- TypeScript `tsc --noEmit` — zero errors
- ESLint — zero errors (25 pre-existing warnings)
- All existing Vitest tests — pass with no regressions
- Python syntax check — both Lambda files compile clean

## Design Decisions
1. **Synchronous Bedrock call** — Haiku is fast (~1-2s), 15s timeout provides headroom. Avoids async pipeline complexity for a low-volume feature.
2. **No email notifications** — Admin console is the sole review interface per user request.
3. **Archive = soft status toggle** — Archived reports stay in the table with a gray badge. Can be unarchived. Delete is permanent with confirmation.
4. **Single ADMIN_FEEDBACK endpoint constant** — Service functions append `/{reportId}` and use different HTTP methods, matching the ADMIN_SETTINGS pattern.

## Future Considerations
- Add filter toggle to show/hide archived reports in the admin table
- Add pagination if report volume grows significantly
- Consider a "reclassify" button for unclassified reports (Bedrock retry)
- Optional: export feedback reports to CSV
