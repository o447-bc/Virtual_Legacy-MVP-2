# Requirements Document

## Introduction

This feature builds a complete email capture and nurture system for SoulReel. The landing page already has an `EmailCaptureSection` component that collects email addresses but currently only logs to the console via `trackEvent`. This spec adds backend storage (DynamoDB), an immediate welcome email, a multi-stage email reminder sequence (SES + CloudWatch scheduled Lambda), conversion tracking (integrated with the existing Cognito postConfirmation trigger), unsubscribe handling, email open/click tracking, A/B testing infrastructure, a win-back email for expired leads, admin management UI with A/B test results, and abuse prevention. The system spans the full stack: React frontend, API Gateway endpoints, Lambda functions, DynamoDB, SES templates, SES notifications, and CloudWatch Events.

## Glossary

- **Email_Capture_API**: The POST `/email-capture` Lambda-backed API Gateway endpoint that accepts and stores email addresses from the landing page.
- **EmailCapture_Table**: A DynamoDB table storing captured email records with fields: `email` (partition key), `capturedAt`, `reminderStage`, `convertedAt`, `expiredAt`, `unsubscribedAt`, `convertedAtStage`, `source`, `variant`, `openCount`, `clickCount`, `lastOpenedAt`, `lastClickedAt`, `bounceStatus` (null, "soft", or "hard"), `referredBy` (email of referrer, if any).
- **Nurture_Scheduler**: A CloudWatch Events cron-triggered Lambda function that runs daily, scans the EmailCapture_Table, and sends stage-appropriate reminder emails via SES.
- **Reminder_Stage**: An integer (0–5) representing the current position in the nurture sequence. Stage 0 = welcome email sent immediately on capture, Stages 1–4 = scheduled reminder emails, Stage 5 = win-back email at 6 months. Stage 4 with `expiredAt` set = expired (before win-back).
- **Welcome_Email**: An email sent immediately upon capture (not via the daily cron) containing the promised sample question. This is the Stage 0 email.
- **Unsubscribe_Endpoint**: The GET `/email-capture/unsubscribe` API Gateway endpoint that marks an email as unsubscribed using a signed token.
- **Unsubscribe_Token**: An HMAC-signed, base64url-encoded representation of an email address used to authenticate unsubscribe requests without requiring login.
- **Conversion_Tracker**: Logic added to the existing Cognito postConfirmation Lambda that checks the EmailCapture_Table and marks matching emails as converted.
- **Admin_Email_Capture_Page**: A new React admin page at `/admin/email-capture` showing metrics, email list, and management controls for the nurture system.
- **Email_Template**: An SES email template containing SoulReel-branded HTML with a sample question, signup CTA, and unsubscribe link, one per reminder stage.
- **Rate_Limiter**: Server-side logic in the Email_Capture_API that restricts submissions to a maximum of 5 per source IP per hour.
- **SSM_Parameters**: AWS Systems Manager Parameter Store entries used to configure the reminder schedule (days between stages) and the nurture pause flag.
- **EmailCaptureSection**: The existing React component at `FrontEndCode/src/components/landing/EmailCaptureSection.tsx` that renders the email capture form on the landing page.
- **AB_Variant**: A string field ("A" or "B") assigned randomly on capture, used to split recipients into two groups for testing different email subject lines, content, or CTAs.
- **SES_Notifications**: SES event notifications (via SNS or SES event destinations) that report email open and click events back to a Lambda for tracking.
- **Win_Back_Email**: A final re-engagement email sent approximately 6 months after capture to expired leads who never converted, offering one last chance to sign up with a generous incentive.
- **Capture_Source**: A string field recording which page or section triggered the email capture (e.g., "landing-page", "discover-page", "founder-story") for future segmentation.
- **Bounce_Handler**: Logic that processes SES bounce notifications to mark hard-bounced emails as undeliverable and prevent further sends, protecting the SES sender reputation.
- **Referral_Link**: A shareable URL included in each nurture email that allows recipients to forward or share SoulReel with someone they think should preserve their story, with referral tracking.

## Requirements

### Requirement 1: Email Capture API Endpoint

**User Story:** As a landing page visitor, I want to submit my email address to receive a sample question, so that I can experience SoulReel before signing up.

#### Acceptance Criteria

1. WHEN a POST request with a valid email address is received at `/email-capture`, THE Email_Capture_API SHALL store a record in the EmailCapture_Table with the email, a `capturedAt` ISO-8601 timestamp, `reminderStage` set to 0, `convertedAt`, `expiredAt`, `unsubscribedAt` all set to null, `source` set to the value of the `source` field from the request body (defaulting to `"landing-page"` if not provided), `variant` randomly assigned as `"A"` or `"B"` (50/50 split), and `openCount`/`clickCount` set to 0.
2. WHEN a POST request contains an email that already exists in the EmailCapture_Table, THE Email_Capture_API SHALL update the existing record by setting `capturedAt` to the current timestamp and resetting `reminderStage` to 0, but SHALL preserve the original `variant` assignment.
3. WHEN a POST request contains an email that fails RFC 5322 basic format validation, THE Email_Capture_API SHALL return a 400 response with an error message indicating the email format is invalid.
4. WHEN a POST request contains no email field or an empty email field, THE Email_Capture_API SHALL return a 400 response with an error message indicating the email is required.
5. WHEN a record is successfully stored or updated, THE Email_Capture_API SHALL return a 200 response with a JSON body containing `{"success": true}`.
6. WHEN a record is successfully stored (new capture, not a re-capture), THE Email_Capture_API SHALL immediately send the Welcome_Email (Stage 0) to the captured email address via SES, containing the promised sample question. This email is sent synchronously as part of the API request, not via the daily cron.
7. WHEN a record is re-captured (email already existed), THE Email_Capture_API SHALL also send the Welcome_Email to re-deliver the sample question.
8. IF a DynamoDB write operation fails, THEN THE Email_Capture_API SHALL return a 500 response with a JSON body containing `{"success": false, "error": "Internal server error"}`.
9. IF the Welcome_Email SES send fails, THE Email_Capture_API SHALL still return a 200 success response (the capture was stored) but SHALL log the SES error for monitoring.
10. THE Email_Capture_API SHALL include the `Access-Control-Allow-Origin` header set to the value of the `ALLOWED_ORIGIN` environment variable in every response.
11. THE Email_Capture_API SHALL be defined as an `AWS::Serverless::Function` resource in `SamLambda/template.yml` with an API event source for `POST /email-capture`.

### Requirement 2: Frontend Email Capture Integration

**User Story:** As a landing page visitor, I want the email form to actually save my email to the backend, so that I receive the promised sample question.

#### Acceptance Criteria

1. WHEN the user submits the email form in the EmailCaptureSection, THE EmailCaptureSection SHALL send a POST request to the Email_Capture_API with the entered email address and a `source` field indicating where the capture occurred (e.g., `"landing-page"`, `"discover-page"`, `"founder-story"`) in the request body.
2. WHEN the Email_Capture_API returns a 200 success response, THE EmailCaptureSection SHALL display a confirmation message such as "Check your inbox — your first question is on its way!" to set the expectation that a welcome email is coming immediately.
3. WHEN the Email_Capture_API returns a 400 error response, THE EmailCaptureSection SHALL display the server-provided error message to the user.
4. IF the Email_Capture_API request fails due to a network error or 500 response, THEN THE EmailCaptureSection SHALL display a generic error message asking the user to try again later.
5. WHILE the POST request is in flight, THE EmailCaptureSection SHALL disable the submit button and show a loading indicator to prevent duplicate submissions.
6. THE EmailCaptureSection SHALL continue to call `trackEvent("email_capture_submit")` after a successful API submission for analytics continuity.

### Requirement 3: Email Reminder Nurture Sequence

**User Story:** As a product owner, I want captured emails to receive a timed sequence of reminder emails with sample questions, so that visitors are encouraged to sign up over time.

#### Acceptance Criteria

1. THE Nurture_Scheduler SHALL be triggered by a CloudWatch Events cron rule that fires once daily.
2. WHEN the Nurture_Scheduler runs, THE Nurture_Scheduler SHALL scan the EmailCapture_Table for all records where `convertedAt` is null, `expiredAt` is null, `unsubscribedAt` is null, and `bounceStatus` is not `"hard"`.
3. WHEN a record has `reminderStage` 0 and `capturedAt` is at least 7 days ago, THE Nurture_Scheduler SHALL send the Stage 1 reminder email and update `reminderStage` to 1.
4. WHEN a record has `reminderStage` 1 and `capturedAt` is at least 14 days ago, THE Nurture_Scheduler SHALL send the Stage 2 reminder email and update `reminderStage` to 2.
5. WHEN a record has `reminderStage` 2 and `capturedAt` is at least 28 days ago, THE Nurture_Scheduler SHALL send the Stage 3 reminder email and update `reminderStage` to 3.
6. WHEN a record has `reminderStage` 3 and `capturedAt` is at least 56 days ago, THE Nurture_Scheduler SHALL send the Stage 4 (final) reminder email and update `reminderStage` to 4.
7. WHEN a record has `reminderStage` 4 and `capturedAt` is at least 56 days ago, THE Nurture_Scheduler SHALL set `expiredAt` to the current timestamp and send no further emails until the win-back stage.
8. THE Nurture_Scheduler SHALL read the reminder schedule intervals (days between stages) from SSM_Parameters, falling back to the default intervals (7, 14, 28, 56) if the parameters are not set.
9. THE Nurture_Scheduler SHALL select the email template that matches both the current stage AND the record's `variant` field (e.g., `stage-1-A` or `stage-1-B`). If no B variant template exists for a stage, THE Nurture_Scheduler SHALL fall back to the A variant template.
10. THE Nurture_Scheduler SHALL use SES `SendTemplatedEmail` to send each reminder using the selected stage-and-variant-specific Email_Template.
11. IF an SES send operation fails for a specific email, THEN THE Nurture_Scheduler SHALL log the error and continue processing the remaining emails without updating that record's `reminderStage`.
12. THE Nurture_Scheduler SHALL be defined as an `AWS::Serverless::Function` resource in `SamLambda/template.yml` with a `Schedule` event source.
13. WHILE the SSM parameter `/soulreel/email-nurture/paused` is set to `"true"`, THE Nurture_Scheduler SHALL skip all processing and exit immediately.
14. WHEN a record has `expiredAt` set and `capturedAt` is at least 180 days (approximately 6 months) ago, and `convertedAt` is null and `unsubscribedAt` is null, THE Nurture_Scheduler SHALL send the Win_Back_Email (Stage 5) and update `reminderStage` to 5. This is a one-time re-engagement attempt for expired leads.
15. WHEN a record has `reminderStage` 5, THE Nurture_Scheduler SHALL send no further emails regardless of any other conditions.

### Requirement 4: Email Templates

**User Story:** As a product owner, I want each reminder email to be branded, personal, and contain a unique sample question, so that recipients feel engaged rather than spammed.

#### Acceptance Criteria

1. THE system SHALL define Email_Templates for 6 stages (0 through 5), each with an A and B variant (12 templates total). The B variant for each stage may initially be identical to A until the admin creates a differentiated version.
2. THE Stage 0 (Welcome) Email_Template SHALL be sent immediately on capture and SHALL include: a warm welcome message, the promised sample question (e.g., "What's the bravest thing you've ever done?"), and a CTA button to sign up. Subject line example: "Your first SoulReel question is here."
3. THE Stage 1 (7-day) Email_Template SHALL include: the founder story (abbreviated), a different sample question, and a CTA. This email builds emotional connection. Subject line example: "Why I built SoulReel — and a question for you."
4. THE Stage 2 (14-day) Email_Template SHALL include: social proof messaging ("Families are using SoulReel to..."), a question from a different content path, and a CTA. Subject line example: "A question your grandchildren will thank you for."
5. THE Stage 3 (28-day) Email_Template SHALL include: urgency-based copy tied to the product's inherent time-sensitivity ("Stories don't wait"), a compelling question, and a CTA. Subject line example: "Every day holds stories worth preserving."
6. THE Stage 4 (56-day / final) Email_Template SHALL include: a gentle, non-pushy closing message, one more question, the COMEBACK20 coupon code ("Here's 20% off your first 3 months"), and a CTA. Subject line example: "One last question — and a gift from us."
7. THE Stage 5 (Win-back / 6-month) Email_Template SHALL include: a brief "We're still here when you're ready" message, a fresh question, a generous incentive (e.g., "Your first month free" or 30% off — more generous than the Stage 4 COMEBACK20 since this is the last chance), and a CTA. Subject line example: "Still thinking about preserving your story? Here's a gift."
8. THE Email_Template for each stage SHALL include a call-to-action button linking to `https://www.soulreel.net/?signup=create-legacy` which will auto-open the signup modal on the landing page, keeping the user in the warm context of the site.
9. THE Email_Template for each stage SHALL include an unsubscribe link in the footer that points to the Unsubscribe_Endpoint with the recipient's Unsubscribe_Token.
10. THE Email_Template for each stage SHALL include a "Know someone who should preserve their story?" referral link in the footer that points to `https://www.soulreel.net/?ref={email_hash}` for referral tracking.
11. THE Email_Template for each stage SHALL use SoulReel brand colors (purple #7C3AED, navy #1E1B4B) in the header and CTA button.
12. THE Email_Template for each stage SHALL render correctly on mobile devices with a single-column layout and minimum touch target size of 44x44 pixels for the CTA button.
13. THE Email_Template resources SHALL be defined as `AWS::SES::Template` resources in `SamLambda/template.yml` or deployed via a setup script.

### Requirement 5: Conversion Tracking

**User Story:** As a product owner, I want to know which captured emails eventually signed up, so that I can measure the effectiveness of the nurture sequence.

#### Acceptance Criteria

1. WHEN a new user completes signup (Cognito postConfirmation trigger fires), THE Conversion_Tracker SHALL query the EmailCapture_Table for a record matching the new user's email address.
2. WHEN a matching record is found in the EmailCapture_Table, THE Conversion_Tracker SHALL update the record by setting `convertedAt` to the current ISO-8601 timestamp and `convertedAtStage` to the current `reminderStage` value.
3. WHEN no matching record is found in the EmailCapture_Table, THE Conversion_Tracker SHALL take no action and allow the postConfirmation trigger to continue normally.
4. IF the EmailCapture_Table query or update fails, THEN THE Conversion_Tracker SHALL log the error and allow the postConfirmation trigger to continue normally without blocking user signup.
5. THE existing postConfirmation Lambda function's IAM policy in `SamLambda/template.yml` SHALL be updated to include `dynamodb:GetItem` and `dynamodb:UpdateItem` permissions on the EmailCapture_Table.

### Requirement 6: Unsubscribe Handling

**User Story:** As an email recipient, I want to unsubscribe from reminder emails with one click, so that I stop receiving emails I no longer want.

#### Acceptance Criteria

1. WHEN a GET request is received at `/email-capture/unsubscribe` with a valid `token` query parameter, THE Unsubscribe_Endpoint SHALL decode the token, verify the HMAC signature, extract the email address, and set `unsubscribedAt` to the current timestamp in the EmailCapture_Table.
2. WHEN the unsubscribe operation succeeds, THE Unsubscribe_Endpoint SHALL return an HTML page displaying "You've been unsubscribed" with SoulReel branding.
3. WHEN a GET request contains an invalid or tampered token, THE Unsubscribe_Endpoint SHALL return a 400 response with an HTML page displaying "Invalid unsubscribe link".
4. WHEN a GET request contains a token for an email that does not exist in the EmailCapture_Table, THE Unsubscribe_Endpoint SHALL return the success HTML page without error (to prevent email enumeration).
5. THE Unsubscribe_Token SHALL be generated using HMAC-SHA256 with a secret stored in SSM_Parameters at `/soulreel/email-nurture/unsubscribe-secret`.
6. THE Unsubscribe_Endpoint SHALL be defined as an `AWS::Serverless::Function` resource in `SamLambda/template.yml` with an API event source for `GET /email-capture/unsubscribe` that does not require Cognito authorization.
7. THE Unsubscribe_Endpoint SHALL include the `Access-Control-Allow-Origin` header set to the value of the `ALLOWED_ORIGIN` environment variable in every response.

### Requirement 7: Rate Limiting and Abuse Prevention

**User Story:** As a system operator, I want the email capture endpoint to resist abuse, so that the system is not flooded with invalid or malicious submissions.

#### Acceptance Criteria

1. WHEN more than 5 POST requests from the same source IP address are received within a 1-hour window, THE Email_Capture_API SHALL return a 429 response with a JSON body containing `{"success": false, "error": "Too many requests. Please try again later."}`.
2. THE Email_Capture_API SHALL track request counts per IP using a DynamoDB record or in-memory mechanism with a 1-hour TTL.
3. WHEN a submitted email address belongs to a known disposable email domain (checked against a configurable blocklist), THE Email_Capture_API SHALL return a 400 response with a JSON body containing `{"success": false, "error": "Please use a permanent email address."}`.
4. THE Unsubscribe_Endpoint SHALL validate the HMAC signature of the Unsubscribe_Token before performing any database operations.

### Requirement 8: Admin Email Capture Management Page

**User Story:** As an admin, I want a dedicated page to view and manage captured emails and the nurture sequence, so that I can monitor performance and troubleshoot issues.

#### Acceptance Criteria

1. THE Admin_Email_Capture_Page SHALL be accessible at the route `/admin/email-capture` and appear in the admin sidebar under a new "MARKETING" section with the label "Email Capture".
2. THE Admin_Email_Capture_Page SHALL display the total count of captured emails.
3. THE Admin_Email_Capture_Page SHALL display a breakdown of emails by current status: new (stage 0), 1-week (stage 1), 2-week (stage 2), 4-week (stage 3), 8-week (stage 4), converted, expired, and unsubscribed.
4. THE Admin_Email_Capture_Page SHALL display a stacked bar chart showing the count of emails in each stage, bucketed by week of capture.
5. THE Admin_Email_Capture_Page SHALL display the conversion rate calculated as (count of converted emails / total captured emails) × 100, shown as a percentage.
6. THE Admin_Email_Capture_Page SHALL display a scrollable table of captured emails showing: email address, current stage, `capturedAt` date, `convertedAt` date, `expiredAt` date, and `unsubscribedAt` date.
7. WHEN the admin clicks a "Send Test Reminder" button for a specific email, THE Admin_Email_Capture_Page SHALL trigger a manual reminder send for that email at its current stage via an admin API endpoint.
8. THE Admin_Email_Capture_Page SHALL provide controls to update the reminder schedule intervals (days between stages) by writing to SSM_Parameters.
9. THE Admin_Email_Capture_Page SHALL provide a toggle to pause or resume the entire nurture sequence by writing to the SSM parameter `/soulreel/email-nurture/paused`.
10. THE Admin_Email_Capture_Page SHALL display a "Nurture Configuration" panel showing the current email callback times for each stage (e.g., "Stage 1: 7 days, Stage 2: 14 days, Stage 3: 28 days, Stage 4: 56 days") read from SSM_Parameters, with inline edit controls to change each value.
11. THE Admin_Email_Capture_Page SHALL display a "Funnel Status" section showing a horizontal funnel visualization or summary table with the count of users currently at each phase:
    - Captured (stage 0, waiting for first reminder)
    - 7-day reminder sent (stage 1)
    - 14-day reminder sent (stage 2)
    - 28-day reminder sent (stage 3)
    - 56-day / final reminder sent (stage 4)
    - Converted (signed up after receiving reminders, with breakdown by which stage they converted at)
    - Expired (completed all reminders without converting)
    - Unsubscribed (opted out at any stage)
12. THE Admin_Email_Capture_Page SHALL display the "Funnel Status" counts as both absolute numbers and percentages of total captured.
13. THE Admin_Email_Capture_Page SHALL display a "Conversion by Stage" breakdown showing how many users converted at each reminder stage (e.g., "Converted after Stage 1: 12, after Stage 2: 8, after Stage 3: 3, after Stage 4: 1") to help identify which reminder is most effective.
14. THE Admin_Email_Capture_Page SHALL display a "Conversion by Source" breakdown showing conversion rates for each capture source (e.g., "landing-page: 5.2%, discover-page: 8.1%, founder-story: 7.4%") to identify which capture points are most effective.
15. THE Admin_Email_Capture_Page SHALL display a "Time to Convert" section showing: the average number of days from capture to conversion, a histogram of conversion times bucketed by week (e.g., "Week 1: 15 conversions, Week 2: 8, Week 3: 4..."), and the median time-to-convert. This helps determine if the reminder timing is optimal.
16. THE Admin_Email_Capture_Page SHALL display a "Bounce Rate" indicator showing the percentage of emails that hard-bounced, and a count of emails marked as undeliverable.

### Requirement 9: Admin Dashboard Integration

**User Story:** As an admin, I want to see email capture metrics at a glance on the main dashboard, so that I can quickly assess the health of the nurture funnel without navigating to a separate page.

#### Acceptance Criteria

1. THE AdminDashboard SHALL display an "Email Capture" summary card showing: total captured count, conversion rate percentage, count of emails in active nurture (stages 0–4, not expired/unsubscribed), count of expired emails, and count of unsubscribed emails.
2. THE AdminDashboard "Email Capture" card SHALL display a mini funnel indicator showing the count at each active stage (0 through 4) as small labeled numbers or a compact horizontal bar, so the admin can see at a glance where users are in the pipeline.
3. WHEN the admin clicks the "Email Capture" summary card, THE AdminDashboard SHALL navigate to the Admin_Email_Capture_Page at `/admin/email-capture`.
4. THE AdminDashboard SHALL fetch email capture metrics from a new admin API endpoint that returns aggregated counts by stage, conversion counts by stage, and totals.

### Requirement 10: IAM Permissions

**User Story:** As a DevOps engineer, I want all Lambda functions to have precisely scoped IAM permissions, so that the system follows the principle of least privilege.

#### Acceptance Criteria

1. THE Email_Capture_API Lambda's IAM policy in `SamLambda/template.yml` SHALL grant `dynamodb:PutItem`, `dynamodb:GetItem`, and `dynamodb:UpdateItem` on the EmailCapture_Table resource, and `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem` on the RateLimitTable resource.
2. THE Nurture_Scheduler Lambda's IAM policy in `SamLambda/template.yml` SHALL grant `dynamodb:Scan` and `dynamodb:UpdateItem` on the EmailCapture_Table resource, and `ses:SendEmail` and `ses:SendTemplatedEmail` on the SES identity resource.
3. THE Nurture_Scheduler Lambda's IAM policy in `SamLambda/template.yml` SHALL grant `ssm:GetParameter` and `ssm:GetParameters` on the `/soulreel/email-nurture/*` parameter path.
4. THE existing postConfirmation Lambda's IAM policy in `SamLambda/template.yml` SHALL be updated to include `dynamodb:GetItem` and `dynamodb:UpdateItem` on the EmailCapture_Table resource.
5. THE Unsubscribe_Endpoint Lambda's IAM policy in `SamLambda/template.yml` SHALL grant `dynamodb:UpdateItem` on the EmailCapture_Table resource and `ssm:GetParameter` on `/soulreel/email-nurture/unsubscribe-secret`.
6. THE admin API endpoint Lambda's IAM policy SHALL grant `dynamodb:Scan` and `dynamodb:Query` on the EmailCapture_Table resource, `ssm:GetParameter`, `ssm:GetParameters`, and `ssm:PutParameter` on the `/soulreel/email-nurture/*` parameter path, and `ses:SendTemplatedEmail` for the test reminder feature.
7. THE Email_Capture_API Lambda's IAM policy SHALL additionally grant `ses:SendTemplatedEmail` for sending the immediate Welcome_Email on capture, and `ssm:GetParameter` on `/soulreel/email-nurture/unsubscribe-secret` and `/soulreel/email-nurture/disposable-domains` for runtime reads.

---

### Requirement 11: Email Open and Click Tracking

**User Story:** As a product owner, I want to know if recipients are opening and clicking my nurture emails, so that I can identify whether low conversion is a subject line problem (low opens) or a content/CTA problem (low clicks).

#### Acceptance Criteria

1. ALL emails sent via the nurture system (Welcome through Win-back) SHALL be sent with SES open tracking enabled (tracking pixel) and click tracking enabled (redirect links).
2. THE system SHALL configure an SES event destination (via SNS topic or SES configuration set) that delivers open and click events to a Lambda function.
3. WHEN an open event is received, THE tracking Lambda SHALL increment the `openCount` field and update `lastOpenedAt` on the matching EmailCapture_Table record.
4. WHEN a click event is received, THE tracking Lambda SHALL increment the `clickCount` field and update `lastClickedAt` on the matching EmailCapture_Table record.
5. THE Admin_Email_Capture_Page SHALL display open rate (emails with openCount > 0 / total sent) and click rate (emails with clickCount > 0 / total sent) for each stage.
6. THE Admin_Email_Capture_Page SHALL display open and click rates broken down by A/B variant for each stage, so the admin can compare variant performance.
7. THE tracking Lambda's IAM policy SHALL grant `dynamodb:UpdateItem` on the EmailCapture_Table resource.

---

### Requirement 12: A/B Testing Management

**User Story:** As an admin, I want to create and manage A/B test variants for each email stage, so that I can optimize subject lines and content based on real performance data.

#### Acceptance Criteria

1. THE Admin_Email_Capture_Page SHALL include an "A/B Tests" section showing, for each stage: the A variant subject line, the B variant subject line, and a side-by-side comparison of open rate, click rate, and conversion rate for each variant.
2. THE Admin_Email_Capture_Page SHALL display the sample size (number of emails sent) for each variant at each stage.
3. WHEN one variant has a statistically meaningful advantage (at least 100 sends per variant and a difference of 5+ percentage points in open or click rate), THE Admin_Email_Capture_Page SHALL display a "Winner" indicator next to the better-performing variant.
4. THE Admin_Email_Capture_Page SHALL provide a "Promote to Default" button that, when clicked, copies the winning variant's template content to the A variant and resets the B variant to match A (preparing for the next test).
5. THE Admin_Email_Capture_Page SHALL provide an interface to edit the B variant's subject line and preview the email body for each stage. Editing the B variant SHALL update the corresponding SES template via an admin API endpoint.
6. THE A/B variant assignment SHALL happen once at capture time and remain fixed for the lifetime of that email record, ensuring each recipient sees a consistent experience across all stages.

---

### Requirement 13: Secondary Email Capture Placement

**User Story:** As a product owner, I want an additional email capture prompt after the founder story section, so that emotionally moved visitors who aren't ready to sign up can still be captured.

#### Acceptance Criteria

1. THE Landing_Page SHALL display a secondary email capture prompt directly after the FounderStorySection, before the ClosingCTASection.
2. THE secondary email capture prompt SHALL use a softer, more emotionally resonant message such as "Moved by this story? We'll send you a question to think about." instead of the primary EmailCaptureSection's "Not ready yet?" messaging.
3. THE secondary email capture prompt SHALL use the same Email_Capture_API endpoint as the primary EmailCaptureSection, with `source` set to `"founder-story"`.
4. THE secondary email capture prompt SHALL use a compact, inline layout (single row: input + button) that does not duplicate the visual weight of the primary EmailCaptureSection.
5. IF the user has already submitted an email via the primary EmailCaptureSection in the same session, THE secondary prompt SHALL display "You're already on the list!" instead of the form.

---

### Requirement 14: SES Bounce Handling

**User Story:** As a system operator, I want hard-bounced emails to be automatically marked as undeliverable, so that the SES sender reputation is protected and no further emails are wasted on invalid addresses.

#### Acceptance Criteria

1. THE system SHALL configure an SES event destination (via the same SNS topic or SES configuration set used for open/click tracking) that delivers bounce events to a Lambda function.
2. WHEN a hard bounce event is received (permanent delivery failure — invalid address, domain doesn't exist), THE Bounce_Handler SHALL set `bounceStatus` to `"hard"` on the matching EmailCapture_Table record.
3. WHEN a soft bounce event is received (temporary delivery failure — mailbox full, server unavailable), THE Bounce_Handler SHALL set `bounceStatus` to `"soft"` on the matching EmailCapture_Table record. The Nurture_Scheduler SHALL still attempt to send to soft-bounced emails on the next cycle; if a second soft bounce occurs, THE Bounce_Handler SHALL upgrade `bounceStatus` to `"hard"`.
4. WHEN a record has `bounceStatus` set to `"hard"`, THE Nurture_Scheduler SHALL skip that record and send no further emails.
5. THE Bounce_Handler Lambda's IAM policy SHALL grant `dynamodb:GetItem` and `dynamodb:UpdateItem` on the EmailCapture_Table resource.
6. THE Admin_Email_Capture_Page SHALL display hard-bounced emails in the email table with a visual indicator (e.g., red "Bounced" badge) and SHALL exclude them from active nurture counts.

---

### Requirement 15: Referral Tracking

**User Story:** As a product owner, I want nurture email recipients to be able to share SoulReel with someone they think should preserve their story, so that I can amplify reach through word-of-mouth at zero cost.

#### Acceptance Criteria

1. EACH nurture email SHALL include a "Know someone who should preserve their story? Share this with them" section in the footer with a referral link.
2. THE referral link SHALL point to `https://www.soulreel.net/?ref={referrer_hash}` where `referrer_hash` is a short, non-reversible hash of the referrer's email address.
3. WHEN a visitor arrives at the landing page with a `?ref=` query parameter, THE Landing_Page SHALL store the referrer hash in sessionStorage.
4. WHEN that visitor subsequently submits the email capture form, THE EmailCaptureSection SHALL include the `referredBy` hash in the POST request body, and THE Email_Capture_API SHALL store it on the EmailCapture_Table record.
5. THE Admin_Email_Capture_Page SHALL display a "Referrals" count showing how many captured emails came via referral links, and the conversion rate of referred vs non-referred captures.
6. THE referral tracking SHALL NOT expose the referrer's actual email address — only the hash is stored and displayed.

---

### Requirement 16: Landing Page Auto-Open Signup Modal from Email Links

**User Story:** As a nurture email recipient clicking the signup CTA, I want to land on the SoulReel landing page with the signup form already open, so that I can sign up immediately without an extra click.

#### Acceptance Criteria

1. WHEN the Landing_Page loads with a `?signup=create-legacy` query parameter, THE Landing_Page SHALL automatically open the Signup_Modal with the `create-legacy` variant.
2. WHEN the Landing_Page loads with a `?signup=start-their-legacy` query parameter, THE Landing_Page SHALL automatically open the Signup_Modal with the `start-their-legacy` variant.
3. WHEN the Landing_Page loads without a `?signup` query parameter, THE Landing_Page SHALL NOT auto-open any modal (existing behavior).
4. THE auto-open behavior SHALL be implemented in the HeroSection component by reading the query parameter on mount via `useSearchParams` and setting the modal state accordingly.
5. THE auto-open SHALL fire `trackEvent('signup_modal_auto_open', { variant, source: 'email' })` to distinguish email-driven modal opens from manual CTA clicks.

---

### Future Enhancement Note: Email Preference Center

> **Not in scope for this spec**, but noted for future consideration: An email preference center (linked from the email footer alongside unsubscribe) that lets recipients choose "send me less often" or "only send me the important ones" would reduce unsubscribes while keeping leads warm. This is a "soft no" instead of a hard no. Consider implementing this when the nurture system has been running for 3+ months and unsubscribe rates are measurable.
