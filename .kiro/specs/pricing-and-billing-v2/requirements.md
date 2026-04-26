# Requirements Document

## Introduction

This specification consolidates and supersedes the existing `stripe-subscription-tiers` and `pricing-conversion-optimization` specs into a single implementation plan for SoulReel's updated pricing model. The previous specs assumed a 4-tier model (Free/Personal/Family/Vault), weekly conversation caps, degraded free-tier AI quality, and a $9.99/$89.99 price point. Analysis across four pricing and costing reports has produced a fundamentally different strategy.

The updated model uses a simplified 2-tier structure (Free + Premium) with content-level gating instead of usage caps. Free users get the complete Level 1 experience at full AI quality (Haiku model, Neural voice, 4 turns per conversation) with no weekly limits — the gate is content, not usage. After completing Level 1, non-converting users cost $0/month. Premium is priced at $14.99/month or $149/year, with a soft launch at $99/year for the first 100 "Founding Member" users before raising to $149/year.

The scope covers: (1) Stripe billing infrastructure — DynamoDB subscription table, billing Lambda, webhook Lambda, coupon system, Stripe Python SDK layer; (2) content-level access enforcement — Level 1 gate for free users, Life Events and Values & Emotions locked behind Premium; (3) free-tier limits — 1 benefactor with immediate-access only; (4) cost optimization — Nova Micro for depth scoring, Haiku for conversations, Polly caching, Deepgram batch for video transcription; (5) engagement and conversion — Level 1 completion celebration, upgrade prompt banners, personalized question teasers, weekly re-engagement emails, benefactor-aware nudges; (6) future hooks — founding member coupon with auto-expiry, SSM-based plan system for future tiers, model routing via SSM, win-back coupon system.

Existing billing Lambda functions at `SamLambda/functions/billingFunctions/` and frontend components (`PricingPage.tsx`, `SubscriptionContext.tsx`, `billingService.ts`) will be updated to reflect the new pricing model. The SAM template at `SamLambda/template.yml` will be extended with the UserSubscriptionsDB table, billing Lambda definitions, and IAM policies.

## Glossary

- **Billing_Service**: The authenticated Lambda function (`billingFunctions/billing/app.py`) handling checkout session creation, portal access, subscription status, and coupon redemption. Exposed via API Gateway with Cognito authorization.
- **Stripe_Webhook_Service**: The unauthenticated Lambda function (`billingFunctions/stripeWebhook/app.py`) that receives Stripe webhook events, verifies signatures, and updates subscription state. No Cognito authorization.
- **UserSubscriptionsDB**: DynamoDB table (PK: `userId`, GSI on `stripeCustomerId`) storing subscription plan, Stripe identifiers, payment status, coupon information, and benefactor count per user.
- **Plan_Definition**: JSON object in SSM Parameter Store at `/soulreel/plans/{planId}` defining tier limits: `maxLevel` (highest question level allowed), `allowedCategories` (content paths), `maxBenefactors`, `accessConditionTypes`, `features`, and pricing display fields.
- **Coupon**: JSON object in SSM at `/soulreel/coupons/{code}` defining promotional or family coupons with `type` (forever_free, time_limited, percentage), `grantPlan`, `maxRedemptions`, `currentRedemptions`, `expiresAt`, and type-specific fields.
- **Coupon_Expiration_Service**: Scheduled Lambda (`billingFunctions/couponExpiration/app.py`) triggered daily by EventBridge that reverts expired time-limited coupons and trials to the free plan.
- **Stripe_Layer**: Lambda Layer containing the Stripe Python SDK, shared by Billing_Service and Stripe_Webhook_Service.
- **Plan_Check_Utility**: Shared Python module providing `get_user_plan()`, `check_level_access()`, `check_category_access()`, and `check_benefactor_limit()` for use by existing Lambdas enforcing access.
- **Legacy_Maker**: A user with `persona_type` of `legacy_maker` who records conversations and video responses. The primary subscriber persona.
- **Pricing_Page**: Frontend page at `/pricing` displaying Free vs Premium comparison, Stripe Checkout initiation, coupon redemption, and Stripe Customer Portal link.
- **Celebration_Screen**: A modal or full-screen overlay shown when a user completes all Level 1 questions, displaying achievement summary and upgrade CTA with locked level progression.
- **Upgrade_Banner**: A contextual banner component shown on the Dashboard at key conversion moments (50% Level 1 completion, post-Level 1 completion, every dashboard visit after Level 1 done).
- **Win_Back_Service**: Scheduled Lambda (`billingFunctions/winBack/app.py`) that sends re-engagement coupons to churned or non-converting users.
- **Founding_Member_Coupon**: A coupon with `maxRedemptions: 100` at $99/year that auto-expires when the limit is hit, after which new users see the $149/year price.
- **PostConfirmation_Lambda**: The existing Cognito post-confirmation trigger Lambda that runs after user signup. Extended to create the initial UserSubscriptionsDB record.

## Requirements

### Requirement 1: Subscription Data Model

**User Story:** As a system administrator, I want a DynamoDB table that stores each user's subscription state, Stripe identifiers, and usage counters, so that all billing and access enforcement operations have a single source of truth.

#### Acceptance Criteria

1. THE UserSubscriptionsDB table SHALL use `userId` (string, Cognito `sub`) as the partition key.
2. THE UserSubscriptionsDB table SHALL include a Global Secondary Index named `stripeCustomerId-index` with `stripeCustomerId` as the partition key.
3. THE UserSubscriptionsDB table SHALL use PAY_PER_REQUEST billing mode.
4. THE UserSubscriptionsDB table SHALL use KMS server-side encryption with the existing `DataEncryptionKey` CMK.
5. THE UserSubscriptionsDB table SHALL have Point-in-Time Recovery enabled.
6. THE UserSubscriptionsDB table SHALL store the following attributes per user record: `userId`, `stripeCustomerId`, `stripeSubscriptionId`, `planId` (free or premium), `status` (active, canceled, past_due, trialing, comped, or expired), `billingInterval` (monthly, annual, or null for non-Stripe plans), `currentPeriodEnd` (ISO 8601), `couponCode`, `couponType`, `couponExpiresAt`, `benefactorCount` (integer), `level1CompletionPercent` (integer 0–100), `level1CompletedAt` (ISO 8601 or null), `totalQuestionsCompleted` (integer), `legacyCompleteAt` (ISO 8601 or null), `lastReengagementEmailAt` (ISO 8601 or null), `createdAt`, and `updatedAt`.

### Requirement 2: Subscription Record Initialization

**User Story:** As a new user, I want a subscription record created automatically when I sign up, so that access enforcement and progress tracking work from my first interaction.

#### Acceptance Criteria

1. WHEN a new user completes signup (Cognito post-confirmation trigger), THE PostConfirmation Lambda SHALL create a UserSubscriptionsDB record with `userId` set to the Cognito `sub`, `planId` set to free, `status` set to active, `benefactorCount` set to 0, `level1CompletionPercent` set to 0, `totalQuestionsCompleted` set to 0, `createdAt` and `updatedAt` set to the current UTC timestamp, and all other fields set to null.
2. IF a UserSubscriptionsDB record already exists for the `userId`, THEN THE PostConfirmation Lambda SHALL not overwrite it.
3. THE PostConfirmation Lambda SHALL have IAM permissions for `dynamodb:PutItem` (with a condition expression to prevent overwrites) on the UserSubscriptionsDB table.

### Requirement 3: Two-Tier Plan Definitions

**User Story:** As a product owner, I want exactly two subscription tiers (Free and Premium) with content-level gating stored as runtime-configurable SSM parameters, so that plan limits can be adjusted without code deployments.

#### Acceptance Criteria

1. THE system SHALL define two Plan_Definitions in SSM Parameter Store: Free (`/soulreel/plans/free`) and Premium (`/soulreel/plans/premium`).
2. THE Free Plan_Definition SHALL specify: `maxLevel` set to 1, `allowedCategories` restricted to life_story_reflections only (no life_events, no values_and_emotions), `maxBenefactors` set to 1, `accessConditionTypes` restricted to immediate only, and `features` restricted to basic only.
3. THE Premium Plan_Definition SHALL specify: `maxLevel` set to 10, `allowedCategories` including life_story_reflections, life_events, and values_and_emotions, `maxBenefactors` set to -1 (unlimited), `accessConditionTypes` including immediate, time_delayed, inactivity_trigger, manual_release, and dead_mans_switch, and `features` including basic, dead_mans_switch, pdf_export, legacy_export, and data_export.
4. THE Premium Plan_Definition SHALL include pricing display fields: `monthlyPrice` set to 14.99, `annualPrice` set to 149, `annualMonthlyEquivalent` set to 12.42, and `annualSavingsPercent` set to 17.
5. WHEN a Plan_Definition is updated in SSM Parameter Store, THE Billing_Service and Plan_Check_Utility SHALL use the updated values on subsequent invocations without requiring a code deployment.
6. THE Free Plan_Definition SHALL NOT include any weekly conversation caps or turn limits — free users get unlimited conversations within Level 1 at full AI quality (same model, same voice, same 4 turns as Premium).
7. THE Premium Plan_Definition SHALL include a `foundingMemberPrice` field set to 99 and a `foundingMemberCouponCode` field set to FOUNDING100, so the Pricing_Page can display the founding member offer when available.

### Requirement 4: Stripe Checkout Session Creation

**User Story:** As a Legacy_Maker, I want to start a subscription checkout flow, so that I can upgrade from the free plan to Premium.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a POST endpoint at `/billing/create-checkout-session` on the existing API Gateway with Cognito authorization.
2. WHEN a valid request with a `priceId` is received, THE Billing_Service SHALL create a Stripe Customer (if one does not already exist for the user) and store the `stripeCustomerId` in UserSubscriptionsDB.
3. WHEN a valid request is received, THE Billing_Service SHALL create a Stripe Checkout Session in subscription mode with the specified `priceId`, the user's Stripe Customer ID, success URL pointing to `/dashboard?checkout=success`, and cancel URL pointing to `/pricing?checkout=canceled`.
4. THE Billing_Service SHALL include the Cognito `userId` in the Stripe Checkout Session metadata so the webhook can associate the subscription with the correct user.
5. THE Billing_Service SHALL enable `allow_promotion_codes` on the Checkout Session to support Stripe-native promotional codes.
6. THE Billing_Service SHALL return HTTP 200 with `{ "sessionUrl": "<stripe_checkout_url>" }`.
7. IF the `priceId` field is missing from the request body, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "Missing priceId" }`.
8. THE Billing_Service SHALL return CORS headers using the `ALLOWED_ORIGIN` environment variable on all responses including error responses.

### Requirement 5: Stripe Webhook Processing

**User Story:** As a system operator, I want Stripe webhook events to automatically update user subscription state, so that plan changes, renewals, cancellations, and payment failures are reflected in real time.

#### Acceptance Criteria

1. THE Stripe_Webhook_Service SHALL expose a POST endpoint at `/billing/webhook` on the existing API Gateway without Cognito authorization.
2. WHEN a webhook request is received, THE Stripe_Webhook_Service SHALL verify the request signature using the Stripe webhook signing secret stored in SSM at `/soulreel/stripe/webhook-secret`.
3. IF the webhook signature verification fails, THEN THE Stripe_Webhook_Service SHALL return HTTP 400 with `{ "error": "Invalid signature" }` and log the failure.
4. WHEN a `checkout.session.completed` event is received with a `userId` in the session metadata, THE Stripe_Webhook_Service SHALL update the user's UserSubscriptionsDB record with `stripeCustomerId`, `stripeSubscriptionId`, `planId` set to premium, `status` set to active, `currentPeriodEnd` from the subscription, and `billingInterval` set to monthly or annual based on the Stripe Price ID.
5. WHEN a `checkout.session.completed` event is received without a `userId` in the metadata, THE Stripe_Webhook_Service SHALL log a warning and return HTTP 200 without modifying any records.
6. WHEN a `customer.subscription.updated` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI and update `status`, `planId`, and `currentPeriodEnd` in UserSubscriptionsDB.
7. WHEN a `customer.subscription.deleted` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI and set `planId` to free and `status` to canceled.
8. WHEN an `invoice.payment_failed` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI and set `status` to past_due.
9. WHEN updating a user record from a webhook event, THE Stripe_Webhook_Service SHALL preserve existing usage counters (`benefactorCount`, `level1CompletionPercent`, `level1CompletedAt`) and only update subscription-related fields.
10. THE Stripe_Webhook_Service SHALL return HTTP 200 with `{ "received": true }` for all successfully processed events.
11. THE Stripe_Webhook_Service SHALL return CORS headers on all responses.

### Requirement 6: Subscription Status Retrieval

**User Story:** As a Legacy_Maker, I want to see my current plan, usage, and limits, so that I know what features are available and whether I should upgrade.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a GET endpoint at `/billing/status` on the existing API Gateway with Cognito authorization.
2. WHEN a user with no record in UserSubscriptionsDB calls the status endpoint, THE Billing_Service SHALL return the free plan limits with zero usage counters and `planId` set to free.
3. WHEN a user with an existing subscription record calls the status endpoint, THE Billing_Service SHALL return the user's `planId`, `status`, `currentPeriodEnd`, `couponCode`, `couponExpiresAt`, plan limits from the Plan_Definition (including pricing display fields), and current usage counters (`benefactorCount`, `level1CompletionPercent`, `level1CompletedAt`).
4. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 7: Stripe Customer Portal Access

**User Story:** As a Legacy_Maker with an active subscription, I want to manage my billing details and cancel my subscription through Stripe's Customer Portal, so that I have full control over my payment method and plan.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a GET endpoint at `/billing/portal` on the existing API Gateway with Cognito authorization.
2. WHEN a user with a `stripeCustomerId` in UserSubscriptionsDB calls the portal endpoint, THE Billing_Service SHALL create a Stripe Billing Portal Session with the return URL set to `/dashboard` and return `{ "portalUrl": "<stripe_portal_url>" }`.
3. IF a user without a `stripeCustomerId` calls the portal endpoint, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "No billing account found" }`.
4. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 8: Coupon System

**User Story:** As a product owner, I want a coupon system supporting lifetime free access for family, time-limited promotions, percentage discounts, and a founding member rate, so that I can offer flexible incentives without code changes.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a POST endpoint at `/billing/apply-coupon` on the existing API Gateway with Cognito authorization.
2. WHEN a `forever_free` coupon is redeemed, THE Billing_Service SHALL write a record to UserSubscriptionsDB with `planId` set to premium, `status` set to comped, the `couponCode`, and `couponType` set to forever_free, without creating any Stripe subscription.
3. WHEN a `time_limited` coupon is redeemed, THE Billing_Service SHALL write a record to UserSubscriptionsDB with `planId` set to premium, `status` set to trialing, the `couponCode`, `couponType` set to time_limited, and `couponExpiresAt` set to the current time plus the coupon's `durationDays`.
4. WHEN a `percentage` coupon is redeemed, THE Billing_Service SHALL return the `stripeCouponId` to the frontend so it can be applied during Stripe Checkout, without directly modifying UserSubscriptionsDB.
5. WHEN a coupon is successfully redeemed (forever_free or time_limited), THE Billing_Service SHALL increment the `currentRedemptions` counter in the coupon's SSM parameter.
6. IF the coupon code does not exist in SSM, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "Invalid coupon code" }`.
7. IF the coupon's `expiresAt` date is in the past, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "This coupon has expired" }`.
8. IF the coupon's `currentRedemptions` has reached `maxRedemptions`, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "This coupon has reached its redemption limit" }`.
9. IF the user already has an active paid plan (status is active and planId is premium), THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "You already have an active plan" }`.
10. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 9: Coupon and Trial Expiration Processing

**User Story:** As a system operator, I want time-limited coupons and trials to expire automatically, so that promotional users revert to the free plan when their period ends.

#### Acceptance Criteria

1. THE Coupon_Expiration_Service SHALL be triggered by an EventBridge scheduled rule running daily.
2. WHEN triggered, THE Coupon_Expiration_Service SHALL scan UserSubscriptionsDB for records where `couponType` equals time_limited and `couponExpiresAt` is earlier than the current UTC time, and set those records' `planId` to free and `status` to expired.
3. WHEN triggered, THE Coupon_Expiration_Service SHALL also scan for records where `status` equals trialing and `couponExpiresAt` is earlier than the current UTC time, and set those records' `planId` to free and `status` to expired.
4. THE Coupon_Expiration_Service SHALL have a timeout of 60 seconds and 256 MB memory.

### Requirement 10: Content-Level Access Enforcement

**User Story:** As a product owner, I want free-tier users restricted to Level 1 Life Story Reflections only, with Life Events and Values & Emotions locked behind Premium, so that the content progression drives conversion.

#### Acceptance Criteria

1. WHEN a user initiates a conversation via WebSocketDefaultFunction, THE Plan_Check_Utility SHALL read the user's subscription record from UserSubscriptionsDB and the plan's `maxLevel` and `allowedCategories` from the Plan_Definition.
2. WHEN a free-plan user attempts to start a conversation with a question above Level 1, THE WebSocketDefaultFunction SHALL send a WebSocket message of type `limit_reached` with `limitType` set to question_level and a descriptive upgrade prompt message, and SHALL NOT start the conversation.
3. WHEN a free-plan user attempts to start a conversation with a question from the life_events or values_and_emotions category, THE WebSocketDefaultFunction SHALL send a WebSocket message of type `limit_reached` with `limitType` set to question_category and a descriptive upgrade prompt message, and SHALL NOT start the conversation.
4. WHEN a premium-plan user (status is active, trialing with valid coupon, or comped) initiates a conversation, THE WebSocketDefaultFunction SHALL allow the conversation for any question category or level.
5. WHEN a user has no record in UserSubscriptionsDB, THE Plan_Check_Utility SHALL treat the user as being on the free plan.
6. THE free-plan conversation experience SHALL use the same AI model (Haiku), same voice (Neural), and same turn limit (4) as Premium — there is no quality degradation for free users.

### Requirement 11: Benefactor Limit Enforcement

**User Story:** As a product owner, I want free-tier users limited to 1 benefactor with immediate-access only, and Premium users to have unlimited benefactors with all access condition types, so that benefactor features scale with subscription tier.

#### Acceptance Criteria

1. WHEN a user creates a benefactor assignment via CreateAssignmentFunction, THE Plan_Check_Utility SHALL read the user's `benefactorCount` from UserSubscriptionsDB and the plan's `maxBenefactors` and `accessConditionTypes` from the Plan_Definition.
2. WHEN the user's `benefactorCount` equals or exceeds the plan's `maxBenefactors` limit, THE CreateAssignmentFunction SHALL return HTTP 403 with `{ "error": "benefactor_limit", "message": "Upgrade to Premium to share your story with everyone who matters.", "currentCount": <current>, "limit": <limit> }`.
3. WHEN a free-plan user attempts to create a benefactor assignment with an access condition type not in the free plan's `accessConditionTypes` list, THE CreateAssignmentFunction SHALL return HTTP 403 with `{ "error": "access_condition_restricted", "message": "Upgrade to Premium to unlock time-delay, inactivity, and dead man's switch access conditions." }`.
4. WHEN the plan's `maxBenefactors` is -1 (unlimited), THE CreateAssignmentFunction SHALL allow the assignment without checking the count.
5. WHEN a user has no record in UserSubscriptionsDB, THE Plan_Check_Utility SHALL treat the user as being on the free plan with zero benefactors counted.

### Requirement 12: Stripe Secrets and Configuration Management

**User Story:** As a system administrator, I want Stripe API keys and webhook secrets stored securely in SSM Parameter Store, so that sensitive credentials are not in source control.

#### Acceptance Criteria

1. THE Stripe secret key SHALL be stored as a SecureString SSM parameter at `/soulreel/stripe/secret-key`.
2. THE Stripe webhook signing secret SHALL be stored as a SecureString SSM parameter at `/soulreel/stripe/webhook-secret`.
3. THE Stripe publishable key SHALL be stored as a String SSM parameter at `/soulreel/stripe/publishable-key`.
4. THE Billing_Service SHALL have IAM permissions to read SSM parameters under `/soulreel/stripe/*`, `/soulreel/plans/*`, and `/soulreel/coupons/*`, and to write SSM parameters under `/soulreel/coupons/*` (for incrementing redemption counters).
5. THE Stripe_Webhook_Service SHALL have IAM permissions to read SSM parameters under `/soulreel/stripe/*` only.
6. THE Billing_Service and Stripe_Webhook_Service SHALL cache SSM parameter values in memory within a single Lambda invocation to minimize SSM API calls.

### Requirement 13: Stripe Lambda Layer

**User Story:** As a developer, I want the Stripe Python SDK packaged as a Lambda Layer, so that both billing Lambda functions share the dependency.

#### Acceptance Criteria

1. THE Stripe_Layer SHALL contain the `stripe` Python package compatible with Python 3.12.
2. THE Stripe_Layer SHALL be defined in template.yml as an `AWS::Serverless::LayerVersion` resource with `BuildMethod: python3.12`.
3. THE Billing_Service and Stripe_Webhook_Service SHALL both reference the Stripe_Layer in their `Layers` configuration.

### Requirement 14: IAM Permissions for Access Enforcement

**User Story:** As a system administrator, I want existing Lambda functions to have the minimum IAM permissions needed to check subscription limits, so that enforcement works without granting excessive access.

#### Acceptance Criteria

1. THE WebSocketDefaultFunction SHALL have IAM permissions for `dynamodb:GetItem` and `dynamodb:UpdateItem` on the UserSubscriptionsDB table and `ssm:GetParameter` on `/soulreel/plans/*`.
2. THE CreateAssignmentFunction SHALL have IAM permissions for `dynamodb:GetItem` on the UserSubscriptionsDB table and `ssm:GetParameter` on `/soulreel/plans/*`.
3. THE Billing_Service SHALL have IAM permissions for `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, and `dynamodb:Query` on the UserSubscriptionsDB table.
4. THE Stripe_Webhook_Service SHALL have IAM permissions for `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, and `dynamodb:Query` on the UserSubscriptionsDB table (including the `stripeCustomerId-index` GSI).

### Requirement 15: Stripe Product Configuration

**User Story:** As a system administrator, I want Stripe products and prices configured for the 2-tier model with founding member pricing, so that checkout sessions reference the correct pricing.

#### Acceptance Criteria

1. THE Stripe Dashboard SHALL contain one product: "SoulReel Premium" with two prices: a monthly recurring price at $14.99 and an annual recurring price at $149.
2. THE Stripe_Webhook_Service price-to-plan mapping SHALL map both Stripe Price IDs (monthly and annual) to the premium plan.
3. THE Stripe webhook endpoint SHALL be configured to listen for: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, and `invoice.payment_failed`.
4. THE Founding_Member_Coupon SHALL be defined in SSM at `/soulreel/coupons/FOUNDING100` with `type` set to percentage, `maxRedemptions` set to 100, and a Stripe coupon that discounts the $149/year price to $99/year, locked in for life (coupon duration: forever).

### Requirement 16: Frontend Pricing Page

**User Story:** As a Legacy_Maker, I want a pricing page that shows the Free vs Premium comparison with the updated $14.99/$149 pricing, lets me subscribe, redeem coupons, or manage my subscription, so that I can choose and control my plan.

#### Acceptance Criteria

1. THE Pricing_Page SHALL be accessible at the `/pricing` route.
2. THE Pricing_Page SHALL fetch the user's current plan and usage from `GET /billing/status` on load.
3. THE Pricing_Page SHALL display a comparison of the Free and Premium tiers showing content access (Level 1 vs all 10 levels + Life Events + Values & Emotions), benefactor limits (1 vs unlimited), access condition types, and feature list. All pricing text SHALL be rendered from Plan_Definition data returned by the status endpoint, not hardcoded.
4. THE Pricing_Page SHALL default the billing toggle to "Annual" with a "Save 17%" badge on the annual option.
5. THE Pricing_Page SHALL display a Subscribe button for Premium that calls `POST /billing/create-checkout-session` with the corresponding Stripe Price ID and redirects to the Stripe Checkout URL.
6. THE Pricing_Page SHALL display a small "Have a code?" link that expands to reveal a coupon input field with an Apply button calling `POST /billing/apply-coupon`.
7. WHEN the user has an active Premium subscription, THE Pricing_Page SHALL display a Manage Subscription button that calls `GET /billing/portal` and redirects to the Stripe Customer Portal.
8. THE Pricing_Page SHALL highlight the user's current plan in the comparison.
9. THE Pricing_Page SHALL use the existing SoulReel design system (Tailwind, legacy-purple and legacy-navy tokens, shadcn/ui components) and be responsive on mobile and desktop viewports.
10. THE Pricing_Page SHALL display the anchoring text "Less than a cup of coffee a week" below the annual Premium price.
11. THE Pricing_Page SHALL display trust messaging with a shield icon below the plan comparison: recordings, transcripts, and summaries remain accessible regardless of plan status.

### Requirement 17: Level 1 Completion Tracking

**User Story:** As a product owner, I want to track each free user's Level 1 completion progress, so that the system can trigger upgrade prompts and the celebration screen at the right moments.

#### Acceptance Criteria

1. WHEN a free-plan user completes a conversation for a Level 1 question, THE WebSocketDefaultFunction SHALL update the user's `level1CompletionPercent` in UserSubscriptionsDB based on the ratio of completed Level 1 questions to total Level 1 questions.
2. WHEN a free-plan user completes the last Level 1 question, THE WebSocketDefaultFunction SHALL set `level1CompletedAt` to the current UTC timestamp in UserSubscriptionsDB.
3. THE Billing_Service status endpoint SHALL return `level1CompletionPercent` and `level1CompletedAt` in the subscription status response.
4. WHEN a premium-plan user completes conversations, THE WebSocketDefaultFunction SHALL NOT update Level 1 completion tracking (it is only relevant for free-tier conversion).

### Requirement 18: Level 1 Completion Celebration Screen

**User Story:** As a free user who has completed all Level 1 questions, I want to see a celebration screen that acknowledges my achievement and shows me what's next, so that I feel accomplished and motivated to upgrade.

#### Acceptance Criteria

1. WHEN a free-plan user's `level1CompletedAt` transitions from null to a timestamp (detected on the next dashboard load or conversation completion), THE Dashboard SHALL display the Celebration_Screen.
2. THE Celebration_Screen SHALL display the number of stories recorded, the Level 1 categories completed (Childhood Memories, Family & Upbringing, School Days, Friends), and a congratulatory message.
3. THE Celebration_Screen SHALL display a locked level progression showing Levels 2 through 10 with their category names and lock icons, emphasizing the emotional progression from "Hobbies & Traditions" to "Messages to Loved Ones."
4. THE Celebration_Screen SHALL display the count of personalized Life Events questions waiting, fetched from the user's completed Life Events survey responses stored in the SurveyResponsesDB table, formatted as "X personalized questions waiting for you."
5. THE Celebration_Screen SHALL display an "Upgrade to Premium" button linking to the Pricing_Page with the annual plan pre-selected.
6. THE Celebration_Screen SHALL display the Premium price ($14.99/month or $149/year) directly on the screen.
7. THE Celebration_Screen SHALL be dismissible, returning the user to the Dashboard.

### Requirement 19: Upgrade Prompt Banners

**User Story:** As a product owner, I want contextual upgrade banners shown at key conversion moments, so that free users are nudged toward Premium at the points of highest motivation.

#### Acceptance Criteria

1. WHEN a free-plan user's `level1CompletionPercent` reaches or exceeds 50 and `level1CompletedAt` is null, THE Dashboard SHALL display an Upgrade_Banner with the message "You're halfway through Level 1. Premium unlocks 9 more levels of deeper questions."
2. WHEN a free-plan user's `level1CompletedAt` is not null, THE Dashboard SHALL display a persistent "Continue your legacy" section showing the locked level progression and an upgrade CTA on every dashboard visit.
3. WHEN a free-plan user's `level1CompletedAt` is not null, THE Dashboard SHALL display the count of personalized Life Events questions waiting as a teaser: "X personalized questions waiting for you."
4. WHEN a free-plan user with a benefactor set up visits the Dashboard after Level 1 completion, THE Dashboard SHALL display a benefactor-aware prompt: "Your [benefactor name] can see your Level 1 stories. Upgrade to share the stories that really matter."
5. WHILE the user is on the Premium plan, THE Dashboard SHALL NOT display any Upgrade_Banners.

### Requirement 20: Dashboard Locked Content Display

**User Story:** As a free-tier user, I want to see all three content paths on the Dashboard with locked indicators on premium content, so that I understand what is available with an upgrade.

#### Acceptance Criteria

1. THE Dashboard SHALL display all three content path cards (Life Story Reflections, Life Events, Values & Emotions) for all users regardless of plan.
2. WHILE the user is on the free plan, THE Dashboard SHALL display a lock icon with a "Premium" badge on the Life Events and Values & Emotions content path cards.
3. WHILE the user is on the free plan, THE Dashboard SHALL display lock icons on Life Story Reflections levels 2 through 10 within the Life Story Reflections content path.
4. WHEN a free-plan user taps a locked content path card, THE Dashboard SHALL display a preview overlay showing a sample question from that category with a "Subscribe to unlock" message and a link to the Pricing_Page.
5. WHILE the user is on the Premium plan, THE Dashboard SHALL display all content path cards as fully accessible without lock icons.

### Requirement 21: Cost Optimization — Depth Scoring Model Switch

**User Story:** As a system operator, I want depth scoring switched from Claude 3 Haiku to Amazon Nova Micro, so that scoring costs are reduced by approximately 85% without impacting quality for this simple classification task.

#### Acceptance Criteria

1. THE SSM parameter at `/virtuallegacy/conversation/llm-scoring-model` SHALL be updated to `amazon.nova-micro-v1:0`.
2. THE WebSocketDefaultFunction IAM policy in template.yml SHALL include `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0` in the Bedrock InvokeModel resource list.
3. WHEN the scoring model is changed, THE depth scoring function in `llm.py` SHALL continue to produce scores as an integer between 0 and 3 inclusive, parseable from the model response using the existing `score_response_depth()` parsing logic.

### Requirement 22: Cost Optimization — Conversation Model Switch to Haiku

**User Story:** As a system operator, I want the conversation response generation model switched from Claude 3.5 Sonnet v2 to Claude 3.5 Haiku, so that the largest per-turn cost is reduced by approximately 85%.

#### Acceptance Criteria

1. THE SSM parameter at `/virtuallegacy/conversation/llm-conversation-model` SHALL be updated to `us.anthropic.claude-3-5-haiku-20241022-v1:0`.
2. THE WebSocketDefaultFunction IAM policy SHALL already include the Haiku inference profile ARN (verified as existing in the current template).
3. WHEN the conversation model is changed, THE conversation engine SHALL produce follow-up questions that reference the user's previous response content and maintain conversational coherence across turns.

### Requirement 23: Cost Optimization — Polly Caching for Question Greetings

**User Story:** As a system operator, I want Polly audio cached for question greetings (turn 0), so that the same question text is not re-synthesized for every user.

#### Acceptance Criteria

1. WHEN the conversation turn is 0 (initial question greeting), THE `text_to_speech` function in `speech.py` SHALL check for a cached audio file at a deterministic S3 key based on the question ID, voice ID, and engine.
2. WHEN a cache hit is found, THE `text_to_speech` function SHALL return a presigned URL for the cached file without calling Polly.
3. WHEN a cache miss occurs, THE `text_to_speech` function SHALL synthesize the audio via Polly, store it at the deterministic cache key, and return the presigned URL.
4. WHEN the conversation turn is greater than 0 (AI follow-up responses), THE `text_to_speech` function SHALL synthesize via Polly as normal without caching (follow-up responses are unique per conversation).

### Requirement 24: Cost Optimization — Video Transcription Switch to Deepgram Batch

**User Story:** As a system operator, I want video transcription switched from AWS Transcribe to Deepgram batch API, so that transcription costs are reduced by approximately 80%.

#### Acceptance Criteria

1. WHEN a video is uploaded and requires transcription, THE ProcessVideoFunction SHALL call the Deepgram batch transcription API instead of AWS Transcribe.
2. THE ProcessVideoFunction SHALL use the Deepgram API key stored in SSM Parameter Store.
3. THE ProcessVideoFunction SHALL produce transcription output in the same format expected by downstream summarization functions.
4. THE template.yml SHALL remove the AWS Transcribe IAM permissions from ProcessVideoFunction and add permissions for the Deepgram API key SSM parameter.

### Requirement 25: Engagement — Weekly Re-engagement Email

**User Story:** As a product owner, I want free users who completed Level 1 but did not convert to receive a weekly re-engagement email, so that they are reminded of the value they've already created and motivated to upgrade.

#### Acceptance Criteria

1. THE Win_Back_Service SHALL run on a weekly EventBridge schedule.
2. WHEN triggered, THE Win_Back_Service SHALL query UserSubscriptionsDB for users where `planId` is free, `level1CompletedAt` is not null, and `level1CompletedAt` is more than 7 days ago.
3. FOR EACH qualifying user, THE Win_Back_Service SHALL send an email via SES with the subject line "Your stories are preserved. Your family is waiting for the deeper ones." and body content referencing the number of stories recorded and the locked levels ahead. THE email SHALL include an unsubscribe link.
4. WHEN a re-engagement email is sent, THE Win_Back_Service SHALL update the user's `lastReengagementEmailAt` field in UserSubscriptionsDB to the current UTC timestamp.
5. THE Win_Back_Service SHALL skip users whose `lastReengagementEmailAt` is within the last 7 days.
6. THE Win_Back_Service SHALL have IAM permissions for `dynamodb:Scan` and `dynamodb:UpdateItem` on UserSubscriptionsDB and `ses:SendEmail`.

### Requirement 26: Engagement — Soft Nudge for High-Volume Users

**User Story:** As a product owner, I want premium users who complete 50 conversations in a month to see a one-time suggestion to switch to the annual plan, so that high-engagement users are guided toward higher-LTV billing.

#### Acceptance Criteria

1. WHEN a premium monthly-plan user completes their 50th conversation in a calendar month, THE WebSocketDefaultFunction SHALL send a one-time WebSocket message suggesting the annual plan with the savings percentage.
2. THE nudge message SHALL be sent at most once per user per calendar month.
3. THE nudge message SHALL NOT be sent to users already on an annual plan.

### Requirement 27: Future Hooks — Founding Member Auto-Expiry

**User Story:** As a product owner, I want the founding member coupon to auto-expire after 100 redemptions, so that new users automatically see the $149/year price once the founding cohort is full.

#### Acceptance Criteria

1. THE Founding_Member_Coupon in SSM SHALL have `maxRedemptions` set to 100.
2. WHEN the Billing_Service processes a coupon redemption and the coupon's `currentRedemptions` reaches `maxRedemptions`, THE Billing_Service SHALL reject subsequent redemption attempts with `{ "error": "This coupon has reached its redemption limit" }`.
3. THE Pricing_Page SHALL check whether the founding member price is still available and display it only when the coupon has remaining redemptions, otherwise displaying the standard $149/year price.

### Requirement 28: Future Hooks — Win-Back Coupon System

**User Story:** As a product owner, I want a win-back coupon (WINBACK99) ready for churned users, so that re-engagement campaigns can offer the $99/year rate to users who canceled.

#### Acceptance Criteria

1. THE WINBACK99 coupon SHALL be defined in SSM at `/soulreel/coupons/WINBACK99` with `type` set to percentage, a Stripe coupon that discounts the $149/year price to $99/year, and a configurable `maxRedemptions` and `expiresAt`.
2. THE Win_Back_Service SHALL be capable of including the WINBACK99 code in re-engagement emails sent to users whose `status` is canceled and whose `currentPeriodEnd` is more than 30 days in the past.

### Requirement 29: Future Hooks — Legacy Complete Discount

**User Story:** As a product owner, I want a mechanism to offer a $20 discount on annual renewal when a user finishes all 300 questions, so that completion is rewarded and annual retention is reinforced.

#### Acceptance Criteria

1. THE system SHALL track total questions completed per user (across all levels and categories) in UserSubscriptionsDB via a `totalQuestionsCompleted` counter.
2. WHEN `totalQuestionsCompleted` reaches 300, THE system SHALL set a `legacyCompleteAt` timestamp on the user's subscription record.
3. THE system SHALL support a `LEGACYCOMPLETE` coupon in SSM that grants a $20 discount on the next annual renewal, to be triggered by a future scheduled function or manual campaign.

### Requirement 30: Homepage Pricing Section Update

**User Story:** As a visitor, I want to see the updated pricing on the homepage, so that I understand the value proposition with the new $14.99/$149 price point.

#### Acceptance Criteria

1. THE Home page SHALL display a pricing section below the "How It Works" section.
2. THE pricing section SHALL display the annual price as the primary price with the monthly equivalent, using values from the Plan_Definition (not hardcoded).
3. THE pricing section SHALL include a call-to-action button linking to the signup flow.
4. THE Home page primary CTA button text SHALL read "Start Free" to lower the commitment barrier.
5. THE Home page footer navigation SHALL include a "Pricing" link pointing to `/pricing`.

### Requirement 31: User Plan Settings Section

**User Story:** As a Legacy_Maker, I want to see my current plan details and usage in my profile settings, so that I can manage my subscription without navigating to the pricing page.

#### Acceptance Criteria

1. THE Plan settings section SHALL be accessible from the user's profile or settings area.
2. THE Plan settings section SHALL display the current plan name (Free or Premium) and status.
3. WHILE the user is on the free plan, THE Plan settings section SHALL display an "Upgrade to Premium" button linking to the Pricing_Page.
4. WHILE the user has an active Premium subscription, THE Plan settings section SHALL display a "Manage Subscription" button that opens the Stripe Customer Portal.
5. THE Plan settings section SHALL display the benefactor count and Level 1 completion progress for free users.

### Requirement 32: Existing User Migration

**User Story:** As a product owner, I want existing users to be migrated gracefully when the subscription system goes live, so that no one loses access to content they have already recorded.

#### Acceptance Criteria

1. WHEN the subscription system is deployed, THE system SHALL create a UserSubscriptionsDB record for each existing Cognito user with `planId` set to free and `status` set to active, via a one-time migration script.
2. THE migration script SHALL calculate `level1CompletionPercent` and `level1CompletedAt` for each existing user based on their existing conversation history in the ConversationStateDB table.
3. THE migration script SHALL calculate `benefactorCount` for each existing user based on their existing assignments in the AssignmentsDB table.
4. THE migration script SHALL calculate `totalQuestionsCompleted` for each existing user based on their existing conversation history.
5. EXISTING users who have already recorded content beyond Level 1 SHALL still be able to view and access their previously recorded conversations and videos regardless of plan — the content-level gate SHALL only apply to starting new conversations, not viewing existing ones.
6. THE migration script SHALL be idempotent — running it multiple times SHALL not create duplicate records or overwrite existing subscription records.

### Requirement 33: Public Plan Information Endpoint

**User Story:** As a visitor who is not logged in, I want to see pricing information on the homepage and pricing page, so that I can evaluate the product before signing up.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a GET endpoint at `/billing/plans` on the existing API Gateway without Cognito authorization.
2. THE `/billing/plans` endpoint SHALL return the Premium Plan_Definition pricing display fields (`monthlyPrice`, `annualPrice`, `annualMonthlyEquivalent`, `annualSavingsPercent`, `foundingMemberPrice`, `foundingMemberCouponCode`) and the founding member coupon's remaining redemptions count.
3. THE `/billing/plans` endpoint SHALL return CORS headers on all responses.
4. THE Home page and Pricing_Page SHALL use this endpoint to display pricing information for unauthenticated visitors.
