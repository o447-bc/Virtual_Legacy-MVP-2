# Public Deployment Plan
## Making Virtual Legacy Publicly Accessible on AWS

**Created:** February 14, 2026  
**Status:** Ready to Execute  
**Estimated Time:** 30-45 minutes

---

## OVERVIEW

This plan will make your Virtual Legacy app publicly accessible using AWS services with a default AWS domain. You'll also establish a workflow for pushing bug fixes and feature updates.

### What You'll Get

- **Public Frontend URL:** `https://[app-id].amplifyapp.com`
- **Backend API:** Already deployed via SAM
- **Update Workflow:** Simple commands to push changes
- **No Custom Domain:** Using AWS default URLs (can add later)

---

## PREREQUISITES CHECKLIST

Before starting, verify you have:

- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Node.js and npm installed
- [ ] Your AWS credentials are working (`aws sts get-caller-identity`)
- [ ] You're in the project root directory

---

## PHASE 1: VERIFY BACKEND DEPLOYMENT

Your backend should already be deployed. Let's verify:

### Step 1.1: Check Backend Status

```bash
cd SamLambda
sam list stack-outputs --stack-name Virtual-Legacy-MVP-1
```

**Expected Output:**
- API Gateway URL
- WebSocket URL
- Stack status: CREATE_COMPLETE or UPDATE_COMPLETE

### Step 1.2: Test Backend (Optional)

```bash
# View recent logs
sam logs --stack-name Virtual-Legacy-MVP-1 --tail
```

### Step 1.3: Note Your API URLs

Save these for later:
- **API Gateway URL:** `https://________.execute-api.us-east-1.amazonaws.com/Prod`
- **WebSocket URL:** `wss://________.execute-api.us-east-1.amazonaws.com/prod`

**If backend isn't deployed:**
```bash
cd SamLambda
sam build
sam deploy --guided
```

---

## PHASE 2: PREPARE FRONTEND FOR DEPLOYMENT

### Step 2.1: Verify Environment Configuration

Check that your frontend has the correct API endpoints:

```bash
# Check current API configuration
cat FrontEndCode/src/config/api.ts
```

**Verify it points to your deployed API Gateway URL.**

### Step 2.2: Build Frontend

```bash
cd FrontEndCode

# Install dependencies (if needed)
npm install

# Build for production
npm run build
```

**Expected Output:**
- Build completes successfully
- `dist/` folder created with production files
- No errors in console

### Step 2.3: Create Deployment Package

```bash
# Create zip file for Amplify upload
cd dist
zip -r ../dist.zip .
cd ..
```

**Result:** `FrontEndCode/dist.zip` ready for upload

---

## PHASE 3: DEPLOY TO AWS AMPLIFY HOSTING

### Option A: Amplify Console (Recommended - Easiest)

#### Step 3A.1: Access Amplify Console

1. Open browser to: https://console.aws.amazon.com/amplify/
2. Click **"New app"** → **"Host web app"**
3. Choose **"Deploy without Git provider"**

#### Step 3A.2: Upload Your App

1. **App name:** `virtual-legacy` (or your choice)
2. **Environment name:** `production`
3. **Drag and drop** `FrontEndCode/dist.zip` OR click to browse
4. Click **"Save and deploy"**

#### Step 3A.3: Wait for Deployment

- Deployment takes 2-3 minutes
- Watch the progress bar
- Status will change to "Deployed"

#### Step 3A.4: Get Your Public URL

**Your app is now live at:**
```
https://[app-id].amplifyapp.com
```

**Save this URL!** You'll need it for CORS configuration.

### Option B: Amplify CLI (Alternative)

```bash
# Install Amplify CLI (one-time)
npm install -g @aws-amplify/cli

# Initialize Amplify
cd FrontEndCode
amplify init

# Add hosting
amplify add hosting
# Choose: "Hosting with Amplify Console"
# Choose: "Manual deployment"

# Publish
amplify publish
```

---

## PHASE 4: CONFIGURE CORS (CRITICAL!)

Your backend needs to allow requests from your new Amplify URL.

### Step 4.1: Update Backend CORS

```bash
# Open template.yml
cd SamLambda
# Edit template.yml
```

**Find this section (around line 18):**
```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: "'*'"
```

**Replace with your Amplify URL:**
```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: "'https://[your-app-id].amplifyapp.com'"
```

### Step 4.2: Redeploy Backend

```bash
sam build
sam deploy --no-confirm-changeset
```

**This takes 2-3 minutes.**

---

## PHASE 5: TEST YOUR PUBLIC APP

### Step 5.1: Open Your App

Visit: `https://[your-app-id].amplifyapp.com`

### Step 5.2: Test Core Functionality

- [ ] Home page loads
- [ ] Can navigate to signup
- [ ] Can create account
- [ ] Can login
- [ ] Can view dashboard
- [ ] Can record video (if applicable)
- [ ] No CORS errors in browser console (F12)

### Step 5.3: Check Browser Console

Press F12 → Console tab

**Good:** No red errors
**Bad:** CORS errors → Go back to Phase 4

---

## PHASE 6: DOCUMENT YOUR DEPLOYMENT

### Step 6.1: Create Deployment Info File

```bash
# From project root
cat > DEPLOYMENT_INFO.txt << EOF
Deployment Date: $(date)
Frontend URL: https://[your-app-id].amplifyapp.com
Backend API: [your-api-gateway-url]
WebSocket API: [your-websocket-url]
AWS Region: us-east-1
Stack Name: Virtual-Legacy-MVP-1
Amplify App ID: [your-app-id]
EOF
```

### Step 6.2: Commit Deployment Changes

```bash
git add .
git commit -m "Configure for public deployment"
git push
```

---

## UPDATE WORKFLOW: PUSHING CHANGES

Now that you're deployed, here's how to push updates:

### For Frontend Changes (UI, Components, Pages)

```bash
# 1. Make your changes in FrontEndCode/src/

# 2. Test locally
cd FrontEndCode
npm run dev
# Test at http://localhost:8080

# 3. Build for production
npm run build

# 4. Deploy to Amplify
cd dist
zip -r ../dist.zip .
cd ..

# 5. Upload to Amplify Console
# Go to: https://console.aws.amazon.com/amplify/
# Select your app → "Hosting" → "Deploy updates"
# Upload new dist.zip
```

**OR use the script:**
```bash
./deploy-frontend.sh
# Then upload dist.zip via Amplify Console
```

### For Backend Changes (Lambda, API, Database)

```bash
# 1. Make your changes in SamLambda/

# 2. Test locally (optional)
cd SamLambda
sam local start-api

# 3. Deploy
sam build
sam deploy --no-confirm-changeset
```

**OR use the script:**
```bash
./deploy-backend.sh
```

### For Full Stack Changes

```bash
# Deploy everything at once
./deploy-all.sh

# Then upload dist.zip to Amplify Console
```

---

## QUICK REFERENCE COMMANDS

### Check What's Deployed

```bash
# Backend status
cd SamLambda
sam list stack-outputs --stack-name Virtual-Legacy-MVP-1

# View backend logs
sam logs --stack-name Virtual-Legacy-MVP-1 --tail

# Frontend status
# Visit Amplify Console: https://console.aws.amazon.com/amplify/
```

### Deploy Updates

```bash
# Backend only
./deploy-backend.sh

# Frontend only
./deploy-frontend.sh
# Then upload to Amplify Console

# Both
./deploy-all.sh
# Then upload to Amplify Console
```

### Rollback

```bash
# Backend rollback
cd SamLambda
aws cloudformation cancel-update-stack --stack-name Virtual-Legacy-MVP-1

# Frontend rollback
# Go to Amplify Console → Select previous deployment
```

---

## COST ESTIMATE

With low to moderate traffic:

| Service | Monthly Cost |
|---------|-------------|
| Lambda | $0-5 (1M requests free) |
| API Gateway | $0-5 (1M requests free) |
| DynamoDB | $0-5 (25GB free) |
| Amplify Hosting | $0 (free tier) |
| S3 Storage | $0-2 |
| Cognito | $0 (50k MAU free) |
| **Total** | **$5-20/month** |

### Monitor Costs

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

Or visit: https://console.aws.amazon.com/billing/

---

## TROUBLESHOOTING

### Problem: CORS Errors

**Symptoms:** Browser console shows "CORS policy" errors

**Solution:**
1. Verify CORS in `SamLambda/template.yml` has your Amplify URL
2. Redeploy backend: `./deploy-backend.sh`
3. Clear browser cache (Cmd+Shift+R)

### Problem: 401 Unauthorized

**Symptoms:** API calls return 401 errors

**Solution:**
1. Check Cognito configuration in `FrontEndCode/src/aws-config.ts`
2. Verify user pool IDs match your deployment
3. Try logging out and back in

### Problem: Old Version Showing

**Symptoms:** Changes not visible after deployment

**Solution:**
1. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)
2. Clear browser cache
3. Check Amplify Console deployment status
4. Verify you uploaded the latest dist.zip

### Problem: Build Fails

**Symptoms:** `npm run build` fails

**Solution:**
```bash
cd FrontEndCode
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Problem: Upload Fails

**Symptoms:** Amplify upload times out or fails

**Solution:**
1. Check zip file size (should be < 100MB)
2. Try Amplify CLI instead: `amplify publish`
3. Check AWS credentials: `aws sts get-caller-identity`

---

## NEXT STEPS (OPTIONAL)

Once your app is live and stable:

### 1. Set Up Automated Deployment

Connect Amplify to your Git repository for automatic deployments on push.

**See:** `CICD_SETUP.md` for details

### 2. Add Custom Domain

Register a domain and configure it in Amplify.

**Steps:**
1. Register domain in Route 53 (or use existing)
2. Amplify Console → Domain management → Add domain
3. Amplify handles SSL certificate automatically

### 3. Set Up Monitoring

Create CloudWatch dashboards and alarms:

```bash
# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### 4. Enable Logging

Set up structured logging for better debugging:
- CloudWatch Logs for Lambda
- Amplify deployment logs
- API Gateway access logs

---

## SUCCESS CHECKLIST

- [ ] Backend deployed and accessible
- [ ] Frontend built successfully
- [ ] Frontend deployed to Amplify
- [ ] Public URL obtained and saved
- [ ] CORS configured with Amplify URL
- [ ] Backend redeployed with CORS
- [ ] App tested end-to-end
- [ ] No CORS errors in browser
- [ ] Deployment info documented
- [ ] Update workflow understood
- [ ] Costs being monitored

---

## SUPPORT RESOURCES

- **AWS Amplify Console:** https://console.aws.amazon.com/amplify/
- **CloudFormation Console:** https://console.aws.amazon.com/cloudformation/
- **Billing Dashboard:** https://console.aws.amazon.com/billing/
- **SAM Documentation:** https://docs.aws.amazon.com/serverless-application-model/
- **Amplify Documentation:** https://docs.amplify.aws/

---

## YOUR DEPLOYMENT URLS

Fill these in after deployment:

```
Frontend URL: https://________________________.amplifyapp.com
Backend API:  https://________________________.execute-api.us-east-1.amazonaws.com/Prod
WebSocket:    wss://________________________.execute-api.us-east-1.amazonaws.com/prod
Amplify App ID: ________________________
Deployment Date: ________________________
```

---

**You're ready to deploy! Start with Phase 1 and work through each phase in order.**
