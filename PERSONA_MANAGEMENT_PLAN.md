# Persona Management — Comprehensive Phased Plan
## SoulReel / Virtual Legacy
**Created:** March 16, 2026
**Based on:** Deep analysis of full-stack persona lifecycle, conversation AI, and access control

---

## Context & Key Findings

### What "Persona" Means in This System

"Persona" refers to **user role types** — `legacy_maker` (records life stories) and
`legacy_benefactor` (views content). The AI interviewer has a single personality defined
by one SSM system prompt. There is no multi-personality switching or AI character management.

### Critical Discovery: PersonaValidator Is Broken and Unused

`PersonaValidator.get_user_persona_from_jwt()` reads `claims.get('custom:persona_type')`,
but production stores persona in the `profile` attribute as JSON — not as `custom:persona_type`.
The validator always returns empty string for `persona_type`.

Both production Lambda functions that imported it have the import **commented out**:
- `getUnansweredQuestionsFromUser/app.py`: `# from shared.persona_validator import PersonaValidator`
- `getUnansweredQuestionsWithText/app.py`: `# from shared.persona_validator import PersonaValidator`

The one function that validates persona correctly (`initializeUserProgress/app.py`) does it
inline by parsing `claims.get('profile', '{}')` as JSON. The test suite passes only because
mocks inject `custom:persona_type` — data that doesn't exist in production JWTs.

**Impact:** Server-side persona enforcement is effectively absent on most endpoints. The system
works because the frontend routes users correctly, but there is no backend safety net.

### Signup Pipeline Fragility

Four-stage pipeline with three fragility points:

| Stage | Component | Fragility |
|---|---|---|
| 1 | Frontend `signupWithPersona` | `clientMetadata` not server-validated |
| 2 | PreSignup Lambda → DynamoDB temp | Write failure silently swallowed — invited benefactor gets wrong role |
| 3 | PostConfirmation → Cognito profile | Async execution, no alerting on retry exhaustion |
| 4 | Frontend `checkAuthState` | Client-side override masks server-side failures |

### AI Conversation Coherence

The conversation system is solid for single-personality consistency:
- System prompt cached per Lambda container, full history sent to Bedrock each turn
- Parallel scoring on separate model (Haiku) prevents cross-contamination
- State persisted to DynamoDB per connection, survives container recycling

Gaps: no WebSocket reconnection, no conversation state size guard, no TTS caching.

---

## Phase 1: Critical Fixes (Immediate — <1 hour each)

### 1.1 Fix PersonaValidator to Match Production JWT Structure

**Priority:** P0 — Foundation for all server-side access control
**Files:** `SamLambda/functions/shared/persona_validator.py`, `SamLambda/functions/shared/python/persona_validator.py`
**Risk:** Low — validator is currently unused in production

The validator reads `custom:persona_type` from JWT claims, but production stores persona
in the `profile` claim as JSON. Fix `get_user_persona_from_jwt()`:

**Before:**
```python
return {
    'user_id': claims.get('sub'),
    'email': claims.get('email'),
    'persona_type': claims.get('custom:persona_type', ''),
    'initiator_id': claims.get('custom:initiator_id', ''),
    'related_user_id': claims.get('custom:related_user_id', '')
}
```

**After:**
```python
profile_raw = claims.get('profile', '{}')
try:
    profile = json.loads(profile_raw)
except (json.JSONDecodeError, TypeError):
    profile = {}

return {
    'user_id': claims.get('sub'),
    'email': claims.get('email'),
    'persona_type': profile.get('persona_type', ''),
    'initiator_id': profile.get('initiator_id', ''),
    'related_user_id': profile.get('related_user_id', '')
}
```

Also fix the duplicate copy in `getUnansweredQuestionsFromUser/persona_validator.py`.

**Verification:** Run existing persona validation tests — they will fail (expected).
That leads directly to 1.2.

### 1.2 Fix All Persona Test Mocks

**Priority:** P0 — Tests validate against fake data that doesn't match production
**Files:** All `test_persona_validation.py` files, `comprehensive_persona_test_suite.py`,
`api_endpoint_test_suite.py`, `test_persona_flow.py`, `test_persona_validator.py`

Every test mock uses `custom:persona_type` in claims. Update to use `profile` JSON:

**Before:**
```python
'claims': {
    'sub': 'test-user-123',
    'custom:persona_type': 'legacy_maker',
    'custom:initiator_id': 'test-user-123'
}
```

**After:**
```python
'claims': {
    'sub': 'test-user-123',
    'profile': json.dumps({
        'persona_type': 'legacy_maker',
        'initiator_id': 'test-user-123',
        'related_user_id': ''
    })
}
```

**Must be done atomically with 1.1** — changing mocks without changing the validator
(or vice versa) breaks all tests.

### 1.3 Add CloudWatch Metric for Persona Write Failures

**Priority:** P0 — One failure = one user with wrong role, currently invisible
**File:** `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`
**IAM:** Add `cloudwatch:PutMetricData` to PostConfirmationFunction policy in `template.yml`

After all Cognito write retries are exhausted, emit a metric:

```python
import boto3
cloudwatch = boto3.client('cloudwatch')

# After retry loop fails:
try:
    cloudwatch.put_metric_data(
        Namespace='SoulReel/Persona',
        MetricData=[{
            'MetricName': 'PersonaWriteFailure',
            'Value': 1,
            'Unit': 'Count'
        }]
    )
except Exception:
    pass  # Don't fail signup over metric emission
```

Create a CloudWatch alarm: `PersonaWriteFailure > 0` for 1 datapoint in 5 minutes → SNS notification.

### 1.4 Add Feature Flag for Persona Validation Rollout

**Priority:** P1 — Enables gradual rollout of server-side validation
**File:** `SamLambda/template.yml` (Globals section)

Add to Globals environment variables:

```yaml
Globals:
  Function:
    Environment:
      Variables:
        ENFORCE_PERSONA_VALIDATION: 'false'
        # ... existing vars
```

Lambda functions check this before enforcing:

```python
ENFORCE_PERSONA = os.environ.get('ENFORCE_PERSONA_VALIDATION', 'false') == 'true'
```

Flip to `'true'` after verifying no users have broken `profile` attributes.

---

## Phase 2: Server-Side Access Control (1–2 weeks)

### 2.1 Enable Persona Validation on Question Endpoints

**Priority:** P1 — These are the primary maker-only endpoints
**Files:**
- `SamLambda/functions/questionDbFunctions/getUnansweredQuestionsFromUser/app.py`
- `SamLambda/functions/questionDbFunctions/getUnansweredQuestionsWithText/app.py`

Uncomment the `PersonaValidator` import (now fixed from Phase 1). Add validation
after extracting user ID:

```python
from persona_validator import PersonaValidator

# In lambda_handler, after auth check:
if os.environ.get('ENFORCE_PERSONA_VALIDATION', 'false') == 'true':
    persona_info = PersonaValidator.get_user_persona_from_jwt(event)
    is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
    if not is_valid:
        return PersonaValidator.create_access_denied_response(message)
```

Use the `initializeUserProgress/app.py` implementation as the reference pattern —
it already validates correctly by parsing `profile` JSON from claims.

### 2.2 Add Persona Validation to Assignment Endpoints

**Priority:** P1 — Assignment operations are role-sensitive
**Files:** All 7 functions in `SamLambda/functions/assignmentFunctions/`

These functions currently use `extract_user_id_from_jwt()` (manual base64 JWT decoding,
duplicated 7 times — see tech debt Area #5). Replace with authorizer claims + persona check:

```python
# Replace:
legacy_maker_id = extract_user_id_from_jwt(event)

# With:
claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
legacy_maker_id = claims.get('sub')

# Add persona validation for maker-only operations:
if os.environ.get('ENFORCE_PERSONA_VALIDATION', 'false') == 'true':
    persona_info = PersonaValidator.get_user_persona_from_jwt(event)
    is_valid, message = PersonaValidator.validate_legacy_maker_access(persona_info)
    if not is_valid:
        return PersonaValidator.create_access_denied_response(message)
```

Delete the `extract_user_id_from_jwt` function from each file after migration.

### 2.3 Harden PreSignup Persona Data Write

**Priority:** P1 — Silent failure here causes wrong role assignment
**File:** `SamLambda/functions/cognitoTriggers/preSignup/app.py`

For invited benefactors, the DynamoDB temp write is critical. Make it conditional:

```python
except Exception as e:
    print(f"Error storing persona data: {str(e)}")
    if invite_token:
        # Invited benefactors MUST have persona data — PostConfirmation
        # needs it to set the correct role. Fail signup so user can retry.
        raise
    # For non-invited signups, PostConfirmation defaults to legacy_maker
    # which is correct for the create_legacy flow.
```

**Alternative (lower risk):** Keep the write non-fatal but encode persona data in the
Cognito event response as a fallback source for PostConfirmation:

```python
except Exception as e:
    print(f"Error storing persona data: {str(e)}")
    # Fallback: encode in event so PostConfirmation can read it
    event['response']['claimsOverrideDetails'] = {
        'claimsToAddOrOverride': {
            'persona_type_pending': persona_type
        }
    }
```

Then update PostConfirmation to check DynamoDB first, fall back to event metadata.

### 2.4 Conversation State Size Guard

**Priority:** P2 — Prevents DynamoDB 400KB item limit crash during long conversations
**File:** `SamLambda/functions/conversationFunctions/wsDefault/conversation_state.py`

Add size check in `set_conversation()`:

```python
def set_conversation(connection_id: str, state: ConversationState):
    try:
        table = _get_table()
        item = _floats_to_decimals(state.to_dict())
        item['ttl'] = int(time.time()) + _STATE_TTL_SECONDS

        # Guard against DynamoDB 400KB item limit
        item_json = json.dumps(item, default=str)
        if len(item_json) > 300_000:  # 300KB safety margin
            print(f"[STATE] Item size {len(item_json)} bytes — trimming older turns")
            turns = item.get('turns', [])
            for turn in turns[:-3]:  # Keep last 3 turns full
                turn.pop('reasoning', None)
                turn.pop('ai_response', None)

        table.put_item(Item=item)
    except Exception as e:
        print(f"[STATE] Error saving conversation {connection_id}: {e}")
        raise
```

### 2.5 TTS Caching

**Priority:** P2 — Reduces latency and Polly costs
**File:** `SamLambda/functions/conversationFunctions/wsDefault/speech.py`
**IAM:** Add `s3:HeadObject` permission and `arn:aws:s3:::virtual-legacy/tts-cache/*` resource

```python
import hashlib

def _cache_key(text: str, voice_id: str, engine: str) -> str:
    content_hash = hashlib.sha256(f"{text}|{voice_id}|{engine}".encode()).hexdigest()[:16]
    return f"tts-cache/{content_hash}.mp3"

def text_to_speech(text, user_id, question_id, turn_number, voice_id, engine):
    cache_key = _cache_key(text, voice_id, engine)

    # Check cache (only for short responses where hit rate is highest)
    if len(text) < 200:
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
            print(f"[POLLY] Cache hit: {cache_key}")
            return s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': S3_BUCKET, 'Key': cache_key}, ExpiresIn=3600
            )
        except s3_client.exceptions.ClientError:
            pass  # Cache miss — synthesize normally

    # ... existing Polly synthesis code ...

    # Write to cache after synthesis (short responses only)
    if len(text) < 200:
        try:
            s3_client.copy_object(
                Bucket=S3_BUCKET, Key=cache_key,
                CopySource={'Bucket': S3_BUCKET, 'Key': s3_key}
            )
        except Exception:
            pass  # Cache write failure is non-fatal
```

Update `template.yml` WebSocketDefaultFunction policy:
```yaml
Resource:
  - arn:aws:s3:::virtual-legacy/conversations/*
  - arn:aws:s3:::virtual-legacy/test-audio/*
  - arn:aws:s3:::virtual-legacy/tts-cache/*
```

---

## Phase 3: Conversation Resilience (2–4 weeks)

### 3.1 WebSocket Conversation Reconnection

**Priority:** P2 — Users lose conversation progress on disconnect
**Files:** `conversation_state.py`, `app.py` (wsDefault), `template.yml`, `ConversationInterface.tsx`

**Backend — Add GSI for user-based state lookup:**

Add to `ConversationStateTable` in `template.yml`:
```yaml
ConversationStateTable:
  Properties:
    AttributeDefinitions:
      - AttributeName: connectionId
        AttributeType: S
      - AttributeName: userId
        AttributeType: S
    GlobalSecondaryIndexes:
      - IndexName: UserIdIndex
        KeySchema:
          - AttributeName: userId
            KeyType: HASH
        Projection:
          ProjectionType: ALL
```

Add `dynamodb:Query` on the GSI to WebSocketDefaultFunction IAM policy.

**Backend — Add resume handler in `app.py`:**
```python
def handle_resume_conversation(connection_id: str, user_id: str, body: dict, config: dict):
    question_id = body.get('questionId')
    # Query GSI for existing state
    table = boto3.resource('dynamodb').Table(
        os.environ.get('CONVERSATION_STATE_TABLE', 'ConversationStateDB')
    )
    response = table.query(
        IndexName='UserIdIndex',
        KeyConditionExpression='userId = :uid',
        FilterExpression='questionId = :qid AND completed = :false',
        ExpressionAttributeValues={
            ':uid': user_id, ':qid': question_id, ':false': False
        }
    )
    if response['Items']:
        old_item = response['Items'][0]
        # Delete old connection's state
        table.delete_item(Key={'connectionId': old_item['connectionId']})
        # Restore under new connection
        state = ConversationState.from_dict(old_item)
        state.connection_id = connection_id
        set_conversation(connection_id, state)
        send_message(connection_id, {
            'type': 'conversation_resumed',
            'turnNumber': state.turn_number,
            'cumulativeScore': state.cumulative_score,
            'scoreGoal': config['score_goal']
        })
    else:
        send_message(connection_id, {
            'type': 'no_conversation_found'
        })
```

**Frontend — Add reconnection logic in `ConversationInterface.tsx`:**

On WebSocket `onopen`, send `resume_conversation` before `start_conversation`.
If server responds with `conversation_resumed`, restore UI state.
If `no_conversation_found`, proceed with `start_conversation` as normal.

### 3.2 Conversation Context Truncation for Long Sessions

**Priority:** P3 — Prevents context window degradation and reduces Bedrock costs
**File:** `SamLambda/functions/conversationFunctions/wsDefault/llm.py`

After turn 10, summarize earlier turns instead of sending full history:

```python
def _build_messages(conversation_history, max_full_turns=5):
    if len(conversation_history) <= max_full_turns:
        return _all_turns_as_messages(conversation_history)

    # Summarize older turns
    older = conversation_history[:-max_full_turns]
    summary = "Previous conversation covered: " + "; ".join(
        turn['user_text'][:100] for turn in older
    )
    recent = conversation_history[-max_full_turns:]

    messages = [{"role": "user", "content": f"[Context from earlier in conversation: {summary}]"},
                {"role": "assistant", "content": "I understand. Let's continue."}]
    for turn in recent:
        messages.append({"role": "user", "content": turn['user_text']})
        messages.append({"role": "assistant", "content": turn['ai_response']})
    return messages
```

### 3.3 Consolidate Shared Layer Duplicates

**Priority:** P3 — Reduces maintenance burden, prevents drift
**Scope:** `functions/shared/` vs `functions/shared/python/`

Both directories contain identical copies of `persona_validator.py`, `assignment_dal.py`,
`invitation_utils.py`, `email_templates.py`, etc. The `shared/python/` directory is the
SharedUtilsLayer source. The `shared/` directory is used by functions that import directly.

**Plan:**
1. Make `shared/python/` the single source of truth
2. Delete duplicates from `shared/` (keep only test files)
3. Ensure all functions use the SharedUtilsLayer import path
4. Update `phase4.py` automation to only patch `shared/python/`

---

## Phase 4: Long-Term Vision

### 4.1 Per-Question-Type System Prompts

**Priority:** P4 — Enhances emotional quality of conversations
**Scope:** SSM parameters, `config.py`

Currently all questions use the same system prompt with a `{question}` placeholder.
Different question types deserve different interviewing styles:

- "Childhood memories" → warm, nostalgic, sensory-detail probing
- "Life values" → reflective, philosophical, connecting-to-examples
- "Relationships" → empathetic, careful with sensitive topics

Store per-type prompts in SSM: `/virtuallegacy/conversation/system-prompt/{questionType}`.
Fall back to the default prompt if type-specific prompt doesn't exist.

### 4.2 Conversation Quality Monitoring

**Priority:** P4 — Enables data-driven improvements
**Scope:** CloudWatch metrics from `app.py` and `llm.py`

Emit metrics on every conversation:
- `SoulReel/Conversation/TurnCount` — distribution of conversation lengths
- `SoulReel/Conversation/CompletionReason` — `score_goal_reached` vs `max_turns_reached` vs `user_ended`
- `SoulReel/Conversation/AvgTurnScore` — quality signal per conversation
- `SoulReel/Conversation/TranscriptionTier` — which fallback tier was used (Deepgram/Streaming/Batch)
- `SoulReel/Conversation/E2ELatency` — total time from user audio upload to AI audio response

Create a CloudWatch dashboard for conversation health.

### 4.3 Persona Migration Tool

**Priority:** P4 — Admin recovery for users with wrong/missing persona
**Scope:** New Lambda function + admin API endpoint

Build an admin-only endpoint that:
1. Looks up a user by email in Cognito
2. Reads their current `profile` attribute
3. Allows updating `persona_type` with audit logging
4. Optionally creates/fixes relationship records in `PersonaRelationshipsDB`

Gate behind a separate Cognito group (`admin`) with its own authorizer.

---

## Testing Strategy

### Synthetic Test Scenarios

| Scenario | What It Tests | How to Create |
|---|---|---|
| Missing `profile` attribute | Validator graceful degradation | Create Cognito user without profile, call protected endpoint |
| Malformed `profile` JSON | JSON parse error handling | Set profile to `"not json"` via admin API |
| Empty `persona_type` | Default behavior | Set profile to `{"persona_type": ""}` |
| PreSignup DynamoDB failure | Fallback path | Temporarily revoke DynamoDB write permission on PreSignup role |
| PostConfirmation timeout | Race condition | Add artificial delay in PostConfirmation, observe frontend behavior |
| 20-turn conversation | State size limits | Script a WebSocket client that sends 20 long responses |
| WebSocket disconnect at turn 10 | Reconnection (after Phase 3) | Kill WebSocket mid-conversation, reconnect |
| Concurrent tabs same question | Data integrity | Open two tabs, start same question, complete both |

### Automated Test Updates

All files requiring mock updates for Phase 1.2:

- `SamLambda/functions/questionDbFunctions/getUnansweredQuestionsFromUser/test_persona_validation.py`
- `SamLambda/functions/questionDbFunctions/getUnansweredQuestionsWithText/test_persona_validation.py`
- `SamLambda/functions/videoFunctions/uploadVideoResponse/test_persona_validation.py`
- `SamLambda/functions/shared/test_persona_validator.py`
- `SamLambda/functions/tests/comprehensive_persona_test_suite.py`
- `SamLambda/functions/tests/api_endpoint_test_suite.py`
- `SamLambda/functions/tests/test_persona_flow.py`

---

## Monitoring Metrics to Add Post-Deploy

| Metric | Namespace | Alarm Threshold | Phase |
|---|---|---|---|
| `PersonaWriteFailure` | `SoulReel/Persona` | > 0 in 5 min | 1 |
| `PersonaValidationDenied` | `SoulReel/Persona` | > 10 in 5 min (anomaly) | 2 |
| `ConversationStateWriteFailure` | `SoulReel/Conversation` | > 0 in 5 min | 2 |
| `TurnCount` | `SoulReel/Conversation` | Informational | 4 |
| `CompletionRate` | `SoulReel/Conversation` | Informational | 4 |
| `TranscriptionTier` | `SoulReel/Conversation` | Tier3 > 50% (Deepgram down) | 4 |
| `E2ELatency` | `SoulReel/Conversation` | p99 > 30s | 4 |

---

## IAM Changes Required

| Phase | Function | Action to Add | Resource |
|---|---|---|---|
| 1.3 | PostConfirmationFunction | `cloudwatch:PutMetricData` | `*` |
| 2.5 | WebSocketDefaultFunction | `s3:HeadObject` | `arn:aws:s3:::virtual-legacy/tts-cache/*` |
| 2.5 | WebSocketDefaultFunction | (existing `s3:PutObject`, `s3:GetObject`) | Add `arn:aws:s3:::virtual-legacy/tts-cache/*` |
| 3.1 | WebSocketDefaultFunction | `dynamodb:Query` | `ConversationStateTable/index/UserIdIndex` |

Per the project's lambda-iam-permissions steering rule: code changes and IAM policy
changes must be in the same deploy.

---

## Summary

The highest-impact work is in Phase 1: fixing the broken `PersonaValidator`, updating
test mocks to match production JWT structure, and adding alerting for persona write
failures. This is the foundation — without it, server-side access control doesn't exist
and the system relies entirely on frontend routing to enforce role separation.

Phase 2 enables that access control gradually with a feature flag, hardens the signup
pipeline, and adds conversation quality improvements (state size guard, TTS caching).

Phase 3 addresses conversation resilience — reconnection and context management for
long sessions.

Phase 4 is aspirational — per-question AI personality, monitoring dashboards, admin tools.
