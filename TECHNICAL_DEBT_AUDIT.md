# Technical Debt & Quality Audit — Re-Assessment
## SoulReel / Virtual Legacy — Full-Stack AWS Application
**Audit Date:** March 15, 2026
**Previous Audit:** March 14, 2026 (Grade: C-)
**Current Grade: B-**

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [What Was Fixed Since Last Audit](#what-was-fixed-since-last-audit)
4. [Prioritized Improvement Areas](#prioritized-improvement-areas)
5. [Detailed Remediation Plans](#detailed-remediation-plans)
6. [Quick Wins Summary](#quick-wins-summary)
7. [Open Questions](#open-questions)

---

## Executive Summary

One day later, this codebase has made real, measurable progress. The previous audit
identified 17 prioritized issues graded at C-. The developer has addressed the most
dangerous ones: conversation state moved to DynamoDB with TTL, CORS wildcard replaced
with the production domain, CI/CD pipelines created for both frontend and backend,
SSM batch loading implemented with caching, text-path parallelism fixed, dead variant
files cleaned up, route-level auth guards added, SSH keys removed, frontend environment
variables externalized, a SharedUtilsLayer created, N+1 Cognito queries parallelized,
IAM wildcard ARNs mostly scoped, and frontend error handling improved.

That's genuine progress — roughly 12 of the original 17 items addressed in some form.
The grade moves from C- to B-. The remaining gap to B+ is mostly about finishing what
was started: adopting the shared helpers that already exist, removing hardcoded resource
names, plugging the error-leak pattern across ~15 Lambda functions, and wiring up React
Query which is already installed and wrapped around the app.

**Top 5 Remaining Time Bombs:**

1. `.env` file still committed with live Cognito credentials — git history exposure
2. ~15 Lambda functions leak `str(e)` in HTTP responses — information disclosure
3. ~30+ Lambda functions use hardcoded DynamoDB table names — fragile, blocks multi-env
4. Shared CORS/response helpers exist but aren't adopted — same bugs will recur
5. Hardcoded test emails in BenefactorDashboard block real users from sending invites

**Highest-ROI Next Steps:** Adopt shared helpers across all Lambdas (#4), fix error
leaks (#2), remove `.env` from git history (#1), remove test email gate (#5). These
are all low-risk, high-impact changes that finish work already in progress.

---

## Architecture Overview

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| Auth | AWS Cognito (User Pool `us-east-1_KsG65yYlo`, managed outside CloudFormation) |
| API | API Gateway REST + WebSocket API (SAM-managed) |
| Backend | Python 3.12 Lambda functions (SAM), SharedUtilsLayer |
| AI/ML | Bedrock (Claude 3.5 Sonnet conversation, Claude 3 Haiku scoring), Polly (TTS), Deepgram + AWS Transcribe |
| Database | DynamoDB (9 tables incl. ConversationStateDB) |
| Storage | S3 (`virtual-legacy` bucket), KMS CMK encryption |
| Email | SES |
| Monitoring | CloudTrail, GuardDuty, CloudWatch |
| Hosting | AWS Amplify (`d33jt7rnrasyvj`, branch `main`), custom domain `www.soulreel.net` |
| CI/CD | GitHub Actions — `backend.yml` (SAM) + `frontend.yml` (Amplify), triggers on push to `master` |

**Persona Model:** Two types — `legacy_maker` (records answers) and `legacy_benefactor`
(views content). Relationship stored in `PersonaRelationshipsDB` with access conditions
(`immediate`, `time_delayed`, `inactivity_trigger`, `manual_release`).

---

## What Was Fixed Since Last Audit

Credit where it's due. These items from the March 14 audit have been addressed:

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Conversation state in Lambda memory | ✅ Fixed | Moved to DynamoDB (`ConversationStateDB`) with TTL, Decimal handling, `from_dict` |
| 2 | CORS wildcard `*` | ✅ Fixed | Replaced with `https://www.soulreel.net` in template Globals + GatewayResponses |
| 3 | SSH keys in repo | ✅ Fixed | Deleted, added to `.gitignore` |
| 4 | Text-path sequential blocking | ✅ Fixed | `handle_user_response` now uses `process_user_response_parallel()` |
| 5 | Shared code duplication | 🟡 Partial | `SharedUtilsLayer` created, used by ~15 functions, but not all |
| 6 | N+1 Cognito queries | ✅ Fixed | `getRelationships` uses `ThreadPoolExecutor` + `_query_all_pages` |
| 7 | Dead code / variant files | ✅ Fixed | All `App-*.tsx`, `Home-*.tsx`, `Login-simple.tsx`, `AuthContext-simple.tsx`, `toDelete/` removed |
| 8 | No route-level auth guards | ✅ Fixed | `ProtectedRoute` component with `requiredPersona` prop |
| 9 | SSM individual loading | ✅ Fixed | `config.py` uses `ssm.get_parameters()` batch call with cache |
| 10 | No CI/CD | ✅ Fixed | `backend.yml` + `frontend.yml` in `.github/workflows/` |
| 11 | Frontend env vars hardcoded | ✅ Fixed | `import.meta.env.VITE_*` pattern, `.env.example` created |
| 12 | IAM wildcard ARNs | 🟡 Mostly fixed | Most scoped with `!Sub`, a few `Resource: '*'` remain |
| 13 | Frontend error handling | ✅ Fixed | ProfileDialog, PasswordDialog, useStatistics, logout have try-catch |
| 14 | Secrets in `.env` | ❌ Still committed | `.gitignore` lists it but file exists in tree + git history |

---

## Prioritized Improvement Areas

Ordered by **severity × ease** (highest combined impact first).

| # | Title | Severity | Ease | Effort | Status |
|---|---|---|---|---|---|
| 1 | `.env` committed with live credentials | Critical | Easy | S | New finding — was partially addressed |
| 2 | Error responses leak `str(e)` to clients | High | Easy | S | ~15 Lambda functions affected |
| 3 | Hardcoded DynamoDB table names across ~30 functions | High | Easy | M | Not addressed |
| 4 | Shared CORS/response helpers exist but unadopted | High | Easy | M | Helpers created, adoption stalled |
| 5 | Hardcoded test emails block real invite flow | High | Easy | S | Production blocker |
| 6 | CORS fallback defaults use old Amplify URL | Medium | Easy | S | ~20 Lambda functions affected |
| 7 | Hardcoded S3 bucket `virtual-legacy` in 6+ files | Medium | Easy | S | Not addressed |
| 8 | `ForgotPassword` page references missing auth function | Medium | Easy | S | Broken page |
| 9 | `ForgotPassword` / `ResetPassword` not in routes | Medium | Easy | S | Unreachable pages |
| 10 | React Query installed but unused — manual caching | Medium | Medium | M | Not addressed |
| 11 | TTS has no caching — Polly called for identical text | Medium | Medium | M | Not addressed |
| 12 | Persona race condition on benefactor signup | Medium | Hard | M | Not addressed |
| 13 | `ProtectedRoute` redirects benefactors to wrong dashboard | Medium | Easy | S | Bug in guard logic |
| 14 | Remaining IAM `Resource: '*'` on Transcribe/CloudWatch | Medium | Easy | S | Partially addressed |
| 15 | No backend tests in CI pipeline | Medium | Medium | M | `backend.yml` skips tests |
| 16 | CI/CD uses long-lived IAM keys instead of OIDC | Medium | Medium | M | Security best practice gap |
| 17 | N+1 sequential calls in BenefactorDashboard | Medium | Medium | S | Frontend performance |
| 18 | Dead file: `app old.py` in getNumValidQuestionsForQType | Low | Easy | S | Cleanup |
| 19 | `console.log` debug statements in AuthContext | Low | Easy | S | Cleanup |
| 20 | `QueryClient` has zero configuration | Low | Easy | S | Missing defaults |

---

## Detailed Remediation Plans

---

### Area #1: `.env` Committed with Live Credentials

**Why it matters:** `FrontEndCode/.env` is in the repository with live Cognito User Pool
Client ID (`465mg8nd442ku9vpd8ni723oo4`), Identity Pool ID, API Gateway URL, and S3
bucket name. `.gitignore` lists `.env` but the file was committed before the ignore rule
was added, so git continues tracking it. Anyone with repo access — or anyone who ever
had access — can see these credentials in git history. Additionally,
`SamLambda/template.yml` Parameters section still has live User Pool ID/ARN as defaults.

**Evidence:**
- `FrontEndCode/.env` — contains `VITE_USER_POOL_CLIENT_ID=465mg8nd442ku9vpd8ni723oo4`,
  `VITE_IDENTITY_POOL_ID=us-east-1:4f912954-ea9f-4d5c-b30f-563a45107715`,
  `VITE_API_BASE_URL=https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod`
- File says `# DO NOT COMMIT THIS FILE TO GIT` at the top — but it is committed

**Remediation Steps:**

1. Remove the file from git tracking (keeps local copy):
```bash
git rm --cached FrontEndCode/.env
git commit -m "Stop tracking .env file"
```

2. Verify `.gitignore` already has the entry (it does — `FrontEndCode/.gitignore` lists `.env`).

3. Purge from git history using BFG Repo-Cleaner:
```bash
# Install BFG if needed: brew install bfg
bfg --delete-files .env --no-blob-protection
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

4. After purging history, rotate the Cognito User Pool Client ID:
   - Cognito Console → User Pool → App clients → Delete `465mg8nd442ku9vpd8ni723oo4`
   - Create a new app client with the same settings
   - Update the GitHub Actions secret `VITE_USER_POOL_CLIENT_ID` with the new value
   - Update your local `.env` with the new value

5. Move SAM template parameter defaults to `samconfig.toml` so they're not in source:
```toml
# SamLambda/samconfig.toml
[default.deploy.parameters]
parameter_overrides = "CognitoUserPoolId=us-east-1_KsG65yYlo CognitoUserPoolArn=arn:aws:cognito-idp:..."
```

Then change the template defaults to empty strings:
```yaml
Parameters:
  CognitoUserPoolId:
    Type: String
    Default: ''
  CognitoUserPoolArn:
    Type: String
    Default: ''
```

**Risk:** Force-pushing rewrites history for all collaborators. Since this is a solo
project, the risk is minimal. Do it before adding any collaborators.


---

### Area #2: Error Responses Leak `str(e)` to Clients

**Why it matters:** At least 15 Lambda functions return `str(e)` directly in HTTP
response bodies. This exposes internal details — DynamoDB table names, Cognito pool
IDs, S3 bucket names, Python tracebacks, and AWS SDK error messages — to anyone who
can trigger an error. This is an information disclosure vulnerability that makes
targeted attacks easier.

**Evidence (sample of affected functions):**
- `getUploadUrl/app.py` — `'body': json.dumps({'error': str(e)})`
- `uploadVideoResponse/app.py` — `'body': json.dumps({'error': str(e)})`
- `getMakerVideos/app.py` — `'body': json.dumps({'error': str(e)})`
- `createRelationship/app.py` — `'body': json.dumps({'error': str(e)})`
- `validateAccess/app.py` — `'body': json.dumps({'error': str(e)})`
- `getStreak/app.py` — `'body': json.dumps({'error': str(e)})`
- `checkStreak/app.py` — `'body': json.dumps({'error': str(e)})`
- `processVideo/app.py` — `'body': json.dumps({'error': str(e)})`
- `sendInviteEmail/app.py` — `'body': json.dumps({'error': str(e)})`
- `acceptDeclineAssignment/app.py` — `'body': json.dumps({'error': f'Internal server error: {str(e)}'})` (still leaks)
- `createAssignment/app.py` — same pattern
- `updateAssignment/app.py` — same pattern
- `resendInvitation/app.py` — same pattern
- `manualRelease/app.py` — same pattern
- `initializeUserProgress/app.py` — `'body': json.dumps({'error': f'Internal error: {str(e)}'})`

**Remediation Steps:**

A shared `error_response()` helper already exists at `SamLambda/functions/shared/responses.py`.
It logs the full exception to CloudWatch and returns only a safe public message. Use it.

1. For every affected function, replace the catch block:

**Before:**
```python
except Exception as e:
    return {
        'statusCode': 500,
        'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', '...')},
        'body': json.dumps({'error': str(e)})
    }
```

**After (using shared helper):**
```python
from responses import error_response

except Exception as e:
    return error_response(500, 'A server error occurred. Please try again.', exception=e, event=event)
```

2. If a function doesn't yet use the SharedUtilsLayer, add it to the function's
   `Layers` property in `template.yml` first (see Area #4).

3. For functions that can't use the layer yet, apply the minimal inline fix:
```python
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")  # Log full details to CloudWatch
    import traceback
    print(traceback.format_exc())
    return {
        'statusCode': 500,
        'headers': {'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')},
        'body': json.dumps({'error': 'A server error occurred. Please try again.'})
    }
```

**Verification:** After deploying, trigger an error (e.g., pass invalid input) and
confirm the response body says "A server error occurred" — not a Python traceback.
Check CloudWatch to confirm the full error is still logged there.


---

### Area #3: Hardcoded DynamoDB Table Names Across ~30 Functions

**Why it matters:** At least 30 Lambda functions construct DynamoDB table references
with hardcoded strings like `dynamodb.Table('allQuestionDB')`. This means you cannot
run a staging environment with different table names, cannot rename tables without a
codebase-wide find-and-replace, and any typo in a table name silently creates a
reference to a nonexistent table that fails at runtime.

**Evidence (sample):**
- `getNumQuestionTypes/app.py` — `table = dynamodb.Table('allQuestionDB')`
- `getQuestionById/app.py` — `table = dynamodb.Table('allQuestionDB')`
- `getQuestionTypeData/app.py` — `table = dynamodb.Table('allQuestionDB')`
- `getQuestionTypes/app.py` — `table = dynamodb.Table('allQuestionDB')`
- `getNumValidQuestionsForQType/app.py` — `table = dynamodb.Table('allQuestionDB')`
- `getUnansweredQuestionsWithText/app.py` — `dynamodb.Table('allQuestionDB')` + `dynamodb.Table('userQuestionStatusDB')`
- `getUnansweredQuestionsFromUser/app.py` — same two tables
- `initializeUserProgress/app.py` — `Table('userQuestionLevelProgressDB')` + `Table('allQuestionDB')` + `Table('userStatusDB')`
- `incrementUserLevel2/app.py` — three hardcoded table names
- `getProgressSummary2/app.py` — `Table('allQuestionDB')`

**Remediation Steps:**

1. Add environment variables for each table in `template.yml` Globals:
```yaml
Globals:
  Function:
    Environment:
      Variables:
        ALL_QUESTIONS_TABLE: !Ref AllQuestionsTable
        USER_QUESTION_STATUS_TABLE: !Ref UserQuestionStatusTable
        USER_STATUS_TABLE: !Ref UserStatusTable
        USER_QUESTION_LEVEL_PROGRESS_TABLE: !Ref UserQuestionLevelProgressTable
        ENGAGEMENT_TABLE: !Ref EngagementTable
        PERSONA_RELATIONSHIPS_TABLE: !Ref PersonaRelationshipsTable
```

If the tables are not created by SAM (i.e., they pre-exist), use hardcoded names in
the template only — not in Lambda code:
```yaml
Globals:
  Function:
    Environment:
      Variables:
        ALL_QUESTIONS_TABLE: allQuestionDB
        USER_QUESTION_STATUS_TABLE: userQuestionStatusDB
        USER_STATUS_TABLE: userStatusDB
```

2. Update each Lambda function to read from env vars:

**Before:**
```python
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('allQuestionDB')
```

**After:**
```python
import os
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ALL_QUESTIONS_TABLE'])
```

3. Do this incrementally — one function group at a time. Start with the `questionDbFunctions/`
   directory since it has the most hardcoded references.

**Gotchas:**
- The `ALLOWED_ORIGIN` env var is already set via Globals, so adding more env vars to
  Globals is the established pattern.
- Some functions reference 3+ tables — make sure all are covered.
- The `LoadJSONToDynamoDB/` and `UtilityFunctions/` directories also have hardcoded
  table names, but those are utility scripts, not deployed Lambda functions. Lower priority.


---

### Area #4: Shared CORS/Response Helpers Exist but Unadopted

**Why it matters:** `SamLambda/functions/shared/cors.py` and `responses.py` were created
to solve the CORS consistency and error-leak problems. They work. But the vast majority
of Lambda functions still inline their own CORS headers and error responses. This means
the next time the CORS origin changes or an error format needs updating, you'll be
editing 20+ files instead of one. The shared layer was the right architectural decision
— it just needs to be finished.

**Evidence:**
- `SamLambda/functions/shared/cors.py` — has `cors_headers()`, `get_cors_origin()`,
  allowlist with `www.soulreel.net`, localhost origins
- `SamLambda/functions/shared/responses.py` — has `error_response()` that logs to
  CloudWatch and returns safe public message
- ~20 Lambda functions still inline:
  ```python
  'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')
  ```
- The `SharedUtilsLayer` exists in `template.yml` and is used by ~15 functions, but
  the remaining functions don't reference it

**Remediation Steps:**

1. Identify all functions NOT yet using the SharedUtilsLayer. Check `template.yml` for
   functions missing `Layers: [!Ref SharedUtilsLayer]`.

2. Add the layer to each remaining function in `template.yml`:
```yaml
GetStreakFunction:
  Type: AWS::Serverless::Function
  Properties:
    Layers:
      - !Ref SharedUtilsLayer
    # ... rest of properties
```

3. Update each function's imports and response patterns:

**Before:**
```python
import os
import json

CORS_HEADERS = {
    'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com'),
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

def lambda_handler(event, context):
    try:
        # ... business logic ...
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }
```

**After:**
```python
import json
from cors import cors_headers
from responses import error_response

def lambda_handler(event, context):
    try:
        # ... business logic ...
        return {
            'statusCode': 200,
            'headers': cors_headers(event),
            'body': json.dumps(result)
        }
    except Exception as e:
        return error_response(500, 'A server error occurred. Please try again.', exception=e, event=event)
```

4. This also fixes Area #2 (error leaks) and Area #6 (old Amplify URL fallback) in
   one pass. Three birds, one stone.

**Approach:** Do this in batches of 3-5 functions per commit. Test each batch with
`sam build` to catch import errors before deploying.

**Gotchas:**
- Lambda Layers mount at `/opt/python/`. The `SharedUtilsLayer` ContentUri is
  `functions/shared/` which should contain a `python/` subdirectory. Verify the
  directory structure is `functions/shared/python/cors.py` (not `functions/shared/cors.py`
  directly) — otherwise imports will fail.
- Actually, looking at the current structure: `cors.py` and `responses.py` are at
  `functions/shared/` level, and there's also a `functions/shared/python/` directory.
  Verify which path the layer actually uses. If `cors.py` is at the top level and not
  inside `python/`, the import `from cors import cors_headers` won't work from the
  layer — it needs to be at `/opt/python/cors.py`.


---

### Area #5: Hardcoded Test Emails Block Real Invite Flow

**Why it matters:** `BenefactorDashboard.tsx` has a hardcoded email validation that
only allows `legacymaker1@o447.net` and `legacymaker2@o447.net`. Any real user trying
to send an invite to a real email address gets the error "For testing, please use
legacyMaker1@o447.net or legacyMaker2@o447.net". This is a production blocker for the
core benefactor invite feature.

**Evidence:**
- `FrontEndCode/src/pages/BenefactorDashboard.tsx` line 56:
```typescript
const testEmails = ['legacymaker1@o447.net', 'legacymaker2@o447.net'];
if (!testEmails.includes(email.toLowerCase().trim())) {
    setEmailError('For testing, please use legacyMaker1@o447.net or legacyMaker2@o447.net');
    return false;
}
```
- The placeholder text and help text also reference these test emails

**Remediation Steps:**

1. Remove the test email validation entirely:

**Before:**
```typescript
const testEmails = ['legacymaker1@o447.net', 'legacymaker2@o447.net'];
if (!testEmails.includes(email.toLowerCase().trim())) {
    setEmailError('For testing, please use legacyMaker1@o447.net or legacyMaker2@o447.net');
    return false;
}
```

**After:**
```typescript
// Standard email format validation only
if (!/\S+@\S+\.\S+/.test(email.trim())) {
    setEmailError('Please enter a valid email address');
    return false;
}
```

2. Update the placeholder and help text:
```tsx
placeholder="Enter their email address"
```

3. Remove the "For testing" help text paragraph.

**This is a 5-minute fix with immediate user impact.**

---

### Area #6: CORS Fallback Defaults Use Old Amplify URL

**Why it matters:** ~20 Lambda functions use
`os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')` as
their CORS fallback. The env var is set correctly to `https://www.soulreel.net` in
`template.yml`, so this works today. But if the env var is ever missing (misconfigured
deploy, new function without Globals, local testing), the fallback kicks in with the
old Amplify URL and CORS breaks silently.

**Evidence:** Search for `amplifyapp.com` in `SamLambda/` returns 20+ matches across:
- `getUnansweredQuestionsFromUser/app.py` (6 occurrences)
- `getUnansweredQuestionsWithText/app.py` (4 occurrences)
- `incrementUserLevel2/app.py` (8 occurrences)
- `getTotalValidAllQuestions/app.py`
- `invalidateTotalValidQuestionsCache/app.py`
- `getAudioQuestionSummaryForVideoRecording/app.py` (4 occurrences)
- `persona_validator.py`
- Plus all the functions listed in Area #2

**Remediation Steps:**

If adopting the shared `cors.py` helper (Area #4), this is fixed automatically — the
helper's fallback is already `https://www.soulreel.net` via the `ALLOWED_ORIGIN` env var.

For functions not yet using the shared helper, do a find-and-replace:

**Before:**
```python
os.environ.get('ALLOWED_ORIGIN', 'https://main.d33jt7rnrasyvj.amplifyapp.com')
```

**After:**
```python
os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')
```

This is a safe, mechanical change. The env var value doesn't change — only the fallback
default that's used when the env var is missing.

**Note per project steering rules:** The CORS fallback default should always match the
production domain `https://www.soulreel.net`. The `ALLOWED_ORIGIN` env var is set via
SAM Globals and should be the primary source of truth.


---

### Area #7: Hardcoded S3 Bucket `virtual-legacy` in 6+ Files

**Why it matters:** The S3 bucket name `virtual-legacy` is hardcoded as a module-level
constant in multiple Lambda files. The `template.yml` already sets an `S3_BUCKET` env
var for some functions, but the code ignores it and uses the hardcoded string. This
blocks multi-environment deployments and means a bucket rename requires editing 6+ files.

**Evidence:**
- `speech.py` line 15: `S3_BUCKET = 'virtual-legacy'` (ignores `os.environ.get('S3_BUCKET')`)
- `transcribe.py` line 15: `S3_BUCKET = 'virtual-legacy'`
- `transcribe_streaming.py` line 18: `S3_BUCKET = 'virtual-legacy'`
- `uploadVideoResponse/app.py` lines 280, 478: `bucket_name = 'virtual-legacy'`
- `processVideo/app.py` line 540: `bucket_name = 'virtual-legacy'`
- `UtilityFunctions/purge_user.py` line 42: `self.s3_bucket = 'virtual-legacy'`

**Remediation Steps:**

1. In each affected file, replace the hardcoded bucket with the env var:

**Before (`speech.py`):**
```python
S3_BUCKET = 'virtual-legacy'
```

**After:**
```python
import os
S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
```

2. Verify `S3_BUCKET` is set in `template.yml` for each affected function. If not,
   add it to the function's environment variables or to Globals:
```yaml
Globals:
  Function:
    Environment:
      Variables:
        S3_BUCKET: virtual-legacy
```

3. For `uploadVideoResponse/app.py` and `processVideo/app.py`, the bucket name is
   assigned inline inside functions — refactor to a module-level constant:
```python
import os
BUCKET_NAME = os.environ.get('S3_BUCKET', 'virtual-legacy')
```

Then replace all `bucket_name = 'virtual-legacy'` references with `BUCKET_NAME`.

---

### Area #8: `ForgotPassword` Page References Missing Auth Function

**Why it matters:** `ForgotPassword.tsx` destructures `forgotPassword` from `useAuth()`,
but `AuthContext.tsx` does not export a `forgotPassword` function. This page will crash
with a runtime error when any user tries to reset their password. The page exists, is
importable, but is fundamentally broken.

**Evidence:**
- `FrontEndCode/src/pages/ForgotPassword.tsx` line 15:
  `const { forgotPassword, isLoading } = useAuth();`
- `FrontEndCode/src/contexts/AuthContext.tsx` — no `forgotPassword` in the context value

**Remediation Steps:**

1. Add `forgotPassword` to `AuthContext.tsx`:
```typescript
// In the AuthContext value type
forgotPassword: (email: string) => Promise<void>;

// In the provider implementation
const forgotPassword = async (email: string) => {
  setIsLoading(true);
  try {
    await resetPassword({ username: email });
    toast.success('Password reset code sent to your email.');
    navigate('/reset-password', { state: { email } });
  } catch (error: any) {
    console.error('Forgot password error:', error);
    toast.error('Failed to send reset code. Please try again.');
  } finally {
    setIsLoading(false);
  }
};
```

2. Import `resetPassword` from `aws-amplify/auth` at the top of `AuthContext.tsx`.

3. Add the function to the context value object.

**Alternatively**, if password reset is not a priority feature right now, remove
`ForgotPassword.tsx` and `ResetPassword.tsx` entirely to avoid dead code confusion.

---

### Area #9: `ForgotPassword` / `ResetPassword` Not in Routes

**Why it matters:** Both `ForgotPassword.tsx` and `ResetPassword.tsx` exist as page
components but are not registered in `App.tsx` routes. Even if the `forgotPassword`
function is implemented (Area #8), users cannot navigate to these pages.

**Evidence:**
- `FrontEndCode/src/App.tsx` — no `/forgot-password` or `/reset-password` routes
- `FrontEndCode/src/pages/ForgotPassword.tsx` — exists, has a `Link to="/login"`
- `FrontEndCode/src/pages/ResetPassword.tsx` — exists

**Remediation Steps:**

1. Add routes to `App.tsx` in the public routes section:
```tsx
{/* Public routes */}
<Route path="/forgot-password" element={<ForgotPassword />} />
<Route path="/reset-password" element={<ResetPassword />} />
```

2. Add imports at the top of `App.tsx`:
```tsx
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
```

3. Add a "Forgot password?" link on the Login page pointing to `/forgot-password`.

**Do this together with Area #8** — there's no point adding routes to a broken page.


---

### Area #10: React Query Installed but Unused — Manual Caching

**Why it matters:** `@tanstack/react-query` is installed, `QueryClientProvider` wraps
the app, but zero queries use it. All data fetching uses raw `useEffect` + `useState` +
`fetch`. The `useStatistics` hook is 150 lines of manual stale-while-revalidate logic
with localStorage — reimplementing what React Query does out of the box. This means no
query deduplication, no automatic background refetching, no cache invalidation on
mutations, and no devtools visibility.

**Evidence:**
- `FrontEndCode/src/App.tsx` — `const queryClient = new QueryClient()` with zero config
- `FrontEndCode/src/hooks/useStatistics.ts` — 150 lines: `getCachedStatistics()`,
  `setCachedStatistics()`, `CACHE_DURATION = 300000`, localStorage read/write, manual
  `isMounted` tracking, background refresh logic
- `FrontEndCode/src/pages/Dashboard.tsx` — multiple `useEffect` hooks for data fetching

**Remediation Steps:**

1. Configure the `QueryClient` with sensible defaults in `App.tsx`:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,          // 1 minute before refetch
      retry: 2,
      refetchOnWindowFocus: false, // avoid surprise refetches
    },
  },
});
```

2. Create query key constants:
```typescript
// src/lib/queryKeys.ts
export const queryKeys = {
  progress: (userId: string) => ['progress', userId] as const,
  streak: (userId: string) => ['streak', userId] as const,
  relationships: (userId: string) => ['relationships', userId] as const,
  assignments: (userId: string) => ['assignments', userId] as const,
  statistics: (userId: string) => ['statistics', userId] as const,
};
```

3. Replace `useStatistics` (150 lines → ~15 lines):

**Before (abbreviated):**
```typescript
export function useStatistics(userId: string | undefined) {
  const [data, setData] = useState<StatisticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadStatistics() {
      const cached = getCachedStatistics(userId);
      if (cached) { setData(cached); setLoading(false); }
      const fresh = await fetchStatistics(userId);
      if (isMounted) { setData(fresh); setCachedStatistics(userId, fresh); }
      // ... 80 more lines of error handling, fallbacks, cleanup
    }
    loadStatistics();
    return () => { isMounted = false; };
  }, [userId]);

  return { data, loading, error };
}
```

**After:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';

export function useStatistics(userId: string | undefined) {
  const { data, isLoading: loading, error } = useQuery({
    queryKey: queryKeys.statistics(userId ?? ''),
    queryFn: () => fetchStatistics(userId!),
    enabled: !!userId,
    staleTime: 5 * 60_000,
    placeholderData: { longestStreak: 0, totalQuestionsAnswered: 0, currentLevel: 1, overallProgress: 0 },
  });

  return { data: data ?? null, loading, error: error?.message ?? null };
}
```

4. Delete the `getCachedStatistics`, `setCachedStatistics`, `CACHE_KEY_PREFIX`,
   `CACHE_DURATION`, and `CachedStatistics` interface — React Query handles all of this.

5. Migrate Dashboard data fetching similarly — replace each `useEffect` + `useState`
   pair with a `useQuery` call.

**Migrate incrementally.** Start with `useStatistics` (biggest win), then Dashboard,
then BenefactorDashboard. Each can be a separate commit.

---

### Area #11: TTS Has No Caching — Polly Called for Identical Text

**Why it matters:** Every conversation turn calls Polly to synthesize the AI response,
even if the exact same text was synthesized before (e.g., greetings, transition phrases,
repeated prompts). Each Polly call adds 200-500ms latency and costs money. There's no
cache check — the audio is generated fresh every time and uploaded to a unique S3 key
with a timestamp.

**Evidence:**
- `SamLambda/functions/conversationFunctions/wsDefault/speech.py`:
  - `S3_BUCKET = 'virtual-legacy'` (hardcoded, see Area #7)
  - `s3_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}-{timestamp}.mp3"`
    — unique key per call, no cache lookup
  - No `head_object` check, no hash-based key, no cache prefix

**Remediation Steps:**

1. Add a cache layer using a deterministic S3 key based on text + voice hash:
```python
import hashlib

def _cache_key(text: str, voice_id: str, engine: str) -> str:
    content_hash = hashlib.sha256(f"{text}|{voice_id}|{engine}".encode()).hexdigest()[:16]
    return f"tts-cache/{content_hash}.mp3"

def text_to_speech(text: str, user_id: str, question_id: str,
                   turn_number: int, voice_id: str, engine: str) -> str:
    cache_key = _cache_key(text, voice_id, engine)

    # Check cache first
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
        print(f"[POLLY] Cache hit: {cache_key}")
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': cache_key},
            ExpiresIn=3600
        )
    except s3_client.exceptions.ClientError:
        pass  # Cache miss — synthesize

    # Synthesize and upload to cache key
    response = polly.synthesize_speech(Text=text, OutputFormat='mp3',
                                        VoiceId=voice_id, Engine=engine)
    audio_data = response['AudioStream'].read()

    s3_client.put_object(
        Bucket=S3_BUCKET, Key=cache_key, Body=audio_data,
        ContentType='audio/mpeg',
        ServerSideEncryption='aws:kms', SSEKMSKeyId=kms_key_arn
    )

    # Also store at the conversation-specific path for audit trail
    conversation_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}.mp3"
    s3_client.copy_object(
        Bucket=S3_BUCKET,
        CopySource={'Bucket': S3_BUCKET, 'Key': cache_key},
        Key=conversation_key,
        ServerSideEncryption='aws:kms', SSEKMSKeyId=kms_key_arn
    )

    return s3_client.generate_presigned_url(
        'get_object', Params={'Bucket': S3_BUCKET, 'Key': cache_key}, ExpiresIn=3600
    )
```

2. Also fix the hardcoded `S3_BUCKET` while you're in this file (Area #7):
```python
import os
S3_BUCKET = os.environ.get('S3_BUCKET', 'virtual-legacy')
```

**Expected impact:** Common phrases like "Thank you for sharing that" or "Let's move
on to the next question" will be served from cache in ~50ms instead of ~300ms from Polly.
Over many conversations, this adds up to meaningful latency reduction and cost savings.


---

### Area #12: Persona Race Condition on Benefactor Signup

**Why it matters:** When a benefactor signs up via invite link, the frontend calls
`signupWithPersona` which triggers the Cognito `postConfirmation` Lambda to write the
persona type. But the Lambda runs asynchronously — the frontend doesn't wait for it to
complete. Instead, it calls `checkAuthState()` and then forcibly overrides the user's
`personaType` to `'legacy_benefactor'` on the client side. If the Lambda hasn't finished
writing the Cognito attribute, the user's server-side persona is wrong until the next
login. If the client-side override fails (component unmount, navigation), the user lands
on the wrong dashboard.

**Evidence:**
- `FrontEndCode/src/contexts/AuthContext.tsx` line 210:
```typescript
await checkAuthState();
setUser(prev => prev ? { ...prev, personaType: 'legacy_benefactor' } : prev);
```
- Comment above it explicitly acknowledges the race condition

**Remediation Steps:**

1. Replace the client-side override with a polling retry that waits for the server to
   confirm the persona attribute:
```typescript
const waitForPersona = async (expected: string, maxAttempts = 5): Promise<boolean> => {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const attributes = await fetchUserAttributes();
      if (attributes.profile) {
        const profile = JSON.parse(attributes.profile);
        if (profile.persona_type === expected) return true;
      }
    } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 1000 * (i + 1))); // exponential backoff
  }
  return false;
};
```

2. In `signupWithPersona`, replace the override:
```typescript
// BEFORE
await checkAuthState();
setUser(prev => prev ? { ...prev, personaType: 'legacy_benefactor' } : prev);

// AFTER
const confirmed = await waitForPersona('legacy_benefactor');
await checkAuthState(); // refresh user state from server
if (!confirmed) {
  console.warn('Persona attribute not confirmed after retries — proceeding with client state');
}
```

3. In `postConfirmation/app.py`, ensure the Lambda raises on failure so Cognito retries:
```python
try:
    cognito.admin_update_user_attributes(...)
except ClientError as e:
    print(f"CRITICAL: Failed to set persona for {username}: {e}")
    raise  # Fail the trigger — Cognito will retry
```

**Risk:** The polling adds 1-5 seconds to the signup flow. This is acceptable because
it only happens once per user, and the alternative is a broken persona assignment.

---

### Area #13: `ProtectedRoute` Redirects Benefactors to Wrong Dashboard

**Why it matters:** When a benefactor navigates to a maker-only route (e.g., `/dashboard`
without `requiredPersona` set, or a route with `requiredPersona="legacy_maker"`), the
`ProtectedRoute` component redirects them to `/dashboard` — which is the maker dashboard.
Benefactors should be redirected to `/benefactor-dashboard`.

**Evidence:**
- `FrontEndCode/src/components/ProtectedRoute.tsx` lines 19-20:
```typescript
if (requiredPersona && user.personaType !== requiredPersona) {
    return <Navigate to="/dashboard" replace />;
}
```

**Remediation Steps:**

Update the redirect logic to route based on the user's actual persona:
```typescript
if (requiredPersona && user.personaType !== requiredPersona) {
    const fallback = user.personaType === 'legacy_benefactor'
        ? '/benefactor-dashboard'
        : '/dashboard';
    return <Navigate to={fallback} replace />;
}
```

**This is a 2-line fix.**

---

### Area #14: Remaining IAM `Resource: '*'` on Transcribe/CloudWatch

**Why it matters:** Three IAM policy statements still use `Resource: '*'` without
conditions, granting broader permissions than necessary.

**Evidence (in `template.yml`):**
- `UploadVideoResponseFunction` — `cloudwatch:PutMetricData` with `Resource: '*'`
- `StartTranscriptionFunction` — `transcribe:StartTranscriptionJob` with `Resource: '*'`
- `ProcessTranscriptFunction` — `transcribe:GetTranscriptionJob` with `Resource: '*'`

**Remediation Steps:**

1. For CloudWatch `PutMetricData`, `Resource: '*'` is actually required — CloudWatch
   metrics don't support resource-level permissions. Add a `Condition` to limit the
   namespace instead:
```yaml
- Effect: Allow
  Action: cloudwatch:PutMetricData
  Resource: '*'
  Condition:
    StringEquals:
      cloudwatch:namespace: 'SoulReel/VideoUpload'
```

2. For Transcribe, scope to the account:
```yaml
- Effect: Allow
  Action: transcribe:StartTranscriptionJob
  Resource: !Sub 'arn:aws:transcribe:${AWS::Region}:${AWS::AccountId}:*'
```

3. Same for `GetTranscriptionJob`:
```yaml
- Effect: Allow
  Action: transcribe:GetTranscriptionJob
  Resource: !Sub 'arn:aws:transcribe:${AWS::Region}:${AWS::AccountId}:*'
```


---

### Area #15: No Backend Tests in CI Pipeline

**Why it matters:** `backend.yml` runs `sam validate --lint`, `sam build`, and
`sam deploy` — but no tests. Any Python syntax error, logic bug, or import failure
in a Lambda function won't be caught until it's deployed and invoked in production.
The frontend pipeline runs `tsc --noEmit` and `npm run lint` before building, which
is a good pattern — the backend should match.

**Evidence:**
- `.github/workflows/backend.yml` — no test step between build and deploy
- No `pytest` or `unittest` configuration visible in `SamLambda/`

**Remediation Steps:**

1. Add a `requirements-dev.txt` to `SamLambda/`:
```
pytest>=7.0
moto>=5.0
boto3-stubs
```

2. Add a test step to `backend.yml` between build and deploy:
```yaml
- name: Install test dependencies
  run: pip install -r requirements-dev.txt
  working-directory: SamLambda

- name: Run tests
  run: python -m pytest tests/ -v --tb=short
  working-directory: SamLambda
```

3. Start with smoke tests — verify each Lambda handler can be imported without errors:
```python
# SamLambda/tests/test_imports.py
import importlib
import pytest

HANDLERS = [
    'functions.streakFunctions.getStreak.app',
    'functions.streakFunctions.checkStreak.app',
    'functions.questionDbFunctions.getQuestionTypes.app',
    # ... add all handlers
]

@pytest.mark.parametrize('module_path', HANDLERS)
def test_handler_imports(module_path):
    """Verify each Lambda handler can be imported without errors."""
    importlib.import_module(module_path)
```

4. Add unit tests for the shared helpers (`cors.py`, `responses.py`) since they're
   used by many functions.

**Start small.** Import tests catch the most common deployment failures (missing
imports, syntax errors) with minimal effort. Add logic tests incrementally.

---

### Area #16: CI/CD Uses Long-Lived IAM Keys Instead of OIDC

**Why it matters:** The GitHub Actions workflows authenticate to AWS using long-lived
IAM access keys stored as GitHub secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
If these keys are leaked (GitHub breach, accidental exposure), an attacker has persistent
access to the AWS account. OIDC federation eliminates long-lived credentials entirely.

**Evidence:**
- `.github/workflows/backend.yml` and `frontend.yml` both use:
```yaml
aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Remediation Steps:**

1. Create an OIDC identity provider in IAM:
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

2. Create an IAM role with a trust policy scoped to your repo:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::962214556635:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/master"
      }
    }
  }]
}
```

3. Update the workflows:
```yaml
permissions:
  id-token: write
  contents: read

- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::962214556635:role/github-actions-deploy
    aws-region: us-east-1
```

4. After verifying OIDC works, delete the long-lived access keys for the
   `soulreel-github-actions` IAM user and remove the GitHub secrets.

**Note per project steering rules:** The IAM user is `soulreel-github-actions`. Don't
create a new user — migrate to OIDC and retire the user entirely.

---

### Area #17: N+1 Sequential Calls in BenefactorDashboard

**Why it matters:** `BenefactorDashboard.tsx` has two sequential loops that make API
calls one at a time: `for (const assignment of assignments)` calling `validateAccess()`
individually, and `for (const rel of relationships)` calling `getUserProgress()`
individually. With 5 relationships and 5 assignments, that's 10 sequential API calls
on page load.

**Evidence:**
- `FrontEndCode/src/pages/BenefactorDashboard.tsx` — sequential `for...of` loops
  with `await` inside

**Remediation Steps:**

Replace sequential loops with `Promise.all`:

**Before:**
```typescript
for (const assignment of assignments) {
    const access = await validateAccess(assignment.id);
    // ...
}
```

**After:**
```typescript
const accessResults = await Promise.all(
    assignments.map(a => validateAccess(a.id).catch(() => null))
);
```

Same pattern for the relationships loop. This turns 10 sequential calls into 2 parallel
batches.


---

### Area #18: Dead File — `app old.py` in getNumValidQuestionsForQType

**Why it matters:** `SamLambda/functions/questionDbFunctions/getNumValidQuestionsForQType/app old.py`
is a dead file sitting next to the active `app.py`. It's also present in the SAM build
output (`.aws-sam/build/`). It adds confusion about which file is canonical and inflates
the deployment package.

**Evidence:**
- `SamLambda/functions/questionDbFunctions/getNumValidQuestionsForQType/app old.py` — exists
- `SamLambda/.aws-sam/build/GetNumValidQuestionsForQTypeFunction/app old.py` — copied to build

**Remediation:** Delete the file:
```bash
rm "SamLambda/functions/questionDbFunctions/getNumValidQuestionsForQType/app old.py"
```

---

### Area #19: `console.log` Debug Statements in AuthContext

**Why it matters:** `AuthContext.tsx` contains multiple `console.log` statements that
output auth state, user attributes, and persona information to the browser console in
production. This is information leakage — any user can open DevTools and see internal
auth flow details.

**Evidence:**
- `FrontEndCode/src/contexts/AuthContext.tsx` — multiple `console.log` calls throughout
  `checkAuthState`, `login`, `signupWithPersona`

**Remediation:** Replace `console.log` with conditional logging:
```typescript
const isDev = import.meta.env.DEV;
const log = isDev ? console.log : () => {};
```

Or simply remove them. Auth flow debugging should use breakpoints, not console output
in production.

---

### Area #20: `QueryClient` Has Zero Configuration

**Why it matters:** `const queryClient = new QueryClient()` in `App.tsx` uses all
defaults: `staleTime: 0` (every render triggers a refetch), `retry: 3` (failed queries
retry 3 times with exponential backoff), `refetchOnWindowFocus: true` (switching tabs
triggers refetches). These defaults are aggressive for a production app and will cause
unnecessary API calls.

**Evidence:**
- `FrontEndCode/src/App.tsx` line 28: `const queryClient = new QueryClient();`

**Remediation:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

This is a 5-line change that improves behavior for all future React Query adoption.
Do it now even before migrating any data fetching to React Query.


---

## Quick Wins Summary

Items that can be completed in under 30 minutes each, with immediate impact.

| # | Fix | Effort | Impact | Files |
|---|---|---|---|---|
| 1 | Remove test email gate in BenefactorDashboard | 10 min | Unblocks real invite flow | `BenefactorDashboard.tsx` |
| 2 | Fix ProtectedRoute benefactor redirect | 5 min | Correct persona routing | `ProtectedRoute.tsx` |
| 3 | Delete `app old.py` dead file | 2 min | Cleanup | `getNumValidQuestionsForQType/app old.py` |
| 4 | Configure QueryClient defaults | 5 min | Better caching behavior | `App.tsx` |
| 5 | `git rm --cached FrontEndCode/.env` | 5 min | Stop tracking secrets | `.env` |
| 6 | Update CORS fallback defaults to `soulreel.net` | 20 min | Eliminate latent CORS risk | ~20 Lambda `app.py` files |
| 7 | Fix `speech.py` to use `S3_BUCKET` env var | 5 min | Env-var consistency | `speech.py`, `transcribe.py`, `transcribe_streaming.py` |
| 8 | Remove `console.log` from AuthContext | 10 min | Stop leaking auth details | `AuthContext.tsx` |
| 9 | Add ForgotPassword/ResetPassword routes | 10 min | Enable password reset flow | `App.tsx` |
| 10 | Scope Transcribe IAM to account ARN | 10 min | Tighter IAM | `template.yml` |
| 11 | Add CloudWatch PutMetricData namespace condition | 5 min | Tighter IAM | `template.yml` |
| 12 | Parallelize BenefactorDashboard API calls | 15 min | Faster page load | `BenefactorDashboard.tsx` |

**Recommended order:** 1 → 5 → 2 → 3 → 4 → 6 → 7 → 8 → 9 → 10 → 11 → 12

Items 1-5 can be done in a single commit. Items 6-7 are a natural batch (CORS + S3
consistency). Items 10-11 are a template.yml batch.

---

## Open Questions

These are architectural decisions that need your input — they don't have a single
"correct" answer.

**1. SharedUtilsLayer directory structure — is it correct?**
The layer's `ContentUri` is `functions/shared/`. For Python Lambda Layers, the code
must be at `python/` inside the content directory (i.e., `functions/shared/python/cors.py`).
But `cors.py` and `responses.py` appear to be at `functions/shared/cors.py` directly.
If the `python/` subdirectory has different copies, there may be version drift. Verify
which path is actually used at runtime and consolidate.

**2. Should `getProgressSummary2` and `incrementUserLevel2` be renamed?**
The "2" suffix suggests these replaced earlier versions. If the originals are gone from
the template, rename to drop the suffix for clarity. If both versions are still
referenced in `template.yml`, determine which is active and remove the other.

**3. Password reset flow — implement or remove?**
`ForgotPassword.tsx` and `ResetPassword.tsx` exist but are broken (missing auth function,
missing routes). Either implement the full flow (add `forgotPassword` to AuthContext,
add routes, wire up Cognito `resetPassword`) or delete both files to avoid dead code.

**4. React Query migration scope — how far to go?**
The minimal path is: configure QueryClient defaults, migrate `useStatistics`, and stop.
The full path is: migrate all Dashboard/BenefactorDashboard data fetching, add mutation
hooks for video upload and invite sending, add cache invalidation. The minimal path
takes ~1 hour; the full path takes ~1 day. Both are valid — depends on your priorities.

**5. `CheckInResponseFunction` and `InitializeUserProgressFunction` — intentionally public?**
These endpoints have no Cognito authorizer. If they're meant to be called by
unauthenticated users (e.g., during signup flow before auth is established), that's
fine. If they should be protected, add the authorizer in `template.yml`.

**6. Denormalize user attributes into PersonaRelationshipsDB?**
The N+1 Cognito query fix (ThreadPoolExecutor) is a good quick fix, but the proper
solution is storing `email`, `first_name`, `last_name` in the relationship record at
write time. This eliminates the Cognito dependency on the read path entirely. Worth
doing if the relationship count per user is expected to grow.

**7. TTS caching — worth the S3 `head_object` overhead?**
Each cache check adds an S3 `head_object` call (~20-50ms). For short, unique AI
responses, the cache hit rate may be low and the overhead not worth it. For repeated
phrases (greetings, transitions), it's a clear win. Consider caching only responses
shorter than N characters, or pre-warming the cache with known phrases.

**8. Git history purge — ready to force-push?**
Purging `.env` from git history requires `git push --force`, which rewrites history for
all collaborators. As a solo developer, this is safe. But if you've shared the repo
with anyone or have any CI integrations that cache commit SHAs, coordinate first.

---

## Summary of Grade Change

| Dimension | March 14 | March 15 | Notes |
|---|---|---|---|
| Reliability | D | B | DynamoDB state, parallel text path, SSM batch |
| Security | D | C+ | CORS fixed, SSH removed, but `.env` still committed, error leaks remain |
| Maintainability | D+ | C+ | Dead code removed, shared layer created but unadopted, hardcoded names persist |
| Performance | C- | C | Text parallelism fixed, but TTS uncached, N+1 on frontend |
| Observability | C | C | No new monitoring, no backend tests in CI |
| CI/CD | F | B- | Pipelines created and working, but no tests, long-lived keys |
| Frontend Architecture | C- | C+ | ProtectedRoute added, React Query still unused |
| **Overall** | **C-** | **B-** | Solid progress in 24 hours. Finish the shared helper adoption and error leak fixes to reach B. |

The path from B- to B+ is clear and mostly mechanical: adopt shared helpers across all
Lambdas (fixes errors, CORS, and consistency in one pass), remove the test email gate,
fix the ProtectedRoute redirect, and configure React Query. No architectural changes
needed — just finishing what's already been started.
