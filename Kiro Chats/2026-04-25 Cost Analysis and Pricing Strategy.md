# 2026-04-25 — SoulReel Cost Analysis & Pricing Strategy

## Context

Full bottom-up cost analysis of the SoulReel platform, covering all AWS services, third-party integrations, and per-user unit economics. Followed by free-tier design, paid-tier pricing, and price-point optimization from a consumer marketing perspective.

## Key Decisions

### Pricing: $149/year ($14.99/month)
- Launch at $99/year for first 100 "Founding Member" users
- Raise to $149/year once social proof exists
- Keep $99 as promotional floor for campaigns and win-back
- Monthly option at $14.99 always available
- No usage caps, no storage fees, no metering

### Free Tier: Complete Level 1 at any pace, full quality
- All 4 Level 1 categories: Childhood Memories, Family & Upbringing, School Days, Friends
- Same AI model (Haiku), same voice (Neural), same 4 turns as paid
- No weekly conversation limits within Level 1
- 1 benefactor, immediate access only
- Life Events survey completed but questions locked (shows "X questions waiting")
- After Level 1 complete: read-only dashboard + upgrade prompts
- Non-converting users cost $0/month after completing Level 1

---

## Infrastructure Cost Model

### Per-Conversation Cost (4 turns)

```
Deepgram real-time STT:     $0.0088
Bedrock Haiku (response):   $0.0112
Bedrock Nova Micro (score): $0.00012
Polly Neural TTS:           $0.0256
S3 + DynamoDB + Lambda:     $0.0023
Summarization:              $0.005
─────────────────────────────────────
Total per conversation:     $0.053
```

### Per-User Cost Scenarios

| User Type | Conversations/Month | Monthly AI Cost | Annual Cost |
|---|---|---|---|
| Light (40% of users) | 3 | $0.16 | $1.92 |
| Regular (40%) | 8 | $0.42 | $5.04 |
| Power (15%) | 30 | $1.59 | $19.08 |
| Binge (5%) | 300 total over 1-2 months | $15.90 total | $15.90 total |
| **Blended average** | **~12** | **$0.64** | **$7.68** |

### 300-Question Worst Case

A user completing all 300 questions costs $16 in AI processing and generates 390 MB of storage (~$0.05/year). At $149/year, that's 89% margin even in the worst case.

### Monthly Platform Cost (100 paid users, optimized)

| Category | Monthly Cost |
|---|---|
| Bedrock AI (paid + free users) | $51 |
| Stripe processing | $32 |
| Video transcription (Deepgram batch) | $5 |
| Security stack (KMS, GuardDuty, CloudTrail, CW) | $22 |
| Polly TTS | $23 |
| Deepgram real-time | $7 |
| Lambda compute | $6 |
| DynamoDB | $5 |
| S3 + egress | $5 |
| Amplify + API Gateway + SES + Cognito | $5 |
| **Total** | **~$161** |

### Scaling Projections ($149/year, optimized)

| Paid Users | Monthly Cost | Annual Revenue | Annual Profit | Margin |
|---|---|---|---|---|
| 50 | $100 | $7,450 | $6,250 | 84% |
| 100 | $156 | $14,900 | $13,028 | 87% |
| 500 | $660 | $74,500 | $66,580 | 89% |
| 1,000 | $1,270 | $149,000 | $133,760 | 90% |

---

## Conversion Rate Model

### Industry Benchmarks
- Freemium consumer apps: 2–5% median conversion
- AI tools: 15–20% (Artisan Growth Strategies 2026)
- SoulReel estimate: 2–3% at launch, 3–5% mature

### Funnel Math (3% conversion)
- 3,333 total signups needed for 100 paid users
- ~3,233 free users, of which ~485 are actively using the product
- ~15% of signups become active free users consuming AI resources
- Customer acquisition cost: ~$4–$5 per paid user (free-tier AI subsidy)

---

## Competitive Positioning

| Competitor | Price | SoulReel Advantage |
|---|---|---|
| StoryWorth ($99/yr) | Text-only prompts, printed book | AI voice conversations, video, benefactor controls, psych tests |
| Remento ($99/yr) | Voice prompts, AI transcription only | Real-time AI interviewing with follow-ups |
| StoriedLife ($99-$129/yr) | AI conversations, text only | Voice + video, benefactor management, access conditions |
| Eternos ($300+/yr) | AI avatar, 10+ hour setup | Accessible, no setup, immediate value |
| Ghostwriter ($3,000+) | Professional memoir | 98% cheaper, self-guided |

$149/year positions SoulReel above the $99 commodity tier and below the $300+ premium tier — exactly where the product belongs.

---

## Cost Optimization Actions (Priority Order)

| # | Action | Effort | Monthly Savings |
|---|---|---|---|
| 1 | Switch depth scoring to Nova Micro (SSM change) | 15 min | $2 |
| 2 | Use Nova Lite v1 for free-tier conversations | 2 hours | $55 |
| 3 | Switch video transcription to Deepgram batch | 2-3 days | $24 |
| 4 | Use Polly Standard for free tier | 1 hour | $4 |
| 5 | Implement Polly caching for question greetings | 2 hours | $5 |
| 6 | Test Nova 2 Lite for paid conversations | 1 week | $17 |

Items 1-2 and 4-5 can be done in a single afternoon.

---

## AWS Services in Use

**Compute**: 60+ Lambda functions (Python 3.12, mostly ARM64), API Gateway REST + WebSocket
**Data**: 17+ DynamoDB tables (on-demand, KMS encrypted, PITR enabled)
**Storage**: S3 (virtual-legacy bucket + 3 lifecycle-managed buckets), Intelligent-Tiering
**Auth**: Cognito User Pools (free up to 50K MAUs)
**AI/ML**: Bedrock (Claude 3.5 Haiku, Nova Micro, Claude 3 Sonnet for summarization), Transcribe, Polly Neural
**Email**: SES with configuration sets for nurture tracking
**Security**: KMS CMK, CloudTrail data events, GuardDuty, CloudWatch Logs/Metrics/Alarms
**Scheduling**: EventBridge rules (hourly, daily, weekly, monthly cron jobs)
**Frontend**: Amplify hosting (React/Vite/TypeScript)
**Third-party**: Deepgram Nova-2 (real-time STT), Stripe (payments)

---

## Key Assumptions

| Assumption | Value | Source |
|---|---|---|
| Turns per conversation | 4 | Product owner input |
| Conversations per month (avg paid user) | 8 | Estimated ~2/week |
| Total questions in database | 300 | Product owner input |
| Freemium conversion rate | 3% (realistic) | Industry benchmarks |
| Active free user rate | 15% of signups | Industry benchmarks |
| Level 1 questions | 12-30 (4 categories) | Question theme structure |
| Bedrock Haiku input/output | $0.80/$4.00 per 1M tokens | AWS pricing April 2026 |
| Deepgram Nova-2 | $0.0043/min | Deepgram pricing April 2026 |
| Polly Neural | $16.00/1M chars | AWS pricing April 2026 |

---

## Supporting Documents

| File | Description |
|---|---|
| `SOULREEL_COST_AND_PRICING_REPORT.md` | Full infrastructure cost breakdown with 17 sections: per-service costs, critique cycles, conversion modeling, alternative provider evaluation, optimized projections |
| `SOULREEL_FREE_TIER_STRATEGY.md` | Product emotional analysis, 3 free tier options (The Taste / The Hook / The Drip), "Complete Level 1" hybrid recommendation |
| `SOULREEL_PAID_TIER_PRICING.md` | 300-question cost analysis, 3 paid structures (flat / one-time+storage / completion bonus), flat $9.99 recommendation, post-completion retention analysis |
| `SOULREEL_PRICE_POINT_ANALYSIS.md` | $90 vs $150 vs $200 comparison, competitive landscape, conversion-revenue tradeoff, $149 recommendation with launch strategy |
| `SOULREEL_PRICING_SUMMARY.md` | One-page executive summary of all findings |

---

## Post-Completion Retention (Open Question)

Users who finish all 300 questions still get value from:
- Benefactor access condition monitoring (dead man's switch, inactivity triggers)
- New question packs added over time
- Psych test retakes and new assessments
- The emotional weight of "my family loses access if I cancel"
- Annual "legacy review" prompts to update stories

If churn after completion becomes a problem at scale, introduce a "Legacy Keeper" tier at $4.99/month — but as a retention offer to users about to cancel, not a default pricing tier.
