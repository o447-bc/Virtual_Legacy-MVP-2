# User Data Reset Utility

## Overview

`purgeUserProgressAndDataButKeepUser.py` is a utility script that safely resets a user's data in the Virtual Legacy system while preserving their Cognito account. This is useful for testing first-time login scenarios and debugging initialization issues.

## What Gets Deleted

### S3 Data (virtual-legacy bucket)
- `user-responses/{userId}/` — Video responses, thumbnails, transcripts
- `conversations/{userId}/` — Conversation audio and transcripts
- `psych-exports/{userId}/` — Psychological test export files (PDF/CSV)

### S3 Data (soulreel-exports-temp-{accountId} bucket)
- `exports/{userId}/` — Data export ZIP archives (GDPR/content packages)

### DynamoDB Data (14 tables)
- `userQuestionStatusDB` — Answered questions tracking
- `userQuestionLevelProgressDB` — Level progress per question type
- `userStatusDB` — Current global level
- `PersonaRelationshipsDB` — All relationships (as initiator or related user)
- `AccessConditionsDB` — Access conditions (cascade-deleted with relationships)
- `PersonaSignupTempDB` — Temporary signup / invitation data
- `EngagementDB` — Streak and engagement data
- `UserSubscriptionsDB` — Stripe subscription and billing tier
- `UserTestProgressDB` — In-progress psych test responses
- `UserTestResultsDB` — Completed psych test results and scores
- `DataRetentionDB` — Export requests, deletion requests, dormancy tracking
- `WebSocketConnectionsDB` — Active WebSocket connections
- `ConversationStateDB` — In-flight conversation state
- `FeedbackReportsDB` — User-submitted bug reports and feature requests

### ⚠️ Data Retention Warning
- If the user has pending data export requests, they will be deleted.
- If the user has a pending account deletion (grace period), it will be cleared.
- Any exported ZIP archives in the temp bucket will be removed immediately.
- Psychological test results are permanently destroyed — no undo.
- Stripe subscription DynamoDB record is deleted (does NOT cancel Stripe itself).
- This utility is intended for **test accounts only**.

## What Gets Preserved

- ✅ Cognito User Pool account
- ✅ Email address
- ✅ Password
- ✅ Authentication credentials
- ✅ User can log in immediately after reset

## Usage

### Interactive Mode (Recommended)
```bash
cd UtilityFunctions
python purgeUserProgressAndDataButKeepUser.py
```

You'll be prompted for:
1. User email address
2. Confirmation of email
3. Confirmation for each operation

### Dry Run Mode (Safe Testing)
```bash
python purgeUserProgressAndDataButKeepUser.py --dry-run
```

Shows what would be deleted without actually deleting anything. Perfect for:
- Verifying the script works correctly
- Checking what data exists for a user
- Testing before actual deletion

### Batch Mode (Automation)
```bash
python purgeUserProgressAndDataButKeepUser.py --email user@example.com
```

Skips the email prompt but still requires confirmation for each operation.

### Batch + Dry Run
```bash
python purgeUserProgressAndDataButKeepUser.py --email user@example.com --dry-run
```

## Example Session

```
🔄 VIRTUAL LEGACY USER DATA RESET UTILITY 🔄
============================================================
⚠️  WARNING: This will delete ALL user data but keep the account!
   - All S3 video responses and conversations
   - All DynamoDB progress and status records
   - User will be reset to first-time login state
   ✅ Cognito account will be PRESERVED
============================================================

📧 Enter the email address of the user to reset: legacymaker3@example.com

⚠️  CONFIRM: You want to reset data for user 'legacymaker3@example.com'? (yes/no): yes

🔍 Searching for user 'legacymaker3@example.com' in Cognito User Pool...
✅ Found user: abc-123-def-456 (legacymaker3@example.com)

📊 USER FOUND:
   Email: legacymaker3@example.com
   User ID: abc-123-def-456
   Status: CONFIRMED

🚨 FINAL CONFIRMATION: Reset ALL data for user 'legacymaker3@example.com'? (type 'RESET' to confirm): RESET

🚀 Starting data reset process for user 'legacymaker3@example.com'...

============================================================
[S3 OPERATIONS]
============================================================

🚨 ABOUT TO PERFORM: Delete all S3 files from user-responses/abc-123-def-456/
Continue? (Y/N): Y

🗑️  Deleting S3 files from user-responses/abc-123-def-456/...
   Deleted batch: 15 files
✅ Successfully deleted 15 S3 files total

🚨 ABOUT TO PERFORM: Delete all S3 files from conversations/abc-123-def-456/
Continue? (Y/N): Y

🗑️  Deleting S3 files from conversations/abc-123-def-456/...
ℹ️  No S3 files found at conversations/abc-123-def-456/

============================================================
[DYNAMODB OPERATIONS]
============================================================

🚨 ABOUT TO PERFORM: Delete all records from userQuestionStatusDB for userId=abc-123-def-456
Continue? (Y/N): Y

🗑️  Deleting records from userQuestionStatusDB...
✅ Successfully deleted 42 records from userQuestionStatusDB

... [more operations] ...

============================================================
📋 DATA RESET OPERATION SUMMARY
============================================================
✅ Successfully completed 10 operations:
   1. S3 user-responses: Deleted 15 files
   2. S3 conversations: No files found
   3. userQuestionStatusDB: Deleted 42 records
   4. userQuestionLevelProgressDB: Deleted 6 records
   5. userStatusDB: Deleted 1 record
   6. PersonaRelationshipsDB: No records found
   7. PersonaSignupTempDB: No records found
   8. EngagementDB: Deleted 1 record
   9. WebSocketConnectionsDB: No connections found

============================================================
✅ User account PRESERVED in Cognito
   Email: legacymaker3@example.com
   User ID: abc-123-def-456
   Status: Account active and ready for login

🎯 User data reset completed successfully!
⚠️  All user data has been permanently deleted.
✅ User can now log in as if it's their first time.

🎉 DATA RESET COMPLETED SUCCESSFULLY for user 'legacymaker3@example.com'
   User account is preserved and ready for testing!
```

## Testing the Fix

After running this script, you can test the first-time login initialization:

1. Reset the user data:
   ```bash
   python purgeUserProgressAndDataButKeepUser.py --email legacymaker3@example.com
   ```

2. Log in to the dashboard as that user

3. Verify:
   - User sees level 1 questions (not "congratulations")
   - Progress shows actual question counts
   - All question types are initialized properly

## Safety Features

1. **Dry Run Mode** - Test without deleting
2. **Multiple Confirmations** - Email confirmation + operation confirmations
3. **User Verification** - Checks user exists before deleting
4. **Account Preservation** - Never touches Cognito account
5. **Detailed Logging** - Shows exactly what was deleted
6. **Error Handling** - Continues on errors, reports issues
7. **Final Verification** - Confirms account still exists after reset

## Comparison with purge_user.py

| Feature | purge_user.py | purgeUserProgressAndDataButKeepUser.py |
|---------|---------------|----------------------------------------|
| Deletes Cognito account | ✅ Yes | ❌ No |
| Deletes S3 data | ✅ Yes | ✅ Yes |
| Deletes DynamoDB data | ✅ Yes | ✅ Yes |
| Includes EngagementDB | ❌ No | ✅ Yes |
| Includes WebSocketConnectionsDB | ❌ No | ✅ Yes |
| Includes conversations/ S3 | ❌ No | ✅ Yes |
| Includes psych-exports/ S3 | ❌ No | ✅ Yes |
| Includes exports temp bucket | ❌ No | ✅ Yes |
| Includes UserSubscriptionsDB | ❌ No | ✅ Yes |
| Includes UserTestProgressDB | ❌ No | ✅ Yes |
| Includes UserTestResultsDB | ❌ No | ✅ Yes |
| Includes DataRetentionDB | ❌ No | ✅ Yes |
| Includes ConversationStateDB | ❌ No | ✅ Yes |
| Includes FeedbackReportsDB | ❌ No | ✅ Yes |
| Cascade AccessConditionsDB | ❌ No | ✅ Yes |
| Data retention warning | ❌ No | ✅ Yes |
| Dry run mode | ❌ No | ✅ Yes |
| Batch mode | ❌ No | ✅ Yes |
| Use case | Complete user removal | Testing first-time login |

## Requirements

- Python 3.6+
- boto3
- AWS credentials configured (AWS CLI)
- Appropriate IAM permissions:
  - Cognito: `cognito-idp:ListUsers`, `cognito-idp:AdminGetUser`
  - STS: `sts:GetCallerIdentity` (to discover account ID for exports bucket)
  - S3: `s3:ListBucket`, `s3:DeleteObject` (on both `virtual-legacy` and `soulreel-exports-temp-*` buckets)
  - DynamoDB: `dynamodb:Query`, `dynamodb:Scan`, `dynamodb:DeleteItem` (on all 14 tables)

## Troubleshooting

### "AWS credentials not found"
```bash
aws configure
```

### "User not found in Cognito"
- Verify the email address is correct
- Check you're using the right AWS region (us-east-1)
- Ensure the user exists in the User Pool

### "Access Denied" errors
- Check your IAM permissions
- Ensure you have access to all required services

### Script hangs during S3 deletion
- Large number of files may take time
- Each batch of 1000 files is reported
- Be patient or use Ctrl+C to cancel

## Author

Created by Kiro AI Assistant on 2026-02-21 to support testing of the first-time login initialization fix.

Updated 2026-04-26: Added 7 new DynamoDB tables (UserSubscriptionsDB, DataRetentionDB,
UserTestProgressDB, UserTestResultsDB, ConversationStateDB, AccessConditionsDB,
FeedbackReportsDB), 2 new S3 prefixes (psych-exports, exports temp bucket),
cascade delete of AccessConditionsDB from PersonaRelationships, and data retention warning.
