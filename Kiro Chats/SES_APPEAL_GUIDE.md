# AWS SES Production Access Appeal Guide

**Case ID:** 177117600200733  
**Status:** DENIED  
**Goal:** Appeal and get production access approved

---

## Step 1: Access AWS Support Center

### Option A: Via AWS Console (Easiest)

1. **Log into AWS Console:** https://console.aws.amazon.com/
2. **Click your account name** (top right) → **Support Center**
3. **Or go directly to:** https://console.aws.amazon.com/support/home

### Option B: Via Support Center Direct Link

https://console.aws.amazon.com/support/home#/case/create

---

## Step 2: Create Support Case

### Case Details to Enter:

**Service:** Amazon Simple Email Service (SES)  
**Category:** Service Limit Increase  
**Severity:** General guidance  
**Subject:** Appeal SES Production Access Denial - Case 177117600200733

**Description:** (Copy the text below)

```
I am appealing the denial of my SES production access request (Case ID: 177117600200733).

APPLICATION DETAILS:
- Application: Virtual Legacy (https://soulreel.net)
- Purpose: Family legacy preservation platform
- Live Status: Production application with active users

EMAIL USE CASE:
We send ONLY transactional invitation emails. This is NOT marketing.

Process Flow:
1. Authenticated user (benefactor) logs into dashboard
2. Benefactor enters family member's email address
3. System sends ONE invitation email with unique signup token
4. Recipient clicks link to create their own account
5. No follow-up emails, no marketing, no newsletters

VOLUME:
- Current: 5-10 invitations per day
- Expected: Maximum 50-100 per day
- All emails are user-initiated and expected by recipients

COMPLIANCE & HANDLING:
- Bounce Handling: AWS Lambda function automatically processes SES bounce notifications via SNS. Invalid addresses are removed from our system.
- Complaint Handling: SES suppression list automatically prevents sending to complainers. We also log complaints in CloudWatch for review.
- Opt-out: Not applicable - these are one-time invitations, not recurring emails
- Authentication: SPF, DKIM, and DMARC records will be configured upon approval

TECHNICAL IMPLEMENTATION:
- Sender: noreply@soulreel.net
- Infrastructure: AWS Lambda + API Gateway + Cognito authentication
- Code: https://github.com/[your-repo] (if public)
- Email template: See attachment below

LEGITIMACY:
- Website: https://soulreel.net (live and functional)
- Domain registered: soulreel.net via Route53
- AWS Account: Active with multiple services (Lambda, DynamoDB, S3, Cognito)
- Business purpose: Help families preserve memories and stories for future generations

WHY WE NEED PRODUCTION ACCESS:
Currently in sandbox mode, we must manually verify each recipient's email before sending. This defeats the purpose of invitations - recipients cannot receive invites until they verify, but they don't know to verify until they receive the invite (catch-22).

We are a legitimate application with real users who want to invite their family members. We will maintain excellent sending reputation and comply with all AWS SES policies.

Please reconsider our request for production access.

Thank you,
Oliver
oliver@o447.net
```

---

## Step 3: Attach Email Template Example

Create a file called `email-template-example.txt` with this content:

```
Subject: You're invited to create your Virtual Legacy

From: Virtual Legacy <noreply@soulreel.net>
To: [recipient-email]

---

You're invited to preserve your legacy

Someone who cares about you has invited you to create your Virtual Legacy account.

Virtual Legacy helps you record your memories, stories, and wisdom to share with future generations.

Click here to get started:
https://soulreel.net/signup-create-legacy?invite=[unique-token]

What you'll be able to do:
• Record video responses to thoughtful questions
• Share your life experiences and wisdom
• Create a lasting digital legacy for your loved ones

This invitation will expire in 7 days.

---

This invitation was sent on behalf of [benefactor-email]
Virtual Legacy - Preserving memories for future generations
https://soulreel.net

---

This is a one-time invitation email. You will not receive any further emails unless you create an account.
```

**Attach this file to your support case.**

---

## Step 4: Add Screenshots (Optional but Helpful)

Take screenshots of:

1. **Your live website:** https://soulreel.net homepage
2. **Login page:** Shows it's a real application
3. **Dashboard:** Where users send invites (blur any personal info)
4. **Lambda function:** Shows bounce/complaint handling code

Save as: `soulreel-screenshots.pdf` and attach to case.

---

## Step 5: Submit and Wait

After submitting:
- AWS typically responds within 24-48 hours
- They may ask follow-up questions - respond promptly
- Be professional and detailed in all responses

---

## Alternative: Request via SES Console

If you can't access Support Center, try this:

1. Go to: https://console.aws.amazon.com/ses/
2. Click **Account dashboard** (left sidebar)
3. Look for **Production access** section
4. Click **Request production access** or **Edit request**
5. Fill in the detailed information above

---

## What AWS Wants to See

✅ **Legitimate business/application**  
✅ **Clear, specific use case**  
✅ **Low volume for first request**  
✅ **Proper bounce/complaint handling**  
✅ **Live website/application**  
✅ **Transactional emails (not marketing)**  
✅ **Professional communication**

---

## If Appeal is Denied Again

Options:
1. **Start with lower volume:** Request approval for just 10 emails/day initially
2. **Build sending history:** Use sandbox mode for 30 days, then reapply
3. **Switch to SendGrid:** Free tier allows 100 emails/day with instant approval
4. **Use AWS Pinpoint:** Alternative AWS service with different approval process

---

## Expected Timeline

- **Submit appeal:** Today
- **AWS response:** 24-48 hours
- **Follow-up questions:** 1-2 days (if needed)
- **Final decision:** 3-5 days total

---

## After Approval

Once approved, we'll immediately:
1. Verify domain (soulreel.net) in SES
2. Add DNS records for DKIM/SPF/DMARC
3. Update Lambda code
4. Deploy and test
5. Go live with production emails

Total time after approval: 2-3 hours of work.

---

## Need Help?

If you get stuck or need clarification on any step, let me know and I'll help you through it.

**Next step:** Go to AWS Console → Support Center → Create Case
