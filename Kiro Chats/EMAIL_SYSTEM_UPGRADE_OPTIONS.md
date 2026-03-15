# Email System Upgrade Analysis
## Moving from Validated Addresses to Production Domain

**Date:** February 15, 2026  
**Current Status:** Prototype using AWS SES Sandbox with validated addresses (@o447.net)

---

## Current Implementation Analysis

### What You Have Now

Your email system uses AWS SES (Simple Email Service) in **sandbox mode** with the following characteristics:

**Architecture:**
- Lambda function: `SendInviteEmailFunction` (SamLambda/functions/inviteFunctions/sendInviteEmail/)
- Trigger: API Gateway endpoint `/invites/send` (authenticated via Cognito)
- Email service: AWS SES with `ses:SendEmail` and `ses:SendRawEmail` permissions
- Current domains: `@o447.net` (test addresses like legacymaker1@o447.net, legacyBenefactor1@o447.net)

**Current Limitations (SES Sandbox):**
1. Can only send TO verified email addresses
2. Can only send FROM verified email addresses
3. Limited to 200 emails per 24-hour period
4. Limited to 1 email per second
5. All recipients must be manually verified via AWS console

**What Works Well:**
- Clean Lambda implementation with proper error handling
- JWT token extraction for benefactor identification
- HTML and plain text email templates
- DynamoDB integration for invite token storage
- 7-day invite expiration with TTL

**Critical Issue in Current Code:**
- Hardcoded localhost URL: `http://localhost:8080/signup-create-legacy?invite={invite_token}`
- This needs to be changed to your production domain

---

## Production-Ready Options

### Option 1: Move SES Out of Sandbox (Simplest)
**What it does:** Request production access for SES, continue using existing infrastructure

**Steps:**
1. Request production access via AWS SES console (takes 24-48 hours)
2. Verify your sending domain (e.g., soulreel.net)
3. Update Lambda code to use production domain
4. Configure SPF, DKIM, and DMARC records

**Pros:**
- Minimal code changes
- Uses existing Lambda function
- No new services to learn
- Cost-effective for low volume
- Can send to ANY email address (not just verified ones)

**Cons:**
- Still need to verify sending domain
- Requires DNS configuration
- Need to maintain email reputation

**Cost:** ~$0.10 per 1,000 emails (very cheap for low volume)

**Ease of Implementation with CLI:** ⭐⭐⭐⭐⭐ (5/5)
- Single AWS CLI command to request production access
- DNS records can be added via CLI
- Lambda code update is straightforward

**Best for:** Your use case - low volume, transactional emails

---

### Option 2: Use a Custom Domain with SES
**What it does:** Set up noreply@soulreel.net or invites@soulreel.net as sender

**Steps:**
1. Request SES production access
2. Verify soulreel.net domain in SES
3. Add DNS records (TXT, CNAME for DKIM)
4. Update Lambda to use custom sender address
5. Configure email forwarding if needed

**Pros:**
- Professional appearance (emails from @soulreel.net)
- Better deliverability with proper DNS setup
- Can use multiple sender addresses (noreply@, support@, etc.)
- Full control over email branding

**Cons:**
- Requires DNS management
- Need to monitor bounce/complaint rates
- More setup steps than Option 1

**Cost:** Same as Option 1 (~$0.10 per 1,000 emails)

**Ease of Implementation with CLI:** ⭐⭐⭐⭐ (4/5)
- AWS CLI can handle most tasks
- DNS updates require access to domain registrar
- Verification process is automated

**Best for:** Professional appearance with your own domain

---

### Option 3: Third-Party Email Service (SendGrid, Mailgun, Postmark)
**What it does:** Replace SES with a dedicated email service provider

**Steps:**
1. Sign up for service (e.g., SendGrid free tier: 100 emails/day)
2. Verify domain with provider
3. Get API key
4. Update Lambda to use provider's API instead of SES
5. Store API key in AWS Secrets Manager or SSM Parameter Store

**Pros:**
- Better deliverability (they manage reputation)
- Built-in analytics and tracking
- Email templates and testing tools
- Easier domain verification
- Better support and documentation

**Cons:**
- Additional service to manage
- Code changes required in Lambda
- Potential vendor lock-in
- May be overkill for low volume

**Cost:**
- SendGrid: Free (100/day), $15/mo (40k/mo)
- Mailgun: Free (5k/mo), $35/mo (50k/mo)
- Postmark: $15/mo (10k/mo)

**Ease of Implementation with CLI:** ⭐⭐⭐ (3/5)
- Requires Lambda code changes
- Need to manage API keys securely
- Different API patterns to learn

**Best for:** If you want advanced features or better deliverability guarantees

---

### Option 4: Keep Sandbox Mode with Verified Recipients
**What it does:** Continue current approach, just verify production email addresses

**Steps:**
1. Verify each recipient email address in SES console
2. Update localhost URL to production domain
3. Keep everything else the same

**Pros:**
- Zero AWS approval process
- Works immediately
- No DNS configuration needed
- Simplest option

**Cons:**
- Every recipient must be manually verified
- Limited to 200 emails/day
- Not scalable
- Unprofessional for production

**Cost:** Free (within AWS free tier)

**Ease of Implementation with CLI:** ⭐⭐⭐⭐⭐ (5/5)
- Just update Lambda code
- Verify emails via AWS CLI

**Best for:** Extended testing, very limited user base (not recommended for production)

---

## Recommended Approach

### 🏆 **Option 2: Custom Domain with SES Production Access**

**Why this is best for you:**
1. You already have soulreel.net domain
2. Low email volume means SES is cost-effective
3. Professional appearance builds trust
4. Minimal code changes
5. Easy to implement with CLI

**Implementation Timeline:** 2-3 days
- Day 1: Request SES production access (24-48 hour wait)
- Day 2: Configure DNS records
- Day 3: Update Lambda code and test

---

## Step-by-Step Implementation Plan

### Phase 1: Request SES Production Access (Day 1)
```bash
# This opens a support case with AWS
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url https://soulreel.net \
  --use-case-description "Sending invitation emails for Virtual Legacy platform. Low volume transactional emails to users who request to join the platform." \
  --additional-contact-email-addresses your-email@example.com
```

**What to include in request:**
- Use case: Transactional invitation emails
- Expected volume: <100 emails/day
- Bounce/complaint handling: Automated via Lambda
- Website: https://soulreel.net

### Phase 2: Verify Domain (Day 2, after approval)
```bash
# Verify your domain
aws sesv2 create-email-identity \
  --email-identity soulreel.net

# Get DNS records to add
aws sesv2 get-email-identity \
  --email-identity soulreel.net
```

**DNS Records to Add:**
You'll need to add these to your domain registrar (the CLI will give you exact values):
1. TXT record for domain verification
2. CNAME records for DKIM (3 records)
3. TXT record for SPF: `v=spf1 include:amazonses.com ~all`
4. TXT record for DMARC: `v=DMARC1; p=none; rua=mailto:dmarc@soulreel.net`

### Phase 3: Update Lambda Code (Day 3)
```python
# Changes needed in: SamLambda/functions/inviteFunctions/sendInviteEmail/app.py

# 1. Change sender email (line ~130)
# OLD:
response = ses_client.send_email(
    Source=benefactor_email,  # This uses the benefactor's email
    ...
)

# NEW:
response = ses_client.send_email(
    Source='invites@soulreel.net',  # Professional sender address
    ReplyTo=[benefactor_email],  # Replies go to benefactor
    ...
)

# 2. Update invite URL (line ~95 and ~145)
# OLD:
href="http://localhost:8080/signup-create-legacy?invite={invite_token}"

# NEW:
href="https://soulreel.net/signup-create-legacy?invite={invite_token}"
```

### Phase 4: Deploy and Test
```bash
# Deploy updated Lambda
cd SamLambda
sam build
sam deploy

# Test email sending
python test_invite_system.py
```

---

## Code Changes Required

### File: `SamLambda/functions/inviteFunctions/sendInviteEmail/app.py`

**Change 1: Sender Address**

```python
# Line ~130 in send_invite_email function
# BEFORE:
response = ses_client.send_email(
    Source=benefactor_email,
    Destination={'ToAddresses': [invitee_email]},
    Message={...}
)

# AFTER:
response = ses_client.send_email(
    Source='invites@soulreel.net',  # Professional sender
    ReplyTo=[benefactor_email],      # Replies go to benefactor
    Destination={'ToAddresses': [invitee_email]},
    Message={...}
)
```

**Change 2: Invite URLs**
```python
# Line ~95 (HTML body)
# BEFORE:
<a href="http://localhost:8080/signup-create-legacy?invite={invite_token}" class="button">

# AFTER:
<a href="https://soulreel.net/signup-create-legacy?invite={invite_token}" class="button">

# Line ~145 (Text body)
# BEFORE:
Visit this link to get started: http://localhost:8080/signup-create-legacy?invite={invite_token}

# AFTER:
Visit this link to get started: https://soulreel.net/signup-create-legacy?invite={invite_token}
```

**Change 3: Email Footer (Optional Enhancement)**
```python
# Update footer to be more professional
<div class="footer">
    <p>This invitation was sent on behalf of {benefactor_email}</p>
    <p>Virtual Legacy - Preserving memories for future generations</p>
    <p><a href="https://soulreel.net">Visit our website</a> | <a href="https://soulreel.net/privacy">Privacy Policy</a></p>
</div>
```

---

## DNS Configuration Details

Once SES is approved and you verify your domain, you'll need to add these DNS records:

### Required DNS Records

**1. Domain Verification (TXT)**
```
Type: TXT
Name: _amazonses.soulreel.net
Value: [AWS will provide this - looks like: abc123def456...]
TTL: 1800
```

**2. DKIM Records (3 CNAME records)**
```
Type: CNAME
Name: abc123._domainkey.soulreel.net
Value: abc123.dkim.amazonses.com
TTL: 1800

Type: CNAME
Name: def456._domainkey.soulreel.net
Value: def456.dkim.amazonses.com
TTL: 1800

Type: CNAME
Name: ghi789._domainkey.soulreel.net
Value: ghi789.dkim.amazonses.com
TTL: 1800
```

**3. SPF Record (TXT)**
```
Type: TXT
Name: soulreel.net
Value: v=spf1 include:amazonses.com ~all
TTL: 1800
```

**4. DMARC Record (TXT)**
```
Type: TXT
Name: _dmarc.soulreel.net
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@soulreel.net
TTL: 1800
```

### How to Add DNS Records via CLI

If your domain is hosted on Route53:
```bash
# Get your hosted zone ID
aws route53 list-hosted-zones-by-name --dns-name soulreel.net

# Add records (example for SPF)
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch file://dns-changes.json
```

**dns-changes.json:**
```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "soulreel.net",
      "Type": "TXT",
      "TTL": 1800,
      "ResourceRecords": [{"Value": "\"v=spf1 include:amazonses.com ~all\""}]
    }
  }]
}
```

---

## Testing Checklist

### Before Going Live
- [ ] SES production access approved
- [ ] Domain verified in SES console
- [ ] All DNS records added and propagated (check with `dig` or `nslookup`)
- [ ] Lambda code updated with production URLs
- [ ] Lambda code updated with professional sender address
- [ ] Test email sent successfully
- [ ] Email received in inbox (not spam)
- [ ] Invite link works correctly
- [ ] Reply-to address works (replies go to benefactor)

### Test Commands
```bash
# Check DNS propagation
dig TXT soulreel.net
dig TXT _amazonses.soulreel.net
dig TXT _dmarc.soulreel.net

# Verify domain status
aws sesv2 get-email-identity --email-identity soulreel.net

# Check sending quota
aws sesv2 get-account

# Send test email via Lambda
aws lambda invoke \
  --function-name SendInviteEmailFunction \
  --payload file://test-event.json \
  response.json
```

---

## Monitoring and Maintenance

### Set Up CloudWatch Alarms
```bash
# Alert on bounce rate > 5%
aws cloudwatch put-metric-alarm \
  --alarm-name ses-high-bounce-rate \
  --alarm-description "Alert when SES bounce rate exceeds 5%" \
  --metric-name Reputation.BounceRate \
  --namespace AWS/SES \
  --statistic Average \
  --period 3600 \
  --threshold 0.05 \
  --comparison-operator GreaterThanThreshold

# Alert on complaint rate > 0.1%
aws cloudwatch put-metric-alarm \
  --alarm-name ses-high-complaint-rate \
  --alarm-description "Alert when SES complaint rate exceeds 0.1%" \
  --metric-name Reputation.ComplaintRate \
  --namespace AWS/SES \
  --statistic Average \
  --period 3600 \
  --threshold 0.001 \
  --comparison-operator GreaterThanThreshold
```

### Handle Bounces and Complaints
Add SNS topic for notifications:
```bash
# Create SNS topic
aws sns create-topic --name ses-bounce-complaints

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT:ses-bounce-complaints \
  --protocol email \
  --notification-endpoint your-email@example.com

# Configure SES to publish to SNS
aws sesv2 put-configuration-set-event-destination \
  --configuration-set-name default \
  --event-destination-name bounce-complaint-notifications \
  --event-destination '{
    "Enabled": true,
    "MatchingEventTypes": ["BOUNCE", "COMPLAINT"],
    "SnsDestination": {
      "TopicArn": "arn:aws:sns:us-east-1:YOUR_ACCOUNT:ses-bounce-complaints"
    }
  }'
```

---

## Cost Breakdown

### Option 2 (Recommended): SES with Custom Domain

**Monthly Costs (assuming 100 emails/month):**
- SES emails: 100 × $0.0001 = $0.01
- SES data transfer: ~$0.01
- Lambda invocations: Free tier (1M free/month)
- DynamoDB: Free tier
- **Total: ~$0.02/month** (essentially free)

**At scale (1,000 emails/month):**
- SES emails: 1,000 × $0.0001 = $0.10
- **Total: ~$0.11/month**

**At higher scale (10,000 emails/month):**
- SES emails: 10,000 × $0.0001 = $1.00
- **Total: ~$1.01/month**

### Comparison with Third-Party Services

| Service | Free Tier | Paid Tier | Cost at 1k/mo | Cost at 10k/mo |
|---------|-----------|-----------|---------------|----------------|
| **AWS SES** | 62k/mo (if on EC2) | $0.10/1k | $0.10 | $1.00 |
| SendGrid | 100/day | $15/mo | $15 | $15 |
| Mailgun | 5k/mo | $35/mo | Free | $35 |
| Postmark | None | $15/mo | $15 | $15 |

**Winner for low volume: AWS SES** (by far)

---

## Security Considerations

### 1. Protect Against Email Spoofing
- SPF record prevents others from sending as your domain
- DKIM signs emails cryptographically
- DMARC tells receivers what to do with failed checks

### 2. Rate Limiting
Add to Lambda to prevent abuse:
```python
# In app.py, add rate limiting check
def check_rate_limit(benefactor_id):
    """Limit to 10 invites per hour per benefactor"""
    # Use DynamoDB or ElastiCache to track
    # Return True if under limit, False if exceeded
    pass
```

### 3. Validate Email Addresses
```python
import re

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
```

### 4. Store API Keys Securely
If you ever need to store sensitive data:
```bash
# Use AWS Systems Manager Parameter Store
aws ssm put-parameter \
  --name /virtuallegacy/email/sender \
  --value "invites@soulreel.net" \
  --type String

# Or use Secrets Manager for sensitive data
aws secretsmanager create-secret \
  --name virtuallegacy/email/api-key \
  --secret-string "your-secret-key"
```

---

## Rollback Plan

If something goes wrong:

### Quick Rollback
```bash
# Revert Lambda to previous version
aws lambda update-function-code \
  --function-name SendInviteEmailFunction \
  --s3-bucket your-deployment-bucket \
  --s3-key previous-version.zip

# Or use SAM
cd SamLambda
git checkout HEAD~1 functions/inviteFunctions/sendInviteEmail/app.py
sam build && sam deploy
```

### Fallback to Sandbox Mode
1. Keep sandbox mode active during transition
2. Test production setup with a few verified addresses first
3. Only remove sandbox addresses after confirming production works

---

## Timeline Summary

### Recommended Path: Option 2 (Custom Domain with SES)

**Day 1 (15 minutes):**
- Submit SES production access request via AWS CLI
- Wait for approval (24-48 hours)

**Day 2 (30 minutes):**
- Verify domain in SES
- Add DNS records (TXT, CNAME, SPF, DMARC)
- Wait for DNS propagation (1-24 hours)

**Day 3 (1 hour):**
- Update Lambda code (3 changes)
- Deploy via SAM CLI
- Test with real email addresses
- Monitor first few sends

**Total active work: ~2 hours**  
**Total calendar time: 2-3 days**

---

## Quick Start Commands

Here's everything you need to run, in order:

```bash
# 1. Request production access
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url https://soulreel.net \
  --use-case-description "Transactional invitation emails for Virtual Legacy platform"

# 2. Wait for approval email from AWS (24-48 hours)

# 3. Verify domain
aws sesv2 create-email-identity --email-identity soulreel.net

# 4. Get DNS records to add
aws sesv2 get-email-identity --email-identity soulreel.net

# 5. Add DNS records (via your domain registrar or Route53)

# 6. Check verification status
aws sesv2 get-email-identity --email-identity soulreel.net | grep VerificationStatus

# 7. Update Lambda code (see changes above)

# 8. Deploy
cd SamLambda
sam build
sam deploy

# 9. Test
python test_invite_system.py
```

---

## Conclusion

**Recommended: Option 2 - Custom Domain with SES Production Access**

This gives you:
- ✅ Professional emails from @soulreel.net
- ✅ Unlimited recipients (no more verified addresses)
- ✅ Extremely low cost (~$0.10 per 1,000 emails)
- ✅ Easy CLI implementation
- ✅ Minimal code changes
- ✅ Scalable for future growth

**Total effort:** ~2 hours of active work, 2-3 days calendar time

**Next step:** Run the first command to request SES production access, then I can help you with the DNS configuration and code updates once approved.
