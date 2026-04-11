# SoulReel — Payment & Marketing Strategy

**Prepared**: March 29, 2026  
**Product**: SoulReel (www.soulreel.net)  
**Stage**: Pre-revenue, functional MVP deployed  
**Inventor**: Oliver Richard Astley, Chicago, IL

---

## 1. Website & Code Analysis Summary

### What SoulReel Actually Is

SoulReel is a serverless, AI-powered digital legacy preservation platform. Users ("Legacy Makers") answer guided life questions through real-time AI-moderated voice conversations. A dual-LLM system scores narrative depth in parallel — one model generates empathetic follow-up questions, another scores response quality — and the conversation continues until a cumulative depth threshold is met. This is not a simple video diary. It's a quality-controlled memory extraction pipeline with three planned phases:

- **Phase 1 (Live)**: AI-guided depth-scored conversations + video recordings across 12 life-topic categories with 10 difficulty levels each
- **Phase 2 (Planned)**: Rapid-fire psychological profiling to capture decision-making patterns
- **Phase 3 (Planned)**: AI Avatar with advisory mode — "What would Dad do about this job offer?"

Two provisional patents are filed covering the platform and the avatar system.

### Technical Architecture (Cost-Relevant)

| Component | Service | Cost Driver |
|-----------|---------|-------------|
| Conversation AI | Bedrock Claude 3.5 Sonnet ($6/$30 per 1M tokens) | Per-turn, ~8-20 turns per conversation |
| Depth Scoring | Bedrock Claude 3 Haiku (~$0.25/$1.25 per 1M tokens) | Per-turn, parallel with above |
| Transcription | Deepgram → AWS Transcribe (cascading fallback) | Per audio minute |
| Text-to-Speech | Amazon Polly (neural) | Per character synthesized |
| Video/Audio Storage | S3 with KMS encryption ($0.023/GB/month) | Grows linearly with users |
| Data Egress | S3 → Internet ($0.09/GB after 100GB free) | When benefactors watch videos |
| Database | DynamoDB (9 tables + GSIs) | Read/write capacity units |
| Auth | Cognito | Free tier covers 50K MAU |
| Compute | 40+ Lambda functions | Per-invocation |

**Critical cost insight**: The most expensive component per-user is Bedrock. A single 15-turn conversation costs roughly $0.15-0.40 in LLM tokens alone (Sonnet + Haiku combined). A user completing 5 conversations/week = $0.75-2.00/week in AI costs. At scale, this is the cost that must be covered by pricing.

### Strengths

- **Genuinely novel product**: The depth-scoring conversation engine is patentable and creates a moat. No competitor does quality-controlled AI-guided memory extraction
- **Dual-persona architecture is smart**: Legacy Maker / Benefactor split creates natural viral loops (every maker invites benefactors)
- **Engagement mechanics exist**: Streak counter with freeze, progress bars across 12 categories with level progression — the gamification scaffolding is already built
- **Conditional access control is a killer feature**: Time-delayed, inactivity-triggered ("dead man's switch"), and manual release options. This is the emotional hook that justifies premium pricing
- **Patent protection**: Two provisionals filed covering the core innovation and the avatar roadmap
- **Infrastructure is production-ready**: Cognito auth, KMS encryption, WebSocket real-time conversations, presigned URL uploads — this isn't a prototype

### Opportunities / Friction Points

- **Landing page is generic**: "Preserve Your Legacy" + 3-step "How It Works" doesn't communicate the AI conversation experience or the emotional weight of what's being built. No social proof, no testimonials, no video demo
- **No pricing page, no payment system**: Zero monetization infrastructure exists
- **No onboarding demo**: Users must sign up before they can experience the AI conversation — the highest-value moment is gated behind registration
- **"Start Their Legacy" path is confusing**: The benefactor signup flow (someone signing up on behalf of another person) needs clearer messaging about what happens next
- **No SEO content**: Single landing page, no blog, no question themes page linked from navigation (it exists at `/question-themes` but isn't discoverable)
- **Mobile experience unknown**: The conversation interface uses WebSocket + MediaRecorder API — needs testing on mobile Safari/Chrome
- **No email capture or waitlist**: If someone isn't ready to sign up, there's no way to stay in touch
- **Logo is a placeholder**: "SR" circle + gradient text. Functional but not memorable

---

## 2. Infancy Payment Recommendation (Months 0–12)

### The Core Principle: Don't Charge Until You Have Proof of Retention

SoulReel's biggest risk isn't revenue — it's proving that people will complete enough conversations to build a meaningful legacy. The product's value compounds over time (more conversations = richer legacy = more valuable to benefactors). Charging too early kills the behavior loop before it forms.

### Recommended Model: Generous Free Tier + Soft Paywall at Storage Threshold

**Months 0–6: "Founding Members" Free Access**

| What's Free | Limit |
|-------------|-------|
| AI-guided conversations | 3 per week |
| Video recordings | 3 per week |
| Storage | 5 GB (≈ 25-40 video recordings) |
| Benefactor invites | 2 benefactors |
| Question categories | All 12 unlocked |
| Streak tracking | Full access |

**Why this works**:
- 3 conversations/week is enough to build the habit but creates natural scarcity ("I used my conversations this week, I'll come back Monday")
- 5 GB storage covers roughly 2-3 months of active use before hitting the wall
- 2 benefactors is enough to demonstrate the sharing value but creates upgrade desire for families with multiple children/grandchildren
- All categories unlocked — don't gate content discovery, gate volume

**Estimated AWS cost per free user (active)**:
- 3 conversations/week × $0.25 avg AI cost = $0.75/week = ~$3.25/month
- Storage: negligible at 5 GB ($0.12/month)
- Transcription + Polly: ~$0.50/month
- **Total: ~$4/month per active free user**

This means you need to convert roughly 1 in 4 free users to a $15/month plan to break even. That's achievable.

**Months 3–6: Introduce "Early Supporter" Pricing**

Once you have 50-100 active users and can demonstrate retention data:

| Plan | Price | What It Adds |
|------|-------|-------------|
| Free | $0 | 3 conversations/week, 5 GB, 2 benefactors |
| Early Supporter (annual) | $79/year ($6.58/mo) | Unlimited conversations, 50 GB, 5 benefactors, priority support |
| Early Supporter (monthly) | $9.99/month | Same as annual |

**Why $79/year**: StoryWorth charges $99/year for text-based prompts with a printed book. Remento charges $99/year for voice/video with a book. SoulReel's AI conversation engine is more sophisticated, but you don't have the physical book deliverable yet. $79 positions you as accessible while signaling real value. The "Early Supporter" framing creates urgency and loyalty.

**Lock in the price**: Promise early supporters they keep this rate for life. This creates word-of-mouth ("I got in at $79/year, it's $129 now") and reduces churn.

### Payment Provider: Stripe

- Stripe Checkout for one-click payment (supports Apple Pay, Google Pay out of the box)
- Stripe Billing for subscription management
- Stripe Customer Portal for self-service plan changes/cancellation
- Integration path: Add a Stripe webhook Lambda to your SAM template, store subscription status in a new DynamoDB table (`UserSubscriptionsDB`), check plan limits in your existing Lambda functions

**Do not use Paddle or PayPal as primary**. Stripe's developer experience is unmatched for your stack, and the React + Lambda integration is well-documented. You can add PayPal as a secondary option later.

### Migration Plan: Free → Paid

The trigger for the soft paywall is natural:

1. User hits 5 GB storage → "You've recorded 30 memories. Upgrade to keep going and invite more family members."
2. User tries to invite a 3rd benefactor → "Upgrade to share your legacy with your whole family."
3. User tries a 4th conversation in a week → "You've used your free conversations this week. Upgrade for unlimited."

Each of these moments is a value-proven conversion point — the user has already experienced the product and wants more.

---

## 3. Long-Term Payment Recommendation (12+ Months)

### Tiered Subscription Model

| Feature | Free | Personal ($12.99/mo or $99/yr) | Family ($19.99/mo or $179/yr) | Legacy Vault ($29.99/mo or $249/yr) |
|---------|------|------|--------|-------------|
| AI conversations/week | 3 | Unlimited | Unlimited | Unlimited |
| Storage | 5 GB | 100 GB | 500 GB | 2 TB |
| Benefactor seats | 2 | 5 | 15 | Unlimited |
| Question categories | All 12 | All 12 | All 12 | All 12 |
| Video memory recordings | 3/week | Unlimited | Unlimited | Unlimited |
| Conversation transcripts | View only | Download PDF | Download PDF | Download PDF |
| Access conditions | Immediate only | All 4 types | All 4 types | All 4 types |
| Dead man's switch | — | ✓ | ✓ | ✓ |
| Priority AI (faster responses) | — | — | ✓ | ✓ |
| Legacy export (full archive) | — | — | — | ✓ (annual) |
| Phase 2: Psychological profile | — | — | — | ✓ |
| Phase 3: AI Avatar | — | — | — | ✓ |

### Pricing Rationale

- **Personal at $99/year**: Matches StoryWorth/Remento pricing. Users understand this price point for "memory preservation." The dead man's switch alone justifies the upgrade from free — it's the feature that makes this a legacy tool rather than a journal
- **Family at $179/year**: The jump from 5 to 15 benefactor seats targets families with multiple children, grandchildren, or extended family. $179/year for a family plan is cheaper than 2 individual StoryWorth subscriptions
- **Legacy Vault at $249/year**: This is the premium tier that funds Phase 2 and 3 development. The full archive export and future AI Avatar access are the hooks. Position this as "the complete legacy package"

### Additional Revenue Streams

| Revenue Stream | Price | Rationale |
|----------------|-------|-----------|
| Premium Question Packs | $9.99 one-time | Themed packs: "Wartime Memories," "Immigration Stories," "Entrepreneurship Journey," "Faith & Spirituality." Curated by therapists/historians |
| Legacy Book (printed) | $49.99-79.99 | Partner with a print-on-demand service (Lulu, Blurb) to compile transcripts + photos into a physical book. This is what StoryWorth's entire business model is built on |
| Gift Subscriptions | Same as regular pricing | "Give the gift of legacy" — purchaser buys a subscription for someone else. Huge for holidays (Mother's Day, Father's Day, Christmas, birthdays) |
| Corporate/Enterprise | Custom ($500-2000/yr) | "Company Values" package — executives record their vision, founding stories, leadership principles. Onboarding tool for new employees |
| Therapist/Counselor Licenses | $29.99/mo per practitioner | Life review therapy is a real clinical practice. Therapists use guided reminiscence with elderly patients. SoulReel's AI conversation engine is a natural fit |
| Legacy Transfer Fee | $199 one-time | When a Legacy Maker passes, transfer full ownership of the vault to a designated benefactor. One-time fee covers perpetual storage migration |

### Expected Unit Economics (at scale, 12+ months)

| Metric | Target |
|--------|--------|
| Monthly ARPU (blended) | $10-14 |
| Gross margin | 65-75% (after AWS costs) |
| Monthly churn | 3-5% (annual plans reduce this to <2%) |
| LTV (annual subscriber) | $200-350 |
| CAC target | <$40 |
| LTV:CAC ratio | >5:1 |

### Churn Mitigation

The product has natural churn resistance because of:

1. **Sunk cost of recorded memories**: Users won't abandon 50+ recorded conversations. The data is irreplaceable
2. **Benefactor expectations**: Once family members are invited and viewing content, the maker feels social obligation to continue
3. **Streak mechanics**: Already built. Daily engagement creates habit
4. **Progressive depth**: 12 categories × 10 levels = 120+ unique conversation paths. It takes months to exhaust the content
5. **Dead man's switch**: If you cancel, your conditional access rules stop being monitored. This is the strongest retention lever — "If I cancel, my family might not get access when they need it"

---

## 4. Full Marketing Strategy

### Target Audience Segments (in priority order)

| Segment | Who | Why They Care | Where They Are |
|---------|-----|---------------|----------------|
| 1. Gift Givers (35-55) | Adult children buying for aging parents | "I want to preserve Mom's stories before it's too late" | Facebook, Instagram, Google Shopping, gift guides |
| 2. Legacy-Minded Seniors (60-80) | Retirees, grandparents | "I want my grandchildren to know who I was" | Facebook, church groups, AARP, retirement communities |
| 3. Life Transition Adults (40-65) | People facing mortality (diagnosis, retirement, milestone birthday) | "I need to do this now" | Google Search (high intent), health/wellness communities |
| 4. Genealogy Enthusiasts (30-60) | Family history hobbyists | "This adds the personal stories to my family tree" | Ancestry.com partnerships, genealogy forums, FindAGrave |
| 5. Therapists & Counselors | Mental health professionals using life review therapy | "This is a clinical tool I can use with patients" | Psychology Today, NASW conferences, continuing education |

### Top 5 Acquisition Channels

**1. Facebook/Instagram Ads (Primary — 40% of budget)**

This is where your audience lives. The gift-giving segment (adult children, 35-55) is the most Facebook-active demographic. Creative strategy:

- Video ads showing a real conversation in progress (the AI asking a follow-up question, the user's face lighting up as they remember something)
- Carousel ads: "12 categories of questions your parents will love answering"
- Seasonal pushes: Mother's Day (May), Father's Day (June), Grandparents Day (September), Christmas (November-December)
- Retargeting: Anyone who visits the site but doesn't sign up gets a "Your family's stories are waiting" ad

**2. Google Search (High Intent — 25% of budget)**

Target keywords:
- "preserve family stories" / "record family memories"
- "gift for parent who has everything"
- "digital legacy" / "legacy preservation"
- "StoryWorth alternative" / "Remento alternative"
- "record grandparent stories" / "interview parents about their life"
- "end of life planning" / "what to do before parent dies"

**3. Content Marketing / SEO (Long-term — 15% of budget)**

Blog content pillars:
- "Questions to Ask" series: "50 Questions to Ask Your Mom Before It's Too Late," "Questions About Dad's Childhood You Never Thought to Ask" — these are high-search-volume, emotionally resonant, and naturally lead to "SoulReel asks these for you, with AI follow-ups"
- Legacy planning guides: "Digital Legacy Checklist," "How to Preserve Family Stories"
- Competitor comparisons: "SoulReel vs StoryWorth: Why AI-Guided Conversations Capture Deeper Stories"
- Question themes page (already built at `/question-themes`) should be linked from main nav and optimized for SEO

**4. Referral Program (Viral — 10% of budget)**

The dual-persona architecture is a built-in referral engine:
- Every Legacy Maker invites 2-5 benefactors
- Every benefactor who watches a video gets a prompt: "Want to create your own legacy? Start free"
- Incentive: "Invite a friend to create their legacy → both get 1 month free"
- The benefactor-to-maker conversion is the most powerful growth loop. Someone who watches their parent's legacy videos is emotionally primed to create their own

**5. Partnerships (Relationship-driven — 10% of budget)**

- **Ancestry.com / FamilySearch**: "You've built the tree. Now add the stories." Integration or co-marketing
- **Retirement communities / senior living**: Bulk licenses, activity directors use it as a group activity
- **Funeral homes / estate planners**: "Recommend SoulReel to clients as part of end-of-life planning"
- **Churches / faith communities**: "Record your testimony" — faith-based question packs
- **Therapists**: Life review therapy practitioners (see revenue stream above)

### Messaging Framework

**Core positioning**: "The AI that helps you tell your life story — so the people you love never have to wonder who you were."

**Tagline options** (test these):
- "Your stories. Their inheritance."
- "Every family has a story worth hearing."
- "The legacy that outlasts everything."

**Emotional hooks by segment**:
- Gift givers: "The gift they'll talk about for generations"
- Seniors: "Your grandchildren want to hear your stories. We help you tell them."
- Life transition: "You have stories no one else can tell. Don't let them disappear."
- Genealogy: "Names and dates tell you who they were. Stories tell you who they really were."

**Key differentiator messaging** (vs StoryWorth/Remento):
- "StoryWorth sends questions. SoulReel has conversations." — emphasize the AI follow-up, the depth scoring, the fact that it doesn't accept shallow answers
- "Other apps record what you say. SoulReel helps you say what matters." — the depth-scoring engine is the moat
- "Your stories are protected by conditions you set — released only when you decide." — the access control system is unique

### Launch Sequence (First 90 Days of Marketing)

**Week 1-2: Soft Launch**
- Personal network outreach (friends, family, LinkedIn)
- 10-20 "founding member" users for testimonials and feedback
- Record 2-3 demo conversations to use in marketing materials

**Week 3-4: Content Foundation**
- Publish 5 SEO blog posts (questions-to-ask series)
- Create 30-second demo video showing a real AI conversation
- Set up Facebook pixel and Google Analytics
- Link `/question-themes` from main navigation

**Week 5-8: Paid Acquisition Test**
- $500-1000 Facebook/Instagram test budget
- 3-4 ad creative variants (video demo, carousel, testimonial, emotional hook)
- Google Search ads on top 10 keywords
- Measure: CPC, signup rate, conversation completion rate

**Week 9-12: Optimize and Scale**
- Kill underperforming ads, double down on winners
- Launch referral program
- First partnership outreach (2-3 retirement communities, 1 genealogy org)
- Introduce Early Supporter pricing based on conversion data

### KPIs to Track

| Metric | Target (Month 3) | Target (Month 12) |
|--------|-------------------|---------------------|
| Monthly signups | 100-200 | 1,000-2,000 |
| Signup → first conversation | >60% | >70% |
| First conversation → 5th conversation | >30% | >40% |
| Free → paid conversion | 5-10% | 15-20% |
| Benefactor invite rate | 1.5 per maker | 2.5 per maker |
| Benefactor → maker conversion | 5% | 10% |
| Monthly churn (paid) | <8% | <5% |
| CAC (blended) | <$30 | <$25 |
| NPS | >40 | >50 |

---

## 5. Implementation Roadmap

### Next 30 Days (Critical Path)

| Priority | Task | Effort |
|----------|------|--------|
| 1 | Redesign landing page: add demo video, social proof section, email capture for non-ready visitors, link to `/question-themes` | 3-5 days |
| 2 | Integrate Stripe: add `UserSubscriptionsDB` DynamoDB table, Stripe webhook Lambda, plan-checking middleware in existing Lambdas | 5-7 days |
| 3 | Implement usage limits: conversation count per week, storage quota check before upload, benefactor seat limit | 3-4 days |
| 4 | Add "Upgrade" prompts at natural friction points (storage full, conversation limit hit, 3rd benefactor invite) | 2-3 days |
| 5 | Set up Facebook pixel, Google Analytics 4, and basic conversion tracking | 1 day |
| 6 | Record 2-3 demo conversations for marketing use | 1-2 days |

### Next 90 Days

| Priority | Task |
|----------|------|
| 7 | Launch blog with 5 SEO-optimized "questions to ask" articles |
| 8 | Build pricing page with plan comparison table |
| 9 | Implement gift subscription purchase flow |
| 10 | Launch Facebook/Instagram ad campaigns ($500-1000/month test budget) |
| 11 | Build referral system (unique invite links with tracking) |
| 12 | Add email onboarding sequence (Day 1, 3, 7, 14 — nudge toward first conversation) |
| 13 | Implement Stripe Customer Portal for self-service subscription management |

### Next 180 Days

| Priority | Task |
|----------|------|
| 14 | Launch printed Legacy Book integration (Lulu/Blurb API) |
| 15 | Build premium question pack marketplace |
| 16 | Partnership outreach: 5 retirement communities, 2 genealogy orgs, 10 therapists |
| 17 | Implement annual plan with discount |
| 18 | Begin Phase 2 (psychological profiling) development — this becomes the Legacy Vault tier differentiator |
| 19 | Corporate/enterprise pilot with 1-2 companies |

### Quick AWS Optimizations (Do Now)

1. **Move completed conversation audio to S3 Intelligent-Tiering**: Audio from completed conversations is rarely re-accessed. Intelligent-Tiering automatically moves infrequently accessed objects to cheaper storage classes, saving 40-70% on storage for older content
2. **Switch depth scoring from Claude 3 Haiku to Amazon Nova Micro**: At $0.035/$0.14 per 1M tokens vs Haiku's $0.25/$1.25, this is an 85% cost reduction on scoring with comparable quality for a numeric depth score task
3. **Add CloudFront in front of S3 for video delivery**: Reduces egress costs and improves playback latency for benefactors. CloudFront's first 1 TB/month is free
4. **Cache Polly audio responses**: If the same AI text is generated for common follow-up patterns, cache the Polly output in S3 rather than re-synthesizing

---

## 6. Risks & Mitigations

### Risk 1: Video Storage Costs Scale Faster Than Revenue

**Scenario**: 1,000 active users × 50 GB average storage = 50 TB × $0.023/GB = $1,150/month in storage alone, plus egress when benefactors watch.

**Mitigation**:
- S3 Intelligent-Tiering (automatic, saves 40-70% on older content)
- Storage quotas per plan tier (5 GB free, 100 GB personal, 500 GB family)
- Video compression on upload (client-side, before S3) — most phone video is 1080p but 720p is sufficient for talking-head recordings. This halves storage per video
- Lifecycle policies: move content older than 1 year to S3 Glacier Instant Retrieval ($0.004/GB/month — 83% cheaper than Standard)

### Risk 2: Bedrock AI Costs Per Conversation Are Too High

**Scenario**: At scale, Claude 3.5 Sonnet at $6/$30 per 1M tokens becomes the dominant cost. 10,000 conversations/month × $0.30 avg = $3,000/month in LLM costs alone.

**Mitigation**:
- Switch response generation to Claude 3.5 Haiku or Amazon Nova Pro for most conversations (80% cheaper, still high quality for empathetic interviewing)
- Reserve Sonnet for the first 2-3 turns (where question quality matters most) then downgrade to a cheaper model for follow-ups
- Implement prompt caching (Bedrock supports this) — system prompts are identical across conversations, cache them
- Batch inference for summarization (50% discount, not latency-sensitive)

### Risk 3: Low Conversion from Free to Paid

**Scenario**: Users record 3-5 conversations, feel "done," and never hit the paywall.

**Mitigation**:
- The 12-category × 10-level structure creates 120+ conversation paths — communicate this depth during onboarding ("You've completed 4 of 120 conversations")
- Streak mechanics create daily engagement habit
- Benefactor notifications ("Your daughter watched your childhood story") create social motivation to continue
- The dead man's switch is only available on paid plans — this is the strongest conversion lever for the target demographic

### Risk 4: User Trust and Data Sensitivity

**Scenario**: Users are sharing deeply personal stories. Any data breach or perceived misuse destroys the brand.

**Mitigation**:
- KMS encryption at rest is already implemented — communicate this clearly on the site
- Add a "Privacy Promise" page: "Your stories are encrypted, never used for AI training, and only accessible to people you choose"
- SOC 2 compliance roadmap (not needed now, but plan for it before enterprise sales)
- The conditional access control system is itself a trust signal — "You control who sees your stories, and when"

### Risk 5: Competitor Response (StoryWorth, Remento Add AI)

**Scenario**: StoryWorth or Remento adds AI-guided conversations to their existing platforms.

**Mitigation**:
- Patent protection (two provisionals filed) covers the depth-scoring conversation engine and the avatar pipeline
- First-mover advantage on the avatar roadmap — Phase 2 and 3 are years of development that competitors would need to replicate
- The conditional access control system (dead man's switch, inactivity triggers) is a unique feature neither competitor has
- Focus on the "conversation" differentiator: "They send questions. We have conversations."

### Risk 6: Gift Subscription Seasonality

**Scenario**: 60-70% of revenue comes in Q4 (holiday gifts), creating cash flow volatility.

**Mitigation**:
- Annual subscriptions smooth revenue recognition
- Market aggressively around non-holiday moments: Mother's Day (May), Father's Day (June), Grandparents Day (September), milestone birthdays
- The "life transition" segment (diagnosis, retirement) is not seasonal — invest in Google Search for these high-intent, year-round queries
- Corporate/enterprise revenue is not seasonal

---

*This strategy is designed to be executed incrementally. The first 30 days focus on Stripe integration and landing page improvements — everything else builds on that foundation. The product is strong. The technology is differentiated. The market timing is right (aging Boomers, AI normalization, post-COVID family connection desire). The path from here is: prove retention → prove conversion → scale acquisition.*
