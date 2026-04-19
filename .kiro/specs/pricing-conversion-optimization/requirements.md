# Requirements Document

## Introduction

This specification covers 10 marketing and conversion optimization improvements for the SoulReel legacy preservation app. The goal is to increase free-to-premium conversion rates by improving the user journey from landing page through trial to paid subscription. Changes span the Home page, Pricing page, Dashboard, UpgradePromptDialog, backend plan enforcement, trial duration, conversation usage tracking, and re-engagement flows.

## Glossary

- **SoulReel_App**: The SoulReel legacy preservation web application where users record video/audio responses to AI-guided conversation questions
- **Home_Page**: The public landing page (`Home.tsx`) that introduces SoulReel and contains sign-up CTAs
- **Pricing_Page**: The plan comparison page (`PricingPage.tsx`) showing Free vs Premium cards with billing toggle and checkout flow
- **Dashboard**: The authenticated content hub (`Dashboard.tsx`) displaying three content path cards (Life Story Reflections, Life Events, Values & Emotions)
- **Upgrade_Dialog**: The modal component (`UpgradePromptDialog.tsx`) shown when a free user attempts a premium-only action
- **Plan_Check_Service**: The backend subscription enforcement module (`plan_check.py`) that verifies user access to question categories and benefactor limits
- **Billing_Lambda**: The billing endpoint Lambda (`billing/app.py`) handling checkout, status, portal, coupon, and public plan endpoints
- **PostConfirmation_Lambda**: The Cognito post-confirmation trigger (`postConfirmation/app.py`) that creates trial subscription records on signup
- **WebSocket_Handler**: The conversation WebSocket Lambda (`wsDefault/app.py`) that manages real-time AI conversations
- **Subscription_Context**: The React context (`SubscriptionContext.tsx`) providing subscription state to all frontend components
- **Billing_Service**: The frontend API service (`billingService.ts`) for billing-related HTTP calls
- **Content_Path_Card**: A Dashboard card representing one of the three content paths (Life Story Reflections, Life Events, Values & Emotions)
- **Preview_Question**: A single sample question from a locked content category that free users may try before upgrading
- **Billing_Toggle**: The Monthly/Annual switch on the Pricing_Page that controls which price is displayed
- **Usage_Indicator**: A Dashboard element showing how many conversations a user has started in the current week relative to their plan limit
- **SSM_Plan_Definition**: The AWS SSM Parameter Store entries (`/soulreel/plans/free`, `/soulreel/plans/premium`) defining plan capabilities
- **Win_Back_Function**: The existing daily Lambda (`winBack/app.py`) that sends 50% off coupons to users whose trial expired 3-4 days ago
- **COMEBACK20_Coupon**: A persistent SSM coupon offering 20% off, shown to returning Pricing_Page visitors who did not convert on their first visit
- **Trust_Messaging**: Copy reassuring users that recordings remain accessible regardless of plan status

## Requirements

### Requirement 1: Preview Questions for Locked Categories

**User Story:** As a free user, I want to try one sample question from each locked content category, so that I can experience the value of premium content before deciding to upgrade.

#### Acceptance Criteria

1. THE SSM_Plan_Definition for the free plan SHALL include a `previewQuestions` list containing one question ID per locked category (Life Events, Values & Emotions)
2. WHEN a free user requests access to a question listed in `previewQuestions`, THE Plan_Check_Service SHALL return `allowed: true` with an `isPreview: true` flag in the response
3. WHEN a free user requests access to a locked question that is not in `previewQuestions`, THE Plan_Check_Service SHALL deny access with an upgrade message
4. WHEN a premium user requests access to any question, THE Plan_Check_Service SHALL allow access without the `isPreview` flag
5. THE Dashboard SHALL display a "Try 1 free question" label on each locked Content_Path_Card instead of showing the card as fully locked
6. WHEN a free user taps "Try 1 free question" on a locked Content_Path_Card, THE Dashboard SHALL navigate the user to the preview question for that category
7. WHEN a free user completes the preview question for a category, THE Dashboard SHALL revert that Content_Path_Card to the standard locked state with an upgrade prompt
8. THE Billing_Lambda status endpoint SHALL include `previewQuestions` in the plan limits returned to the frontend
9. THE Subscription_Context SHALL expose `previewQuestions` from the plan limits to consuming components

### Requirement 2: Extend Trial Duration to 14 Days

**User Story:** As a new user, I want a 14-day premium trial instead of 7 days, so that I have more time to explore premium features before deciding to subscribe.

#### Acceptance Criteria

1. WHEN a new user completes signup, THE PostConfirmation_Lambda SHALL create a trial subscription record with a `trialExpiresAt` value 14 days from the current UTC time
2. WHILE a user's trial has 5 or fewer days remaining and more than 0 days remaining, THE Dashboard SHALL display a trial expiration nudge banner
3. WHILE a user's trial has 5 or fewer days remaining and more than 0 days remaining, THE Header component SHALL display a trial expiration indicator

### Requirement 3: Redesign Home Page to Sell the Experience

**User Story:** As a prospective user visiting the landing page, I want to understand the SoulReel experience through concrete examples, so that I feel motivated to sign up.

#### Acceptance Criteria

1. THE Home_Page "How It Works" section SHALL display three product-specific steps: "Choose a question from your life story", "Have an AI-guided conversation", and "Share your story with the people who matter"
2. THE Home_Page SHALL display a sample question section between the "How It Works" section and the pricing section, showing one example question from each content path
3. THE Home_Page SHALL display a testimonial placeholder section between the sample question section and the pricing section
4. THE Home_Page pricing section SHALL lead with the value proposition text before displaying the price
5. THE Home_Page pricing section SHALL display the annual equivalent price as the primary price with the monthly price shown as a secondary option

### Requirement 4: Clarify Dual CTA on Home Page

**User Story:** As a first-time visitor, I want to clearly understand the difference between "Start Free" and "Start Their Legacy", so that I choose the correct signup path.

#### Acceptance Criteria

1. THE Home_Page "Start Free" button SHALL display the subtitle "Preserve your own stories and memories" directly below the button text
2. THE Home_Page "Start Their Legacy" button SHALL display the subtitle "Set it up for a parent, grandparent, or loved one" directly below the button text
3. THE Home_Page SHALL render the "Start Free" button with primary visual styling (filled background) and the "Start Their Legacy" button with secondary visual styling (outline or muted background)

### Requirement 5: Add Anchoring and Social Proof to Pricing Page

**User Story:** As a user evaluating plans, I want to see social proof and value anchoring on the pricing page, so that I feel confident the premium plan is worth the cost.

#### Acceptance Criteria

1. WHILE a non-subscribed or free user views the Pricing_Page, THE Pricing_Page SHALL display a "Recommended" badge on the Premium plan card
2. THE Pricing_Page Premium card SHALL display the anchoring text "Less than a cup of coffee a week" below the price
3. THE Pricing_Page SHALL display a social proof section below the plan comparison grid containing a testimonial placeholder and a family counter placeholder
4. THE Pricing_Page SHALL display Trust_Messaging directly below the plan comparison grid, above the social proof section, replacing the current bottom gray trust section

### Requirement 6: Default Billing Toggle to Annual with Savings Emphasis

**User Story:** As a user on the pricing page, I want the annual billing option to be pre-selected and visually emphasized, so that I am guided toward the best-value option.

#### Acceptance Criteria

1. WHEN the Pricing_Page loads, THE Billing_Toggle SHALL default to the "annual" position
2. THE Billing_Toggle SHALL display a "Best Value" badge adjacent to the "Annual" option
3. WHILE the Billing_Toggle is set to "annual", THE Pricing_Page SHALL display the savings percentage in a prominent callout near the Premium price
4. THE Home_Page pricing section SHALL display the annual equivalent price as the primary displayed price

### Requirement 7: Show Price and Annual Option in Upgrade Dialog

**User Story:** As a free user encountering an upgrade prompt, I want to see the price and subscribe directly from the dialog, so that I can convert without navigating to a separate page.

#### Acceptance Criteria

1. THE Upgrade_Dialog SHALL display both the monthly price and the annual equivalent price retrieved from the Subscription_Context
2. THE Upgrade_Dialog SHALL include a "Subscribe Now" button that initiates a Stripe checkout session for the annual plan
3. WHEN a user clicks "Subscribe Now" in the Upgrade_Dialog, THE Billing_Service SHALL create a checkout session with the annual Stripe price ID and redirect the user to Stripe
4. THE Upgrade_Dialog SHALL label the dismiss action "Remind Me Later" instead of "Maybe Later"
5. WHEN a user clicks "Remind Me Later", THE Upgrade_Dialog SHALL store a flag in localStorage indicating the user deferred the upgrade
6. THE Upgrade_Dialog SHALL continue to include the "Upgrade to Premium" button that navigates to the Pricing_Page for users who want to compare plans

### Requirement 8: Conversation Usage Indicator on Dashboard

**User Story:** As a free user, I want to see how many conversations I have used this week, so that I understand my remaining usage and the value of upgrading.

#### Acceptance Criteria

1. THE SSM_Plan_Definition for the free plan SHALL include a `conversationsPerWeek` field set to 3
2. THE SSM_Plan_Definition for the premium plan SHALL include a `conversationsPerWeek` field set to -1 (unlimited)
3. WHEN a conversation starts in the WebSocket_Handler, THE WebSocket_Handler SHALL increment a `conversationsThisWeek` counter on the user's subscription record in UserSubscriptionsDB
4. THE WebSocket_Handler SHALL store a `weekResetDate` field on the subscription record indicating the Monday of the current ISO week
5. WHEN the current date is past the stored `weekResetDate`, THE WebSocket_Handler SHALL reset `conversationsThisWeek` to 0 and update `weekResetDate` to the current week's Monday before incrementing
6. THE Billing_Lambda status endpoint SHALL return `conversationsThisWeek`, `weekResetDate`, and `conversationsPerWeek` in the subscription status response
7. THE Subscription_Context SHALL expose `conversationsThisWeek`, `weekResetDate`, and `conversationsPerWeek` to consuming components
8. WHILE a free user is on the Dashboard, THE Dashboard SHALL display a usage indicator showing "{used} of {limit} conversations used this week"
9. WHILE a premium user is on the Dashboard, THE Dashboard SHALL not display the usage indicator

### Requirement 9: Re-engagement for Non-Converting Pricing Page Visitors

**User Story:** As a free user who visited the pricing page but did not subscribe, I want to receive a discount offer on my next visit, so that I am incentivized to convert.

#### Acceptance Criteria

1. WHEN a free user visits the Pricing_Page, THE Pricing_Page SHALL record the visit timestamp in localStorage
2. WHEN a free user visits the Pricing_Page for the second or subsequent time and has not subscribed, THE Pricing_Page SHALL display a banner offering 20% off with the code COMEBACK20
3. THE COMEBACK20_Coupon SHALL be defined in SSM at `/soulreel/coupons/COMEBACK20` as a percentage coupon with 20% off
4. WHEN a subscribed user visits the Pricing_Page, THE Pricing_Page SHALL not display the COMEBACK20 banner
5. WHEN a user who has not previously visited the Pricing_Page arrives for the first time, THE Pricing_Page SHALL not display the COMEBACK20 banner

### Requirement 10: Relocate Trust Messaging on Pricing Page

**User Story:** As a user evaluating plans, I want to see trust messaging near the plan cards, so that I feel reassured about data ownership while making my decision.

#### Acceptance Criteria

1. THE Pricing_Page SHALL display Trust_Messaging with a shield icon directly below the plan comparison grid
2. THE Pricing_Page SHALL not display the current bottom gray trust section as a separate element
3. THE Trust_Messaging SHALL contain the existing copy: recordings, transcripts, and summaries remain accessible regardless of plan; benefactors keep access; Premium unlocks new content without restricting existing content
