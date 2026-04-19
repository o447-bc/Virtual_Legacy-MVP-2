# Implementation Plan: Email Capture & Nurture System

## Overview

This plan implements a full-stack email capture and nurture system for SoulReel. Tasks are ordered by dependency: infrastructure first, then backend Lambda functions, SES templates, frontend integration, and admin UI. Backend is Python 3.12 (Lambda + SAM), frontend is React + TypeScript + Tailwind + shadcn/ui.

## Tasks

- [x] 1. Infrastructure — DynamoDB tables, SES config, SNS topic, SSM parameters in template.yml
  - [x] 1.1 Add EmailCaptureTable DynamoDB resource to `SamLambda/template.yml`
    - Table name `EmailCaptureDB`, partition key `email` (String), BillingMode PAY_PER_REQUEST
    - GSI `StatusIndex`: partition key `statusGsi`, sort key `capturedAt`, projection ALL
    - GSI `CapturedWeekIndex`: partition key `capturedWeek`, sort key `capturedAt`, projection ALL
    - PointInTimeRecoverySpecification enabled, SSESpecification with existing `DataEncryptionKey`
    - Add `TABLE_EMAIL_CAPTURE` as an environment variable on the specific Lambda functions that need it (EmailCapture, Unsubscribe, NurtureScheduler, SesEventTracking, AdminEmailCapture, PostConfirmation) — do NOT add to Globals to avoid giving it to all functions
    - _Requirements: 1.1, 1.11_

  - [x] 1.2 Add EmailCaptureRateLimitTable DynamoDB resource to `SamLambda/template.yml`
    - Table name `EmailCaptureRateLimitDB`, partition key `ipAddress` (String), BillingMode PAY_PER_REQUEST
    - TimeToLiveSpecification enabled on `ttl` attribute
    - Add `TABLE_RATE_LIMIT` as an environment variable only on the EmailCaptureFunction
    - _Requirements: 7.2_

  - [x] 1.3 Add SES Configuration Set, SNS topic, and SSM parameters to `SamLambda/template.yml`
    - SES Configuration Set `soulreel-nurture` with event destination for open, click, bounce, complaint events to SNS topic
    - SNS topic `soulreel-ses-nurture-events`
    - Add `SES_CONFIGURATION_SET` as an environment variable only on functions that send emails (EmailCapture, NurtureScheduler, AdminEmailCapture)
    - SSM parameters: `/soulreel/email-nurture/schedule` (default JSON), `/soulreel/email-nurture/paused` (default `"false"`), `/soulreel/email-nurture/unsubscribe-secret` (SecureString), `/soulreel/email-nurture/disposable-domains` (JSON array)
    - _Requirements: 3.8, 3.13, 6.5, 7.3, 11.2_

- [x] 2. Shared referral and unsubscribe utilities (needed by tasks 3, 4, 5)
  - [x] 2.1 Create shared utility functions in `SamLambda/functions/shared/python/referral_utils.py`
    - Implement `generate_referral_hash(email, salt)` using SHA-256, first 10 hex chars
    - Implement `generate_unsubscribe_token(email, secret)` and `verify_unsubscribe_token(token, secret)` per design
    - These are imported by emailCapture, unsubscribe, and nurtureScheduler functions
    - _Requirements: 15.2, 15.6, 6.1, 6.5_

  - [ ]* 2.2 Write property tests for referral hash and unsubscribe token
    - **Property 19: Referral hash is deterministic and fixed-length**
    - **Property 12: Unsubscribe token round trip**
    - **Property 13: Tampered unsubscribe token is rejected**
    - **Validates: Requirements 15.2, 6.1, 6.3**

- [x] 3. Checkpoint — Validate infrastructure and shared utilities
  - Ensure `sam validate --lint` passes on `SamLambda/template.yml`, ask the user if questions arise.

- [x] 3. Email Capture API Lambda function
  - [x] 3.1 Create `SamLambda/functions/emailCaptureFunctions/emailCapture/app.py`
    - Implement `lambda_handler` for POST /email-capture
    - Email validation (RFC 5322 basic format), empty/missing email check
    - Rate limiting: read/increment IP counter in RateLimitTable with atomic `ADD` and TTL, return 429 if >5/hr
    - Disposable domain check: read blocklist from SSM (cached), return 400 if domain matches
    - DynamoDB PutItem for new captures (set defaults: `reminderStage=0`, `variant` random A/B, `openCount=0`, `clickCount=0`, `statusGsi="active"`, `capturedWeek` computed)
    - DynamoDB GetItem + UpdateItem for re-captures (reset `capturedAt` and `reminderStage`, preserve `variant`)
    - Generate unsubscribe token and referral hash for welcome email template data
    - Send Welcome Email (stage 0) via SES `SendTemplatedEmail` with configuration set
    - CORS headers on all responses, `import os` at top
    - Return 200 on success, 400/429/500 on errors per design error table
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 7.1, 7.2, 7.3_

  - [x] 3.2 Add EmailCaptureFunction resource and IAM policy to `SamLambda/template.yml`
    - AWS::Serverless::Function with API event `POST /email-capture` (no auth)
    - CodeUri pointing to `functions/emailCaptureFunctions/emailCapture/`
    - IAM: `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` on EmailCaptureTable; `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` on RateLimitTable; `ses:SendTemplatedEmail`; `ssm:GetParameter` on `/soulreel/email-nurture/unsubscribe-secret` and `/soulreel/email-nurture/disposable-domains`
    - _Requirements: 1.11, 10.1, 10.7_

  - [ ]* 3.3 Write property tests for email capture logic
    - **Property 1: New capture record has correct defaults**
    - **Property 3: Invalid email format is rejected**
    - **Property 4: Welcome email sent on every capture**
    - **Property 5: CORS header present on all responses**
    - **Property 14: Rate limiting enforces per-IP threshold**
    - **Property 15: Disposable email domains are rejected**
    - **Validates: Requirements 1.1, 1.3, 1.6, 1.7, 1.10, 7.1, 7.3**

  - [ ]* 3.4 Write property test for re-capture variant preservation
    - **Property 2: Re-capture preserves variant assignment**
    - **Validates: Requirements 1.2, 12.6**

- [x] 4. Unsubscribe Lambda function
  - [x] 4.1 Create `SamLambda/functions/emailCaptureFunctions/unsubscribe/app.py`
    - Implement `lambda_handler` for GET /email-capture/unsubscribe
    - Read unsubscribe secret from SSM (cached)
    - Validate HMAC token using `verify_unsubscribe_token` logic from design
    - On valid token: set `unsubscribedAt` and `statusGsi="unsubscribed"` in DynamoDB, return branded HTML success page
    - On invalid/tampered token: return 400 HTML error page
    - On non-existent email: attempt UpdateItem which will silently have no effect, then return success page (prevent enumeration). Do NOT use GetItem first — just catch ConditionalCheckFailedException if using a condition, or let the update be a no-op.
    - CORS headers, `import os` at top
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 7.4_

  - [x] 4.2 Add UnsubscribeFunction resource and IAM policy to `SamLambda/template.yml`
    - AWS::Serverless::Function with API event `GET /email-capture/unsubscribe` (no auth)
    - IAM: `dynamodb:UpdateItem` on EmailCaptureTable; `ssm:GetParameter` on `/soulreel/email-nurture/unsubscribe-secret`
    - _Requirements: 6.6, 10.5_

- [x] 5. Nurture Scheduler Lambda function
  - [x] 5.1 Create `SamLambda/functions/emailCaptureFunctions/nurtureScheduler/app.py`
    - Implement `lambda_handler` triggered by CloudWatch Events cron
    - Check pause flag from SSM; if `"true"`, exit immediately
    - Read schedule intervals from SSM (with defaults: 7, 14, 28, 56 days)
    - Read unsubscribe secret from SSM for generating tokens in emails
    - Pass 1 (active): Scan EmailCaptureTable for records where `convertedAt` is null, `expiredAt` is null, `unsubscribedAt` is null, `bounceStatus` != `"hard"`; advance stages based on elapsed days from `capturedAt`
    - Stage 4 past threshold: set `expiredAt`, update `statusGsi` to `"expired"`
    - Pass 2 (win-back): Scan for records with `expiredAt` set, `reminderStage=4`, `capturedAt` >= 180 days ago, not converted/unsubscribed/hard-bounced; send stage 5 and update `reminderStage` to 5
    - Stage 5 records: no further emails
    - Select template by stage and variant (`soulreel-nurture-stage-{N}-{variant}`), fall back to A if B doesn't exist
    - Send via SES `SendTemplatedEmail` with configuration set
    - On SES failure: log error, skip stage update, continue with remaining
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.13, 3.14, 3.15_

  - [x] 5.2 Add NurtureSchedulerFunction resource and IAM policy to `SamLambda/template.yml`
    - AWS::Serverless::Function with Schedule event `cron(0 14 * * ? *)`
    - IAM: `dynamodb:Scan`, `dynamodb:UpdateItem` on EmailCaptureTable; `ses:SendEmail`, `ses:SendTemplatedEmail`; `ssm:GetParameter`, `ssm:GetParameters` on `/soulreel/email-nurture/*`
    - _Requirements: 3.1, 3.12, 10.2, 10.3_

  - [ ]* 5.3 Write property tests for nurture scheduler logic
    - **Property 6: Nurture scheduler filters only eligible records**
    - **Property 7: Stage transition correctness**
    - **Property 8: Template selection matches stage and variant**
    - **Property 9: Pause flag stops all processing**
    - **Property 10: Schedule intervals from SSM with defaults**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.13, 3.14, 3.15, 14.4**

- [x] 6. SES Event Tracking Lambda function
  - [x] 6.1 Create `SamLambda/functions/emailCaptureFunctions/sesEventTracking/app.py`
    - Implement `lambda_handler` triggered by SNS subscription
    - Parse SNS messages for open, click, bounce event types
    - Extract stage number from SES template name (e.g., `soulreel-nurture-stage-2-A` → stage 2)
    - Open events: increment `openCount`, update `lastOpenedAt`, update `stageOpens` map
    - Click events: increment `clickCount`, update `lastClickedAt`, update `stageClicks` map
    - Bounce events: GetItem to check current `bounceStatus`; hard bounce → set `"hard"` and `statusGsi="bounced"`; soft bounce → set `"soft"`, or upgrade to `"hard"` if already `"soft"`
    - Return 200 to SNS on all outcomes (prevent retries)
    - _Requirements: 11.2, 11.3, 11.4, 14.1, 14.2, 14.3, 14.4_

  - [x] 6.2 Add SesEventTrackingFunction resource and IAM policy to `SamLambda/template.yml`
    - AWS::Serverless::Function with SNS event source (soulreel-ses-nurture-events topic)
    - IAM: `dynamodb:GetItem`, `dynamodb:UpdateItem` on EmailCaptureTable
    - _Requirements: 11.7, 14.5_

  - [ ]* 6.3 Write property tests for SES event tracking
    - **Property 16: SES event tracking increments correct counter**
    - **Property 17: Hard bounce marks record as undeliverable**
    - **Property 18: Soft bounce escalation to hard**
    - **Validates: Requirements 11.3, 11.4, 14.2, 14.3**

- [x] 7. Admin Email Capture Lambda function
  - [x] 7.1 Create `SamLambda/functions/adminFunctions/adminEmailCapture/app.py`
    - Implement `lambda_handler` with path-based routing for:
      - `GET /admin/email-capture/metrics`: Scan EmailCaptureTable, compute aggregated metrics (total, by-status breakdown, conversion rate, conversion-by-stage, conversion-by-source, time-to-convert stats, bounce rate)
      - `GET /admin/email-capture/emails`: Paginated list with status filtering via StatusIndex GSI
      - `POST /admin/email-capture/test-send`: Send manual reminder for a specific email at its current stage via SES
      - `PUT /admin/email-capture/config`: Update SSM parameters (schedule intervals, pause flag)
      - `GET /admin/email-capture/ab-results`: Compute per-stage A/B variant performance (open rate, click rate, conversion rate, sample size, winner indicator)
    - CORS headers, `import os` at top
    - _Requirements: 8.1–8.16, 9.4, 11.5, 11.6, 12.1–12.5, 14.6, 15.5_

  - [x] 7.2 Add AdminEmailCaptureFunction resource and IAM policy to `SamLambda/template.yml`
    - AWS::Serverless::Function with multiple API events (Cognito-authorized)
    - IAM: `dynamodb:Scan`, `dynamodb:Query` on EmailCaptureTable; `ssm:GetParameter`, `ssm:GetParameters`, `ssm:PutParameter` on `/soulreel/email-nurture/*`; `ses:SendTemplatedEmail`
    - _Requirements: 10.6_

- [x] 8. SES Email Templates
  - [x] 8.1 Define 12 SES email templates in `SamLambda/template.yml` (or a deploy script)
    - Templates: `soulreel-nurture-stage-{0-5}-{A,B}` (12 total)
    - Each template uses SoulReel brand colors (purple #7C3AED, navy #1E1B4B)
    - Each includes: sample question, CTA button linking to `https://www.soulreel.net/?signup=create-legacy`, unsubscribe link with `{{unsubscribe_url}}`, referral link with `{{referral_url}}`
    - Mobile-responsive single-column layout, 44x44px minimum touch targets
    - Template data variables: `{{email}}`, `{{unsubscribe_url}}`, `{{signup_url}}`, `{{referral_url}}`
    - Stage-specific content per requirements (welcome, founder story, social proof, urgency, final + COMEBACK20, win-back with generous incentive)
    - B variants initially identical to A
    - _Requirements: 4.1–4.13_

- [x] 9. Checkpoint — Validate all backend resources and Lambda functions
  - Ensure `sam validate --lint` passes, ask the user if questions arise.

- [x] 10. PostConfirmation modification — Conversion tracking
  - [x] 10.1 Modify `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`
    - After existing subscription creation logic, query EmailCaptureTable for the new user's email
    - If found: set `convertedAt` to current ISO-8601 timestamp, `convertedAtStage` to current `reminderStage`, `statusGsi` to `"converted"`
    - If not found: no action
    - Wrap in try/except so failures never block signup
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 10.2 Update PostConfirmation IAM policy in `SamLambda/template.yml`
    - Add `dynamodb:GetItem` and `dynamodb:UpdateItem` on EmailCaptureTable
    - _Requirements: 5.5, 10.4_

  - [ ]* 10.3 Write property test for conversion tracking
    - **Property 11: Conversion tracking updates matching records**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 11. Checkpoint — Backend complete
  - Ensure all backend Lambda functions, IAM policies, templates, and infrastructure are defined. Run `sam validate --lint`. Ask the user if questions arise.

- [x] 13. Frontend API config and EmailCaptureSection integration
  - [x] 13.1 Add email capture endpoint constants to `FrontEndCode/src/config/api.ts`
    - Add `EMAIL_CAPTURE`, `EMAIL_UNSUBSCRIBE`, `ADMIN_EMAIL_CAPTURE_METRICS`, `ADMIN_EMAIL_CAPTURE_EMAILS`, `ADMIN_EMAIL_CAPTURE_TEST_SEND`, `ADMIN_EMAIL_CAPTURE_CONFIG`, `ADMIN_EMAIL_CAPTURE_AB_RESULTS` endpoints
    - _Requirements: 2.1, 8.1, 9.4_

  - [x] 13.2 Modify `FrontEndCode/src/components/landing/EmailCaptureSection.tsx`
    - Replace console-only `trackEvent` with POST to `/email-capture` API
    - Accept `source` prop (default `"landing-page"`)
    - Add loading state: disable submit button, show spinner while request in flight
    - On 200: show "Check your inbox — your first question is on its way!", store submission flag in sessionStorage
    - On 400: show server-provided error message
    - On network error/500: show "Something went wrong. Please try again later."
    - On 429: show "Too many requests. Please try again later."
    - Continue calling `trackEvent("email_capture_submit")` after success
    - Read `ref` from sessionStorage and include as `referredBy` in request body
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 15.4_

- [x] 14. SecondaryEmailCapture component and Home.tsx changes
  - [x] 14.1 Create `FrontEndCode/src/components/landing/SecondaryEmailCapture.tsx`
    - Compact inline layout (single row: input + button)
    - Softer messaging: "Moved by this story? We'll send you a question to think about."
    - Call same API with `source: "founder-story"`
    - Check sessionStorage for prior submission; show "You're already on the list!" if already captured
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x] 14.2 Modify `FrontEndCode/src/pages/Home.tsx`
    - Read `?ref=` query parameter on mount and store in sessionStorage
    - Insert `<SecondaryEmailCapture />` between FounderStorySection and ClosingCTASection
    - _Requirements: 13.1, 15.3_

- [x] 15. HeroSection auto-open signup modal from email links
  - [x] 15.1 Modify `FrontEndCode/src/components/landing/HeroSection.tsx`
    - Read `?signup=` query parameter on mount via `useSearchParams`
    - If `signup=create-legacy`, auto-open SignupModal with `create-legacy` variant
    - If `signup=start-their-legacy`, auto-open SignupModal with `start-their-legacy` variant
    - Fire `trackEvent('signup_modal_auto_open', { variant, source: 'email' })`
    - No auto-open without `?signup` param (existing behavior preserved)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 16. Checkpoint — Frontend capture integration complete
  - Ensure frontend builds without errors (`npm run build` in FrontEndCode/). Ask the user if questions arise.

- [x] 17. Admin Email Capture page
  - [x] 17.1 Create `FrontEndCode/src/pages/admin/AdminEmailCapture.tsx` — metrics cards and funnel
    - Metrics cards: total captured, conversion rate, active nurture count, expired, unsubscribed, bounce rate
    - Funnel status section: counts and percentages at each stage (0–4), converted (with by-stage breakdown), expired, unsubscribed
    - Conversion by stage breakdown, conversion by source breakdown
    - Time to convert section: average days, median, histogram by week
    - Referrals count and referred vs non-referred conversion rate
    - _Requirements: 8.2, 8.3, 8.5, 8.11, 8.12, 8.13, 8.14, 8.15, 8.16, 15.5_

  - [x] 17.2 Add email table and management controls to AdminEmailCapture page
    - Stacked bar chart: emails by stage bucketed by capture week (using CapturedWeekIndex data)
    - Scrollable email table: email, stage, capturedAt, convertedAt, expiredAt, unsubscribedAt, bounce badge
    - "Send Test Reminder" button per email row
    - Nurture Configuration panel: stage intervals with inline edit, pause/resume toggle
    - _Requirements: 8.4, 8.6, 8.7, 8.8, 8.9, 8.10_

  - [x] 17.3 Add A/B testing section to AdminEmailCapture page
    - Open rate and click rate per stage, broken down by A/B variant
    - A/B Tests section: per-stage variant comparison (subject, open rate, click rate, conversion rate, sample size, winner indicator at 100+ sends and 5+ pp difference)
    - "Promote to Default" button, B variant subject line editor
    - _Requirements: 11.5, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 18. Admin sidebar and dashboard integration
  - [x] 18.1 Modify `FrontEndCode/src/components/AdminLayout.tsx`
    - Add "MARKETING" nav section with "Email Capture" link (Mail icon) to `/admin/email-capture`
    - _Requirements: 8.1_

  - [x] 18.2 Modify `FrontEndCode/src/pages/admin/AdminDashboard.tsx`
    - Add "Email Capture" summary card: total captured, conversion rate, active nurture count, expired, unsubscribed
    - Mini funnel indicator showing count at each active stage (0–4)
    - Card is clickable, navigates to `/admin/email-capture`
    - Fetch metrics from admin email capture metrics endpoint
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 18.3 Add admin route in `FrontEndCode/src/App.tsx`
    - Import AdminEmailCapture page
    - Add `<Route path="email-capture" element={<AdminEmailCapture />} />` under the admin route group
    - _Requirements: 8.1_

- [x] 19. Final checkpoint — Full stack validation
  - Ensure frontend builds without errors. Ensure `sam validate --lint` passes on template.yml. Ensure all tests pass. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Backend uses Python 3.12 (Hypothesis for property tests), frontend uses TypeScript (fast-check for property tests)
- All Lambda functions must include `import os` and CORS headers per project rules
- IAM policies must be scoped per function per the lambda-iam-permissions rule
- SES templates use `SendTemplatedEmail` with the `soulreel-nurture` configuration set for tracking
- The shared referral/unsubscribe utilities (task 2) must be implemented before tasks 4, 5, and 6 which import them
- Task numbering was adjusted to put shared utilities before the Lambda functions that depend on them
