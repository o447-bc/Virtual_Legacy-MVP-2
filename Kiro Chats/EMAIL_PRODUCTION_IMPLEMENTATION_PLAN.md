# Email Production Implementation Plan
## CLI-Based Step-by-Step Guide

**Goal:** Move from SES sandbox with validated addresses to production with noreply@soulreel.net  
**Approach:** Option A - No-reply address, no inbox management  
**Timeline:** 2-3 days (mostly waiting for AWS approval)  
**Active Work:** ~2 hours total

---

## Prerequisites Check

Before starting, verify you have:

```bash
# 1. AWS CLI installed and configured
aws --version
# Should show: aws-cli/2.x.x or higher

# 2. AWS credentials configured
aws sts get-caller-identity
# Should show your account ID and user

# 3. SAM CLI installed (for Lambda deployment)
sam --version
# Should show: SAM CLI, version 1.x.x or higher

# 4. Access to your domain DNS settings
# You'll need to add DNS records (via registrar or Route53)

# 5. Current directory
cd /path/to/Virtual-Legacy-MVP-1
```

---

## Phase 1: Request SES Production Access

**Time:** 5 minutes (then wait 24-48 hours for approval)

### Step 1.1: Check Current SES Status

```bash
# Check if you're in sandbox mode
aws sesv2 get-account

# Look for: ProductionAccessEnabled: false
```

### Step 1.2: Submit Production Access Request

```bash
# Submit the request
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url https://soulreel.net \
  --use-case-description "Virtual Legacy sends transactional invitation emails when benefactors invite family members to create legacy accounts. Low volume (<100 emails/day). Users opt-in by requesting invites. Bounce and complaint handling automated via Lambda." \
  --additional-contact-email-addresses oliver@youremail.com \
  --region us-east-1
```

**Expected Output:**
```
{
    "Status": "PENDING"
}
```

### Step 1.3: Monitor Request Status

```bash
# Check status (run this periodically)
aws sesv2 get-account --region us-east-1 | grep ProductionAccessEnabled

# When approved, you'll see: "ProductionAccessEnabled": true
```

**What happens next:**
- AWS reviews your request (usually 24-48 hours)
- You'll receive an email when approved
- Once approved, proceed to Phase 2

---

## Phase 2: Verify Domain in SES

**Time:** 10 minutes (then wait 1-24 hours for DNS propagation)  
**Prerequisites:** SES production access approved

### Step 2.1: Create Email Identity

```bash
# Verify your domain
aws sesv2 create-email-identity \
  --email-identity soulreel.net \
  --region us-east-1
```

**Expected Output:**
```json
{
    "IdentityType": "DOMAIN",
    "VerifiedForSendingStatus": false
}
```

### Step 2.2: Get DNS Records to Add

```bash
# Get the DNS records you need to add
aws sesv2 get-email-identity \
  --email-identity soulreel.net \
  --region us-east-1 > ses-dns-records.json

# View the records
cat ses-dns-records.json
```

**Save this output!** You'll need these values for DNS configuration.

### Step 2.3: Extract DNS Record Values

```bash
# Extract domain verification token
cat ses-dns-records.json | grep -A 5 "DkimAttributes"

# You'll see something like:
# "Tokens": [
#   "abc123def456ghi789",
#   "jkl012mno345pqr678",
#   "stu901vwx234yz567"
# ]
```

### Step 2.4: Add DNS Records

You need to add these records to your domain. Choose your method:

#### Option A: If using Route53

```bash
# Get your hosted zone ID
aws route53 list-hosted-zones-by-name \
  --dns-name soulreel.net \
  --query 'HostedZones[0].Id' \
  --output text

# Save the zone ID (looks like: /hostedzone/Z1234567890ABC)
ZONE_ID="Z1234567890ABC"  # Replace with your actual zone ID
```

Create a file `dns-records.json`:

```bash
cat > dns-records.json << 'EOF'
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "abc123def456ghi789._domainkey.soulreel.net",
        "Type": "CNAME",
        "TTL": 1800,
        "ResourceRecords": [
          {
            "Value": "abc123def456ghi789.dkim.amazonses.com"
          }
        ]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "jkl012mno345pqr678._domainkey.soulreel.net",
        "Type": "CNAME",
        "TTL": 1800,
        "ResourceRecords": [
          {
            "Value": "jkl012mno345pqr678.dkim.amazonses.com"
          }
        ]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "stu901vwx234yz567._domainkey.soulreel.net",
        "Type": "CNAME",
        "TTL": 1800,
        "ResourceRecords": [
          {
            "Value": "stu901vwx234yz567.dkim.amazonses.com"
          }
        ]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "soulreel.net",
        "Type": "TXT",
        "TTL": 1800,
        "ResourceRecords": [
          {
            "Value": "\"v=spf1 include:amazonses.com ~all\""
          }
        ]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_dmarc.soulreel.net",
        "Type": "TXT",
        "TTL": 1800,
        "ResourceRecords": [
          {
            "Value": "\"v=DMARC1; p=none; rua=mailto:dmarc@soulreel.net\""
          }
        ]
      }
    }
  ]
}
EOF
```

**IMPORTANT:** Replace the DKIM token values (abc123..., jkl012..., stu901...) with the actual values from `ses-dns-records.json`

```bash
# Apply the DNS changes
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch file://dns-records.json
```

#### Option B: If using another DNS provider

You'll need to manually add these records via your registrar's web interface:

**DKIM Records (3 CNAME records):**
```
Type: CNAME
Name: abc123def456ghi789._domainkey.soulreel.net
Value: abc123def456ghi789.dkim.amazonses.com
TTL: 1800

Type: CNAME
Name: jkl012mno345pqr678._domainkey.soulreel.net
Value: jkl012mno345pqr678.dkim.amazonses.com
TTL: 1800

Type: CNAME
Name: stu901vwx234yz567._domainkey.soulreel.net
Value: stu901vwx234yz567.dkim.amazonses.com
TTL: 1800
```

**SPF Record (TXT record):**
```
Type: TXT
Name: soulreel.net
Value: v=spf1 include:amazonses.com ~all
TTL: 1800
```

**DMARC Record (TXT record):**
```
Type: TXT
Name: _dmarc.soulreel.net
Value: v=DMARC1; p=none; rua=mailto:dmarc@soulreel.net
TTL: 1800
```

### Step 2.5: Verify DNS Propagation

```bash
# Check DKIM records (replace with your actual token)
dig CNAME abc123def456ghi789._domainkey.soulreel.net +short

# Check SPF record
dig TXT soulreel.net +short | grep spf1

# Check DMARC record
dig TXT _dmarc.soulreel.net +short

# All should return values. If empty, DNS hasn't propagated yet (wait 1-24 hours)
```

### Step 2.6: Check SES Verification Status

```bash
# Check if domain is verified
aws sesv2 get-email-identity \
  --email-identity soulreel.net \
  --region us-east-1 \
  --query 'DkimAttributes.Status' \
  --output text

# Should show: SUCCESS (once DNS propagates)
# If PENDING, wait and check again later
```

---

## Phase 3: Update Lambda Code

**Time:** 30 minutes  
**Prerequisites:** Domain verified in SES

### Step 3.1: Backup Current Code

```bash
# Navigate to the function directory
cd SamLambda/functions/inviteFunctions/sendInviteEmail

# Create backup
cp app.py app.py.backup

# Verify backup
ls -la app.py*
```

### Step 3.2: Review Current Code

```bash
# View current implementation
cat app.py | grep -A 10 "def send_invite_email"
cat app.py | grep "localhost"
cat app.py | grep "Source="
```

### Step 3.3: Update the Code

Create the updated version:

```bash
cat > app.py << 'EOF'
import json
import boto3
import uuid
import time
import base64
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """Send invitation email via SES"""
    
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            },
            'body': ''
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract parameters and normalize to lowercase
        benefactor_email = body.get('benefactor_email', '').lower()
        invitee_email = body.get('invitee_email', '').lower()
        
        if not all([benefactor_email, invitee_email]):
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Extract benefactor_id from JWT token in Authorization header
        benefactor_id = extract_user_id_from_jwt(event)
        if not benefactor_id:
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Unable to identify benefactor from token'})
            }
        
        # Generate invite token
        invite_token = str(uuid.uuid4())
        
        # Store invite data (non-blocking - continue if this fails)
        try:
            store_invite_token(invite_token, benefactor_id, invitee_email)
        except Exception as store_error:
            print(f"Warning: Failed to store invite token: {str(store_error)}")
        
        # Send email (this is the critical operation)
        try:
            result = send_invite_email(benefactor_email, invitee_email, invite_token)
        except Exception as email_error:
            print(f"SES Error Details: {str(email_error)}")
            raise Exception(f"Email sending failed: {str(email_error)}")
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'message': 'Invitation sent successfully',
                'invite_token': invite_token,
                'sent_to': invitee_email
            })
        }
        
    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def send_invite_email(benefactor_email, invitee_email, invite_token):
    """Send invitation email using SES"""
    
    ses_client = boto3.client('ses', region_name='us-east-1')
    
    # Professional sender - no-reply address
    sender = 'Virtual Legacy <noreply@soulreel.net>'
    
    # Email content
    subject = "You're invited to create your Virtual Legacy"
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #6366f1; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background-color: #f9fafb; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>You're invited to preserve your legacy</h2>
                <p>Someone who cares about you has invited you to create your Virtual Legacy account.</p>
                <p>Virtual Legacy helps you record your memories, stories, and wisdom to share with future generations.</p>
                <p>Click the button below to get started:</p>
                <a href="https://soulreel.net/signup-create-legacy?invite={invite_token}" class="button">Create Your Legacy</a>
                <p><strong>What you'll be able to do:</strong></p>
                <ul>
                    <li>Record video responses to thoughtful questions</li>
                    <li>Share your life experiences and wisdom</li>
                    <li>Create a lasting digital legacy for your loved ones</li>
                </ul>
                <p>This invitation will expire in 7 days.</p>
            </div>
            <div class="footer">
                <p>This invitation was sent on behalf of {benefactor_email}</p>
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="https://soulreel.net">Visit our website</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    You're invited to create your Virtual Legacy!
    
    Someone who cares about you has invited you to create your Virtual Legacy account.
    
    Virtual Legacy helps you record your memories, stories, and wisdom to share with future generations.
    
    Visit this link to get started: https://soulreel.net/signup-create-legacy?invite={invite_token}
    
    What you'll be able to do:
    - Record video responses to thoughtful questions
    - Share your life experiences and wisdom  
    - Create a lasting digital legacy for your loved ones
    
    This invitation will expire in 7 days.
    
    This invitation was sent on behalf of {benefactor_email}
    Virtual Legacy - Preserving memories for future generations
    https://soulreel.net
    """
    
    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [invitee_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        
        print(f"Email sent successfully. MessageId: {response['MessageId']}")
        return response
        
    except ClientError as e:
        print(f"SES Error: {e.response['Error']['Message']}")
        raise e

def extract_user_id_from_jwt(event):
    """
    Extract user ID from JWT token in Authorization header.
    
    Args:
        event: Lambda event containing headers with Authorization token
        
    Returns:
        str: User ID from JWT token, or None if extraction fails
    """
    try:
        # Get Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            print("No Bearer token found in Authorization header")
            return None
        
        # Extract JWT token (remove 'Bearer ' prefix)
        jwt_token = auth_header[7:]
        
        # Parse JWT payload (second part after first dot)
        # JWT format: header.payload.signature
        token_parts = jwt_token.split('.')
        if len(token_parts) != 3:
            print("Invalid JWT token format")
            return None
        
        # Decode payload (add padding if needed for base64 decoding)
        payload_b64 = token_parts[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        
        # Decode base64 payload
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        
        # Extract user ID from 'sub' claim (standard JWT claim for subject/user ID)
        user_id = payload.get('sub')
        if user_id:
            print(f"Extracted user ID from JWT: {user_id}")
            return user_id
        else:
            print("No 'sub' claim found in JWT payload")
            return None
            
    except Exception as e:
        print(f"Error extracting user ID from JWT: {str(e)}")
        return None

def store_invite_token(invite_token, benefactor_id, invitee_email):
    """
    Store invite token data in PersonaSignupTempDB for processing during signup.
    
    Args:
        invite_token: Unique invite token (UUID)
        benefactor_id: Cognito user ID of the benefactor who sent the invite
        invitee_email: Email address of the person being invited
    """
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('PersonaSignupTempDB')
        
        # Calculate expiration time (7 days from now)
        expiration_time = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days in seconds
        
        # Store invite data using invite_token as the key
        table.put_item(
            Item={
                'userName': invite_token,  # Using invite_token as primary key
                'benefactor_id': benefactor_id,  # Who sent the invite
                'invitee_email': invitee_email,  # Who was invited
                'invite_type': 'legacy_maker_invite',  # Type of invite
                'created_at': datetime.now().isoformat(),  # When invite was created
                'ttl': expiration_time  # Auto-delete after 7 days
            }
        )
        
        print(f"Stored invite token {invite_token} for benefactor {benefactor_id} -> {invitee_email}")
        
    except Exception as e:
        print(f"Error storing invite token: {str(e)}")
        # Don't fail the entire invite process if storage fails
        # The email will still be sent, but relationship won't be auto-created
        raise e
EOF
```

### Step 3.4: Verify Changes

```bash
# Check the key changes
echo "=== Checking sender address ==="
grep "Source=" app.py

echo "=== Checking URLs ==="
grep "soulreel.net" app.py

echo "=== Checking no ReplyTo (should be empty) ==="
grep -i "replyto" app.py || echo "Good - no ReplyTo found"

# Compare with backup
echo "=== Differences from original ==="
diff app.py.backup app.py
```

**Expected differences:**
- Line ~90: `sender = 'Virtual Legacy <noreply@soulreel.net>'`
- Line ~95: `https://soulreel.net/signup-create-legacy?invite={invite_token}`
- Line ~145: `https://soulreel.net/signup-create-legacy?invite={invite_token}`
- Line ~155: `Source=sender` (no ReplyTo parameter)

---

## Phase 4: Deploy Updated Lambda

**Time:** 15 minutes  
**Prerequisites:** Code updated and verified

### Step 4.1: Navigate to SAM Directory

```bash
# Go to SAM project root
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Documents\ -\ Mac/AI/Virtual-Legacy/Virtual-Legacy-MVP-1/SamLambda
```

### Step 4.2: Build SAM Application

```bash
# Build the application
sam build

# Expected output:
# Building codeuri: functions/inviteFunctions/sendInviteEmail/ runtime: python3.12
# ...
# Build Succeeded
```

### Step 4.3: Deploy to AWS

```bash
# Deploy (uses existing samconfig.toml)
sam deploy

# You'll see:
# Deploying with following values
# Stack name: virtual-legacy-backend
# Region: us-east-1
# ...
# Successfully created/updated stack
```

### Step 4.4: Verify Deployment

```bash
# Get function info
aws lambda get-function \
  --function-name SendInviteEmailFunction \
  --region us-east-1 \
  --query 'Configuration.[FunctionName,LastModified,Runtime]' \
  --output table

# Check function logs (should show recent update)
aws logs tail /aws/lambda/SendInviteEmailFunction --follow
```

---

## Phase 5: Test the System

**Time:** 20 minutes  
**Prerequisites:** Lambda deployed, domain verified

### Step 5.1: Prepare Test Event

```bash
# Create test event file
cat > test-invite-event.json << 'EOF'
{
  "httpMethod": "POST",
  "headers": {
    "Authorization": "Bearer eyJraWQiOiJtest-token-here",
    "Content-Type": "application/json"
  },
  "body": "{\"benefactor_email\":\"test-benefactor@example.com\",\"invitee_email\":\"your-real-email@gmail.com\"}"
}
EOF
```

**IMPORTANT:** Replace `your-real-email@gmail.com` with your actual email address for testing.

### Step 5.2: Test Lambda Directly

```bash
# Invoke the function
aws lambda invoke \
  --function-name SendInviteEmailFunction \
  --payload file://test-invite-event.json \
  --region us-east-1 \
  response.json

# Check response
cat response.json | jq '.'
```

**Expected response:**
```json
{
  "statusCode": 200,
  "headers": {
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"message\":\"Invitation sent successfully\",\"invite_token\":\"abc-123-def-456\",\"sent_to\":\"your-real-email@gmail.com\"}"
}
```

### Step 5.3: Check Your Email

```bash
# While waiting for email, check CloudWatch logs
aws logs tail /aws/lambda/SendInviteEmailFunction \
  --since 5m \
  --follow

# Look for:
# "Email sent successfully. MessageId: ..."
```

**Verify in your inbox:**
- [ ] Email received from "Virtual Legacy <noreply@soulreel.net>"
- [ ] Subject: "You're invited to create your Virtual Legacy"
- [ ] Link goes to: https://soulreel.net/signup-create-legacy?invite=...
- [ ] Email mentions benefactor: "sent on behalf of test-benefactor@example.com"
- [ ] Email is NOT in spam folder

### Step 5.4: Test via API Gateway

```bash
# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name virtual-legacy-backend \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`SendInviteEmailApi`].OutputValue' \
  --output text

# Save the endpoint
API_ENDPOINT="https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod/invites/send"

# Test with curl (you'll need a real Cognito token)
curl -X POST $API_ENDPOINT \
  -H "Authorization: Bearer YOUR_COGNITO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "test-benefactor@example.com",
    "invitee_email": "your-real-email@gmail.com"
  }'
```

### Step 5.5: Run Full Test Suite

```bash
# Navigate to test directory
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Documents\ -\ Mac/AI/Virtual-Legacy/Virtual-Legacy-MVP-1/SamLambda

# Update test file with production domain
sed -i.bak 's/legacymaker1@o447.net/your-real-email@gmail.com/g' test_invite_system.py
sed -i.bak 's/legacyBenefactor1@o447.net/test-benefactor@example.com/g' test_invite_system.py

# Run tests
python3 test_invite_system.py
```

---

## Phase 6: Monitor and Verify Production

**Time:** 10 minutes  
**Prerequisites:** Tests passing, emails received

### Step 6.1: Check SES Sending Statistics

```bash
# Get sending statistics
aws sesv2 get-account \
  --region us-east-1 \
  --query '{SendQuota:SendQuota,SendingEnabled:SendingEnabled,ProductionAccess:ProductionAccessEnabled}' \
  --output table

# Get detailed metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SES \
  --metric-name Send \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

### Step 6.2: Check Email Reputation

```bash
# Check bounce and complaint rates
aws sesv2 get-account \
  --region us-east-1 \
  --query 'SendQuota' \
  --output table

# View reputation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SES \
  --metric-name Reputation.BounceRate \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average \
  --region us-east-1
```

**Healthy metrics:**
- Bounce rate: < 5%
- Complaint rate: < 0.1%
- Sending enabled: true

### Step 6.3: Set Up CloudWatch Alarms

```bash
# Create alarm for high bounce rate
aws cloudwatch put-metric-alarm \
  --alarm-name ses-high-bounce-rate \
  --alarm-description "Alert when SES bounce rate exceeds 5%" \
  --metric-name Reputation.BounceRate \
  --namespace AWS/SES \
  --statistic Average \
  --period 3600 \
  --threshold 0.05 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region us-east-1

# Create alarm for high complaint rate
aws cloudwatch put-metric-alarm \
  --alarm-name ses-high-complaint-rate \
  --alarm-description "Alert when SES complaint rate exceeds 0.1%" \
  --metric-name Reputation.ComplaintRate \
  --namespace AWS/SES \
  --statistic Average \
  --period 3600 \
  --threshold 0.001 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region us-east-1

# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name invite-lambda-errors \
  --alarm-description "Alert on Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=SendInviteEmailFunction \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region us-east-1
```

### Step 6.4: Enable SES Event Publishing (Optional)

```bash
# Create SNS topic for notifications
aws sns create-topic \
  --name ses-email-events \
  --region us-east-1

# Get topic ARN
TOPIC_ARN=$(aws sns list-topics --region us-east-1 --query 'Topics[?contains(TopicArn, `ses-email-events`)].TopicArn' --output text)

# Subscribe your email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1

# Confirm subscription (check your email and click confirm link)

# Create configuration set
aws sesv2 create-configuration-set \
  --configuration-set-name virtual-legacy-emails \
  --region us-east-1

# Add event destination
aws sesv2 create-configuration-set-event-destination \
  --configuration-set-name virtual-legacy-emails \
  --event-destination-name bounce-complaint-notifications \
  --event-destination '{
    "Enabled": true,
    "MatchingEventTypes": ["BOUNCE", "COMPLAINT", "DELIVERY"],
    "SnsDestination": {
      "TopicArn": "'$TOPIC_ARN'"
    }
  }' \
  --region us-east-1
```

### Step 6.5: View Recent Logs

```bash
# Tail Lambda logs in real-time
aws logs tail /aws/lambda/SendInviteEmailFunction \
  --follow \
  --region us-east-1

# Search for errors in last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/SendInviteEmailFunction \
  --start-time $(date -u -v-1H +%s)000 \
  --filter-pattern "ERROR" \
  --region us-east-1

# Get successful sends
aws logs filter-log-events \
  --log-group-name /aws/lambda/SendInviteEmailFunction \
  --start-time $(date -u -v-1H +%s)000 \
  --filter-pattern "Email sent successfully" \
  --region us-east-1
```

---

## Phase 7: Update Frontend (If Needed)

**Time:** 5 minutes  
**Prerequisites:** Backend working correctly

### Step 7.1: Check Frontend API Endpoint

```bash
# Navigate to frontend
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Documents\ -\ Mac/AI/Virtual-Legacy/Virtual-Legacy-MVP-1/FrontEndCode

# Search for invite API calls
grep -r "invites/send" src/
grep -r "SendInviteEmail" src/
```

### Step 7.2: Verify Frontend Configuration

```bash
# Check if API endpoint is hardcoded or from config
cat src/aws-config.ts | grep -i api
cat src/aws-exports.js | grep -i api
```

**If API endpoint is hardcoded, update it:**
```bash
# Find and replace (if needed)
find src/ -type f -name "*.tsx" -o -name "*.ts" | xargs grep -l "localhost.*invites"
```

---

## Troubleshooting Guide

### Issue 1: Domain Not Verified

```bash
# Check verification status
aws sesv2 get-email-identity \
  --email-identity soulreel.net \
  --region us-east-1

# If PENDING, check DNS records
dig TXT _amazonses.soulreel.net +short
dig CNAME abc123._domainkey.soulreel.net +short

# Wait for DNS propagation (can take up to 24 hours)
```

### Issue 2: Email Not Received

```bash
# Check Lambda logs for errors
aws logs tail /aws/lambda/SendInviteEmailFunction --since 10m

# Check SES sending statistics
aws sesv2 get-account --region us-east-1

# Verify email wasn't bounced
aws sesv2 list-suppressed-destinations \
  --region us-east-1 \
  --query 'SuppressedDestinationSummaries[?EmailAddress==`recipient@example.com`]'
```

### Issue 3: Email in Spam

**Check SPF/DKIM/DMARC:**
```bash
# Verify SPF
dig TXT soulreel.net +short | grep spf1

# Verify DKIM
dig CNAME abc123._domainkey.soulreel.net +short

# Verify DMARC
dig TXT _dmarc.soulreel.net +short
```

**Test email authentication:**
- Send test email to mail-tester.com
- Check score (should be 10/10)

### Issue 4: Lambda Permission Error

```bash
# Check Lambda execution role
aws lambda get-function \
  --function-name SendInviteEmailFunction \
  --region us-east-1 \
  --query 'Configuration.Role'

# Verify SES permissions
aws iam get-role-policy \
  --role-name SendInviteEmailFunction-role \
  --policy-name SendInviteEmailFunction-policy \
  --region us-east-1
```

### Issue 5: Rate Limiting

```bash
# Check sending limits
aws sesv2 get-account \
  --region us-east-1 \
  --query 'SendQuota'

# If hitting limits, request increase
aws service-quotas request-service-quota-increase \
  --service-code ses \
  --quota-code L-804C8AE8 \
  --desired-value 1000 \
  --region us-east-1
```

---

## Rollback Procedure

If something goes wrong and you need to revert:

### Quick Rollback

```bash
# Navigate to function directory
cd SamLambda/functions/inviteFunctions/sendInviteEmail

# Restore backup
cp app.py.backup app.py

# Redeploy
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Documents\ -\ Mac/AI/Virtual-Legacy/Virtual-Legacy-MVP-1/SamLambda
sam build
sam deploy

# Verify rollback
aws lambda get-function \
  --function-name SendInviteEmailFunction \
  --region us-east-1 \
  --query 'Configuration.LastModified'
```

### Keep Sandbox Mode Active

You can keep sandbox mode as a fallback:
```bash
# Verify specific test addresses (keep these working)
aws sesv2 create-email-identity \
  --email-identity legacymaker1@o447.net \
  --region us-east-1

# Test with verified address
aws lambda invoke \
  --function-name SendInviteEmailFunction \
  --payload '{"body":"{\"benefactor_email\":\"legacyBenefactor1@o447.net\",\"invitee_email\":\"legacymaker1@o447.net\"}"}' \
  --region us-east-1 \
  response.json
```

---

## Post-Deployment Checklist

### Immediate (Day 1)
- [ ] SES production access approved
- [ ] Domain verified in SES (DkimAttributes.Status = SUCCESS)
- [ ] DNS records added and propagated
- [ ] Lambda code updated with noreply@soulreel.net
- [ ] Lambda code updated with https://soulreel.net URLs
- [ ] Lambda deployed successfully
- [ ] Test email sent and received
- [ ] Email not in spam folder
- [ ] Invite link works correctly

### First Week
- [ ] Monitor bounce rate (should be < 5%)
- [ ] Monitor complaint rate (should be < 0.1%)
- [ ] Check CloudWatch logs daily
- [ ] Verify 5-10 real invites work correctly
- [ ] Confirm no emails going to spam

### Ongoing
- [ ] CloudWatch alarms configured
- [ ] SNS notifications set up (optional)
- [ ] Weekly review of SES metrics
- [ ] Monthly review of email deliverability

---

## Cost Monitoring

### Check Current Costs

```bash
# Get SES usage
aws sesv2 get-account \
  --region us-east-1 \
  --query 'SendQuota.SentLast24Hours'

# Estimate monthly cost (assuming 100 emails/month)
# SES: 100 * $0.0001 = $0.01
# Lambda: Free tier (1M requests/month)
# Total: ~$0.01/month
```

### Set Up Billing Alarm

```bash
# Create billing alarm (requires us-east-1)
aws cloudwatch put-metric-alarm \
  --alarm-name ses-monthly-cost \
  --alarm-description "Alert if SES costs exceed $1/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=ServiceName,Value=AmazonSES \
  --region us-east-1
```

---

## Summary

### What Changed
1. **Sender address:** `noreply@soulreel.net` (instead of benefactor email)
2. **Invite URLs:** `https://soulreel.net` (instead of localhost:8080)
3. **No CC/ReplyTo:** Emails are one-way notifications
4. **Production SES:** Can send to any email address (not just verified)

### What Stayed the Same
1. Lambda function logic and error handling
2. DynamoDB invite token storage
3. JWT authentication
4. API Gateway endpoint
5. 7-day invite expiration

### Key Benefits
- ✅ Professional appearance (noreply@soulreel.net)
- ✅ No recipient verification needed
- ✅ Scalable to any volume
- ✅ Extremely low cost (~$0.10 per 1,000 emails)
- ✅ No inbox to manage
- ✅ Industry-standard approach

### Next Steps
1. Run Phase 1 command to request SES production access
2. Wait for approval (24-48 hours)
3. Follow phases 2-6 in sequence
4. Monitor for first week
5. You're done!

---

## Quick Reference Commands

```bash
# Check SES status
aws sesv2 get-account --region us-east-1

# Check domain verification
aws sesv2 get-email-identity --email-identity soulreel.net --region us-east-1

# Deploy Lambda
cd SamLambda && sam build && sam deploy

# Test Lambda
aws lambda invoke --function-name SendInviteEmailFunction --payload file://test-event.json response.json

# View logs
aws logs tail /aws/lambda/SendInviteEmailFunction --follow

# Check metrics
aws cloudwatch get-metric-statistics --namespace AWS/SES --metric-name Send --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 3600 --statistics Sum
```

---

**Ready to start?** Run the first command from Phase 1 to request SES production access!
