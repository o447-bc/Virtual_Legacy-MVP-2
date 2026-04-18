# Data Retention Lifecycle — Implementation Summary

## Date: April 11, 2026

## What Was Built

A comprehensive data retention, export, and account lifecycle system for SoulReel covering 19 requirements across 6 new Lambda functions, 3 new AWS resources, 2 modified existing functions, a new frontend page, and 30 property-based tests.

### New Infrastructure (SAM template.yml)

- **DataRetentionDB** — DynamoDB table (userId PK, recordType SK) with status-index GSI and TTL. Tracks export requests, deletion requests, dormancy state, legacy protection status, retrieval queue, and storage metrics.
- **RetentionAuditBucket** — S3 bucket with Object Lock (Compliance mode, 3-year retention) for tamper-proof audit logs. KMS encrypted, versioning enabled.
- **ExportsTempBucket** — S3 bucket for temporary Content_Package ZIP archives. Auto-expires objects after 7 days. KMS encrypted.
- **12 SSM Parameters** under `/soulreel/data-retention/` — configurable thresholds for dormancy (6/12/24 months), deletion grace period (30 days), Glacier transitions (365 days), export rate limit (30 days), and testing mode flag.

### New Lambda Functions

1. **DataExportFunction** (900s timeout, 512MB, 10GB ephemeral)
   - POST /data/export-request — Full Content_Package export (Premium only). Builds ZIP with all S3 content, manifest.json, README.txt, data-portability.json. 5GB size limit.
   - POST /data/gdpr-export — Lightweight GDPR text-only export (all users). JSON file with profile, question responses, benefactors, subscription history.
   - GET /data/export-status — Returns current export status with fresh presigned URL on each call.
   - Handles async auto-export invocation from StripeWebhookFunction on subscription cancellation.

2. **AccountDeletionFunction** (300s timeout, 256MB)
   - POST /account/delete-request — Creates deletion request with 30-day grace period.
   - POST /account/cancel-deletion — Cancels pending deletion during grace period.
   - GET /account/deletion-status — Returns current deletion status.
   - EventBridge daily schedule — Processes expired grace periods with cascading deletion across all DynamoDB tables, S3, Cognito, and Stripe.

3. **DormantAccountDetector** (300s timeout, 256MB)
   - EventBridge weekly schedule — Scans userStatusDB for inactive accounts.
   - Sends escalating re-engagement emails at 6/12/24 month thresholds.
   - Flags accounts for Legacy Protection evaluation at 24 months.
   - Skips legacy-protected accounts. Never deletes content.

4. **StorageLifecycleManager** (900s timeout, 512MB)
   - EventBridge weekly schedule — Reconciles per-user storage metrics, manages Glacier transitions for legacy-protected content.
   - GET /admin/storage-report — Admin-only aggregate storage metrics.
   - Handles async reactivation restore when lapsed user resubscribes.
   - Publishes CloudWatch metrics for cost tracking.

5. **LegacyProtectionFunction** (120s timeout, 256MB)
   - POST /legacy/protection-request — Manual activation by benefactor (verifies relationship).
   - EventBridge weekly schedule — Auto-evaluates flagged accounts (24mo dormant + 12mo lapsed + benefactors exist).
   - Deactivation when user returns and logs in.

6. **AdminLifecycleFunction** (300s timeout, 256MB)
   - POST /admin/lifecycle/simulate — Invoke lifecycle functions with simulated time.
   - POST /admin/lifecycle/set-timestamps — Set user timestamps for testing.
   - POST /admin/lifecycle/run-scenario — Execute predefined end-to-end test scenarios.
   - POST /admin/storage/simulate-tier — Simulate storage tier for testing.
   - POST /admin/storage/clear-simulation — Clear simulated tier.
   - All gated by admin Cognito group + SSM testing-mode flag.

### Modified Existing Functions

- **StripeWebhookFunction** — Added lapse reassurance email on subscription.deleted, async auto-export trigger, and Glacier content check + reactivation restore trigger on checkout.session.completed.
- **GetMakerVideosFunction** — Added storage tier check before presigned URL generation. Returns HTTP 202 for Glacier/Deep Archive content with retrieval queue entry.

### New Shared Utilities

- **audit_logger.py** — SHA-256 hashed user IDs, validates event types, writes JSON to audit S3 bucket.
- **retention_config.py** — SSM parameter reader with caching, defaults fallback, simulated time support.

### Frontend

- **YourData page** (`/your-data`) — Trust statement, storage explanation, export controls (Premium full + GDPR text-only), deletion controls with confirmation dialog, rights section. Persona-based visibility (benefactors see subset).
- **DeleteConfirmationDialog** — Requires typing "DELETE" to confirm. Shows grace period, permanence, and benefactor impact warnings.
- **UserMenu** — Added "Your Data" menu item with HardDrive icon after "Security & Privacy".
- **dataRetentionService.ts** — Service layer with typed interfaces for all 7 API endpoints.
- **api.ts** — Added 8 new endpoint constants.

### IAM Changes

- Added inline policy `SoulReelKMSDeployAccess` to `soulreel-github-actions-oidc` OIDC role with kms:CreateGrant, kms:Decrypt, kms:DescribeKey, kms:Encrypt, kms:GenerateDataKey for the DataEncryptionKey. Required for CloudFormation to create KMS-encrypted DynamoDB tables and S3 buckets.

---

## Bugs Found and Fixed During Testing

1. **KMS presigned URL signature version** — ExportsTempBucket uses KMS encryption, which requires SigV4. The S3 client was using default SigV2. Fixed by adding `Config(signature_version='s3v4')`.

2. **userStatusDB key name** — Code used `UserId` (uppercase U) but the actual PK is `userId` (lowercase). Caused email lookups and profile data to silently fail.

3. **User email/profile not in userStatusDB** — Email, name, and persona_type are stored in Cognito attributes, not userStatusDB. Fixed by using `cognito-idp:AdminGetUser` for all profile and email lookups.

4. **userQuestionStatusDB query key** — Code used `Key('UserId')` but actual PK is `userId`. Caused question responses to always return empty.

5. **PersonaRelationshipsDB query key** — Code used `Key('makerId')` but actual PK is `initiator_id`. Caused benefactors list to always return empty.

6. **userQuestionStatusDB field names** — Code referenced non-existent fields (questionText, transcript, summary, answeredAt, questionType). Fixed to use actual fields (questionId, responseType, audioOneSentence, audioDetailedSummary, completedAt, status).

7. **PersonaRelationshipsDB field names** — Code referenced non-existent fields (visitorId, visitorName, visitorEmail). Fixed to use `related_user_id` + Cognito lookup for benefactor name/email.

8. **Presigned URL expiry in emails** — Lambda session tokens expire in 1-6 hours, making presigned URLs in emails go blank. Fixed by having email links point to `/your-data` page, and generating fresh presigned URLs on each `/data/export-status` call.

9. **HeadObject performance** — Removed unnecessary HeadObject calls for every S3 object in `_list_user_content`. Uses StorageClass from list_objects_v2 response directly.

10. **Cognito UserCreateDate type** — boto3 returns a datetime object, not a string. Fixed with explicit `.isoformat()` conversion.

11. **Rate limit blocking on failed/stale exports** — Rate limit now only blocks when status is 'ready' within the window. Allows re-export when previous status was 'pending_retrieval' or 'failed'.

12. **CloudFormation KMS CreateGrant** — OIDC deploy role lacked kms:CreateGrant permission. Added inline policy with GrantIsForAWSResource condition.

---

## Tests Completed

### Property-Based Tests (30 tests, all passing locally)

| Test File | Properties | Count |
|-----------|-----------|-------|
| test_data_export_properties.py | 1 (access control), 2 (completeness), 3 (GDPR text-only), 4 (record round trip), 5 (Glacier pending), 6 (one active), 7 (auto-export dedup), 23 (rate limit) | 9 |
| test_account_deletion_properties.py | 8 (grace period state machine), 9 (cascading deletion), 23 (deletion rate limit) | 9 |
| test_dormant_detector_properties.py | 11 (dormancy escalation), 12 (never deletes) | 4 |
| test_storage_lifecycle_properties.py | 19 (restore completeness), 20 (partial restore), 21 (metrics accuracy), 22 (aggregate consistency), 27 (Glacier transition criteria) | 6 |
| test_legacy_protection_properties.py | 13 (benefactor access invariant), 14 (exempts from cleanup), 15 (benefactor verification), 16 (deactivation on login) | 8 |
| test_admin_lifecycle_properties.py | 24 (testing mode gate), 25 (simulated time), 26 (tier simulation round trip), 30 (scenario result structure) | 9 |
| test_glacier_retrieval_properties.py | 17 (tier selection), 18 (retrieval queue TTL) | 8 |
| test_audit_log_properties.py | 10 (no PII, correct hash, required fields) | 3 |
| data-retention.property.test.ts | 28 (persona section visibility), 29 (content summary accuracy) | 3 |

### Live API Tests Completed (April 11, 2026)

| Test | Result | Details |
|------|--------|---------|
| DataRetentionDB table exists | PASS | ACTIVE, correct key schema (userId/recordType), status-index GSI |
| ExportsTempBucket exists | PASS | 7-day lifecycle, KMS encrypted |
| RetentionAuditBucket exists | PASS | Object Lock Compliance 3-year, KMS encrypted |
| SSM parameters created | PASS | All 12 parameters under /soulreel/data-retention/ |
| All 6 Lambda functions deployed | PASS | CREATE_COMPLETE with IAM roles, API permissions, EventBridge schedules |
| GET /data/export-status | PASS | Returns 'none' for fresh user |
| POST /data/export-request (Free user) | PASS | Returns 403 with upgrade URL |
| POST /data/gdpr-export (any user) | PASS | Returns 200 with download URL, correct JSON schema |
| GDPR export file content | PASS | schemaVersion 1.0, profile with name/email from Cognito, subscription history |
| Full Content_Package export (Premium) | PASS | ZIP with videos, manifest.json, README.txt, data-portability.json |
| Download from /your-data page | PASS | Fresh presigned URL generated on each page load |
| Email notification received | PASS | Links to /your-data page (not raw S3 URL) |
| POST /account/delete-request | PASS | Returns pending with 30-day grace end date |
| GET /account/deletion-status | PASS | Returns pending with correct dates |
| POST /account/cancel-deletion | PASS | Returns canceled, confirmation email sent |
| Audit log entries | PASS | 3 entries verified: export_completed, deletion_requested, deletion_canceled. SHA-256 hashed IDs, no PII. |
| Rate limiting (429) | PASS | Blocks within 30-day window for 'ready' exports |
| Rate limit bypass for failed/pending | PASS | Allows re-export when previous status was failed or pending_retrieval |

---

## Tests Still To Do

### Admin Simulation Endpoints (requires testing mode enabled)

1. **Enable testing mode**: `aws ssm put-parameter --name "/soulreel/data-retention/testing-mode" --value "enabled" --type String --overwrite`
2. **POST /admin/storage/simulate-tier** — Set a user's content to appear as DEEP_ARCHIVE, verify GetMakerVideos returns 202
3. **POST /admin/lifecycle/set-timestamps** — Set a user's lastLoginAt to 6 months ago
4. **POST /admin/lifecycle/simulate** — Run dormancy check with simulated time, verify email would be sent
5. **POST /admin/lifecycle/run-scenario** — Execute dormancy_full_cycle, deletion_with_grace_period, legacy_protection_activation scenarios
6. **POST /admin/storage/clear-simulation** — Verify tier restored to original
7. **Disable testing mode**: `aws ssm put-parameter --name "/soulreel/data-retention/testing-mode" --value "disabled" --type String --overwrite`
8. **Verify 403 when testing mode disabled** — All admin simulation endpoints should return 403

### Legacy Protection Flow

1. **Manual activation** — Log in as a benefactor account, POST /legacy/protection-request with a maker's userId. Verify 200 response, benefactor notification emails sent, DataRetentionDB record created.
2. **Non-benefactor rejection** — POST /legacy/protection-request for a maker you're not connected to. Verify 403.
3. **Deactivation on login** — After activating legacy protection, log in as the maker. Verify protection deactivated, welcome-back email sent.

### Stripe Webhook Integration

1. **Auto-export on cancellation** — Cancel a Premium subscription through Stripe. Verify StripeWebhookFunction triggers async DataExportFunction invocation, export is created, lapse reassurance email sent.
2. **Reactivation restore** — After content is in Glacier (simulated), resubscribe. Verify StripeWebhookFunction triggers StorageLifecycleManager reactivation restore.

### Scheduled Functions (will run automatically on EventBridge schedules)

1. **DormantAccountDetector** — Runs weekly. Verify it scans userStatusDB, sends emails at correct thresholds, skips legacy-protected accounts. Can be manually invoked for testing.
2. **StorageLifecycleManager** — Runs weekly. Verify it calculates per-user storage metrics, publishes CloudWatch metrics. Can be manually invoked.
3. **LegacyProtectionFunction auto-evaluation** — Runs weekly. Verify it processes flagged accounts and activates legacy protection when criteria met.
4. **AccountDeletionFunction daily scan** — Runs daily. Verify it processes expired grace periods (DO NOT test with real accounts unless using a throwaway).

### One-Time Manual Steps

1. **Apply S3 Intelligent-Tiering lifecycle rule** to virtual-legacy bucket (CLI command documented in template.yml)
2. **Verify CloudWatch metrics** appear under SoulReel/Storage namespace after StorageLifecycleManager runs
3. **Test with a user who has many recordings** (50+) to verify full Content_Package export performance and ZIP assembly
