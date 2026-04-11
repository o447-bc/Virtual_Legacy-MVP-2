# SoulReel — Phase 1: Cost Reduction Plan + Phase 2: Stripe & Tier Implementation

**Date**: March 29, 2026  
**Scope**: Backend cost optimization, then payment/subscription infrastructure  
**Codebase**: SamLambda/ (SAM template + Python Lambdas) + FrontEndCode/ (React)

---

## PHASE 1: COST REDUCTION

### Current Cost Profile Per Conversation Turn

Every time a user taps "Send" during an AI conversation, this happens:

| Step | Service | Current Config | Est. Cost Per Turn |
|------|---------|---------------|-------------------|
| 1. Transcription | Deepgram (Tier 1) | Nova-2 model, pay-per-minute | ~$0.0043/min |
| 2. Depth Scoring | Bedrock Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0`, max_tokens=300, temp=0.3 | ~$0.001-0.003 |
| 3. Response Generation | Bedrock Claude 3.5 Sonnet v2 | `anthropic.claude-3-5-sonnet-20241022-v2:0`, max_tokens=500, temp=0.7 | ~$0.015-0.04 |
| 4. Text-to-Speech | Amazon Polly Neural | Joanna voice, MP3 output | ~$0.004/100 chars |
| 5. Audio Storage | S3 + KMS | User audio + AI audio per turn | ~$0.0001 |
| 6. State Persistence | DynamoDB | ConversationStateDB put/get | ~$0.000003 |

**Total per turn: ~$0.025-0.05**  
**Total per conversation (12 turns avg): ~$0.30-0.60**  
**Plus summarization at end: ~$0.01-0.03 (Haiku)**

The dominant cost is Step 3 — Claude 3.5 Sonnet v2 for response generation. It's 10-15x more expensive than Haiku per token, and it sends the full conversation history (growing each turn).

---

### Optimization 1: Switch Depth Scoring to Amazon Nova Micro

**Impact: ~70-85% reduction on scoring costs**  
**Risk: Low**  
**Effort: 15 minutes (SSM parameter change, no code deploy needed)**

The depth scoring task is simple: read a user response, output a number 0-3 and a one-line reasoning. This doesn't need Haiku's full capabilities. Nova Micro is purpose-built for simple classification/extraction tasks.

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) |
|-------|---------------------------|----------------------------|
| Claude 3 Haiku (current) | $0.25 | $1.25 |
| Amazon Nova Micro | $0.035 | $0.14 |
| **Savings** | **86% cheaper input** | **89% cheaper output** |

**How to implement:**

The scoring model is already configurable via SSM Parameter Store. No code change or deploy needed.

```bash
# Update the SSM parameter to use Nova Micro
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-scoring-model" \
  --value "amazon.nova-micro-v1:0" \
  --type String \
  --overwrite

# IMPORTANT: Also update the IAM policy in template.yml to allow the new model
# Then deploy: sam build && sam deploy --no-confirm-changeset
```

**Required template.yml change** — add Nova Micro to the WebSocketDefaultFunction's Bedrock policy:

File: `SamLambda/template.yml`  
In the WebSocketDefaultFunction Policies, find the `bedrock:InvokeModel` statement and add:

```yaml
- arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0
```

**Testing**: After the SSM update + deploy, run one conversation and check CloudWatch logs for `[SCORING]` entries. Verify the score format matches what `score_response_depth()` in `llm.py` expects (either a bare number or "Score: X\nReasoning: ..."). If Nova Micro returns a different format, you may need a minor tweak to the scoring prompt in SSM (`/virtuallegacy/conversation/scoring-prompt`) to explicitly request the format.

**Rollback**: Change the SSM parameter back to `anthropic.claude-3-haiku-20240307-v1:0`. Instant, no deploy.

---

### Optimization 2: Downgrade Response Generation to Claude 3.5 Haiku

**Impact: ~75-80% reduction on the biggest cost line**  
**Risk: Medium — requires quality testing**  
**Effort: 15 minutes (SSM parameter change + IAM policy update)**

Claude 3.5 Sonnet v2 at $6/$30 per 1M tokens is your single largest per-turn cost. Claude 3.5 Haiku at ~$0.80/$4.00 per 1M tokens is 7-8x cheaper and still excellent at empathetic, conversational follow-up questions.

| Model | Input (per 1M) | Output (per 1M) | Quality for Interviewing |
|-------|----------------|-----------------|------------------------|
| Claude 3.5 Sonnet v2 (current) | $6.00 | $30.00 | Excellent |
| Claude 3.5 Haiku | $0.80 | $4.00 | Very good |
| **Savings** | **87%** | **87%** | Slight quality trade-off |

**How to implement:**

```bash
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-conversation-model" \
  --value "us.anthropic.claude-3-5-haiku-20241022-v1:0" \
  --type String \
  --overwrite
```

The IAM policy already includes the Haiku inference profile:
```yaml
- !Sub arn:aws:bedrock:us-east-1:${AWS::AccountId}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0
```

So this is already permitted — just change the SSM parameter.

**Quality testing protocol:**
1. Run 3-5 test conversations across different question categories
2. Compare: Does Haiku ask good follow-up questions? Does it feel empathetic?
3. Check: Are conversations still reaching the score goal in a reasonable number of turns?
4. If quality is noticeably worse on deep/emotional topics, consider a hybrid approach (Optimization 2B below)

**Optimization 2B (Hybrid — if pure Haiku isn't good enough):**

Modify `llm.py` to use Sonnet for turns 1-3 (where question quality matters most for setting the conversation tone) and Haiku for turns 4+. This requires a small code change:

In `app.py`, before calling `process_user_response_parallel()`, check the turn number:

```python
# Use Sonnet for first 3 turns, Haiku for the rest
if state.turn_number < 3:
    conversation_model = config['llm_conversation_model']  # Sonnet (set via SSM)
else:
    conversation_model = config.get('llm_conversation_model_economy', config['llm_conversation_model'])
```

Add a new SSM parameter `/virtuallegacy/conversation/llm-conversation-model-economy` pointing to Haiku. This gives you ~60-70% savings (Sonnet for 3 turns, Haiku for ~9 turns in a typical 12-turn conversation).

---

### Optimization 3: Add S3 Intelligent-Tiering to the Main Bucket

**Impact: 40-70% storage cost reduction on older content**  
**Risk: None — transparent to the application**  
**Effort: Add lifecycle rule to template.yml**

Currently, the `virtual-legacy` S3 bucket has no lifecycle policies (only the audit log bucket does). All conversation audio, AI audio, video recordings, and transcripts sit in S3 Standard forever.

Most content is accessed frequently only in the first few days after recording (user reviews it, benefactors watch it). After that, access drops dramatically.

**Add to template.yml** — you'll need to add the `virtual-legacy` bucket as a managed resource (it's currently created outside SAM), OR apply the lifecycle policy via AWS CLI:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket virtual-legacy \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "IntelligentTieringForConversations",
        "Status": "Enabled",
        "Filter": {
          "Prefix": "conversations/"
        },
        "Transitions": [
          {
            "Days": 30,
            "StorageClass": "INTELLIGENT_TIERING"
          }
        ]
      },
      {
        "ID": "IntelligentTieringForUserResponses",
        "Status": "Enabled",
        "Filter": {
          "Prefix": "user-responses/"
        },
        "Transitions": [
          {
            "Days": 30,
            "StorageClass": "INTELLIGENT_TIERING"
          }
        ]
      }
    ]
  }'
```

**Cost impact at scale:**
- 1,000 users × 50 GB avg = 50 TB
- S3 Standard: $0.023/GB = $1,150/month
- After Intelligent-Tiering (most content infrequently accessed): ~$460-690/month
- **Savings: $460-690/month at 1,000 users**

---

### Optimization 4: Add CloudFront for Video/Audio Delivery

**Impact: Reduced egress costs + faster playback for benefactors**  
**Risk: Low**  
**Effort: 2-3 hours (CloudFront distribution + presigned URL changes)**

Currently, benefactors watching videos generate S3 egress at $0.09/GB. CloudFront's first 1 TB/month is free, and beyond that it's $0.085/GB (cheaper than direct S3 egress) with caching benefits.

This is a bigger infrastructure change — I'd recommend doing it after the Stripe integration is live, as it requires:
1. Creating a CloudFront distribution with an OAI (Origin Access Identity) for the S3 bucket
2. Updating presigned URL generation in `speech.py` and video serving to use CloudFront signed URLs instead of S3 presigned URLs
3. Adding the CloudFront distribution to `template.yml`

**Defer this to after Phase 2 (Stripe). It's a nice-to-have, not urgent until you have significant benefactor traffic.**

---

### Optimization 5: Reduce Polly Costs with Response Caching

**Impact: 20-40% reduction on Polly costs**  
**Risk: Low**  
**Effort: 1-2 hours (code change in speech.py)**

The initial greeting for each conversation is the question text itself — these are reused across all users answering the same question. Currently, Polly re-synthesizes the same question text every time.

**Implementation**: Before calling Polly, check if an audio file already exists at a deterministic S3 key based on the question ID:

```python
# In speech.py, modify text_to_speech():
def text_to_speech(text, user_id, question_id, turn_number, voice_id, engine):
    # For turn 0 (initial question), use a shared cached version
    if turn_number == 0:
        cache_key = f"polly-cache/{question_id}/{voice_id}-{engine}.mp3"
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=cache_key)
            # Cache hit — generate presigned URL and return
            url = s3_client.generate_presigned_url(...)
            return url
        except:
            # Cache miss — synthesize, store at cache_key, then return
            pass
    # ... existing Polly logic for turns > 0
```

This eliminates Polly calls for the most common synthesis (question greetings). AI follow-up responses (turns 1+) are unique per conversation and can't be cached.

---

### Optimization 6: Reduce Lambda Memory Where Over-Provisioned

**Impact: Small but free money**  
**Risk: Low — test after changes**  
**Effort: 30 minutes**

Several Lambdas are allocated more memory than they need:

| Function | Current Memory | Recommended | Rationale |
|----------|---------------|-------------|-----------|
| WebSocketDefaultFunction | 512 MB | 512 MB | Keep — runs Bedrock + transcription, needs headroom |
| ProcessVideoFunction | 1024 MB | 512 MB | FFmpeg thumbnail extraction doesn't need 1 GB |
| UploadVideoResponseFunction | 1024 MB | 256 MB | Generates presigned URLs, minimal compute |
| SummarizeTranscriptFunction | 512 MB | 256 MB | Single Bedrock call, no heavy processing |
| TimeDelayProcessorFunction | 512 MB | 256 MB | DynamoDB scans, no heavy compute |
| CheckInSenderFunction | 512 MB | 256 MB | SES email sending |
| InactivityProcessorFunction | 512 MB | 256 MB | DynamoDB scans |
| ManualReleaseFunction | 512 MB | 256 MB | DynamoDB updates |

**Caveat**: ProcessVideoFunction uses FFmpeg as a Lambda layer. Test at 512 MB first — if FFmpeg runs out of memory on larger videos, keep at 1024 MB.

Lambda pricing is proportional to memory × duration. Halving memory halves cost per millisecond.

---

### Combined Savings Estimate

| Optimization | Monthly Savings (at 100 active users) | Monthly Savings (at 1,000 users) |
|-------------|--------------------------------------|----------------------------------|
| 1. Nova Micro for scoring | $3-8 | $30-80 |
| 2. Haiku for response gen | $25-60 | $250-600 |
| 3. S3 Intelligent-Tiering | $2-5 | $460-690 |
| 4. CloudFront (deferred) | — | $50-200 |
| 5. Polly caching | $1-3 | $10-30 |
| 6. Lambda memory reduction | $2-5 | $20-50 |
| **Total** | **$33-81/month** | **$820-1,650/month** |

At 100 users, Optimizations 1+2 are the priority (they're free to implement via SSM). At 1,000 users, S3 Intelligent-Tiering becomes the biggest win.

---
---

## PHASE 2: STRIPE INTEGRATION & SUBSCRIPTION TIERS

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Pricing Page │  │ Stripe       │  │ Usage Limit       │  │
│  │ /pricing     │  │ Checkout     │  │ Enforcement UI    │  │
│  │              │  │ (redirect)   │  │ (upgrade prompts) │  │
│  └──────────────┘  └──────┬───────┘  └───────────────────┘  │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (REST)                         │
│                                                              │
│  POST /billing/create-checkout-session                       │
│  POST /billing/webhook  (Stripe webhook, NO auth)            │
│  GET  /billing/portal   (Stripe Customer Portal redirect)    │
│  GET  /billing/status   (current plan + usage)               │
│  POST /billing/apply-coupon  (validate & apply coupon)       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Lambda Functions                           │
│                                                              │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ BillingFunction     │  │ StripeWebhookFunction        │  │
│  │ (authenticated)     │  │ (unauthenticated, Stripe     │  │
│  │                     │  │  signature verification)     │  │
│  │ - create checkout   │  │                              │  │
│  │ - get portal URL    │  │ - checkout.session.completed │  │
│  │ - get plan status   │  │ - customer.subscription.*    │  │
│  │ - apply coupon      │  │ - invoice.payment_failed     │  │
│  └─────────┬───────────┘  └──────────────┬───────────────┘  │
│            │                              │                  │
│            ▼                              ▼                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              UserSubscriptionsDB (DynamoDB)              ││
│  │                                                          ││
│  │  PK: userId                                              ││
│  │  stripeCustomerId, subscriptionId, planId,               ││
│  │  status (active|canceled|past_due|trialing),             ││
│  │  currentPeriodEnd, couponCode, couponType,               ││
│  │  conversationsThisWeek, weekResetDate,                   ││
│  │  storageUsedBytes, benefactorCount                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Existing Lambdas get a NEW check before expensive ops:      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ WebSocketDefaultFunction (conversation engine)           ││
│  │  → Before start_conversation: check conversationsThisWeek││
│  │                                                          ││
│  │ UploadVideoResponseFunction                              ││
│  │  → Before upload: check storageUsedBytes vs plan limit   ││
│  │                                                          ││
│  │ CreateAssignmentFunction                                 ││
│  │  → Before create: check benefactorCount vs plan limit    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### Step 2.1: DynamoDB Table — UserSubscriptionsDB

Add to `SamLambda/template.yml`:

```yaml
  UserSubscriptionsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: UserSubscriptionsDB
      BillingMode: PAY_PER_REQUEST
      SSESpecification:
        SSEEnabled: true
        SSEType: KMS
        KMSMasterKeyId: !GetAtt DataEncryptionKey.Arn
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      AttributeDefinitions:
        - AttributeName: userId
          AttributeType: S
        - AttributeName: stripeCustomerId
          AttributeType: S
      KeySchema:
        - AttributeName: userId
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: stripeCustomerId-index
          KeySchema:
            - AttributeName: stripeCustomerId
              KeyType: HASH
          Projection:
            ProjectionType: ALL
```

**Record schema:**

```json
{
  "userId": "cognito-sub-uuid",
  "stripeCustomerId": "cus_xxxxx",
  "stripeSubscriptionId": "sub_xxxxx",
  "planId": "free|personal|family|vault",
  "status": "active|canceled|past_due|trialing|comped",
  "currentPeriodEnd": "2026-04-29T00:00:00Z",
  "couponCode": "FAMILY2026",
  "couponType": "forever_free|time_limited|percentage",
  "couponExpiresAt": "2027-03-29T00:00:00Z",
  "conversationsThisWeek": 2,
  "weekResetDate": "2026-03-31",
  "storageUsedBytes": 1073741824,
  "benefactorCount": 2,
  "createdAt": "2026-03-29T00:00:00Z",
  "updatedAt": "2026-03-29T00:00:00Z"
}
```

---

### Step 2.2: Plan Definitions & Limits

Store plan limits in SSM Parameter Store for runtime configurability:

```bash
aws ssm put-parameter --name "/soulreel/plans/free" --type String --value '{
  "planId": "free",
  "conversationsPerWeek": 3,
  "storageBytes": 5368709120,
  "maxBenefactors": 2,
  "accessConditionTypes": ["immediate"],
  "features": ["basic"]
}'

aws ssm put-parameter --name "/soulreel/plans/personal" --type String --value '{
  "planId": "personal",
  "conversationsPerWeek": -1,
  "storageBytes": 107374182400,
  "maxBenefactors": 5,
  "accessConditionTypes": ["immediate", "time_delayed", "inactivity_trigger", "manual_release"],
  "features": ["basic", "dead_mans_switch", "pdf_export"]
}'

aws ssm put-parameter --name "/soulreel/plans/family" --type String --value '{
  "planId": "family",
  "conversationsPerWeek": -1,
  "storageBytes": 536870912000,
  "maxBenefactors": 15,
  "accessConditionTypes": ["immediate", "time_delayed", "inactivity_trigger", "manual_release"],
  "features": ["basic", "dead_mans_switch", "pdf_export", "priority_ai"]
}'

aws ssm put-parameter --name "/soulreel/plans/vault" --type String --value '{
  "planId": "vault",
  "conversationsPerWeek": -1,
  "storageBytes": 2199023255552,
  "maxBenefactors": -1,
  "accessConditionTypes": ["immediate", "time_delayed", "inactivity_trigger", "manual_release"],
  "features": ["basic", "dead_mans_switch", "pdf_export", "priority_ai", "legacy_export", "psych_profile", "avatar"]
}'
```

(`-1` means unlimited)

---

### Step 2.3: Coupon System Design

This is the system that handles your two requirements: (1) free access for family, and (2) time-based promotional incentives.

**Coupon types:**

| Type | Behavior | Use Case |
|------|----------|----------|
| `forever_free` | Grants a specific plan permanently, no Stripe subscription created | Your family members |
| `time_limited` | Grants a specific plan for N days, then reverts to free | "Try Personal free for 30 days" promos |
| `percentage` | Applies % discount via Stripe Coupon, creates real subscription | "50% off first 3 months" |

**Coupon storage** — SSM Parameter Store (simple, no new table needed):

```bash
# Family coupon — forever free on Vault plan
aws ssm put-parameter \
  --name "/soulreel/coupons/FAMILY2026" \
  --type String \
  --value '{
    "code": "FAMILY2026",
    "type": "forever_free",
    "grantPlan": "vault",
    "maxRedemptions": 10,
    "currentRedemptions": 0,
    "expiresAt": null,
    "createdBy": "oliver"
  }'

# Time-limited promo — 30 days free Personal
aws ssm put-parameter \
  --name "/soulreel/coupons/LAUNCH30" \
  --type String \
  --value '{
    "code": "LAUNCH30",
    "type": "time_limited",
    "grantPlan": "personal",
    "durationDays": 30,
    "maxRedemptions": 500,
    "currentRedemptions": 0,
    "expiresAt": "2026-06-30T00:00:00Z",
    "createdBy": "oliver"
  }'

# Percentage discount — 50% off for 3 months (uses Stripe Coupon)
aws ssm put-parameter \
  --name "/soulreel/coupons/HALFOFF3" \
  --type String \
  --value '{
    "code": "HALFOFF3",
    "type": "percentage",
    "percentOff": 50,
    "durationMonths": 3,
    "stripeCouponId": "HALFOFF3",
    "maxRedemptions": 200,
    "currentRedemptions": 0,
    "expiresAt": "2026-12-31T00:00:00Z",
    "createdBy": "oliver"
  }'
```

**Coupon redemption flow:**

```
User enters code on /pricing or /settings
  → POST /billing/apply-coupon { code: "FAMILY2026" }
  → Lambda validates:
      1. Code exists in SSM
      2. Not expired
      3. Under max redemptions
      4. User hasn't already redeemed a coupon
  → If type == "forever_free":
      - Write to UserSubscriptionsDB: planId=vault, status="comped", couponCode="FAMILY2026"
      - Increment currentRedemptions in SSM
      - No Stripe interaction at all
      - Return { success: true, plan: "vault", message: "You have lifetime Vault access" }
  → If type == "time_limited":
      - Write to UserSubscriptionsDB: planId=personal, status="trialing",
        couponCode="LAUNCH30", couponExpiresAt=now+30days
      - Increment currentRedemptions
      - Return { success: true, plan: "personal", expiresAt: "...", message: "30 days free" }
  → If type == "percentage":
      - Create Stripe Checkout Session with the Stripe coupon applied
      - User completes payment at discounted rate
      - Webhook handles the rest
```

**Expiration of time-limited coupons:**

Add an EventBridge scheduled rule (daily) that scans UserSubscriptionsDB for records where `couponType == "time_limited"` and `couponExpiresAt < now()`, then sets `planId = "free"` and `status = "expired"`.

```yaml
  CouponExpirationFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: functions/billingFunctions/couponExpiration/
      Handler: app.lambda_handler
      Runtime: python3.12
      Architectures:
        - arm64
      Timeout: 60
      MemorySize: 256
      Events:
        DailyCheck:
          Type: Schedule
          Properties:
            Schedule: rate(1 day)
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UserSubscriptionsTable
```

---

### Step 2.4: Stripe Setup (One-Time)

**In Stripe Dashboard:**

1. Create Products & Prices:
   - Product: "SoulReel Personal" → Price: $12.99/month, $99/year
   - Product: "SoulReel Family" → Price: $19.99/month, $179/year
   - Product: "SoulReel Legacy Vault" → Price: $29.99/month, $249/year

2. Create Stripe Coupons (for percentage-type coupons):
   - Coupon ID: `HALFOFF3` → 50% off, duration: 3 months

3. Configure Webhook endpoint:
   - URL: `https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod/billing/webhook`
   - Events to listen for:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`

4. Store secrets in SSM:

```bash
aws ssm put-parameter \
  --name "/soulreel/stripe/secret-key" \
  --type SecureString \
  --value "sk_live_xxxxx"

aws ssm put-parameter \
  --name "/soulreel/stripe/webhook-secret" \
  --type SecureString \
  --value "whsec_xxxxx"

aws ssm put-parameter \
  --name "/soulreel/stripe/publishable-key" \
  --type String \
  --value "pk_live_xxxxx"
```

---

### Step 2.5: Lambda Functions — Billing & Webhook

**New functions to add to template.yml:**

```yaml
  # ---- Billing Functions ----

  BillingFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: functions/billingFunctions/billing/
      Handler: app.lambda_handler
      Runtime: python3.12
      Architectures:
        - arm64
      Timeout: 15
      MemorySize: 256
      Layers:
        - !Ref StripeDependencyLayer  # stripe Python package
      Environment:
        Variables:
          SUBSCRIPTIONS_TABLE: !Ref UserSubscriptionsTable
          FRONTEND_URL: 'https://www.soulreel.net'
      Events:
        CreateCheckout:
          Type: Api
          Properties:
            Path: /billing/create-checkout-session
            Method: post
            Auth:
              Authorizer: CognitoAuthorizer
        GetPortal:
          Type: Api
          Properties:
            Path: /billing/portal
            Method: get
            Auth:
              Authorizer: CognitoAuthorizer
        GetStatus:
          Type: Api
          Properties:
            Path: /billing/status
            Method: get
            Auth:
              Authorizer: CognitoAuthorizer
        ApplyCoupon:
          Type: Api
          Properties:
            Path: /billing/apply-coupon
            Method: post
            Auth:
              Authorizer: CognitoAuthorizer
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UserSubscriptionsTable
        - Statement:
            - Effect: Allow
              Action:
                - ssm:GetParameter
              Resource:
                - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/stripe/*
                - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/plans/*
                - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/coupons/*
        - Statement:
            - Effect: Allow
              Action:
                - ssm:PutParameter
              Resource:
                - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/coupons/*

  StripeWebhookFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: functions/billingFunctions/stripeWebhook/
      Handler: app.lambda_handler
      Runtime: python3.12
      Architectures:
        - arm64
      Timeout: 15
      MemorySize: 256
      Layers:
        - !Ref StripeDependencyLayer
      Environment:
        Variables:
          SUBSCRIPTIONS_TABLE: !Ref UserSubscriptionsTable
      Events:
        Webhook:
          Type: Api
          Properties:
            Path: /billing/webhook
            Method: post
            # NO Auth — Stripe sends webhooks without Cognito tokens
            # Verification is done via Stripe signature in the Lambda code
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UserSubscriptionsTable
        - Statement:
            - Effect: Allow
              Action:
                - ssm:GetParameter
              Resource:
                - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/stripe/*

  # Lambda Layer for Stripe Python SDK
  StripeDependencyLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: stripe-python-layer
      Description: Stripe Python SDK
      ContentUri: layers/stripe/
      CompatibleRuntimes:
        - python3.12
    Metadata:
      BuildMethod: python3.12
```

**To create the Stripe layer:**

```bash
mkdir -p SamLambda/layers/stripe/python
pip install stripe -t SamLambda/layers/stripe/python/
```

---

### Step 2.6: Billing Lambda — Core Logic

**File: `SamLambda/functions/billingFunctions/billing/app.py`**

```python
import json
import os
import boto3
import stripe
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

_stripe_key_cache = None
_plan_cache = {}

def get_stripe_key():
    global _stripe_key_cache
    if not _stripe_key_cache:
        resp = ssm.get_parameter(Name='/soulreel/stripe/secret-key', WithDecryption=True)
        _stripe_key_cache = resp['Parameter']['Value']
    return _stripe_key_cache

def get_plan_limits(plan_id):
    if plan_id not in _plan_cache:
        resp = ssm.get_parameter(Name=f'/soulreel/plans/{plan_id}')
        _plan_cache[plan_id] = json.loads(resp['Parameter']['Value'])
    return _plan_cache[plan_id]

def get_user_subscription(user_id):
    table = dynamodb.Table(os.environ['SUBSCRIPTIONS_TABLE'])
    resp = table.get_item(Key={'userId': user_id})
    return resp.get('Item')

def cors_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    stripe.api_key = get_stripe_key()
    
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    if method == 'OPTIONS':
        return cors_response(200, {})
    
    if path == '/billing/create-checkout-session' and method == 'POST':
        return handle_create_checkout(event, user_id)
    elif path == '/billing/portal' and method == 'GET':
        return handle_portal(user_id)
    elif path == '/billing/status' and method == 'GET':
        return handle_status(user_id)
    elif path == '/billing/apply-coupon' and method == 'POST':
        return handle_apply_coupon(event, user_id)
    
    return cors_response(404, {'error': 'Not found'})

def handle_create_checkout(event, user_id):
    body = json.loads(event.get('body', '{}'))
    price_id = body.get('priceId')
    
    if not price_id:
        return cors_response(400, {'error': 'Missing priceId'})
    
    # Get or create Stripe customer
    sub_record = get_user_subscription(user_id)
    customer_id = sub_record.get('stripeCustomerId') if sub_record else None
    
    if not customer_id:
        customer = stripe.Customer.create(metadata={'userId': user_id})
        customer_id = customer.id
    
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='subscription',
        success_url=f"{os.environ['FRONTEND_URL']}/dashboard?checkout=success",
        cancel_url=f"{os.environ['FRONTEND_URL']}/pricing?checkout=canceled",
        metadata={'userId': user_id},
        allow_promotion_codes=True  # Lets users enter Stripe-native promo codes too
    )
    
    return cors_response(200, {'sessionUrl': session.url})

def handle_portal(user_id):
    sub_record = get_user_subscription(user_id)
    if not sub_record or not sub_record.get('stripeCustomerId'):
        return cors_response(400, {'error': 'No billing account found'})
    
    session = stripe.billing_portal.Session.create(
        customer=sub_record['stripeCustomerId'],
        return_url=f"{os.environ['FRONTEND_URL']}/dashboard"
    )
    
    return cors_response(200, {'portalUrl': session.url})

def handle_status(user_id):
    sub_record = get_user_subscription(user_id)
    
    if not sub_record:
        plan_limits = get_plan_limits('free')
        return cors_response(200, {
            'planId': 'free',
            'status': 'active',
            'limits': plan_limits,
            'usage': {
                'conversationsThisWeek': 0,
                'storageUsedBytes': 0,
                'benefactorCount': 0
            }
        })
    
    plan_limits = get_plan_limits(sub_record.get('planId', 'free'))
    
    return cors_response(200, {
        'planId': sub_record.get('planId', 'free'),
        'status': sub_record.get('status', 'active'),
        'currentPeriodEnd': sub_record.get('currentPeriodEnd'),
        'couponCode': sub_record.get('couponCode'),
        'couponExpiresAt': sub_record.get('couponExpiresAt'),
        'limits': plan_limits,
        'usage': {
            'conversationsThisWeek': int(sub_record.get('conversationsThisWeek', 0)),
            'storageUsedBytes': int(sub_record.get('storageUsedBytes', 0)),
            'benefactorCount': int(sub_record.get('benefactorCount', 0))
        }
    })

def handle_apply_coupon(event, user_id):
    body = json.loads(event.get('body', '{}'))
    code = body.get('code', '').strip().upper()
    
    if not code:
        return cors_response(400, {'error': 'Missing coupon code'})
    
    # Check if user already has an active paid plan
    sub_record = get_user_subscription(user_id)
    if sub_record and sub_record.get('status') == 'active' and sub_record.get('planId') != 'free':
        return cors_response(400, {'error': 'You already have an active plan'})
    
    # Fetch coupon from SSM
    try:
        resp = ssm.get_parameter(Name=f'/soulreel/coupons/{code}')
        coupon = json.loads(resp['Parameter']['Value'])
    except ssm.exceptions.ParameterNotFound:
        return cors_response(400, {'error': 'Invalid coupon code'})
    
    # Validate expiration
    if coupon.get('expiresAt'):
        if datetime.fromisoformat(coupon['expiresAt'].replace('Z', '+00:00')) < datetime.now(tz=None):
            return cors_response(400, {'error': 'This coupon has expired'})
    
    # Validate redemption limit
    if coupon.get('maxRedemptions') and coupon.get('currentRedemptions', 0) >= coupon['maxRedemptions']:
        return cors_response(400, {'error': 'This coupon has reached its redemption limit'})
    
    table = dynamodb.Table(os.environ['SUBSCRIPTIONS_TABLE'])
    now = datetime.utcnow().isoformat() + 'Z'
    
    if coupon['type'] == 'forever_free':
        # Grant plan permanently — no Stripe involved
        table.put_item(Item={
            'userId': user_id,
            'planId': coupon['grantPlan'],
            'status': 'comped',
            'couponCode': code,
            'couponType': 'forever_free',
            'conversationsThisWeek': 0,
            'weekResetDate': _get_next_monday(),
            'storageUsedBytes': 0,
            'benefactorCount': sub_record.get('benefactorCount', 0) if sub_record else 0,
            'createdAt': now,
            'updatedAt': now
        })
        _increment_coupon_redemptions(code, coupon)
        
        return cors_response(200, {
            'success': True,
            'planId': coupon['grantPlan'],
            'type': 'forever_free',
            'message': f"You now have lifetime {coupon['grantPlan'].title()} access!"
        })
    
    elif coupon['type'] == 'time_limited':
        expires_at = (datetime.utcnow() + timedelta(days=coupon['durationDays'])).isoformat() + 'Z'
        
        table.put_item(Item={
            'userId': user_id,
            'planId': coupon['grantPlan'],
            'status': 'trialing',
            'couponCode': code,
            'couponType': 'time_limited',
            'couponExpiresAt': expires_at,
            'conversationsThisWeek': 0,
            'weekResetDate': _get_next_monday(),
            'storageUsedBytes': 0,
            'benefactorCount': sub_record.get('benefactorCount', 0) if sub_record else 0,
            'createdAt': now,
            'updatedAt': now
        })
        _increment_coupon_redemptions(code, coupon)
        
        return cors_response(200, {
            'success': True,
            'planId': coupon['grantPlan'],
            'type': 'time_limited',
            'expiresAt': expires_at,
            'message': f"You have free {coupon['grantPlan'].title()} access for {coupon['durationDays']} days!"
        })
    
    elif coupon['type'] == 'percentage':
        # For percentage coupons, redirect to Stripe Checkout with the coupon applied
        # The actual subscription creation happens via webhook
        return cors_response(200, {
            'success': True,
            'type': 'percentage',
            'stripeCouponId': coupon['stripeCouponId'],
            'message': f"{coupon['percentOff']}% off for {coupon['durationMonths']} months! Complete checkout to apply."
        })
    
    return cors_response(400, {'error': 'Unknown coupon type'})

def _get_next_monday():
    today = datetime.utcnow()
    days_ahead = 7 - today.weekday()  # Monday = 0
    if days_ahead == 7:
        days_ahead = 0
    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

def _increment_coupon_redemptions(code, coupon):
    coupon['currentRedemptions'] = coupon.get('currentRedemptions', 0) + 1
    ssm.put_parameter(
        Name=f'/soulreel/coupons/{code}',
        Value=json.dumps(coupon),
        Type='String',
        Overwrite=True
    )
```

---

### Step 2.7: Stripe Webhook Lambda

**File: `SamLambda/functions/billingFunctions/stripeWebhook/app.py`**

```python
import json
import os
import boto3
import stripe
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

_secrets_cache = {}

def get_secret(name):
    if name not in _secrets_cache:
        resp = ssm.get_parameter(Name=name, WithDecryption=True)
        _secrets_cache[name] = resp['Parameter']['Value']
    return _secrets_cache[name]

# Map Stripe Price IDs to plan IDs (set these after creating products in Stripe)
PRICE_TO_PLAN = {
    'price_personal_monthly': 'personal',
    'price_personal_annual': 'personal',
    'price_family_monthly': 'family',
    'price_family_annual': 'family',
    'price_vault_monthly': 'vault',
    'price_vault_annual': 'vault',
}

def cors_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net'),
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    stripe.api_key = get_secret('/soulreel/stripe/secret-key')
    webhook_secret = get_secret('/soulreel/stripe/webhook-secret')
    
    # Verify Stripe signature
    payload = event.get('body', '')
    sig_header = event.get('headers', {}).get('Stripe-Signature') or \
                 event.get('headers', {}).get('stripe-signature', '')
    
    try:
        stripe_event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"Webhook signature verification failed: {e}")
        return cors_response(400, {'error': 'Invalid signature'})
    
    event_type = stripe_event['type']
    data = stripe_event['data']['object']
    
    print(f"[WEBHOOK] Processing: {event_type}")
    
    table = dynamodb.Table(os.environ['SUBSCRIPTIONS_TABLE'])
    now = datetime.utcnow().isoformat() + 'Z'
    
    if event_type == 'checkout.session.completed':
        user_id = data.get('metadata', {}).get('userId')
        customer_id = data.get('customer')
        subscription_id = data.get('subscription')
        
        if not user_id:
            print("[WEBHOOK] No userId in metadata, skipping")
            return cors_response(200, {'received': True})
        
        # Fetch subscription to get price/plan info
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription['items']['data'][0]['price']['id']
        plan_id = PRICE_TO_PLAN.get(price_id, 'personal')
        
        # Get existing record to preserve usage counters
        existing = table.get_item(Key={'userId': user_id}).get('Item', {})
        
        table.put_item(Item={
            'userId': user_id,
            'stripeCustomerId': customer_id,
            'stripeSubscriptionId': subscription_id,
            'planId': plan_id,
            'status': 'active',
            'currentPeriodEnd': datetime.fromtimestamp(
                subscription['current_period_end']
            ).isoformat() + 'Z',
            'conversationsThisWeek': existing.get('conversationsThisWeek', 0),
            'weekResetDate': existing.get('weekResetDate', ''),
            'storageUsedBytes': existing.get('storageUsedBytes', 0),
            'benefactorCount': existing.get('benefactorCount', 0),
            'createdAt': existing.get('createdAt', now),
            'updatedAt': now
        })
        print(f"[WEBHOOK] Subscription activated: {user_id} → {plan_id}")
    
    elif event_type == 'customer.subscription.updated':
        # Handle plan changes, renewals
        subscription_id = data.get('id')
        status = data.get('status')  # active, past_due, canceled, etc.
        
        # Find user by stripeCustomerId
        customer_id = data.get('customer')
        user_record = _find_user_by_customer(table, customer_id)
        
        if user_record:
            price_id = data['items']['data'][0]['price']['id']
            plan_id = PRICE_TO_PLAN.get(price_id, user_record.get('planId', 'personal'))
            
            table.update_item(
                Key={'userId': user_record['userId']},
                UpdateExpression='SET #s = :status, planId = :plan, currentPeriodEnd = :end, updatedAt = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':plan': plan_id,
                    ':end': datetime.fromtimestamp(data['current_period_end']).isoformat() + 'Z',
                    ':now': now
                }
            )
            print(f"[WEBHOOK] Subscription updated: {user_record['userId']} → {status}/{plan_id}")
    
    elif event_type == 'customer.subscription.deleted':
        customer_id = data.get('customer')
        user_record = _find_user_by_customer(table, customer_id)
        
        if user_record:
            table.update_item(
                Key={'userId': user_record['userId']},
                UpdateExpression='SET #s = :status, planId = :plan, updatedAt = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': 'canceled',
                    ':plan': 'free',
                    ':now': now
                }
            )
            print(f"[WEBHOOK] Subscription canceled: {user_record['userId']} → free")
    
    elif event_type == 'invoice.payment_failed':
        customer_id = data.get('customer')
        user_record = _find_user_by_customer(table, customer_id)
        
        if user_record:
            table.update_item(
                Key={'userId': user_record['userId']},
                UpdateExpression='SET #s = :status, updatedAt = :now',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': 'past_due',
                    ':now': now
                }
            )
            print(f"[WEBHOOK] Payment failed: {user_record['userId']}")
    
    return cors_response(200, {'received': True})

def _find_user_by_customer(table, customer_id):
    """Look up user by Stripe customer ID using GSI."""
    resp = table.query(
        IndexName='stripeCustomerId-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('stripeCustomerId').eq(customer_id)
    )
    items = resp.get('Items', [])
    return items[0] if items else None
```

---

### Step 2.8: Usage Limit Enforcement in Existing Lambdas

The key enforcement points are in three existing Lambdas. Each needs a small addition at the top of its handler to check the user's plan limits before proceeding.

**Shared utility function** (add to a shared layer or inline in each Lambda):

```python
# plan_check.py — shared utility
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

_plan_cache = {}

def get_plan_limits(plan_id):
    if plan_id not in _plan_cache:
        try:
            resp = ssm.get_parameter(Name=f'/soulreel/plans/{plan_id}')
            _plan_cache[plan_id] = json.loads(resp['Parameter']['Value'])
        except:
            _plan_cache[plan_id] = json.loads(
                ssm.get_parameter(Name='/soulreel/plans/free')['Parameter']['Value']
            )
    return _plan_cache[plan_id]

def get_user_plan(user_id, table_name='UserSubscriptionsDB'):
    table = dynamodb.Table(table_name)
    resp = table.get_item(Key={'userId': user_id})
    item = resp.get('Item')
    
    if not item:
        return 'free', get_plan_limits('free'), {}
    
    plan_id = item.get('planId', 'free')
    status = item.get('status', 'active')
    
    # Treat canceled/past_due as free for limit purposes
    if status in ('canceled', 'expired'):
        plan_id = 'free'
    
    limits = get_plan_limits(plan_id)
    usage = {
        'conversationsThisWeek': int(item.get('conversationsThisWeek', 0)),
        'weekResetDate': item.get('weekResetDate', ''),
        'storageUsedBytes': int(item.get('storageUsedBytes', 0)),
        'benefactorCount': int(item.get('benefactorCount', 0))
    }
    
    return plan_id, limits, usage

def check_conversation_limit(user_id, table_name='UserSubscriptionsDB'):
    """Returns (allowed: bool, message: str)"""
    plan_id, limits, usage = get_user_plan(user_id, table_name)
    
    max_convos = limits.get('conversationsPerWeek', 3)
    if max_convos == -1:  # unlimited
        return True, ''
    
    # Reset weekly counter if past reset date
    today = datetime.utcnow().strftime('%Y-%m-%d')
    if usage.get('weekResetDate', '') <= today:
        # Reset counter
        table = dynamodb.Table(table_name)
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET conversationsThisWeek = :zero, weekResetDate = :next',
            ExpressionAttributeValues={
                ':zero': 0,
                ':next': _get_next_monday()
            }
        )
        return True, ''
    
    if usage['conversationsThisWeek'] >= max_convos:
        return False, f'You have used all {max_convos} conversations this week. Upgrade for unlimited conversations.'
    
    return True, ''

def increment_conversation_count(user_id, table_name='UserSubscriptionsDB'):
    """Call this after a conversation starts successfully."""
    table = dynamodb.Table(table_name)
    table.update_item(
        Key={'userId': user_id},
        UpdateExpression='SET conversationsThisWeek = if_not_exists(conversationsThisWeek, :zero) + :one',
        ExpressionAttributeValues={':zero': 0, ':one': 1}
    )

def _get_next_monday():
    from datetime import timedelta
    today = datetime.utcnow()
    days_ahead = 7 - today.weekday()
    if days_ahead == 7:
        days_ahead = 0
    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
```

**Enforcement point 1 — Conversation start** (`wsDefault/app.py`):

In `handle_start_conversation()`, add before creating the conversation state:

```python
from plan_check import check_conversation_limit, increment_conversation_count

def handle_start_conversation(connection_id, user_id, body, config):
    # --- NEW: Check conversation limit ---
    allowed, message = check_conversation_limit(user_id)
    if not allowed:
        send_message(connection_id, {
            'type': 'limit_reached',
            'limitType': 'conversations',
            'message': message
        })
        return
    # --- END NEW ---
    
    # ... existing code ...
    
    # After successful start, increment counter
    increment_conversation_count(user_id)
```

**Enforcement point 2 — Video upload** (UploadVideoResponseFunction):

Before generating the presigned upload URL, check storage:

```python
plan_id, limits, usage = get_user_plan(user_id)
max_storage = limits.get('storageBytes', 5368709120)  # 5 GB default
if max_storage != -1 and usage['storageUsedBytes'] >= max_storage:
    return cors_response(403, {
        'error': 'storage_limit',
        'message': 'You have reached your storage limit. Upgrade for more space.',
        'currentBytes': usage['storageUsedBytes'],
        'limitBytes': max_storage
    })
```

**Enforcement point 3 — Benefactor assignment** (CreateAssignmentFunction):

Before creating the assignment, check benefactor count:

```python
plan_id, limits, usage = get_user_plan(user_id)
max_benefactors = limits.get('maxBenefactors', 2)
if max_benefactors != -1 and usage['benefactorCount'] >= max_benefactors:
    return cors_response(403, {
        'error': 'benefactor_limit',
        'message': f'Your plan allows {max_benefactors} benefactors. Upgrade for more.',
        'currentCount': usage['benefactorCount'],
        'limit': max_benefactors
    })
```

---

### Step 2.9: Frontend — Pricing Page & Upgrade Prompts

**New route**: Add `/pricing` to `App.tsx`

**Pricing page** should:
1. Fetch `GET /billing/status` to show current plan
2. Display plan comparison table (Free / Personal / Family / Vault)
3. Each plan has a "Subscribe" button that calls `POST /billing/create-checkout-session` with the Stripe Price ID
4. Include a coupon code input field that calls `POST /billing/apply-coupon`
5. If user has an active subscription, show "Manage Subscription" button that calls `GET /billing/portal` and redirects to Stripe Customer Portal

**Upgrade prompts** — add to existing components:

1. **ConversationInterface.tsx**: Handle the new `limit_reached` WebSocket message type:
```typescript
case 'limit_reached':
    setError(null);
    setLimitReached({
        type: data.limitType,
        message: data.message
    });
    // Show upgrade dialog
    break;
```

2. **Dashboard.tsx**: Fetch billing status on load, show a subtle banner if on free plan:
```
"You're on the Free plan (2 of 3 conversations used this week)" [Upgrade →]
```

3. **ManageBenefactors.tsx**: When CreateAssignment returns 403 with `benefactor_limit`, show upgrade prompt instead of generic error.

---

### Step 2.10: Weekly Conversation Counter Reset

Add an EventBridge scheduled function to reset weekly counters every Monday:

```yaml
  WeeklyUsageResetFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: functions/billingFunctions/weeklyReset/
      Handler: app.lambda_handler
      Runtime: python3.12
      Architectures:
        - arm64
      Timeout: 120
      MemorySize: 256
      Events:
        MondayReset:
          Type: Schedule
          Properties:
            Schedule: cron(0 6 ? * MON *)  # Every Monday at 6 AM UTC
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref UserSubscriptionsTable
```

```python
# functions/billingFunctions/weeklyReset/app.py
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    table = dynamodb.Table('UserSubscriptionsDB')
    
    # Scan all records and reset conversation counters
    response = table.scan(ProjectionExpression='userId')
    
    next_monday = (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    for item in response.get('Items', []):
        table.update_item(
            Key={'userId': item['userId']},
            UpdateExpression='SET conversationsThisWeek = :zero, weekResetDate = :next',
            ExpressionAttributeValues={':zero': 0, ':next': next_monday}
        )
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ProjectionExpression='userId',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response.get('Items', []):
            table.update_item(
                Key={'userId': item['userId']},
                UpdateExpression='SET conversationsThisWeek = :zero, weekResetDate = :next',
                ExpressionAttributeValues={':zero': 0, ':next': next_monday}
            )
    
    print(f"Reset complete")
    return {'statusCode': 200}
```

---

### Step 2.11: Implementation Order & IAM Checklist

**Deploy order** (each step should be a separate `sam build && sam deploy`):

| Step | What | Deploy? | IAM Changes? |
|------|------|---------|-------------|
| 1 | Add `UserSubscriptionsTable` to template.yml | Yes | No |
| 2 | Create Stripe layer (`layers/stripe/`) | No (just file creation) | No |
| 3 | Add `BillingFunction` + `StripeWebhookFunction` to template.yml | Yes | Yes — new SSM read permissions for `/soulreel/stripe/*`, `/soulreel/plans/*`, `/soulreel/coupons/*`; SSM write for `/soulreel/coupons/*`; DynamoDB CRUD on UserSubscriptionsTable |
| 4 | Create SSM parameters for plans and coupons | No (CLI commands) | No |
| 5 | Create Stripe products/prices/webhook in Stripe Dashboard | No | No |
| 6 | Add `plan_check.py` to shared layer or inline in wsDefault | Yes | Yes — WebSocketDefaultFunction needs DynamoDB read on UserSubscriptionsTable + SSM read on `/soulreel/plans/*` |
| 7 | Add enforcement to `wsDefault/app.py` | Yes (same deploy as 6) | Same as 6 |
| 8 | Add enforcement to UploadVideoResponseFunction | Yes | Yes — needs DynamoDB read on UserSubscriptionsTable |
| 9 | Add enforcement to CreateAssignmentFunction | Yes | Yes — needs DynamoDB read on UserSubscriptionsTable |
| 10 | Add `WeeklyUsageResetFunction` + `CouponExpirationFunction` | Yes | Yes — DynamoDB CRUD on UserSubscriptionsTable |
| 11 | Frontend: Add `/pricing` page, upgrade prompts, coupon input | Frontend deploy only | No |

**IAM policy additions for WebSocketDefaultFunction** (Step 6):

```yaml
# Add to WebSocketDefaultFunction Policies:
- Statement:
    - Effect: Allow
      Action:
        - dynamodb:GetItem
        - dynamodb:UpdateItem
      Resource: !GetAtt UserSubscriptionsTable.Arn
- Statement:
    - Effect: Allow
      Action:
        - ssm:GetParameter
      Resource:
        - !Sub arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/soulreel/plans/*
```

---

### Coupon Quick Reference

**Your family coupon** — create this immediately after deploying the billing system:

```bash
aws ssm put-parameter \
  --name "/soulreel/coupons/FAMILY2026" \
  --type String \
  --value '{
    "code": "FAMILY2026",
    "type": "forever_free",
    "grantPlan": "vault",
    "maxRedemptions": 10,
    "currentRedemptions": 0,
    "expiresAt": null,
    "createdBy": "oliver"
  }'
```

Your family members enter `FAMILY2026` on the pricing page → instant lifetime Vault access, no credit card, no Stripe interaction.

**Time-based promotional coupons** — create as needed:

```bash
# 14-day free trial of Personal (for launch campaign)
aws ssm put-parameter \
  --name "/soulreel/coupons/TRY14" \
  --type String \
  --value '{
    "code": "TRY14",
    "type": "time_limited",
    "grantPlan": "personal",
    "durationDays": 14,
    "maxRedemptions": 1000,
    "currentRedemptions": 0,
    "expiresAt": "2026-09-30T00:00:00Z",
    "createdBy": "oliver"
  }'

# 30-day free trial of Family (for partnership with retirement community)
aws ssm put-parameter \
  --name "/soulreel/coupons/SENIORLIVING30" \
  --type String \
  --value '{
    "code": "SENIORLIVING30",
    "type": "time_limited",
    "grantPlan": "family",
    "durationDays": 30,
    "maxRedemptions": 200,
    "currentRedemptions": 0,
    "expiresAt": "2026-12-31T00:00:00Z",
    "createdBy": "oliver"
  }'

# 50% off first 3 months (for social media campaign)
aws ssm put-parameter \
  --name "/soulreel/coupons/HALFOFF3" \
  --type String \
  --value '{
    "code": "HALFOFF3",
    "type": "percentage",
    "percentOff": 50,
    "durationMonths": 3,
    "stripeCouponId": "HALFOFF3",
    "maxRedemptions": 500,
    "currentRedemptions": 0,
    "expiresAt": "2026-12-31T00:00:00Z",
    "createdBy": "oliver"
  }'
```

To create a new coupon at any time, just run another `aws ssm put-parameter` command. No code deploy needed. To disable a coupon, set `maxRedemptions` to `currentRedemptions` (or set `expiresAt` to a past date).

---

### Summary of New AWS Resources

| Resource | Type | Purpose |
|----------|------|---------|
| UserSubscriptionsTable | DynamoDB | Stores plan, status, usage per user |
| StripeDependencyLayer | Lambda Layer | `stripe` Python package |
| BillingFunction | Lambda | Checkout, portal, status, coupon endpoints |
| StripeWebhookFunction | Lambda | Processes Stripe events |
| WeeklyUsageResetFunction | Lambda + EventBridge | Resets conversation counters every Monday |
| CouponExpirationFunction | Lambda + EventBridge | Expires time-limited coupons daily |
| 6 SSM Parameters | SSM Parameter Store | Stripe keys, plan definitions |
| N coupon parameters | SSM Parameter Store | One per coupon code |

**Estimated additional AWS cost for billing infrastructure**: ~$2-5/month (Lambda invocations + DynamoDB reads are negligible at early scale).
