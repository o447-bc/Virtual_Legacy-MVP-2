# Technical Debt & Quality Audit
## SoulReel / Virtual Legacy — Full-Stack AWS Application
**Audit Date:** March 14, 2026
**Overall Grade: C-**

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Prioritized Improvement Areas](#prioritized-improvement-areas)
4. [Detailed Remediation Plans](#detailed-remediation-plans)
5. [Quick Wins Summary](#quick-wins-summary)
6. [Open Questions](#open-questions)

---

## Executive Summary

The app has a solid domain model and some genuinely good patterns: structured logging,
KMS encryption at rest, CloudTrail auditing, GuardDuty, a three-tier transcription
fallback (Deepgram → AWS Streaming → AWS Batch), and a well-thought-out access
conditions system. The security infrastructure investment is real and commendable.

**Top 6 Time Bombs:**

1. Conversation state stored in Lambda memory — data loss under any real load
2. CORS wildcard `*` on a production Cognito-authenticated API — CSRF/token-theft vector
3. Secrets and SSH keys committed to the repository — immediate rotation required
4. TTS/conversation latency doubled on text path due to sequential LLM calls
5. Shared utility code copy-pasted across 5+ Lambda directories — divergent bugs guaranteed
6. No CI/CD pipeline — every deploy is a manual, error-prone ceremony

**Highest-ROI Starting Points:** Fix CORS (#2), rotate secrets (#3), fix text-path
parallelism (#4), move conversation state to DynamoDB (#1). These four address the most
critical security, reliability, and UX issues with contained effort.

---

## Architecture Overview

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| Auth | AWS Cognito (User Pool `us-east-1_KsG65yYlo`, managed outside CloudFormation) |
| API | API Gateway REST + WebSocket API (SAM-managed) |
| Backend | Python 3.12 Lambda functions (SAM) |
| AI/ML | Bedrock (Claude 3.5 Sonnet conversation, Claude 3 Haiku scoring), Polly (TTS), Deepgram + AWS Transcribe |
| Database | DynamoDB (8 tables: allQuestionDB, userQuestionStatusDB, userQuestionLevelProgressDB, userStatusDB, PersonaRelationshipsDB, AccessConditionsDB, EngagementDB, WebSocketConnectionsDB) |
| Storage | S3 (`virtual-legacy` bucket), KMS CMK encryption |
| Email | SES |
| Monitoring | CloudTrail, GuardDuty, CloudWatch |
| Hosting | AWS Amplify (frontend), API Gateway (backend) |
| Deployment | SAM CLI (backend), manual dist.zip upload (frontend) |

**Persona Model:** Two types — `legacy_maker` (records answers) and `legacy_benefactor`
(views content). Relationship stored in `PersonaRelationshipsDB` with access conditions
(`immediate`, `time_delayed`, `inactivity_trigger`, `manual_release`).

---

## Prioritized Improvement Areas

Ordered by **severity × ease** (highest combined impact first).

| # | Title | Severity | Ease | Effort |
|---|---|---|---|---|
| 1 | Conversation state in Lambda memory | Critical | Medium | M |
| 2 | CORS wildcard `*` on production API | Critical | Easy | S |
| 3 | Secrets committed to repository | Critical | Easy | S |
| 4 | TTS/conversation latency — sequential blocking | High | Medium | M |
| 5 | Shared code duplicated across Lambda functions | High | Medium | M |
| 6 | N+1 Cognito queries in relationship loading | High | Medium | S |
| 7 | Persona race condition during invited benefactor signup | High | Hard | M |
| 8 | Dead code and variant files | High | Easy | S |
| 9 | No route-level auth guards | High | Easy | S |
| 10 | React Query installed but unused | Medium | Medium | M |
| 11 | SSM parameters loaded individually on every message | Medium | Easy | S |
| 12 | Error messages leak internal details | Medium | Easy | S |
| 13 | Hardcoded S3 bucket names and AWS resources | Medium | Easy | S |
| 14 | No DynamoDB pagination | Medium | Medium | S |
| 15 | Wildcard IAM resource ARNs | Medium | Easy | S |
| 16 | Silent fire-and-forget API call in login | Medium | Easy | S |
| 17 | Manual deployment process — no CI/CD | Medium | Hard | L |


---

## Detailed Remediation Plans

---

### Area #1: Conversation State Stored in Lambda Memory

**Why it matters:** A mid-conversation user loses everything if the Lambda container
recycles. AWS can kill containers at any time — under load, after inactivity, or during
a deployment. This is a silent data-loss bug that will manifest unpredictably in
production.

**Evidence:**
- `SamLambda/functions/conversationFunctions/wsDefault/conversation_state.py` lines 72-82
- `_active_conversations: Dict[str, ConversationState] = {}` — a plain Python dict in
  Lambda process memory
- `WebSocketConnectionsTable` already exists in DynamoDB but only stores connection IDs

**Remediation Steps:**

1. Add a `ConversationStateDB` DynamoDB table to `template.yml` with `connectionId` as
   the hash key and a TTL attribute.
2. Rewrite `get_conversation`, `set_conversation`, and `remove_conversation` in
   `conversation_state.py` to read/write DynamoDB instead of the in-memory dict.
3. Add a `from_dict` classmethod to `ConversationState` for deserialization.
4. Grant `WebSocketDefaultFunction` read/write permissions on the new table.
5. Remove the `_active_conversations` global dict entirely.
6. Add a TTL of 2 hours on all conversation state items.

**Before:**
```python
# conversation_state.py
_active_conversations: Dict[str, ConversationState] = {}

def get_conversation(connection_id: str) -> Optional[ConversationState]:
    return _active_conversations.get(connection_id)

def set_conversation(connection_id: str, state: ConversationState):
    _active_conversations[connection_id] = state
```

**After:**
```python
import boto3, os, time
dynamodb = boto3.resource('dynamodb')
_table = dynamodb.Table(os.environ['CONVERSATION_STATE_TABLE'])

def get_conversation(connection_id: str) -> Optional[ConversationState]:
    resp = _table.get_item(Key={'connectionId': connection_id})
    item = resp.get('Item')
    return ConversationState.from_dict(item) if item else None

def set_conversation(connection_id: str, state: ConversationState):
    _table.put_item(Item={**state.to_dict(), 'ttl': int(time.time()) + 7200})

def remove_conversation(connection_id: str):
    _table.delete_item(Key={'connectionId': connection_id})
```

**SAM template addition:**
```yaml
ConversationStateTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: ConversationStateDB
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: connectionId
        AttributeType: S
    KeySchema:
      - AttributeName: connectionId
        KeyType: HASH
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
    SSESpecification:
      SSEEnabled: true
      SSEType: KMS
      KMSMasterKeyId: !GetAtt DataEncryptionKey.Arn
```

**Gotchas:**
- DynamoDB item size limit is 400KB. Long conversations with many turns could approach
  this. Consider storing only the last N turns in DynamoDB and archiving older turns to S3.
- Add `ConversationStateTable` to `WebSocketDefaultFunction` policies.
- The `from_dict` method must handle Decimal types from DynamoDB (use a custom decoder).

**Tests to add:**
- Unit test: conversation survives a simulated container restart (mock DynamoDB)
- Integration test: start conversation, simulate cold start, verify state is recovered


---

### Area #2: CORS Wildcard `*` on Production API

**Why it matters:** `Access-Control-Allow-Origin: *` on a Cognito-authenticated API
means any website can make cross-origin requests using a user's browser-stored tokens.
Combined with XSS on any third-party site a user visits, this is a token-theft vector.
The SAM template even has a `# TODO: Implement dynamic CORS` comment acknowledging this.

**Evidence:**
- `SamLambda/template.yml` Globals section: `AllowOrigin: '''*'''`
- Every single Lambda `app.py` response includes `'Access-Control-Allow-Origin': '*'`
- `GatewayResponseUnauthorized`, `GatewayResponseDefault4XX`, `GatewayResponseDefault5XX`
  all use `'*'`

**Remediation Steps:**

1. Replace the wildcard in `template.yml` Globals with your actual domain:
```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: '''https://main.d33jt7rnrasyvj.amplifyapp.com'''
```

2. Create a shared CORS headers constant in a shared module:
```python
# functions/shared/cors.py
import os

ALLOWED_ORIGIN = os.environ.get(
    'ALLOWED_ORIGIN',
    'https://main.d33jt7rnrasyvj.amplifyapp.com'
)

CORS_HEADERS = {
    'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}
```

3. Update all Lambda handlers to import and use `CORS_HEADERS`.
4. Update the three `GatewayResponse` resources in `template.yml`.
5. Add `ALLOWED_ORIGIN` as an environment variable to all Lambda functions.

**For local development**, add a second allowed origin via a Lambda that checks the
`Origin` request header against an allowlist:
```python
def get_cors_origin(event):
    origin = event.get('headers', {}).get('origin', '')
    allowed = [
        'https://main.d33jt7rnrasyvj.amplifyapp.com',
        'http://localhost:5173',
        'http://localhost:8080',
    ]
    return origin if origin in allowed else allowed[0]
```

**Gotchas:** If you use a custom domain later, update the environment variable — don't
hardcode the Amplify URL in source code.


---

### Area #3: Secrets and Credentials Committed to Repository

**Why it matters:** Live API Gateway URLs, Cognito Pool IDs, Client IDs, and SSH private
key material are in the repository. Anyone with repo access can impersonate users,
enumerate your Cognito pool, or use the SSH key. Git history preserves these even after
deletion.

**Evidence:**
- `FrontEndCode/.env` — live `VITE_API_BASE_URL`, `VITE_USER_POOL_CLIENT_ID`,
  `VITE_IDENTITY_POOL_ID`
- Root-level `ssh-keygen -t ed25519 -C "oliver@o447.net"` and `.pub` files
- `SamLambda/template.yml` Parameters defaults contain live User Pool ID and ARN
- AWS account ID `962214556635` hardcoded in `processVideo/app.py`,
  `uploadVideoResponse/app.py`, and `template.yml`

**Remediation Steps:**

1. **Immediately rotate** the Cognito User Pool Client ID (`5j6k6kb1tbnncbnpsrc5cgin2l`).
   Go to Cognito Console → App clients → Delete and recreate.

2. **Delete the SSH key files** from the repository:
```bash
git rm "ssh-keygen -t ed25519 -C \"oliver@o447.net\""
git rm "ssh-keygen -t ed25519 -C \"oliver@o447.net\".pub"
```

3. **Purge secrets from git history** using BFG Repo-Cleaner:
```bash
bfg --delete-files ".env" --no-blob-protection
bfg --replace-text secrets.txt  # list of secrets to redact
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

4. **Verify `.gitignore`** includes `.env` (it's listed but the file is present):
```
FrontEndCode/.env
*.pem
id_ed25519
id_ed25519.pub
```

5. **Remove hardcoded account IDs** from Lambda source — replace with environment
   variable or dynamic lookup:
```python
# BEFORE
"Layer ARN: arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1"

# AFTER — reference via environment variable set in template.yml
FFMPEG_LAYER_ARN = os.environ.get('FFMPEG_LAYER_ARN', 'not-configured')
```

6. **Move SAM parameter defaults** out of `template.yml` into `samconfig.toml`
   `parameter_overrides` so they're not in source-controlled template defaults.

7. For CI/CD, use **OIDC federation** (GitHub Actions → AWS) instead of long-lived
   access keys.


---

### Area #4: TTS/Conversation Latency — Sequential Blocking

**Why it matters:** Every conversation turn adds unnecessary latency. The text input
path calls scoring and AI generation sequentially, even though a parallel version
already exists in the codebase. After that, Polly TTS is fully synchronous with no
caching. Each turn is 3-6 seconds slower than it needs to be.

**Evidence:**
- `wsDefault/app.py` `handle_user_response` (lines 83-210): calls `score_response_depth`
  then `generate_ai_response` sequentially
- `wsDefault/app.py` `handle_audio_response` (lines 213-400): correctly uses
  `process_user_response_parallel` — the fix already exists, just not applied to the
  text path
- `wsDefault/speech.py`: `synthesize_speech` → read full `AudioStream` into memory →
  `put_object` to S3 → `generate_presigned_url` — fully sequential, no streaming, no
  caching

**Remediation Steps:**

1. Fix `handle_user_response` to use the parallel function (1-line change):
```python
# BEFORE
turn_score, reasoning = score_response_depth(
    user_text, config['scoring_prompt'], config['llm_scoring_model']
)
ai_response = generate_ai_response(
    state.question_text, state.turns, user_text,
    config['system_prompt'], config['llm_conversation_model']
)

# AFTER
ai_response, turn_score, reasoning = process_user_response_parallel(
    state.question_text, state.turns, user_text,
    config['system_prompt'], config['scoring_prompt'],
    config['llm_conversation_model'], config['llm_scoring_model']
)
```

2. Start Polly synthesis in parallel with state updates using `ThreadPoolExecutor`:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=2) as executor:
    tts_future = executor.submit(
        text_to_speech, ai_response, user_id,
        state.question_id, state.turn_number,
        config['polly_voice_id'], config['polly_engine']
    )
    state.add_turn(user_text, ai_response, turn_score, reasoning)
    should_continue, reason = state.should_continue(
        config['score_goal'], config['max_turns']
    )
    audio_url = tts_future.result()
```

3. Cache common Polly phrases (greetings, transitions) in S3 with a deterministic key
   based on `hash(text + voice_id)`. Check cache before calling Polly:
```python
def text_to_speech(text: str, ...) -> str:
    cache_key = f"tts-cache/{hashlib.md5(f'{text}{voice_id}'.encode()).hexdigest()}.mp3"
    # Check if cached version exists
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
        return s3_client.generate_presigned_url('get_object',
            Params={'Bucket': S3_BUCKET, 'Key': cache_key}, ExpiresIn=3600)
    except ClientError:
        pass  # Not cached, synthesize
    # ... existing Polly call, upload to cache_key
```

4. Add **provisioned concurrency** to `WebSocketDefaultFunction` to eliminate cold
   starts on the critical conversation path:
```yaml
WebSocketDefaultFunction:
  Type: AWS::Serverless::Function
  Properties:
    AutoPublishAlias: live
    ProvisionedConcurrencyConfig:
      ProvisionedConcurrentExecutions: 2
```

5. Consider switching to **Polly streaming** for longer AI responses — stream the audio
   bytes directly to S3 via multipart upload instead of buffering the entire response.

**AWS changes needed:**
- Enable provisioned concurrency on `WebSocketDefaultFunction`
- Add a CloudFront distribution in front of the TTS cache S3 prefix for edge caching

**Tests to add:**
- Latency benchmark: measure p50/p95 turn-around time before and after
- Unit test: verify parallel path is used for both text and audio handlers


---

### Area #5: Shared Code Duplicated Across Lambda Functions

**Why it matters:** `assignment_dal.py`, `email_utils.py`, `invitation_utils.py`,
`logging_utils.py`, and `validation_utils.py` are physically copied into at least 4
Lambda function directories. A `shared/` directory exists but is not deployed as a
Lambda Layer. Any bug fix must be applied to 4-5 copies — and they will diverge.

**Evidence:**
- `SamLambda/functions/assignmentFunctions/createAssignment/` — 6 files including all
  shared utilities
- `SamLambda/functions/assignmentFunctions/acceptDeclineAssignment/` — own copies of
  `assignment_dal.py`, `logging_utils.py`, `validation_utils.py`
- `SamLambda/functions/assignmentFunctions/updateAssignment/` — same
- `SamLambda/functions/cognitoTriggers/postConfirmation/` — own copies
- `SamLambda/functions/shared/` — the canonical versions, unused as a Layer

**Remediation Steps:**

1. Create a Lambda Layer from the `shared/` directory. Add to `template.yml`:
```yaml
SharedUtilsLayer:
  Type: AWS::Serverless::LayerVersion
  Properties:
    LayerName: soulreel-shared-utils
    ContentUri: functions/shared/
    CompatibleRuntimes:
      - python3.12
    RetentionPolicy: Retain
```

2. Add the layer to all affected functions:
```yaml
WebSocketDefaultFunction:
  Properties:
    Layers:
      - !Ref SharedUtilsLayer
      - arn:aws:lambda:us-east-1:962214556635:layer:ffmpeg-layer:1
```

3. Update imports in each Lambda. Lambda Layers are mounted at `/opt/python/`:
```python
# BEFORE (in createAssignment/app.py)
from assignment_dal import create_assignment_record

# AFTER
from shared.assignment_dal import create_assignment_record
# or add /opt/python to sys.path in a conftest/init
```

4. Delete the duplicate files from each function directory after verifying the Layer
   import works.

5. Run the existing test suite to confirm no regressions.

**Gotchas:**
- Lambda Layer path is `/opt/python/` for Python runtimes. You may need to add
  `sys.path.insert(0, '/opt/python')` in a shared `__init__.py` or use the
  `PYTHONPATH` environment variable.
- Layer versions are immutable — each `sam deploy` creates a new version. Use
  `!Ref SharedUtilsLayer` (not a hardcoded ARN) so functions always get the latest.


---

### Area #6: N+1 Cognito Queries in Relationship Loading

**Why it matters:** `getRelationships` fetches all relationships from DynamoDB, then
loops through each one calling `cognito.admin_get_user()` individually. With 10
benefactors, that's 10 sequential Cognito API calls. Cognito's default rate limit for
`AdminGetUser` is 5 RPS — this will throttle under any real usage.

**Evidence:**
- `SamLambda/functions/relationshipFunctions/getRelationships/app.py` lines 30-43:
```python
for rel in relationships:
    response = cognito.admin_get_user(
        UserPoolId=user_pool_id,
        Username=rel['related_user_id']
    )
```

**Remediation Steps:**

**Option A (quick fix): Parallelize the Cognito calls**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def enrich_relationship(rel, cognito, user_pool_id):
    try:
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id, Username=rel['related_user_id']
        )
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                rel['related_user_email'] = attr['Value']
            elif attr['Name'] == 'given_name':
                rel['related_user_first_name'] = attr['Value']
            elif attr['Name'] == 'family_name':
                rel['related_user_last_name'] = attr['Value']
    except ClientError:
        pass
    return rel

with ThreadPoolExecutor(max_workers=10) as executor:
    relationships = list(executor.map(
        lambda r: enrich_relationship(r, cognito, user_pool_id),
        relationships
    ))
```

**Option B (proper fix): Denormalize into DynamoDB at write time**

Store `email`, `first_name`, `last_name` directly in `PersonaRelationshipsDB` when the
relationship is created. Update via a Cognito post-authentication trigger if the user
changes their name.

```python
# In createRelationship/app.py and postConfirmation/app.py
# When writing the relationship record, include user attributes:
table.put_item(Item={
    'initiator_id': initiator_id,
    'related_user_id': related_user_id,
    'related_user_email': benefactor_email,
    'related_user_first_name': first_name,
    'related_user_last_name': last_name,
    # ... other fields
})
```

Option B eliminates the Cognito dependency entirely from the read path and is the
recommended long-term solution.

**Files to change:**
- `getRelationships/app.py` — remove Cognito loop
- `createRelationship/app.py` — add user attributes at write time
- `postConfirmation/app.py` — add user attributes when creating benefactor relationship
- `PersonaRelationshipsDB` schema — no migration needed (DynamoDB is schemaless)


---

### Area #7: Persona Race Condition During Invited Benefactor Signup

**Why it matters:** The frontend forcibly overrides the user's `personaType` to
`'legacy_benefactor'` on the client side because the postConfirmation Lambda may not
have finished writing the Cognito attribute yet. This is a documented race condition
that means the frontend is lying about auth state — and if the race is lost, the user
lands on the wrong dashboard.

**Evidence:**
- `FrontEndCode/src/contexts/AuthContext.tsx` lines ~185-200:
```typescript
// postConfirmation Lambda runs asynchronously and may not have finished writing
// the profile attribute to Cognito yet (race condition). We call checkAuthState
// to get the real user.id, then forcibly set personaType to 'legacy_benefactor'
setUser(prev => prev ? { ...prev, personaType: 'legacy_benefactor' } : prev);
```

**Remediation Steps:**

1. In `postConfirmation/app.py`, ensure `AdminUpdateUserAttributes` completes and add
   error handling that fails the trigger if it doesn't:
```python
try:
    cognito.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{'Name': 'profile', 'Value': json.dumps({'persona_type': persona_type})}]
    )
except ClientError as e:
    print(f"CRITICAL: Failed to set persona type for {username}: {e}")
    raise  # Fail the trigger — better to fail loudly than silently
```

2. On the frontend, replace the client-side override with a polling retry:
```typescript
const waitForPersonaAttribute = async (expectedPersona: string, maxAttempts = 5) => {
  for (let i = 0; i < maxAttempts; i++) {
    const attrs = await fetchUserAttributes({ forceRefresh: true });
    if (attrs.profile) {
      const profile = JSON.parse(attrs.profile);
      if (profile.persona_type === expectedPersona) return profile.persona_type;
    }
    await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // backoff
  }
  return expectedPersona; // fallback after exhausting retries
};
```

3. Remove the `setUser(prev => ...)` override from `signupWithPersona`.

**Files to change:**
- `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`
- `FrontEndCode/src/contexts/AuthContext.tsx`


---

### Area #8: Dead Code and Variant Files

**Why it matters:** At least 12 dead/variant files exist in the frontend, plus duplicate
Lambda function versions. This creates confusion about which version is canonical,
inflates bundle analysis noise, and makes onboarding harder.

**Evidence:**

Frontend dead files:
- `FrontEndCode/src/App-baseline.tsx`
- `FrontEndCode/src/App-home-working.tsx`
- `FrontEndCode/src/App-simple.tsx`
- `FrontEndCode/src/App-test.tsx`
- `FrontEndCode/src/App-with-auth.tsx`
- `FrontEndCode/src/App-working.tsx`
- `FrontEndCode/src/pages/Home-fixed.tsx`
- `FrontEndCode/src/pages/Home-nolinks.tsx`
- `FrontEndCode/src/pages/Home-simple.tsx`
- `FrontEndCode/src/pages/Login-simple.tsx`
- `FrontEndCode/src/contexts/AuthContext-simple.tsx`

Backend dead/duplicate:
- `SamLambda/functions/toDelete/` — entire directory
- `SamLambda/functions/questionDbFunctions/getProgressSummary/` vs `getProgressSummary2/`
- `SamLambda/functions/questionDbFunctions/incrementUserLevel/` vs `incrementUserLevel2/`

**Remediation Steps:**

1. Confirm which version is live (check `App.tsx` imports — it uses none of the variants).
2. Delete all variant files listed above.
3. Determine if `getProgressSummary` or `getProgressSummary2` is the active endpoint
   (check API Gateway logs or CloudWatch for recent invocations). Delete the unused one
   and remove its SAM template entry.
4. Same for `incrementUserLevel` vs `incrementUserLevel2`.
5. Delete `SamLambda/functions/toDelete/` entirely.
6. Remove the corresponding API endpoints from `template.yml` for any deleted functions.

**Verification:** After deletion, run `npm run build` to confirm no import errors, and
`sam build` to confirm no template errors.

---

### Area #9: No Route-Level Auth Guards

**Why it matters:** All routes in `App.tsx` are publicly accessible. Auth checks happen
inside each page component via `useEffect` redirects, causing a flash of unauthenticated
content. A benefactor can navigate to `/dashboard` and briefly see the maker dashboard.

**Evidence:**
- `FrontEndCode/src/App.tsx` — all `<Route>` elements have no wrapper
- `FrontEndCode/src/pages/Dashboard.tsx` — auth check is in `useEffect`, not a guard

**Remediation Steps:**

1. Create `FrontEndCode/src/components/ProtectedRoute.tsx`:
```tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedPersonas?: string[];
  redirectTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedPersonas,
  redirectTo = '/login'
}) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-legacy-purple" />
    </div>;
  }

  if (!user) return <Navigate to={redirectTo} replace />;

  if (allowedPersonas && !allowedPersonas.includes(user.personaType)) {
    const fallback = user.personaType === 'legacy_benefactor'
      ? '/benefactor-dashboard'
      : '/dashboard';
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
```

2. Update `App.tsx` to use the guard:
```tsx
<Route path="/dashboard" element={
  <ProtectedRoute allowedPersonas={['legacy_maker']}>
    <Dashboard />
  </ProtectedRoute>
} />
<Route path="/benefactor-dashboard" element={
  <ProtectedRoute allowedPersonas={['legacy_benefactor']}>
    <BenefactorDashboard />
  </ProtectedRoute>
} />
<Route path="/record-conversation" element={
  <ProtectedRoute allowedPersonas={['legacy_maker']}>
    <RecordConversation />
  </ProtectedRoute>
} />
```

3. Remove the redundant `useEffect` redirect logic from `Dashboard.tsx`,
   `BenefactorDashboard.tsx`, and `RecordConversation.tsx`.


---

### Area #10: React Query Installed but Unused

**Why it matters:** `@tanstack/react-query` is installed and `QueryClientProvider` wraps
the app, but all data fetching uses raw `useEffect` + `useState` + `fetch`. The custom
`useStatistics` hook manually reimplements stale-while-revalidate with localStorage.
This means no query deduplication, no automatic background refetching, no cache
invalidation on mutations, and no devtools visibility.

**Evidence:**
- `FrontEndCode/package.json` — `"@tanstack/react-query": "^5.56.2"`
- `FrontEndCode/src/App.tsx` — `QueryClientProvider` wraps the app but nothing uses it
- `FrontEndCode/src/hooks/useStatistics.ts` — 150 lines of manual caching logic
- `FrontEndCode/src/pages/Dashboard.tsx` — three separate `useEffect` hooks for data

**Remediation Steps:**

1. Create query key constants:
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

2. Replace `useStatistics` with a React Query hook:
```typescript
// src/hooks/useStatistics.ts (simplified replacement)
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';

export function useStatistics(userId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.statistics(userId ?? ''),
    queryFn: () => fetchStatistics(userId!),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,   // 5 minutes
    gcTime: 10 * 60 * 1000,     // keep in cache 10 minutes
  });
}
```

3. Replace Dashboard `useEffect` data fetching:
```typescript
// BEFORE
const [overallProgress, setOverallProgress] = useState(null);
useEffect(() => {
  const fetchProgress = async () => {
    const data = await getUserProgress(user.id);
    setOverallProgress(data);
  };
  fetchProgress();
}, [user?.id]);

// AFTER
const { data: overallProgress } = useQuery({
  queryKey: queryKeys.progress(user?.id ?? ''),
  queryFn: () => getUserProgress(user!.id),
  enabled: !!user?.id,
  staleTime: 5 * 60 * 1000,
});
```

4. Add cache invalidation after video upload:
```typescript
const queryClient = useQueryClient();
// After successful upload:
queryClient.invalidateQueries({ queryKey: queryKeys.progress(user.id) });
queryClient.invalidateQueries({ queryKey: queryKeys.statistics(user.id) });
```

5. Delete `useStatistics.ts` manual localStorage caching logic.

6. Configure the `QueryClient` with sensible defaults:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});
```

**Files to change:**
- `FrontEndCode/src/App.tsx` — update QueryClient config
- `FrontEndCode/src/hooks/useStatistics.ts` — rewrite
- `FrontEndCode/src/pages/Dashboard.tsx` — replace useEffect fetching
- `FrontEndCode/src/pages/BenefactorDashboard.tsx` — same
- Create `FrontEndCode/src/lib/queryKeys.ts`


---

### Area #11: SSM Parameters Loaded Individually on Every Cold Start

**Why it matters:** `get_conversation_config()` makes 8 individual `ssm.get_parameter()`
calls on a cold start. SSM has a default throughput of 40 TPS — under concurrent cold
starts this will throttle. Each call adds ~20-50ms of latency.

**Evidence:**
- `SamLambda/functions/conversationFunctions/wsDefault/config.py` — 8 separate
  `get_parameter()` calls in `get_conversation_config()`
- `wsDefault/app.py` line 527: `config = get_conversation_config()` called on every
  WebSocket message

**Remediation Steps:**

1. Replace individual calls with a single `get_parameters` batch call:
```python
def get_conversation_config() -> Dict:
    """Load all conversation config in a single SSM batch call"""
    param_names = [
        '/virtuallegacy/conversation/score-goal',
        '/virtuallegacy/conversation/max-turns',
        '/virtuallegacy/conversation/llm-conversation-model',
        '/virtuallegacy/conversation/llm-scoring-model',
        '/virtuallegacy/conversation/system-prompt',
        '/virtuallegacy/conversation/scoring-prompt',
        '/virtuallegacy/conversation/polly-voice-id',
        '/virtuallegacy/conversation/polly-engine',
    ]

    # Return from cache if populated
    if len(_param_cache) >= len(param_names):
        return _build_config_from_cache()

    response = ssm.get_parameters(Names=param_names)
    for param in response['Parameters']:
        _param_cache[param['Name']] = param['Value']

    return _build_config_from_cache()

def _build_config_from_cache() -> Dict:
    return {
        'score_goal': int(_param_cache.get('/virtuallegacy/conversation/score-goal', '12')),
        'max_turns': int(_param_cache.get('/virtuallegacy/conversation/max-turns', '20')),
        'llm_conversation_model': _param_cache.get('/virtuallegacy/conversation/llm-conversation-model'),
        'llm_scoring_model': _param_cache.get('/virtuallegacy/conversation/llm-scoring-model'),
        'system_prompt': _param_cache.get('/virtuallegacy/conversation/system-prompt'),
        'scoring_prompt': _param_cache.get('/virtuallegacy/conversation/scoring-prompt'),
        'polly_voice_id': _param_cache.get('/virtuallegacy/conversation/polly-voice-id', 'Joanna'),
        'polly_engine': _param_cache.get('/virtuallegacy/conversation/polly-engine', 'neural'),
    }
```

2. `get_parameters` supports up to 10 names per call — all 8 fit in one request.
3. The existing `_param_cache` dict already handles container-reuse caching correctly.

---

### Area #12: Error Messages Leak Internal Details

**Why it matters:** Raw `str(e)` in HTTP responses can expose DynamoDB table names,
internal paths, stack traces, and AWS resource identifiers to the client. This is an
OWASP A05 (Security Misconfiguration) issue.

**Evidence:**
- `getRelationships/app.py` line 53: `'error': str(e)`
- `wsDefault/app.py` line 556: `'message': f'Server error: {str(e)}'`
- Similar pattern across most Lambda handlers

**Remediation Steps:**

1. Add a safe error response helper to `shared/cors.py` (or a new `shared/responses.py`):
```python
import logging, traceback

logger = logging.getLogger()

def error_response(e: Exception, status_code: int = 500,
                   public_message: str = 'An internal error occurred') -> dict:
    """Log full error internally, return safe message to client"""
    logger.error(f"Internal error: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps({'error': public_message})
    }
```

2. Replace all `'error': str(e)` patterns:
```python
# BEFORE
except Exception as e:
    return {'statusCode': 500, 'headers': {...}, 'body': json.dumps({'error': str(e)})}

# AFTER
except Exception as e:
    return error_response(e)
```

3. For validation errors (400s), it's fine to return descriptive messages since those
   are user-facing. Only suppress internal exception details on 500s.

---

### Area #13: Hardcoded S3 Bucket Names and AWS Resources

**Why it matters:** `S3_BUCKET = 'virtual-legacy'` and DynamoDB table names like
`'PersonaRelationshipsDB'` are hardcoded strings. This makes multi-environment
deployment impossible and creates a maintenance burden when resources are renamed.

**Evidence:**
- `wsDefault/speech.py` line 15: `S3_BUCKET = 'virtual-legacy'`
- `wsDefault/storage.py`: hardcoded table names
- `getRelationships/app.py` line 63: `dynamodb.Table('PersonaRelationshipsDB')`
- Multiple Lambda handlers with hardcoded table names

**Remediation Steps:**

1. Add environment variables to all Lambda functions in `template.yml`:
```yaml
Environment:
  Variables:
    S3_BUCKET: virtual-legacy
    PERSONA_RELATIONSHIPS_TABLE: !Ref PersonaRelationshipsTable
    ACCESS_CONDITIONS_TABLE: !Ref AccessConditionsTable
    ENGAGEMENT_TABLE: !Ref EngagementTable
```

2. Replace hardcoded strings in Lambda code:
```python
# BEFORE
S3_BUCKET = 'virtual-legacy'
table = dynamodb.Table('PersonaRelationshipsDB')

# AFTER
S3_BUCKET = os.environ['S3_BUCKET']
table = dynamodb.Table(os.environ['PERSONA_RELATIONSHIPS_TABLE'])
```

3. For tables managed outside CloudFormation (`userQuestionStatusDB`, `userStatusDB`,
   `allQuestionDB`), add them as SSM parameters or CloudFormation parameters and
   reference via environment variables.


---

### Area #14: No DynamoDB Pagination

**Why it matters:** DynamoDB returns a maximum of 1MB per query. If a user accumulates
enough relationships, assignments, or question statuses, results will be silently
truncated with no error. The caller has no way to know data is missing.

**Evidence:**
- `getRelationships/app.py` — `table.query()` with no `LastEvaluatedKey` handling
- `getAssignments/app.py` — same pattern
- Question status queries in multiple functions

**Remediation Steps:**

1. Add a pagination helper to `shared/`:
```python
def query_all_pages(table, **kwargs) -> list:
    """Query DynamoDB handling pagination automatically"""
    items = []
    while True:
        response = table.query(**kwargs)
        items.extend(response.get('Items', []))
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
        kwargs['ExclusiveStartKey'] = last_key
    return items
```

2. Replace all direct `table.query()` calls with `query_all_pages()`.

3. For large datasets, consider adding a `limit` parameter and returning a
   `nextToken` (base64-encoded `LastEvaluatedKey`) for cursor-based pagination on
   the API level.

---

### Area #15: Wildcard IAM Resource ARNs

**Why it matters:** `arn:aws:dynamodb:*:*:table/userQuestionStatusDB` grants access to
any DynamoDB table with that name in any region and any AWS account. This violates
least-privilege and could allow cross-account access if the account boundary is ever
breached.

**Evidence:**
- `SamLambda/template.yml` — `GetUnansweredQuestionsFromUserFunction`,
  `ProcessVideoFunction`, `UploadVideoResponseFunction`, and others use
  `arn:aws:dynamodb:*:*:table/...`

**Remediation Steps:**

Replace all wildcard ARNs with scoped versions:
```yaml
# BEFORE
Resource: arn:aws:dynamodb:*:*:table/userQuestionStatusDB

# AFTER
Resource: !Sub arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/userQuestionStatusDB
```

This is a find-and-replace across `template.yml`. Also scope the KMS key ARN in
`GetUploadUrlFunction` which uses a hardcoded key ID instead of `!GetAtt DataEncryptionKey.Arn`.

---

### Area #16: Silent Fire-and-Forget API Call in Login

**Why it matters:** The `login` function fires a `fetch` to `initialize-progress` with
`.catch(() => {})`. If this fails, the user's progress state may be inconsistent and
nobody will know. Silent failures are the hardest bugs to diagnose.

**Evidence:**
- `FrontEndCode/src/contexts/AuthContext.tsx` lines ~95-105:
```typescript
fetch(buildApiUrl('/functions/questionDbFunctions/initialize-progress'), {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` }
}).catch(() => {}); // Silent fail
```

**Remediation Steps:**

1. Replace with a React Query mutation that logs failures:
```typescript
// In a useInitializeProgress hook or directly in AuthContext
const initializeProgress = async (token: string) => {
  try {
    const response = await fetch(
      buildApiUrl('/functions/questionDbFunctions/initialize-progress'),
      { method: 'POST', headers: { Authorization: `Bearer ${token}` } }
    );
    if (!response.ok) {
      console.warn('Progress initialization returned non-OK status:', response.status);
    }
  } catch (error) {
    console.warn('Progress initialization failed (non-blocking):', error);
    // Still non-blocking — user can proceed — but now we know about it
  }
};
```

2. Consider moving progress initialization to the `postConfirmation` Cognito trigger
   (runs once at account creation) rather than on every login.

---

### Area #17: Manual Deployment Process — No CI/CD

**Why it matters:** The current workflow is `npm run build → create dist.zip → upload
to Amplify Console` manually. No automated testing before deploy, no staging
environment, no rollback mechanism. One bad deploy goes straight to production.

**Evidence:**
- `DEPLOYMENT_INFO.txt`: "UPDATE WORKFLOW: Frontend: npm run build → create dist.zip →
  upload to Amplify Console"
- No `.github/workflows/` directory exists

**Remediation Steps:**

1. Create `.github/workflows/deploy-backend.yml`:
```yaml
name: Deploy Backend
on:
  push:
    branches: [main]
    paths: ['SamLambda/**']

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsDeployRole
          aws-region: us-east-1
      - uses: aws-actions/setup-sam@v2
      - run: pip install -r SamLambda/test_requirements.txt
      - run: pytest SamLambda/tests/ -v
        working-directory: SamLambda
      - run: sam build
        working-directory: SamLambda
      - run: sam deploy --no-confirm-changeset
        working-directory: SamLambda
```

2. Create `.github/workflows/deploy-frontend.yml`:
```yaml
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths: ['FrontEndCode/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: FrontEndCode
      - run: npm run test
        working-directory: FrontEndCode
      - run: npm run build
        working-directory: FrontEndCode
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsDeployRole
          aws-region: us-east-1
      - run: |
          aws amplify start-deployment \
            --app-id ${{ secrets.AMPLIFY_APP_ID }} \
            --branch-name main \
            --source-url s3://deploy-bucket/dist.zip
```

3. Create an IAM role `GitHubActionsDeployRole` with OIDC trust for
   `token.actions.githubusercontent.com` — no long-lived credentials needed.

4. Add a staging Amplify branch (`staging`) that deploys from a `develop` branch,
   with a separate API Gateway stage and Cognito pool.


---

## Quick Wins Summary

These are the fastest, highest-impact items — most can be done in under an hour each.

| # | Action | File(s) | Time | Impact |
|---|---|---|---|---|
| 1 | Fix `handle_user_response` to use `process_user_response_parallel` | `wsDefault/app.py` | 5 min | ~50% latency reduction on text path |
| 2 | Replace CORS `'*'` with actual domain in SAM Globals | `template.yml` | 5 min | Closes CSRF vector |
| 3 | Delete 12 dead variant files (App-*.tsx, Home-*.tsx, etc.) | `FrontEndCode/src/` | 10 min | Cleaner codebase, faster onboarding |
| 4 | Batch SSM parameters with `get_parameters(Names=[...])` | `wsDefault/config.py` | 15 min | Reduces cold start by ~7 API calls |
| 5 | Delete SSH key files and add to `.gitignore` | repo root | 5 min | Removes credential exposure |
| 6 | Replace wildcard IAM ARNs with `!Sub` scoped versions | `template.yml` | 20 min | Least-privilege compliance |
| 7 | Add `ProtectedRoute` wrapper component | `App.tsx`, new component | 30 min | Eliminates auth flash, cleaner routing |
| 8 | Fix error responses to not leak `str(e)` | all Lambda `app.py` files | 30 min | Stops internal detail exposure |
| 9 | Move hardcoded S3/DynamoDB names to environment variables | `template.yml` + Lambda files | 45 min | Enables multi-environment deploy |
| 10 | Delete `SamLambda/functions/toDelete/` entirely | `toDelete/` directory | 2 min | Pure deletion |
| 11 | Add `Cache-Control` headers to static question endpoints | question Lambda handlers | 20 min | Reduces repeat API calls |
| 12 | Fix silent `fetch().catch(() => {})` in login | `AuthContext.tsx` | 10 min | Surfaces hidden failures |

---

## Open Questions

These business and architectural questions could shift priorities significantly.

1. **Concurrent user target** — What's the expected number of simultaneous active
   conversations? This determines whether DynamoDB for conversation state is sufficient
   or if ElastiCache/Redis is needed.

2. **Benefactor count per maker** — How many benefactors can a single legacy maker
   have? This determines the severity of the N+1 Cognito query problem and whether
   denormalization is urgent.

3. **Third persona type** — Is there a plan for a third persona (e.g., an executor,
   a family admin)? The current binary if/else persona checks would need refactoring
   to a role-based system before adding a third type.

4. **Average conversation length** — How many turns does a typical conversation run?
   This affects the DynamoDB item size limit for conversation state storage (400KB max).

5. **Compliance requirements** — Are there HIPAA, SOC2, or GDPR obligations given the
   personal/legacy nature of the content? The CloudTrail + GuardDuty setup suggests
   awareness, but data residency, right-to-deletion, and data retention policies aren't
   addressed in the codebase.

6. **Team size** — A solo developer can manage the current copy-paste Lambda pattern
   with discipline. A team of 3+ will immediately hit merge conflicts and divergent
   bugs in the duplicated shared utilities.

7. **`getProgressSummary2` / `incrementUserLevel2` intent** — Are these intentional
   A/B tests or accidental duplication? This determines whether to merge or keep both.
   Check CloudWatch invocation metrics to see which is actually being called.

8. **Custom domain** — Is `main.d33jt7rnrasyvj.amplifyapp.com` the permanent URL or
   is a custom domain planned? The CORS fix should target the final domain, not the
   Amplify-generated URL.

---

*Audit performed March 14, 2026. Evidence cited from live source files in the workspace.*
