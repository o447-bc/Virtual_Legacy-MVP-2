# Requirements Document

## Introduction

SoulReel is a legacy preservation platform where users record deeply personal, irreplaceable video responses to AI-guided interview questions. The platform's core value proposition is that content outlives the creator — benefactors (family, friends) receive access to these recordings as a digital legacy. This makes SoulReel's data retention policy fundamentally different from typical SaaS: deleting a user's data could mean permanently destroying irreplaceable life stories, memories of deceased loved ones, and reflections on major life events.

Currently, SoulReel has no formal data retention policy, no data export capability, no account deletion workflow, no dormant account handling, and no explicit plan for what happens to content when a creator dies and their subscription lapses. The pricing page states "Your stories are always yours — all recordings remain accessible regardless of your plan" and the existing subscription system reverts lapsed users to the Free tier while preserving content access. However, there is no system for long-term storage cost optimization, regulatory compliance (GDPR Article 17/20, CCPA), or the critical scenario where a legacy maker passes away and their payment method stops working.

This feature introduces a comprehensive data retention, export, and account lifecycle policy system covering: self-service data export packaging, tiered storage lifecycle management (S3 Standard → Intelligent-Tiering → Glacier), GDPR/CCPA-compliant account deletion with grace periods, dormant account detection and re-engagement, a "Legacy Protection" mode for deceased creators that preserves benefactor access indefinitely, and cost modeling for sustainable long-term storage at scale.

## Glossary

- **Data_Export_Service**: A Lambda function that packages a user's complete content (videos, transcripts, summaries, metadata) into a downloadable archive and generates a time-limited presigned download URL. Triggered by user request or automated lifecycle events.
- **Storage_Lifecycle_Manager**: A scheduled Lambda function that applies S3 lifecycle transitions, monitors storage costs per user, and manages retrieval requests for archived content.
- **Account_Deletion_Service**: A Lambda function that processes account deletion requests with a configurable grace period, handles cascading data removal across S3 and DynamoDB, and manages benefactor access revocation.
- **Dormant_Account_Detector**: A scheduled Lambda function that identifies accounts with no login activity beyond configurable thresholds and triggers re-engagement email sequences via SES.
- **Legacy_Protection_Service**: A system that detects when a creator's account enters a post-mortem state (subscription lapsed with no login activity beyond a configurable threshold, or explicitly marked by a benefactor/executor) and transitions the account to a protected mode where content is preserved indefinitely for benefactors at minimal storage cost.
- **Retrieval_Queue**: A DynamoDB-backed queue that manages asynchronous retrieval requests for content that has been moved to S3 Glacier, notifying benefactors when content becomes available.
- **Legacy_Maker**: A user with `persona_type` of `legacy_maker` who creates video responses and AI conversations. The primary content creator.
- **Benefactor**: A user with `persona_type` of `legacy_benefactor` who has been granted access to view a Legacy_Maker's content.
- **Content_Package**: A ZIP archive containing all of a user's videos, transcripts, AI conversation summaries, and a metadata manifest file in JSON format.
- **Grace_Period**: A configurable time window (default 30 days) between an account deletion request and permanent data removal, during which the user can cancel the deletion.
- **Dormancy_Threshold**: Configurable time periods (6 months, 12 months, 24 months) after which an account with no login activity triggers escalating re-engagement actions.
- **Legacy_Protection_Mode**: An account state where the Legacy_Maker's content is preserved indefinitely for benefactor access, storage is transitioned to the lowest-cost tier, and no deletion or archival actions are taken against the content. The account is exempt from dormant account cleanup.
- **DataRetentionDB**: A new DynamoDB table that tracks data export requests, deletion requests with grace period status, dormancy state, legacy protection status, and storage retrieval queue entries per user.
- **Storage_Tier**: The S3 storage class for a user's content: Standard (first 30 days), Intelligent-Tiering (30+ days, auto-managed), or Glacier Deep Archive (content in Legacy_Protection_Mode older than 365 days with no benefactor access in 180 days).

## Requirements

### Requirement 1: Self-Service Data Export

**User Story:** As a Premium legacy maker, I want to download all my content (videos, transcripts, summaries) as a single package, so that I have a personal backup of my irreplaceable life stories.

#### Acceptance Criteria

1. THE Data_Export_Service SHALL expose a POST endpoint at `/data/export-request` on the existing API Gateway with Cognito authorization.
2. WHEN a legacy maker requests a data export, THE Data_Export_Service SHALL create a Content_Package containing all video files from S3 under the user's `conversations/` and `user-responses/` prefixes, all transcript text, all AI conversation summaries, and a `manifest.json` file listing every included item with its original filename, creation date, question text, and content category.
3. WHEN the Content_Package is assembled, THE Data_Export_Service SHALL upload the archive to a temporary S3 location with a 7-day expiration lifecycle rule and return a presigned download URL valid for 72 hours.
4. THE Data_Export_Service SHALL only be available to users with an active Premium subscription (monthly or annual). IF a user on the Free tier or with a lapsed subscription requests a data export, THEN THE Data_Export_Service SHALL return HTTP 403 with `{ "error": "Data export requires an active Premium subscription", "upgradeUrl": "/pricing" }`.
5. WHEN a data export is requested, THE Data_Export_Service SHALL create a record in DataRetentionDB with the request timestamp, status (pending, processing, ready, expired, failed), and the presigned URL when ready.
6. WHEN the Content_Package is ready, THE Data_Export_Service SHALL send an email via SES to the user's registered email address containing the download link and an expiration notice.
7. IF any content files are stored in S3 Glacier or Glacier Deep Archive, THEN THE Data_Export_Service SHALL initiate a retrieval request, set the export status to pending_retrieval, and notify the user that the export will be available within 12 hours.
8. THE Data_Export_Service SHALL limit each user to one active export request at a time to prevent abuse and excessive S3 egress costs.
9. THE Data_Export_Service SHALL include a `README.txt` file in the Content_Package explaining the archive contents, file organization, and how to view the included media files.

### Requirement 2: Automated Export on Subscription Cancellation

**User Story:** As a legacy maker who cancels my subscription, I want to automatically receive a download link for all my content, so that I have peace of mind that my stories are safe even if I leave the platform.

#### Acceptance Criteria

1. WHEN a user's Premium subscription status changes to canceled (via Stripe webhook `customer.subscription.deleted`), THE Data_Export_Service SHALL automatically initiate a final Content_Package export for that user as a courtesy before their export access ends.
2. WHEN the automated export is ready, THE Data_Export_Service SHALL send an email via SES with the subject line "Your SoulReel Legacy — Download Your Stories" containing the presigned download URL, a note that the link expires in 72 hours, and a reassurance message that all content remains accessible on the platform.
3. THE automated export email SHALL include a re-subscription call-to-action link pointing to the Pricing_Page.
4. IF the user has already requested a manual export within the past 24 hours, THEN THE Data_Export_Service SHALL skip the automated export and reference the existing export in the cancellation email instead.

### Requirement 3: S3 Storage Lifecycle Management

**User Story:** As a system operator, I want user content to automatically transition to cheaper storage tiers based on access patterns, so that storage costs remain sustainable at scale without degrading the experience for active users and benefactors.

#### Acceptance Criteria

1. THE Storage_Lifecycle_Manager SHALL apply S3 Intelligent-Tiering to all objects under the `conversations/` and `user-responses/` prefixes in the `virtual-legacy` bucket after 30 days from object creation.
2. WHILE a user's account is in Legacy_Protection_Mode and the user's content has not been accessed by any benefactor in 180 days, THE Storage_Lifecycle_Manager SHALL transition that user's content to S3 Glacier Deep Archive after 365 days from the last benefactor access.
3. THE Storage_Lifecycle_Manager SHALL maintain a per-user storage usage record in DataRetentionDB tracking total bytes stored, current storage tier distribution, and estimated monthly cost.
4. WHEN content is transitioned to Glacier Deep Archive, THE Storage_Lifecycle_Manager SHALL update the content's metadata in DynamoDB to include the storage tier and the estimated retrieval time.
5. THE Storage_Lifecycle_Manager SHALL run as a scheduled Lambda triggered by EventBridge weekly to reconcile storage tier records and identify candidates for archival transitions.
6. WHEN a previously dormant or lapsed user reactivates their account by subscribing to a Premium plan, THE Storage_Lifecycle_Manager SHALL initiate a bulk S3 RestoreObject request for all of the user's content that is currently in Glacier or Glacier Deep Archive, using Standard retrieval tier (3-5 hours for Glacier Deep Archive).
7. WHEN a reactivation restore is initiated, THE Storage_Lifecycle_Manager SHALL create a record in DataRetentionDB with recordType `reactivation_restore`, tracking the total number of objects to restore, the number restored so far, and the estimated completion time.
8. WHEN all objects for a reactivation restore are restored to S3 Standard, THE Storage_Lifecycle_Manager SHALL copy the restored objects to S3 Standard storage class (replacing the Glacier-archived versions), update the storage tier metadata in DynamoDB, and send an email via SES to the user confirming that all their content is now fully accessible.
9. WHILE a reactivation restore is in progress, THE system SHALL allow the user to access any content that has already been restored, and SHALL show the retrieval status (per Requirement 4) for content still pending restoration.

### Requirement 4: Glacier Content Retrieval for Benefactors

**User Story:** As a benefactor trying to watch a video that has been archived to cold storage, I want to be notified that the video is being retrieved and receive an alert when it is ready, so that I understand the delay and can return to view the content.

#### Acceptance Criteria

1. WHEN a benefactor requests playback of a video that is stored in S3 Glacier or Glacier Deep Archive, THE system SHALL detect the storage class before generating a presigned URL.
2. WHEN archived content is detected, THE system SHALL return an HTTP 202 response with a JSON body containing `{ "status": "retrieving", "estimatedMinutes": <estimate>, "message": "This recording is being retrieved from our archive. We'll email you when it's ready." }` instead of a playback URL.
3. WHEN archived content is detected, THE system SHALL initiate an S3 RestoreObject request with Expedited retrieval tier (1-5 minutes) for Intelligent-Tiering archive access tiers, or Standard retrieval tier (3-5 hours) for Glacier Deep Archive.
4. THE system SHALL create a Retrieval_Queue entry in DataRetentionDB with the benefactor's user ID, the content S3 key, the retrieval tier, the estimated completion time, and a status of pending.
5. WHEN the S3 restore completes (detected via S3 Event Notification or periodic polling), THE system SHALL update the Retrieval_Queue entry status to ready and send an email via SES to the benefactor with a direct link to the now-available content.
6. THE Retrieval_Queue entry SHALL expire and be cleaned up 24 hours after the content becomes available.

### Requirement 5: GDPR/CCPA-Compliant Account Deletion

**User Story:** As a legacy maker, I want to request permanent deletion of my account and all associated data, so that I can exercise my right to erasure under GDPR Article 17 and CCPA.

#### Acceptance Criteria

1. THE Account_Deletion_Service SHALL expose a POST endpoint at `/account/delete-request` on the existing API Gateway with Cognito authorization.
2. WHEN a deletion request is received, THE Account_Deletion_Service SHALL create a record in DataRetentionDB with the request timestamp, a Grace_Period end date (30 days from request), and a status of pending.
3. DURING the Grace_Period, THE Account_Deletion_Service SHALL NOT delete any data. THE user SHALL be able to cancel the deletion by calling a POST endpoint at `/account/cancel-deletion`.
4. WHEN a deletion request is created, THE Account_Deletion_Service SHALL send a confirmation email via SES to the user containing: the deletion request date, the Grace_Period end date, instructions for canceling the deletion, and a reminder that deletion is permanent and irreversible.
5. WHEN the Grace_Period expires, THE Account_Deletion_Service SHALL permanently delete all of the user's content from S3 (all objects under the user's prefixes in `conversations/` and `user-responses/`), all user records from DynamoDB tables (userQuestionStatusDB, userQuestionLevelProgressDB, userStatusDB, UserSubscriptionsDB, DataRetentionDB, ConversationStateDB), and the Cognito user account.
6. WHEN the user's data is deleted, THE Account_Deletion_Service SHALL revoke all benefactor access to the deleted user's content by removing the relevant assignment records from the assignments DynamoDB table.
7. WHEN benefactor access is revoked due to creator deletion, THE Account_Deletion_Service SHALL send an email via SES to each affected benefactor explaining that the legacy maker has deleted their account and the shared content is no longer available.
8. THE Account_Deletion_Service SHALL log a deletion audit record (user ID hash, deletion timestamp, data categories deleted) to a separate audit log that does not contain any personal data, retained for 3 years for regulatory compliance.
9. IF the user has an active Stripe subscription, THEN THE Account_Deletion_Service SHALL cancel the Stripe subscription before proceeding with data deletion.
10. THE Account_Deletion_Service SHALL process pending deletions via a daily EventBridge-triggered scan of DataRetentionDB for records where the Grace_Period has expired and status is pending.

### Requirement 6: GDPR Data Portability (Article 20)

**User Story:** As a legacy maker, I want to export my data in a structured, commonly used, machine-readable format, so that I can exercise my right to data portability under GDPR Article 20.

#### Acceptance Criteria

1. THE Data_Export_Service SHALL support two export tiers: a lightweight GDPR portability export available to all users regardless of subscription status, and a full Content_Package export available only to Premium subscribers (per Requirement 1, AC 4).
2. THE lightweight GDPR portability export SHALL produce a `data-portability.json` file containing all user-provided data in a structured JSON format: user profile information (name, email), all question responses with timestamps, all transcript text, all AI conversation summaries, benefactor list (names and email addresses), subscription history, and account creation date. This export SHALL NOT include video or audio files.
3. THE lightweight GDPR portability export SHALL be triggered via a POST endpoint at `/data/gdpr-export` on the existing API Gateway with Cognito authorization, available to users on any plan tier including Free and lapsed subscriptions.
4. THE full Content_Package export (Requirement 1) SHALL include the `data-portability.json` file in addition to all video files in their original recorded format (WebM or MP4) without transcoding or quality reduction.
5. THE `data-portability.json` file SHALL use a documented JSON schema that is self-describing, with field names that are human-readable and a schema version identifier at the root level.
6. THE Data_Export_Service SHALL complete either export tier within 30 days of the request, in compliance with GDPR Article 20 timelines.
7. THE lightweight GDPR portability export SHALL NOT require retrieval from Glacier storage since it contains only text-based data stored in DynamoDB.

### Requirement 7: Dormant Account Detection and Re-engagement

**User Story:** As a product owner, I want to identify accounts that have been inactive for extended periods and send re-engagement communications, so that users are reminded of their legacy content and given the opportunity to return before any lifecycle actions are taken.

#### Acceptance Criteria

1. THE Dormant_Account_Detector SHALL run as a scheduled Lambda triggered by EventBridge weekly.
2. WHEN an account has had no login activity for 6 months, THE Dormant_Account_Detector SHALL send a re-engagement email via SES with the subject "Your stories are waiting for you" containing a summary of the user's content (number of recordings, number of benefactors), a direct login link, and an emotional reminder of the value of their preserved memories.
3. WHEN an account has had no login activity for 12 months, THE Dormant_Account_Detector SHALL send a second re-engagement email via SES with the subject "Don't let your legacy go silent" containing the same content summary plus a notice that the account may be considered for Legacy_Protection_Mode evaluation.
4. WHEN an account has had no login activity for 24 months and the subscription has been lapsed for at least 12 months, THE Dormant_Account_Detector SHALL flag the account for Legacy_Protection_Mode evaluation in DataRetentionDB.
5. THE Dormant_Account_Detector SHALL track the last login timestamp by reading the `lastLoginAt` attribute from the userStatusDB table.
6. THE Dormant_Account_Detector SHALL NOT send re-engagement emails to accounts that are already in Legacy_Protection_Mode.
7. THE Dormant_Account_Detector SHALL NOT delete or archive any content based solely on dormancy. Content deletion SHALL only occur through an explicit user deletion request (Requirement 5).
8. IF a dormant account user requests a data export, THE Data_Export_Service SHALL require the user to first reactivate their account by logging in and resubscribing to a Premium plan before the export can be processed. THE Data_Export_Service SHALL return HTTP 403 with `{ "error": "Please reactivate your account to export your data", "loginUrl": "/login", "upgradeUrl": "/pricing" }`.
9. THE Dormant_Account_Detector SHALL record each re-engagement email sent in DataRetentionDB to prevent duplicate sends and to maintain an audit trail.

### Requirement 8: Legacy Protection Mode for Deceased Creators

**User Story:** As a benefactor of a legacy maker who has passed away, I want continued access to their recorded stories and memories, so that the platform fulfills its core promise of preserving legacies beyond the creator's lifetime.

#### Acceptance Criteria

1. THE Legacy_Protection_Service SHALL support two activation paths: automatic activation (when an account has had no login for 24 months, subscription lapsed for 12+ months, and at least one benefactor exists) and manual activation (when a benefactor or designated executor submits a Legacy Protection request with supporting documentation).
2. WHEN Legacy_Protection_Mode is activated for an account, THE Legacy_Protection_Service SHALL set the account status to `legacy_protected` in DataRetentionDB and exempt the account from all dormant account cleanup, deletion, and archival processes.
3. WHILE an account is in Legacy_Protection_Mode, THE system SHALL maintain full benefactor access to all of the creator's content, including video playback, transcript viewing, and summary reading.
4. WHILE an account is in Legacy_Protection_Mode, THE Storage_Lifecycle_Manager SHALL transition the creator's content to the lowest-cost storage tier (Glacier Deep Archive) only after 365 days with no benefactor access, and SHALL restore content to a higher tier when a benefactor requests access (per Requirement 4).
5. THE Legacy_Protection_Service SHALL expose a POST endpoint at `/legacy/protection-request` accessible to authenticated benefactors, accepting the legacy maker's user ID and an optional reason field.
6. WHEN a manual Legacy Protection request is received from a benefactor, THE Legacy_Protection_Service SHALL verify that the requesting user is an assigned benefactor of the specified legacy maker before processing the request.
7. WHEN Legacy_Protection_Mode is activated, THE Legacy_Protection_Service SHALL send an email via SES to all assigned benefactors of the legacy maker informing them that the account is now in Legacy Protection and that their access to the creator's content is preserved indefinitely.
8. THE Legacy_Protection_Service SHALL NOT require an active subscription or payment to maintain Legacy_Protection_Mode. The cost of storing legacy-protected content in Glacier Deep Archive SHALL be absorbed by the platform as a core product commitment.
9. IF a legacy maker returns and logs in to an account that is in Legacy_Protection_Mode, THEN THE Legacy_Protection_Service SHALL deactivate Legacy_Protection_Mode, restore the account to normal status, and send a welcome-back email. IF the user subscribes to a Premium plan, THE system SHALL trigger the reactivation storage restore process (per Requirement 3, AC 6-9) to move content back from Glacier to S3 Standard.

### Requirement 9: Benefactor Access Continuity After Subscription Lapse

**User Story:** As a benefactor, I want to continue accessing a legacy maker's content even after their subscription lapses or their credit card stops working, so that shared memories remain available regardless of payment status.

#### Acceptance Criteria

1. WHEN a legacy maker's subscription status changes to canceled or past_due, THE system SHALL maintain all existing benefactor access assignments without modification.
2. WHILE a legacy maker's subscription is lapsed (canceled, past_due, or expired), THE system SHALL continue to serve all previously shared content to assigned benefactors with no degradation in playback quality or access speed for content in Standard or Intelligent-Tiering storage.
3. THE system SHALL NOT revoke benefactor access based on the legacy maker's subscription status. Benefactor access SHALL only be revoked by explicit legacy maker action (removing a benefactor) or account deletion (Requirement 5).
4. WHEN a legacy maker's subscription lapses, THE system SHALL send an email to the legacy maker reassuring them that all benefactor access is preserved and their content remains safe.

### Requirement 10: Storage Cost Monitoring and Reporting

**User Story:** As a system operator, I want visibility into per-user and aggregate storage costs, so that I can make informed decisions about pricing, retention policies, and infrastructure spending.

#### Acceptance Criteria

1. THE Storage_Lifecycle_Manager SHALL calculate and store per-user storage metrics in DataRetentionDB: total bytes stored, bytes per storage tier (Standard, Intelligent-Tiering, Glacier Deep Archive), estimated monthly cost, and number of content items.
2. THE Storage_Lifecycle_Manager SHALL calculate aggregate platform metrics: total storage across all users, total estimated monthly cost, number of accounts per lifecycle state (active, dormant, legacy_protected, pending_deletion), and average storage per user.
3. THE Storage_Lifecycle_Manager SHALL expose a GET endpoint at `/admin/storage-report` accessible only to admin users, returning the aggregate metrics and a breakdown by account lifecycle state.
4. THE Storage_Lifecycle_Manager SHALL log a weekly cost summary to CloudWatch Metrics with dimensions for storage tier and account lifecycle state, enabling CloudWatch alarms for cost anomalies.

### Requirement 11: Data Retention Audit Trail

**User Story:** As a system administrator, I want a complete audit trail of all data lifecycle events (exports, deletions, archival transitions, legacy protection activations), so that the platform can demonstrate regulatory compliance.

#### Acceptance Criteria

1. THE system SHALL log every data lifecycle event to a dedicated audit log in S3 (separate from user content) with the following fields: event type, anonymized user identifier (SHA-256 hash of user ID), timestamp, event details (action taken, data categories affected), and the initiator (user, system, or admin).
2. THE audit log SHALL be stored in a separate S3 bucket with a 3-year retention lifecycle rule and Object Lock in compliance mode to prevent premature deletion.
3. THE audit log SHALL NOT contain any personally identifiable information. User identifiers SHALL be one-way hashed before logging.
4. THE system SHALL log the following event types: export_requested, export_completed, export_failed, deletion_requested, deletion_canceled, deletion_completed, legacy_protection_activated, legacy_protection_deactivated, storage_tier_transition, dormancy_email_sent, benefactor_access_revoked, and glacier_retrieval_requested.

### Requirement 12: DataRetentionDB Table

**User Story:** As a system administrator, I want a dedicated DynamoDB table to track all data lifecycle state (export requests, deletion requests, dormancy status, legacy protection status, retrieval queue), so that lifecycle operations have a single source of truth.

#### Acceptance Criteria

1. THE DataRetentionDB table SHALL use `userId` (string, Cognito `sub`) as the partition key and `recordType` (string) as the sort key, where `recordType` values include: `export_request`, `deletion_request`, `dormancy_state`, `legacy_protection`, `retrieval_queue#{s3Key}`, and `storage_metrics`.
2. THE DataRetentionDB table SHALL use PAY_PER_REQUEST billing mode.
3. THE DataRetentionDB table SHALL use KMS server-side encryption with the existing `DataEncryptionKey` CMK.
4. THE DataRetentionDB table SHALL have Point-in-Time Recovery enabled.
5. THE DataRetentionDB table SHALL include a Global Secondary Index named `status-index` with `status` as the partition key and `updatedAt` as the sort key, to enable efficient queries for pending deletions, active retrievals, and dormant accounts.
6. THE DataRetentionDB table SHALL include a TTL attribute named `expiresAt` for automatic cleanup of completed export records and resolved retrieval queue entries.

### Requirement 13: Frontend Data & Privacy Page — Export and Deletion Controls

**User Story:** As a legacy maker, I want functional data export and account deletion controls on the Data & Privacy page, so that I can take action on my data management needs.

#### Acceptance Criteria

1. THE "Download Your Legacy" section on the `/your-data` page SHALL include a "Download My Legacy" button that triggers a data export request via POST `/data/export-request`.
2. WHEN an export is in progress, THE "Download Your Legacy" section SHALL display the export status (processing, ready with download link, or pending retrieval for archived content) instead of the export button.
3. THE "Delete Your Account" section on the `/your-data` page SHALL include a "Delete My Account" button that opens a confirmation dialog explaining the 30-day Grace_Period, the permanence of deletion, the impact on benefactor access, and requires the user to type "DELETE" to confirm.
4. WHILE a deletion request is pending (within the Grace_Period), THE "Delete Your Account" section SHALL display the scheduled deletion date and a "Cancel Deletion" button instead of the delete button.

### Requirement 14: Deletion Request Cancellation

**User Story:** As a legacy maker who requested account deletion, I want to cancel the deletion during the grace period, so that I can change my mind and keep my irreplaceable content.

#### Acceptance Criteria

1. THE Account_Deletion_Service SHALL expose a POST endpoint at `/account/cancel-deletion` on the existing API Gateway with Cognito authorization.
2. WHEN a cancellation request is received during the Grace_Period, THE Account_Deletion_Service SHALL update the deletion record status to canceled in DataRetentionDB and restore the account to its previous state.
3. WHEN a deletion is canceled, THE Account_Deletion_Service SHALL send a confirmation email via SES to the user confirming that the deletion has been canceled and their content is safe.
4. IF a cancellation request is received after the Grace_Period has expired and deletion has been executed, THEN THE Account_Deletion_Service SHALL return HTTP 410 with `{ "error": "Deletion has already been completed and cannot be reversed" }`.

### Requirement 15: Data Retention Policy Page Accessible from User Menu

**User Story:** As a legacy maker, I want to easily find and read SoulReel's data retention and storage policy from the user menu, so that I understand how my irreplaceable content is protected, stored, and preserved over time without having to search for this information.

#### Acceptance Criteria

1. THE UserMenu dropdown SHALL include a "Your Data" menu item in the Navigation Section, positioned after "Security & Privacy" and before the disabled "Settings" item.
2. THE "Your Data" menu item SHALL use a `Database` (or `HardDrive`) icon from lucide-react, consistent with the existing menu icon style.
3. WHEN the user clicks "Your Data", THE system SHALL navigate to a `/your-data` route that renders a dedicated Data & Privacy page.
4. THE Data & Privacy page SHALL include the following sections presented in clear, non-technical language:
   - "Your Stories Are Always Yours" — a trust statement explaining that all recordings remain accessible regardless of subscription status, and that content is never automatically deleted.
   - "How We Store Your Content" — an explanation of the storage lifecycle: content starts in high-performance storage, transitions to cost-optimized storage over time for inactive content, and is always retrievable (with a brief note that archived content may take a few minutes to load).
   - "Legacy Protection" — an explanation that if a legacy maker becomes permanently inactive, SoulReel preserves their content indefinitely for benefactors at no cost, fulfilling the platform's core promise.
   - "Download Your Legacy" — a description of the self-service data export feature (Premium only) with a "Download My Legacy" button that triggers a data export request (same as Requirement 13, AC 2). For Free tier users, this section SHALL display a "Download My Data (Text Only)" button for the lightweight GDPR portability export (per Requirement 6, AC 3) and a message explaining that the full export including videos is a Premium feature with an upgrade call-to-action.
   - "Delete Your Account" — a description of the account deletion process including the 30-day grace period, with a "Delete My Account" button (same as Requirement 13, AC 4).
   - "Your Rights" — a brief summary of GDPR Article 17 (right to erasure) and Article 20 (data portability) rights, and CCPA rights, with a note that SoulReel supports both.
5. THE Data & Privacy page SHALL NOT expose technical details such as S3 storage class names (Standard, Intelligent-Tiering, Glacier Deep Archive), specific cost figures, or internal system architecture. All language SHALL be user-friendly and focused on the user's experience and trust.
6. THE Data & Privacy page SHALL display the user's content summary: number of recordings, total storage used (in human-readable format, e.g., "2.3 GB"), number of benefactors with access, and account status.
7. THE Data & Privacy page SHALL be accessible to users on any plan tier, including Free and lapsed subscriptions.
8. THE "Your Data" menu item SHALL be visible to both legacy_maker and legacy_benefactor persona types. For legacy_benefactor users, the page SHALL show only the "Your Stories Are Always Yours", "Legacy Protection", and "Your Rights" sections (omitting export and deletion since benefactors don't own the content).

### Requirement 16: Export and Deletion Rate Limiting

**User Story:** As a system operator, I want rate limits on data export and deletion operations, so that the platform is protected from abuse and excessive infrastructure costs.

#### Acceptance Criteria

1. THE Data_Export_Service SHALL limit each user to a maximum of one export request per 30-day period.
2. THE Account_Deletion_Service SHALL limit each user to a maximum of one deletion request per 30-day period (to prevent repeated request-cancel cycles).
3. IF a rate limit is exceeded, THEN THE respective service SHALL return HTTP 429 with a JSON body containing `{ "error": "Rate limit exceeded", "retryAfter": "<ISO 8601 timestamp>" }`.

### Requirement 17: Testability — Time Override and Lifecycle Simulation

**User Story:** As a developer or QA tester, I want to simulate the passage of time and trigger lifecycle events on demand, so that I can verify dormancy detection, grace period expiration, storage tier transitions, and legacy protection activation without waiting months or years.

#### Acceptance Criteria

1. ALL time-based thresholds in the data retention system SHALL be configurable via SSM Parameter Store parameters under the `/soulreel/data-retention/` prefix, including:
   - `/soulreel/data-retention/dormancy-threshold-1` (default: 180 days)
   - `/soulreel/data-retention/dormancy-threshold-2` (default: 365 days)
   - `/soulreel/data-retention/dormancy-threshold-3` (default: 730 days)
   - `/soulreel/data-retention/deletion-grace-period` (default: 30 days)
   - `/soulreel/data-retention/legacy-protection-dormancy-days` (default: 730 days)
   - `/soulreel/data-retention/legacy-protection-lapse-days` (default: 365 days)
   - `/soulreel/data-retention/glacier-transition-days` (default: 365 days)
   - `/soulreel/data-retention/glacier-no-access-days` (default: 180 days)
   - `/soulreel/data-retention/intelligent-tiering-days` (default: 30 days)
   - `/soulreel/data-retention/export-rate-limit-days` (default: 30 days)
   - `/soulreel/data-retention/export-link-expiry-hours` (default: 72 hours)
2. FOR testing purposes, ALL lifecycle Lambda functions (Dormant_Account_Detector, Account_Deletion_Service, Storage_Lifecycle_Manager, Legacy_Protection_Service) SHALL accept an optional `simulatedCurrentTime` parameter (ISO 8601 timestamp) in their event payload. WHEN present, the function SHALL use this timestamp instead of the actual current time for all threshold calculations.
3. THE system SHALL expose a POST endpoint at `/admin/lifecycle/simulate` accessible only to admin users, accepting a JSON body with `{ "userId": "<userId>", "simulatedCurrentTime": "<ISO 8601>", "action": "<action>" }` where action is one of: `check_dormancy`, `process_deletion`, `check_legacy_protection`, `check_storage_transition`. This endpoint SHALL invoke the corresponding lifecycle function with the simulated time for the specified user only.
4. THE system SHALL expose a POST endpoint at `/admin/lifecycle/set-timestamps` accessible only to admin users, accepting a JSON body with `{ "userId": "<userId>", "lastLoginAt": "<ISO 8601>", "subscriptionLapsedAt": "<ISO 8601>" }`. This endpoint SHALL update the user's `lastLoginAt` in userStatusDB and `subscriptionLapsedAt` in UserSubscriptionsDB to the specified values, enabling testers to set up dormancy and lapse scenarios without waiting.
5. THE `simulatedCurrentTime` parameter and the `/admin/lifecycle/simulate` and `/admin/lifecycle/set-timestamps` endpoints SHALL only be functional when the SSM parameter `/soulreel/data-retention/testing-mode` is set to `enabled`. WHEN testing mode is disabled (default), the `simulatedCurrentTime` parameter SHALL be ignored and the admin simulation endpoints SHALL return HTTP 403.
6. ALL lifecycle functions SHALL log when they are operating in simulated time mode, including the simulated timestamp and the target user ID, to the audit log with event type `lifecycle_simulation`.

### Requirement 18: Testability — Storage Tier Simulation

**User Story:** As a developer or QA tester, I want to simulate content being in different S3 storage tiers without actually waiting for lifecycle transitions, so that I can test Glacier retrieval flows, reactivation restores, and export behavior for archived content.

#### Acceptance Criteria

1. THE system SHALL expose a POST endpoint at `/admin/storage/simulate-tier` accessible only to admin users, accepting a JSON body with `{ "userId": "<userId>", "storageTier": "STANDARD|INTELLIGENT_TIERING|GLACIER|DEEP_ARCHIVE" }`. This endpoint SHALL update the storage tier metadata for all of the user's content in DynamoDB without actually moving objects in S3.
2. WHEN storage tier metadata is set to GLACIER or DEEP_ARCHIVE via simulation, THE system SHALL behave as if the content is in that storage tier for all downstream logic: the Glacier retrieval flow (Requirement 4) SHALL be triggered on playback requests, the export service (Requirement 1) SHALL report `pending_retrieval` status, and the reactivation restore (Requirement 3) SHALL be triggered on resubscription.
3. THE simulated storage tier SHALL include a `simulated: true` flag in the DynamoDB metadata so that the actual S3 GetObject call still succeeds (since the object is physically still in Standard), while all tier-checking logic reads from the metadata instead of querying S3 HeadObject.
4. THE `/admin/storage/simulate-tier` endpoint SHALL only be functional when the SSM parameter `/soulreel/data-retention/testing-mode` is set to `enabled`. WHEN testing mode is disabled, the endpoint SHALL return HTTP 403.
5. THE system SHALL expose a POST endpoint at `/admin/storage/clear-simulation` accessible only to admin users, accepting `{ "userId": "<userId>" }`, which removes all simulated storage tier metadata and restores the DynamoDB records to reflect the actual S3 storage classes.

### Requirement 19: Testability — End-to-End Lifecycle Test Scenarios

**User Story:** As a developer, I want predefined test scenarios that exercise the full account lifecycle, so that I can validate the complete flow from active account through dormancy, legacy protection, reactivation, export, and deletion.

#### Acceptance Criteria

1. THE system SHALL expose a POST endpoint at `/admin/lifecycle/run-scenario` accessible only to admin users, accepting a JSON body with `{ "userId": "<userId>", "scenario": "<scenario_name>" }`. This endpoint SHALL execute a predefined sequence of lifecycle events with simulated timestamps against the specified user.
2. THE following test scenarios SHALL be supported:
   - `dormancy_full_cycle`: Simulates 6-month email → 12-month email → 24-month legacy protection evaluation, verifying each email is sent and the final dormancy flag is set.
   - `deletion_with_grace_period`: Creates a deletion request, simulates the 30-day grace period expiring, and verifies data is deleted and benefactors are notified.
   - `deletion_canceled`: Creates a deletion request, then cancels it within the grace period, verifying the account is restored.
   - `legacy_protection_activation`: Simulates the conditions for automatic legacy protection (24 months dormant, 12 months lapsed, benefactors exist) and verifies activation and benefactor notification.
   - `reactivation_from_glacier`: Simulates a user in legacy protection with Glacier-archived content, then simulates login and Premium resubscription, verifying the restore process is triggered.
   - `export_premium_only`: Attempts export as Free user (expects 403), upgrades to Premium, attempts export again (expects success).
   - `gdpr_export_free_tier`: Triggers lightweight GDPR export as Free user, verifies only text data is included (no videos).
3. EACH scenario SHALL return a JSON result with `{ "scenario": "<name>", "steps": [{ "step": "<description>", "status": "passed|failed", "details": "<details>" }], "overallStatus": "passed|failed" }`.
4. THE `/admin/lifecycle/run-scenario` endpoint SHALL only be functional when the SSM parameter `/soulreel/data-retention/testing-mode` is set to `enabled`.
5. EACH scenario execution SHALL be logged to the audit log with event type `test_scenario_executed`.
