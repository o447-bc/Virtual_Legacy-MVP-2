# Implementation Plan: Stripe Subscription Tiers

## Overview

Implements a two-tier Stripe subscription model (Free / Premium at $9.99/month or $79/year) for SoulReel. The plan follows the design's component order: infrastructure first, then backend billing Lambdas, shared plan_check utility, modifications to existing Lambdas, scheduled functions, and finally frontend components. Each task builds incrementally so the system is testable at each checkpoint.

## Tasks

- [x] 1. Infrastructure: DynamoDB table, Stripe layer, SSM parameters, and template.yml globals
  - [x] 1.1 Add UserSubscriptionsDB table to `SamLambda/template.yml`
    - Define DynamoDB table with `userId` partition key (String)
    - PAY_PER_REQUEST billing mode
    - KMS encryption with existing `DataEncryptionKey`
    - Point-in-Time Recovery enabled
    - GSI `stripeCustomerId-index` with `stripeCustomerId` as partition key, Projection ALL
    - Add `TABLE_SUBSCRIPTIONS: 'UserSubscriptionsDB'` to Globals.Function.Environment.Variables
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 1.2 Add StripeDependencyLayer to `SamLambda/template.yml`
    - Create `SamLambda/layers/stripe/requirements.txt` with `stripe` package
    - Define `AWS::Serverless::LayerVersion` resource with `BuildMethod: python3.12` and `CompatibleArchitectures: [arm64]`
    - _Requirements: 13.1, 13.2_

  - [x] 1.3 Update SharedUtilsLayer architecture compatibility
    - Add `x86_64` to SharedUtilsLayer `CompatibleArchitectures` so WebSocketDefaultFunction (x86_64) can use plan_check
    - _Requirements: 14.1, 14.2 (prerequisite)_

  - [x] 1.4 Document SSM Parameter Store setup for Stripe secrets and plan definitions
    - Create a setup script or README at `SamLambda/scripts/setup-ssm-params.sh` that puts:
      - `/soulreel/stripe/secret-key` (SecureString)
      - `/soulreel/stripe/webhook-secret` (SecureString)
      - `/soulreel/stripe/publishable-key` (String)
      - `/soulreel/plans/free` (String, JSON plan definition)
      - `/soulreel/plans/premium` (String, JSON plan definition with pricing display fields)
    - _Requirements: 2.1, 2.2, 2.3, 12.1, 12.2, 12.3_

- [x] 2. Checkpoint — Validate infrastructure
  - Ensure `sam validate --lint` passes with the new table, layer, and globals. Ask the user if questions arise.

- [-] 3. Backend: plan_check shared utility module
  - [x] 3.1 Create `SamLambda/functions/shared/python/plan_check.py`
    - Implement `get_user_plan(user_id)` — reads UserSubscriptionsDB, returns subscription record or free-plan default
    - Implement `is_trial_active(subscription_record)` — checks status=trialing and trialExpiresAt in future
    - Implement `is_premium_active(subscription_record)` — checks status in [active, comped] or active trial
    - Implement `check_question_category_access(user_id, question_id)` — parses question ID, checks plan's allowedQuestionCategories
    - Implement `check_benefactor_limit(user_id)` — reads benefactorCount and plan's maxBenefactors
    - Implement `_parse_question_id(question_id)` — extracts category and level from question ID pattern
    - Implement `_get_plan_definition(plan_id)` / `_load_all_plans()` with module-level SSM caching
    - Use `ssm.get_parameters()` (plural) for batch loading both plan definitions on cold start
    - Fail-open on DynamoDB/SSM errors (log and allow access)
    - _Requirements: 2.4, 3.3, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4_

  - [ ]* 3.2 Write property tests for plan_check: question ID parsing (Property 26)
    - **Property 26: Question ID parsing correctness**
    - Create `SamLambda/tests/test_plan_check_properties.py`
    - Generate question ID strings following `{category_parts}-L{level}-Q{number}` pattern
    - Verify `_parse_question_id()` extracts correct category and integer level
    - Verify default level is 1 for IDs without a level segment
    - **Validates: Requirements 9.2, 9.3**

  - [ ] 3.3 Write property tests for plan_check: access enforcement (Properties 18, 19, 20)
    - **Property 18: Free-plan users denied restricted questions**
    - **Property 19: Premium users have unrestricted access**
    - **Property 20: Benefactor limit enforcement**
    - Generate free-plan users with restricted question IDs, verify denied
    - Generate premium users with any question IDs, verify allowed
    - Generate users with various benefactorCount and maxBenefactors, verify enforcement
    - **Validates: Requirements 9.2, 9.3, 9.4, 10.2, 10.3**

  - [ ] 3.4 Write property tests for plan_check: trial and missing record handling (Properties 3, 13)
    - **Property 3: Active trial grants premium access**
    - **Property 13: Missing subscription record defaults to free plan**
    - Generate records with status=trialing and future trialExpiresAt, verify is_premium_active returns true
    - Generate random user IDs with no records, verify free plan returned
    - **Validates: Requirements 3.2, 3.3, 6.2, 9.5, 10.4**

- [-] 4. Backend: BillingFunction Lambda
  - [x] 4.1 Create BillingFunction directory and handler at `SamLambda/functions/billingFunctions/billing/app.py`
    - Implement request routing by path + httpMethod
    - Implement `handle_create_checkout()` — create Stripe Customer if needed, create Checkout Session with userId metadata, return sessionUrl
    - Implement `handle_status()` — read UserSubscriptionsDB, return plan info with limits from SSM, default to free plan if no record
    - Implement `handle_portal()` — create Stripe Billing Portal Session, return portalUrl
    - Implement `handle_apply_coupon()` — validate coupon from SSM, handle forever_free/time_limited/percentage types, increment redemption counter
    - Implement `handle_get_plans()` — read plan definitions from SSM, return public plan data (no auth required)
    - Include CORS headers on all responses using `cors_headers()` from SharedUtilsLayer
    - Include `import os` at top, use `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')` for CORS
    - Cache SSM parameters in memory within Lambda invocation
    - _Requirements: 4.1–4.8, 6.1–6.4, 7.1–7.4, 8.1–8.10, 12.4, 12.5, 12.7_

  - [x] 4.2 Add BillingFunction resource to `SamLambda/template.yml`
    - Define Lambda with `python3.12`, `arm64`, Layers: SharedUtilsLayer + StripeDependencyLayer
    - Add API events for all 5 endpoints: create-checkout-session (POST, CognitoAuthorizer), status (GET, CognitoAuthorizer), portal (GET, CognitoAuthorizer), apply-coupon (POST, CognitoAuthorizer), plans (GET, Auth: NONE)
    - IAM policies: DynamoDB CRUD on UserSubscriptionsDB + GSI, SSM read on `/soulreel/stripe/*`, `/soulreel/plans/*`, `/soulreel/coupons/*`, SSM write on `/soulreel/coupons/*`, KMS Decrypt/DescribeKey on DataEncryptionKey
    - Environment variables: SUBSCRIPTIONS_TABLE, FRONTEND_URL
    - _Requirements: 4.1, 6.1, 7.1, 8.1, 12.4, 12.5, 13.3_

  - [ ] 4.3 Write property tests for BillingFunction (Properties 1, 7, 8, 14, 15, 16, 17)
    - **Property 1: Subscription record round-trip**
    - **Property 7: Checkout session includes userId and returns sessionUrl**
    - **Property 8: All billing responses include CORS headers**
    - **Property 14: Status returns plan limits matching plan definition**
    - **Property 15: Coupon redemption creates correct subscription record**
    - **Property 16: Percentage coupon returns stripeCouponId without DB modification**
    - **Property 17: Coupon redemption increments counter**
    - Add tests to `SamLambda/tests/test_plan_check_properties.py` or new `SamLambda/tests/test_billing_properties.py`
    - **Validates: Requirements 1.6, 4.2, 4.4, 4.6, 4.8, 6.3, 8.2–8.5**

- [-] 5. Backend: StripeWebhookFunction Lambda
  - [x] 5.1 Create StripeWebhookFunction at `SamLambda/functions/billingFunctions/stripeWebhook/app.py`
    - Implement `handle_webhook()` — verify Stripe signature, route by event type
    - Handle `checkout.session.completed` — use userId from metadata (PK lookup, not GSI), set planId=premium, status=active, clear trialExpiresAt
    - Handle `customer.subscription.updated` — GSI lookup by stripeCustomerId, update status/planId/currentPeriodEnd
    - Handle `customer.subscription.deleted` — GSI lookup, set planId=free, status=canceled
    - Handle `invoice.payment_failed` — GSI lookup, set status=past_due
    - Preserve benefactorCount on all updates (use UpdateExpression, not PutItem)
    - Define PRICE_PLAN_MAP with 2 entries mapping to 'premium'
    - Include CORS headers on all responses, `import os` at top
    - Return 200 with `{"received": true}` for all processed events
    - Return 400 for invalid signature
    - Log event.id, event.type, and resolved userId for debugging
    - _Requirements: 5.1–5.12_

  - [x] 5.2 Add StripeWebhookFunction resource to `SamLambda/template.yml`
    - Define Lambda with `python3.12`, `arm64`, Layers: SharedUtilsLayer + StripeDependencyLayer
    - API event: `/billing/webhook` POST with `Auth: NONE`
    - IAM policies: DynamoDB GetItem/PutItem/UpdateItem/Query on UserSubscriptionsDB + GSI, SSM read on `/soulreel/stripe/*` only, KMS Decrypt/DescribeKey on DataEncryptionKey
    - _Requirements: 5.1, 5.2, 12.6, 13.3_

  - [ ] 5.3 Write property tests for StripeWebhookFunction (Properties 9, 10, 11, 12)
    - **Property 9: Webhook signature verification gates processing**
    - **Property 10: checkout.session.completed updates subscription correctly**
    - **Property 11: Subscription lifecycle webhook transitions**
    - **Property 12: Webhook updates preserve usage counters**
    - **Validates: Requirements 5.2, 5.4, 5.6, 5.7, 5.8, 5.9**

- [x] 6. Checkpoint — Validate billing backend
  - Ensure `sam validate --lint` passes. Ensure all property tests pass. Ask the user if questions arise.

- [-] 7. Backend: Modify existing Lambdas for plan enforcement
  - [x] 7.1 Modify PostConfirmationFunction to create trial subscription record
    - Add trial creation logic after existing persona attribute logic in `SamLambda/functions/cognitoTriggers/postConfirmation/app.py`
    - Create UserSubscriptionsDB record: planId=premium, status=trialing, trialExpiresAt=now+7d, benefactorCount=0
    - Wrap in try/except — don't fail signup if trial creation fails (log WARNING)
    - Add `TABLE_SUBSCRIPTIONS` environment variable to PostConfirmationFunction in template.yml
    - Add IAM: `dynamodb:PutItem` on UserSubscriptionsTable, `kms:Encrypt` + `kms:GenerateDataKey` on DataEncryptionKey
    - _Requirements: 3.1, 3.2_

  - [ ] 7.2 Write property test for trial creation (Property 2)
    - **Property 2: Trial record creation correctness**
    - Generate random user IDs and timestamps, verify trial record has planId=premium, status=trialing, benefactorCount=0, trialExpiresAt exactly 7 days after signup
    - **Validates: Requirements 3.1**

  - [x] 7.3 Modify WebSocketDefaultFunction for plan_check access enforcement
    - Add plan_check import and `check_question_category_access()` call at start of `handle_start_conversation()` in `SamLambda/functions/conversationFunctions/wsDefault/app.py`
    - Send `limit_reached` WebSocket message with limitType and upgradeUrl if access denied
    - Fail-open on plan_check errors (log and allow conversation)
    - Add SharedUtilsLayer to WebSocketDefaultFunction Layers in template.yml
    - Add IAM: `dynamodb:GetItem` on UserSubscriptionsTable
    - Add IAM: `ssm:GetParameter` and `ssm:GetParameters` on `/soulreel/plans/*`
    - Add `TABLE_SUBSCRIPTIONS` environment variable
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 14.1, 14.2_

  - [x] 7.4 Modify CreateAssignmentFunction for benefactor limit check
    - Add plan_check import and `check_benefactor_limit()` call after extracting `legacy_maker_id` in `SamLambda/functions/assignmentFunctions/createAssignment/app.py`
    - Return 403 with benefactor_limit error if limit exceeded
    - Fail-open on plan_check errors (log and allow assignment)
    - Add benefactorCount increment after successful assignment creation (last step, after email)
    - Add SharedUtilsLayer to CreateAssignmentFunction Layers in template.yml (if not already present)
    - Add IAM: `dynamodb:GetItem` + `dynamodb:UpdateItem` on UserSubscriptionsTable
    - Add IAM: `ssm:GetParameter` and `ssm:GetParameters` on `/soulreel/plans/*`
    - Add `TABLE_SUBSCRIPTIONS` environment variable
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 14.3, 14.4_

- [-] 8. Backend: Scheduled functions (CouponExpiration, WinBack)
  - [x] 8.1 Create CouponExpirationFunction at `SamLambda/functions/billingFunctions/couponExpiration/app.py`
    - Scan UserSubscriptionsDB for status=trialing with trialExpiresAt < now
    - Scan for couponType=time_limited with couponExpiresAt < now
    - UpdateItem each match: planId=free, status=expired
    - Add to template.yml: EventBridge Schedule rule (daily), 60s timeout, IAM for DynamoDB Scan + UpdateItem on UserSubscriptionsTable
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ] 8.2 Write property test for expiration logic (Property 4)
    - **Property 4: Expiration service transitions expired records to free**
    - Generate mixed sets of expired/active records, run expiration logic, verify correct transitions and non-expired records unchanged
    - **Validates: Requirements 3.4, 11.2, 11.3, 11.4, 11.5**

  - [x] 8.3 Create WinBackFunction at `SamLambda/functions/billingFunctions/winBack/app.py`
    - Scan UserSubscriptionsDB for status=expired with trialExpiresAt between 3-4 days ago
    - Auto-generate single-use percentage coupon in SSM with 48h expiry
    - Create corresponding Stripe Coupon via API
    - Send SES email with coupon code and link to /pricing
    - Add to template.yml: EventBridge Schedule rule (daily), IAM for DynamoDB Scan, SSM read/write, SES SendEmail, Stripe layer
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6_

  - [ ] 8.4 Write property tests for WinBack (Properties 24, 25)
    - **Property 24: Win-back targets correct user cohort**
    - **Property 25: Win-back coupon generation**
    - Generate subscription records with various expiry dates, verify only 3-4 day window targeted
    - Verify auto-generated coupon has type=percentage, maxRedemptions=1, expiresAt within 48h
    - **Validates: Requirements 22.1, 22.5, 22.6**

- [x] 9. Checkpoint — Full backend validation
  - Ensure `sam validate --lint` passes. Ensure all backend property tests pass. Ask the user if questions arise.

- [-] 10. Frontend: SubscriptionContext and billingService
  - [x] 10.1 Create `FrontEndCode/src/services/billingService.ts`
    - Implement `getSubscriptionStatus()` — GET /billing/status with auth token
    - Implement `createCheckoutSession(priceId)` — POST /billing/create-checkout-session
    - Implement `getPortalUrl()` — GET /billing/portal
    - Implement `applyCoupon(code)` — POST /billing/apply-coupon
    - Implement `getPublicPlans()` — GET /billing/plans (no auth)
    - Add billing endpoint paths to `FrontEndCode/src/config/api.ts`
    - Follow existing service patterns (see assignmentService.ts)
    - _Requirements: 4.6, 6.1, 7.2, 8.1, 16.2_

  - [x] 10.2 Create `FrontEndCode/src/contexts/SubscriptionContext.tsx`
    - Define SubscriptionState interface with planId, status, trialExpiresAt, trialDaysRemaining, planLimits, isPremium, isLoading, refetch
    - Use React Query with staleTime: 5 minutes, refetch on window focus
    - Compute isPremium from status (active, trialing with valid trial, comped)
    - Compute trialDaysRemaining from trialExpiresAt
    - Return static free-plan object for unauthenticated users (no API call)
    - Immediate refetch on `?checkout=success` URL param
    - Wrap in AuthProvider tree in App.tsx
    - _Requirements: 6.2, 6.3, 3.5_

  - [ ] 10.3 Write property test for trial days remaining computation (Property 5)
    - **Property 5: Trial days remaining computation**
    - Generate random trialExpiresAt and current times
    - Verify trialDaysRemaining = ceil((trialExpiresAt - now) / 86400) when positive, 0 when expired
    - Verify trial nudge displays iff 0 < trialDaysRemaining <= 3
    - Add to `FrontEndCode/src/__tests__/subscription.property.test.ts`
    - **Validates: Requirements 3.5**

- [-] 11. Frontend: PricingPage
  - [x] 11.1 Create `FrontEndCode/src/pages/PricingPage.tsx`
    - Public route (no ProtectedRoute wrapper)
    - Fetch plans from `/billing/plans` for unauthenticated, `/billing/status` for authenticated
    - BillingToggle component for monthly/annual switch
    - PlanComparisonGrid with Free and Premium PlanCards
    - PlanFeatureList showing category access, benefactor limits, features
    - All pricing text rendered from PlanLimits data (monthlyPriceDisplay, annualPriceDisplay, annualMonthlyEquivalentDisplay, annualSavingsPercent) — never hardcoded
    - CTA behavior by auth state: unauthenticated → "Start Free Trial" → /signup-create-legacy; free plan → "Subscribe" → createCheckoutSession; premium → "Manage Subscription" → getPortalUrl; trialing → "Subscribe Now"
    - Collapsed "Have a code?" link expanding to CouponInput + Apply button
    - Use shadcn/ui components, Tailwind, legacy-purple/legacy-navy tokens
    - Responsive for mobile and desktop
    - _Requirements: 16.1–16.11, 21.1, 21.3, 23.1–23.5_

  - [x] 11.2 Add `/pricing` route to `FrontEndCode/src/App.tsx`
    - Add PricingPage import and public Route
    - _Requirements: 16.1_

- [-] 12. Frontend: Dashboard and ContentPathCard changes
  - [x] 12.1 Create `FrontEndCode/src/components/UpgradePromptDialog.tsx`
    - Reusable shadcn Dialog for locked content previews and limit-reached prompts
    - Props: title, message, previewQuestion?, onUpgrade, onClose
    - Emotionally framed messaging
    - _Requirements: 20.1, 20.4, 20.6_

  - [x] 12.2 Modify `FrontEndCode/src/components/ContentPathCard.tsx`
    - Add `locked?: boolean` and `onLockedClick?: () => void` props
    - When locked: show Lock icon (lucide-react), "Premium" Badge, trigger onLockedClick instead of navigating
    - _Requirements: 18.2, 18.3_

  - [x] 12.3 Modify `FrontEndCode/src/pages/Dashboard.tsx`
    - Import and use `useSubscription()` from SubscriptionContext
    - Pass `locked` prop to Life Events and Values & Emotions ContentPathCards based on isPremium
    - Show UpgradePromptDialog on locked card click with emotionally framed preview
    - Show trial nudge banner when trialDaysRemaining <= 3 with link to /pricing
    - Show checkout success toast when URL has `?checkout=success` (poll /billing/status for up to 10s)
    - _Requirements: 3.5, 18.1, 18.2, 18.3, 18.4, 20.4, 20.5_

  - [ ] 12.4 Write property tests for dashboard card visibility (Property 22)
    - **Property 22: Dashboard content path card visibility by plan**
    - Generate random subscription states, verify correct locked/unlocked card rendering
    - Add to `FrontEndCode/src/__tests__/subscription.property.test.ts`
    - **Validates: Requirements 18.1, 18.2, 18.4**

- [-] 13. Frontend: Header, UserMenu, and Home page changes
  - [x] 13.1 Modify `FrontEndCode/src/components/UserMenu.tsx`
    - Add "Plan & Billing" menu item between "Manage Benefactors" and "Security & Privacy"
    - Show current plan name badge (Free/Premium)
    - Link to /pricing for free users, Stripe Portal for premium users
    - _Requirements: 19.1, 19.2, 19.3, 19.5, 19.6_

  - [x] 13.2 Modify `FrontEndCode/src/pages/Home.tsx`
    - Change primary CTA from "Create Your Legacy" to "Start Free"
    - Add HomePricingSection component below "How It Works" section
    - Fetch plan definitions from `/billing/plans` for pricing display
    - Show annual pricing as monthly equivalent with savings percentage from PlanLimits
    - Add "Pricing" link to footer navigation
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [ ] 13.3 Write property test for pricing text derivation (Property 21)
    - **Property 21: Pricing text is derived from plan definition data**
    - Generate random plan definitions with pricing fields
    - Verify rendered pricing UI displays exact values from plan definition, not hardcoded strings
    - Add to `FrontEndCode/src/__tests__/subscription.property.test.ts`
    - **Validates: Requirements 16.3, 17.2, 21.1, 21.2, 21.3**

- [-] 14. Frontend: Upgrade prompts in ConversationInterface and ManageBenefactors
  - [x] 14.1 Modify ConversationInterface to handle `limit_reached` WebSocket messages
    - Listen for `type: 'limit_reached'` messages in WebSocket handler
    - Display UpgradePromptDialog with emotionally framed message from the event
    - Include link to /pricing
    - _Requirements: 20.1, 20.2, 20.6_

  - [x] 14.2 Modify ManageBenefactors page to handle 403 benefactor_limit response
    - Catch 403 with `error: 'benefactor_limit'` from CreateAssignmentFunction
    - Display UpgradePromptDialog with emotionally framed benefactor limit message
    - _Requirements: 20.3_

  - [ ] 14.3 Write property test for plan settings display (Property 23)
    - **Property 23: Plan settings display matches subscription state**
    - Generate random subscription records, verify plan name and trial days display
    - Add to `FrontEndCode/src/__tests__/subscription.property.test.ts`
    - **Validates: Requirements 19.2, 19.3**

- [ ] 15. Frontend: Webhook checkout.session.completed → subscribe during trial (Property 6)
  - [ ] 15.1 Write property test for subscribe-during-trial state transition (Property 6)
    - **Property 6: Subscribing during trial clears trial state**
    - Generate trialing records with valid trialExpiresAt, simulate checkout.session.completed processing
    - Verify resulting record has status=active, planId=premium, trialExpiresAt=null
    - Add to `SamLambda/tests/test_billing_properties.py`
    - **Validates: Requirements 3.6**

- [ ] 16. Checkpoint — Full frontend validation
  - Ensure frontend builds without errors (`npm run build` in FrontEndCode/). Ensure all frontend property tests pass. Ask the user if questions arise.

- [-] 17. Integration wiring and final validation
  - [x] 17.1 Add `VITE_STRIPE_PUBLISHABLE_KEY` to `FrontEndCode/.env.example` and `.env`
    - Document that the publishable key is safe for frontend use
    - _Requirements: 12.3_

  - [x] 17.2 Verify end-to-end route wiring
    - Ensure /pricing route is accessible unauthenticated
    - Ensure SubscriptionContext is in the component tree (inside AuthProvider, wrapping Routes)
    - Ensure all billing API endpoints are in api.ts ENDPOINTS
    - _Requirements: 16.1, 16.2_

  - [ ] 17.3 Write integration-level unit tests
    - Test: Signup → trial record creation → dashboard shows premium access
    - Test: Checkout success URL param → polling → success toast
    - Test: Free user → locked card click → preview overlay → pricing link
    - Test: Coupon apply → plan update → UI refresh
    - Add to `FrontEndCode/src/__tests__/subscription.unit.test.ts`
    - _Requirements: 3.1, 18.3, 20.5, 23.4_

- [x] 18. Final checkpoint — Ensure all tests pass
  - Ensure `sam validate --lint` passes. Ensure all backend and frontend tests pass. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (26 properties total)
- The design specifies fail-open for plan_check in existing Lambdas — never block users due to billing infra issues
- IAM permissions follow the lambda-iam-permissions rule: `ssm:GetParameters` (plural) is needed alongside `ssm:GetParameter` for batch plan loading
- CORS follows the cors-lambda rule: every new Lambda must have `import os` and use `os.environ.get('ALLOWED_ORIGIN', ...)` on all responses
- SharedUtilsLayer needs both arm64 and x86_64 compatibility for WebSocketDefaultFunction
