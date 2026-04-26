# SoulReel — Pricing & Cost Analysis: Summary of Findings

**Date**: April 25, 2026

---

## What It Costs to Run

A single AI conversation (4 turns) costs **$0.053** — that's Deepgram transcription, Bedrock Haiku response generation, Nova Micro depth scoring, Polly Neural text-to-speech, S3 storage, and Lambda compute combined. A user who completes all 300 questions costs **$16 total** in AI processing and generates 390 MB of storage that costs under $0.50/year to retain.

At 100 paid users with realistic usage (8 conversations/month average), the fully loaded monthly infrastructure cost — including free user subsidy, security stack, Stripe fees, and all AWS services — is **$148–$234/month** depending on free-tier configuration. Per paid user: **$1.48–$2.34/month**.

The top cost drivers are Stripe payment processing ($32/month), AWS Transcribe for video ($29/month), and the AI conversation engine ($42–$78/month depending on free user volume). Storage is negligible. Security infrastructure (KMS, GuardDuty, CloudTrail, CloudWatch) is a fixed ~$22/month regardless of user count.

Switching video transcription from AWS Transcribe to Deepgram batch saves $24/month. Using Amazon Nova Lite for free-tier conversations saves $55/month. These two changes alone cut costs by a third.

---

## What Free Users Should Get

**Complete Level 1 at any pace, full quality, no compromises.**

Level 1 spans 4 question categories — Childhood Memories, Family & Upbringing, School Days, and Friends — roughly 12–30 questions depending on the database. Users get the same AI model, same Neural voice, same 4 turns per conversation as paid users. No weekly caps. No degraded experience.

The wall hits at the perfect emotional moment. The user has told their easy stories and can see the progression ahead: Level 6 is "Challenges & Hard Times," Level 9–10 is "Messages to Loved Ones." Their Life Events survey is complete and shows "12 personalized questions waiting." The product has shown them the map and said "you've walked the first mile."

Cost per free user who completes Level 1: ~$1.06 one-time. Cost per free user who bounces early: ~$0.10–$0.16. After Level 1, non-converting users cost $0/month — no recurring free-rider drain.

Estimated customer acquisition cost at 3% conversion: **$4–$5 per paid user.**

---

## What Paid Users Should Pay

**$149/year ($14.99/month).**

Not $89.99. Not $199. Here's why.

The competitive landscape clusters at $99/year for products that do far less — StoryWorth (text-only prompts), Remento (voice prompts, no AI interviewing), StoriedLife (AI conversations but text-only, no video, no benefactor controls). Eternos charges $300+/year for AI avatar creation with 10+ hours of setup. SoulReel sits in the gap between these tiers.

$149/year generates **37% more revenue** than $89.99 with only ~17% fewer conversions. The users lost at the higher price are the least committed — the ones who would have churned after month 2 anyway. At 100 paid users, that's $14,900/year vs $8,999.

$149 also creates room for strategic discounting that $89.99 doesn't. Launch at $99 for founding members, raise to $149 with social proof, run $119 holiday promotions, offer $99 win-back deals. Every discount feels generous because the anchor is $149.

A significant portion of purchases will be gifts — adult children buying for aging parents. Gift buyers don't compare to StoryWorth. They compare to "what's Dad's stories worth?" $149 feels like a serious investment in something that matters. $89.99 feels like another subscription.

The power user who completes all 300 questions in month 1 costs $16 in AI processing. At $149/year, that's 89% margin even in the worst case. At $14.99/month, you break even in month 2. No usage caps, no storage fees, no metering needed.

---

## The Numbers at Scale

| Paid Users | Annual Revenue ($149) | Monthly Cost (optimized) | Annual Profit | Margin |
|---|---|---|---|---|
| 50 | $7,450 | $100 | $6,250 | 84% |
| 100 | $14,900 | $156 | $13,028 | 87% |
| 500 | $74,500 | $660 | $66,580 | 89% |
| 1,000 | $149,000 | $1,270 | $133,760 | 90% |

Margins improve with scale because fixed costs (security stack, Amplify hosting, scheduled Lambda jobs) get amortized while per-user variable costs stay flat at ~$0.64/month for average users.

---

## Launch Strategy

1. Soft launch at **$99/year** for the first 100 users — "Founding Member" rate, locked in for life
2. Raise to **$149/year** once testimonials and social proof exist
3. Keep **$99 as the promotional floor** for campaigns, partnerships, and win-back emails
4. Monthly option at **$14.99** always available for users who won't commit annually
5. Never go below $99 — it still has 91% margin and anchors the product above the $99 commodity tier

---

## Supporting Documents

| Document | Contents |
|---|---|
| `SOULREEL_COST_AND_PRICING_REPORT.md` | Full infrastructure cost breakdown, per-service analysis, conversion rate modeling, alternative provider evaluation, optimized cost projections |
| `SOULREEL_FREE_TIER_STRATEGY.md` | Product analysis, 3 free tier options evaluated, "Complete Level 1" recommendation with cost modeling and upgrade prompt design |
| `SOULREEL_PAID_TIER_PRICING.md` | 300-question cost analysis, 3 paid pricing structures evaluated, flat pricing recommendation, post-completion retention analysis |
| `SOULREEL_PRICE_POINT_ANALYSIS.md` | $90 vs $150 vs $200 comparison, competitive landscape, conversion-revenue tradeoff modeling, $149 recommendation with launch strategy |
