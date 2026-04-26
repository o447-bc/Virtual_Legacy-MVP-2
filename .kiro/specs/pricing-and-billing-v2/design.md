# Design Document

## Overview

This design implements SoulReel's updated pricing model: a 2-tier system (Free + Premium at $14.99/month or $149/year) with content-level gating instead of usage caps. Free users complete Level 1 at full AI quality with no weekly limits. The gate is content progression, not degraded experience.

The existing billing infrastructure (billing Lambda, webhook Lambda, plan_check.py, SubscriptionContext, billingService.ts, PricingPage.tsx) is updated rather than rebuilt. Key changes: remove the 7-day trial (Level 1 IS the trial), update pricing from $9.99/$89.99 to $14.99/$149, reduce free benefactors from 2 to 1, remove weekly conversation caps, add Level 1 completion tracking, add celebration screen and upgrade banners, deploy cost optimizations, and wire up founding member and win-back coupon infrastructure.

## Architecture Changes

### Backend Changes

1. **PostConfirmation Lambda** — Change from creating a 14-day premium trial to creating a free-plan record with `planId: free`, `status: active`. Remove trial logic entirely.

2. **plan_check.py** — Update `_get_plan_definition()` to use new plan structure with `maxLevel` field. Update `check_question_category_access()` to enforce level-based gating (not just category). Remove `conversationsPerWeek` enforcement. Remove `is_trial_active()` checks from premium determination (no more trials for new users — only coupon-based trialing remains).

3. **wsDefault/app.py** — Add Level 1 completion tracking after conversation end. Remove `_increment_weekly_conversation_count()` call (no weekly caps). Add annual-plan nudge at 50 conversations/month for monthly subscribers.

4. **wsDefault/speech.py** — Add Polly caching for turn 0 (question greetings) using deterministic S3 keys.

5. **billing/app.py** — Update plan definitions to new structure. Add `/billing/plans` public endpoint. Update pricing display fields. Add founding member coupon availability to plans response.

6. **stripeWebhook/app.py** — Update price-to-plan mapping for new Stripe prices ($14.99 monthly, $149 annual). Store `billingInterval` on checkout completion.

7. **winBack/app.py** — Add weekly re-engagement email for Level 1 completers who didn't convert. Add `lastReengagementEmailAt` tracking.

8. **template.yml** — Update IAM policies for Nova Micro model access. Add `dynamodb:UpdateItem` for WebSocketDefaultFunction on UserSubscriptionsDB. Update SSM parameter paths.

### Frontend Changes

1. **SubscriptionContext.tsx** — Remove trial-related state (`trialExpiresAt`, `trialDaysRemaining`). Add `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted`. Update `computeIsPremium()` to remove trial logic (only `active` and `comped` are premium; `trialing` only for coupon-based trials).

2. **billingService.ts** — Update `SubscriptionStatus` interface with new fields. Update `PlanLimits` to include `maxLevel`, `foundingMemberPrice`, `foundingMemberCouponCode`. Add `getPublicPlans()` founding member availability.

3. **PricingPage.tsx** — Update pricing display to $14.99/$149. Default toggle to annual with "Save 17%" badge. Add founding member pricing display when available. Add "Less than a cup of coffee a week" anchoring text.

4. **Dashboard.tsx** — Add Level 1 completion celebration screen. Add upgrade banners at 50% and 100% Level 1 completion. Add locked level progression display. Add "X personalized questions waiting" teaser. Add benefactor-aware upgrade prompts.

5. **Home.tsx** — Update pricing section with new prices. Change CTA to "Start Free".

### SSM Parameter Changes

```
# Updated plan definitions
/soulreel/plans/free → {
  "planId": "free",
  "maxLevel": 1,
  "allowedCategories": ["life_story_reflections"],
  "maxBenefactors": 1,
  "accessConditionTypes": ["immediate"],
  "features": ["basic"]
}

/soulreel/plans/premium → {
  "planId": "premium",
  "maxLevel": 10,
  "allowedCategories": ["life_story_reflections", "life_events", "values_and_emotions"],
  "maxBenefactors": -1,
  "accessConditionTypes": ["immediate", "time_delayed", "inactivity_trigger", "manual_release", "dead_mans_switch"],
  "features": ["basic", "dead_mans_switch", "pdf_export", "legacy_export", "data_export"],
  "monthlyPrice": 14.99,
  "annualPrice": 149,
  "annualMonthlyEquivalent": 12.42,
  "annualSavingsPercent": 17,
  "foundingMemberPrice": 99,
  "foundingMemberCouponCode": "FOUNDING100"
}

# Cost optimization model switches
/virtuallegacy/conversation/llm-scoring-model → "amazon.nova-micro-v1:0"
/virtuallegacy/conversation/llm-conversation-model → "us.anthropic.claude-3-5-haiku-20241022-v1:0"

# Founding member coupon
/soulreel/coupons/FOUNDING100 → {
  "code": "FOUNDING100",
  "type": "percentage",
  "percentOff": 33,
  "stripeCouponId": "FOUNDING100",
  "maxRedemptions": 100,
  "currentRedemptions": 0,
  "expiresAt": null,
  "createdBy": "system"
}

# Win-back coupon
/soulreel/coupons/WINBACK99 → {
  "code": "WINBACK99",
  "type": "percentage",
  "percentOff": 33,
  "stripeCouponId": "WINBACK99",
  "maxRedemptions": 1000,
  "currentRedemptions": 0,
  "expiresAt": null,
  "createdBy": "system"
}
```

## Components

### Component 1: Updated PostConfirmation Lambda

**File:** `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`

**Change:** Replace the 14-day premium trial creation block with a free-plan record creation.

**Current behavior:** Creates `planId: premium`, `status: trialing`, `trialExpiresAt: now + 14 days`.

**New behavior:** Creates `planId: free`, `status: active`, `level1CompletionPercent: 0`, `totalQuestionsCompleted: 0`, `benefactorCount: 0`. No trial fields.

**Condition expression:** `attribute_not_exists(userId)` to prevent overwriting existing records (idempotency).

### Component 2: Updated Plan Check Utility

**File:** `SamLambda/functions/shared/python/plan_check.py`

**Changes:**
- `_get_plan_definition()` — No structural change needed; already loads from SSM. The new plan JSON includes `maxLevel` which the existing code doesn't check.
- `check_question_category_access()` — Add level check: parse the question ID to extract the level number, compare against `plan_def['maxLevel']`. If level > maxLevel, deny with `limitType: question_level`. The existing category check remains.
- `is_premium_active()` — Keep `active` and `comped` as premium. Keep `trialing` with valid `couponExpiresAt` as premium (for coupon-based trials). Also keep `trialing` with valid `trialExpiresAt` as premium for backward compatibility with existing trial users (this path will naturally phase out as trials expire). Remove creation of new signup trials.
- Remove `conversationsPerWeek` enforcement from any check paths.
- `_parse_question_id()` — Already extracts level from question ID format `{category}-{subcategory}-L{level}-Q{number}`. Verify it returns the level as an integer.

**Level check logic (inserted before category check):**
```python
question_level = _parse_question_id(question_id)[2]  # Extract level number
max_level = plan_def.get('maxLevel', 10)
if question_level > max_level:
    return {
        'allowed': False,
        'reason': 'question_level',
        'message': f'Level {question_level} questions are available with Premium. '
                   f'Upgrade to unlock all 10 levels of deeper questions.'
    }
```

### Component 3: Level 1 Completion Tracking in WebSocket Handler

**File:** `SamLambda/functions/conversationFunctions/wsDefault/app.py`

**Changes to `handle_end_conversation()`:**

After a conversation ends successfully, if the user is on the free plan:
1. Query the user's completed questions from ConversationStateDB (or UserProgressDB) to count Level 1 completions.
2. Query the total number of Level 1 questions from the QuestionDB table (filter by `difficulty: 1` or `level: 1`). Cache this count in a module-level variable since it rarely changes.
3. Calculate `level1CompletionPercent = (completed_L1_questions / total_L1_questions) * 100`, clamped to [0, 100].
4. Update UserSubscriptionsDB with the new `level1CompletionPercent`.
5. If `level1CompletionPercent == 100`, also set `level1CompletedAt` to current UTC timestamp.
6. Increment `totalQuestionsCompleted` counter via an atomic `ADD` update expression.

**New helper function:**
```python
_total_l1_questions_cache = None

def _get_total_l1_questions() -> int:
    """Get total Level 1 questions, cached for Lambda lifetime."""
    global _total_l1_questions_cache
    if _total_l1_questions_cache is None:
        # Query QuestionDB for count of Level 1 questions
        # ... scan with filter difficulty=1 or level=1
        _total_l1_questions_cache = count
    return _total_l1_questions_cache

def _update_level1_progress(user_id: str):
    """Update Level 1 completion tracking for free users."""
    sub_record = get_user_plan(user_id)
    if sub_record.get('planId') != 'free':
        return  # Only track for free users
    
    total_l1 = _get_total_l1_questions()
    if total_l1 == 0:
        return
    
    # Count completed L1 questions from UserProgressDB
    # ... query with filter for level=1 and status=completed
    completed_l1 = ...
    
    percent = min(100, int((completed_l1 / total_l1) * 100))
    
    update_expr = 'SET level1CompletionPercent = :pct, updatedAt = :now ADD totalQuestionsCompleted :one'
    expr_values = {':pct': percent, ':now': now_iso, ':one': 1}
    
    if percent == 100:
        update_expr += ', level1CompletedAt = if_not_exists(level1CompletedAt, :now)'
    
    subscriptions_table.update_item(
        Key={'userId': user_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values
    )
```

**Remove:** `_increment_weekly_conversation_count()` function and its call in `handle_start_conversation()`. No weekly caps in the new model.

### Component 4: Polly Caching in Speech Module

**File:** `SamLambda/functions/conversationFunctions/wsDefault/speech.py`

**Change to `text_to_speech()`:**

For turn 0 (initial question greeting), check for a cached audio file before calling Polly:

```python
def text_to_speech(text, user_id, question_id, turn_number, voice_id, engine):
    # For turn 0, use shared cache
    if turn_number == 0:
        cache_key = f"polly-cache/{question_id}/{voice_id}-{engine}.mp3"
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
            # Cache hit — return presigned URL
            audio_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': cache_key},
                ExpiresIn=3600
            )
            print(f"[POLLY] Cache hit for {cache_key}")
            return audio_url
        except s3_client.exceptions.ClientError:
            # Cache miss — synthesize and store at cache key
            print(f"[POLLY] Cache miss for {cache_key}, synthesizing...")
            pass
    
    # Existing Polly synthesis logic...
    response = polly.synthesize_speech(...)
    audio_data = response['AudioStream'].read()
    
    # For turn 0, store at cache key (shared across users)
    if turn_number == 0:
        s3_key = cache_key
    else:
        # Per-user key for follow-up responses
        timestamp = int(datetime.now().timestamp())
        s3_key = f"conversations/{user_id}/{question_id}/ai-audio/turn-{turn_number}-{timestamp}.mp3"
    
    s3_client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=audio_data, ...)
    # ... generate and return presigned URL
```

**Note:** Cached files use a shared `polly-cache/` prefix, not per-user paths. KMS encryption is required — the `put_object` call must include `ServerSideEncryption='aws:kms'` and `SSEKMSKeyId=kms_key_arn` (same as existing uploads). The cache key is deterministic: same question + same voice + same engine = same file.

### Component 5: Updated Billing Lambda

**File:** `SamLambda/functions/billingFunctions/billing/app.py`

**Changes:**
- `handle_get_plans()` — Add founding member coupon availability: read the FOUNDING100 coupon from SSM, include `foundingMemberAvailable: (currentRedemptions < maxRedemptions)` and `foundingMemberSlotsRemaining` in the response.
- `handle_status()` — Include `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted`, `couponExpiresAt` in the response. Remove `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek` (no weekly caps).
- `handle_create_checkout()` — Update Stripe Price IDs to the new $14.99 monthly and $149 annual prices. Accept an optional `couponId` in the request body. When `couponId` is provided, pass it to `stripe.checkout.Session.create()` as `discounts=[{"coupon": couponId}]`. This is the primary mechanism for founding member pricing: the frontend calls `/billing/apply-coupon` first to validate the code and get the `stripeCouponId`, then passes it to checkout.
- `_load_all_plans()` — No change needed; already loads from SSM. The new plan JSON structure is backward-compatible.

### Component 6: Updated Webhook Lambda

**File:** `SamLambda/functions/billingFunctions/stripeWebhook/app.py`

**Changes:**
- `_handle_checkout_completed()` — Store `billingInterval` based on the Stripe Price ID (monthly or annual). Update the price-to-plan mapping for new Stripe prices.
- Price mapping: `{ "price_monthly_1499": {"planId": "premium", "interval": "monthly"}, "price_annual_149": {"planId": "premium", "interval": "annual"} }` (actual Stripe Price IDs to be configured).

### Component 7: Updated Win-Back / Re-engagement Lambda

**File:** `SamLambda/functions/billingFunctions/winBack/app.py`

**Changes:**
- Add a new scan for Level 1 completers: query UserSubscriptionsDB for `planId == free AND level1CompletedAt IS NOT NULL AND level1CompletedAt < (now - 7 days) AND (lastReengagementEmailAt IS NULL OR lastReengagementEmailAt < (now - 7 days))`.
- Send re-engagement email via SES with subject "Your stories are preserved. Your family is waiting for the deeper ones."
- Update `lastReengagementEmailAt` after sending.
- Include unsubscribe link in email body.
- Existing win-back logic for churned subscribers remains unchanged.

### Component 8: Updated SubscriptionContext

**File:** `FrontEndCode/src/contexts/SubscriptionContext.tsx`

**Changes:**
- Remove `trialExpiresAt`, `trialDaysRemaining` from `SubscriptionState` interface.
- Add `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted`, `couponExpiresAt`.
- Update `FREE_PLAN_LIMITS`: change `maxBenefactors` from 2 to 1. Remove `conversationsPerWeek`. Add `maxLevel: 1`.
- Update `computeIsPremium()`: remove trial expiry check. Premium = `status === 'active' || status === 'comped' || (status === 'trialing' && couponExpiresAt && new Date(couponExpiresAt) > Date.now())`.
- Remove `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek` from state.

### Component 9: Level 1 Celebration Screen Component

**File:** `FrontEndCode/src/components/Level1CelebrationScreen.tsx` (new)

**Behavior:**
- Shown as a modal overlay when the Dashboard detects `level1CompletedAt` transitioned from null to a value (tracked via localStorage flag `level1CelebrationShown`).
- Displays: congratulatory message, number of stories recorded, Level 1 categories completed, locked Levels 2–10 with category names and lock icons, personalized Life Events question count (from survey data), Premium price, and "Upgrade to Premium" CTA button.
- Dismissible via close button or "Maybe Later" link.
- On "Upgrade to Premium" click: navigate to `/pricing?plan=annual`.

**Data sources:**
- `level1CompletionPercent` and `level1CompletedAt` from SubscriptionContext.
- Level category names: hardcoded mapping (Level 2 = "Hobbies & Traditions", ..., Level 10 = "Messages to Loved Ones").
- Life Events question count: fetched from survey service or passed via SubscriptionContext.

### Component 10: Upgrade Banner Components

**File:** `FrontEndCode/src/components/UpgradeBanner.tsx` (new)

**Variants:**
1. **HalfwayBanner** — Shown when `level1CompletionPercent >= 50 && !level1CompletedAt`. Message: "You're halfway through Level 1. Premium unlocks 9 more levels of deeper questions." Dismissible, re-shows on next dashboard visit.

2. **PostCompletionBanner** — Shown when `level1CompletedAt` is set. Persistent "Continue your legacy" section with locked level progression and upgrade CTA. Not dismissible (always shown on dashboard for free users post-completion).

3. **BenefactorAwareBanner** — Shown when `level1CompletedAt` is set AND `benefactorCount > 0`. Message: "Your [name] can see your Level 1 stories. Upgrade to share the stories that really matter." Requires benefactor name from assignment data.

4. **LifeEventsTeaser** — Shown when `level1CompletedAt` is set. Displays "X personalized questions waiting for you" with lock icon.

### Component 11: Updated Dashboard Locked Content

**File:** `FrontEndCode/src/pages/Dashboard.tsx`

**Changes:**
- Life Events and Values & Emotions cards: show lock icon + "Premium" badge for free users (existing behavior, verify it works with new plan structure).
- Life Story Reflections card: show Levels 2–10 with lock icons for free users. Level 1 shows as accessible/completed.
- On tap of locked card: show preview overlay with sample question and "Subscribe to unlock" CTA.
- Integrate celebration screen trigger: check if `level1CompletedAt` is newly set and `localStorage.getItem('level1CelebrationShown')` is not set.
- Integrate upgrade banners based on `level1CompletionPercent` and `level1CompletedAt`.

### Component 12: Updated Pricing Page

**File:** `FrontEndCode/src/pages/PricingPage.tsx`

**Changes:**
- Update pricing display: $14.99/month, $149/year (from Plan_Definition, not hardcoded).
- Default billing toggle to "Annual" with "Save 17%" badge.
- Add "Less than a cup of coffee a week" anchoring text below annual price.
- Add founding member pricing: if `foundingMemberAvailable` from `/billing/plans`, show "$99/year — Founding Member Rate" with slots remaining count. Otherwise show $149/year.
- Add trust messaging with shield icon below plan comparison.
- Free tier description: "Complete Level 1 — Childhood, Family, School & Friends. Full AI quality. Share with 1 family member."
- Premium tier description: "All 10 levels — from Childhood to Messages to Loved Ones. Life Events. Values & Emotions. Unlimited benefactors. Data export."

### Component 13: Updated Home Page

**File:** `FrontEndCode/src/pages/Home.tsx`

**Changes:**
- Update pricing section with new prices from `/billing/plans` endpoint.
- Change primary CTA to "Start Free".
- Add "Pricing" link to footer navigation.
- Display annual price as primary with monthly equivalent.

### Component 14: Cost Optimization — SSM Parameter Updates

**No code changes required.** These are SSM parameter updates deployed via CLI scripts:

1. Depth scoring model: `aws ssm put-parameter --name "/virtuallegacy/conversation/llm-scoring-model" --value "amazon.nova-micro-v1:0" --type String --overwrite`
2. Conversation model: `aws ssm put-parameter --name "/virtuallegacy/conversation/llm-conversation-model" --value "us.anthropic.claude-3-5-haiku-20241022-v1:0" --type String --overwrite`

**template.yml change required:** Add Nova Micro model ARN to WebSocketDefaultFunction's Bedrock IAM policy.

### Component 15: Cost Optimization — Deepgram Batch for Video Transcription

**File:** `SamLambda/functions/videoFunctions/processVideo/app.py` (or equivalent)

**Changes:**
- Replace AWS Transcribe `start_transcription_job()` call with Deepgram batch API call.
- Use Deepgram API key from SSM (`/soulreel/deepgram/api-key` — already exists for real-time transcription).
- Parse Deepgram response into the same transcript format expected by the summarization function.
- Update template.yml: remove `transcribe:StartTranscriptionJob` and `transcribe:GetTranscriptionJob` IAM permissions from ProcessVideoFunction.

### Component 16: Migration Script

**File:** `SamLambda/scripts/migrate_existing_users.py` (new)

**One-time script** to run before or alongside deployment:
1. Scan all Cognito users.
2. For each user without a UserSubscriptionsDB record, create one with `planId: free`, `status: active`.
3. For each user, calculate `level1CompletionPercent` from ConversationStateDB/UserProgressDB.
4. For each user, calculate `benefactorCount` from AssignmentsDB.
5. For each user, calculate `totalQuestionsCompleted`.
6. Use `attribute_not_exists(userId)` condition to prevent overwriting existing records.
7. Idempotent — safe to run multiple times.

**Critical:** Existing content beyond Level 1 remains viewable. The content-level gate only applies to starting NEW conversations, not viewing existing recordings, transcripts, or summaries.

### Component 17: Public Plans Endpoint

**File:** `SamLambda/functions/billingFunctions/billing/app.py`

The `handle_get_plans()` function already exists. Update it to:
- Include `foundingMemberAvailable` boolean and `foundingMemberSlotsRemaining` count.
- Read the FOUNDING100 coupon from SSM and check `currentRedemptions < maxRedemptions`.
- Return pricing display fields from the Premium plan definition.

**template.yml:** The `/billing/plans` GET endpoint already exists without auth. Verify it's configured correctly.

### Component 18: User Plan Settings Section

**File:** `FrontEndCode/src/pages/YourData.tsx` or `FrontEndCode/src/components/PlanSettingsSection.tsx` (new)

**Behavior:**
- Displays current plan name (Free or Premium) and status.
- For free users: shows "Upgrade to Premium" button linking to `/pricing`. Shows benefactor count and Level 1 completion progress bar.
- For premium users: shows "Manage Subscription" button that calls `GET /billing/portal` and redirects to Stripe Customer Portal. Shows billing interval (monthly/annual).
- Uses `useSubscription()` hook for all data.

### Component 19: Benefactor Name Resolution for Upgrade Banners

**File:** `FrontEndCode/src/components/UpgradeBanner.tsx`

The benefactor-aware banner (variant 3) needs the benefactor's name. This is fetched from the existing assignment service (`assignmentService.ts`) which already provides benefactor details. The Dashboard already loads assignment data — pass the first benefactor's name to the `BenefactorAwareBanner` component as a prop.

## Deployment Order

The changes have dependencies that require a specific deployment sequence:

### Phase A: Infrastructure & SSM (deploy first)
1. Update SSM plan definitions (`/soulreel/plans/free`, `/soulreel/plans/premium`) with new structure.
2. Create founding member and win-back coupons in SSM.
3. Create Stripe products and prices ($14.99 monthly, $149 annual).
4. Create Stripe coupons (FOUNDING100, WINBACK99).
5. Configure Stripe webhook endpoint for new URL if changed.
6. Update SSM scoring model to Nova Micro.
7. Update SSM conversation model to Haiku.

### Phase B: Migration (run before code deploy)
1. Run `migrate_existing_users.py` to create UserSubscriptionsDB records for all existing users.
2. Verify migration completed successfully (spot-check records).

### Phase C: Backend Deploy (SAM build + deploy)
1. template.yml changes (Nova Micro IAM, WebSocketDefaultFunction UpdateItem permission).
2. PostConfirmation Lambda update (free plan instead of trial).
3. plan_check.py update (level-based gating).
4. wsDefault/app.py update (Level 1 tracking, remove weekly caps).
5. speech.py update (Polly caching).
6. billing/app.py update (new pricing, founding member availability).
7. stripeWebhook/app.py update (billingInterval, new price mapping).
8. winBack/app.py update (re-engagement emails).

### Phase D: Frontend Deploy (Amplify)
1. SubscriptionContext update.
2. billingService.ts update.
3. PricingPage.tsx update.
4. Dashboard.tsx update (locked content, banners, celebration screen).
5. Home.tsx update.
6. New components (Level1CelebrationScreen, UpgradeBanner, PlanSettingsSection).

### Phase E: Post-Deploy Verification
1. Verify plan check works: free user blocked from Level 2, allowed Level 1.
2. Verify Polly cache: second conversation for same question uses cached audio.
3. Verify founding member coupon: apply FOUNDING100, checkout at $99.
4. Verify webhook: complete checkout, verify UserSubscriptionsDB updated.
5. Verify pricing page: shows correct prices, founding member availability.

### Handling Existing Trial Users
Existing users currently on a 14-day trial (`status: trialing`, `trialExpiresAt` set) will be handled naturally:
- The Coupon_Expiration_Service already scans for expired trials and reverts them to free.
- The updated `is_premium_active()` in plan_check.py will still recognize `trialing` with valid `trialExpiresAt` as premium (backward compatibility).
- Once their trial expires, they become free users and experience the new Level 1 gate.
- No forced migration needed — let trials expire naturally.

## Data Flow Diagrams

### Free User Conversation Flow (with Level Gate)

```
User taps "Start Conversation" on Level 2 question
  → Frontend sends WebSocket message: { action: "start_conversation", questionId: "life_story_reflections-hobbies-L2-Q1" }
  → wsDefault/app.py: handle_start_conversation()
    → plan_check.check_question_category_access(userId, questionId)
      → get_user_plan(userId) → reads UserSubscriptionsDB → { planId: "free" }
      → _get_plan_definition("free") → reads SSM → { maxLevel: 1 }
      → _parse_question_id(questionId) → level = 2
      → 2 > 1 → DENIED
    → send_message: { type: "limit_reached", limitType: "question_level", message: "..." }
  → Frontend shows UpgradePromptDialog
```

### Free User Completes Level 1 Question

```
User finishes conversation for last Level 1 question
  → wsDefault/app.py: handle_end_conversation()
    → Summarize conversation (existing logic)
    → _update_level1_progress(userId)
      → Query completed L1 questions → 20/20 = 100%
      → Update UserSubscriptionsDB: level1CompletionPercent=100, level1CompletedAt=now
  → User returns to Dashboard
    → SubscriptionContext fetches /billing/status → level1CompletedAt is set
    → Dashboard detects level1CompletedAt is new (localStorage check)
    → Shows Level1CelebrationScreen modal
```

### Founding Member Checkout Flow

```
User on Pricing Page sees "Founding Member — $99/year (X slots remaining)"
  → Clicks "Subscribe at Founding Member Rate"
  → Frontend calls POST /billing/apply-coupon { code: "FOUNDING100" }
    → Billing Lambda validates: code exists, not expired, under max redemptions, user not already premium
    → Returns { success: true, type: "percentage", stripeCouponId: "FOUNDING100" }
  → Frontend calls POST /billing/create-checkout-session { priceId: "price_annual_149", couponId: "FOUNDING100" }
    → Billing Lambda creates Stripe Checkout Session with:
      - price: $149/year annual price
      - discounts: [{ coupon: "FOUNDING100" }]  → effective price: $99
      - metadata: { userId: "cognito-sub" }
  → User redirected to Stripe Checkout → pays $99
  → Stripe fires checkout.session.completed webhook
    → stripeWebhook: update UserSubscriptionsDB { planId: premium, status: active, billingInterval: annual }
    → Billing Lambda increments FOUNDING100 currentRedemptions in SSM
```

### Weekly Re-engagement Email Flow

```
EventBridge weekly trigger → winBack Lambda
  → Scan UserSubscriptionsDB:
    planId = "free"
    AND level1CompletedAt IS NOT NULL
    AND level1CompletedAt < (now - 7 days)
    AND (lastReengagementEmailAt IS NULL OR lastReengagementEmailAt < (now - 7 days))
  → For each qualifying user:
    → SES.send_email(subject: "Your stories are preserved...", body: ...)
    → Update UserSubscriptionsDB: lastReengagementEmailAt = now
```

## Correctness Properties

### Property 1: Plan Check Level Enforcement Consistency

For all question IDs with level L and all users with plan maxLevel M:
- If L <= M, the plan check allows access (assuming category is also allowed).
- If L > M, the plan check denies access with `limitType: question_level`.

This is a metamorphic property: increasing the plan's maxLevel should only increase the set of allowed questions, never decrease it.

### Property 2: Subscription Record Initialization Idempotency

For all user IDs, calling the subscription record creation function multiple times produces the same result as calling it once. The condition expression `attribute_not_exists(userId)` ensures no overwrites.

### Property 3: Coupon Redemption Counter Monotonicity

For all coupons, `currentRedemptions` is monotonically non-decreasing. Each successful redemption increments by exactly 1. When `currentRedemptions >= maxRedemptions`, all subsequent redemption attempts are rejected.

### Property 4: Level 1 Completion Percentage Bounds

For all users, `level1CompletionPercent` is always in the range [0, 100]. It is monotonically non-decreasing for free users (completing a question can only increase or maintain the percentage, never decrease it).

### Property 5: Polly Cache Determinism

For all question IDs Q, voice IDs V, and engines E: the cache key `polly-cache/{Q}/{V}-{E}.mp3` is deterministic. Two calls with the same (Q, V, E) produce the same cache key. The cached audio content is identical to what Polly would synthesize for the same text.

### Property 6: Webhook Idempotency

Processing the same Stripe webhook event multiple times produces the same final state in UserSubscriptionsDB. The webhook uses `PutItem` with full attribute replacement for subscription fields, preserving usage counters.

### Property 7: Billing Interval Round-Trip

For all checkout completions, the `billingInterval` stored in UserSubscriptionsDB matches the Stripe Price ID's interval. Monthly prices map to "monthly", annual prices map to "annual".

### Property 8: Migration Script Idempotency

Running the migration script N times (N >= 1) produces the same UserSubscriptionsDB state as running it once. The `attribute_not_exists(userId)` condition prevents overwrites of records created by the PostConfirmation trigger or by previous migration runs.

### Property 9: Free User Post-Completion Zero Cost

For all free users where `level1CompletedAt` is not null and no new conversations are started, the monthly AI processing cost is $0. The content-level gate prevents new conversations beyond Level 1, and existing content incurs only negligible S3 storage costs.

### Property 10: Founding Member Coupon Exhaustion

When `currentRedemptions` reaches `maxRedemptions` (100), the `/billing/plans` endpoint returns `foundingMemberAvailable: false`, and the Pricing Page displays the standard $149/year price instead of the $99 founding member rate.
