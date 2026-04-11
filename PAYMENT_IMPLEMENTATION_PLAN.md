# SoulReel — Phased Payment Implementation Plan

**Date**: March 30, 2026  
**Focus**: Stripe integration, subscription UX, and conversion-optimized UI placement  
**Principle**: Never clutter. Always earn the upgrade moment.

---

## Philosophy: The Invisible Paywall

SoulReel's payment system should feel like a natural extension of the product, not a gate bolted onto it. The best SaaS conversion patterns follow a rule: **the user should hit the paywall at the exact moment they've proven the product's value to themselves.** Not before. Not after.

Every upgrade prompt in this plan is tied to a moment where the user has already received value and wants more. No pop-ups on first login. No banners screaming "UPGRADE NOW" on the dashboard. The product sells itself through usage — the payment system just catches the overflow.

---

## Phase A: Foundation (Backend + Stripe Wiring)
**Timeline: 5-7 days | No visible UI changes yet**

This phase is invisible to users. You're laying pipe.

### A.1 — DynamoDB: UserSubscriptionsTable

Add to `template.yml`. Schema per the existing plan doc. Every user defaults to `free` — no record needed until they interact with billing (lazy initialization).

### A.2 — Stripe Account Setup

1. Create Products & Prices in Stripe Dashboard:
   - Personal: $12.99/mo (`price_personal_monthly`) / $99/yr (`price_personal_annual`)
   - Family: $19.99/mo (`price_family_monthly`) / $179/yr (`price_family_annual`)
   - Legacy Vault: $29.99/mo (`price_vault_monthly`) / $249/yr (`price_vault_annual`)
2. Store keys in SSM (`/soulreel/stripe/secret-key`, `/soulreel/stripe/webhook-secret`, `/soulreel/stripe/publishable-key`)
3. Create Stripe webhook pointing to your API Gateway endpoint

### A.3 — Lambda Functions

Deploy per the existing plan:
- `BillingFunction` (checkout, portal, status, coupon)
- `StripeWebhookFunction` (event processing)
- `StripeDependencyLayer` (stripe Python SDK)
- `WeeklyUsageResetFunction` (EventBridge Monday cron)
- `CouponExpirationFunction` (EventBridge daily cron)

### A.4 — SSM Plan Definitions + Family Coupon

Create the plan limit parameters and your `FAMILY2026` forever-free coupon immediately.

### A.5 — Billing Status Service (Frontend)

Create `FrontEndCode/src/services/billingService.ts`:
- `getBillingStatus()` → `GET /billing/status`
- `createCheckoutSession(priceId)` → `POST /billing/create-checkout-session`
- `getPortalUrl()` → `GET /billing/portal`
- `applyCoupon(code)` → `POST /billing/apply-coupon`

Create `FrontEndCode/src/hooks/useBillingStatus.ts`:
- Fetches billing status on mount, caches in React Query
- Exposes: `planId`, `status`, `limits`, `usage`, `isFreePlan`, `isPaidPlan`
- This hook will be consumed by every component that needs plan awareness

**Deploy checkpoint**: Backend fully functional. No user-facing changes. Test with curl and Stripe test mode.

---

## Phase B: The Pricing Page
**Timeline: 3-4 days | First visible payment UI**

### B.1 — Route: `/pricing`

Add to `App.tsx` as a **public route** (no auth required). Unauthenticated visitors see the plans with a "Sign Up Free" CTA. Authenticated users see their current plan highlighted.

### B.2 — UX Design: The Pricing Page

This is your primary conversion surface. It needs to do three things:
1. Communicate value (what do I get?)
2. Create urgency (why now?)
3. Reduce friction (how easy is it?)

**Layout — Desktop (3-column + 1 highlighted)**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   "Choose the plan that protects your legacy"                       │
│   Toggle: [Monthly] / [Annual — Save up to 30%]                    │
│                                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐       │
│  │  FREE    │  │  PERSONAL ★  │  │  FAMILY  │  │  VAULT   │       │
│  │          │  │  Most Popular │  │          │  │          │       │
│  │  $0      │  │  $12.99/mo   │  │ $19.99/mo│  │$29.99/mo │       │
│  │          │  │  $99/yr      │  │ $179/yr  │  │$249/yr   │       │
│  │          │  │              │  │          │  │          │       │
│  │ 3 convos │  │ Unlimited    │  │ Unlimited│  │Unlimited │       │
│  │ 5 GB     │  │ 100 GB       │  │ 500 GB   │  │ 2 TB     │       │
│  │ 2 people │  │ 5 people     │  │ 15 people│  │Unlimited │       │
│  │          │  │ Dead man's   │  │ Priority │  │ Avatar   │       │
│  │          │  │ switch       │  │ AI       │  │ (coming) │       │
│  │          │  │ PDF export   │  │          │  │          │       │
│  │          │  │              │  │          │  │          │       │
│  │[Current] │  │[Subscribe →] │  │[Choose →]│  │[Choose →]│       │
│  └──────────┘  └──────────────┘  └──────────┘  └──────────┘       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Have a coupon code?  [____________] [Apply]                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  "Your stories are encrypted, never used for AI training,          │
│   and only accessible to people you choose."                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Layout — Mobile (stacked cards, Personal first)**:

On mobile, show Personal plan first (not Free). The user scrolled to pricing — they're interested. Lead with value. Free plan goes last as a "or start free" fallback.

**Key UX decisions**:

1. **Annual toggle defaults to ON**: Show annual pricing by default. The monthly price appears as smaller text below ("or $12.99/month"). Annual plans have lower churn and higher LTV. The "Save up to 30%" badge on the toggle creates immediate anchoring.

2. **"Most Popular" badge on Personal**: Social proof. Even if you don't have data yet, this guides the eye and reduces decision paralysis. Personal is the right default recommendation — it's the plan where the dead man's switch unlocks, which is the emotional hook.

3. **Feature rows use emotional language, not technical**:
   - Don't say "100 GB storage" — say "100 GB — room for hundreds of conversations"
   - Don't say "5 benefactor seats" — say "Share with up to 5 family members"
   - Don't say "All 4 access condition types" — say "Control exactly when your family receives your stories"
   - Don't say "Dead man's switch" — say "Automatic legacy release if you become inactive"

4. **Coupon input is subtle**: A single-line text input below the plan cards. Not a modal, not a separate page. Just: "Have a coupon code?" with a text field and Apply button. This serves your family coupons and promotional codes without cluttering the main flow.

5. **Trust signal at the bottom**: One line about encryption and privacy. Not a wall of text. Just enough to address the "but my stories are personal" objection.

6. **No feature comparison matrix**: Avoid the giant checkbox grid. It's overwhelming and makes the free plan look "good enough." Instead, each card lists its 4-5 most compelling features. The paid plans list what they ADD, not what free lacks.

### B.3 — Stripe Checkout Flow

When a user clicks "Subscribe" on a paid plan:
1. If not authenticated → redirect to `/signup` with `?redirect=/pricing&plan=personal`
2. If authenticated → call `createCheckoutSession(priceId)` → redirect to Stripe Checkout
3. Stripe Checkout handles card entry, Apple Pay, Google Pay
4. On success → redirect to `/dashboard?checkout=success` → show a one-time toast: "Welcome to Personal. Your legacy just got an upgrade."
5. On cancel → redirect to `/pricing?checkout=canceled` → no message, just back to pricing

**Do not build a custom payment form.** Stripe Checkout is PCI-compliant, supports Apple/Google Pay, handles 3D Secure, and converts better than any custom form you'd build. Let Stripe do what Stripe does.

### B.4 — Navigation: Where Does Pricing Live?

**On the public Home page (`/`)**:
- Add "Pricing" to the header nav, between the logo and Login/Sign Up buttons
- Add a pricing section BELOW the "How It Works" section on the home page itself (anchor link `/#pricing`). This is a condensed version — just the 4 plan cards with prices and a "See full details" link to `/pricing`

**On authenticated pages (Dashboard, etc.)**:
- Do NOT add "Pricing" to the main header. It clutters the authenticated experience.
- Pricing is accessible via: UserMenu → "Manage Plan" (see Phase C)

---

## Phase C: Plan Awareness in the Authenticated Experience
**Timeline: 2-3 days | Subtle, contextual, never intrusive**

This is where marketing psychology meets product design. The goal: make the user aware of their plan without making them feel restricted.

### C.1 — UserMenu: "Manage Plan" Item

Add a new menu item to `UserMenu.tsx` in the Navigation Section, between "Question Themes" and "Security & Privacy":

```
┌──────────────────────────────────┐
│  🎨 Question Themes              │
│  👥 Manage Benefactors           │
│  ✨ Free Plan — Upgrade          │  ← NEW (only for free users)
│  ✨ Personal Plan — Manage       │  ← NEW (only for paid users)
│  🛡️ Security & Privacy           │
│  ⚙️ Settings          Coming Soon │
│  ─────────────────────────────── │
│  🚪 Log Out                      │
└──────────────────────────────────┘
```

**For free users**: Icon is a subtle sparkle (✨ or Zap from lucide). Text: "Free Plan" with a small "Upgrade" label in legacy-purple. Clicking navigates to `/pricing`.

**For paid users**: Same icon. Text: "{Plan Name} Plan" with "Manage" label. Clicking calls `getPortalUrl()` and redirects to Stripe Customer Portal (where they can change plans, update payment, cancel).

**Why this placement**: It's discoverable but not aggressive. The user sees their plan status every time they open the menu, which creates ambient awareness. The "Upgrade" text is a gentle nudge, not a shout.

### C.2 — Dashboard: Usage Context Bar

On the Dashboard page, add a thin contextual bar below the Header and above the main content. This is NOT a banner ad. It's a usage indicator.

**For free users**:

```
┌─────────────────────────────────────────────────────────────────┐
│ Free Plan · 2 of 3 conversations this week · 1.2 GB of 5 GB    │
│                                              [See Plans →]      │
└─────────────────────────────────────────────────────────────────┘
```

- Light gray background (`bg-gray-50`), small text (`text-sm`), single line
- "See Plans →" is a text link, not a button. Understated.
- When usage is at 0/3, don't show this bar at all. Only show it once the user has started using their quota (they've proven value to themselves)
- When usage is at 2/3 or 3/3, the text shifts to amber: "1 conversation remaining this week"
- When at 3/3: "You've used all 3 conversations this week. Resets Monday. [Upgrade for unlimited →]"

**For paid users**:

Don't show this bar at all. Paid users shouldn't feel metered. If they're on a plan with storage limits and approaching 80%, show a subtle storage indicator — but only then.

**Why this works**: It uses the "progress toward a limit" pattern that Dropbox, Slack, and Notion all use. The user sees their consumption naturally, which creates two effects:
1. Scarcity awareness ("I only have 1 left") drives urgency
2. Usage visibility ("I've used 2 this week") reinforces the product's value ("I'm actually using this")

### C.3 — Conversation Start: Limit Gate

When a free user tries to start a conversation and has hit their weekly limit, the WebSocket will return a `limit_reached` message. Handle this in `ConversationInterface.tsx`:

**Do NOT show a generic error.** Show a purpose-built upgrade moment:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│        You've had 3 great conversations this week.          │
│                                                             │
│   Your stories are worth more than 3 a week.                │
│   Upgrade to Personal for unlimited conversations           │
│   and features like automatic legacy release.               │
│                                                             │
│        [Upgrade to Personal — $99/year]                     │
│                                                             │
│   or wait until Monday when your free conversations reset   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key details**:
- Positive framing: "You've had 3 great conversations" not "You've hit your limit"
- Value proposition in the prompt: mention the dead man's switch ("automatic legacy release") — this is the feature that converts
- Show the annual price, not monthly. $99/year feels like a decision. $12.99/month feels like a subscription
- Always offer the free alternative ("wait until Monday"). Never make the user feel trapped. Forced upgrades create resentment; chosen upgrades create loyalty

### C.4 — Benefactor Limit Gate

When a legacy maker tries to invite a 3rd benefactor on the free plan, show in `ManageBenefactors.tsx`:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Your free plan includes 2 benefactors.                    │
│                                                             │
│   Want to share your legacy with more family members?       │
│   Personal includes 5 seats. Family includes 15.            │
│                                                             │
│        [See Plans]          [Maybe Later]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- "Maybe Later" dismisses the dialog. No guilt. No countdown timer. No dark patterns.
- "See Plans" navigates to `/pricing`

### C.5 — Storage Limit Gate

When a user approaches 80% of their storage quota, show a subtle inline notice on the Dashboard (not a modal):

```
Storage: 4.1 GB of 5 GB used · [Upgrade for more space →]
```

When they hit 100% and try to record/upload:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   You've filled your 5 GB of story storage.                 │
│   That's a lot of memories — nice work.                     │
│                                                             │
│   Upgrade to keep recording. Personal gives you 100 GB     │
│   — room for years of conversations.                        │
│                                                             │
│        [Upgrade]            [Maybe Later]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase D: Home Page Pricing Integration
**Timeline: 1-2 days | Marketing surface**

### D.1 — Pricing Section on Home Page

Add a new section to `Home.tsx` between "How It Works" and the footer:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│          Start free. Upgrade when you're ready.             │
│                                                             │
│  ┌────────────┐  ┌────────────────┐  ┌────────────┐       │
│  │   FREE     │  │  PERSONAL ★    │  │   FAMILY   │       │
│  │   $0       │  │  $8.25/mo      │  │  $14.92/mo │       │
│  │            │  │  billed yearly  │  │  billed    │       │
│  │ 3 convos/  │  │                │  │  yearly    │       │
│  │ week       │  │ Unlimited      │  │            │       │
│  │ 2 family   │  │ convos         │  │ 15 family  │       │
│  │ members    │  │ 5 family       │  │ members    │       │
│  │            │  │ members        │  │ Priority   │       │
│  │            │  │ Legacy release │  │ AI         │       │
│  │            │  │                │  │            │       │
│  │[Start Free]│  │[Start Free →]  │  │[Start Free]│       │
│  └────────────┘  └────────────────┘  └────────────┘       │
│                                                             │
│         All plans start with a free account.                │
│         No credit card required.                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key differences from the full `/pricing` page**:
- Only show 3 plans (drop Vault — it's for power users who'll find it on `/pricing`)
- Show annual price as monthly equivalent ("$8.25/mo billed yearly") — lower number, less sticker shock
- ALL CTAs say "Start Free" — even on paid plans. The goal of the home page is signup, not payment. Payment comes after they've experienced the product
- "No credit card required" removes the last objection

### D.2 — Header Nav Update

Add "Pricing" link to the Home page header nav:

```
[Logo]                              [Pricing]  [Log In]  [Sign Up]
```

Only on the public home page. Not on authenticated pages.

### D.3 — Footer Update

Add "Pricing" to the Quick Links in the footer.

---

## Phase E: Post-Checkout Polish
**Timeline: 1-2 days | Delight moments**

### E.1 — Checkout Success Toast

When redirected to `/dashboard?checkout=success`, show a warm toast notification:

```
✨ Welcome to {Plan Name}. Your legacy just got an upgrade.
```

Auto-dismiss after 5 seconds. No modal. No confetti. Just a clean acknowledgment.

### E.2 — Plan Badge in UserMenu

After upgrading, the UserMenu profile section gets a subtle plan indicator:

```
┌──────────────────────────────────┐
│  [Avatar]  Oliver Astley         │
│            oliver@email.com      │
│            ✨ Personal Plan       │  ← subtle, small text
└──────────────────────────────────┘
```

This serves as a quiet status symbol. It also reminds the user they're paying, which paradoxically reduces churn — people who forget they're subscribed are more likely to cancel when they notice the charge. People who see the value reminder stay.

### E.3 — Stripe Customer Portal Access

The "Manage" link in UserMenu (for paid users) opens Stripe's hosted Customer Portal. This handles:
- Plan upgrades/downgrades
- Payment method updates
- Invoice history
- Cancellation

You don't need to build any of this UI. Stripe provides it. Customize the portal branding in Stripe Dashboard to match SoulReel's purple/navy palette.

---

## Phase F: Conversion Optimization (Post-Launch)
**Timeline: Ongoing, after Phases A-E are live**

### F.1 — "Upgrade" Nudge After Conversation Completion

After a user finishes a conversation (the score goal is met, summary is generated), this is the highest-emotion moment in the product. The user just had a meaningful experience. Show a subtle prompt:

```
That was a beautiful conversation about [topic].

You have 1 conversation remaining this week.
[Keep going — upgrade to unlimited →]
```

Only show this for free users. Only when they have ≤1 conversation remaining. The emotional high of completing a conversation + the scarcity of "1 remaining" is the highest-converting moment in the entire product.

### F.2 — Benefactor-to-Maker Conversion

When a benefactor watches a legacy maker's video, show a subtle CTA at the end:

```
Inspired by [Maker's Name]'s stories?
[Create your own legacy — start free →]
```

This is the viral loop. Every benefactor is a potential maker. The emotional context of having just watched a family member's story is the perfect conversion moment.

### F.3 — Email Nudges (Future)

After a free user hits their conversation limit:
- Day 0: No email (they saw the in-app prompt)
- Day 2: "Your conversations reset Monday. In the meantime, here's what Personal unlocks..."
- Day 7 (after reset): "You have 3 new conversations this week. Pick up where you left off."

These require SES integration, which is a separate workstream. Plan for it but don't block the payment launch on it.

### F.4 — Annual Plan Incentive

On the `/pricing` page, when a user selects monthly billing, show a small inline note:

```
$12.99/month  ·  Switch to annual and save $56.88/year →
```

This is the "save X per year" pattern that every SaaS uses because it works. Show the absolute dollar savings, not the percentage — "$56.88" feels more tangible than "36% off."

---

## Implementation Priority Summary

| Phase | What | Days | User Impact |
|-------|------|------|-------------|
| A | Backend + Stripe wiring | 5-7 | None (invisible) |
| B | Pricing page + Stripe Checkout | 3-4 | New `/pricing` route, home page pricing section |
| C | Plan awareness in authenticated UI | 2-3 | Usage bar, limit gates, UserMenu plan item |
| D | Home page pricing integration | 1-2 | Pricing section on landing page, nav link |
| E | Post-checkout polish | 1-2 | Success toast, plan badge, portal access |
| F | Conversion optimization | Ongoing | Nudges, viral loops, email (future) |

**Total to payment-ready: ~12-18 days**

Phases A-D get you to a functional payment system. Phase E polishes it. Phase F optimizes it over time.

---

## What NOT to Build

- **No custom payment form**: Use Stripe Checkout. Period.
- **No plan comparison matrix with 20 rows of checkmarks**: It overwhelms and makes Free look sufficient.
- **No "trial" of paid plans**: The free tier IS the trial. Adding a separate trial creates confusion.
- **No aggressive upgrade modals on login**: The user just opened the app. Let them use it first.
- **No "days remaining" countdown timers**: This is a legacy preservation tool, not a flash sale.
- **No "are you sure?" when they click "Maybe Later"**: Respect the decision. They'll come back.
- **No pricing in the conversation interface itself**: The conversation is sacred space. No ads, no upsells, no distractions while they're recording memories. The only exception is the limit gate (C.3), which only appears when they literally cannot start a new conversation.
