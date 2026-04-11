# Requirements Document

## Introduction

SoulReel currently operates as a free service with no subscription tiers, usage limits, or payment infrastructure. Every user has unrestricted access to all features — unlimited conversations, unlimited benefactors, and all access condition types. This is unsustainable as the platform scales, since each AI conversation costs approximately $0.30–$0.60 in Bedrock, Polly, and storage charges.

This feature introduces a simplified two-tier Stripe-powered subscription model (Free and SoulReel Premium at $9.99/month or $79/year) with content-category-based access control enforced at the Lambda level, a 7-day automatic Premium trial for all new signups, a coupon system for family members and promotional campaigns, and frontend pricing with emotionally framed upgrade prompts. The billing infrastructure consists of new REST API endpoints backed by two Lambda functions (one Cognito-authenticated for user-facing operations, one unauthenticated for Stripe webhook processing with signature verification), a new DynamoDB table for subscription state, plan definitions stored in SSM Parameter Store, and a scheduled function for trial and coupon expiration.

Free-tier users are restricted to Level 1 Life Story Reflections questions only — Life Events and Values & Emotions content paths are locked behind Premium. The Dashboard shows all three content paths to free users, but Life Events and Values & Emotions display a lock icon with a "Premium" badge and a preview overlay when tapped. Existing Lambdas (WebSocketDefaultFunction, CreateAssignmentFunction) gain category-based access checks that read from the subscription table before allowing operations. The frontend adds a pricing page, homepage pricing section, user plan settings, coupon redemption flow, and contextual upgrade prompts with emotional framing when users hit limits.

## Glossary

- **Billing_Service**: The authenticated Lambda function that handles user-facing billing operations: creating Stripe Checkout sessions, generating Stripe Customer Portal URLs, returning subscription status and usage, and processing coupon redemptions. Exposed via API Gateway with Cognito authorization.
- **Stripe_Webhook_Service**: The unauthenticated Lambda function that receives and processes Stripe webhook events. Verifies event authenticity using the Stripe webhook signing secret before updating subscription state in DynamoDB. Does not use Cognito authorization.
- **UserSubscriptionsDB**: A new DynamoDB table (partition key: `userId`, GSI on `stripeCustomerId`) that stores each user's subscription plan, Stripe identifiers, payment status, trial expiration, coupon information, and current usage counters (benefactor count).
- **Plan_Definition**: A JSON object stored in SSM Parameter Store at `/soulreel/plans/{planId}` that defines the limits for a subscription tier: `allowedQuestionCategories` (list of allowed content paths), `maxBenefactors` (-1 for unlimited), `accessConditionTypes` (list of allowed types), and `features` (list of feature flags).
- **Coupon**: A JSON object stored in SSM Parameter Store at `/soulreel/coupons/{code}` that defines a promotional or family coupon with fields: `code`, `type` (forever_free, time_limited, or percentage), `grantPlan`, `maxRedemptions`, `currentRedemptions`, `expiresAt`, and type-specific fields. Coupon `grantPlan` values reference the premium plan only (replacing previous personal/family/vault references).
- **Coupon_Expiration_Service**: A scheduled Lambda function triggered by EventBridge daily that scans UserSubscriptionsDB for time-limited coupons past their expiration date and for trial subscriptions past their `trialExpiresAt` date, and reverts those users to the free plan.
- **Stripe_Layer**: A Lambda Layer containing the Stripe Python SDK, shared by Billing_Service and Stripe_Webhook_Service.
- **Plan_Check_Utility**: A shared Python module (added to the existing SharedUtilsLayer or inlined) that provides `get_user_plan()`, `check_question_category_access()`, `check_benefactor_limit()`, and `is_trial_active()` functions for use by existing Lambdas enforcing access limits.
- **Legacy_Maker**: A user with `persona_type` of `legacy_maker` who creates video responses and AI conversations. The primary subscriber persona.
- **Pricing_Page**: A new frontend page at `/pricing` that displays the Free vs Premium comparison, handles Stripe Checkout initiation, coupon redemption, and links to the Stripe Customer Portal for existing subscribers.
- **Plan_Settings_Section**: A section in the user's profile or settings area that shows current plan name, trial status and days remaining, usage summary, and upgrade or manage subscription actions.
- **Homepage_Pricing_Section**: A section on the Home page below "How It Works" that displays a clear value statement for the Free and Premium tiers with a call-to-action.

## Requirements

### Requirement 1: Subscription Data Model

**User Story:** As a system administrator, I want a DynamoDB table that stores each user's subscription state, Stripe identifiers, trial information, and usage counters, so that all billing and limit-enforcement operations have a single source of truth.

#### Acceptance Criteria

1. THE UserSubscriptionsDB table SHALL use `userId` (string, Cognito `sub`) as the partition key.
2. THE UserSubscriptionsDB table SHALL include a Global Secondary Index named `stripeCustomerId-index` with `stripeCustomerId` as the partition key, to enable lookups from Stripe webhook events.
3. THE UserSubscriptionsDB table SHALL use PAY_PER_REQUEST billing mode.
4. THE UserSubscriptionsDB table SHALL use KMS server-side encryption with the existing `DataEncryptionKey` CMK.
5. THE UserSubscriptionsDB table SHALL have Point-in-Time Recovery enabled.
6. THE UserSubscriptionsDB table SHALL store the following attributes per user record: `userId`, `stripeCustomerId`, `stripeSubscriptionId`, `planId` (free or premium), `status` (active, canceled, past_due, trialing, comped, or expired), `currentPeriodEnd` (ISO 8601 timestamp), `trialExpiresAt` (ISO 8601 timestamp, set when a trial begins), `couponCode`, `couponType`, `couponExpiresAt`, `benefactorCount` (integer), `createdAt`, and `updatedAt`.

### Requirement 2: Subscription Tier Definitions

**User Story:** As a product owner, I want two subscription tiers (Free and Premium) with specific limits stored as runtime-configurable parameters, so that plan limits can be adjusted without code deployments.

#### Acceptance Criteria

1. THE system SHALL define two subscription tiers stored as Plan_Definitions in SSM Parameter Store: Free and Premium. THE Premium Plan_Definition SHALL include `monthlyPriceDisplay`, `annualPriceDisplay`, `annualMonthlyEquivalentDisplay`, and `annualSavingsPercent` fields so that all pricing text displayed on the frontend is driven by configuration, not hardcoded.
2. THE Free Plan_Definition SHALL specify: `allowedQuestionCategories` restricted to life_story_reflections Level 1 only (no life_events, no values_and_emotions), 2 maximum benefactors, immediate access condition type only, and basic features only.
3. THE Premium Plan_Definition SHALL specify: `allowedQuestionCategories` including life_story_reflections (all levels), life_events, and values_and_emotions, unlimited benefactors (-1), all access condition types (immediate, time_delayed, inactivity_trigger, manual_release), and features including basic, dead_mans_switch, pdf_export, priority_ai, legacy_export, psych_profile, and avatar.
4. WHEN a Plan_Definition is updated in SSM Parameter Store, THE Billing_Service and Plan_Check_Utility SHALL use the updated values on subsequent invocations without requiring a code deployment.

### Requirement 3: Automatic 7-Day Premium Trial on Signup

**User Story:** As a new user, I want to automatically receive 7 days of full Premium access when I sign up, so that I can experience all features before deciding to subscribe.

#### Acceptance Criteria

1. WHEN a new user completes signup, THE system SHALL create a UserSubscriptionsDB record with `planId` set to premium, `status` set to trialing, and `trialExpiresAt` set to 7 days from the current UTC time.
2. THE trial SHALL grant full Premium access (all question categories, unlimited benefactors, all access condition types, all features) without requiring a credit card or coupon code.
3. WHILE a user's `status` is trialing and `trialExpiresAt` is in the future, THE Plan_Check_Utility SHALL treat the user as having Premium plan access.
4. WHEN the trial expires, THE Coupon_Expiration_Service SHALL set the user's `planId` to free and `status` to expired.
5. WHILE a user's trial has 3 or fewer days remaining (starting on day 5 of the trial), THE Dashboard SHALL display a nudge message showing "Your trial ends in N days" with a link to the Pricing_Page.
6. WHEN a trialing user subscribes to Premium before the trial expires, THE Billing_Service SHALL update the user's `status` to active and clear the `trialExpiresAt` field.

### Requirement 4: Stripe Checkout Session Creation

**User Story:** As a legacy maker, I want to start a subscription checkout flow, so that I can upgrade from the free plan to Premium.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a POST endpoint at `/billing/create-checkout-session` on the existing API Gateway with Cognito authorization.
2. WHEN a valid request with a `priceId` is received, THE Billing_Service SHALL create a Stripe Customer (if one does not already exist for the user) and store the `stripeCustomerId` in UserSubscriptionsDB.
3. WHEN a valid request is received, THE Billing_Service SHALL create a Stripe Checkout Session in subscription mode with the specified `priceId`, the user's Stripe Customer ID, success URL pointing to `/dashboard?checkout=success`, and cancel URL pointing to `/pricing?checkout=canceled`.
4. THE Billing_Service SHALL include the Cognito `userId` in the Stripe Checkout Session metadata so the webhook can associate the subscription with the correct user.
5. THE Billing_Service SHALL enable `allow_promotion_codes` on the Checkout Session to support Stripe-native promotional codes.
6. THE Billing_Service SHALL return HTTP 200 with a JSON body containing `{ "sessionUrl": "<stripe_checkout_url>" }`.
7. IF the `priceId` field is missing from the request body, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "Missing priceId" }`.
8. THE Billing_Service SHALL return CORS headers consistent with the existing `ALLOWED_ORIGIN` configuration on all responses including error responses.

### Requirement 5: Stripe Webhook Processing

**User Story:** As a system operator, I want Stripe webhook events to automatically update user subscription state, so that plan changes, renewals, cancellations, and payment failures are reflected in real time.

#### Acceptance Criteria

1. THE Stripe_Webhook_Service SHALL expose a POST endpoint at `/billing/webhook` on the existing API Gateway without Cognito authorization.
2. WHEN a webhook request is received, THE Stripe_Webhook_Service SHALL verify the request signature using the Stripe webhook signing secret stored in SSM Parameter Store at `/soulreel/stripe/webhook-secret`.
3. IF the webhook signature verification fails, THEN THE Stripe_Webhook_Service SHALL return HTTP 400 with `{ "error": "Invalid signature" }` and log the failure.
4. WHEN a `checkout.session.completed` event is received with a `userId` in the session metadata, THE Stripe_Webhook_Service SHALL retrieve the subscription details from Stripe, determine the plan as premium from the price ID, and write or update the user's record in UserSubscriptionsDB with `stripeCustomerId`, `stripeSubscriptionId`, `planId` set to premium, `status` set to active, `currentPeriodEnd`, and `trialExpiresAt` cleared.
5. WHEN a `checkout.session.completed` event is received without a `userId` in the metadata, THE Stripe_Webhook_Service SHALL log a warning and return HTTP 200 without modifying any records.
6. WHEN a `customer.subscription.updated` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI, update the `status`, `planId`, and `currentPeriodEnd` fields in UserSubscriptionsDB.
7. WHEN a `customer.subscription.deleted` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI and set `planId` to free and `status` to canceled in UserSubscriptionsDB.
8. WHEN an `invoice.payment_failed` event is received, THE Stripe_Webhook_Service SHALL look up the user by `stripeCustomerId` via the GSI and set `status` to past_due in UserSubscriptionsDB.
9. WHEN updating a user record from a webhook event, THE Stripe_Webhook_Service SHALL preserve existing usage counters (`benefactorCount`) and only update subscription-related fields.
10. THE Stripe_Webhook_Service SHALL return HTTP 200 with `{ "received": true }` for all successfully processed events.
11. THE Stripe_Webhook_Service SHALL return CORS headers on all responses.
12. THE Stripe_Webhook_Service SHALL map Stripe Price IDs to the premium plan only. The webhook price mapping SHALL contain two entries: one for the Premium monthly price and one for the Premium annual price.

### Requirement 6: Subscription Status Retrieval

**User Story:** As a legacy maker, I want to see my current plan, usage, and limits, so that I know what features are available and how much of my quota I have used.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a GET endpoint at `/billing/status` on the existing API Gateway with Cognito authorization.
2. WHEN a user with no record in UserSubscriptionsDB calls the status endpoint, THE Billing_Service SHALL return the free plan limits and zero usage counters.
3. WHEN a user with an existing subscription record calls the status endpoint, THE Billing_Service SHALL return the user's `planId`, `status`, `currentPeriodEnd`, `trialExpiresAt`, `couponCode`, `couponExpiresAt`, plan limits from the Plan_Definition (including pricing display fields), and current usage counters (`benefactorCount`).
4. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 7: Stripe Customer Portal Access

**User Story:** As a legacy maker with an active subscription, I want to manage my billing details and cancel my subscription through Stripe's Customer Portal, so that I have full control over my payment method and plan.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a GET endpoint at `/billing/portal` on the existing API Gateway with Cognito authorization.
2. WHEN a user with a `stripeCustomerId` in UserSubscriptionsDB calls the portal endpoint, THE Billing_Service SHALL create a Stripe Billing Portal Session with the return URL set to `/dashboard` and return `{ "portalUrl": "<stripe_portal_url>" }`.
3. IF a user without a `stripeCustomerId` calls the portal endpoint, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "No billing account found" }`.
4. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 8: Coupon System

**User Story:** As a product owner, I want a coupon system that supports lifetime free access for family members, time-limited promotional trials, and percentage discounts, so that I can offer flexible incentives without code changes.

#### Acceptance Criteria

1. THE Billing_Service SHALL expose a POST endpoint at `/billing/apply-coupon` on the existing API Gateway with Cognito authorization.
2. WHEN a `forever_free` coupon is redeemed, THE Billing_Service SHALL write a record to UserSubscriptionsDB with `planId` set to premium, `status` set to comped, the `couponCode`, and `couponType` set to forever_free, without creating any Stripe subscription.
3. WHEN a `time_limited` coupon is redeemed, THE Billing_Service SHALL write a record to UserSubscriptionsDB with `planId` set to premium, `status` set to trialing, the `couponCode`, `couponType` set to time_limited, and `couponExpiresAt` set to the current time plus the coupon's `durationDays`.
4. WHEN a `percentage` coupon is redeemed, THE Billing_Service SHALL return the `stripeCouponId` to the frontend so it can be applied during Stripe Checkout, without directly modifying UserSubscriptionsDB.
5. WHEN a coupon is successfully redeemed (forever_free or time_limited), THE Billing_Service SHALL increment the `currentRedemptions` counter in the coupon's SSM parameter.
6. IF the coupon code does not exist in SSM Parameter Store, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "Invalid coupon code" }`.
7. IF the coupon's `expiresAt` date is in the past, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "This coupon has expired" }`.
8. IF the coupon's `currentRedemptions` has reached `maxRedemptions`, THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "This coupon has reached its redemption limit" }`.
9. IF the user already has an active paid plan (status is active and planId is premium), THEN THE Billing_Service SHALL return HTTP 400 with `{ "error": "You already have an active plan" }`.
10. THE Billing_Service SHALL return CORS headers on all responses.

### Requirement 9: Question Category Access Enforcement

**User Story:** As a product owner, I want free-tier users restricted to Level 1 Life Story Reflections questions only, so that Life Events and Values & Emotions content is reserved for Premium subscribers.

#### Acceptance Criteria

1. WHEN a user initiates a conversation via WebSocketDefaultFunction, THE Plan_Check_Utility SHALL read the user's subscription record from UserSubscriptionsDB and the plan's `allowedQuestionCategories` from the Plan_Definition.
2. WHEN a free-plan user attempts to start a conversation with a question from the life_events or values_and_emotions category, THE WebSocketDefaultFunction SHALL send a WebSocket message of type `limit_reached` with `limitType` set to question_category and a descriptive upgrade prompt message, and SHALL NOT start the conversation.
3. WHEN a free-plan user attempts to start a conversation with a Life Story Reflections question above Level 1, THE WebSocketDefaultFunction SHALL send a WebSocket message of type `limit_reached` with `limitType` set to question_level and a descriptive upgrade prompt message, and SHALL NOT start the conversation.
4. WHEN a premium-plan user (status is active, trialing with valid trial, or comped) initiates a conversation, THE WebSocketDefaultFunction SHALL allow the conversation for any question category or level.
5. WHEN a user has no record in UserSubscriptionsDB, THE Plan_Check_Utility SHALL treat the user as being on the free plan.

### Requirement 10: Benefactor Limit Enforcement

**User Story:** As a product owner, I want free-tier users limited to 2 benefactors and Premium users to have unlimited benefactors, so that the benefactor feature scales with subscription tier.

#### Acceptance Criteria

1. WHEN a user creates a benefactor assignment via CreateAssignmentFunction, THE Plan_Check_Utility SHALL read the user's `benefactorCount` from UserSubscriptionsDB and the plan's `maxBenefactors` limit from the Plan_Definition.
2. WHEN the user's `benefactorCount` equals or exceeds the plan's `maxBenefactors` limit, THE CreateAssignmentFunction SHALL return HTTP 403 with `{ "error": "benefactor_limit", "message": "You've chosen 2 people to receive your legacy. Upgrade to share your story with everyone who matters.", "currentCount": <current>, "limit": <limit> }`.
3. WHEN the plan's `maxBenefactors` is -1 (unlimited), THE CreateAssignmentFunction SHALL allow the assignment without checking the count.
4. WHEN a user has no record in UserSubscriptionsDB, THE Plan_Check_Utility SHALL treat the user as being on the free plan with zero benefactors counted.

### Requirement 11: Trial and Coupon Expiration Processing

**User Story:** As a system operator, I want trials and time-limited coupons to expire automatically, so that trial users and promotional users revert to the free plan when their period ends.

#### Acceptance Criteria

1. THE Coupon_Expiration_Service SHALL be triggered by an EventBridge scheduled rule running daily.
2. WHEN triggered, THE Coupon_Expiration_Service SHALL scan UserSubscriptionsDB for records where `couponType` equals time_limited and `couponExpiresAt` is earlier than the current UTC time.
3. WHEN an expired time-limited coupon record is found, THE Coupon_Expiration_Service SHALL update the record to set `planId` to free and `status` to expired.
4. WHEN triggered, THE Coupon_Expiration_Service SHALL also scan UserSubscriptionsDB for records where `status` equals trialing and `trialExpiresAt` is earlier than the current UTC time.
5. WHEN an expired trial record is found, THE Coupon_Expiration_Service SHALL update the record to set `planId` to free and `status` to expired.
6. THE Coupon_Expiration_Service SHALL have a timeout of 60 seconds.

### Requirement 12: Stripe Secrets and Configuration Management

**User Story:** As a system administrator, I want Stripe API keys and webhook secrets stored securely in SSM Parameter Store, so that sensitive credentials are not hardcoded or stored in source control.

#### Acceptance Criteria

1. THE Stripe secret key SHALL be stored as a SecureString SSM parameter at `/soulreel/stripe/secret-key`.
2. THE Stripe webhook signing secret SHALL be stored as a SecureString SSM parameter at `/soulreel/stripe/webhook-secret`.
3. THE Stripe publishable key SHALL be stored as a String SSM parameter at `/soulreel/stripe/publishable-key`.
4. THE Billing_Service SHALL have IAM permissions to read SSM parameters under `/soulreel/stripe/*`, `/soulreel/plans/*`, and `/soulreel/coupons/*`.
5. THE Billing_Service SHALL have IAM permissions to write SSM parameters under `/soulreel/coupons/*` (for incrementing redemption counters).
6. THE Stripe_Webhook_Service SHALL have IAM permissions to read SSM parameters under `/soulreel/stripe/*` only.
7. THE Billing_Service and Stripe_Webhook_Service SHALL cache SSM parameter values in memory within a single Lambda invocation to minimize SSM API calls.

### Requirement 13: Stripe Lambda Layer

**User Story:** As a developer, I want the Stripe Python SDK packaged as a Lambda Layer, so that both billing Lambda functions can share the dependency without bundling it separately.

#### Acceptance Criteria

1. THE Stripe_Layer SHALL contain the `stripe` Python package compatible with Python 3.12.
2. THE Stripe_Layer SHALL be defined in template.yml as an `AWS::Serverless::LayerVersion` resource with `BuildMethod: python3.12`.
3. THE Billing_Service and Stripe_Webhook_Service SHALL both reference the Stripe_Layer in their `Layers` configuration.

### Requirement 14: IAM Permissions for Usage Enforcement

**User Story:** As a system administrator, I want existing Lambda functions to have the minimum IAM permissions needed to check subscription limits, so that enforcement works without granting excessive access.

#### Acceptance Criteria

1. THE WebSocketDefaultFunction SHALL have IAM permissions for `dynamodb:GetItem` and `dynamodb:UpdateItem` on the UserSubscriptionsDB table (to read subscription state and enforce question category access).
2. THE WebSocketDefaultFunction SHALL have IAM permissions for `ssm:GetParameter` on `/soulreel/plans/*` (to read plan limit definitions).
3. THE CreateAssignmentFunction SHALL have IAM permissions for `dynamodb:GetItem` on the UserSubscriptionsDB table (to read benefactor count).
4. THE CreateAssignmentFunction SHALL have IAM permissions for `ssm:GetParameter` on `/soulreel/plans/*`.

### Requirement 15: Stripe Product Configuration

**User Story:** As a system administrator, I want Stripe products and prices configured for the simplified two-tier model, so that checkout sessions reference the correct Premium pricing.

#### Acceptance Criteria

1. THE Stripe Dashboard SHALL contain one product: "SoulReel Premium" with two prices: a monthly recurring price and an annual recurring price. The specific dollar amounts SHALL be configured in Stripe and reflected in the Plan_Definition SSM parameters.
2. THE Stripe_Webhook_Service price-to-plan mapping SHALL contain exactly two entries: the Premium monthly Stripe Price ID mapping to premium, and the Premium annual Stripe Price ID mapping to premium.
3. THE Stripe webhook endpoint SHALL be configured to listen for: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, and `invoice.payment_failed`.

### Requirement 16: Frontend Pricing Page

**User Story:** As a legacy maker, I want a pricing page that shows the Free vs Premium comparison and lets me subscribe, redeem coupons, or manage my existing subscription, so that I can choose and control my plan.

#### Acceptance Criteria

1. THE Pricing_Page SHALL be accessible at the `/pricing` route in the React application.
2. THE Pricing_Page SHALL fetch the user's current plan and usage from `GET /billing/status` on load.
3. THE Pricing_Page SHALL display a comparison of the Free and Premium tiers showing the price, question category access, benefactor limit, access condition types, and feature list for each tier. All pricing text (monthly price, annual price, monthly equivalent, savings percentage) SHALL be rendered from the Plan_Definition data returned by the `/billing/status` endpoint, not hardcoded in the frontend.
4. THE Pricing_Page SHALL display a Subscribe button for Premium that calls `POST /billing/create-checkout-session` with the corresponding Stripe Price ID and redirects the user to the returned Stripe Checkout URL.
5. THE Pricing_Page SHALL display a small "Have a code?" link that, when clicked, expands to reveal a coupon code input field with an Apply button that calls `POST /billing/apply-coupon`. The coupon input SHALL NOT be prominently displayed by default.
6. WHEN the user has an active Premium subscription, THE Pricing_Page SHALL display a Manage Subscription button that calls `GET /billing/portal` and redirects to the Stripe Customer Portal URL.
7. THE Pricing_Page SHALL highlight the user's current plan in the comparison display.
8. THE Pricing_Page SHALL offer both monthly and annual pricing options with a toggle or tab selector.
9. THE Pricing_Page SHALL display the annual price as a monthly equivalent with savings percentage, using values from the Plan_Definition returned by the billing status endpoint.
10. THE Pricing_Page SHALL use the existing SoulReel design system (Tailwind classes, legacy-purple and legacy-navy color tokens, shadcn/ui components).
11. THE Pricing_Page SHALL be responsive, rendering correctly on mobile viewports (below 640px) and desktop viewports.

### Requirement 17: Homepage Pricing Section

**User Story:** As a visitor, I want to see pricing information on the homepage, so that I understand the value proposition before signing up.

#### Acceptance Criteria

1. THE Home page SHALL display a pricing section below the existing "How It Works" section.
2. THE Homepage_Pricing_Section SHALL display a clear value statement communicating that the app is free to start with a Premium upgrade available. The specific price amounts SHALL be fetched from the Plan_Definition via a public pricing endpoint or embedded configuration, not hardcoded in the frontend markup.
3. THE Homepage_Pricing_Section SHALL display the annual pricing as a monthly equivalent with savings percentage, using values from the Plan_Definition.
4. THE Homepage_Pricing_Section SHALL include a call-to-action button linking to the signup flow.
5. THE Home page primary call-to-action button text SHALL be changed from "Create Your Legacy" to "Start Free" to lower the commitment barrier.
6. THE Home page footer navigation SHALL include a "Pricing" link pointing to the `/pricing` route.

### Requirement 18: Dashboard Locked Content with Preview

**User Story:** As a free-tier user, I want to see all three content paths on the Dashboard with locked indicators on premium content, so that I understand what is available with an upgrade.

#### Acceptance Criteria

1. THE Dashboard SHALL display all three content path cards (Life Story Reflections, Life Events, Values & Emotions) for all users regardless of plan.
2. WHILE the user is on the free plan, THE Dashboard SHALL display a lock icon with a "Premium" badge on the Life Events and Values & Emotions content path cards instead of hiding them or showing "Coming Soon".
3. WHEN a free-plan user taps a locked content path card, THE Dashboard SHALL display a preview overlay showing the first question of that content category with a "Subscribe to continue" message and a link to the Pricing_Page.
4. WHILE the user is on the Premium plan (status is active, trialing with valid trial, or comped), THE Dashboard SHALL display all three content path cards as fully accessible without lock icons or badges.

### Requirement 19: User Plan Settings Section

**User Story:** As a legacy maker, I want to see my current plan details, trial status, and usage summary in my profile or settings area, so that I can manage my subscription without navigating to the pricing page.

#### Acceptance Criteria

1. THE Plan_Settings_Section SHALL be accessible from the user's profile or settings area.
2. THE Plan_Settings_Section SHALL display the current plan name (Free or Premium).
3. WHILE the user's `status` is trialing and `trialExpiresAt` is in the future, THE Plan_Settings_Section SHALL display the trial status and the number of days remaining.
4. THE Plan_Settings_Section SHALL display a usage summary including the number of conversations completed and the number of benefactors added.
5. WHILE the user is on the free plan, THE Plan_Settings_Section SHALL display an "Upgrade to Premium" button linking to the Pricing_Page.
6. WHILE the user has an active Premium subscription (status is active), THE Plan_Settings_Section SHALL display a "Manage Subscription" button that calls `GET /billing/portal` and redirects to the Stripe Customer Portal URL.

### Requirement 20: Frontend Upgrade Prompts with Emotional Framing

**User Story:** As a legacy maker on the free plan, I want emotionally framed upgrade prompts when I hit a content boundary or usage limit, so that I understand the value of upgrading in the context of preserving my story.

#### Acceptance Criteria

1. WHEN the ConversationInterface receives a WebSocket message of type `limit_reached` with `limitType` set to question_category, THE ConversationInterface SHALL display an emotionally framed upgrade prompt (e.g., "You've started capturing your story. Unlock Life Events to preserve the moments that shaped who you are.") with a link to the Pricing_Page.
2. WHEN the ConversationInterface receives a WebSocket message of type `limit_reached` with `limitType` set to question_level, THE ConversationInterface SHALL display an emotionally framed upgrade prompt (e.g., "You've explored the first chapter. Upgrade to Premium to go deeper into your life story.") with a link to the Pricing_Page.
3. WHEN CreateAssignmentFunction returns HTTP 403 with error `benefactor_limit`, THE ManageBenefactors page SHALL display an emotionally framed upgrade prompt (e.g., "You've chosen 2 people to receive your legacy. Upgrade to share your story with everyone who matters.") with a link to the Pricing_Page.
4. WHEN a free-plan user taps a locked content path on the Dashboard, THE preview overlay SHALL use emotionally framed messaging (e.g., for Life Events: "These are the moments that shaped who you are. Upgrade to Premium to start preserving them.").
5. WHEN a checkout completes successfully (URL contains `checkout=success`), THE Dashboard SHALL display a success toast confirming the plan upgrade.
6. THE upgrade prompt messages SHALL focus on the emotional value of preserving stories rather than using transactional language about feature unlocking.

### Requirement 21: Annual Pricing with Savings Framing

**User Story:** As a potential subscriber, I want to see the annual pricing presented as a monthly equivalent with clear savings, so that I can make an informed decision between monthly and annual billing.

#### Acceptance Criteria

1. THE Pricing_Page SHALL display the annual price as a monthly equivalent alongside the savings percentage, using the `annualMonthlyEquivalentDisplay` and `annualSavingsPercent` values from the Plan_Definition.
2. THE Homepage_Pricing_Section SHALL display the same annual pricing framing using values from the Plan_Definition.
3. THE Pricing_Page SHALL always show the monthly equivalent of the annual price, not just the annual total. All displayed amounts SHALL be derived from the Plan_Definition, so that changing prices in SSM Parameter Store automatically updates the frontend without a code deployment.

### Requirement 22: Post-Trial Win-Back Notification

**User Story:** As a product owner, I want users who don't convert after their trial expires to receive a win-back notification, so that they are reminded of the value they experienced and encouraged to subscribe.

#### Acceptance Criteria

1. WHEN a user's trial expires and the user does not subscribe to Premium within 3 days of expiration, THE system SHALL trigger a win-back notification (email or in-app).
2. THE win-back notification message SHALL be emotionally framed, referencing the user's trial activity (e.g., "You recorded X conversations during your trial. Your stories are safe, but you can't add new ones to Life Events until you upgrade.").
3. THE win-back notification SHALL include a direct link to the Pricing_Page.
4. THE win-back mechanism SHALL be implemented as a future EventBridge-triggered Lambda that queries UserSubscriptionsDB for users with `status` equal to expired and `trialExpiresAt` between 3 and 4 days ago, and sends a notification via SES or in-app messaging.

### Requirement 23: Subtle Coupon Input on Pricing Page

**User Story:** As a product owner, I want the coupon code input to be unobtrusive on the pricing page, so that regular users are not distracted by searching for a coupon code before subscribing.

#### Acceptance Criteria

1. THE Pricing_Page SHALL display a small "Have a code?" text link below the Subscribe button area.
2. WHEN the "Have a code?" link is clicked, THE Pricing_Page SHALL expand to reveal a coupon code input field with an Apply button.
3. THE coupon input field SHALL NOT be visible by default on page load.
4. WHEN a valid coupon is applied, THE Pricing_Page SHALL display the resulting plan access and confirmation message.
5. WHEN an invalid or expired coupon is applied, THE Pricing_Page SHALL display the error message returned by the Billing_Service.
