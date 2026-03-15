# Virtual Legacy - Deployment Steps
## Make Your App Publicly Accessible

**Date:** February 14, 2026  
**Time Required:** 30-45 minutes  
**AWS CLI Version:** v2.33.22 ✓

---

## PHASE 1: VERIFY BACKEND IS DEPLOYED

Your backend Lambda functions and API Gateway should already be deployed.

### Commands to Run:

```bash
cd SamLambda
sam list stack-outputs --stack-name Virtual-Legacy-MVP-1
```

### What You Should See:
- Stack status: CREATE_COMPLETE or UPDATE_COMPLETE
- API Gateway URL
- WebSocket URL

### Save These URLs:
```
API Gateway: https://________.execute-api.us-east-1.amazonaws.com/Prod
WebSocket:   wss://________.execute-api.us-east-1.amazonaws.com/prod
```

### If Backend Isn't Deployed:
```bash
cd SamLambda
sam build
sam deploy --guided
```

---

## PHASE 2: BUILD YOUR FRONTEND

Create the production-ready files for your React app.

### Commands to Run:

```bash
cd FrontEndCode

# Install dependencies (if needed)
npm install

# Build for production
npm run build
```

### What You Should See:
- ✓ Build completes successfully
- ✓ `dist/` folder created
- ✓ No errors in output

### Create Upload Package:

```bash
# Still in FrontEndCode directory
cd dist
zip -r ../dist.zip .
cd ..
```

### Result:
- File created: `FrontEndCode/dist.zip`
- This is what you'll upload to AWS

---

## PHASE 3: DEPLOY TO AWS AMPLIFY

Make your app publicly accessible with a URL.

### Step 3.1: Open Amplify Console

Open your browser to:
```
https://console.aws.amazon.com/amplify/
```

### Step 3.2: Create New App

1. Click **"New app"** button (top right)
2. Select **"Host web app"**
3. Choose **"Deploy without Git provider"**
4. Click **"Continue"**

### Step 3.3: Configure App

1. **App name:** `virtual-legacy` (or your choice)
2. **Environment name:** `production`
3. **Branch name:** `main` (default is fine)

### Step 3.4: Upload Your Build

1. Click **"Choose files"** or drag and drop
2. Select `FrontEndCode/dist.zip`
3. Click **"Save and deploy"**

### Step 3.5: Wait for Deployment

- Progress bar will show deployment status
- Takes 2-3 minutes
- Status will change to **"Deployed"** when ready

### Step 3.6: Get Your Public URL

**Your app is now live!**

Copy the URL shown (looks like):
```
https://[random-id].amplifyapp.com
```

**SAVE THIS URL - YOU'LL NEED IT IN PHASE 4**

---

## PHASE 4: FIX CORS (CRITICAL!)

Your backend needs to allow requests from your new Amplify URL.

### Step 4.1: Edit Backend Configuration

```bash
cd SamLambda
```

Open `template.yml` in your editor.

### Step 4.2: Find CORS Section

Look for this (around line 18):

```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: "'*'"
```

### Step 4.3: Replace with Your Amplify URL

Change it to:

```yaml
Globals:
  Api:
    Cors:
      AllowOrigin: "'https://[your-app-id].amplifyapp.com'"
```

**Replace `[your-app-id]` with your actual Amplify URL from Phase 3!**

### Step 4.4: Save and Deploy

```bash
# Still in SamLambda directory
sam build
sam deploy --no-confirm-changeset
```

This takes 2-3 minutes.

---

## PHASE 5: TEST YOUR APP

Verify everything works end-to-end.

### Step 5.1: Open Your App

Visit your Amplify URL:
```
https://[your-app-id].amplifyapp.com
```

### Step 5.2: Test These Features

- [ ] Home page loads
- [ ] Can click "Sign Up"
- [ ] Can create a new account
- [ ] Can log in
- [ ] Dashboard loads
- [ ] Can navigate between pages

### Step 5.3: Check for Errors

1. Press **F12** (or Cmd+Option+I on Mac)
2. Click **"Console"** tab
3. Look for red errors

**Good:** No CORS errors  
**Bad:** See "CORS policy" errors → Go back to Phase 4, check your URL

---

## PHASE 6: DOCUMENT YOUR DEPLOYMENT

Save your deployment information for future reference.

### Create Deployment Info File:

```bash
# From project root
cat > DEPLOYMENT_INFO.txt << EOF
===========================================
VIRTUAL LEGACY - DEPLOYMENT INFORMATION
===========================================

Deployment Date: $(date)

FRONTEND:
URL: https://[your-app-id].amplifyapp.com

BACKEND:
API Gateway: [paste your API URL]
WebSocket: [paste your WebSocket URL]
Stack Name: Virtual-Legacy-MVP-1

AWS DETAILS:
Region: us-east-1
Account: 962214556635

AMPLIFY:
App ID: [your-app-id]
Environment: production

===========================================
EOF
```

Fill in the bracketed values with your actual URLs.

### Commit Your Changes:

```bash
git add .
git commit -m "Configure for public deployment"
git push
```

---

## ✅ DEPLOYMENT COMPLETE!

Your app is now publicly accessible at:
```
https://[your-app-id].amplifyapp.com
```

---

## HOW TO PUSH UPDATES

Now that you're deployed, here's how to update your app:

### FOR FRONTEND CHANGES (UI, React Components)

When you fix a bug or add a feature in `FrontEndCode/src/`:

```bash
# 1. Test locally first
cd FrontEndCode
npm run dev
# Visit http://localhost:8080 and test

# 2. Build for production
npm run build

# 3. Create new zip
cd dist
zip -r ../dist.zip .
cd ..

# 4. Deploy to Amplify
# Go to: https://console.aws.amazon.com/amplify/
# Click your app → "Hosting" tab
# Click "Deploy updates" button
# Upload the new dist.zip
```

**OR use the script:**
```bash
./deploy-frontend.sh
# Then upload dist.zip via Amplify Console
```

### FOR BACKEND CHANGES (Lambda Functions, API)

When you modify Lambda functions in `SamLambda/`:

```bash
# 1. Test locally (optional)
cd SamLambda
sam local start-api

# 2. Deploy to AWS
sam build
sam deploy --no-confirm-changeset
```

**OR use the script:**
```bash
./deploy-backend.sh
```

### FOR BOTH FRONTEND AND BACKEND

```bash
# Deploy everything
./deploy-all.sh

# Then upload dist.zip to Amplify Console
```

---

## QUICK REFERENCE

### Check Deployment Status

```bash
# Backend status
cd SamLambda
sam list stack-outputs --stack-name Virtual-Legacy-MVP-1

# View backend logs
sam logs --stack-name Virtual-Legacy-MVP-1 --tail

# Frontend status
# Visit: https://console.aws.amazon.com/amplify/
```

### Rollback if Something Breaks

```bash
# Backend rollback
cd SamLambda
aws cloudformation cancel-update-stack --stack-name Virtual-Legacy-MVP-1

# Frontend rollback
# Go to Amplify Console → Deployments → Click previous version → Redeploy
```

### Monitor Costs

```bash
# Check current month spending
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Or visit: https://console.aws.amazon.com/billing/
```

---

## TROUBLESHOOTING

### Problem: CORS Errors in Browser Console

**Fix:**
1. Check `SamLambda/template.yml` has correct Amplify URL
2. Redeploy backend: `./deploy-backend.sh`
3. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

### Problem: Changes Not Showing

**Fix:**
1. Hard refresh: Cmd+Shift+R or Ctrl+Shift+R
2. Clear browser cache
3. Check Amplify Console shows latest deployment

### Problem: 401 Unauthorized Errors

**Fix:**
1. Log out and log back in
2. Check `FrontEndCode/src/aws-config.ts` has correct Cognito pool IDs
3. Verify user exists in Cognito console

### Problem: Build Fails

**Fix:**
```bash
cd FrontEndCode
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## ESTIMATED COSTS

With low to moderate traffic:

| Service | Cost/Month |
|---------|-----------|
| Lambda | $0-5 |
| API Gateway | $0-5 |
| DynamoDB | $0-5 |
| Amplify Hosting | $0 (free tier) |
| S3 | $0-2 |
| Cognito | $0 (50k users free) |
| **TOTAL** | **$5-20** |

---

## NEXT STEPS (OPTIONAL)

Once stable, you can:

1. **Add Custom Domain**
   - Register domain in Route 53
   - Configure in Amplify Console
   - Automatic SSL certificate

2. **Set Up Auto-Deploy**
   - Connect Amplify to GitHub
   - Auto-deploy on git push
   - See `CICD_SETUP.md`

3. **Add Monitoring**
   - CloudWatch dashboards
   - Error alerts
   - Performance metrics

---

## SUPPORT LINKS

- **Amplify Console:** https://console.aws.amazon.com/amplify/
- **CloudFormation:** https://console.aws.amazon.com/cloudformation/
- **Billing Dashboard:** https://console.aws.amazon.com/billing/
- **Cognito Console:** https://console.aws.amazon.com/cognito/

---

## YOUR DEPLOYMENT INFO

Fill this in as you complete each phase:

```
✓ Phase 1: Backend verified
  API URL: _________________________________

✓ Phase 2: Frontend built
  dist.zip created: YES / NO

✓ Phase 3: Deployed to Amplify
  Public URL: _________________________________
  App ID: _________________________________

✓ Phase 4: CORS configured
  Updated template.yml: YES / NO
  Redeployed backend: YES / NO

✓ Phase 5: Tested
  All features working: YES / NO
  No CORS errors: YES / NO

✓ Phase 6: Documented
  DEPLOYMENT_INFO.txt created: YES / NO
  Changes committed: YES / NO
```

---

**Ready to start? Begin with Phase 1!**
