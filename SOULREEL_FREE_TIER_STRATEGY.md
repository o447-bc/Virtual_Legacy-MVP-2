# SoulReel — Free Tier Strategy: Marketing Analysis & Recommendations

**Date**: April 25, 2026
**Perspective**: Consumer internet marketing, freemium conversion optimization

---

## PRODUCT ANALYSIS

SoulReel is an emotional product. That's the single most important thing to understand before designing the free tier.

Users aren't signing up to manage a database or track a metric. They're sitting down to talk about the day their father died, the moment they held their first child, or the lesson they want their grandchildren to remember. The AI asks follow-up questions. The user hears their own voice played back alongside an empathetic AI interviewer. They see a transcript and summary of something deeply personal they've never articulated before.

That emotional moment — hearing yourself tell a story you've never told, and realizing it matters — is the conversion event. Everything about the free tier should be designed to get users to that moment as fast as possible, and then make them feel the wall when it's taken away.

### What the product offers (by content path)

1. **Life Story Reflections** — 12 question categories progressing from "Childhood Memories" (Level 1, light/nostalgic) to "Messages to Loved Ones" (Level 9–10, deeply emotional). Free users currently get Level 1 only.

2. **Life Events** — Personalized questions based on the user's actual life (marriage, children, loss, career). Generated from the onboarding survey. Premium only.

3. **Values & Emotions** — Psychological assessments with AI-generated personality narratives. Premium only.

4. **Benefactor Access** — Sharing content with family under conditional access rules (dead man's switch, time-delay, etc.). Free users get 2 benefactors with immediate access only.

### The emotional arc of the product

```
Signup → Life Events Survey (emotional priming) → First Conversation (the hook)
→ See transcript/summary (the "wow") → Want to share with family (the pull)
→ Want deeper questions (the hunger) → Hit the wall → Convert or leave
```

The survey is brilliant marketing even if users never pay — it forces them to mentally catalog their life's most significant moments. By the time they finish checking "death of a parent" and typing their mother's name, they're emotionally invested. The product has already started working before the first conversation.

---

## THE FREE USER COST PROBLEM

From the cost report (4 turns per conversation):

| Free Tier Config | Cost per free user/month | 485 active free users/month |
|---|---|---|
| 2 convos/week, 4 turns, Haiku model | $0.66 | $320 |
| 2 convos/week, 3 turns, Haiku model | $0.50 | $243 |
| 2 convos/week, 3 turns, Nova Lite v1 | $0.16 | $78 |
| 1 convo/week, 3 turns, Nova Lite v1 | $0.08 | $39 |

The tension: every dollar spent on free users is an investment in conversion. Cut too deep and users never feel the product. Spend too much and you're subsidizing people who will never pay.

The key insight: **the first conversation is worth 10x more than the fifth.** The marginal emotional impact of conversation #1 is enormous. Conversation #5 is habit. Conversation #10 is routine. You need to fund the first few experiences generously, then gate aggressively.

---

## THREE FREE TIER OPTIONS

### Option A: "The Taste" — 1 Conversation/Week, 3 Turns, Level 1 Only

**What the user gets:**
- 1 AI conversation per week (3 turns each)
- Life Story Reflections Level 1 only (Childhood Memories, Family & Upbringing, School Days, Friends)
- 1 benefactor, immediate access only
- No Life Events, no Values & Emotions
- Economy AI voice (Polly Standard)
- No data export

**What the user feels:**
They get one conversation per week. It's short — 3 turns means the AI asks the question, the user responds, the AI follows up once, the user responds again, the AI wraps up. It's enough to feel the magic of the AI interview format, but it ends before the conversation gets deep. The questions stay surface-level (childhood, school). They can share with one person.

**Conversion trigger:** "I want to talk about the hard stuff. I want to tell the story about losing my mom. I want my kids to hear this." They can see the Life Events and Values & Emotions paths on the dashboard but can't access them. The survey already made them think about those events.

**Cost per active free user:** ~$0.08/month (Nova Lite, 1 convo/week, 3 turns)
**Cost for 485 active free users:** ~$39/month

**Pros:**
- Cheapest option by far
- Clear, simple limit (1/week)
- Strong upgrade motivation — users feel constrained quickly

**Cons:**
- May not be enough to hook users. One 3-turn conversation per week is ~90 seconds of actual talking. Some users will bounce before feeling the emotional payoff.
- The AI voice quality difference (Standard vs Neural) may make the free experience feel cheap
- Risk of high churn before conversion — users leave before they're invested

---

### Option B: "The Hook" — 3 Conversations Total (Lifetime), Full Quality, Then Lock

**What the user gets:**
- 3 total AI conversations (not per week — lifetime on free tier)
- Full 4 turns per conversation
- Full AI quality (Haiku model, Neural voice) — identical to paid experience
- Access to Level 1 AND Level 2 questions (Childhood + Hobbies/Traditions)
- Life Events survey completed, but Life Events questions locked with a teaser: "12 personalized questions are waiting for you"
- 1 benefactor, immediate access only
- After 3 conversations: dashboard shows completed conversations with transcripts, but "Start Conversation" button becomes an upgrade prompt

**What the user feels:**
The first 3 conversations are the real product. Full quality. No compromises. The user records a childhood memory, a story about their family, maybe a holiday tradition. They hear the Neural voice. They see the AI summary. They feel it.

Then it stops. The dashboard still shows their progress. Their 3 completed conversations sit there with transcripts and summaries. The Life Events section shows "12 questions personalized for you" with a lock icon. The Values & Emotions section shows available assessments they can't take. The "Start Conversation" button says "Upgrade to continue your legacy."

They've already invested. They've already told 3 stories. Walking away means those stories sit incomplete. Their family can't see the deeper stuff. The sunk cost is emotional, not financial.

**Conversion trigger:** "I've already started. I can see my personalized questions waiting. My daughter is already set up as a benefactor. I need to keep going."

**Cost per active free user:** ~$0.16 total (3 conversations × $0.053 each, one-time)
**Cost for 485 active free users:** ~$78 total (one-time, not recurring)

**Pros:**
- Users experience the REAL product, not a degraded version
- Emotional sunk cost is powerful — they've already recorded personal stories
- One-time cost, not recurring — free users who don't convert stop costing money after 3 conversations
- The "personalized questions waiting" message from the survey creates FOMO
- No weekly drip means faster time-to-conversion (days, not weeks)

**Cons:**
- No ongoing engagement for free users — once they use 3 conversations, the product goes silent unless they convert
- Some users may feel tricked ("I thought it was free")
- Need clear messaging: "3 free conversations to start your legacy"

---

### Option C: "The Drip" — 2 Conversations/Week, But Progressive Lockout After 2 Weeks

**What the user gets:**
- Week 1–2: 2 conversations/week, 4 turns, full quality (Haiku, Neural voice)
- Access to Level 1 AND Level 2 questions
- Life Events survey completed, 1 preview Life Events question unlocked
- 2 benefactors, immediate access only
- Week 3+: Drops to 1 conversation/week, 3 turns, economy model (Nova Lite, Standard voice)
- After week 4: Conversations locked entirely. Dashboard becomes read-only with upgrade prompts.

**What the user feels:**
The first two weeks feel generous. Two conversations a week, good quality, interesting questions. They complete the survey, see their personalized questions, maybe try the one free Life Events preview question. They add a benefactor.

Week 3, the experience degrades. The AI voice sounds different. The conversations are shorter. The questions repeat from the same shallow pool. It feels like the product is fading.

Week 4, it stops. "You've completed your free trial. Upgrade to continue." But their dashboard still shows everything they've built — completed conversations, transcripts, their benefactor connection, the locked Life Events questions.

**Conversion trigger:** The degradation itself. Users who experienced the good version in weeks 1–2 feel the loss in week 3. By week 4, they either convert or leave — but the ones who felt the product in weeks 1–2 have a strong pull to come back.

**Cost per active free user:** ~$0.55 total over 4 weeks (8 full convos + 2 degraded + lockout)
**Cost for 485 active free users:** ~$267 total (one-time over the 4-week window)

**Pros:**
- Longest engagement window — 4 weeks of product exposure
- The degradation creates a visceral "I want the good version back" feeling
- The preview Life Events question lets users taste personalization
- Most similar to how successful apps (Spotify, Headspace) handle free tiers

**Cons:**
- Most expensive option
- Complex to implement (time-based tier changes, quality switching)
- The degradation might feel punitive rather than motivating
- 4 weeks is a long time — some users will form habits around the degraded version and never convert

---

## RECOMMENDATION: OPTION B HYBRID — "Complete Level 1, Full Quality, At Your Own Pace"

After reviewing the options, the strongest approach combines Option B's full-quality philosophy with a content-based gate instead of a conversation-count gate.

### The design

```
Free tier:
- Complete ALL of Level 1 at any pace — no weekly limits, no turn limits
- 4 turns per conversation (same as paid)
- Claude 3.5 Haiku model (same as paid)
- Polly Neural voice (same as paid)
- All 4 Level 1 categories:
    • Childhood Memories
    • Family & Upbringing
    • School Days & Education
    • Friends & Important Relationships (youth)
- Life Events survey completed, questions visible but locked
- 1 benefactor, immediate access only
- After Level 1 complete: dashboard shows Level 2 locked + upgrade prompts
- Life Events and Values & Emotions visible but locked throughout
```

### Why this is better than a hard conversation cap

**1. It respects the user's pace — and that matters for this demographic.**

SoulReel's likely core users are 45–75 years old. Some will do one conversation a day. Some will do one a week. Some will binge 5 in a weekend when the grandkids visit and inspire them. A "3 conversations lifetime" cap punishes the binger and frustrates the slow starter equally. "Complete Level 1" lets both user types find their rhythm. The grandmother who does one conversation every Sunday afternoon for a month gets the same full experience as the retiree who knocks out Level 1 in a weekend.

**2. Completing a level is a natural emotional milestone — hitting a number isn't.**

"You've used 3 of 3 conversations" feels like a meter running out. "You've completed Level 1 — Childhood Memories, Family & Upbringing, School Days, and Friends" feels like an achievement. The user has a body of work. They've told their childhood stories. They can see them on their dashboard. They feel accomplished AND hungry for more.

The wall hits at exactly the right emotional moment: "You've told the easy stories. The deeper ones — your career, your proudest moments, your hardest times, your messages to your loved ones — are waiting in Levels 2 through 10."

**3. The content itself creates the conversion pressure.**

Look at what's locked behind Level 2+:

| Level | What Unlocks | Emotional Weight |
|---|---|---|
| Level 2 | Hobbies, Traditions & Holidays | Medium — personal joy |
| Level 3 | Love, Romance & Early Partnerships | High — vulnerability begins |
| Level 4 | Work & Career Beginnings | Medium — identity |
| Level 5 | Proudest Moments & Achievements | High — self-worth |
| Level 6 | Challenges & Hard Times | Very high — real vulnerability |
| Level 7 | Values & Guiding Principles | High — legacy core |
| Level 9–10 | Messages to Loved Ones | Maximum — the whole point |

A user who completed Level 1 can see this progression. They know "Messages to Loved Ones" exists at Level 9–10. They know their Life Events questions are waiting. The product has shown them the map and said "you've walked the first mile — the rest of the journey is here when you're ready."

That's infinitely more compelling than "you've used 3 of 3 conversations."

**4. It's self-limiting on cost without feeling limiting to the user.**

Level 1 has 4 question categories. Each category likely has 3–8 questions at difficulty 1. That's roughly **12–30 conversations** to complete Level 1 — a meaningful amount of content, but finite.

Estimated cost per free user completing all of Level 1:

| Questions | Conversations | Cost per user |
|---|---|---|
| 12 (low estimate) | 12 × $0.053 | $0.64 |
| 20 (mid estimate) | 20 × $0.053 | $1.06 |
| 30 (high estimate) | 30 × $0.053 | $1.59 |

At the mid estimate, 3,233 free signups × 15% active × $1.06 = **$514 total** to acquire 100 paid users. That's a customer acquisition cost of **$5.14 per paid user** — excellent for a $9.99/month subscription.

But here's the key: most free users won't complete Level 1. Industry data shows ~30% of signups never complete onboarding, ~40% use the product once and leave. Of the 3,233 free signups:
- ~970 never finish onboarding (cost: $0)
- ~1,293 do 1–3 conversations and leave (cost: ~$0.10–$0.16 each = ~$160)
- ~485 become active and work through Level 1 (cost: ~$1.06 each = ~$514)
- ~485 × some fraction actually complete Level 1 and hit the wall

**Realistic total free-user cost: ~$350–$500 one-time** to generate 100 paid users.

**5. After Level 1, non-converting users cost $0/month.**

Same as Option B — once a user completes Level 1 (or abandons), they stop generating AI costs. The dashboard becomes a read-only showcase of their completed stories plus upgrade prompts. No recurring free-rider cost.

### What the upgrade wall looks like

When a user completes their last Level 1 question:

```
🎉 Level 1 Complete!

You've recorded [X] stories about your childhood, family, school days,
and early friendships. Your legacy is off to a beautiful start.

Ready for the deeper questions?

Level 2 unlocks Hobbies, Traditions & Holidays
Level 3 unlocks Love, Romance & Partnerships
...
Level 9-10 unlocks Messages to Your Loved Ones

Plus: [12] personalized Life Events questions are waiting for you.

[Upgrade to Premium — $9.99/month]
```

On subsequent dashboard visits, the Level 1 card shows a green checkmark. The Level 2+ cards show lock icons with "Upgrade to unlock." The Life Events card shows the count of personalized questions waiting. The Values & Emotions card shows available assessments.

### Upgrade prompt timing

- **After completing 50% of Level 1:** Soft banner: "You're halfway through Level 1. Premium unlocks 9 more levels of deeper questions."
- **After completing Level 1:** Full celebration screen + upgrade CTA (shown above)
- **Every dashboard visit after Level 1 complete:** Persistent but non-intrusive "Continue your legacy" section
- **Weekly email after Level 1 complete:** "Your [X] stories are preserved. Your family is waiting for the deeper ones."
- **If benefactor is set up:** "Your [benefactor name] can see your Level 1 stories. Upgrade to share the stories that really matter."

### Cost model update

| Metric | Previous (2/week recurring) | This approach (Level 1 complete) |
|---|---|---|
| Cost per free user who completes Level 1 | $0.16/month recurring | ~$1.06 one-time |
| Cost per free user who bounces early | $0.16/month recurring | ~$0.10–$0.16 one-time |
| Monthly recurring free-user cost | $78/month | $0 (after initial cohort) |
| Cost to acquire 100 paid users (3% conv) | $936/year | ~$400–$500 one-time |
| Ongoing cost for new signups | Same monthly rate | ~$0.50 avg per new signup |

### What to show on the pricing page

**Free Plan:**
- Complete Level 1 — Childhood, Family, School & Friends
- Full AI interview experience (same quality as Premium)
- Share with 1 family member
- Your stories are yours forever

**Premium Plan — $9.99/month:**
- All 10 levels — from Childhood to Messages to Loved Ones
- Personalized Life Events questions
- Values & Emotions assessments
- Unlimited benefactors with advanced access controls
- Data export & legacy protection

The free tier description emphasizes what you GET (a complete level, full quality, permanent access to your stories) rather than what you DON'T get. The premium description emphasizes the emotional progression — "from Childhood to Messages to Loved Ones" tells the user exactly what they're missing.

---

*This analysis is based on the product architecture in FrontEndCode/src/, the cost model in SOULREEL_COST_AND_PRICING_REPORT.md, the question theme structure in QuestionThemes.tsx, and conversion rate research from Section 13 of the cost report.*
