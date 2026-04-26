# SoulReel — Comprehensive Project Summary for AI Consumption

**Document Date:** April 26, 2026
**Scope:** Complete technical, architectural, business, and operational summary of the SoulReel platform
**Purpose:** Provide any AI assistant with full context to understand, modify, debug, and extend this codebase

---

## TABLE OF CONTENTS

1. Project Purpose & Vision
2. Business Model & Competitive Position
3. Technology Stack
4. Repository Structure
5. Backend Architecture — AWS SAM & Lambda
6. Frontend Architecture — React & Amplify
7. Database Schema — DynamoDB
8. Authentication & Authorization
9. API Specification
10. AI Conversation Engine
11. Video Recording & Transcription Pipeline
12. Psychological Testing Framework
13. Benefactor & Access Control System
14. Data Retention & Account Lifecycle
15. Billing & Subscription System (Stripe)
16. Email System (SES)
17. Admin Console
18. CI/CD Pipelines
19. Security Architecture
20. Cost Analysis & Pricing Strategy
21. Technical Debt & Known Issues
22. Intellectual Property & Patents
23. Steering Rules & Development Conventions
24. Feature Specs & Roadmap

---

## 1. PROJECT PURPOSE & VISION

SoulReel (codebase name: "Virtual Legacy") is an AI-powered digital legacy preservation platform. Users — called "Legacy Makers" — record personal memories by answering structured life story questions through AI-guided voice conversations. The platform captures video and audio responses, transcribes them, generates AI summaries, and stores everything in encrypted cloud storage. Users designate "Benefactors" (family members, friends) who can access the recorded stories under configurable conditions — immediately, on a future date, after a period of inactivity (dead man's switch), or via manual release.

The three-phase vision:

- **Phase 1 (Implemented):** Deep narrative collection via AI-moderated voice conversations with real-time depth scoring, video memory recordings, transcription, and AI summarization. Structured question categories with level progression.
- **Phase 2 (Partially Implemented):** Psychological profiling via standardized personality assessments (Big Five, Jungian Type, Emotional Intelligence). Captures decision-making patterns, values hierarchies, and cognitive tendencies.
- **Phase 3 (Planned):** AI Avatar construction from combined narrative data + psychological profile + voice/video samples. Advisory mode where benefactors can ask "What would [person] do about X?" and receive grounded responses with attribution.

The platform is live at **https://www.soulreel.net** and serves real users.

---

## 2. BUSINESS MODEL & COMPETITIVE POSITION

### Pricing Model (Current — V2 In Progress)

The pricing strategy has evolved through multiple iterations. The current live model uses a simplified 2-tier approach:

| Feature | Free | Premium |
|---------|------|---------|
| Monthly Price | $0 | $14.99/month |
| Annual Price | $0 | $149/year |
| Content Access | Level 1 only (Life Story Reflections) | All 10 levels + Life Events + Values & Emotions |
| AI Quality | Full (same Haiku model, Neural voice, 4 turns) | Full |
| Conversation Limits | Unlimited within Level 1 | Unlimited |
| Benefactors | 1 (immediate access only) | Unlimited (all access condition types) |
| Psych Tests | 1 free test | All tests |
| Data Export | GDPR text-only | Full Content Package |
| Legacy Protection | No | Yes |

The key insight: free users get the complete Level 1 experience at full AI quality with no weekly limits. The gate is content progression, not degraded experience. After completing Level 1, non-converting users cost $0/month (no ongoing AI costs). This replaces an earlier 4-tier model (Free/Personal/Family/Vault at $9.99/$89.99).

A "Founding Member" rate of $99/year is available for the first 100 subscribers.

### Cost Structure

At 100 paid users, estimated monthly infrastructure cost is $145–$300:
- AI Conversation Engine (Bedrock + Deepgram + Polly): ~$49 (28.5%)
- Stripe Payment Processing: ~$32 (18.4%)
- Video Recording & Transcription: ~$30 (17.5%)
- Security & Compliance (KMS, CloudTrail, GuardDuty): ~$18 (10.4%)
- Lambda Compute: ~$5 (3.1%)
- DynamoDB: ~$4 (2.3%)
- Everything else: ~$10

Per paid user: ~$1.48–$1.88/month fully loaded. At $14.99/month, that is ~80% gross margin.

### Competitors

| Platform | Price | Differentiator vs SoulReel |
|----------|-------|---------------------------|
| StoryWorth | $99/year | Text-only prompts, printed book. No AI, no video, no access controls. |
| Eternos | $25–$49/month + $995 upfront | AI avatar creation. 10+ hour setup. Much more expensive. |
| Remento | $149/year | Voice prompts, multimedia. No AI conversation. |
| StoriedLife AI | $14.99/month | AI memoir assistant. Text-based only. |

SoulReel's unique differentiators: real-time AI-guided voice conversations with depth scoring, conditional access controls (dead man's switch), psychological testing integration, and video + audio multimodal capture.

---

## 3. TECHNOLOGY STACK

### Frontend
- **Framework:** React 18.3.1 + TypeScript 5.5.3
- **Build Tool:** Vite 5.4.1 with SWC plugin
- **Routing:** React Router DOM 6.26.2
- **State Management:** TanStack Query 5.56.2 (server state), React Context (auth), localStorage (caching)
- **UI Components:** shadcn/ui (50+ components) built on Radix UI primitives
- **Styling:** Tailwind CSS 3.4.11 with custom design tokens (legacy-purple, legacy-navy)
- **Forms:** React Hook Form 7.53.0 + Zod 3.23.8
- **Charts:** Recharts 2.12.7
- **Icons:** Lucide React 0.462.0
- **AWS Integration:** AWS Amplify 6.15.1 (auth + storage)
- **Testing:** Vitest 4.0.18 + React Testing Library + fast-check (property-based)
- **Hosting:** AWS Amplify (app ID: d33jt7rnrasyvj, branch: main)

### Backend
- **Framework:** AWS SAM (Serverless Application Model)
- **Runtime:** Python 3.12
- **Architecture:** ARM64 (Graviton) for most functions, x86_64 for FFmpeg-dependent functions
- **Functions:** 69+ Lambda functions across 21 functional categories
- **API:** API Gateway REST (Cognito-authorized) + WebSocket API (custom authorizer)
- **Database:** DynamoDB (17+ tables), all PAY_PER_REQUEST, KMS-encrypted, PITR-enabled
- **Storage:** S3 (virtual-legacy bucket), KMS-encrypted, Intelligent-Tiering lifecycle
- **AI/ML:** AWS Bedrock (Claude 3.5 Haiku for conversations, Nova Micro for scoring), Amazon Polly Neural (TTS), Deepgram Nova-2 (real-time STT), AWS Transcribe (batch fallback)
- **Email:** AWS SES
- **Auth:** AWS Cognito (User Pool us-east-1_KsG65yYlo)
- **Payments:** Stripe (checkout, webhooks, customer portal)
- **Monitoring:** CloudTrail, GuardDuty, CloudWatch
- **Scheduling:** EventBridge (cron rules for scheduled jobs)
- **Caching:** SSM Parameter Store (cache-aside pattern)

### Infrastructure
- **Region:** us-east-1
- **Stack Name:** Virtual-Legacy-MVP-1
- **Custom Domain:** www.soulreel.net
- **API Gateway:** https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod
- **WebSocket:** wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod
- **AWS Account:** 962214556635

---

## 4. REPOSITORY STRUCTURE

```
/
├── .github/workflows/          # CI/CD pipelines
│   ├── backend.yml             # SAM build, validate, test, deploy
│   └── frontend.yml            # TypeScript check, lint, build, Amplify deploy
├── .kiro/
│   ├── specs/                  # 16 feature specifications (requirements, design, tasks)
│   └── steering/               # 6 development convention rules
├── FrontEndCode/               # React frontend application
│   ├── src/
│   │   ├── components/         # 9 custom + 50+ shadcn/ui components
│   │   ├── pages/              # 25 page components
│   │   ├── contexts/           # AuthContext, SubscriptionContext
│   │   ├── services/           # API integration layer (6+ modules)
│   │   ├── config/             # API endpoint configuration
│   │   ├── hooks/              # Custom React hooks
│   │   ├── types/              # TypeScript type definitions
│   │   └── lib/                # Utility functions
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
├── SamLambda/                  # Backend SAM application
│   ├── template.yml            # CloudFormation template (~1500+ lines)
│   ├── samconfig.toml          # SAM CLI configuration
│   ├── functions/              # 69+ Lambda functions in 21 categories
│   │   ├── adminFunctions/     # 10 admin tools
│   │   ├── assignmentFunctions/# 7 benefactor assignment functions
│   │   ├── billingFunctions/   # 4 Stripe billing functions
│   │   ├── cognitoTriggers/    # 2 signup/confirmation triggers
│   │   ├── conversationFunctions/ # 4 WebSocket conversation functions
│   │   ├── dataRetentionFunctions/ # 6 lifecycle management functions
│   │   ├── emailCaptureFunctions/  # 4 email capture/nurture functions
│   │   ├── psychTestFunctions/ # 6 psychological testing functions
│   │   ├── questionDbFunctions/# 14 question management functions
│   │   ├── relationshipFunctions/ # 3 relationship management functions
│   │   ├── scheduledJobs/      # 3 EventBridge-triggered jobs
│   │   ├── shared/             # Shared utilities layer
│   │   ├── streakFunctions/    # 3 engagement tracking functions
│   │   ├── surveyFunctions/    # 1 survey function
│   │   └── videoFunctions/     # 7 video processing functions
│   ├── tests/                  # Backend test suites
│   ├── schemas/                # JSON schemas (psych test definitions)
│   ├── psych-tests/            # 3 psychological test definition files
│   └── layers/                 # Lambda layers (Stripe SDK)
├── Questions/                  # Question bank (Excel + JSON)
├── Lambda/                     # Legacy Lambda utilities
├── Python/                     # Database setup scripts
├── UtilityFunctions/           # Data migration and maintenance scripts
├── patent_filings/             # 2 provisional patent applications
├── Kiro Chats/                 # Development session logs and documentation
├── Q Chats/                    # Earlier development session logs
└── DEPLOYMENT_INFO.txt         # Deployment configuration reference
```

---

## 5. BACKEND ARCHITECTURE — AWS SAM & LAMBDA

### Function Categories (69+ Functions)

**Cognito Triggers (2):** PreSignupFunction stores persona data in temp table during signup. PostConfirmationFunction creates relationships, initializes progress, creates subscription record after email confirmation.

**Question Management (14):** CRUD operations for the question bank, progress tracking with level system, cache management via SSM Parameter Store. Key functions: getProgressSummary2 (enhanced with levels), initializeUserProgress, incrementUserLevel2, getUserCompletedQuestionCount (cached 24h), getTotalValidAllQuestions (cached 24h).

**Video Processing (7):** Presigned URL generation for direct S3 upload, FFmpeg-based thumbnail extraction, transcription pipeline (start → process → summarize), video retrieval with presigned URLs. ProcessVideoFunction runs at 1024MB with 60s timeout for FFmpeg operations.

**Conversation Engine (4):** WebSocket-based real-time AI conversation. wsAuthorizer validates Cognito tokens. wsDefault (512MB, 30s timeout) handles all conversation logic via 9 sub-modules: config, conversation_state, transcribe (Deepgram), transcribe_streaming (AWS fallback), llm (Bedrock), speech (Polly), storage (S3 + DynamoDB), handle_start_conversation, handle_audio_response, handle_end_conversation.

**Assignment/Benefactor Functions (7):** Create, accept/decline, update, manual release, resend invitation, check-in response. Implements the multi-condition access control system.

**Billing Functions (4):** Stripe checkout session creation, webhook processing, coupon system, coupon expiration scheduler.

**Data Retention Functions (6):** Data export (full + GDPR), account deletion with 30-day grace period, dormant account detection, storage lifecycle management, legacy protection activation/deactivation, admin lifecycle simulation.

**Psychological Testing (6):** List tests, save progress, get progress, score test (with Bedrock narrative generation), export results (PDF/JSON/CSV), admin import/update.

**Email Capture (4):** Landing page email capture, nurture email scheduler, SES event tracking, unsubscribe handling.

**Scheduled Jobs (3):** TimeDelayProcessor (hourly — activates time-delayed access), CheckInSender (daily — sends check-in emails for inactivity triggers), InactivityProcessor (daily — evaluates missed check-ins and grants access).

**Streak Functions (3):** Get streak, check streak (with calculation), monthly reset (freeze availability).

**Admin Functions (10):** Question management, assessment management, system settings (41 editable parameters), coverage reports, statistics, theme management, email capture management, feedback management, data migration, simulation tools.

**Other (4):** Error ingestion, feedback ingestion, metrics collector, survey functions.

### Shared Utilities Layer

Located at `SamLambda/functions/shared/`, referenced by 30+ functions:

- **persona_validator.py** — Centralized persona-based access control (extract persona from JWT, validate maker/benefactor access)
- **streak_calculator.py** — Pure functions for streak calculation (no AWS dependencies, easy to test)
- **timezone_utils.py** — Timezone-aware date calculations with LRU cache
- **cors.py** — Standardized CORS response headers
- **responses.py** — Standardized HTTP response formatting
- **email_templates.py** — HTML email template generation
- **email_utils.py** — SES email sending utilities
- **assignment_dal.py** — Data access layer for assignments/relationships
- **invitation_utils.py** — Invitation token management
- **validation_utils.py** — Input validation helpers
- **structured_logger.py** — Structured JSON logging
- **logging_utils.py** — CloudWatch logging utilities
- **settings.py** — SSM-backed settings reader with 5-min TTL cache
- **plan_check.py** — Subscription plan enforcement utility
- **retention_config.py** — Data retention SSM parameter reader with caching
- **audit_logger.py** — Tamper-proof audit logging to S3 with SHA-256 hashed user IDs

### Key Architectural Patterns

1. **JWT Security:** All endpoints extract user ID from `event.requestContext.authorizer.claims.sub`. Never trust client-provided userId.
2. **Graceful Degradation:** Non-critical operations (thumbnails, streaks, cache invalidation) wrapped in try/except — core operations always succeed.
3. **Cache-Aside with SSM:** Frequently accessed counts cached in SSM Parameter Store with application-level TTL and event-driven invalidation.
4. **Async Processing:** Video transcription uses EventBridge (Transcribe job complete → ProcessTranscriptFunction → SummarizeTranscriptFunction).
5. **Modular WebSocket Handler:** wsDefault uses 9 sub-modules for separation of concerns.
6. **Three-Tier Transcription Fallback:** Deepgram (~0.5s) → AWS Transcribe Streaming (~5s) → AWS Transcribe Batch (~15s).

---

## 6. FRONTEND ARCHITECTURE — REACT & AMPLIFY