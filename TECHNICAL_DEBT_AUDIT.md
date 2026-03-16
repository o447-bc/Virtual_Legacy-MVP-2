# Technical Debt & Quality Audit — Third Assessment
## SoulReel / Virtual Legacy — Full-Stack AWS Application
**Audit Date:** March 15, 2026 (evening)
**Previous Audits:** March 14, 2026 (Grade: C-) → March 15, 2026 (Grade: B-)
**Current Grade: B**

---

## Table of Contents

1. [Prioritized Improvement Areas](#prioritized-improvement-areas)
2. [Detailed Remediation Plans](#detailed-remediation-plans)
3. [Executive Summary](#executive-summary)
4. [Quick Wins Summary](#quick-wins-summary)
5. [Open Questions](#open-questions)

---

## Architecture Overview

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui + React Query (partially adopted) |
| Auth | AWS Cognito (User Pool `us-east-1_KsG65yYlo`, managed outside CloudFormation) |
| API | API Gateway REST (Cognito-authorized) + WebSocket API (SAM-managed) |
| Backend | ~40 Python 3.12 Lambda functions via SAM, SharedUtilsLayer |
| AI/ML | Bedrock (Claude 3.5 Sonnet conversation, Claude 3 Haiku scoring), Polly (TTS), Deepgram + AWS Transcribe (3-tier fallback) |
| Database | DynamoDB (9+ tables) with KMS CMK encryption, TTL, PITR |
| Storage | S3 (`virtual-legacy` bucket), KMS-encrypted |
| Email | SES |
| Monitoring | CloudTrail, GuardDuty, CloudWatch |
| Hosting | AWS Amplify (`d33jt7rnrasyvj`, branch `main`), custom domain `www.soulreel.net` |
| CI/CD | GitHub Actions — `backend.yml` (SAM + OIDC) + `frontend.yml` (Amplify + OIDC), triggers on push to `master` |

**Persona Model:** Two types — `legacy_maker` (records answers) and `legacy_benefactor`
(views content). Relationship stored in `PersonaRelationshipsDB` with access conditions
(`immediate`, `time_delayed`, `inactivity_trigger`, `manual_release`).

---

## What Changed Since the B- Audit (March 15 morning → evening)

| Item | Status | Evidence |
|---|---|---|
| Test email gate in BenefactorDashboard | ✅ Fixed | No `testEmails` or `o447` references remain in `BenefactorDashboard.tsx` |
| ProtectedRoute benefactor redirect | ✅ Fixed | Now routes to `/benefactor-dashboard` for benefactors (`ProtectedRoute.tsx`) |
| ForgotPassword/ResetPassword routes | ✅ Fixed | Both imported and routed in `App.tsx` lines 27-28, 55-56 |
| QueryClient zero configuration | ✅ Fixed | `staleTime: 60_000`, `retry: 2`, `refetchOnWindowFocus: false` in `App.tsx` line 30 |
| `useStatistics` manual caching | ✅ Fixed | Now uses `useQuery` with proper key, staleTime, placeholderData (`useStatistics.ts`) |
| CI/CD OIDC migration | ✅ Fixed | Both `backend.yml` and `frontend.yml` use `role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}` with `id-token: write` |
| Backend smoke tests in CI | ✅ Fixed | `backend.yml` installs `requirements-dev.txt` and runs `pytest tests/test_imports.py` |
| `speech.py` S3 bucket env var | ✅ Fixed | Now uses `os.environ.get('S3_BUCKET', 'virtual-legacy')` |
| Error response `str(e)` leaks in handlers | ✅ Mostly fixed | Lambda handlers now return safe messages; `str(e)` remains in internal DAL/utility functions (not HTTP-facing) |
| `str(e)` in shared DAL layer | ⚠️ Partial | `assignment_dal.py`, `invitation_utils.py` still return `str(e)` in error dicts — these bubble up through handlers that may expose them |

That's meaningful progress — roughly 10 items addressed since the B- audit. The grade moves to B.

---

## Prioritized Improvement Areas

Ordered by **severity × ease** (highest combined impact first).

| # | Title | Severity | Ease | Effort |
|---|---|---|---|---|
| 1 | Localhost URLs in all production email templates | Critical | Easy | S |
| 2 | `.env` still committed with live Cognito credentials | Critical | Easy | S |
| 3 | Hardcoded WebSocket URL in ConversationInterface | High | Easy | S |
| 4 | Shared CORS/response helpers adopted by ~30 functions but not by shared DAL layer | High | Easy | M |
| 5 | `extract_user_id_from_jwt` duplicated across 7 assignment functions | High | Easy | M |
| 6 | Hardcoded DynamoDB table names in shared DAL layer (~20 occurrences) | High | Medium | M |
| 7 | No TTS caching — Polly called fresh for every conversation turn | Medium | Medium | M |
| 8 | Dashboard ProgressSection: 200+ lines of manual fetch/state in a single useEffect | Medium | Medium | M |
| 9 | Persona race condition on benefactor signup | Medium | Medium | M |
| 10 | Duplicate code between processVideo and uploadVideoResponse (~700 LOC each) | Medium | Hard | L |
| 11 | WebSocket Lambda 30s timeout vs multi-tier transcription fallback path | Medium | Easy | S |
| 12 | Global Lambda timeout of 3s — dangerous default | Medium | Easy | S |
| 13 | Conversation state grows unbounded per DynamoDB item | Medium | Medium | M |
| 14 | Old Amplify URL in CORS allowlist | Low | Easy | S |
| 15 | `console.log` debug statements in AuthContext and ConversationInterface | Low | Easy | S |
| 16 | `createAssignment` manually parses JWT instead of using Cognito authorizer claims | Low | Easy | S |
| 17 | Remaining `Resource: '*'` on `transcribe:StartStreamTranscription` | Low | Easy | S |
| 18 | `ForgotPassword` page may still reference missing `forgotPassword` auth function | Low | Easy | S |

---

## Detailed Remediation Plans

---

### Area #1: Localhost URLs in All Production Email Templates

**Severity: Critical | Ease: Easy | Effort: S**

**Why it matters:** Every email sent to benefactors — invitations, access granted notifications,
check-in requests, accept/decline confirmations — contains `http://localhost:8080` links instead
of `https://www.soulreel.net`. Users clicking "View Assignment", "Create Your Account", or
"Confirm I'm Active" land on a broken localhost URL. This silently breaks the entire benefactor
onboarding and access-grant flow for every real user.

The root cause: `email_templates.py` line 22 defaults to `http://localhost:8080` via
`os.environ.get('APP_BASE_URL', 'http://localhost:8080')`, and `APP_BASE_URL` is **never set**
in `template.yml` Globals or any function's environment variables. The env var doesn't exist
at runtime, so the fallback always wins.

Additionally, ~10 Lambda functions have their own inline email templates that hardcode
`http://localhost:8080` directly, bypassing `email_templates.py` entirely.

**Evidence (inline hardcoded localhost — not using email_templates.py):**
- `acceptDeclineAssignment/app.py` lines 434, 454, 533, 553 — `http://localhost:8080/manage-benefactors`
- `resendInvitation/app.py` lines 363, 385 — `http://localhost:8080/signup?invite={invitation_token}`
- `manualRelease/app.py` lines 467, 486 — `http://localhost:8080/dashboard`
- `checkInResponse/app.py` lines 307, 433 — `http://localhost:8080/dashboard`
- `timeDelayProcessor/app.py` lines 327, 349 — `http://localhost:8080/dashboard`
- `inactivityProcessor/app.py` lines 384, 410 — `http://localhost:8080/dashboard`
- `postConfirmation/app.py` lines 281, 301 — `http://localhost:8080/dashboard`
- `checkInSender/app.py` line 334 — has `# TODO: Update with production domain` comment

**Evidence (email_templates.py fallback):**
- `SamLambda/functions/shared/email_templates.py` line 22: `return os.environ.get('APP_BASE_URL', 'http://localhost:8080')`
- `SamLambda/functions/shared/python/email_templates.py` — identical copy
- `APP_BASE_URL` does not appear anywhere in `SamLambda/template.yml`

**Remediation Steps:**

1. Add `APP_BASE_URL` to SAM Globals so every Lambda gets it:
```yaml
Globals:
  Function:
    Environment:
      Variables:
        ALLOWED_ORIGIN: 'https://www.soulreel.net'
        APP_BASE_URL: 'https://www.soulreel.net'
        S3_BUCKET: 'virtual-legacy'
        # ... existing vars
```

2. Update the fallback default in `email_templates.py` (both copies):
```python
def get_base_url() -> str:
    return os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')
```

3. Migrate the 10 Lambda functions with inline email templates to use `email_templates.py`
   instead. If that's too much work right now, at minimum find-and-replace all
   `http://localhost:8080` with `os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')`
   in each file. The affected functions are listed above.

4. For `checkInSender/app.py` line 334, replace:
```python
# TODO: Update with production domain
verification_link = f"http://localhost:8080/check-in?token={token}"
```
with:
```python
base_url = os.environ.get('APP_BASE_URL', 'https://www.soulreel.net')
verification_link = f"{base_url}/check-in?token={token}"
```

5. Deploy backend: `sam build && sam deploy --no-confirm-changeset` from `SamLambda/`.

**Verification:** After deploying, trigger a test email (e.g., create a test assignment)
and verify the email body contains `https://www.soulreel.net` links, not localhost.

**This is the single highest-impact fix in this audit.** Every benefactor-facing email
is currently broken.


---

### Area #2: `.env` Still Committed with Live Cognito Credentials

**Severity: Critical | Ease: Easy | Effort: S**

**Why it matters:** `FrontEndCode/.env` is tracked by git and contains live Cognito User Pool
Client ID (`465mg8nd442ku9vpd8ni723oo4`), Identity Pool ID
(`us-east-1:4f912954-ea9f-4d5c-b30f-563a45107715`), API Gateway URL, and S3 bucket name.
The file header says `# DO NOT COMMIT THIS FILE TO GIT` — but it is committed. Anyone with
repo access (current or historical) can see these values. Additionally, `SamLambda/template.yml`
Parameters section has the live User Pool ID and ARN as defaults (lines 9-15).

The frontend CI/CD pipeline correctly injects these values from GitHub secrets during build
(`frontend.yml` env block), so the `.env` file is only needed for local development. It should
not be in the repository.

**Evidence:**
- `FrontEndCode/.env` — contains `VITE_USER_POOL_CLIENT_ID=465mg8nd442ku9vpd8ni723oo4`
- `FrontEndCode/.gitignore` lists `.env` — but the file was committed before the rule was added
- `SamLambda/template.yml` line 10: `Default: us-east-1_KsG65yYlo`
- `SamLambda/template.yml` line 14: `Default: arn:aws:cognito-idp:us-east-1:962214556635:userpool/us-east-1_KsG65yYlo`

**Remediation Steps:**

1. Remove from git tracking (keeps local copy):
```bash
git rm --cached FrontEndCode/.env
git commit -m "chore: stop tracking .env file"
```

2. Purge from git history:
```bash
# Install BFG if needed: brew install bfg
bfg --delete-files .env --no-blob-protection
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

3. After purging, rotate the Cognito User Pool Client:
   - Cognito Console → User Pool → App clients → Delete `465mg8nd442ku9vpd8ni723oo4`
   - Create new app client with same settings
   - Update GitHub secret `VITE_USER_POOL_CLIENT_ID` with new value
   - Update local `.env` with new value

4. Move SAM template parameter defaults to `samconfig.toml`:
```toml
[default.deploy.parameters]
parameter_overrides = "ExistingUserPoolId=us-east-1_KsG65yYlo ExistingUserPoolArn=arn:aws:cognito-idp:..."
```
Then change template defaults to empty strings.

**Risk:** Force-push rewrites history. As a solo project, this is safe. Do it before
adding collaborators.

---

### Area #3: Hardcoded WebSocket URL in ConversationInterface

**Severity: High | Ease: Easy | Effort: S**

**Why it matters:** `ConversationInterface.tsx` line 8 hardcodes the WebSocket API URL:
```typescript
const WS_URL = 'wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod';
```
This means the frontend can never point to a different WebSocket endpoint (staging, local dev)
without editing source code. If the WebSocket API is ever redeployed with a new ID, this
breaks conversations for all users until a frontend deploy catches up.

**Evidence:**
- `FrontEndCode/src/components/ConversationInterface.tsx` line 8

**Remediation Steps:**

1. Add to `.env` and `.env.example`:
```
VITE_WS_URL=wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod
```

2. Add to `frontend.yml` build env:
```yaml
VITE_WS_URL: ${{ secrets.VITE_WS_URL }}
```

3. Update `ConversationInterface.tsx`:
```typescript
const WS_URL = import.meta.env.VITE_WS_URL || 'wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod';
```

4. Add `VITE_WS_URL` to GitHub secrets.

**5-minute fix.**

---

### Area #4: Shared CORS/Response Helpers Adopted by ~30 Functions but Not by Shared DAL Layer

**Severity: High | Ease: Easy | Effort: M**

**Why it matters:** The SharedUtilsLayer is now referenced by ~30+ functions in `template.yml` —
that's great progress. But the shared DAL modules (`assignment_dal.py`, `invitation_utils.py`)
that live *inside* the layer still return `str(e)` in error dictionaries. These error dicts
bubble up through Lambda handlers like `createAssignment`, `acceptDeclineAssignment`, etc.
While the top-level handlers now return safe messages for their own exceptions, errors from
the DAL layer can still leak internal details if the handler passes the DAL error message
through to the response.

Additionally, `assignment_dal.py` and `invitation_utils.py` hardcode DynamoDB table names
(see Area #6) and don't use the shared `cors.py` or `responses.py` helpers.

**Evidence:**
- `SamLambda/functions/shared/assignment_dal.py` — 10 occurrences of `f"Unexpected error...: {str(e)}"`
  at lines 71, 149, 209, 281, 323, 374, 426, 473
- `SamLambda/functions/shared/invitation_utils.py` — 3 occurrences at lines 83, 156, 274
- `SamLambda/functions/shared/python/assignment_dal.py` — identical copy with same issues
- `SamLambda/functions/shared/python/invitation_utils.py` — identical copy

**Remediation Steps:**

1. In `assignment_dal.py` and `invitation_utils.py`, replace error returns:

**Before:**
```python
except Exception as e:
    return False, {'error': f"Unexpected error creating assignment record: {str(e)}"}
```

**After:**
```python
except Exception as e:
    print(f"[DAL ERROR] {type(e).__name__}: {e}")
    import traceback
    print(traceback.format_exc())
    return False, {'error': 'An internal error occurred. Please try again.'}
```

2. Apply the same pattern to all 13 occurrences across both files.

3. Ensure both copies (`functions/shared/` and `functions/shared/python/`) are updated
   identically. Better yet — consolidate to one copy (see Open Questions).

**Gotcha:** The handlers that call these DAL functions sometimes include the DAL error
message in their response body (e.g., `json.dumps({'error': conditions_result.get('error', ...)})`).
After this fix, those responses will show the safe generic message instead.

---

### Area #5: `extract_user_id_from_jwt` Duplicated Across 7 Assignment Functions

**Severity: High | Ease: Easy | Effort: M**

**Why it matters:** Seven Lambda functions each contain their own copy of
`extract_user_id_from_jwt()` — a ~50-line function that manually decodes JWT tokens by
base64-decoding the payload segment. This is fragile (no signature verification), duplicated
(any fix must be applied 7 times), and unnecessary — the Cognito authorizer already validates
the JWT and puts the claims in `event.requestContext.authorizer.claims`.

**Evidence (each file has its own copy):**
- `createAssignment/app.py` line 269
- `getAssignments/app.py` line 103
- `acceptDeclineAssignment/app.py` line 291
- `manualRelease/app.py` line 516
- `updateAssignment/app.py` line 398
- `resendInvitation/app.py` line 259
- `sendInviteEmail/app.py` line 180

Other functions in the codebase correctly use the authorizer claims pattern:
```python
user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
```

**Remediation Steps:**

1. For functions behind the Cognito authorizer (all assignment functions are), replace
   the manual JWT parsing with the authorizer claims:

**Before:**
```python
legacy_maker_id = extract_user_id_from_jwt(event)
```

**After:**
```python
legacy_maker_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
```

2. Delete the `extract_user_id_from_jwt` function from each file.

3. If you want a shared helper for this pattern, add it to the SharedUtilsLayer:
```python
# functions/shared/python/auth_utils.py
def get_user_id(event: dict) -> str | None:
    """Extract user ID from Cognito authorizer claims."""
    return event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
```

**Why the authorizer approach is better:**
- The JWT is already validated by API Gateway — no need to decode it again
- No risk of accepting an expired or tampered token
- No base64 decoding edge cases
- One line instead of 50


---

### Area #6: Hardcoded DynamoDB Table Names in Shared DAL Layer (~20 Occurrences)

**Severity: High | Ease: Medium | Effort: M**

**Why it matters:** While the SAM Globals now define `TABLE_*` environment variables for all
9 DynamoDB tables, the shared DAL modules (`assignment_dal.py`, `invitation_utils.py`,
`timezone_utils.py`) still hardcode table names as string literals. These modules are used
by many Lambda functions, so the hardcoded names are effectively baked into every function
that imports them. This blocks multi-environment deployments and means a table rename requires
editing the shared layer code.

The Lambda function `app.py` files themselves have mostly migrated to `os.environ.get('TABLE_*')`
— the remaining hardcoded names are concentrated in the shared layer.

**Evidence:**
- `assignment_dal.py` — `Table('PersonaRelationshipsDB')` at lines 47, 177, 305, 348, 458;
  `Table('AccessConditionsDB')` at lines 103, 397
- `invitation_utils.py` — `Table('PersonaSignupTempDB')` at lines 54, 118, 259;
  `Table('PersonaRelationshipsDB')` at line 210; `Table('AccessConditionsDB')` at line 227
- `timezone_utils.py` — `Table('userStatusDB')` at line 16 (3 copies: shared/, shared/python/, streakFunctions/)
- All duplicated in `functions/shared/python/` copies

**Remediation Steps:**

1. Update each shared module to read from env vars:

**Before (`assignment_dal.py`):**
```python
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('PersonaRelationshipsDB')
```

**After:**
```python
import os
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB'))
```

2. Apply the same pattern to all table references:
   - `PersonaRelationshipsDB` → `os.environ.get('TABLE_RELATIONSHIPS', 'PersonaRelationshipsDB')`
   - `AccessConditionsDB` → `os.environ.get('TABLE_ACCESS_CONDITIONS', 'AccessConditionsDB')`
   - `PersonaSignupTempDB` → `os.environ.get('TABLE_SIGNUP_TEMP', 'PersonaSignupTempDB')`
   - `userStatusDB` → `os.environ.get('TABLE_USER_STATUS', 'userStatusDB')`

3. These env vars are already defined in SAM Globals, so no template changes needed.

4. Update both copies (`functions/shared/` and `functions/shared/python/`) identically.

**Gotcha:** The `timezone_utils.py` file exists in three places — `shared/`, `shared/python/`,
and `streakFunctions/checkStreak/`. All three need updating.

---

### Area #7: No TTS Caching — Polly Called Fresh for Every Conversation Turn

**Severity: Medium | Ease: Medium | Effort: M**

**Why it matters:** Every conversation turn calls Polly to synthesize the AI response text,
uploads the audio to S3 with a unique timestamp-based key, and generates a presigned URL.
There is no cache check. Common phrases like "Thank you for sharing that" or "Let's explore
that further" are re-synthesized every time. Each Polly call adds 200-500ms latency and
costs $4/million characters (standard) or $16/million (neural).

**Evidence:**
- `speech.py` line 37: `s3_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}-{timestamp}.mp3"`
  — unique key per call, no cache lookup
- No `head_object` check, no hash-based key, no deduplication
- `speech.py` is called from `handle_audio_response` in `app.py` on every turn

**Remediation Steps:**

1. Add a content-hash cache layer in `speech.py`:

```python
import hashlib

def _cache_key(text: str, voice_id: str, engine: str) -> str:
    content_hash = hashlib.sha256(f"{text}|{voice_id}|{engine}".encode()).hexdigest()[:16]
    return f"tts-cache/{content_hash}.mp3"

def text_to_speech(text, user_id, question_id, turn_number, voice_id, engine):
    bucket = os.environ.get('S3_BUCKET', 'virtual-legacy')
    cache_key = _cache_key(text, voice_id, engine)

    # Check cache
    try:
        s3_client.head_object(Bucket=bucket, Key=cache_key)
        print(f"[POLLY] Cache hit: {cache_key}")
        return s3_client.generate_presigned_url(
            'get_object', Params={'Bucket': bucket, 'Key': cache_key}, ExpiresIn=3600
        )
    except s3_client.exceptions.ClientError:
        pass  # Cache miss

    # Synthesize
    response = polly.synthesize_speech(Text=text, OutputFormat='mp3',
                                        VoiceId=voice_id, Engine=engine)
    audio_data = response['AudioStream'].read()

    # Upload to cache key (with KMS encryption)
    kms_key_arn = os.environ.get('KMS_KEY_ARN')
    s3_client.put_object(
        Bucket=bucket, Key=cache_key, Body=audio_data,
        ContentType='audio/mpeg',
        ServerSideEncryption='aws:kms', SSEKMSKeyId=kms_key_arn
    )

    return s3_client.generate_presigned_url(
        'get_object', Params={'Bucket': bucket, 'Key': cache_key}, ExpiresIn=3600
    )
```

2. IAM policy for WebSocketDefaultFunction already grants `s3:GetObject` and `s3:PutObject`
   on `arn:aws:s3:::virtual-legacy/conversations/*`. The `tts-cache/` prefix is outside this
   scope — add it:
```yaml
Resource:
  - arn:aws:s3:::virtual-legacy/conversations/*
  - arn:aws:s3:::virtual-legacy/test-audio/*
  - arn:aws:s3:::virtual-legacy/tts-cache/*
```

3. The `head_object` call adds ~20-50ms overhead on cache misses. For short unique responses
   this is a net loss. Consider only caching responses shorter than 200 characters (where
   cache hit rate is highest — greetings, transitions, follow-up prompts).

**Expected impact:** Common phrases served from S3 in ~50ms instead of ~300ms from Polly.
Over a 10-turn conversation, this could save 1-2 seconds total latency.

---

### Area #8: Dashboard ProgressSection — 200+ Lines of Manual Fetch/State in a Single useEffect

**Severity: Medium | Ease: Medium | Effort: M**

**Why it matters:** `Dashboard.tsx` `ProgressSection` component (lines 186-500+) contains a
single massive `useEffect` that fetches progress data, processes it, checks for level
completion, calls the increment API, reprocesses the response, shows toasts, and manages
6 separate `useState` variables. This is ~200 lines of imperative data fetching that
duplicates what React Query handles declaratively. The `useStatistics` hook was successfully
migrated to React Query — this is the next candidate.

The component also has a subtle bug: the `useEffect` depends on `[user, navigationState]`,
but `navigationState` comes from React Router's `location.state`, which is a new object
reference on every navigation — causing unnecessary refetches.

**Evidence:**
- `FrontEndCode/src/pages/Dashboard.tsx` lines 186-500+
- 6 `useState` calls: `questionTypeData`, `progressData`, `unansweredQuestionsData`,
  `unansweredQuestionTextsData`, `progressItems`, `loading`, `error`
- Manual auth token fetching inside the effect
- Level progression check embedded in the data fetch effect
- Dynamic `import('@/hooks/use-toast')` inside the effect (code splitting a 2KB module)

**Remediation Steps:**

1. Extract the data fetching into a React Query hook:

```typescript
// src/hooks/useProgress.ts
import { useQuery } from '@tanstack/react-query';

async function fetchProgress(userId: string, idToken: string) {
  const response = await fetch(
    buildApiUrl(API_CONFIG.ENDPOINTS.PROGRESS_SUMMARY_2, { userId }),
    { headers: { Authorization: `Bearer ${idToken}` } }
  );
  if (!response.ok) throw new Error('Failed to fetch progress data');
  return response.json();
}

export function useProgress(userId: string | undefined) {
  return useQuery({
    queryKey: ['progress', userId],
    queryFn: () => fetchProgress(userId!, /* get token */),
    enabled: !!userId,
    staleTime: 60_000,
  });
}
```

2. Extract the level progression check into a separate `useMutation`:

```typescript
export function useIncrementLevel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { questionType: string }) => incrementLevel(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
  });
}
```

3. Separate the data processing logic from the fetch logic — the `forEach` that builds
   `questionTypes`, `friendlyNames`, `numValidQuestions` arrays should be a pure function
   or `useMemo`, not embedded in a `useEffect`.

4. Remove the dynamic `import('@/hooks/use-toast')` — just import it statically at the top.

**This reduces ProgressSection from ~300 lines to ~80 lines** and gets proper caching,
deduplication, and background refetching for free.

---

### Area #9: Persona Race Condition on Benefactor Signup

**Severity: Medium | Ease: Medium | Effort: M**

**Why it matters:** When a benefactor signs up via invite link, the frontend calls
`signupWithPersona` which triggers the Cognito `postConfirmation` Lambda to write the
persona type. But the Lambda runs asynchronously — the frontend doesn't wait for it.
Instead, it calls `checkAuthState()` and then forcibly overrides the user's `personaType`
to `'legacy_benefactor'` on the client side. If the Lambda hasn't finished writing the
Cognito attribute, the user's server-side persona is wrong until the next login.

**Evidence:**
- `FrontEndCode/src/contexts/AuthContext.tsx` — `signupWithPersona` function:
  ```typescript
  await checkAuthState();
  setUser(prev => prev ? { ...prev, personaType: 'legacy_benefactor' } : prev);
  ```
- Comment in the code explicitly acknowledges the race condition

**Remediation Steps:**

1. Add a polling helper that waits for the server to confirm the persona:
```typescript
const waitForPersona = async (expected: string, maxAttempts = 5): Promise<boolean> => {
  for (let i = 0; i < maxAttempts; i++) {
    const attributes = await fetchUserAttributes();
    if (attributes.profile) {
      const profile = JSON.parse(attributes.profile);
      if (profile.persona_type === expected) return true;
    }
    await new Promise(r => setTimeout(r, 1000 * (i + 1)));
  }
  return false;
};
```

2. Replace the client-side override:
```typescript
const confirmed = await waitForPersona('legacy_benefactor');
await checkAuthState();
if (!confirmed) {
  console.warn('Persona not confirmed after retries — proceeding with client state');
}
```

3. In `postConfirmation/app.py`, ensure the Lambda raises on failure so Cognito retries:
```python
except ClientError as e:
    print(f"CRITICAL: Failed to set persona for {username}: {e}")
    raise  # Cognito will retry the trigger
```

**Risk:** Adds 1-5 seconds to signup flow. Acceptable since it happens once per user.


---

### Area #10: Duplicate Code Between processVideo and uploadVideoResponse (~700 LOC Each)

**Severity: Medium | Ease: Hard | Effort: L**

**Why it matters:** `processVideo/app.py` and `uploadVideoResponse/app.py` are both ~700+
lines and share nearly identical implementations of: `update_user_streak()`,
`generate_thumbnail()`, `DecimalEncoder`, S3 download/upload logic, video metadata extraction,
and similar `lambda_handler` patterns. Any bug fix or improvement must be applied to both
files. The thumbnail generation code alone is ~100 lines duplicated verbatim.

**Evidence:**
- `SamLambda/functions/videoFunctions/processVideo/app.py` — ~700 lines
- `SamLambda/functions/videoFunctions/uploadVideoResponse/app.py` — ~700 lines
- Both contain identical `generate_thumbnail()` with S3 download → ffmpeg → S3 upload
- Both contain identical `update_user_streak()` with DynamoDB update logic
- Both contain identical `DecimalEncoder` class
- Both contain identical S3 error handling patterns (lines 513-521 in uploadVideoResponse,
  lines 575-583 in processVideo)

**Remediation Steps:**

1. Extract shared utilities into the SharedUtilsLayer:

```python
# functions/shared/python/video_utils.py
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def generate_thumbnail(s3_key: str, bucket: str, kms_key_arn: str) -> str:
    """Download video from S3, extract thumbnail with ffmpeg, upload back."""
    # ... extracted from both files
    pass

def update_user_streak(user_id: str, table_name: str) -> dict:
    """Update user's recording streak in DynamoDB."""
    # ... extracted from both files
    pass
```

2. Update both Lambda functions to import from the shared module:
```python
from video_utils import DecimalEncoder, generate_thumbnail, update_user_streak
```

3. Both functions already use the SharedUtilsLayer (`template.yml` confirms this), so
   no template changes needed — just add the new file to the layer.

4. Start with `DecimalEncoder` (trivial, zero risk), then `update_user_streak`, then
   `generate_thumbnail` (most complex, test carefully).

**Gotcha:** Both functions also use the `ffmpeg-layer` for thumbnail generation. The
shared `generate_thumbnail` function needs to work with the ffmpeg binary path from
that layer (`/opt/bin/ffmpeg`).

---

### Area #11: WebSocket Lambda 30s Timeout vs Multi-Tier Transcription Fallback

**Severity: Medium | Ease: Easy | Effort: S**

**Why it matters:** `WebSocketDefaultFunction` has a 30-second timeout (`template.yml` line 695).
The `handle_audio_response` function executes: transcription (3-tier fallback) → parallel
LLM scoring + response generation → Polly TTS → S3 upload → WebSocket message send.

The worst-case path: Deepgram fails (~2s) → AWS Streaming fails (~5s) → AWS Batch transcription
(~15s average) → Bedrock LLM calls (~3-5s) → Polly (~0.3-0.5s) → S3 + presigned URL (~0.2s).
That's ~25-27 seconds in the worst case, leaving only 3-5 seconds of headroom.

If Bedrock is slow (cold model, high traffic), or if the audio file is large, this can
exceed 30 seconds and the Lambda times out. The user sees a WebSocket disconnect with no
error message.

**Evidence:**
- `template.yml` line 695: `Timeout: 30`
- `app.py` `handle_audio_response` lines 208-398: full pipeline
- Batch transcription comment: "15s average, most reliable"
- No timeout handling or partial-result fallback in the handler

**Remediation Steps:**

1. Increase timeout to 60 seconds:
```yaml
WebSocketDefaultFunction:
  Properties:
    Timeout: 60
```

2. API Gateway WebSocket has a 29-second integration timeout by default. For Lambda
   proxy integrations, this is the *response* timeout — but WebSocket `$default` route
   doesn't need to return a response (it sends messages via the Management API). Verify
   that the WebSocket API stage doesn't have a restrictive timeout override.

3. Add a timeout guard in the handler that sends a user-friendly message before Lambda
   kills the process:
```python
import signal

def timeout_handler(signum, frame):
    send_message(connection_id, {
        'type': 'error',
        'message': 'Processing is taking longer than expected. Please try again.'
    })
    raise TimeoutError("Lambda approaching timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(25)  # Fire 5 seconds before Lambda timeout
```

**Note per project steering rules:** Changing the timeout doesn't require IAM policy
changes — it's a function configuration property, not an API call change.

---

### Area #12: Global Lambda Timeout of 3s — Dangerous Default

**Severity: Medium | Ease: Easy | Effort: S**

**Why it matters:** SAM Globals set `Timeout: 3` (line 29 of `template.yml`). Any Lambda
function that doesn't explicitly override this gets a 3-second timeout. For functions that
call DynamoDB + Cognito + SES, 3 seconds is dangerously tight — especially on cold starts
where the Python runtime + boto3 initialization alone can take 1-2 seconds.

Most functions do override this (the assignment functions set 30-60s, video functions set
120-300s), but any new function added without an explicit timeout inherits the 3s default
and will fail intermittently.

**Evidence:**
- `template.yml` line 29: `Timeout: 3` in Globals
- Functions that override: WebSocketDefault (30s), assignment functions (30s), video functions (120-300s)
- Risk: any new function without explicit timeout gets 3s

**Remediation Steps:**

Change the global default to a safer value:
```yaml
Globals:
  Function:
    Timeout: 10  # Safe default for DynamoDB + auth operations
```

Functions that need more (video processing, conversations) already override this.
Functions that need less (simple reads) won't be harmed by a 10s ceiling — Lambda
billing is per-100ms, so unused timeout doesn't cost anything.

**This is a 1-line change.**

---

### Area #13: Conversation State Grows Unbounded per DynamoDB Item

**Severity: Medium | Ease: Medium | Effort: M**

**Why it matters:** `ConversationState` persists the full conversation history (all turns
with user text, AI response, scores, reasoning, audio URLs) to DynamoDB on every turn via
`set_conversation()`. A 20-turn conversation with detailed AI responses can produce a
DynamoDB item approaching the 400KB limit. The `config.py` `score_goal` is 12 and `max_turns`
is 20, so conversations can be long.

DynamoDB silently rejects items over 400KB with a `ValidationException`. If a conversation
hits this limit mid-flow, the state save fails and the user loses their conversation with
no recovery path.

**Evidence:**
- `conversation_state.py` — `to_dict()` serializes full `turns` list with all fields
- `app.py` — `set_conversation(connection_id, state)` called after every turn
- Each turn stores: `user_text`, `ai_response`, `score`, `reasoning`, `audio_url`
- No size check, no truncation, no pagination

**Remediation Steps:**

1. Add a size guard before writing to DynamoDB:
```python
import sys

def set_conversation(connection_id: str, state: ConversationState):
    state_dict = state.to_dict()
    estimated_size = sys.getsizeof(json.dumps(state_dict, cls=DecimalEncoder))
    if estimated_size > 350_000:  # 350KB safety margin
        # Truncate older turn reasoning to save space
        for turn in state_dict.get('turns', [])[:-3]:  # Keep last 3 turns full
            turn.pop('reasoning', None)
    # ... write to DynamoDB
```

2. Alternatively, store only the last N turns in the DynamoDB item and archive older
   turns to S3. The LLM context window doesn't need all 20 turns anyway — `llm.py`
   already passes the full history but Bedrock has its own context limits.

3. Long-term: consider storing turns as separate DynamoDB items with a GSI on
   `connection_id`, enabling pagination and eliminating the 400KB risk entirely.

---

### Area #14: Old Amplify URL in CORS Allowlist

**Severity: Low | Ease: Easy | Effort: S**

**Why it matters:** `cors.py` line 11 still includes `https://main.d33jt7rnrasyvj.amplifyapp.com`
in `_ALLOWED_ORIGINS`. This isn't actively harmful — the old URL just gets echoed back if
someone sends a request with that Origin header. But it's unnecessary attack surface and
confusing for anyone reading the code.

**Evidence:**
- `SamLambda/functions/shared/cors.py` line 11
- `SamLambda/functions/shared/python/cors.py` — identical copy

**Remediation:** Remove the old Amplify URL from both copies:
```python
_ALLOWED_ORIGINS = [
    'https://www.soulreel.net',
    'https://soulreel.net',
    'http://localhost:5173',
    'http://localhost:8080',
]
```

---

### Area #15: `console.log` Debug Statements in AuthContext and ConversationInterface

**Severity: Low | Ease: Easy | Effort: S**

**Why it matters:** `AuthContext.tsx` contains multiple `console.log` calls that output auth
state, user attributes, and persona information to the browser console in production.
`ConversationInterface.tsx` logs WebSocket messages, audio blob sizes, S3 keys, and upload
URLs. Any user opening DevTools sees internal implementation details.

**Evidence:**
- `AuthContext.tsx` — `console.log` calls throughout `checkAuthState`, `login`, `signupWithPersona`
- `ConversationInterface.tsx` — `console.log` calls for WebSocket messages, audio processing,
  S3 upload details (lines 65, 67, 72, 80, 87, 113, 127, 155, 170, 178, 185, 192, 199)

**Remediation:**
```typescript
// Option A: Conditional logging
const log = import.meta.env.DEV ? console.log : () => {};

// Option B: Remove them entirely — use breakpoints for debugging
```

---

### Area #16: `createAssignment` Manually Parses JWT Instead of Using Cognito Authorizer Claims

**Severity: Low | Ease: Easy | Effort: S**

This is a subset of Area #5 but worth calling out specifically for `createAssignment/app.py`
because it's the most complex assignment function (~250 lines of handler logic) and the
manual JWT parsing adds unnecessary attack surface. The Cognito authorizer already validates
the token — the handler just needs to read the claims.

See Area #5 for the full remediation plan.

---

### Area #17: Remaining `Resource: '*'` on `transcribe:StartStreamTranscription`

**Severity: Low | Ease: Easy | Effort: S**

**Why it matters:** The WebSocketDefaultFunction IAM policy has `Resource: '*'` for
`transcribe:StartStreamTranscription` (line 735 of `template.yml`). The batch transcription
actions are properly scoped to `arn:aws:transcribe:${AWS::Region}:${AWS::AccountId}:transcription-job/*`,
but the streaming action uses a wildcard.

**Evidence:**
- `template.yml` lines 733-735:
```yaml
- Effect: Allow
  Action: transcribe:StartStreamTranscription
  Resource: '*'
```

**Remediation:**
AWS Transcribe Streaming doesn't support resource-level permissions — `Resource: '*'` is
actually required for `StartStreamTranscription`. Add a comment explaining this:
```yaml
- Effect: Allow
  Action: transcribe:StartStreamTranscription
  Resource: '*'  # Streaming Transcribe does not support resource-level permissions
```

No actual change needed — just documentation.

---

### Area #18: `ForgotPassword` Page May Still Reference Missing Auth Function

**Severity: Low | Ease: Easy | Effort: S**

**Why it matters:** The routes for `/forgot-password` and `/reset-password` were added to
`App.tsx` (confirmed in this audit). However, the previous audit noted that `ForgotPassword.tsx`
destructures `forgotPassword` from `useAuth()`, which may not exist in `AuthContext.tsx`.
If the function wasn't added to the context, the page will crash when accessed.

**Evidence:**
- `App.tsx` lines 55-56: routes exist ✅
- `ForgotPassword.tsx` — needs `forgotPassword` from `useAuth()`
- `AuthContext.tsx` — needs verification that `forgotPassword` was added

**Remediation:** Verify `AuthContext.tsx` exports `forgotPassword`. If not, add it:
```typescript
const forgotPassword = async (email: string) => {
  setIsLoading(true);
  try {
    await resetPassword({ username: email });
    navigate('/reset-password', { state: { email } });
  } catch (error) {
    console.error('Forgot password error:', error);
    throw error;
  } finally {
    setIsLoading(false);
  }
};
```

Import `resetPassword` from `aws-amplify/auth` and add `forgotPassword` to the context value.


---

## Executive Summary

**Overall Grade: B**

This codebase has made remarkable progress across three audits in 48 hours. The trajectory
is C- → B- → B, driven by systematic fixes rather than cosmetic changes. The developer has
addressed the most dangerous issues from each audit cycle: conversation state moved to DynamoDB,
CORS locked to production domain, CI/CD pipelines created with OIDC auth, SSM batch loading
with caching, text-path parallelism, dead code cleanup, route-level auth guards, shared utils
layer created and adopted by 30+ functions, React Query adopted for statistics, backend smoke
tests added to CI, ProtectedRoute redirect fixed, test email gate removed, and QueryClient
properly configured.

**What's genuinely solid:**
- 3-tier transcription fallback (Deepgram → AWS Streaming → AWS Batch) with timing logs
- Parallel LLM calls via ThreadPoolExecutor for scoring + response generation
- Proper rollback logic in `createAssignment` — if email fails, DB writes are cleaned up
- N+1 Cognito queries parallelized in `getRelationships`
- CI/CD with OIDC (no more long-lived IAM keys), lint, type-check, and smoke tests
- KMS encryption on S3 and DynamoDB, GuardDuty enabled, CloudTrail active
- SharedUtilsLayer adopted by 30+ functions — the architecture is right
- `useStatistics` properly migrated to React Query with staleTime and placeholderData
- Error responses in Lambda handlers mostly return safe generic messages now

**Top 4 Time Bombs (fix before anything else):**

1. **Localhost URLs in every benefactor email** — Every email sent to benefactors contains
   `http://localhost:8080` links. Invitations, access grants, check-ins — all broken for
   real users. Root cause: `APP_BASE_URL` env var never set in `template.yml`. This is the
   single most impactful bug in the codebase right now.

2. **`.env` committed with live credentials** — Cognito User Pool Client ID, Identity Pool ID,
   and API Gateway URL are in git history. The `.gitignore` rule was added after the commit.
   Needs `git rm --cached` + history purge + credential rotation.

3. **Hardcoded WebSocket URL** — `ConversationInterface.tsx` hardcodes the WebSocket API
   endpoint. If the API is redeployed with a new ID, conversations break for all users
   until a frontend deploy catches up.

4. **Shared DAL layer leaks `str(e)` and hardcodes table names** — `assignment_dal.py` and
   `invitation_utils.py` return exception details in error dicts and use hardcoded DynamoDB
   table names. These modules are imported by every assignment function, so the issues
   propagate widely.

**Highest-ROI Starting Points:**
1. Add `APP_BASE_URL: 'https://www.soulreel.net'` to SAM Globals + find-replace localhost
   in 10 Lambda files (30 minutes, fixes all benefactor emails)
2. `git rm --cached FrontEndCode/.env` (5 minutes, stops tracking secrets)
3. Move WebSocket URL to env var (5 minutes, eliminates fragile hardcoding)
4. Clean up shared DAL error messages and table names (1 hour, fixes the last layer of
   inconsistency)

**The path from B to B+ is clear:** Fix the localhost email URLs (critical user-facing bug),
clean up the shared DAL layer (last pocket of technical debt), and migrate Dashboard's
ProgressSection to React Query (last major manual-fetch holdout). No architectural changes
needed — the architecture is sound. It's about finishing the last 20% of adoption.

---

## Grade Progression

| Dimension | Mar 14 (C-) | Mar 15 AM (B-) | Mar 15 PM (B) | Notes |
|---|---|---|---|---|
| Reliability | D | B | B | DynamoDB state, parallel text path, SSM batch — all solid |
| Security | D | C+ | B- | OIDC, safe error messages, but `.env` still committed, localhost emails |
| Maintainability | D+ | C+ | B- | SharedUtilsLayer at 30+ functions, but DAL layer still inconsistent |
| Performance | C- | C | C+ | TTS uncached, but parallelism good, React Query adopted for stats |
| Observability | C | C | C+ | Smoke tests in CI, structured logging in conversation flow |
| CI/CD | F | B- | B+ | OIDC, lint, type-check, smoke tests, stuck-job handling |
| Frontend Architecture | C- | C+ | B | React Query configured + adopted, routes fixed, ProtectedRoute fixed |
| Persona/Relationships | C | C | C+ | Race condition remains, but DAL layer exists, access conditions work |
| **Overall** | **C-** | **B-** | **B** | Consistent upward trajectory. Localhost emails are the last critical bug. |

---

## Quick Wins Summary

Items completable in under 30 minutes each, with immediate impact.

| # | Fix | Effort | Impact | Files |
|---|---|---|---|---|
| 1 | Add `APP_BASE_URL` to SAM Globals | 5 min | Fixes email_templates.py fallback | `template.yml` |
| 2 | Find-replace `localhost:8080` in 10 Lambda files | 25 min | Fixes all benefactor emails | See Area #1 file list |
| 3 | `git rm --cached FrontEndCode/.env` | 5 min | Stop tracking secrets | `.env` |
| 4 | Move WebSocket URL to env var | 5 min | Eliminates hardcoded endpoint | `ConversationInterface.tsx`, `.env` |
| 5 | Remove old Amplify URL from CORS allowlist | 5 min | Cleanup | `cors.py` (both copies) |
| 6 | Remove `console.log` from AuthContext + ConversationInterface | 15 min | Stop leaking debug info | `AuthContext.tsx`, `ConversationInterface.tsx` |
| 7 | Bump global Lambda timeout from 3s to 10s | 1 min | Safer default for new functions | `template.yml` line 29 |
| 8 | Add comment on `transcribe:StartStreamTranscription` wildcard | 2 min | Documentation | `template.yml` |
| 9 | Update `email_templates.py` fallback default | 5 min | Defense in depth for emails | `email_templates.py` (both copies) |
| 10 | Replace `extract_user_id_from_jwt` with authorizer claims in 1 function | 10 min | Prove the pattern, then repeat | `createAssignment/app.py` |
| 11 | Increase WebSocket Lambda timeout to 60s | 1 min | Prevent timeout on batch transcription fallback | `template.yml` |
| 12 | Verify `forgotPassword` exists in AuthContext | 5 min | Prevent crash on password reset page | `AuthContext.tsx` |

**Recommended order:** 1 → 2 → 9 (email fix batch) → 3 → 4 → 7 → 11 → 5 → 6 → 10 → 12 → 8

Items 1 + 2 + 9 should be a single commit + deploy — they fix the critical email bug.
Items 3 + 4 are a natural frontend commit. Items 7 + 11 are a template.yml batch.

---

## Open Questions

**1. SharedUtilsLayer directory structure — `shared/` vs `shared/python/`?**
Both `functions/shared/cors.py` and `functions/shared/python/cors.py` exist with identical
content. The layer's `ContentUri` determines which path is used at runtime. If both are
maintained separately, they will drift. Consolidate to one canonical location and delete
the other, or use a build step that copies files.

**2. Should the 10 inline email templates be migrated to `email_templates.py`?**
The centralized `email_templates.py` module exists and has well-structured templates for
7 email types. But 10 Lambda functions still have their own inline HTML email templates
(the ones with hardcoded localhost). The quick fix is find-replace localhost → env var.
The proper fix is migrating all inline templates to use the centralized module. The latter
is more work but eliminates future drift.

**3. Conversation state size — what's the actual p99 item size?**
The 400KB DynamoDB limit concern (Area #13) is theoretical. Check CloudWatch for
`ConversationStateDB` consumed write capacity and item sizes. If conversations typically
end at 8-12 turns with short AI responses, the 400KB limit may never be a practical risk.
If conversations regularly hit 20 turns with detailed responses, it's worth addressing.

**4. TTS caching ROI — what's the cache hit rate?**
The Polly caching proposal (Area #7) adds an S3 `head_object` call on every turn. If AI
responses are mostly unique (personalized follow-ups), the cache hit rate will be low and
the overhead not worth it. If there are common phrases (greetings, transitions, closing
remarks), caching is a clear win. Analyze a sample of conversation transcripts to estimate
the hit rate before implementing.

**5. Password reset flow — is it tested end-to-end?**
Routes were added and the page components exist, but the `forgotPassword` function in
AuthContext needs verification. If it's not wired up, the pages will crash. If it is wired
up, test the full flow: forgot password → email with code → reset password → login.

**6. `processVideo` vs `uploadVideoResponse` — are both still needed?**
Both are ~700 lines with significant overlap. If one is a newer version of the other,
remove the old one. If they serve different purposes (e.g., one for direct upload, one for
S3-triggered processing), document the distinction and extract shared code.

**7. Scale targets for TTS and conversation volume?**
Current architecture handles single-digit concurrent conversations fine. At 50+ concurrent
conversations, Polly rate limits (default 8 concurrent `SynthesizeSpeech` calls) become a
bottleneck. If scaling is planned, consider Polly provisioned concurrency or pre-generating
common audio clips.

**8. Denormalize user attributes into PersonaRelationshipsDB?**
The N+1 Cognito query fix (ThreadPoolExecutor) works but adds latency proportional to
relationship count. Storing `email`, `first_name`, `last_name` in the relationship record
at write time eliminates the Cognito dependency on reads entirely. Worth doing if
relationship count per user is expected to grow beyond 5-10.
