# Landing Page Redesign & Email Capture Nurture System
**Date:** April 19, 2026
**Session Duration:** Extended session (~8 hours)

---

## Overview

This session covered three major feature areas for SoulReel, progressing from UX evaluation through full implementation and live testing. The work spanned the entire stack: React frontend, AWS SAM backend (Lambda, DynamoDB, SES, SNS, CloudFront), and admin UI.

---

## Feature 1: Landing Page UX Redesign (Spec: `landing-page-ux-redesign`)

### What was done
Starting from a UX evaluation of the existing landing page (two screenshots provided), the page was redesigned with these changes:

- **Two-column hero section** with a video embed placeholder (16:9 aspect ratio, ready for a HeyGen avatar video the user plans to create)
- **Revertible warm accent color** system — amber/gold (#B45309) for primary CTAs with a single `USE_WARM_ACCENT` boolean toggle in `colorConfig.ts` to revert to purple
- **Step numbers** on How It Works cards (1, 2, 3)
- **Stronger testimonials** — card layout with avatar placeholders and names (later replaced by founder story)
- **Closing CTA section** replacing inline pricing — "Ready to preserve your story?" with links to /pricing and signup
- **Trust/privacy signal strip** — encryption, data ownership, no third-party sharing icons
- **Mobile spacing fixes** — reduced padding on small screens, py-12 hero on mobile
- **Enhanced sample questions** with hover animations and left border accent
- **Footer privacy link** to /your-data

### Architecture
Extracted 11 components under `FrontEndCode/src/components/landing/`: VideoEmbed, HeroSection, HowItWorksCard, HowItWorksSection, SampleQuestionCard, SampleQuestionsSection, TestimonialCard, TestimonialSection, ClosingCTASection, TrustStrip, colorConfig. Home.tsx went from ~180 lines of inline JSX to ~90 lines of clean component composition.

### Files created/modified
- 11 new files in `FrontEndCode/src/components/landing/`
- Modified `FrontEndCode/src/pages/Home.tsx`
- Modified `FrontEndCode/tailwind.config.ts` (added warmAccent colors)

---

## Feature 2: Landing Page UX Polish (Spec: `landing-page-ux-polish`)

### What was done
Building on the redesign, 16 additional UX and conversion optimization enhancements were implemented:

1. **Sticky header** (landing page + dashboard) with frosted glass effect (`bg-white/95 backdrop-blur-sm`)
2. **Warmer copy** for How It Works step 2: "Just Talk — We'll Listen" replacing "Have an AI-Guided Conversation"
3. **Ease-of-use + device compatibility strip** — "No typing required" + "Works on computer, tablet, or phone"
4. **Modal signup overlay** — clicking "Start Free" or "Start Their Legacy" opens a dialog instead of navigating away. Shared form components extracted for reuse.
5. **Expandable How It Works cards** — accordion-style with placeholder screenshots, "Learn more" affordance, smooth animation
6. **Logo simplification** — removed the purple circle with "SR" initials, now wordmark-only with conditional gradient/white rendering
7. **Discover page** (`/discover`) — new public deep-dive page with content paths, conversation flow, security/privacy, device compatibility, persona cards ("For You" / "For Someone You Love"), floating CTA with IntersectionObserver, SEO meta tags
8. **Enhanced sample questions subtitle** — "Three paths to explore: your life story, the events that shaped you, and the values you hold dear."
9. **Enhanced legacy choice page** — descriptions under each signup option + "Learn more" link
10. **"No credit card required"** micro-copy under hero CTAs
11. **Micro social proof** — "Join families already preserving their stories" below CTAs
12. **Founder story section** — real founder story replacing fabricated testimonials (bourbon tasting, father's 80th birthday)
13. **Emotional urgency copy** — "Every day holds stories worth preserving. Don't wait for someday."
14. **Email capture section** — "Not ready yet? Get a free sample question delivered to your inbox."
15. **Analytics event tracking** — `trackEvent` utility with 14+ tracked interactions
16. **Secondary email capture** after founder story — "Moved by this story?"

### Additional fixes
- **Warmer CTA copy (Option D)**: "Preserve your first memory →" and "Help Them Preserve Theirs" replacing transactional language
- **Signup modal explanation** for "Start Their Legacy" — 3-step visual explainer (create account → invite loved one → watch stories)
- **COMEBACK20 timing bug fix** — now requires 24 hours between first visit and banner display
- **COMEBACK20 text clarification** — "20% off your first 3 months of Premium"
- **Pricing page billing toggle fix** — "Best Value" badge moved inside the Annual button

### Architecture
- New shared form components: `CreateLegacyFormFields.tsx`, `StartTheirLegacyFormFields.tsx`
- New components: `EaseOfUseStrip`, `MicroSocialProof`, `FounderStorySection`, `EmailCaptureSection`, `SignupModal`, `SecondaryEmailCapture`
- New page: `Discover.tsx` with 7 sections + floating CTA
- Analytics utility: `FrontEndCode/src/lib/analytics.ts`

---

## Feature 3: Email Capture & Nurture System (Spec: `email-capture-nurture`)

### What was done
A complete full-stack email capture and nurture system with 16 requirements:

**Backend (AWS SAM):**
- **5 new Lambda functions**: EmailCapture, Unsubscribe, NurtureScheduler, SesEventTracking, AdminEmailCapture
- **2 new DynamoDB tables**: EmailCaptureDB (with StatusIndex and CapturedWeekIndex GSIs), EmailCaptureRateLimitDB (with TTL)
- **12 SES email templates** (stages 0-5, A/B variants) deployed via `deploy_nurture_templates.py` script
- **SES Configuration Set** (`soulreel-nurture`) with custom tracking domain
- **CloudFront distribution** for `track.soulreel.net` with ACM SSL certificate — proper HTTPS click/open tracking
- **SNS topic** (`soulreel-ses-nurture-events`) for SES event fan-out to tracking Lambda
- **4 SSM parameters**: schedule intervals, pause flag, unsubscribe secret, disposable domain blocklist
- **Conversion tracking** integrated into existing PostConfirmation Cognito trigger
- **Rate limiting** (5 requests per IP per hour) with atomic DynamoDB operations
- **Disposable email domain blocking**

**Email Nurture Sequence:**
- Stage 0 (immediate): Welcome email with sample question
- Stage 1 (7 days): Founder story + question
- Stage 2 (14 days): Social proof + question
- Stage 3 (28 days): Urgency + question
- Stage 4 (56 days): Final + COMEBACK20 coupon
- Stage 5 (6 months): Win-back with generous incentive
- A/B variant support (random assignment on capture, consistent across stages)
- Two-pass scheduler: active records (stages 0-4) + win-back candidates (expired, 180+ days)

**Frontend:**
- EmailCaptureSection with real API integration, loading states, error handling
- SecondaryEmailCapture after founder story
- HeroSection auto-open signup modal from `?signup=` query parameter (for email CTA links)
- Home.tsx referral hash tracking from `?ref=` parameter
- Full admin page (`/admin/email-capture`) with metrics cards, funnel visualization, email table, A/B test results, nurture configuration panel, referral stats
- Admin dashboard summary card with mini funnel indicator
- Admin sidebar "MARKETING" section

**Tracking & Analytics:**
- SES open tracking (tracking pixel)
- SES click tracking via `track.soulreel.net` → CloudFront → `awstrack.me`
- Per-stage open/click tracking in DynamoDB (`stageOpens`, `stageClicks` map attributes)
- Bounce handling (hard bounce → mark undeliverable, soft bounce → retry once then escalate)
- Referral tracking via email footer share links
- Unsubscribe via HMAC-signed tokens

### Infrastructure setup (manual steps performed during session)
- Created ACM certificate for `track.soulreel.net`
- Created CloudFront distribution (`E2KK54J5TQQ9UE`) with ACM cert and `awstrack.me` origin
- Created Route 53 A alias record pointing `track.soulreel.net` to CloudFront
- Created 4 SSM parameters
- Deployed 12 SES templates via script
- Added `soulreel-ses-sns-deploy` IAM inline policy to GitHub Actions OIDC role (ses:*, sesv2:*, sns:*)

### Bugs fixed during testing
- DynamoDB reserved keyword `source` — escaped with ExpressionAttributeNames
- SES template Handlebars syntax — fixed f-string brace escaping in CTA button
- Unsubscribe URL using empty `VITE_API_BASE_URL` — changed to `API_BASE_URL` env var with API Gateway URL
- SES click tracking SSL certificate mismatch — set up CloudFront with ACM certificate
- CloudFormation SES v1 event destination bug — switched to SES v2 resource types
- GitHub Actions IAM permissions — added SES/SNS management permissions to OIDC role

---

## Specs Created

| Spec | Requirements | Design | Tasks | Status |
|------|-------------|--------|-------|--------|
| `landing-page-ux-redesign` | 9 requirements | Full design with 4 properties | 12 tasks | Implemented & deployed |
| `landing-page-ux-polish` | 16 requirements | Full design with 8 properties | 19 tasks | Implemented & deployed |
| `email-capture-nurture` | 16 requirements | Full design with 19 properties | 19 tasks | Implemented & deployed |

---

## Testing Verified

- Email capture API (POST /email-capture) — 200 success ✓
- Welcome email delivery via SES ✓
- Click tracking via track.soulreel.net → CloudFront → awstrack.me ✓
- Open tracking via SES pixel ✓
- DynamoDB record creation with correct defaults ✓
- Unsubscribe flow (HMAC token → branded HTML page → DynamoDB update) ✓
- Landing page email capture form ✓
- Admin dashboard Email Capture card ✓
- Admin Email Capture management page ✓
- Validation (bad email, empty email) ✓
