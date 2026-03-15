# Development & Deployment Workflow
## SoulReel.net - Frontend & Backend Changes

**Last Updated:** February 14, 2026

---

## Overview

You have two environments:
1. **Development (Local)** - Your laptop, for testing changes
2. **Production (AWS)** - Live at https://soulreel.net

---

## FRONTEND WORKFLOW

### Development (Local Testing)

**1. Make Your Changes**
```bash
# Edit files in FrontEndCode/src/
# Example: FrontEndCode/src/pages/Dashboard.tsx
```

**2. Run Local Dev Server**
```bash
cd FrontEndCode
npm run dev
```

**3. Test Locally**
- Opens at: http://localhost:8080
- Hot reload enabled (changes appear instantly)
- Uses your PRODUCTION backend API
- Test all your changes thoroughly

**4. Stop Dev Server**
- Press `Ctrl+C` in terminal

---

### Deploy to Production

**Option A: Quick Deploy (Recommended)**

```bash
# From project root
./deploy-frontend.sh
```

This creates `FrontEndCode/dist.zip`

Then:
1. Go to: https://console.aws.amazon.com/amplify/
2. Click your app: `virtual-legacy`
3. Click "Hosting" tab
4. Click "Deploy updates"
5. Upload `dist.zip`
6. Wait 2-3 minutes
7. Visit https://soulreel.net to see changes

**Option B: Manual Steps**

```bash
cd FrontEndCode

# Build for production
npm run build

# Create zip
cd dist
zip -r ../dist.zip .
cd ..

# Upload dist.zip via Amplify Console (same as above)
```

**Timeline:** 5-10 minutes total

---

## BACKEND WORKFLOW

### Development (Local Testing)

**1. Make Your Changes**
```bash
# Edit files in SamLambda/functions/
# Example: SamLambda/functions/videoFunctions/uploadVideoResponse/app.py
```

**2. Test Locally (Optional)**
```bash
cd SamLambda

# Start local API
sam local start-api

# API runs at: http://127.0.0.1:3000
# Test with curl or Postman
```

**Note:** Local backend testing is optional. Most developers test directly in production since Lambda is cheap and fast to deploy.

---

### Deploy to Production

**Quick Deploy:**

```bash
# From project root
./deploy-backend.sh
```

**Manual Steps:**

```bash
cd SamLambda

# Build Lambda functions
sam build

# Deploy to AWS
sam deploy --no-confirm-changeset
```

**Timeline:** 2-3 minutes

**What Happens:**
- Lambda functions updated
- API Gateway updated
- Changes live immediately at your API endpoint

---

## FULL STACK CHANGES

When you change both frontend and backend:

```bash
# From project root
./deploy-all.sh
```

Then upload `dist.zip` to Amplify Console.

---

## TYPICAL DEVELOPMENT SCENARIOS

### Scenario 1: Fix a UI Bug

```bash
# 1. Edit the component
vim FrontEndCode/src/components/VideoRecorder.tsx

# 2. Test locally
cd FrontEndCode
npm run dev
# Visit http://localhost:8080 and test

# 3. Deploy to production
cd ..
./deploy-frontend.sh
# Upload dist.zip to Amplify Console

# 4. Verify at https://soulreel.net
```

---

### Scenario 2: Add a New API Endpoint

```bash
# 1. Edit Lambda function
vim SamLambda/functions/videoFunctions/newFunction/app.py

# 2. Update template.yml to add the new endpoint
vim SamLambda/template.yml

# 3. Deploy backend
./deploy-backend.sh

# 4. Test the new endpoint
curl https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod/new-endpoint

# 5. Update frontend to use new endpoint
vim FrontEndCode/src/services/videoService.ts

# 6. Deploy frontend
./deploy-frontend.sh
# Upload dist.zip to Amplify Console
```

---

### Scenario 3: Change Database Schema

```bash
# 1. Update DynamoDB table (via AWS Console or CLI)
aws dynamodb update-table ...

# 2. Update Lambda functions to use new schema
vim SamLambda/functions/*/app.py

# 3. Deploy backend
./deploy-backend.sh

# 4. Update frontend if needed
vim FrontEndCode/src/services/*.ts

# 5. Deploy frontend
./deploy-frontend.sh
# Upload dist.zip to Amplify Console
```

---

## ENVIRONMENT VARIABLES

### Frontend Environment Variables

**Local Development:**
- Edit: `FrontEndCode/.env`
- Prefix with `VITE_`
- Example: `VITE_API_URL=http://localhost:3000`

**Production:**
Currently hardcoded in `FrontEndCode/src/config/api.ts`

**To Use Environment Variables:**

1. Create `FrontEndCode/.env.production`:
```env
VITE_API_URL=https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod
VITE_WS_URL=wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod
```

2. Update code to use:
```typescript
const API_URL = import.meta.env.VITE_API_URL;
```

3. Rebuild and deploy

---

### Backend Environment Variables

**Set in template.yml:**

```yaml
Environment:
  Variables:
    TABLE_NAME: !Ref MyDynamoDBTable
    BUCKET_NAME: !Ref MyS3Bucket
```

**Access in Lambda:**
```python
import os
table_name = os.environ['TABLE_NAME']
```

---

## TESTING CHECKLIST

### Before Deploying to Production:

**Frontend:**
- [ ] Runs locally without errors (`npm run dev`)
- [ ] No console errors in browser (F12)
- [ ] All features work as expected
- [ ] Mobile responsive (test in browser dev tools)
- [ ] Build succeeds (`npm run build`)

**Backend:**
- [ ] Code passes linting
- [ ] Lambda functions have proper error handling
- [ ] IAM permissions are correct in template.yml
- [ ] API endpoints return expected responses
- [ ] Database operations work correctly

---

## ROLLBACK PROCEDURES

### Rollback Frontend

**Via Amplify Console:**
1. Go to: https://console.aws.amazon.com/amplify/
2. Click your app → "Hosting"
3. Find previous successful deployment
4. Click "Redeploy this version"

**Timeline:** 2-3 minutes

---

### Rollback Backend

**Via CloudFormation:**
```bash
aws cloudformation cancel-update-stack \
  --stack-name Virtual-Legacy-MVP-1
```

Or redeploy previous version:
```bash
cd SamLambda
git checkout <previous-commit>
sam build && sam deploy --no-confirm-changeset
```

---

## MONITORING & DEBUGGING

### Frontend Errors

**Check Browser Console:**
- Press F12
- Look for red errors
- Check Network tab for failed API calls

**Check Amplify Logs:**
1. Go to Amplify Console
2. Click your app → "Hosting"
3. View deployment logs

---

### Backend Errors

**View Lambda Logs:**
```bash
cd SamLambda

# View logs for specific function
sam logs -n UploadVideoResponseFunction --tail

# View all logs
sam logs --stack-name Virtual-Legacy-MVP-1 --tail
```

**Via CloudWatch Console:**
1. Go to: https://console.aws.amazon.com/cloudwatch/
2. Click "Log groups"
3. Find `/aws/lambda/Virtual-Legacy-MVP-1-*`
4. View recent logs

---

## BEST PRACTICES

### Development:
1. **Always test locally first** before deploying
2. **Make small, incremental changes** - easier to debug
3. **Test on multiple browsers** (Chrome, Safari, Firefox)
4. **Test on mobile** devices or browser dev tools
5. **Check browser console** for errors before deploying

### Deployment:
1. **Deploy backend first**, then frontend (if both changed)
2. **Test immediately** after deployment
3. **Keep deployment scripts** (`deploy-*.sh`) up to date
4. **Document changes** in git commits
5. **Monitor costs** in AWS Billing Dashboard

### Git Workflow:
```bash
# Before making changes
git checkout -b feature/new-feature

# Make changes, test locally
# ...

# Commit changes
git add .
git commit -m "Add new feature: description"

# Deploy to production
./deploy-all.sh
# Upload to Amplify

# Merge to main
git checkout main
git merge feature/new-feature
git push
```

---

## QUICK REFERENCE

### Frontend Commands
```bash
npm run dev          # Start local dev server
npm run build        # Build for production
npm run lint         # Check for code issues
```

### Backend Commands
```bash
sam build            # Build Lambda functions
sam deploy           # Deploy to AWS
sam local start-api  # Run API locally
sam logs --tail      # View live logs
```

### Deployment Scripts
```bash
./deploy-frontend.sh # Build frontend
./deploy-backend.sh  # Deploy backend
./deploy-all.sh      # Deploy both
```

---

## COMMON ISSUES & SOLUTIONS

### Issue: "CORS Error" in Browser

**Solution:**
1. Check `SamLambda/template.yml` has correct domain
2. Redeploy backend: `./deploy-backend.sh`
3. Clear browser cache (Cmd+Shift+R)

---

### Issue: "Changes Not Showing" on Production

**Solution:**
1. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
2. Clear browser cache
3. Check Amplify deployment succeeded
4. Verify you uploaded latest dist.zip

---

### Issue: "API Returns 500 Error"

**Solution:**
1. Check Lambda logs: `sam logs --tail`
2. Look for Python errors
3. Check IAM permissions in template.yml
4. Verify environment variables are set

---

### Issue: "Build Fails"

**Frontend:**
```bash
cd FrontEndCode
rm -rf node_modules package-lock.json
npm install
npm run build
```

**Backend:**
```bash
cd SamLambda
sam build --use-container
```

---

## COST MONITORING

### Check Current Costs
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

Or visit: https://console.aws.amazon.com/billing/

### Expected Monthly Costs:
- Domain: $1/month
- Lambda: $0-5/month (1M requests free)
- API Gateway: $0-5/month
- Amplify: $0 (free tier)
- DynamoDB: $0-5/month
- S3: $0-2/month
- **Total: ~$5-15/month**

---

## SUMMARY

**Development Cycle:**
1. Make changes locally
2. Test with `npm run dev` (frontend) or `sam local start-api` (backend)
3. Deploy with deployment scripts
4. Upload to Amplify (frontend only)
5. Test on production (https://soulreel.net)
6. Monitor logs if issues arise

**Key Points:**
- Frontend changes require Amplify upload
- Backend changes deploy directly via SAM
- Always test locally before deploying
- Production deploys are fast (2-10 minutes)
- Rollback is easy if needed

---

**You're all set! Happy coding! 🚀**
