# Implementation Plan: Pricing Conversion Optimization

## Overview

Implement 10 coordinated conversion optimization changes across the SoulReel stack. The implementation follows the phased order from the design: quick frontend wins first, then progressively deeper backend+frontend changes. Each phase builds on the previous one, and all code is wired together by the final phase.

Frontend: TypeScript/React (Vitest + fast-check for tests)
Backend: Python (pytest + Hypothesis for tests)

## Tasks

- [x] 1. Phase 1 — Quick frontend wins (Home CTA, annual default, trust relocation, social proof)
  - [x] 1.1 Clarify dual CTA on Home page
    - In `FrontEndCode/src/pages/Home.tsx`, add subtitle text below each CTA button: "Start Free" → "Preserve your own stories and memories"; "Start Their Legacy" → "Set it up for a parent, grandparent, or loved one"
    - Style "Start Free" as primary (filled bg-legacy-purple) and "Start Their Legacy" as secondary (outline variant)
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 1.2 Default billing toggle to annual on PricingPage
    - In `FrontEndCode/src/pages/PricingPage.tsx`, change `useState<"monthly" | "annual">("monthly")` to `useState<"monthly" | "annual">("annual")`
    - Add a "Best Value" badge adjacent to the "Annual" toggle button
    - Display savings percentage in a prominent callout near the Premium price when annual is selected
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 1.3 Relocate trust messaging and add social proof on PricingPage
    - Move trust messaging from the bottom gray `<section>` to directly below the plan comparison grid, with a shield icon
    - Remove the separate bottom gray trust section
    - Add "Recommended" badge on Premium card for non-subscribed users
    - Add anchoring text "Less than a cup of coffee a week" below Premium price
    - Add social proof section below trust messaging with testimonial placeholder and family counter placeholder
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 10.1, 10.2, 10.3_

  - [x] 1.4 Update Home page pricing section to lead with annual price
    - In `FrontEndCode/src/pages/Home.tsx`, restructure the pricing section so the annual equivalent price is the primary displayed price and monthly is secondary
    - Lead with value proposition text before displaying the price
    - _Requirements: 3.4, 3.5, 6.4_

- [x] 2. Checkpoint — Verify Phase 1 frontend changes
  - Run `npm run lint` and `npm run build` in `FrontEndCode/` to verify no regressions
  - Run `npx vitest --run` in `FrontEndCode/` to verify existing tests still pass
  - Visually verify: PricingPage defaults to annual, trust messaging is below plan cards, "Recommended" badge shows, Home page CTAs have subtitles

- [x] 3. Phase 2 — Upgrade dialog enhancements and trial extension
  - [x] 3.1 Enhance UpgradePromptDialog with prices and in-dialog checkout
    - In `FrontEndCode/src/components/UpgradePromptDialog.tsx`, add `import { useSubscription } from '@/contexts/SubscriptionContext'` and `import { createCheckoutSession } from '@/services/billingService'` — these are self-contained imports that work in all render contexts (Dashboard, ConversationInterface, ManageBenefactors) since SubscriptionProvider wraps the entire app
    - Read `planLimits.monthlyPriceDisplay` and `planLimits.annualMonthlyEquivalentDisplay` from `useSubscription()` and display both prices in the dialog body. Fall back to `"$9.99"` / `"$6.58"` if missing.
    - Add "Subscribe Now" button that calls `createCheckoutSession` with `import.meta.env.VITE_STRIPE_ANNUAL_PRICE_ID || "price_annual_placeholder"` (same env var pattern used in PricingPage.tsx)
    - Rename dismiss button from "Maybe Later" to "Remind Me Later"
    - On "Remind Me Later" click, store `sr_upgrade_deferred` flag in localStorage (wrap in try/catch for private browsing)
    - Keep existing "Upgrade to Premium" button for navigating to /pricing
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 3.2 Write property test for upgrade dialog price display (Property 7)
    - **Property 7: Upgrade Dialog Displays Both Prices**
    - Generate random price strings using fast-check, render UpgradePromptDialog with those prices in context
    - Verify both price strings appear in rendered output
    - **Validates: Requirements 7.1**

  - [x] 3.3 Extend trial duration to 14 days in postConfirmation Lambda
    - In `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`, change `timedelta(days=7)` to `timedelta(days=14)`
    - _Requirements: 2.1_

  - [x] 3.4 Update trial nudge threshold in Header and Dashboard
    - In `FrontEndCode/src/components/Header.tsx`, change `trialDaysRemaining <= 3` to `trialDaysRemaining <= 5`
    - In `FrontEndCode/src/pages/Dashboard.tsx`, change the trial nudge banner threshold from `<= 3` to `<= 5`
    - _Requirements: 2.2, 2.3_

  - [ ]* 3.5 Write property test for trial duration (Property 3)
    - **Property 3: Trial Duration Is 14 Days**
    - Generate random UTC timestamps using Hypothesis, compute trial expiration with `timedelta(days=14)`, verify delta is exactly 14 days
    - **Validates: Requirements 2.1**

  - [ ]* 3.6 Write property test for trial nudge threshold (Property 4)
    - **Property 4: Trial Nudge Threshold**
    - Generate random timestamps for `trialExpiresAt` and `now` using fast-check
    - Compute `trialDaysRemaining` via `computeTrialDaysRemaining`, verify banner visibility matches `0 < days <= 5`
    - **Validates: Requirements 2.2, 2.3**

- [x] 4. Checkpoint — Verify Phase 2 changes
  - Run `npx vitest --run` in `FrontEndCode/` to verify frontend tests
  - Run `pytest` in `SamLambda/` to verify backend tests (including postConfirmation trial duration)
  - Visually verify: UpgradePromptDialog shows prices and "Subscribe Now" button, trial nudge appears at 5 days remaining

- [x] 5. Phase 3 — Home page redesign
  - [x] 5.1 Redesign Home page "How It Works" and add sample questions
    - In `FrontEndCode/src/pages/Home.tsx`, replace generic "How It Works" steps with product-specific steps: "Choose a question from your life story", "Have an AI-guided conversation", "Share your story with the people who matter"
    - Add a sample question section between "How It Works" and pricing, showing one example question per content path
    - Add a testimonial placeholder section between sample questions and pricing
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. Phase 4 — Preview questions (backend + frontend)
  - [x] 6.1 Add previewQuestions to SSM free plan definition and update plan_check.py
    - Update the SSM free plan definition JSON to include `previewQuestions` with real question IDs from `allQuestionDB` (one from Life Events, one from Values & Emotions). Query the database to find suitable IDs — do not use placeholder IDs.
    - In `SamLambda/functions/shared/python/plan_check.py`, add a `_QUESTION_STATUS_TABLE` variable referencing `userQuestionStatusDB` via `os.environ.get('TABLE_QUESTION_STATUS', 'userQuestionStatusDB')`
    - Modify `check_question_category_access` to check `previewQuestions` list before denying access
    - Add `_has_completed_preview(user_id, question_id)` helper that does a `get_item` on `userQuestionStatusDB` with `Key={'userId': user_id, 'questionId': question_id}` — item exists means completed
    - Return `{'allowed': True, 'isPreview': True}` when question is in preview list and not yet completed
    - No IAM changes needed — wsDefault already has `dynamodb:GetItem` on `userQuestionStatusDB`, and plan_check.py runs inside wsDefault's execution context
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 6.2 Write property test for free user preview access gate (Property 1)
    - **Property 1: Free User Preview Access Gate**
    - Generate random question IDs and preview question lists using Hypothesis
    - Mock plan definition and userQuestionStatusDB
    - Verify `check_question_category_access` returns `isPreview: true` iff question is in preview list and not completed
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 6.3 Write property test for premium user unrestricted access (Property 2)
    - **Property 2: Premium User Unrestricted Access**
    - Generate random question IDs using Hypothesis, mock premium subscription record
    - Verify access is always allowed without `isPreview` flag
    - **Validates: Requirements 1.4**

  - [x] 6.4 Add previewQuestions to billing status response
    - In `SamLambda/functions/billingFunctions/billing/app.py`, add `previewQuestions` from the plan definition to the `handle_status` response
    - _Requirements: 1.8_

  - [x] 6.5 Expose previewQuestions in frontend types and SubscriptionContext
    - In `FrontEndCode/src/services/billingService.ts`, add `previewQuestions?: string[]` to `PlanLimits` and `SubscriptionStatus` interfaces
    - In `FrontEndCode/src/contexts/SubscriptionContext.tsx`, add `previewQuestions` to `SubscriptionState` interface and wire it from the status response
    - _Requirements: 1.9_

  - [x] 6.6 Add preview question labels and navigation on Dashboard
    - In `FrontEndCode/src/pages/Dashboard.tsx`, for locked ContentPathCards, check if `previewQuestions` (from SubscriptionContext) contains a question for that category by parsing the question ID prefix (`life_events-*` → Life Events card, `values_emotions-*` or `psych_*` → Values & Emotions card)
    - To determine if a preview is already completed, check the existing progress data: `lifeEventsCompleted > 0` means the Life Events preview is done, `psychTests.filter(t => t.completedAt).length > 0` means Values & Emotions preview is done. Alternatively, add a `completedPreviewQuestions` field to the billing status response for explicit tracking.
    - If preview available and not yet completed, pass `badge="Try 1 free question"` to the ContentPathCard and set `onLockedClick` to navigate to the category page (`/life-events` or `/personal-insights`) where the backend will allow the preview question
    - After completion, revert to standard locked state with upgrade prompt (the progress data will show completion, removing the badge)
    - _Requirements: 1.5, 1.6, 1.7_

- [x] 7. Checkpoint — Verify preview questions end-to-end
  - Run `pytest` in `SamLambda/` to verify plan_check.py preview logic and billing status response
  - Run `npx vitest --run` in `FrontEndCode/` to verify frontend tests
  - End-to-end: verify a free user sees "Try 1 free question" on locked Dashboard cards, can start the preview conversation, and sees the card revert to locked after completion

- [x] 8. Phase 5 — Usage indicator (backend + frontend)
  - [x] 8.1 Add conversationsPerWeek to SSM plan definitions
    - Update SSM free plan definition to include `conversationsPerWeek: 3`. **Important**: This is the same SSM parameter modified in task 6.1 (`/soulreel/plans/free`). If task 6.1 has already been applied, this update must preserve the `previewQuestions` field added there. Read the current value first, add the new field, then write back.
    - Update SSM premium plan definition to include `conversationsPerWeek: -1`
    - _Requirements: 8.1, 8.2_

  - [x] 8.2 Implement weekly conversation counter in wsDefault
    - In `SamLambda/functions/conversationFunctions/wsDefault/app.py`, add `_increment_weekly_conversation_count(user_id)` function using conditional DynamoDB updates to avoid race conditions (see design doc for implementation)
    - Call it in `handle_start_conversation` after the plan check passes, wrapped in try/except (never block conversation on counter failure)
    - Implement week reset logic: use `ConditionExpression` to atomically check `weekResetDate` and either increment or reset
    - **IAM CHANGE REQUIRED**: In `SamLambda/template.yml`, add `dynamodb:UpdateItem` to the WebSocketDefaultFunction policy for `UserSubscriptionsTable` (currently only has `dynamodb:GetItem`). This must be deployed before the counter code.
    - _Requirements: 8.3, 8.4, 8.5_

  - [ ]* 8.3 Write property test for weekly conversation counter (Property 6)
    - **Property 6: Weekly Conversation Counter**
    - Generate random sequences of (timestamp, user_id) pairs spanning multiple ISO weeks using Hypothesis
    - Simulate the increment logic, verify `conversationsThisWeek` and `weekResetDate` are correct after each operation
    - **Validates: Requirements 8.3, 8.4, 8.5**

  - [x] 8.4 Add conversation usage fields to billing status response
    - In `SamLambda/functions/billingFunctions/billing/app.py`, add `conversationsThisWeek`, `weekResetDate`, and `conversationsPerWeek` to the `handle_status` response
    - _Requirements: 8.6_

  - [ ]* 8.5 Write property test for billing status response completeness (Property 5)
    - **Property 5: Billing Status Response Completeness**
    - Generate random subscription records with varying fields present/absent using Hypothesis
    - Verify status response always includes `previewQuestions`, `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek`
    - **Validates: Requirements 1.8, 8.6**

  - [x] 8.6 Expose usage fields in frontend types and SubscriptionContext
    - In `FrontEndCode/src/services/billingService.ts`, add `conversationsThisWeek`, `weekResetDate`, and `conversationsPerWeek` to `SubscriptionStatus` interface and `conversationsPerWeek` to `PlanLimits`
    - In `FrontEndCode/src/contexts/SubscriptionContext.tsx`, add `conversationsThisWeek`, `weekResetDate`, and `conversationsPerWeek` to `SubscriptionState` and wire from status response
    - _Requirements: 8.7_

  - [x] 8.7 Add usage indicator to Dashboard
    - In `FrontEndCode/src/pages/Dashboard.tsx`, display "{used} of {limit} conversations used this week" for free users
    - Hide usage indicator for premium users
    - _Requirements: 8.8, 8.9_

  - [ ]* 8.8 Write property test for usage indicator visibility (Property 8)
    - **Property 8: Usage Indicator Visibility**
    - Generate random subscription states (varying isPremium, conversationsThisWeek, conversationsPerWeek) using fast-check
    - Verify indicator is visible iff `!isPremium` and text matches `"{conversationsThisWeek} of {conversationsPerWeek} conversations used this week"`
    - **Validates: Requirements 8.8, 8.9**

- [x] 9. Checkpoint — Verify usage indicator end-to-end
  - Run `pytest` in `SamLambda/` to verify conversation counter and billing status response
  - Run `npx vitest --run` in `FrontEndCode/` to verify frontend tests
  - Verify IAM change deployed: `sam build && sam deploy --no-confirm-changeset` from `SamLambda/` (the `dynamodb:UpdateItem` permission for WebSocketDefaultFunction must be live before testing)
  - End-to-end: verify a free user sees "X of 3 conversations used this week" on Dashboard, counter increments after starting a conversation

- [x] 10. Phase 6 — Re-engagement coupon (frontend + SSM)
  - [x] 10.1 Create COMEBACK20 coupon in SSM and Stripe
    - Create SSM parameter at `/soulreel/coupons/COMEBACK20` with the coupon JSON: `{ "code": "COMEBACK20", "type": "percentage", "percentOff": 20, "durationMonths": 3, "stripeCouponId": "COMEBACK20", "maxRedemptions": 0, "currentRedemptions": 0, "expiresAt": null, "createdBy": "system-config" }`
    - **Also create the corresponding Stripe Coupon** in the Stripe Dashboard (or via Stripe API): ID `COMEBACK20`, 20% off, duration `repeating` with `duration_in_months: 3`. Without this, the coupon code will validate in SSM but fail at Stripe checkout.
    - _Requirements: 9.3_

  - [x] 10.2 Add re-engagement banner to PricingPage
    - In `FrontEndCode/src/pages/PricingPage.tsx`, on mount check `localStorage.getItem('sr_pricing_first_visit')`
    - If null, set it to current timestamp (first visit — no banner)
    - If exists and user is free/non-subscribed, show COMEBACK20 banner: "Welcome back! Use code COMEBACK20 for 20% off Premium"
    - Do not show banner for subscribed users or first-time visitors
    - Wrap all localStorage calls in try/catch for private browsing compatibility
    - _Requirements: 9.1, 9.2, 9.4, 9.5_

  - [ ]* 10.3 Write property test for re-engagement banner visibility (Property 9)
    - **Property 9: Re-engagement Banner Visibility**
    - Generate random combinations of (isPremium, hasLocalStorageTimestamp) using fast-check
    - Verify COMEBACK20 banner is visible iff `!isPremium && hasLocalStorageTimestamp`
    - **Validates: Requirements 9.2, 9.4, 9.5**

- [-] 11. Final checkpoint — Ensure all tests pass
  - Run full test suites: `npx vitest --run` in `FrontEndCode/` and `pytest` in `SamLambda/`
  - Run `npm run lint && npm run build` in `FrontEndCode/` to verify production build
  - Run `sam build && sam validate --lint` in `SamLambda/` to verify backend build
  - Verify all SSM parameters are created (free plan with previewQuestions + conversationsPerWeek, premium plan with conversationsPerWeek, COMEBACK20 coupon)
  - Verify Stripe Coupon COMEBACK20 exists in Stripe Dashboard

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- No new Lambda functions or DynamoDB tables are created
- **One IAM change is required**: `dynamodb:UpdateItem` must be added to WebSocketDefaultFunction's policy for `UserSubscriptionsTable` (task 8.2). This must be deployed before the conversation counter code goes live.
- SSM plan definition updates (tasks 6.1, 8.1, 10.1) are configuration changes applied via AWS console or CLI, not code deploys
- Preview question IDs in SSM must be real IDs from `allQuestionDB` — query the database during implementation
- Property tests use fast-check (frontend) and Hypothesis (backend), matching existing test infrastructure
- Each phase builds on the previous — no orphaned code between phases
