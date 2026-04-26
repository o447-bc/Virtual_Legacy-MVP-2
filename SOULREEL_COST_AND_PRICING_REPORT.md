# SoulReel — Comprehensive Cost Analysis & Pricing Report

**Date**: April 19, 2026
**Scope**: Per-100-paid-user AWS infrastructure cost analysis + subscription pricing recommendation
**Methodology**: Bottom-up cost modeling from template.yml, current AWS pricing, and competitor benchmarking

---

## 1. EXECUTIVE SUMMARY

SoulReel is an AI-powered digital legacy platform where users record video responses to life story questions via conversational AI, manage benefactor relationships with conditional access rules, and take psychological assessments. The platform runs entirely on AWS serverless infrastructure with Stripe for payments and Deepgram for real-time transcription.

**Bottom line**: At 100 paid users, the estimated AWS + third-party cost is **$145–$235/month** (or **$1.45–$2.35 per paid user/month**). A monthly subscription of **$9.99/month** or **$89.99/year** provides very healthy margins while remaining competitive in the digital legacy space.

---

## 2. ASSUMPTIONS

### User Behavior Assumptions (per paid user per month)

| Assumption | Value | Rationale |
|---|---|---|
| AI conversations per month | 8 | ~2 per week, premium users are engaged |
| Turns per conversation | 4 | Typical 3–4 turns; using 4 as realistic max |
| Video recordings per month | 4 | Separate from AI conversations |
| Average video length | 3 minutes | Short personal responses |
| Benefactors per user | 3 | Average across plans |
| Benefactor video views per month | 6 | Each benefactor watches ~2 videos/month |
| Psych tests completed per month | 0.5 | Not every user every month |
| Emails sent per user per month | 8 | Welcome, check-ins, nurture, notifications |
| API calls per user per month | 500 | Dashboard loads, question fetches, progress checks |
| WebSocket connection minutes/month | 40 | ~8 conversations × 5 min avg |
| S3 storage growth per month | 80 MB | Audio + video + transcripts (less conversation audio at 4 turns) |
| Cumulative S3 storage at month 6 | 480 MB | Per user |

### Platform Assumptions

| Assumption | Value |
|---|---|
| Total paid users | 100 |
| Free users (non-paying) | 200 (2:1 ratio) |
| Region | us-east-1 |
| All DynamoDB tables | PAY_PER_REQUEST (on-demand) |
| Lambda architecture | Mostly ARM64 (Graviton) |
| Bedrock model (post-optimization) | Claude 3.5 Haiku for conversations, Nova Micro for scoring |
| Deepgram model | Nova-2 |
| Polly voice | Neural (Joanna) |

---

## 3. DETAILED COST BREAKDOWN PER 100 PAID USERS

### 3.1 AI Conversation Engine (DOMINANT COST)

This is the core product loop: user speaks → Deepgram transcribes → Bedrock scores depth → Bedrock generates response → Polly speaks → S3 stores audio.

**Per conversation turn:**

| Component | Service | Unit Cost | Usage per Turn | Cost per Turn |
|---|---|---|---|---|
| Speech-to-text | Deepgram Nova-2 | $0.0043/min | ~0.5 min user speech | $0.0022 |
| Depth scoring | Bedrock Nova Micro | $0.035/$0.14 per 1M tokens | ~500 in / 100 out tokens | $0.00003 |
| Response generation | Bedrock Claude 3.5 Haiku | $0.80/$4.00 per 1M tokens | ~2,000 in / 300 out tokens (growing context) | $0.0028 |
| Text-to-speech | Polly Neural | $16.00/1M chars | ~400 chars response | $0.0064 |
| Audio storage | S3 Standard | $0.023/GB | ~0.5 MB (user + AI audio) | $0.00001 |
| State persistence | DynamoDB | $1.25/1M writes | 2 writes | $0.0000025 |

**Cost per turn: ~$0.012** (post-optimization, down from $0.025–$0.05 with Sonnet)

**Per conversation (4 turns): ~$0.048**
**Plus end-of-conversation summarization (Haiku): ~$0.005** (shorter transcript to summarize)
**Total per conversation: ~$0.053**

**Monthly for 100 paid users (8 conversations each):**

| Item | Calculation | Monthly Cost |
|---|---|---|
| Conversations | 100 users × 8 convos × $0.053 | **$42.40** |

### 3.2 Video Recording & Processing

| Component | Service | Unit Cost | Usage (100 users) | Monthly Cost |
|---|---|---|---|---|
| Video upload/storage | S3 Standard | $0.023/GB | 400 videos × 50 MB avg = 20 GB new/mo | $0.46 |
| Video processing (FFmpeg) | Lambda (1024 MB, 60s) | $0.0000167/GB-s | 400 invocations × 30s avg | $0.20 |
| Transcription | AWS Transcribe | $0.024/min | 400 videos × 3 min = 1,200 min | $28.80 |
| Summarization | Bedrock Haiku | $0.80/$4.00 per 1M | 400 summaries × ~1,500 tokens | $0.80 |
| **Subtotal** | | | | **$30.26** |

### 3.3 Benefactor Video Viewing

| Component | Service | Unit Cost | Usage (100 users) | Monthly Cost |
|---|---|---|---|---|
| S3 GET requests | S3 | $0.0004/1K requests | 600 views × 3 requests each | $0.001 |
| Data transfer out | S3 egress | $0.09/GB | 600 views × 50 MB = 30 GB | $2.70 |
| Presigned URL generation | Lambda (128 MB) | $0.0000021/GB-s | 600 invocations × 1s | $0.0002 |
| **Subtotal** | | | | **$2.70** |

### 3.4 DynamoDB (17+ Tables, On-Demand)

| Operation Type | Unit Cost | Est. Monthly Requests (100 users) | Monthly Cost |
|---|---|---|---|
| Write requests | $1.25/million | ~200,000 (conversations, progress, engagement, subscriptions) | $0.25 |
| Read requests | $0.25/million | ~500,000 (dashboard loads, question fetches, auth checks) | $0.13 |
| Storage | $0.25/GB | ~5 GB across all tables | $1.25 |
| Point-in-time recovery | 20% of storage cost | 5 GB | $0.25 |
| KMS encryption overhead | ~$0.03/10K requests | ~700K requests | $2.10 |
| **Subtotal** | | | **$3.98** |

### 3.5 API Gateway

| Component | Unit Cost | Usage (100 paid + 200 free users) | Monthly Cost |
|---|---|---|---|
| REST API calls | $3.50/million | ~300,000 requests | $1.05 |
| WebSocket messages | $1.00/million | ~70,000 messages | $0.07 |
| WebSocket connection minutes | $0.25/million | ~4,000 minutes (100 users × 40 min) | $0.001 |
| **Subtotal** | | | **$1.12** |

### 3.6 Lambda Compute

| Function Category | Memory | Avg Duration | Monthly Invocations | Monthly Cost |
|---|---|---|---|---|
| WebSocket Default (conversation) | 512 MB | 5s avg | 3,200 (800 convos × 4 turns) | $1.34 |
| Video processing | 1024 MB | 30s | 400 | $2.00 |
| Summarization | 512 MB | 10s | 1,200 (800 convos + 400 videos) | $1.00 |
| Transcription start | 256 MB | 5s | 400 | $0.08 |
| Question/progress functions | 128 MB | 0.5s | 50,000 | $0.53 |
| Scheduled jobs (7 functions) | 256–512 MB | 10s avg | ~210 (hourly + daily + weekly) | $0.18 |
| Billing functions | 256 MB | 2s | 2,000 | $0.17 |
| Admin functions | 256 MB | 2s | 500 | $0.04 |
| Cognito triggers | 128 MB | 1s | 300 (signups) | $0.01 |
| All other functions | 128–256 MB | 1s avg | 10,000 | $0.21 |
| **Subtotal** | | | | **$5.38** |

### 3.7 S3 Storage (Cumulative)

| Bucket | Storage Class | Size at Month 6 | Monthly Cost |
|---|---|---|---|
| virtual-legacy (conversations) | Intelligent-Tiering | ~18 GB | $0.18–$0.41 |
| virtual-legacy (user-responses) | Intelligent-Tiering | ~40 GB | $0.40–$0.92 |
| virtual-legacy (test-audio) | Standard | ~2 GB | $0.05 |
| Audit logs | Glacier (after 30 days) | ~5 GB | $0.02 |
| Retention audit | Standard → Deep Archive | ~1 GB | $0.01 |
| Exports temp | Standard (7-day expiry) | ~0.5 GB | $0.01 |
| **Subtotal (month 6)** | | ~66.5 GB | **$1.62** |

*Note: Storage grows linearly. At month 12 with 100 users, expect ~115 GB → ~$2.50/month.*

### 3.8 Authentication (Cognito)

| Component | Unit Cost | Usage | Monthly Cost |
|---|---|---|---|
| MAUs (300 total users) | Free up to 50,000 MAUs | 300 MAUs | **$0.00** |

### 3.9 Email (SES)

| Component | Unit Cost | Usage | Monthly Cost |
|---|---|---|---|
| Outbound emails | $0.10/1,000 | ~2,400 emails (300 users × 8) | $0.24 |
| Nurture emails (free users) | $0.10/1,000 | ~800 emails | $0.08 |
| **Subtotal** | | | **$0.32** |

### 3.10 Security & Compliance Infrastructure

| Service | Unit Cost | Usage | Monthly Cost |
|---|---|---|---|
| KMS key | $1.00/month per key | 1 CMK | $1.00 |
| KMS API requests | $0.03/10,000 | ~1M requests (encryption/decryption) | $3.00 |
| CloudTrail (data events) | $0.10/100,000 events | ~500,000 events | $0.50 |
| GuardDuty | $4.00/account + $0.80/million events | Base + S3 monitoring | $4.50 |
| CloudWatch Logs | $0.50/GB ingested | ~5 GB logs | $2.50 |
| CloudWatch Metrics | $0.30/metric/month | ~20 custom metrics | $6.00 |
| CloudWatch Alarms | $0.10/alarm | ~5 alarms | $0.50 |
| SNS | $0.50/million requests | ~5,000 notifications | $0.00 |
| EventBridge | $1.00/million events | ~10,000 events | $0.01 |
| **Subtotal** | | | **$18.01** |

### 3.11 Frontend Hosting (Amplify)

| Component | Unit Cost | Usage | Monthly Cost |
|---|---|---|---|
| Build minutes | $0.01/min | ~30 min/month (deploys) | $0.30 |
| Bandwidth | $0.15/GB served | ~15 GB (300 users × 50 MB) | $2.25 |
| Hosting storage | $0.023/GB | ~0.5 GB (static assets) | $0.01 |
| **Subtotal** | | | **$2.56** |

### 3.12 Third-Party Services

| Service | Unit Cost | Usage (100 paid users) | Monthly Cost |
|---|---|---|---|
| Deepgram (real-time transcription) | $0.0043/min | 800 convos × 4 turns × 0.5 min = 1,600 min | $6.88 |
| Stripe processing fees | 2.9% + $0.30/txn | 100 transactions × $9.99 avg | $31.87 |
| Custom domain (Route 53) | $0.50/hosted zone | 1 zone | $0.50 |
| **Subtotal** | | | **$39.25** |

---

## 4. TOTAL MONTHLY COST SUMMARY (100 PAID USERS)

| Category | Monthly Cost | % of Total |
|---|---|---|
| AI Conversation Engine (Bedrock + Deepgram + Polly) | $49.28 | 28.5% |
| Stripe Payment Processing | $31.87 | 18.4% |
| Video Recording & Transcription | $30.26 | 17.5% |
| Security & Compliance (KMS, CloudTrail, GuardDuty, CW) | $18.01 | 10.4% |
| Lambda Compute | $5.38 | 3.1% |
| DynamoDB | $3.98 | 2.3% |
| S3 Storage | $1.62 | 0.9% |
| Data Transfer / Benefactor Viewing | $2.70 | 1.6% |
| Amplify Hosting | $2.56 | 1.5% |
| API Gateway | $1.12 | 0.6% |
| SES Email | $0.32 | 0.2% |
| Cognito | $0.00 | 0.0% |
| Domain / Route 53 | $0.50 | 0.3% |
| **TOTAL** | **$147.60** | **100%** |

**Per paid user per month: ~$1.48** (infrastructure only, excluding Stripe)
**Per paid user per month: ~$1.80** (including Stripe on a $9.99 plan)

*Range estimate: $145–$300/month depending on actual usage intensity. The upper bound assumes power users doing 15+ conversations/month and uploading 8+ videos.*

---

## 5. FIRST CRITIQUE — WHAT THIS ANALYSIS MIGHT UNDERESTIMATE

### 5.1 Issues Identified

1. **CloudWatch Logs are likely underestimated.** With 60+ Lambda functions, each logging to its own log group, log ingestion could easily be 10–20 GB/month at scale, not 5 GB. Revised estimate: $5–$10/month.

2. **KMS costs compound.** Every DynamoDB read/write on an encrypted table triggers KMS API calls. With 17 KMS-encrypted tables and PITR enabled, the actual KMS request volume could be 2–3x higher. Revised: $5–$8/month.

3. **Bedrock conversation context grows per turn.** The $0.0028/turn estimate for Haiku uses an average of 2,000 input tokens, but at 4 turns the context growth is modest. A more accurate per-conversation cost:
   - Turn 1: ~1,000 input tokens → $0.0008/turn
   - Turn 2: ~1,500 input tokens → $0.0012/turn
   - Turn 3: ~2,000 input tokens → $0.0016/turn
   - Turn 4: ~2,500 input tokens → $0.0020/turn
   - **Revised per conversation: ~$0.055** (close to the $0.053 estimate — context growth is minimal at 4 turns)

4. **Free users still cost money.** 200 free users with 3 conversations/week = 2,400 conversations/month. At $0.055 each = $132/month in AI costs alone for non-paying users. Still significant but much less alarming than with 12-turn conversations.

5. **Polly Neural is expensive.** At $16/million characters, Polly is actually the second-largest per-turn cost. The existing cost reduction plan's caching optimization (for question greetings) would help, but follow-up responses are unique.

6. **S3 egress for benefactor viewing scales badly.** If benefactors watch videos frequently, 30 GB/month egress at $0.09/GB is manageable, but at 1,000 users this becomes $27/month. CloudFront would help.

### 5.2 Revised Totals After Critique

| Category | Original | Revised |
|---|---|---|
| AI Conversations (paid users) | $42.40 | $44.00 |
| AI Conversations (free users) | Not counted | $132.00 |
| CloudWatch | $9.00 | $15.00 |
| KMS | $4.00 | $7.00 |
| Everything else | $92.72 | $92.72 |
| **TOTAL** | **$148.12** | **$290.72** |

**The free tier is still a cost concern.** Free users consuming 3 conversations/week generate more AI cost than 100 paid users, though the gap is much smaller at 4 turns per conversation.

---

## 6. UPDATED COST MODEL (POST-CRITIQUE)

### 6.1 Mitigations for Free User Cost

| Mitigation | Impact |
|---|---|
| Reduce free tier to 2 conversations/week (from 3) | Saves ~$44/month |
| Use Nova Micro for free-tier conversations instead of Haiku | Saves ~$105/month |
| Limit free conversations to 3 turns (not 4) | Saves ~$10/month |
| Implement Polly caching for question greetings | Saves ~$5/month |

**Recommended free-tier cost controls:**
- 2 conversations/week, 3-turn max
- Use Nova Micro (or a cheaper model) for free-tier response generation
- Cache Polly audio for question greetings

**With mitigations, free user cost drops from $132 to ~$25–$40/month.**

### 6.2 Revised Cost Model (With Mitigations)

| Category | Monthly Cost |
|---|---|
| AI Conversations (100 paid users, Haiku, 4 turns) | $44.00 |
| AI Conversations (200 free users, mitigated) | $32.00 |
| Video Recording & Transcription | $30.26 |
| Stripe Processing | $31.87 |
| Deepgram | $6.88 |
| Security & Compliance | $22.00 |
| Lambda Compute | $6.00 |
| DynamoDB | $5.00 |
| S3 + Egress | $5.00 |
| Amplify + API Gateway + SES + Cognito | $4.50 |
| **TOTAL** | **$187.51** |

**Per paid user: $1.88/month** (fully loaded, including free user subsidy)

---

## 7. SECOND CRITIQUE — STRESS TESTING THE MODEL

### 7.1 What if users are more active than assumed?

**Power user scenario** (top 20% of users):
- 15 conversations/month (not 8)
- 8 video recordings/month (not 4)
- 5 benefactors viewing 10 videos/month each

20 power users at this rate would add ~$20/month in AI costs and ~$15 in transcription. Total impact: +$35/month.

### 7.2 What about scaling to 500 and 1,000 paid users?

| Metric | 100 Users | 500 Users | 1,000 Users |
|---|---|---|---|
| Paid user AI cost | $44 | $220 | $440 |
| Free user AI cost (mitigated) | $32 | $160 | $320 |
| Video/Transcription | $30 | $150 | $300 |
| Stripe fees | $32 | $160 | $320 |
| Deepgram | $7 | $35 | $70 |
| Security/Compliance | $22 | $30 | $40 |
| DynamoDB | $5 | $15 | $30 |
| S3 (cumulative, month 12) | $5 | $25 | $50 |
| Lambda | $6 | $25 | $50 |
| Other (Amplify, APIGW, SES) | $5 | $15 | $30 |
| **TOTAL** | **$188** | **$835** | **$1,650** |
| **Per paid user** | **$1.88** | **$1.67** | **$1.65** |

Good news: per-user cost is relatively flat due to serverless architecture. The fixed costs (KMS, GuardDuty, CloudTrail) get amortized. The variable costs (Bedrock, Deepgram, Polly, Transcribe) scale linearly.

### 7.3 What's missing from this model?

1. **Developer time** — not included. This is infrastructure cost only.
2. **Domain registration** — ~$12/year for soulreel.net.
3. **Stripe subscription management overhead** — Stripe Billing portal is free, but disputes cost $15 each.
4. **Data retention compliance costs** — The 3-year Object Lock bucket and Glacier Deep Archive are cheap but non-zero at scale.
5. **Bedrock model price changes** — AWS could change pricing. The model is based on April 2026 rates.

---

## 8. COMPETITOR PRICING ANALYSIS

| Platform | Model | Price | What You Get |
|---|---|---|---|
| **StoryWorth** | Annual subscription | $99/year (~$8.25/mo) | Weekly text prompts, printed book at end of year. No video, no AI, no benefactor access controls. |
| **Eternos** | Monthly subscription | $25/month (basic), $49/month (prosumer) + $995 upfront | AI avatar creation, legacy preservation. 10+ hour setup. |
| **Remento** | Annual subscription | $149/year (~$12.42/mo) | Voice prompts, multimedia, flexible scheduling. No AI conversation. |
| **StoriedLife AI** | Monthly subscription | $14.99/month | AI memoir assistant, conversational storytelling. Text-based. |
| **Evaheld** | Freemium | Free basic, premium pricing varies | Video legacy, vault, benefactor management. |

### SoulReel's Differentiators vs. Competitors

1. **AI-guided conversations** — No competitor offers real-time AI interviewing with voice
2. **Conditional access** — Dead man's switch, time-delay, inactivity triggers are unique
3. **Psychological testing** — Personality profiles integrated into legacy
4. **Video + audio** — Not just text like StoryWorth
5. **Benefactor management** — Granular access controls

### Pricing Position

SoulReel offers significantly more technology (AI, video, conditional access, psych tests) than StoryWorth ($99/year) but should price below Eternos ($25–$49/month) since it doesn't require the intensive setup. The sweet spot is between StoriedLife AI ($14.99/mo) and Eternos ($25/mo).

---

## 9. RECOMMENDED PRICING

### 9.1 Two-Tier Model (Simplified from Original 4-Tier)

The original plan proposed Free / Personal / Family / Vault. For launch, I recommend simplifying to Free / Premium to reduce decision fatigue and engineering complexity. A third tier can be added later.

| | Free | Premium |
|---|---|---|
| **Monthly price** | $0 | **$9.99/month** |
| **Annual price** | $0 | **$89.99/year** (save 25%) |
| Conversations per week | 2 | Unlimited |
| Conversation turn limit | 3 | 4 |
| AI model | Economy (Nova Micro) | Full (Claude 3.5 Haiku) |
| Video recordings | 2/month | Unlimited |
| Storage | 2 GB | 50 GB |
| Benefactors | 1 | 5 |
| Access condition types | Immediate only | All (time-delay, inactivity, manual release) |
| Psych tests | 1 free test | All tests |
| Data export | No | Yes |
| Legacy protection | No | Yes |

### 9.2 Why $9.99/month

| Factor | Analysis |
|---|---|
| **Cost floor** | $1.88/user/month fully loaded → $9.99 gives 81% gross margin |
| **Stripe take** | $0.30 + 2.9% = $0.59/txn → net revenue $9.40 |
| **Net margin per user** | $9.40 - $1.88 = **$7.52/user/month (80% net margin)** |
| **Competitor positioning** | Below Eternos ($25), above StoryWorth ($8.25/mo equivalent) |
| **Psychological pricing** | $9.99 is the most common SaaS entry point |
| **Annual incentive** | $89.99/year = $7.50/mo equivalent, 25% discount drives commitment |

### 9.3 Why $89.99/year

| Factor | Analysis |
|---|---|
| **Annual net revenue** | $89.99 - Stripe ($2.91) = $87.08 |
| **Annual cost per user** | $1.88 × 12 = $22.56 |
| **Annual net margin** | $87.08 - $22.56 = **$64.52/user/year (74% margin)** |
| **vs. StoryWorth** | $89.99 vs $99 — slightly cheaper, vastly more features |
| **Churn reduction** | Annual plans reduce churn by 30–50% vs monthly |
| **Cash flow** | Upfront annual payment funds infrastructure costs |

### 9.4 Revenue Projections

| Scenario | Monthly Users | Annual Users | Monthly Revenue | Annual Revenue |
|---|---|---|---|---|
| **Conservative** (100 paid: 60 monthly, 40 annual) | 60 × $9.99 = $599 | 40 × $7.50 = $300 | $899 | $10,788 |
| **Moderate** (500 paid: 250 monthly, 250 annual) | 250 × $9.99 = $2,498 | 250 × $7.50 = $1,875 | $4,373 | $52,476 |
| **Growth** (1,000 paid: 400 monthly, 600 annual) | 400 × $9.99 = $3,996 | 600 × $7.50 = $4,500 | $8,496 | $101,952 |

| Scenario | Monthly Revenue | Monthly Cost | Monthly Profit | Margin |
|---|---|---|---|---|
| 100 users | $899 | $188 | $711 | 79% |
| 500 users | $4,373 | $835 | $3,538 | 81% |
| 1,000 users | $8,496 | $1,650 | $6,846 | 81% |

---

## 10. COST OPTIMIZATION ROADMAP

### Immediate (No-code, SSM parameter changes)

| Action | Savings/month (100 users) |
|---|---|
| Switch depth scoring to Nova Micro | $3–$8 |
| Switch conversation model to Claude 3.5 Haiku | $25–$60 (already assumed in this model) |
| Reduce free tier to 2 convos/week, 3 turns | $90+ |

### Short-term (1–2 weeks of work)

| Action | Savings/month (100 users) |
|---|---|
| Polly caching for question greetings | $15–$30 |
| Use cheaper model for free-tier conversations | $50–$100 |
| Reduce Lambda memory on over-provisioned functions | $2–$5 |

### Medium-term (1–2 months)

| Action | Savings/month (at 1,000 users) |
|---|---|
| CloudFront for video delivery | $50–$200 |
| S3 Intelligent-Tiering (already in template comments) | $460–$690 |
| DynamoDB reserved capacity (if usage stabilizes) | $50–$100 |

---

## 11. RISK FACTORS

| Risk | Impact | Mitigation |
|---|---|---|
| Bedrock price increase | +20–50% on largest cost line | Model is configurable via SSM; can switch models instantly |
| Free users overwhelm infrastructure | Free users cost more than paid users generate | Strict free-tier limits, usage-based model differentiation |
| Low conversion rate (free → paid) | Revenue doesn't cover free-tier costs | Aggressive feature gating, trial expiration emails, win-back campaigns |
| Video storage grows unbounded | S3 costs compound monthly | Intelligent-Tiering, Glacier transitions, storage limits per plan |
| Stripe chargebacks | $15/dispute + lost revenue | Clear cancellation policy, good UX, email confirmations |
| Deepgram pricing change | +$20–$50/month | Can fall back to AWS Transcribe streaming ($0.024/min, ~5x more expensive) |

---

## 12. FINAL RECOMMENDATION

**Launch pricing: $9.99/month or $89.99/year** for a single "Premium" tier.

This provides:
- 80% gross margin at 100 users
- Competitive positioning below Eternos, near StoryWorth
- Room to add a higher "Family" tier ($19.99/month) later for users who need 10+ benefactors
- Sustainable unit economics that improve with scale

**Critical cost control**: The free tier must be tightly constrained. Free users with unlimited AI conversations will erode margins before the platform reaches profitability. The recommended 2 conversations/week with 3-turn limit and economy AI model keeps free-tier costs to ~$0.17/user/month instead of $0.66/user/month.

**Break-even point**: ~21 paid users at $9.99/month covers the infrastructure for 21 paid + ~42 free users (~$40/month cost). Every user beyond that is profitable.

---

## 13. CONVERSION RATE ANALYSIS — REALISTIC FREE-TO-PAID RATIOS

### 13.1 Industry Benchmarks

Research across multiple sources paints a consistent picture for freemium conversion rates:

| Source | Metric | Rate |
|---|---|---|
| [FirstPageSage](https://firstpagesage.com/seo-blog/saas-freemium-conversion-rates/) (2026, cross-industry) | Traditional freemium → paid | **3.7%** median |
| [Artisan Growth Strategies](https://www.artisangrowthstrategies.com/blog/state-of-freemium-2026-conversion-rates-revenue-share-failure-modes) (2026, 1,200+ companies) | Freemium median | **8%** (AI tools: 15–20%) |
| [Adapty](https://adapty.io/blog/freemium-to-premium-conversion-techniques/) (2026, consumer apps) | Freemium apps median | **2.18%** |
| [ContentGrip](https://www.contentgrip.com/subscription-app-growth-playbook/) (2026) | Hard paywall median | **10.7%** vs freemium **2.1%** |
| [Whop](https://whop.com/blog/subscription-statistics/) (2026) | App download → paying customer | **1.7%** |
| [Databox/CrazyEgg](https://www.crazyegg.com/blog/free-to-paid-conversion-rate/) (SMB SaaS) | Free-to-paid range | **3–10%** |
| [GrowthMethod](https://growthmethod.com/saas-pricing-models/) (2026) | Freemium average | **1–2%**, outliers 4% |
| [Pathmonk](https://pathmonk.com/what-is-the-average-free-to-paid-conversion-rate-saas/) (2026) | Harsh truth | **2–5%** never convert |

*Content was rephrased for compliance with licensing restrictions.*

### 13.2 SoulReel-Specific Conversion Estimate

SoulReel is a **niche consumer app** (not B2B SaaS), which typically converts lower than B2B. However, it has strong conversion tailwinds:

**Factors pushing conversion UP:**
- Emotional product (legacy for family) — high motivation once engaged
- Clear value gate (unlimited conversations, conditional access, more benefactors)
- AI tools category trending 15–20% conversion per Artisan Growth data
- Win-back email system already built
- Coupon/trial system enables time-limited free upgrades

**Factors pushing conversion DOWN:**
- Consumer app, not B2B — lower willingness to pay
- Older demographic may be price-sensitive
- No credit card required at signup (opt-in freemium, not opt-out trial)
- Competing with "free" alternatives (just recording a video on your phone)

**Estimated conversion rate: 3–5%** for a mature product with good onboarding. At launch, expect **2–3%** until the upgrade prompts and feature gating are polished.

### 13.3 Updated User Funnel Model

The original report assumed a 2:1 free-to-paid ratio (200 free : 100 paid). That implied a 33% conversion rate — wildly optimistic. Here's the corrected model:

| Scenario | Total Signups | Conversion Rate | Paid Users | Free Users | Free:Paid Ratio |
|---|---|---|---|---|---|
| **Pessimistic** (launch) | 5,000 | 2% | 100 | 4,900 | 49:1 |
| **Realistic** (6 months in) | 3,333 | 3% | 100 | 3,233 | 32:1 |
| **Optimistic** (mature, good gating) | 2,000 | 5% | 100 | 1,900 | 19:1 |
| **AI-tool benchmark** | 667 | 15% | 100 | 567 | 5.7:1 |

This changes the economics dramatically. At a 3% conversion rate, to get 100 paid users you need ~3,333 total signups, meaning ~3,233 free users — not 200.

### 13.4 Revised Cost Model With Realistic Conversion Rates

**Critical question: How many free users are actively using the product?**

Not all 3,233 signups are active. Industry data shows:
- ~30% of signups never complete onboarding
- ~40% use the product once and leave within the first week
- ~15% become "casual" users (1–2 sessions/month)
- ~15% become "active" free users (weekly usage)

So of 3,233 free signups, roughly **485 are active free users** (15%) consuming meaningful AI resources.

| Scenario | Paid Users | Active Free Users | Free User Monthly AI Cost | Total Monthly Cost | Per Paid User |
|---|---|---|---|---|---|
| **Original model** (2:1 ratio) | 100 | 200 | $32 | $188 | $1.88 |
| **3% conversion, mitigated free tier** | 100 | 485 | $78 | $234 | $2.34 |
| **3% conversion, unmitigated free tier** | 100 | 485 | $320 | $476 | $4.76 |
| **5% conversion, mitigated free tier** | 100 | 285 | $46 | $202 | $2.02 |

**The unmitigated scenario ($4.76/user) is still profitable at $9.99/month** — a major improvement over the 12-turn model where it was unprofitable. At 4 turns, even the worst-case scenario has healthy margins. Free-tier cost controls are still important but no longer existential.

### 13.5 Revised Revenue Projections With Realistic Conversion

| Metric | 3% Conversion | 5% Conversion |
|---|---|---|
| Total signups needed for 100 paid | 3,333 | 2,000 |
| Active free users | 485 | 285 |
| Monthly revenue (100 paid) | $899 | $899 |
| Monthly cost (mitigated free tier) | $234 | $202 |
| Monthly profit | $665 | $697 |
| Margin | 74% | 78% |
| Break-even paid users | ~26 | ~23 |

---

## 14. TOP-COST ALTERNATIVES ANALYSIS

The top 5 cost drivers from the model are:

1. **Stripe processing** — $32/month
2. **AWS Transcribe (video)** — $29/month
3. **Bedrock AI (conversations)** — $44/month (paid) + $32–$78 (free) = $76–$122
4. **Security/Compliance stack** — $22/month
5. **Polly (TTS)** — ~$20/month (embedded in conversation cost)
6. **Deepgram (real-time STT)** — $7/month

### 14.1 Alternative: Bedrock Response Generation — Amazon Nova Lite Instead of Claude 3.5 Haiku

| | Claude 3.5 Haiku (current) | Amazon Nova Lite v1 | Amazon Nova 2 Lite |
|---|---|---|---|
| Input cost/1M tokens | $0.80 | $0.06 | $0.30 |
| Output cost/1M tokens | $4.00 | $0.24 | $2.50 |
| Cost reduction | baseline | **93% cheaper input, 94% cheaper output** | **63% cheaper input, 38% cheaper output** |
| Quality for empathetic interviewing | Excellent | Good for simple tasks, weaker on nuance | Good reasoning, improved over v1 |
| Context window | 200K | 300K | 1M |
| Already in IAM policy? | Yes | No (needs adding) | No (needs adding) |

**Assessment — Nova Lite v1:**
- 93% cheaper but quality is a real concern for SoulReel's core use case. The AI interviewer needs to ask empathetic, contextually-aware follow-up questions about deeply personal life stories. Nova Lite v1 was designed for "real-time customer interactions" and "document analysis" — not nuanced emotional conversation. Testing would be required, but there's a meaningful risk of degraded user experience.
- **Verdict: Not recommended for paid tier conversations. Viable for free tier.**

**Assessment — Nova 2 Lite:**
- 63% cheaper on input, 38% cheaper on output. Better reasoning capabilities than v1. AWS positions it as having "industry-leading price performance" with improved coherence. At $0.30/$2.50 per 1M tokens vs Haiku's $0.80/$4.00, the savings are meaningful but not transformative.
- **Verdict: Worth testing for paid tier. If quality holds, saves ~$50/month at 100 users.**

**Assessment — Nova Micro (for depth scoring, already planned):**
- At $0.035/$0.14 per 1M tokens, this is 23x cheaper than Haiku for the simple scoring task. Already recommended in the existing cost reduction plan. No quality concern for a classification task.
- **Verdict: Implement immediately. Already in the plan.**

**Potential savings (paid user conversations):**

| Model | Monthly Cost (100 paid users) | Savings vs Haiku |
|---|---|---|
| Claude 3.5 Haiku (current) | $44 | — |
| Nova 2 Lite | ~$27 | $17/month (38%) |
| Nova Lite v1 | ~$4 | $40/month (91%) — quality risk |
| Hybrid: Haiku turns 1–2, Nova 2 Lite turns 3–4 | ~$25 | $19/month (43%) |

**Recommended approach:** Test Nova 2 Lite for conversation quality. If acceptable, use the hybrid model (Haiku for opening turns where tone-setting matters, Nova 2 Lite for follow-ups). At only 4 turns, the hybrid savings are more modest — a full switch to Nova 2 Lite may be simpler. This is implementable via the existing SSM parameter + a small code change in `llm.py`.

### 14.2 Alternative: Real-Time Speech-to-Text — AssemblyAI Instead of Deepgram

| | Deepgram Nova-2 (current) | AssemblyAI Universal-2 | AWS Transcribe Streaming |
|---|---|---|---|
| Price per minute | $0.0043 | $0.0025 | $0.024 |
| Price per hour | $0.26 | $0.15 | $1.44 |
| Real-time streaming | Yes | Yes | Yes |
| Latency | ~100ms (fastest) | ~300ms | ~500ms |
| Accuracy | Very good | Very good (claims best) | Good |
| Integration effort | Already integrated | New SDK, new auth | Already in AWS ecosystem |

**Assessment — AssemblyAI:**
- 42% cheaper per minute ($0.0025 vs $0.0043). At 1,600 minutes/month, that's $4.00 vs $6.88 — saving **$2.88/month**. However, this requires replacing the Deepgram SDK integration in the WebSocket conversation handler, updating the credential management (currently in SSM/Secrets Manager), and testing real-time latency. The latency difference (100ms → 300ms) is noticeable in a real-time conversation.
- **Verdict: Marginal savings ($2.88/month) don't justify the migration effort and latency trade-off at 100 users. Revisit at 1,000+ users where savings reach $29/month.**

**Assessment — AWS Transcribe Streaming:**
- 5.6x more expensive than Deepgram. Would increase costs from $20.64 to $115.20/month. Not viable.
- **Verdict: Do not switch. Deepgram is already the cost-optimal choice.**

### 14.3 Alternative: Text-to-Speech — Polly Standard vs Neural, or OpenAI TTS

Polly Neural is the second-largest per-turn cost at $0.0064/turn ($16/1M chars). Over 3,200 turns/month (paid users), that's ~$20/month.

| | Polly Neural (current) | Polly Standard | OpenAI TTS (tts-1) | Google Cloud TTS Neural |
|---|---|---|---|---|
| Price per 1M chars | $16.00 | $4.00 | $15.00 | $16.00 |
| Voice quality | Natural, expressive | Robotic, dated | Very natural | Natural |
| Latency | Low (AWS native) | Low (AWS native) | Medium (external API) | Medium (external API) |
| Integration effort | Current | Config change only | New SDK + API calls | New SDK + API calls |

**Assessment — Polly Standard:**
- 75% cheaper ($4/1M vs $16/1M). Monthly cost drops from ~$20 to ~$5 — saving **$15/month**. However, Standard voices sound noticeably robotic. For a product centered on intimate, emotional life story conversations, a robotic AI voice would significantly degrade the experience. Users are sharing memories about their parents, childhood, and life milestones — the voice quality matters.
- **Verdict: Not recommended for paid tier. Could be used for free tier to further differentiate the experience and incentivize upgrades.**

**Assessment — OpenAI TTS:**
- Similar price to Polly Neural ($15/1M vs $16/1M). Higher quality voices but requires external API integration, adding latency and a new dependency. No meaningful cost savings.
- **Verdict: Not worth the migration. Polly Neural is already competitive.**

**Assessment — Polly caching (from existing cost reduction plan):**
- Cache question greeting audio (turn 0) since the same question text is spoken to every user. This eliminates ~25% of Polly calls (1 of 4 turns). Saves ~$5/month at 100 users. Low effort, no quality impact.
- **Verdict: Implement. Small but free savings.**

**Best Polly optimization: Use Standard for free tier, Neural for paid tier.** This saves ~$4/month on free-tier TTS while creating a tangible quality difference that motivates upgrades.

### 14.4 Alternative: Video Transcription — Deepgram Batch Instead of AWS Transcribe

Video transcription (post-recording, not real-time) currently uses AWS Transcribe at $0.024/min. This is separate from the real-time Deepgram usage during conversations.

| | AWS Transcribe (current) | Deepgram Nova-2 Batch | AssemblyAI Batch |
|---|---|---|---|
| Price per minute | $0.024 | $0.0043 | $0.0025 |
| Price for 1,200 min/month | $28.80 | $5.16 | $3.00 |
| Integration | Native AWS (EventBridge trigger) | New API integration | New API integration |
| Features | Auto language detect, custom vocab | Speaker diarization, summarization | Speaker labels, chapters, summaries |

**Assessment — Deepgram for batch transcription:**
- 82% cheaper ($5.16 vs $28.80). Saves **$23.64/month**. Since Deepgram is already integrated for real-time conversations, the SDK and credentials are already in place. The main work is modifying `startTranscription` Lambda to call Deepgram's batch API instead of AWS Transcribe, and updating the `processTranscript` Lambda to handle Deepgram's response format instead of the Transcribe EventBridge event.
- **Verdict: Recommended. Meaningful savings, and Deepgram is already a dependency. Moderate effort (2–3 days).**

### 14.5 Alternative: Security Stack — AWS Managed Keys Instead of Customer-Managed KMS

The KMS customer-managed key costs $1/month + $0.03/10K API requests. With 17 encrypted DynamoDB tables and PITR, KMS API calls are substantial (~$7/month total).

| | Customer-Managed KMS (current) | AWS Managed Keys |
|---|---|---|
| Key cost | $1.00/month | Free |
| API request cost | $0.03/10K requests | Free (first 20K/month), then $0.03/10K |
| Key rotation | Automatic (configured) | Automatic (AWS-managed) |
| Cross-service encryption | Full control | Same encryption, less control |
| Compliance | Full audit trail, custom policy | Standard audit trail |
| CloudTrail encryption | Supported | Supported |

**Assessment:**
- Switching to AWS managed keys would save ~$7/month (the key + API requests). However, the customer-managed key provides important compliance benefits: custom key policy, explicit rotation control, and the ability to revoke access. For a platform storing sensitive personal legacy data with GDPR compliance requirements and a 3-year retention audit bucket, the CMK is justified.
- **Verdict: Keep the CMK. $7/month is cheap insurance for a data-sensitive platform.**

### 14.6 Alternative: GuardDuty — Disable or Reduce Scope

GuardDuty costs ~$4.50/month at low volume. It provides threat detection for the AWS account.

**Assessment:** GuardDuty is a security best practice, especially for a platform handling personal data. At $4.50/month it's negligible. Disabling it to save $4.50 would be penny-wise and pound-foolish.
- **Verdict: Keep. Non-negotiable for a production platform with user data.**

---

## 15. OPTIMIZED COST MODEL — WITH ALTERNATIVES IMPLEMENTED

Applying only the alternatives that don't degrade service quality:

| Optimization | Change | Monthly Savings |
|---|---|---|
| Nova 2 Lite for paid-tier conversations (full switch) | Bedrock cost reduction | $17 |
| Nova Lite v1 for free-tier conversations | Cheaper model for free users | $55 |
| Polly Standard for free tier, Neural for paid | TTS cost differentiation | $4 |
| Polly caching for question greetings | Eliminate redundant synthesis | $5 |
| Deepgram batch for video transcription (replace AWS Transcribe) | STT provider switch | $24 |
| Nova Micro for depth scoring (already planned) | Scoring model downgrade | $2 |
| **Total savings** | | **$107/month** |

### 15.1 Optimized Monthly Cost (100 Paid Users, 3% Conversion, 485 Active Free Users)

| Category | Before Optimization | After Optimization |
|---|---|---|
| Bedrock — paid conversations | $44 | $27 (Nova 2 Lite) |
| Bedrock — free conversations | $78 | $23 (Nova Lite v1) |
| Bedrock — scoring | $2 | $0.20 (Nova Micro) |
| Bedrock — summarization | $1 | $1 (keep Haiku for quality) |
| Polly — paid users | $20 | $20 (keep Neural) |
| Polly — free users | $10 | $3 (Standard voice) |
| Polly — caching savings | — | -$5 |
| Deepgram (real-time, all users) | $7 | $7 (keep Deepgram) |
| Video transcription | $29 | $5 (Deepgram batch) |
| Stripe | $32 | $32 |
| Security/Compliance | $22 | $22 |
| Lambda | $6 | $6 |
| DynamoDB | $5 | $5 |
| S3 + Egress | $5 | $5 |
| Other (Amplify, APIGW, SES) | $5 | $5 |
| **TOTAL** | **$266** | **$156** |
| **Per paid user** | **$2.66** | **$1.56** |

### 15.2 Optimized Revenue vs Cost (3% Conversion Rate)

| Metric | Before Optimization | After Optimization |
|---|---|---|
| Monthly revenue (100 paid @ $9.99) | $899 | $899 |
| Monthly cost | $266 | $156 |
| Monthly profit | $633 | $743 |
| Margin | 70% | 83% |
| Break-even paid users | ~30 | ~18 |

### 15.3 Scaling Projections (Optimized Model)

| Paid Users | Total Signups (3% conv) | Active Free Users | Monthly Revenue | Monthly Cost | Profit | Margin |
|---|---|---|---|---|---|---|
| 50 | 1,667 | 243 | $450 | $100 | $350 | 78% |
| 100 | 3,333 | 485 | $899 | $156 | $743 | 83% |
| 250 | 8,333 | 1,213 | $2,248 | $350 | $1,898 | 84% |
| 500 | 16,667 | 2,425 | $4,495 | $660 | $3,835 | 85% |
| 1,000 | 33,333 | 4,850 | $8,990 | $1,270 | $7,720 | 86% |

Margins improve with scale because fixed costs (security stack, Amplify, base Lambda) get amortized while per-user variable costs stay flat.

---

## 16. IMPLEMENTATION PRIORITY FOR ALTERNATIVES

| Priority | Action | Effort | Monthly Savings | Cumulative |
|---|---|---|---|---|
| 1 | Switch depth scoring to Nova Micro (SSM change + IAM) | 15 min | $2 | $2 |
| 2 | Use Nova Lite v1 for free-tier conversations (SSM + code) | 2 hours | $55 | $57 |
| 3 | Switch video transcription to Deepgram batch | 2–3 days | $24 | $81 |
| 4 | Use Polly Standard for free tier (code change in speech.py) | 1 hour | $4 | $85 |
| 5 | Implement Polly caching for question greetings | 2 hours | $5 | $90 |
| 6 | Test Nova 2 Lite for paid conversations, full switch | 1 week | $17 | $107 |

Items 1–2 and 4–5 can be done in a single afternoon. Item 3 is a moderate refactor. Item 6 requires quality testing before committing.

---

## 17. UPDATED FINAL RECOMMENDATION

**Pricing: $9.99/month or $89.99/year** — unchanged. With 4 turns per conversation, the unit economics are significantly stronger than the original 12-turn model. Even at a realistic 3% conversion rate with many free users, margins remain above 70%.

**Key insight from this update:** The shift from 12 to 4 turns per conversation fundamentally changes the cost picture. Per-conversation cost drops from $0.15 to $0.053 — a 65% reduction. This means:
- The AI conversation engine is no longer the dominant cost — Stripe fees and video transcription are now comparable
- Free-tier users are still a cost concern but no longer an existential threat
- Even without optimizations, the platform is profitable at $9.99/month with a 3% conversion rate

**The three most impactful actions, in order:**
1. Use a cheap model (Nova Lite v1) for free-tier conversations — saves $55/month
2. Switch video transcription from AWS Transcribe to Deepgram batch — saves $24/month
3. Switch paid conversations to Nova 2 Lite — saves $17/month

These three changes alone account for $96 of the $107 total monthly savings.

---

*Sources: AWS pricing pages (April 2026), Deepgram pricing page, Stripe fee documentation, competitor websites. All AWS prices are for us-east-1. Bedrock token pricing from [claudeapipricing.com](https://www.claudeapipricing.com/) and [AWS Bedrock pricing](https://wring.co/blog/aws-bedrock-pricing-guide). Competitor pricing from [safekeep.co](https://safekeep.co/eternos-review-2026/), [memoirji.com](https://memoirji.com/blog/best-storyworth-alternatives-2026/), and respective company websites. Conversion rate data from [FirstPageSage](https://firstpagesage.com/seo-blog/saas-freemium-conversion-rates/), [Artisan Growth Strategies](https://www.artisangrowthstrategies.com/blog/state-of-freemium-2026-conversion-rates-revenue-share-failure-modes), [Adapty](https://adapty.io/blog/freemium-to-premium-conversion-techniques/), [ContentGrip](https://www.contentgrip.com/subscription-app-growth-playbook/). AssemblyAI pricing from [brasstranscripts.com](https://brasstranscripts.com/blog/assemblyai-vs-deepgram-pricing-high-volume-comparison). Amazon Nova pricing from [wring.co](https://wring.co/blog/aws-bedrock-llm-models-guide) and [anotherwrapper.com](https://anotherwrapper.com/tools/llm-pricing/amazon-nova-lite). Content was rephrased for compliance with licensing restrictions.*
