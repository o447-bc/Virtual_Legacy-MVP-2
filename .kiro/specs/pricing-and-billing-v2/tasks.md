# Implementation Plan: Pricing & Billing V2

## Overview

This plan updates SoulReel's existing billing infrastructure from the old pricing model (14-day trial, $9.99/$79 pricing, `_L1` suffix gating, `maxBenefactors: 2` for free, weekly conversation caps) to the new 2-tier model (Free + Premium at $14.99/month or $149/year) with content-level gating via `maxLevel` field instead of usage caps. The billing infrastructure (DynamoDB table, Stripe layer, billing Lambda, webhook Lambda, coupon system, plan_check.py, frontend SubscriptionContext, PricingPage, billingService) already exists — this plan updates it to the new pricing model and adds Level 1 completion tracking and engagement features.

Key existing infrastructure (verified by audit):
- UserSubscriptionsDB table with stripeCustomerId GSI ✅
- StripeDependencyLayer with stripe Python SDK ✅
- BillingFunction with checkout/status/portal/coupon/plans endpoints ✅
- StripeWebhookFunction with signature verification and event handling ✅
- CouponExpirationFunction and WinBackFunction ✅
- plan_check.py with category gating and benefactor limits ✅
- SubscriptionContext.tsx, billingService.ts, PricingPage.tsx ✅
- Stripe Price IDs configured (old: $9.99 monthly, $79 annual) ✅

Key changes needed:
- SSM plan definitions: add `maxLevel`, update pricing display fields, change `maxBenefactors` to 1
- plan_check.py: replace `_L1` suffix logic with `maxLevel` comparison, remove preview questions
- PostConfirmation: change from 14-day trial to free-plan record
- billing/app.py: add Level 1 fields to status, founding member to plans, couponId to checkout
- stripeWebhook: new Stripe Price IDs, add `billingInterval` storage
- wsDefault: add Level 1 completion tracking, remove weekly conversation counting
- speech.py: add Polly caching for turn 0
- Frontend: remove trial fields, add Level 1 fields, update pricing, add celebration/banners

Backend is Python (SAM/Lambda) using pytest + hypothesis. Frontend is TypeScript/React using vitest + fast-check.

## Tasks

- [x] 1. Phase A: SSM Parameters & IAM Updates
  - [x] 1.1 Update SSM parameter deployment script with new plan definitions
    - Update existing `SamLambda/scripts/setup-ssm-params.sh` (or create `deploy_ssm_params_v2.sh`) to set the new plan structure:
    - `/soulreel/plans/free`: add `maxLevel: 1`; keep `allowedQuestionCategories: [life_story_reflections]` (remove `_L1` suffix — level gating now handled by `maxLevel`); change `maxBenefactors` from 2 to 1; remove `previewQuestions`; keep `features: [basic]`
    - `/soulreel/plans/premium`: add `maxLevel: 10`; keep `allowedQuestionCategories: [life_story_reflections, life_events, values_and_emotions]`; update pricing display fields from `monthlyPriceDisplay: "$9.99", annualPriceDisplay: "$79", annualMonthlyEquivalentDisplay: "$6.58", annualSavingsPercent: 34` to `monthlyPriceDisplay: "$14.99", annualPriceDisplay: "$149", annualMonthlyEquivalentDisplay: "$12.42", annualSavingsPercent: 17`; add `foundingMemberPrice: 99, foundingMemberCouponCode: FOUNDING100`
    - NOTE: keep the key name `allowedQuestionCategories` (not `allowedCategories`) to avoid breaking existing code that reads this field — plan_check.py and billing/app.py both reference `allowedQuestionCategories`
    - Create `/soulreel/coupons/FOUNDING100` (type: percentage, percentOff: 33, stripeCouponId: FOUNDING100, maxRedemptions: 100, currentRedemptions: 0)
    - Create `/soulreel/coupons/WINBACK99` (type: percentage, percentOff: 33, stripeCouponId: WINBACK99, maxRedemptions: 1000, currentRedemptions: 0)
    - Update `/virtuallegacy/conversation/llm-scoring-model` → `amazon.nova-micro-v1:0`
    - Update `/virtuallegacy/conversation/llm-conversation-model` → `us.anthropic.claude-3-5-haiku-20241022-v1:0`
    - PREREQUISITE: Create new Stripe products/prices in Stripe Dashboard ($14.99/month, $149/year) and note the Price IDs for task 5.1
    - _Requirements: 3.1–3.7, 15.4, 21.1, 22.1, 27.1, 28.1_

  - [x] 1.2 Update template.yml IAM policies for Nova Micro model access
    - Add `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0` to WebSocketDefaultFunction's Bedrock InvokeModel resource list
    - Verify all existing billing IAM policies are sufficient (UserSubscriptionsDB CRUD, SSM read/write for coupons, Stripe secrets) — these should already be in place from the previous spec
    - _Requirements: 14.1, 21.2_

  - [x] 1.3 Validate template.yml with `sam validate --lint`
    - Run `sam validate --lint` from `SamLambda/` and fix any errors
    - _Requirements: 14.1–14.4_


- [x] 2. Phase B: Backend — Update plan_check.py to new gating model
  - [x] 2.1 Update plan_check.py with maxLevel-based gating (replacing _L1 suffix pattern)
    - File: `SamLambda/functions/shared/python/plan_check.py`
    - In `_get_plan_definition()`: update fallback default to use `maxLevel: 1, allowedQuestionCategories: [life_story_reflections]` (remove `_L1` suffix — level gating now via `maxLevel`); change `maxBenefactors` default from 2 to 1
    - In `_FREE_PLAN_DEFAULT`: remove `trialExpiresAt` field
    - In `check_question_category_access()`: replace the `_L1` suffix parsing logic (Check 2) with a simple `maxLevel` comparison — extract level from question ID via `_parse_question_id()`, compare against `plan_def.get('maxLevel', 1)`, deny with `limitType: question_level` if level > maxLevel. Keep the category check (Check 1) using the existing `allowedQuestionCategories` key name (NOT renaming to `allowedCategories` — keep backward compat with SSM and billing code)
    - In `check_question_category_access()`: remove the preview question logic (`previewQuestions`, `_has_completed_preview()`) — no longer needed with the "Complete Level 1" model
    - In `is_premium_active()`: keep `active` and `comped` as premium; keep `trialing` with valid `trialExpiresAt` for backward compat (existing trial users); also recognize `trialing` with valid `couponExpiresAt` as premium (for coupon-based trials)
    - In `check_benefactor_limit()`: update default `maxBenefactors` from 2 to 1 in fallback; add access condition type check — read `accessConditionTypes` from plan definition, deny if requested condition type is not in the list
    - Remove `conversationsPerWeek` references from all code paths
    - _Requirements: 10.1–10.6, 11.1–11.5_

  - [x] 2.2 Write unit tests for updated plan_check.py
    - File: `SamLambda/tests/test_plan_check.py` using pytest + hypothesis + unittest.mock
    - **Level gating tests:**
    - Test: free user (maxLevel=1) on Level 1 question → allowed
    - Test: free user (maxLevel=1) on Level 2 question → denied with `limitType: question_level`
    - Test: free user on Level 5 question → denied
    - Test: free user on `life_events` category → denied with `limitType: question_category`
    - Test: free user on `values_and_emotions` category → denied
    - Test: free user on `life_story_reflections` Level 1 → allowed (both category and level pass)
    - **Premium status tests:**
    - Test: premium user (status: active) on any level → allowed
    - Test: premium user (status: comped) on any level → allowed
    - Test: trialing user with valid `trialExpiresAt` → allowed (backward compat)
    - Test: trialing user with expired `trialExpiresAt` → denied (treated as free)
    - Test: trialing user with valid `couponExpiresAt` → allowed
    - Test: trialing user with expired `couponExpiresAt` → denied
    - Test: canceled user → denied (treated as free)
    - Test: user with no subscription record → treated as free, Level 1 only
    - **Benefactor limit tests:**
    - Test: free user with 0 benefactors → allowed (limit is 1)
    - Test: free user with 1 benefactor → denied (at limit)
    - Test: premium user with any count → allowed (unlimited)
    - Test: free user with `immediate` access condition → allowed
    - Test: free user with `time_delayed` access condition → denied
    - **Removed features tests:**
    - Test: no `conversationsPerWeek` enforcement exists
    - Test: no preview question logic exists
    - **Property test (hypothesis):** For all levels L (1–10) and maxLevels M (1–10): L <= M → allowed, L > M → denied. Monotonic: increasing M only increases allowed set.
    - _Validates: Requirements 10.1–10.6, 11.1–11.5_

- [x] 3. Phase B: Backend — Update PostConfirmation Lambda
  - [x] 3.1 Update PostConfirmation Lambda from 14-day trial to free-plan record
    - File: `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`
    - Change the subscription record creation (around line 213) from `planId: premium, status: trialing, trialExpiresAt: now+14days` to `planId: free, status: active, level1CompletionPercent: 0, totalQuestionsCompleted: 0, benefactorCount: 0`
    - Remove `trialExpiresAt` field from the created record
    - Add `attribute_not_exists(userId)` condition expression to prevent overwrites on duplicate triggers
    - Keep all other PostConfirmation logic unchanged (persona handling, invite processing, email capture)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.2 Write unit tests for PostConfirmation subscription record
    - File: `SamLambda/tests/test_post_confirmation.py` using pytest + unittest.mock
    - Test: new legacy_maker signup creates record with `planId: free`, `status: active`
    - Test: record includes `level1CompletionPercent: 0`, `totalQuestionsCompleted: 0`, `benefactorCount: 0`
    - Test: record does NOT include `trialExpiresAt`
    - Test: record does NOT have `planId: premium` or `status: trialing`
    - Test: duplicate trigger does NOT overwrite existing record
    - **Property test (hypothesis):** For all user IDs, the created record always has `planId: free` and `status: active`
    - _Validates: Requirements 2.1, 2.2, 2.3_

- [x] 4. Phase B: Backend — Update billing/app.py
  - [x] 4.1 Update billing Lambda with new pricing, founding member availability, and Level 1 fields
    - File: `SamLambda/functions/billingFunctions/billing/app.py`
    - In `handle_status()`: add `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted` to response; remove `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek`, `trialExpiresAt`
    - In `handle_get_plans()`: read FOUNDING100 coupon from SSM, include `foundingMemberAvailable` boolean and `foundingMemberSlotsRemaining` count in response alongside plan definitions
    - In `handle_create_checkout()`: accept optional `couponId` in request body; when present, pass to `stripe.checkout.Session.create()` as `discounts=[{"coupon": couponId}]`
    - In `_get_plan_definition()` fallback: update to use `maxLevel: 1, allowedQuestionCategories: [life_story_reflections]` (remove `_L1` suffix); change `maxBenefactors` from 2 to 1
    - _Requirements: 4.1–4.8, 6.1–6.4, 27.2, 27.3, 33.1–33.4_

  - [x] 4.2 Write unit tests for updated billing Lambda
    - File: `SamLambda/tests/test_billing.py` using pytest + hypothesis + unittest.mock (mock Stripe SDK, DynamoDB, SSM)
    - **Status endpoint tests:**
    - Test: response includes `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`
    - Test: response does NOT include `conversationsThisWeek`, `weekResetDate`, `trialExpiresAt`
    - Test: user with no record → returns free plan with `maxLevel: 1`, `maxBenefactors: 1`
    - **Checkout tests:**
    - Test: optional couponId passed → included in `discounts` on Checkout Session
    - Test: missing priceId → HTTP 400
    - Test: CORS headers present on all responses
    - **Plans endpoint tests:**
    - Test: response includes `foundingMemberAvailable: true` when coupon has remaining slots
    - Test: response includes `foundingMemberAvailable: false` when coupon exhausted
    - Test: response includes `foundingMemberSlotsRemaining` count
    - **Coupon tests (existing logic, verify still works):**
    - Test: valid `forever_free` coupon → `planId: premium`, `status: comped`
    - Test: expired coupon → HTTP 400
    - Test: coupon at maxRedemptions → HTTP 400
    - **Property test (hypothesis):** For all coupon redemption sequences: `currentRedemptions` monotonically non-decreasing, rejects when >= maxRedemptions
    - _Validates: Requirements 4.1–4.8, 6.1–6.4, 8.1–8.10, 27.2, 27.3, 33.1–33.4_


- [x] 5. Phase B: Backend — Update webhook Lambda
  - [x] 5.1 Update stripeWebhook/app.py with billingInterval and new price mapping
    - File: `SamLambda/functions/billingFunctions/stripeWebhook/app.py`
    - Update price-to-plan mapping: replace existing Stripe Price IDs (`price_1TL03V6hMyNf0PnbOaSd399o` for monthly, `price_1TL06w6hMyNf0PnbCgehYyZB` for annual) with new Price IDs for $14.99 monthly and $149 annual (created in Stripe Dashboard as prerequisite in task 1.1) — both map to `premium`
    - In `_handle_checkout_completed()`: store `billingInterval` (monthly or annual) based on Stripe Price ID
    - Ensure `UpdateExpression` (not `PutItem`) is used for subscription updates to preserve `level1CompletionPercent`, `level1CompletedAt`, `totalQuestionsCompleted`, `benefactorCount`
    - _Requirements: 5.1–5.11_

  - [x] 5.2 Write unit tests for updated webhook Lambda
    - File: `SamLambda/tests/test_stripe_webhook.py` using pytest + unittest.mock
    - Test: checkout.session.completed with monthly price → `billingInterval: monthly`, `planId: premium`
    - Test: checkout.session.completed with annual price → `billingInterval: annual`, `planId: premium`
    - Test: existing `level1CompletionPercent` and `benefactorCount` preserved after checkout update
    - Test: subscription.deleted → `planId: free`, `status: canceled`
    - Test: invoice.payment_failed → `status: past_due`
    - Test: invalid signature → HTTP 400, no DB writes
    - Test: same event processed twice → same final DB state (idempotency)
    - _Validates: Requirements 5.1–5.11_

- [x] 6. Phase B: Backend — Level 1 Completion Tracking in WebSocket Handler
  - [x] 6.1 Add Level 1 completion tracking to wsDefault/app.py
    - File: `SamLambda/functions/conversationFunctions/wsDefault/app.py`
    - Add `_update_level1_progress(user_id)` helper: query completed L1 questions from UserProgressDB/ConversationStateDB, calculate percentage, update UserSubscriptionsDB with `level1CompletionPercent`, set `level1CompletedAt` when 100%
    - Add `_get_total_l1_questions()` with module-level cache (query QuestionDB once per Lambda cold start)
    - Increment `totalQuestionsCompleted` via atomic `ADD` update expression; when counter reaches 300, set `legacyCompleteAt` timestamp
    - Call `_update_level1_progress()` in `handle_end_conversation()` for free users only
    - Remove `_increment_weekly_conversation_count()` and its call if it exists (no weekly caps in new model)
    - Add annual-plan nudge: when a premium monthly user completes their 50th conversation in a calendar month, send a one-time WebSocket message suggesting the annual plan
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 26.1, 26.2, 26.3, 29.1, 29.2_

  - [x] 6.2 Write unit tests for Level 1 completion tracking
    - File: `SamLambda/tests/test_level1_tracking.py` using pytest + hypothesis + unittest.mock
    - Test: free user completes 1 of 20 L1 questions → `level1CompletionPercent` = 5
    - Test: free user completes 10 of 20 → percent = 50
    - Test: free user completes 20 of 20 → percent = 100, `level1CompletedAt` set
    - Test: premium user completing a question does NOT update Level 1 tracking
    - Test: `totalQuestionsCompleted` increments by 1 per conversation
    - Test: `totalQuestionsCompleted` reaching 300 sets `legacyCompleteAt`
    - Test: `_get_total_l1_questions()` caches result (only 1 DynamoDB query across calls)
    - Test: monthly subscriber at 50 conversations gets annual nudge
    - Test: annual subscriber at 50 conversations does NOT get nudge
    - **Property test (hypothesis):** For all C (0–30) and T (1–30) where C <= T: percentage = min(100, int((C/T)*100)) is in [0, 100] and monotonically non-decreasing as C increases
    - _Validates: Requirements 17.1, 17.2, 17.4, 26.1, 26.2, 26.3_

- [x] 7. Phase B: Backend — Polly Caching & Deepgram Batch
  - [x] 7.1 Add Polly caching for turn 0 in speech.py
    - File: `SamLambda/functions/conversationFunctions/wsDefault/speech.py`
    - For turn 0: check S3 for cached audio at `polly-cache/{question_id}/{voice_id}-{engine}.mp3`
    - Cache hit → return presigned URL without calling Polly
    - Cache miss → synthesize via Polly, store at cache key with KMS encryption, return presigned URL
    - Turn > 0 → synthesize normally without caching
    - _Requirements: 23.1, 23.2, 23.3, 23.4_

  - [x] 7.2 Write unit tests for Polly caching
    - File: `SamLambda/tests/test_polly_cache.py` using pytest + hypothesis + unittest.mock
    - Test: turn 0 cache hit → presigned URL returned, Polly NOT called
    - Test: turn 0 cache miss → Polly called, stored with KMS encryption
    - Test: turn 1+ → Polly always called, no cache check
    - Test: same (question_id, voice_id, engine) → same cache key
    - **Property test (hypothesis):** Cache key is deterministic for all (Q, V, E) combinations
    - _Validates: Requirements 23.1–23.4_

  - [ ]* 7.3 Replace AWS Transcribe with Deepgram batch in video transcription
    - DEFERRED: This is a cost optimization ($24/month savings) that requires changing two Lambda functions (startTranscription + processTranscript) and an EventBridge integration. Deferred to a follow-up spec to avoid risking video transcription during the pricing model rollout.
    - File: `SamLambda/functions/videoFunctions/startTranscription/app.py` (or processVideo/app.py)
    - Replace `start_transcription_job()` with Deepgram batch API call
    - Use Deepgram API key from SSM (`/soulreel/deepgram/api-key`)
    - Parse Deepgram response into same transcript format expected by summarization
    - _Requirements: 24.1, 24.2, 24.3, 24.4_

  - [ ]* 7.4 Write unit tests for Deepgram batch transcription
    - DEFERRED: Paired with 7.3
    - File: `SamLambda/tests/test_deepgram_batch.py` using pytest + unittest.mock
    - _Validates: Requirements 24.1–24.3_

- [x] 8. Phase B: Backend — Win-Back & Migration
  - [x] 8.1 Update winBack/app.py with Level 1 completer re-engagement
    - File: `SamLambda/functions/billingFunctions/winBack/app.py`
    - Add scan for Level 1 completers: `planId == free AND level1CompletedAt IS NOT NULL AND level1CompletedAt < (now - 7 days) AND (lastReengagementEmailAt IS NULL OR lastReengagementEmailAt < (now - 7 days))`
    - Send email via SES: "Your stories are preserved. Your family is waiting for the deeper ones."
    - Update `lastReengagementEmailAt` after sending; include unsubscribe link
    - Keep existing win-back logic for churned subscribers unchanged
    - _Requirements: 25.1–25.6, 28.2_

  - [x] 8.2 Write unit tests for win-back re-engagement
    - File: `SamLambda/tests/test_winback.py` using pytest + unittest.mock
    - Test: qualifying free user → email sent, timestamp updated
    - Test: recently emailed user → skipped
    - Test: recently completed user (< 7 days) → skipped
    - Test: premium user → skipped
    - Test: user who never completed Level 1 → skipped
    - _Validates: Requirements 25.1–25.6_

  - [x] 8.3 Create migration script for existing users
    - File: `SamLambda/scripts/migrate_existing_users.py`
    - For each existing user: add `level1CompletionPercent`, `level1CompletedAt`, `totalQuestionsCompleted` fields to their UserSubscriptionsDB record (calculated from conversation history)
    - Convert existing trial users (`status: trialing`, `trialExpiresAt` set) to free plan if trial expired
    - Use `attribute_not_exists` or conditional updates to be idempotent
    - _Requirements: 32.1–32.6_

- [x] 9. Phase B: Backend — Smoke tests and full test run
  - [x] 9.1 Update `SamLambda/tests/test_imports.py` with any new Lambda handlers
    - Verify all billing function handlers are in the HANDLERS list (they should already be from previous spec)
    - Add any new handlers if missing
    - Run `pytest tests/test_imports.py -v`
    - _Requirements: 13.3_

  - [x] 9.2 Run full backend test suite
    - Run `pytest SamLambda/tests/ -v` — all tests must pass
    - Run `sam validate --lint` from `SamLambda/` — must pass
    - Fix any failures before proceeding to frontend
    - _Requirements: all backend requirements_


- [x] 10. Phase C: Frontend — Update SubscriptionContext & billingService
  - [x] 10.1 Update SubscriptionContext.tsx
    - File: `FrontEndCode/src/contexts/SubscriptionContext.tsx`
    - Remove `trialExpiresAt`, `trialDaysRemaining` from state interface
    - Add `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted`, `couponExpiresAt`
    - Update `FREE_PLAN_LIMITS`: `maxBenefactors` from 2 to 1, remove `conversationsPerWeek`, add `maxLevel: 1`
    - Update `computeIsPremium()`: premium = `active || comped || (trialing && couponExpiresAt && future)`
    - Remove `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek` from state
    - _Requirements: 6.2, 6.3, 17.3_

  - [x] 10.2 Update billingService.ts
    - File: `FrontEndCode/src/services/billingService.ts`
    - Update `SubscriptionStatus` interface: add `level1CompletionPercent`, `level1CompletedAt`, `billingInterval`, `totalQuestionsCompleted`, `couponExpiresAt`; remove `conversationsThisWeek`, `weekResetDate`, `trialExpiresAt`
    - Update `PlanLimits`: add `maxLevel`, `foundingMemberPrice`, `foundingMemberCouponCode`; remove `conversationsPerWeek`
    - Add `getPublicPlans()` function calling `GET /billing/plans` (unauthenticated) — include founding member availability in response type
    - _Requirements: 6.3, 33.1, 33.2_

  - [x] 10.3 Write unit tests for SubscriptionContext premium logic
    - File: `FrontEndCode/src/__tests__/subscription-context.property.test.ts` using vitest + fast-check
    - Test: `status: active` → isPremium = true
    - Test: `status: comped` → isPremium = true
    - Test: `status: trialing` with future `couponExpiresAt` → isPremium = true
    - Test: `status: trialing` with past `couponExpiresAt` → isPremium = false
    - Test: `status: canceled` → isPremium = false
    - Test: `FREE_PLAN_LIMITS.maxBenefactors` = 1, `maxLevel` = 1
    - Test: `FREE_PLAN_LIMITS` does NOT contain `conversationsPerWeek`
    - **Property test (fast-check):** For all statuses and dates: `computeIsPremium()` returns true only for `active`, `comped`, or `trialing` with valid future coupon
    - _Validates: Requirements 6.2, 6.3, 10.5, 10.6_

- [x] 11. Phase C: Frontend — Update Pricing Page
  - [x] 11.1 Update PricingPage.tsx with $14.99/$149 pricing and founding member display
    - File: `FrontEndCode/src/pages/PricingPage.tsx`
    - NOTE: PricingPage already reads `monthlyPriceDisplay` from plan data with `$9.99` fallback, already has "Save 17%" badge and "Less than a cup of coffee a week" text, already has billing toggle and coupon input. Changes needed:
    - Update fallback values from `$9.99` to `$14.99` (the SSM update in task 1.1 will provide the correct values, but fallbacks should match)
    - Update FREE_FEATURES: change "Up to 2 benefactors" to "1 benefactor" and update description to "Complete Level 1 — Childhood, Family, School & Friends. Full AI quality. Share with 1 family member."
    - Add founding member pricing display: call `/billing/plans` to check `foundingMemberAvailable`, show "$99/year — Founding Member Rate" with slots remaining when available
    - Update Premium description to emphasize level progression: "All 10 levels — from Childhood to Messages to Loved Ones. Unlimited benefactors. Data export."
    - _Requirements: 16.1–16.11, 27.3_

  - [x] 11.2 Write unit tests for Pricing Page
    - File: `FrontEndCode/src/__tests__/pricing-page.property.test.ts` using vitest + fast-check
    - Test: annual toggle is default selected
    - Test: prices from API data, not hardcoded
    - Test: founding member shown when available, standard price when not
    - Test: current plan highlighted for free user
    - **Property test (fast-check):** Founding member display shown iff slotsRemaining > 0
    - _Validates: Requirements 16.1–16.11, 27.3_

- [x] 12. Phase C: Frontend — Dashboard Engagement Features
  - [x] 12.1 Create Level1CelebrationScreen component
    - File: `FrontEndCode/src/components/Level1CelebrationScreen.tsx` (new)
    - Modal triggered when `level1CompletedAt` transitions from null to a value (localStorage flag)
    - Display: congratulations, stories count, Level 1 categories, locked Levels 2–10 with names, Life Events question count teaser, Premium price, "Upgrade to Premium" CTA
    - Dismissible via close or "Maybe Later"
    - _Requirements: 18.1–18.7_

  - [x] 12.2 Create UpgradeBanner component with variants
    - File: `FrontEndCode/src/components/UpgradeBanner.tsx` (new)
    - HalfwayBanner: `level1CompletionPercent >= 50 && !level1CompletedAt`
    - PostCompletionBanner: `level1CompletedAt` set, persistent, not dismissible
    - BenefactorAwareBanner: `level1CompletedAt` set AND `benefactorCount > 0`
    - LifeEventsTeaser: "X personalized questions waiting"
    - No banners for premium users
    - _Requirements: 19.1–19.5_

  - [x] 12.3 Update Dashboard.tsx with locked content and banner integration
    - File: `FrontEndCode/src/pages/Dashboard.tsx`
    - Lock icons on Life Events, Values & Emotions cards for free users
    - Lock icons on Levels 2–10 for free users
    - Locked card tap → preview overlay with "Subscribe to unlock"
    - Integrate celebration screen and upgrade banners
    - _Requirements: 20.1–20.5, 18.1, 19.1–19.5_

  - [x] 12.4 Write unit tests for dashboard upgrade banner logic
    - File: `FrontEndCode/src/__tests__/upgrade-banners.property.test.ts` using vitest + fast-check
    - Test: free user at 49% → no halfway banner
    - Test: free user at 50% → halfway banner shown
    - Test: free user at 100% complete → post-completion banner, no halfway
    - Test: premium user → no banners
    - Test: free user with benefactor after completion → benefactor-aware banner
    - Test: celebration screen shown only once (localStorage)
    - **Property test (fast-check):** For all percent (0–100) and isPremium: banners shown iff !isPremium, halfway iff percent >= 50 && !completed
    - _Validates: Requirements 18.1, 19.1–19.5, 20.1–20.5_

- [x] 13. Phase C: Frontend — Home Page & Plan Settings
  - [x] 13.1 Update Home.tsx with new pricing section
    - File: `FrontEndCode/src/pages/Home.tsx`
    - Update pricing from `/billing/plans` endpoint
    - Annual price as primary, monthly equivalent secondary
    - CTA: "Start Free"
    - Footer: "Pricing" link
    - _Requirements: 30.1–30.5_

  - [x] 13.2 Create PlanSettingsSection component
    - File: `FrontEndCode/src/components/PlanSettingsSection.tsx` (new)
    - Current plan name + status
    - Free: "Upgrade to Premium" button, Level 1 progress bar
    - Premium: "Manage Subscription" button → Stripe Portal, billing interval
    - _Requirements: 31.1–31.5_

- [x] 14. Phase C: Frontend — Lint, type check, and test run
  - [x] 14.1 Run frontend checks
    - `npm run lint` in `FrontEndCode/` — zero errors
    - `npx tsc --noEmit` — zero type errors
    - `npx vitest --run` — all tests pass
    - _Requirements: all frontend requirements_

- [x] 15. Phase D: End-to-End Verification
  - [ ]* 15.1 End-to-end test: free user content gating flow
    - Free user signs up → free plan → Level 1 allowed → Level 2 blocked → upgrade prompt
    - Complete Level 1 → celebration screen → locked levels on dashboard
    - _Requirements: 2.1, 10.1–10.6, 17.1–17.4, 18.1–18.7_

  - [ ]* 15.2 End-to-end test: checkout and subscription flow
    - Free user → pricing page → checkout → webhook → premium → Level 2+ accessible
    - Premium user → cancel → webhook → free → Level 2 blocked
    - _Requirements: 4.1–4.8, 5.1–5.11, 10.1–10.6_

  - [ ]* 15.3 End-to-end test: coupon flows
    - FOUNDING100 → checkout at $99 → premium → counter incremented
    - forever_free coupon → instant premium, no Stripe
    - time_limited coupon → premium for N days → expires to free
    - _Requirements: 8.1–8.10, 9.1–9.4, 27.1–27.3_

## Notes

- Tasks marked with `*` are optional end-to-end tests requiring a deployed environment — all unit tests are MANDATORY
- The billing infrastructure (DynamoDB table, Stripe layer, Lambda functions, plan_check.py) already exists from the previous `stripe-subscription-tiers` spec — this plan UPDATES it to the new pricing model
- Key changes from old to new model: 14-day trial → free Level 1, $9.99/$79 → $14.99/$149, maxBenefactors 2 → 1 for free, `_L1` suffix → `maxLevel` field (keeping `allowedQuestionCategories` key name for backward compat), preview questions removed, weekly conversation caps removed
- Stripe Price IDs: old IDs are `price_1TL03V6hMyNf0PnbOaSd399o` (monthly) and `price_1TL06w6hMyNf0PnbCgehYyZB` (annual) — new IDs must be created in Stripe Dashboard before task 5.1
- SSM plan definitions use `monthlyPriceDisplay` (string like "$14.99") not `monthlyPrice` (number) — the PricingPage reads these display strings directly
- Backend tests use pytest + hypothesis + unittest.mock — matching `SamLambda/tests/property/` patterns
- Frontend tests use vitest + fast-check — matching `FrontEndCode/src/__tests__/*.property.test.ts` patterns
- All Lambda changes must include CORS headers and `import os` per workspace rules
- All IAM policy changes must be deployed alongside code changes per workspace rules
- Existing trial users phase out naturally — `is_premium_active()` keeps backward compat for `trialExpiresAt`
