# SoulReel Per-User Cost Analysis

**Analysis Date:** February 19, 2026  
**Assumptions:** Based on current AWS infrastructure and Phase 1 security implementation

---

## Executive Summary

Per-user monthly costs vary dramatically based on usage patterns:

- **Active User (10 interactions/day):** $2.10 - $3.50/month
- **Low-Use User (storage only):** $0.23 - $0.46/month
- **Break-even point:** ~$5-10/month subscription fee

---

## Cost Model Assumptions

### Active User Profile
- 10 video uploads per month (1 per day for 10 days)
- 30 video views per month (3 per day)
- 10 conversation sessions per month (AI chat)
- 2GB video storage
- Transcription enabled for 50% of videos
- AI summarization for transcribed videos

### Low-Use User Profile
- No new uploads (legacy content only)
- 2 video views per month (checking old content)
- 2GB video storage
- No transcription or AI processing
- Minimal API calls

---

## Per-User Cost Breakdown: Active User

### Storage Costs

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **S3 Storage** | 2GB | $0.023/GB | $0.046 |
| **S3 Versioning** | 0.4GB (20% churn) | $0.023/GB | $0.009 |
| **DynamoDB Storage** | 10MB | $0.25/GB | $0.0025 |
| **CloudWatch Logs** | 100MB | $0.50/GB | $0.05 |
| **CloudTrail Logs** | 100MB | $0.023/GB | $0.0023 |
| **Subtotal** | | | **$0.11** |

### Compute Costs

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Lambda Invocations** | 50 calls | $0.20/1M | $0.00001 |
| **Lambda Duration** | 250 GB-seconds | $0.0000166667/GB-s | $0.0042 |
| **API Gateway** | 100 requests | $3.50/1M | $0.00035 |
| **WebSocket** | 10 connections | $0.25/1M messages | $0.0025 |
| **Subtotal** | | | **$0.007** |

### AI/ML Processing

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Transcribe** | 20 minutes audio | $0.024/min | $0.48 |
| **Bedrock Claude** | 10k tokens | $0.003/1k tokens | $0.03 |
| **Polly TTS** | 5k characters | $4.00/1M chars | $0.02 |
| **Subtotal** | | | **$0.53** |

### Data Transfer

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **S3 Data Out** | 1GB | $0.09/GB (after 100GB free) | $0.00* |
| **CloudFront** | 1GB | $0.085/GB | $0.085 |
| **Subtotal** | | | **$0.085** |

*First 100GB free tier shared across all users

### Security Services (Phase 1)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **KMS Key** | Shared | $1.00/key ÷ 100 users | $0.01 |
| **KMS API Calls** | 100 ops | $0.03/10k | $0.0003 |
| **CloudTrail Data Events** | 125 events | $0.10/100k | $0.000125 |
| **GuardDuty** | Shared analysis | $0.95 ÷ 100 users | $0.0095 |
| **Subtotal** | | | **$0.02** |

### Authentication

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Cognito MAU** | 1 user | Free (first 50k) | $0.00 |
| **Subtotal** | | | **$0.00** |

---

## Active User Total: $0.75/month

**With 30% overhead/buffer:** $0.98/month  
**Rounded estimate:** **$1.00 - $1.50/month**

---

## Per-User Cost Breakdown: Low-Use User

### Storage Costs

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **S3 Storage** | 2GB | $0.023/GB | $0.046 |
| **S3 Versioning** | 0GB (no changes) | $0.023/GB | $0.00 |
| **DynamoDB Storage** | 10MB | $0.25/GB | $0.0025 |
| **CloudWatch Logs** | 10MB | $0.50/GB | $0.005 |
| **CloudTrail Logs** | 10MB | $0.023/GB | $0.00023 |
| **Subtotal** | | | **$0.054** |

### Compute Costs

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Lambda Invocations** | 2 calls | $0.20/1M | $0.0000004 |
| **Lambda Duration** | 10 GB-seconds | $0.0000166667/GB-s | $0.00017 |
| **API Gateway** | 5 requests | $3.50/1M | $0.0000175 |
| **Subtotal** | | | **$0.0002** |

### AI/ML Processing

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Transcribe** | 0 minutes | $0.024/min | $0.00 |
| **Bedrock** | 0 tokens | $0.003/1k | $0.00 |
| **Polly** | 0 characters | $4.00/1M | $0.00 |
| **Subtotal** | | | **$0.00** |

### Data Transfer

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **S3 Data Out** | 100MB | Free tier | $0.00 |
| **CloudFront** | 100MB | $0.085/GB | $0.0085 |
| **Subtotal** | | | **$0.0085** |

### Security Services (Phase 1)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **KMS Key** | Shared | $1.00 ÷ 100 users | $0.01 |
| **KMS API Calls** | 2 ops | $0.03/10k | $0.000006 |
| **CloudTrail Data Events** | 5 events | $0.10/100k | $0.000005 |
| **GuardDuty** | Shared | $0.95 ÷ 100 users | $0.0095 |
| **Subtotal** | | | **$0.02** |

---

## Low-Use User Total: $0.08/month

**With 30% overhead/buffer:** $0.10/month  
**Rounded estimate:** **$0.10 - $0.20/month**

---

## Cost Comparison by User Type

| User Type | Storage | Compute | AI/ML | Transfer | Security | Total |
|-----------|---------|---------|-------|----------|----------|-------|
| **Active** | $0.11 | $0.007 | $0.53 | $0.085 | $0.02 | **$0.75** |
| **Low-Use** | $0.054 | $0.0002 | $0.00 | $0.0085 | $0.02 | **$0.08** |
| **Difference** | 2x | 35x | ∞ | 10x | 1x | **9.4x** |

**Key Insight:** AI/ML processing (transcription + summarization) accounts for 71% of active user costs.

---

## Scaling Analysis

### At 100 Users (50 active, 50 low-use)

| Component | Cost | Calculation |
|-----------|------|-------------|
| **Active Users** | $37.50 | 50 × $0.75 |
| **Low-Use Users** | $4.00 | 50 × $0.08 |
| **Shared Infrastructure** | $168.50 | Base costs (KMS, GuardDuty, etc.) |
| **Total** | **$210/month** | Matches current baseline |

**Per-user average:** $2.10/month

### At 1,000 Users (500 active, 500 low-use)

| Component | Cost | Calculation |
|-----------|------|-------------|
| **Active Users** | $375 | 500 × $0.75 |
| **Low-Use Users** | $40 | 500 × $0.08 |
| **Shared Infrastructure** | $170 | Minimal increase |
| **Total** | **$585/month** | |

**Per-user average:** $0.59/month (72% reduction due to economies of scale)

### At 10,000 Users (5,000 active, 5,000 low-use)

| Component | Cost | Calculation |
|-----------|------|-------------|
| **Active Users** | $3,750 | 5,000 × $0.75 |
| **Low-Use Users** | $400 | 5,000 × $0.08 |
| **Shared Infrastructure** | $200 | Slight increase |
| **Data Transfer** | $450 | Exceeds free tier |
| **Total** | **$4,800/month** | |

**Per-user average:** $0.48/month (77% reduction)

---

## Cost Drivers Analysis

### What Makes Active Users Expensive?

1. **Transcription (64%)** - $0.48 per user
   - Most expensive single service
   - Scales linearly with video duration
   - Optimization: Make transcription optional

2. **Storage (15%)** - $0.11 per user
   - Grows over time
   - Optimization: Lifecycle policies to Glacier

3. **AI Summarization (4%)** - $0.03 per user
   - Depends on transcription
   - Optimization: Batch processing

4. **Data Transfer (11%)** - $0.085 per user
   - Increases with video views
   - Optimization: CloudFront caching

5. **Security (3%)** - $0.02 per user
   - Fixed overhead
   - Decreases per-user as you scale

### What Makes Low-Use Users Cheap?

1. **No AI processing** - Saves $0.53/month (87% of active cost)
2. **Minimal compute** - Saves $0.007/month
3. **Low bandwidth** - Saves $0.077/month
4. **Storage only** - Just $0.054/month

---

## Pricing Strategy Recommendations

### Option 1: Flat-Rate Pricing

**Charge:** $5/month per user

- **Margin at 100 users:** $5 × 100 - $210 = $290/month (58% margin)
- **Margin at 1,000 users:** $5 × 1,000 - $585 = $4,415/month (88% margin)
- **Pros:** Simple, predictable
- **Cons:** Subsidizes heavy users, penalizes light users

### Option 2: Tiered Pricing

**Free Tier:**
- Storage only (no uploads)
- 2 video views/month
- Cost: $0.08/user
- Target: Benefactors viewing legacy content

**Basic Tier: $3/month**
- 5 video uploads/month
- Unlimited views
- No transcription
- Cost: $0.22/user
- Margin: $2.78/user (93%)

**Premium Tier: $10/month**
- Unlimited uploads
- AI transcription + summarization
- Priority support
- Cost: $0.75/user
- Margin: $9.25/user (93%)

**Projected Revenue (1,000 users):**
- 500 free users: $0
- 300 basic users: $900
- 200 premium users: $2,000
- **Total: $2,900/month**
- **Costs: $585/month**
- **Profit: $2,315/month (80% margin)**

### Option 3: Usage-Based Pricing

**Base: $2/month** (storage + basic features)

**Add-ons:**
- Transcription: $0.50 per video
- AI Summary: $0.10 per video
- Extra storage: $0.50/GB over 2GB

**Example Active User:**
- Base: $2.00
- 10 transcriptions: $5.00
- 10 summaries: $1.00
- **Total: $8.00/month**
- **Cost: $0.75**
- **Margin: $7.25 (91%)**

**Pros:** Fair, scales with value
**Cons:** Unpredictable revenue, complex billing

---

## Cost Optimization Strategies

### Immediate (Phase 1)

1. **Enable S3 Bucket Key** - Reduces KMS costs by 99%
   - Savings: $0.27/month per 100 users
   
2. **Lifecycle Policies** - Move old videos to Glacier
   - Savings: $0.019/GB/month (83% reduction)
   - Impact: $0.038/user/month for 2GB

3. **CloudWatch Log Retention** - Delete after 90 days
   - Savings: $0.03/user/month

4. **Make Transcription Optional** - Let users choose
   - Savings: $0.48/user/month (64% of active cost)

**Total Immediate Savings:** $0.57/user/month (76% reduction for active users)

### Medium-Term (Phase 1.5)

1. **Client-Side Encryption** - Eliminates server-side transcription
   - Savings: $0.48/user/month
   - Trade-off: Users must decrypt locally

2. **Thumbnail Caching** - Reduce Lambda invocations
   - Savings: $0.002/user/month

3. **Batch Processing** - Process videos during off-peak hours
   - Savings: 10-20% on Lambda costs

**Total Medium-Term Savings:** $0.50/user/month

### Long-Term (Phase 2+)

1. **Reserved Capacity** - Commit to DynamoDB/Lambda capacity
   - Savings: 30-50% on compute

2. **Spot Instances** - For batch video processing
   - Savings: 70% on compute

3. **Multi-Region Optimization** - Use cheapest regions
   - Savings: 10-30% depending on region

4. **CDN Optimization** - Aggressive caching
   - Savings: 50% on data transfer

**Total Long-Term Savings:** $0.20/user/month

---

## Break-Even Analysis

### Scenario 1: $5/month Flat Rate

| Users | Revenue | Costs | Profit | Margin |
|-------|---------|-------|--------|--------|
| 50 | $250 | $210 | $40 | 16% |
| 100 | $500 | $210 | $290 | 58% |
| 500 | $2,500 | $585 | $1,915 | 77% |
| 1,000 | $5,000 | $585 | $4,415 | 88% |

**Break-even:** 42 users

### Scenario 2: $10/month Premium Tier (50% adoption)

| Users | Revenue | Costs | Profit | Margin |
|-------|---------|-------|--------|--------|
| 100 | $500 | $210 | $290 | 58% |
| 500 | $2,500 | $585 | $1,915 | 77% |
| 1,000 | $5,000 | $585 | $4,415 | 88% |

**Break-even:** 42 users (same as flat rate with 50% premium adoption)

### Scenario 3: Freemium Model

- 80% free users (storage only)
- 15% basic ($3/month)
- 5% premium ($10/month)

| Total Users | Free | Basic | Premium | Revenue | Costs | Profit |
|-------------|------|-------|---------|---------|-------|--------|
| 1,000 | 800 | 150 | 50 | $950 | $585 | $365 |
| 5,000 | 4,000 | 750 | 250 | $4,750 | $1,200 | $3,550 |
| 10,000 | 8,000 | 1,500 | 500 | $9,500 | $2,000 | $7,500 |

**Break-even:** 616 total users (93 paying)

---

## Recommendations

### For Current Scale (100 users)

**Recommended Pricing:** $5-7/month flat rate
- Simple to communicate
- Covers costs with healthy margin
- Room for discounts/promotions

### For Growth (1,000+ users)

**Recommended Pricing:** Tiered model
- Free tier for benefactors (view-only)
- $3/month basic (uploads, no AI)
- $10/month premium (AI features)

**Why:**
- Captures more market segments
- Maximizes revenue from power users
- Provides free tier for viral growth
- 80%+ profit margins at scale

### For Enterprise (10,000+ users)

**Recommended Pricing:** Usage-based
- $2/month base
- Pay-per-use for AI features
- Volume discounts for organizations
- Custom enterprise plans

**Why:**
- Fairest pricing at scale
- Aligns cost with value
- Enables B2B sales
- Predictable unit economics

---

## Conclusion

**Per-User Costs:**
- Active user: $0.75 - $1.50/month
- Low-use user: $0.10 - $0.20/month
- Average (50/50 mix): $0.43 - $0.85/month

**Recommended Pricing:**
- Minimum: $3/month (4x cost, 75% margin)
- Optimal: $5-7/month (6-8x cost, 83-88% margin)
- Premium: $10/month (12x cost, 92% margin)

**Key Insights:**
1. AI processing (transcription) is 64% of active user cost
2. Storage is cheap ($0.11/user/month)
3. Security overhead is minimal ($0.02/user/month)
4. Economies of scale kick in at 500+ users
5. Making transcription optional saves $0.48/user/month

**Next Steps:**
1. Implement cost optimizations (S3 Bucket Key, lifecycle policies)
2. Make transcription optional to reduce costs
3. Start with $5/month flat rate for simplicity
4. Transition to tiered pricing at 500+ users
5. Monitor actual usage patterns and adjust pricing

---

**Questions? Need more detailed analysis for specific scenarios?**
