# SoulReel — Paid Tier Pricing: The 300-Question Problem

**Date**: April 25, 2026
**Perspective**: Consumer internet marketing + unit economics

---

## THE MATH: WHAT DOES A 300-QUESTION USER ACTUALLY COST?

### Per-conversation cost breakdown (4 turns, Claude 3.5 Haiku)

| Component | Per Turn | Per Conversation (4 turns) |
|---|---|---|
| Deepgram real-time STT | $0.0022 | $0.0088 |
| Bedrock Haiku (response gen) | $0.0028 avg | $0.0112 |
| Bedrock Nova Micro (scoring) | $0.00003 | $0.00012 |
| Polly Neural TTS | $0.0064 | $0.0256 |
| S3 audio storage (user + AI) | $0.00001 | $0.00004 |
| DynamoDB state | $0.0000025 | $0.00001 |
| Lambda compute | ~$0.0005 | $0.002 |
| **Total** | **$0.012** | **$0.048** |

Plus summarization per conversation: ~$0.005

**Total per conversation: $0.053**

### Storage per conversation

Each conversation generates:
- 4 user audio recordings (~30s each, WebM): ~200 KB each = **800 KB**
- 4 AI audio responses (~15s each, MP3): ~120 KB each = **480 KB**
- 1 transcript JSON: ~5 KB
- 1 AI summary: ~2 KB

**Total per conversation: ~1.3 MB**

### The 300-question user

| Metric | Value |
|---|---|
| AI + processing cost | 300 × $0.053 = **$15.90** |
| Storage generated | 300 × 1.3 MB = **390 MB** |
| S3 storage cost (month 1) | 390 MB × $0.023/GB = **$0.009** |
| S3 storage cost (year 1, Intelligent-Tiering) | ~$0.05–$0.10 |
| KMS requests for 300 conversations | ~6,000 requests × $0.03/10K = **$0.02** |
| **Total cost for 300 questions** | **~$16.00** |

So a user who blitzes through all 300 questions in a single month costs about **$16 in AI/processing** and generates **390 MB of storage** that costs essentially nothing ongoing.

The storage is negligible. Even at 10 years of retention, 390 MB in Intelligent-Tiering costs under $0.50 total. The real cost is the one-time AI processing.

### What about video recordings?

If the same power user also records standalone video responses (separate from AI conversations), each 3-minute video:
- AWS Transcribe: $0.072 (3 min × $0.024/min)
- S3 storage: ~50 MB per video
- Bedrock summarization: ~$0.005

At 300 video recordings: $23.10 in transcription + 15 GB storage. But this is an extreme edge case — most users do AI conversations OR video recordings for a given question, not both.

---

## THE PRICING TENSION

The current $9.99/month model works beautifully for the average user doing 8 conversations/month ($0.42 in AI costs, 88% margin). But it has a structural vulnerability:

**A power user doing 300 conversations in month 1 costs $16 and pays $9.99.** You lose $6 on that user in month 1.

But here's the thing: that user just recorded their entire life story in a month. They're done with the AI conversations. Month 2, they cost ~$0 in AI (maybe a few dashboard loads). Month 3, same. If they stay subscribed for 3 months, you've collected $29.97 and spent $16 — a 47% margin. By month 6, it's $59.94 revenue on $16 cost — 73% margin.

**The question isn't "can a power user cost more than one month's subscription?" — it's "will they stay subscribed after they finish recording?"**

And the answer is: yes, if the product gives them reasons to stay. Benefactor management, access condition monitoring, new questions added over time, psych tests, the streak system, and the emotional weight of "if I cancel, my legacy goes dark" all create retention.

---

## THREE PRICING OPTIONS

### Option A: "Flat Monthly, Eat the Power Users" — $9.99/month

Keep the current model. Accept that a small percentage of users will cost more than one month's revenue. Bet on retention.

**How it works:**
- $9.99/month or $89.99/year
- Unlimited conversations, all levels, all features
- No usage caps, no metering, no complexity
- Storage included forever (as long as subscribed)

**The math at 100 paid users:**

| User Type | % of Users | Conversations/Month | AI Cost/User | Revenue/User | Margin |
|---|---|---|---|---|---|
| Light (2–4/month) | 40% | 3 avg | $0.16 | $9.99 | 98% |
| Regular (6–12/month) | 40% | 8 avg | $0.42 | $9.99 | 96% |
| Power (20–50/month) | 15% | 30 avg | $1.59 | $9.99 | 84% |
| Binge (100–300 in month 1) | 5% | 150 avg over first 3 months | $2.65/mo avg | $9.99 | 73% |
| **Blended** | 100% | ~12 avg | **$0.64** | **$9.99** | **94%** |

The blended margin is 94% because the 80% of users who are light/regular subsidize the 5% who binge. And the bingers' cost is front-loaded — after month 1–2, they become the cheapest users (near-zero AI cost, just storage).

**Critique:**

Pros:
- Simplest possible pricing. No cognitive load. No "will I get charged extra?"
- Matches competitor positioning (StoryWorth $99/year, no usage limits)
- Power users become your best advocates — they've recorded 300 stories, they're deeply invested
- No engineering complexity — no metering, no overage billing

Cons:
- A coordinated influx of power users (e.g., a retirement community signs up 50 people who all binge) could create a temporary cash flow problem
- No price discrimination — the user doing 3 conversations/month pays the same as the user doing 100
- Leaves money on the table from users who'd pay more for the "complete your legacy fast" experience

---

### Option B: "Lifetime Access Pass + Storage" — $79 one-time + $2.99/month storage

Separate the AI processing cost (one-time) from the ongoing storage/access cost (monthly).

**How it works:**
- **$79 one-time "Legacy Recording Pass"**: Unlimited AI conversations, all levels, all features. Record as much as you want, as fast as you want. This covers the AI processing cost.
- **$2.99/month "Legacy Vault"**: Keeps your recordings accessible, benefactor access active, access conditions monitored, new features. Cancel and your content goes into cold storage (Glacier) — still preserved but not immediately accessible.
- Annual vault option: $29.99/year (save 16%)

**The math:**

| Scenario | Revenue (Year 1) | AI Cost | Storage Cost | Margin |
|---|---|---|---|---|
| Light user (20 convos total) | $79 + $35.88 = $114.88 | $1.06 | $0.03 | 99% |
| Regular user (100 convos total) | $79 + $35.88 = $114.88 | $5.30 | $0.15 | 95% |
| Power user (300 convos in month 1) | $79 + $35.88 = $114.88 | $15.90 | $0.45 | 86% |
| **Blended** | **$114.88** | **$5.30** | **$0.15** | **95%** |

**Critique:**

Pros:
- The one-time fee covers the worst-case AI cost ($16 for 300 questions) with margin to spare
- The monthly vault fee creates recurring revenue for ongoing costs (storage, monitoring, benefactor access)
- Psychologically powerful: "Pay once to record your legacy, then just $2.99/month to keep it safe"
- The "cold storage if you cancel" mechanic creates strong retention — "my family loses access if I stop paying $2.99"
- Aligns cost structure with value: recording is the expensive part, storage is cheap

Cons:
- $79 upfront is a significant barrier for a consumer product. Conversion from free to $79 is much harder than free to $9.99
- Two-part pricing is more complex to explain and sell
- The "cold storage" mechanic could feel punitive — "you're holding my memories hostage"
- Harder to compare with competitors (StoryWorth is $99/year, simple)
- If a user pays $79 and churns after 1 month, you got $81.99 total — good margin, but you lost a potential long-term subscriber

---

### Option C: "Monthly with a Completion Bonus" — $9.99/month, drops to $4.99 after Level 10

Keep monthly pricing but reward users who complete their legacy with a reduced "maintenance" rate.

**How it works:**
- **$9.99/month** while actively recording (Levels 1–10, Life Events, Values & Emotions)
- **$4.99/month "Legacy Keeper"** after completing Level 10 (or after 12 months, whichever comes first)
- Annual option: $89.99/year (recording phase), $49.99/year (keeper phase)
- Legacy Keeper includes: benefactor access, access condition monitoring, new questions if added, psych test retakes, storage

**The math:**

| Scenario | Months at $9.99 | Months at $4.99 | Year 1 Revenue | AI Cost | Margin |
|---|---|---|---|---|---|
| Slow user (12 months recording) | 12 | 0 | $119.88 | $5.30 | 96% |
| Regular user (6 months recording) | 6 | 6 | $89.88 | $5.30 | 94% |
| Power user (2 months recording) | 2 | 10 | $69.88 | $15.90 | 77% |
| Binge user (1 month recording) | 1 | 11 | $64.88 | $15.90 | 75% |

**Critique:**

Pros:
- Low entry barrier ($9.99, same as current)
- Rewards completion — users feel good about "graduating" to a lower rate
- The price drop creates a goal: "finish your legacy and save $5/month"
- Aligns incentives: you WANT users to finish recording (their AI cost drops to $0), and they WANT to finish (their price drops)
- The "Legacy Keeper" tier name reinforces the product's purpose
- Competitive: $4.99/month for permanent legacy storage is cheaper than any competitor

Cons:
- The binge user paying $9.99 for one month then $4.99 for 11 months generates $64.88/year — less than the $89.99 annual plan
- Users might game it: rush through questions to get to the cheaper tier faster (but this actually saves you AI costs, so it's fine)
- Two price points add complexity to the billing system
- The 12-month auto-transition means even users who never finish recording get the discount eventually — this could feel arbitrary

---

## CRITIQUE OF ALL THREE OPTIONS

### The real question: what behavior do you want to incentivize?

| Behavior | Option A | Option B | Option C |
|---|---|---|---|
| Sign up quickly (low barrier) | ✅ $9.99 | ❌ $79 upfront | ✅ $9.99 |
| Record at their own pace | ✅ No pressure | ✅ No pressure | ⚠️ Slight pressure to finish |
| Binge-record everything | ✅ Allowed, costs absorbed | ✅ Allowed, covered by $79 | ⚠️ Allowed but you lose margin |
| Stay subscribed long-term | ⚠️ No incentive to stay after recording | ✅ $2.99 is easy to keep | ✅ $4.99 drop rewards staying |
| Share with family | ✅ Included | ✅ Included in vault | ✅ Included |
| Feel good about the price | ✅ Simple, fair | ⚠️ Two-part feels complex | ✅ Reward feels good |

### The retention problem

All three options share a risk: **what happens after a user finishes recording all 300 questions?**

If the product has no ongoing value beyond storage, users will cancel regardless of price. The $2.99/month vault (Option B) and $4.99/month keeper (Option C) only work if users perceive ongoing value:

- Benefactor access monitoring (dead man's switch, check-ins)
- New questions added periodically
- Psych test retakes and new assessments
- The emotional weight of "my family loses access if I cancel"
- Annual "legacy review" prompts to update or add stories

Without these, even $2.99/month feels like paying for nothing.

### The power user isn't the problem

After running the numbers, the 300-question binge user costs $16 in AI processing. At $9.99/month, you break even in month 2. The real risk isn't a single power user — it's a cohort of power users who all churn after month 1. But that's a retention problem, not a pricing problem.

---

## UPDATED OPTIONS AFTER CRITIQUE

### Option A (Revised): $9.99/month with Annual Incentive

No changes needed. The math works. The simplicity is a feature.

Add one tweak: **offer a "Legacy Complete" badge and a one-time $20 discount on annual renewal** when a user finishes all 300 questions. This rewards completion and locks in annual retention at the moment the user is most likely to consider canceling.

### Option B (Revised): Lower the Upfront to $49

$79 is too high for consumer conversion. $49 one-time + $2.99/month = $84.88/year, comparable to StoryWorth's $99. But the two-part pricing still adds friction.

### Option C (Revised): Simplify the Transition

Instead of a Level 10 trigger, make it time-based: **$9.99/month for the first 6 months, then $4.99/month automatically.** This removes the gaming incentive and makes the pricing predictable. Users know exactly when their price drops.

---

## RECOMMENDATION: OPTION A — FLAT $9.99/MONTH

Here's why:

### 1. The power user problem doesn't exist at this scale

A user who does 300 conversations costs $16. Your monthly subscription is $9.99. You're underwater by $6 in month 1. But:
- 95% of users won't do 300 conversations in a month
- The 5% who do become your most invested users — they've recorded their entire life story
- By month 2, their AI cost drops to near-zero
- By month 3, you've recouped the loss and they're pure profit
- These users are also your best word-of-mouth marketers

The blended margin across all user types is 94%. You don't need to optimize for the 5% edge case when the 95% is this profitable.

### 2. Simplicity converts

Every pricing complication loses customers. "How much does it cost?" → "$9.99/month." Done. No "well, there's a one-time fee and then a monthly fee" or "it depends on which phase you're in." The user's grandmother doesn't want to think about pricing tiers. She wants to record her stories.

StoryWorth charges $99/year with no usage limits. Remento charges $149/year with no usage limits. The market expectation for legacy/memoir products is simple flat pricing.

### 3. Storage costs are irrelevant

390 MB per user in S3 Intelligent-Tiering costs $0.05/year. Even at 1,000 users with 390 MB each, that's 390 GB = $4.50/month. Storage is not a cost driver that justifies a separate line item. Charging for it would feel petty and erode trust.

### 4. The annual plan solves the binge-and-churn risk

The $89.99/year plan ($7.50/month equivalent) is the real defense against power users. A user who pays $89.99 upfront and does 300 conversations in month 1 has already paid enough to cover the $16 AI cost with $74 left over. Even if they never use the product again, you're profitable.

Push annual aggressively:
- Default the pricing page toggle to "Annual"
- Show "Save 25%" badge
- After the free Level 1 completion, the upgrade prompt should default to annual
- Offer a "Legacy Starter" coupon: first year at $69.99 (still covers the 300-question worst case)

### 5. Add a soft nudge, not a hard gate

Instead of metering or tiered pricing, add a soft engagement nudge for very high-volume users:

After 50 conversations in a single month, show a one-time message:
> "You're on a roll! You've recorded 50 stories this month. At this pace, you'll complete your entire legacy in [X] weeks. Consider switching to an annual plan to save 25%."

This converts bingers to annual (higher LTV) without punishing them or adding pricing complexity.

### Final pricing structure

| | Free | Premium |
|---|---|---|
| **Price** | $0 | **$9.99/month** or **$89.99/year** |
| Content | Level 1 complete (at any pace) | All 10 levels + Life Events + Values & Emotions |
| Conversations | Unlimited within Level 1 | Unlimited |
| Turns per conversation | 4 | 4 |
| AI quality | Full (Haiku + Neural voice) | Full (Haiku + Neural voice) |
| Benefactors | 1, immediate access only | Unlimited, all access condition types |
| Storage | Included | Included |
| Data export | No | Yes |
| Legacy protection | No | Yes |

No usage caps. No storage fees. No metering. No complexity.

The $9.99/month price point works because:
- Average user costs $0.64/month → 94% margin
- Worst-case user costs $16 one-time → break-even in month 2
- Annual plan ($89.99) covers even the worst case with 82% margin
- Simplicity maximizes conversion from the free Level 1 experience

---

*Based on per-conversation cost analysis from SOULREEL_COST_AND_PRICING_REPORT.md, S3 storage patterns from wsDefault/speech.py and wsDefault/storage.py, and the 300-question content volume from the question database structure.*
