# Pricing Conversion Optimization — Session Summary

**Date**: April 18, 2026
**Commits**: `9c8d7bf`, `9e8edb6`
**Branch**: master
**Spec**: `.kiro/specs/pricing-conversion-optimization/`

---

## What Was Done

Implemented 10 marketing/conversion optimization improvements across the SoulReel stack, plus an Admin UI Coupons page. The project started with an expert review of the existing pricing strategy and evolved into a full spec-driven implementation.

---

## Strategy

The optimization targets three stages of the user journey:

1. **Get people to try it**: Redesigned Home page to sell the actual experience (AI conversations, sharing with loved ones), clarified dual CTAs, extended trial from 7 to 14 days.
2. **Show value during trial**: Free users can preview one question from each locked category, Dashboard shows weekly conversation usage ("2 of 3 used"), trial warnings appear earlier (5 days vs 3).
3. **Convert to paid**: Pricing page defaults to annual billing, shows social proof and anchoring, upgrade dialog includes prices and direct checkout, returning visitors see a 20% off banner.

---

## Changes by File

### Frontend (7 files modified, 1 created)

| File | Changes |
|---|---|
| `Home.tsx` | Product-specific "How It Works" steps, sample questions section, testimonial placeholder, CTA subtitles + primary/secondary styling, pricing leads with annual price |
| `PricingPage.tsx` | Default to annual billing, "Best Value" badge, "Recommended" badge, anchoring text, trust messaging relocated with shield icon, social proof section, COMEBACK20 re-engagement banner |
| `Dashboard.tsx` | Trial nudge at 5 days, "Try 1 free question" badges on locked cards, weekly conversation usage indicator for free users |
| `UpgradePromptDialog.tsx` | Shows both prices, "Subscribe Now" button for direct Stripe checkout, "Remind Me Later" with localStorage flag |
| `Header.tsx` | Trial indicator threshold changed from 3 to 5 days |
| `SubscriptionContext.tsx` | Added `previewQuestions`, `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek` |
| `billingService.ts` | Added `previewQuestions`, `conversationsPerWeek` to `PlanLimits`; added usage fields to `SubscriptionStatus` |
| `AdminCoupons.tsx` | **New file** — Coupons reference table in Admin UI at `/admin/coupons` |

### Backend (5 files modified, 1 created)

| File | Changes |
|---|---|
| `plan_check.py` | Preview question support: `_has_completed_preview()` helper, `previewQuestions` check before deny, SSM CLI commands documented |
| `billing/app.py` | Status endpoint returns `conversationsThisWeek`, `weekResetDate`, `conversationsPerWeek` |
| `postConfirmation/app.py` | Trial duration changed from `timedelta(days=7)` to `timedelta(days=14)` |
| `wsDefault/app.py` | `_increment_weekly_conversation_count()` with atomic DynamoDB conditional updates, called after plan check passes |
| `template.yml` | Added `dynamodb:UpdateItem` to WebSocketDefaultFunction policy for UserSubscriptionsTable |
| `test_plan_check_preview.py` | **New file** — 10 unit tests for preview question logic |

### Infrastructure (AdminLayout.tsx, App.tsx)

- Added "BILLING" section to admin sidebar with Coupons nav item
- Added `/admin/coupons` route

---

## Coupon Codes

| Code | Type | Discount | Duration | Audience |
|---|---|---|---|---|
| `COMEBACK20` | Percentage | 20% off | 3 months | Returning pricing page visitors (auto-banner) |
| `LiveInDidcotFree` | Forever free | Lifetime Premium | Permanent | Family members (manual) |
| `TRY14` | Time-limited | Free Personal | 14 days | Launch campaign |
| `SENIORLIVING30` | Time-limited | Free Family | 30 days | Retirement community partnership |
| `HALFOFF3` | Percentage | 50% off | 3 months | Social media campaign |
| `WINBACK-*` | Percentage | 50% off | 1 month | Auto-generated for expired trial users |

---

## Manual Steps Required Before Go-Live

### 1. Deploy backend
```bash
cd SamLambda
sam build && sam deploy --no-confirm-changeset
```
This deploys the IAM change (UpdateItem permission), 14-day trial, conversation counter, and billing status enhancements.

### 2. Update SSM plan definitions

First, find real question IDs for the preview questions:
```bash
# Find a Life Events question ID
aws dynamodb scan --table-name allQuestionDB \
  --filter-expression "begins_with(questionId, :prefix)" \
  --expression-attribute-values '{":prefix": {"S": "life_events"}}' \
  --projection-expression "questionId" --max-items 5

# Find a Values & Emotions question ID
aws dynamodb scan --table-name allQuestionDB \
  --filter-expression "begins_with(questionId, :prefix)" \
  --expression-attribute-values '{":prefix": {"S": "psych"}}' \
  --projection-expression "questionId" --max-items 5
```

Then update the free plan (replace placeholder IDs with real ones):
```bash
aws ssm put-parameter --name "/soulreel/plans/free" --type String --overwrite --value '{
  "planId": "free",
  "allowedQuestionCategories": ["life_story_reflections_L1"],
  "maxBenefactors": 2,
  "accessConditionTypes": ["immediate"],
  "features": ["basic"],
  "previewQuestions": ["<REAL_LIFE_EVENTS_ID>", "<REAL_PSYCH_ID>"],
  "conversationsPerWeek": 3
}'
```

Update the premium plan:
```bash
aws ssm put-parameter --name "/soulreel/plans/premium" --type String --overwrite --value '{
  "planId": "premium",
  "allowedQuestionCategories": ["life_story_reflections", "life_events", "psych_values_emotions"],
  "maxBenefactors": -1,
  "accessConditionTypes": ["immediate", "time_delayed", "inactivity_trigger", "manual_release"],
  "features": ["basic", "dead_mans_switch", "pdf_export"],
  "conversationsPerWeek": -1
}'
```

### 3. Create COMEBACK20 coupon

SSM:
```bash
aws ssm put-parameter --name "/soulreel/coupons/COMEBACK20" --type String --value '{
  "code": "COMEBACK20",
  "type": "percentage",
  "percentOff": 20,
  "durationMonths": 3,
  "stripeCouponId": "COMEBACK20",
  "maxRedemptions": 0,
  "currentRedemptions": 0,
  "expiresAt": null,
  "createdBy": "system-config"
}'
```

Stripe Dashboard: Create coupon with ID `COMEBACK20`, 20% off, repeating, 3 months.

---

## Design Decisions & Critique Notes

During the design review, several issues were caught and fixed before implementation:

1. **IAM gap**: wsDefault only had `dynamodb:GetItem` on UserSubscriptionsTable — needed `UpdateItem` for the conversation counter. The original design incorrectly claimed no IAM changes were needed.
2. **Preview question IDs were fabricated**: The design used placeholder IDs that don't exist in `allQuestionDB`. Fixed to require real IDs queried at deploy time.
3. **Race condition in counter**: The original get-then-update pattern could lose counts under concurrent requests. Replaced with conditional DynamoDB updates using `ConditionExpression`.
4. **plan_check.py had no reference to userQuestionStatusDB**: Added `_QUESTION_STATUS_TABLE` variable and `_has_completed_preview()` helper.
5. **UpgradePromptDialog needed Stripe price ID**: Specified it uses `VITE_STRIPE_ANNUAL_PRICE_ID` env var (same as PricingPage).
6. **Family coupon was `LiveInDidcotFree`**, not `FAMILY2026` as originally documented. Found in chat history from April 11.

---

## Testing

- All 61 frontend tests pass (`npx vitest --run`)
- 10 new backend unit tests for preview question logic
- No TypeScript diagnostics on any modified file
- 2 pre-existing test suite failures (missing `VITE_API_BASE_URL` env var) — unrelated

---

## Spec Files

- `.kiro/specs/pricing-conversion-optimization/requirements.md` — 10 requirements with user stories and acceptance criteria
- `.kiro/specs/pricing-conversion-optimization/design.md` — Architecture, components, data models, 9 correctness properties, error handling
- `.kiro/specs/pricing-conversion-optimization/tasks.md` — 11 top-level tasks across 6 phases with checkpoints
