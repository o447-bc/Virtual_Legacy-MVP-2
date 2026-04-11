# Claims Gap Analysis — What's Built vs. What's Claimed

## The Problem You Identified

The current claims are heavily weighted toward the future avatar system. The actual running application has substantial, novel, implemented features that are either unclaimed or only lightly touched. Here's the gap analysis.

---

## What's Actually Built and Running (Implemented Features)

### A. Dual-Persona User Management System

The app has a complete dual-persona architecture where users are either a "Legacy Maker" (content creator) or a "Legacy Benefactor" (content viewer). This isn't just a role flag — it's a full system:

1. **Persona selection at signup** — Two distinct signup paths (`SignUpCreateLegacy.tsx` → `create_legacy` / `legacy_maker`, `SignUpStartTheirLegacy.tsx` → `setup_for_someone` / `legacy_benefactor`)
2. **Persona stored in Cognito JWT** — The `profile` claim carries `{"persona_type": "legacy_maker", "initiator_id": "...", "related_user_id": ""}` as JSON
3. **Server-side persona enforcement** — `PersonaValidator` class extracts persona from JWT and gates API access (makers can upload, benefactors can view)
4. **Persona-aware API responses** — `add_persona_context_to_response()` enriches every API response with user context
5. **Pre-signup → temp storage → post-confirmation pipeline** — Persona choice flows through `PersonaSignupTempDB` (with TTL) from pre-signup trigger to post-confirmation trigger, surviving the Cognito confirmation gap
6. **Retry logic with CloudWatch alerting** — Post-confirmation retries persona writes 3 times with backoff, emits `PersonaWriteFailure` metric on exhaustion

**Gap in claims**: NONE of the five patents claim the dual-persona system. Patent #4 mentions "content creator" and "beneficiary" but doesn't claim the persona management architecture — the JWT-embedded persona, the temp-storage pipeline across Cognito triggers, or the server-side enforcement.

### B. Token-Based Invitation System with Cross-Registration Linking

A complete invitation workflow for unregistered users:

1. **Legacy Maker creates assignment** → system checks if benefactor email exists in Cognito
2. **If unregistered** → generates UUID invitation token, stores in `PersonaSignupTempDB` with 30-day TTL, sends email with signup link containing token
3. **Benefactor clicks link** → `SignUpCreateLegacy` detects `?invite=` param, passes token through `signupWithPersona()` as `clientMetadata`
4. **Pre-signup trigger** → stores token in temp DB, auto-confirms user (skips email verification since email was already validated by the invitation)
5. **Post-confirmation trigger** → retrieves token, calls `link_registration_to_assignment()` which validates token, verifies email match, creates relationship record, creates access conditions, and cleans up token
6. **Transactional rollback** — if email sending fails during assignment creation, the system rolls back the relationship record AND the access conditions (no orphaned records)

**Gap in claims**: Patent #4 mentions "designation of a beneficiary" but doesn't claim the invitation token flow, the cross-registration linking, the auto-confirmation for invited users, or the transactional rollback on email failure.

### C. Multi-Modal Content Pipeline (Video + Audio Conversation + Video Memory)

Three distinct content types, all linked to a single question record:

1. **Audio Conversation** — AI-guided WebSocket conversation producing transcripts, scores, and audio files. Stored with `audio*` field prefixes.
2. **Regular Video** — Direct video recording uploaded via presigned URL. Stored with `video*` field prefixes.
3. **Video Memory** — Supplementary video recorded AFTER a conversation completes, linked to the existing conversation record via DynamoDB `update_item` (not a new record). Stored with `videoMemory*` field prefixes.

Each type has its own transcription pipeline, summarization pipeline, and thumbnail generation. The `processVideo` function handles all three with the `isVideoMemory` flag routing to different DynamoDB operations.

**Gap in claims**: Patent #1 mentions video memory in the detailed description but the claims don't specifically claim the multi-modal content linking architecture — the prefix-based field routing, the update-vs-create distinction for video memories, or the three-type content model.

### D. Structured Question Category System with Level Progression

The app has a complete question management system:

1. **Question database** (`allQuestionDB`) with questions organized by type/category
2. **Level progression** (`userQuestionLevelProgressDB`) tracking per-category completion with `remainQuestAtCurrLevel` and `remainQuestTextAtCurrLevel` arrays
3. **Progress summary** with caching (`GetProgressSummary2` function with SSM cache)
4. **Level increment** (`IncrementUserLevel2`) advancing users to next difficulty level within a category
5. **Dashboard visualization** — progress bars per category driving navigation to recording

**Gap in claims**: Patent #3 mentions "configurable score threshold" but doesn't claim the category-based question organization, level progression, or the progress-driven user journey. Patent #1 mentions "life-topic categories" in the description but the claims are generic about "a plurality of life-topic categories" without claiming the level progression mechanic.

### E. Engagement/Streak System with Freeze Mechanics

A complete gamification system:

1. **Daily streak tracking** — `EngagementDB` with `streakCount`, `lastVideoDate`, `streakFreezeAvailable`
2. **Pure function streak calculator** — `calculate_new_streak()` with four cases (same day, +1 day, >1 day with freeze, >1 day without freeze)
3. **Monthly freeze reset** — scheduled Lambda resets `streakFreezeAvailable` on 1st of month
4. **Milestone detection** — `check_milestone()` at 7, 30, 100 days with CloudWatch metrics
5. **Non-blocking integration** — streak update is wrapped in try/except so video upload never fails due to streak errors
6. **Timezone-aware** — uses user's timezone from `userStatusDB` for date calculations

**Gap in claims**: Patent #1 Claim 7 mentions "engagement subsystem" with "streak" and "gamification incentives" but it's a thin dependent claim. The freeze mechanic, monthly reset, milestone detection, and timezone-aware calculation are all unclaimed.

### F. Asynchronous Video Processing Pipeline

A complete event-driven pipeline:

1. **Presigned URL generation** → client uploads directly to S3
2. **ProcessVideo** → verifies S3 object, generates thumbnail via FFmpeg (with smart seek to half-duration), updates DynamoDB, triggers transcription
3. **StartTranscription** → initiates AWS Transcribe job
4. **EventBridge rule** → triggers on transcription completion
5. **ProcessTranscript** → retrieves transcript from S3
6. **SummarizeTranscript** → Bedrock Claude generates one-sentence summary + detailed summary + thoughtfulness score, with idempotency check and enable/disable flag

**Gap in claims**: The video processing pipeline is described in Patent #1 but not claimed. The EventBridge-driven architecture, the FFmpeg thumbnail generation with smart seek, and the idempotent summarization are all unclaimed.

### G. Conversation Summarization with Multi-Type Output

The summarization engine produces three distinct outputs per conversation:

1. `oneSentence` — one-sentence summary
2. `detailedSummary` — comprehensive narrative
3. `thoughtfulnessScore` — 0-5 quality rating

These are stored with type-specific prefixes (`audio*`, `video*`, `videoMemory*`) depending on the content type. The summarization has idempotency checking, enable/disable per question, transcript length limits, and CloudWatch metrics.

**Gap in claims**: Patent #3 Claim 3 mentions summarization but only as "a one-sentence summary, a detailed summary, and a thoughtfulness score." The multi-type prefix routing, idempotency, and the fact that summarization serves as knowledge extraction for the avatar are unclaimed.

---

## Recommendations

### 1. Strengthen Patent #3 (Conversation Engine) — Add Claims for the Full Implemented System

Patent #3 currently claims the scoring/termination loop but misses the surrounding system. Add dependent claims for:

- **Claim 8**: The structured question category system with level progression — questions organized into life-topic categories with per-category level tracking, where completing questions at one level unlocks questions at the next level
- **Claim 9**: The multi-modal content linking — upon conversation completion, offering a supplementary video recording that is linked to the existing conversation record via database update (not a new record), with type-specific field prefixes distinguishing audio conversation data from video memory data
- **Claim 10**: The conversation summarization producing three distinct outputs (one-sentence, detailed, thoughtfulness score) stored with content-type-specific field prefixes, with idempotency checking to prevent duplicate summarization

### 2. Strengthen Patent #4 (Access Control) — Add Claims for Invitation Flow and Persona Management

Patent #4 currently claims the condition evaluation but misses the persona system and invitation flow. Add dependent claims for:

- **Claim 8**: The dual-persona user management — users assigned a persona type (content creator or content viewer) at registration, the persona stored as a JSON object within an authentication token claim, and server-side enforcement of persona-based access control on each API request
- **Claim 9**: The cross-registration invitation linking — when a content creator designates an unregistered beneficiary, generating a unique invitation token with TTL-based expiration, embedding the token in a registration URL, and upon the beneficiary's registration, automatically linking the new account to the pending assignment by validating the token, verifying email match, creating the relationship record, and creating access condition records in a single atomic flow
- **Claim 10**: The transactional rollback — if any step in the assignment creation fails (email sending, token creation, database write), all previously created records are deleted to prevent orphaned data
- **Claim 11**: The pre-signup to post-confirmation data pipeline — persona selection data stored in a temporary database during pre-signup, retrieved and applied during post-confirmation, with TTL-based cleanup of temporary records and retry logic with exponential backoff for persona attribute writes

### 3. Add a New Claim Set to Patent #1 (Data Collection) — Claim the Implemented Content Pipeline

Patent #1 is heavily future-focused. Add claims that anchor it to what's built:

- **Claim 9**: The three-type content model — for each question in the question database, the system supports three content types: an AI-guided audio conversation with depth scoring, a direct video recording, and a supplementary video memory recorded after conversation completion, all linked to a single question record via type-specific database field prefixes
- **Claim 10**: The asynchronous video processing pipeline — upon video upload, triggering a processing chain comprising thumbnail extraction, transcription initiation, event-driven transcript processing, and AI summarization, with each stage operating independently and failing gracefully without affecting the upload success response
- **Claim 11**: The engagement streak system with freeze mechanics — tracking daily content creation activity with a streak counter, a streak freeze mechanism that preserves the streak for one missed day per month, monthly freeze replenishment, and milestone detection at configurable thresholds with metric emission

### 4. Consider a 6th Patent — "Digital Legacy Persona Management and Invitation-Based Onboarding System"

The dual-persona architecture + invitation token flow + cross-registration linking is a substantial, novel, fully-implemented system that doesn't fit cleanly into any of the five existing patents. It could be its own filing:

**Title**: Dual-Persona Digital Legacy Platform with Token-Based Cross-Registration Beneficiary Onboarding

**Core claims would cover**:
- Dual-persona assignment at registration with JWT-embedded persona data
- Server-side persona enforcement via token claim extraction
- Token-based invitation for unregistered beneficiaries with auto-confirmation
- Cross-registration linking (token → relationship + access conditions in one atomic flow)
- Transactional rollback on partial failure
- Temporary data pipeline across authentication trigger stages with TTL cleanup

This is the most "defensible today" patent because every element is fully implemented and running in production.

---

## Summary

| Feature | Currently Claimed? | Recommendation |
|---------|-------------------|----------------|
| Depth scoring + termination | ✅ Patent #3 Claim 1 | Adequate |
| Parallel dual-model LLM | ✅ Patent #3 Claim 2 | Adequate |
| Cascading transcription | ✅ Patent #3 Claim 4 | Adequate |
| Dual-persona management | ❌ Not claimed | Add to Patent #4 or new Patent #6 |
| Invitation token flow | ❌ Not claimed | Add to Patent #4 or new Patent #6 |
| Cross-registration linking | ❌ Not claimed | Add to Patent #4 or new Patent #6 |
| Transactional rollback | ❌ Not claimed | Add to Patent #4 or new Patent #6 |
| Question category + levels | ❌ Not claimed | Add to Patent #3 |
| Multi-modal content linking | ❌ Not claimed | Add to Patent #1 or #3 |
| Video processing pipeline | ❌ Not claimed | Add to Patent #1 |
| Streak + freeze mechanics | ⚠️ Thin dependent claim | Strengthen in Patent #1 |
| Summarization (3 outputs) | ⚠️ Thin dependent claim | Strengthen in Patent #3 |
| Multi-condition access control | ✅ Patent #4 Claim 1 | Adequate |
| Dual-threshold inactivity | ✅ Patent #4 Claims 1,3 | Adequate |
| Avatar data collection | ✅ Patent #1 Claim 1 | Adequate (future) |
| Psychological profiling | ✅ Patent #5 Claim 1 | Adequate (future) |
| Advisory "what would they do" | ✅ Patent #2 Claim 1 | Adequate (future) |

**Bottom line**: The five filings do a good job on the forward-looking avatar features and the core conversation scoring, but they leave the actual running application — the persona system, the invitation flow, the content pipeline, the streak mechanics — largely unclaimed. These are the features that are most defensible right now because they're fully implemented and in production.
