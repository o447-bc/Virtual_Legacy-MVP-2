# 🎯 First Deployment Checklist

Use this checklist for your first deployment to AWS.

## ✅ Pre-Deployment Checklist

### Prerequisites
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Node.js and npm installed (`node --version`)
- [ ] Git initialized in project

### Verify AWS Credentials
```bash
aws sts get-caller-identity
```
Should show your AWS account ID and user.

---

## 🚀 Deployment Steps

### Step 1: Deploy Backend (5-10 minutes)

```bash
# From project root
./deploy-backend.sh
```

**Expected Output:**
- ✅ SAM build completes
- ✅ CloudFormation stack updates
- ✅ API endpoints displayed

**Save These URLs:**
- [ ] API Gateway URL: `https://________.execute-api.us-east-1.amazonaws.com/Prod`
- [ ] WebSocket URL: `wss://________.execute-api.us-east-1.amazonaws.com/prod`

**If errors occur:**
- Check AWS credentials: `aws configure list`
- Check SAM CLI: `sam --version`
- View detailed logs in CloudFormation console

---

### Step 2: Build Frontend (2-3 minutes)

```bash
# From project root
./deploy-frontend.sh
```

**Expected Output:**
- ✅ npm dependencies installed
- ✅ Vite build completes
- ✅ `dist.zip` created in FrontEndCode/

**Files Created:**
- [ ] `FrontEndCode/dist/` folder
- [ ] `FrontEndCode/dist.zip` file

---

### Step 3: Deploy Frontend to Amplify (5 minutes)

#### Option A: Amplify Console (Easiest)

1. [ ] Go to https://console.aws.amazon.com/amplify/
2. [ ] Click "New app" → "Host web app"
3. [ ] Choose "Deploy without Git provider"
4. [ ] Drag and drop `FrontEndCode/dist.zip`
5. [ ] Wait for deployment (2-3 minutes)
6. [ ] Copy your Amplify URL: `https://________.amplifyapp.com`

#### Option B: Amplify CLI

```bash
cd FrontEndCode
amplify init
amplify add hosting
amplify publish
```

---

### Step 4: Update CORS (Critical!)

1. [ ] Open `SamLambda/template.yml`
2. [ ] Find line ~18: `AllowOrigin: '''*'''`
3. [ ] Replace with your Amplify URL:
   ```yaml
   AllowOrigin: '''https://your-app-id.amplifyapp.com'''
   ```
4. [ ] Save file
5. [ ] Redeploy backend:
   ```bash
   ./deploy-backend.sh
   ```

---

### Step 5: Test Your Application

1. [ ] Open your Amplify URL in browser
2. [ ] Test user registration
3. [ ] Test user login
4. [ ] Test core features:
   - [ ] View questions
   - [ ] Record video response
   - [ ] View dashboard
   - [ ] Check relationships

**If you see CORS errors:**
- Verify CORS settings in `template.yml`
- Redeploy backend: `./deploy-backend.sh`
- Clear browser cache and reload

**If you see 401/403 errors:**
- Check Cognito configuration
- Verify user pool IDs in `aws-config.ts`

---

## 📝 Post-Deployment

### Record Your URLs

Create a file `DEPLOYMENT_INFO.txt`:
```
Deployment Date: [DATE]
Backend API: https://________.execute-api.us-east-1.amazonaws.com/Prod
WebSocket API: wss://________.execute-api.us-east-1.amazonaws.com/prod
Frontend URL: https://________.amplifyapp.com
AWS Region: us-east-1
Stack Name: Virtual-Legacy-MVP-1
```

### Set Up Monitoring

1. [ ] Go to CloudWatch Console
2. [ ] Create dashboard for your app
3. [ ] Set up alarms for:
   - [ ] Lambda errors
   - [ ] API Gateway 5xx errors
   - [ ] High costs

### Enable Logging

```bash
# View Lambda logs
cd SamLambda
sam logs --tail
```

---

## 🐛 Bug Fix Workflow

When you find a bug:

### Backend Bug
```bash
# 1. Fix the code in SamLambda/functions/
# 2. Deploy
./deploy-backend.sh
# 3. Test at your Amplify URL
```

### Frontend Bug
```bash
# 1. Fix the code in FrontEndCode/src/
# 2. Build and deploy
./deploy-frontend.sh
# 3. Upload dist.zip to Amplify Console
# 4. Test at your Amplify URL
```

---

## 💰 Cost Monitoring

### Check Current Costs
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-02-01,End=2024-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

Or visit: https://console.aws.amazon.com/billing/

### Expected Costs (Low Traffic)
- Lambda: $0-5/month (1M requests free tier)
- API Gateway: $0-5/month (1M requests free tier)
- DynamoDB: $0-5/month (25GB free tier)
- Amplify Hosting: $0 (free tier: 1000 build minutes, 15GB served)
- S3: $0-2/month
- **Total: ~$5-20/month**

---

## 🔄 Update Workflow

### Daily Development
```bash
# Make changes locally
npm run dev  # Test frontend locally
sam local start-api  # Test backend locally

# When ready to deploy
./deploy-all.sh
```

### Quick Updates
```bash
# Backend only
./deploy-backend.sh

# Frontend only
./deploy-frontend.sh
```

---

## 🆘 Troubleshooting

### Backend Issues

**Problem: SAM build fails**
```bash
# Solution: Check Python version
python3 --version  # Should be 3.12

# Reinstall dependencies
cd SamLambda/functions/yourFunction
pip install -r requirements.txt -t .
```

**Problem: Lambda timeout**
```yaml
# In template.yml, increase timeout:
Timeout: 30  # seconds
```

**Problem: Permission denied**
```bash
# Check IAM permissions in template.yml
# Ensure Lambda has access to DynamoDB, S3, etc.
```

### Frontend Issues

**Problem: Build fails**
```bash
# Clear cache and reinstall
cd FrontEndCode
rm -rf node_modules package-lock.json
npm install
npm run build
```

**Problem: CORS errors**
```yaml
# In SamLambda/template.yml:
AllowOrigin: '''https://your-amplify-url.amplifyapp.com'''
```

**Problem: API calls fail**
```typescript
// Check API endpoint in FrontEndCode/src/aws-config.ts
// Should match your API Gateway URL
```

### Amplify Issues

**Problem: Upload fails**
- Try smaller zip file
- Use Amplify CLI instead: `amplify publish`

**Problem: Old version showing**
- Clear browser cache
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

---

## 📚 Resources

- [ ] Read `DEPLOYMENT_GUIDE.md` for detailed info
- [ ] Read `QUICK_START.md` for common commands
- [ ] Read `CICD_SETUP.md` for automation

### AWS Documentation
- SAM: https://docs.aws.amazon.com/serverless-application-model/
- Amplify: https://docs.amplify.aws/
- Lambda: https://docs.aws.amazon.com/lambda/
- API Gateway: https://docs.aws.amazon.com/apigateway/

### Support
- AWS Support: https://console.aws.amazon.com/support/
- SAM GitHub: https://github.com/aws/aws-sam-cli/issues

---

## ✅ Deployment Complete!

Once all checkboxes are checked:

- [ ] Backend deployed and accessible
- [ ] Frontend deployed and accessible
- [ ] CORS configured correctly
- [ ] Application tested end-to-end
- [ ] Monitoring set up
- [ ] Deployment info recorded
- [ ] Cost monitoring enabled

**Your app is now live! 🎉**

Next steps:
1. Share your Amplify URL with users
2. Monitor logs and costs
3. Set up custom domain (optional)
4. Set up CI/CD (optional)

---

## 🔖 Quick Commands Reference

```bash
# Deploy everything
./deploy-all.sh

# Deploy backend only
./deploy-backend.sh

# Build frontend only
./deploy-frontend.sh

# View logs
cd SamLambda && sam logs --tail

# Test locally
cd SamLambda && sam local start-api
cd FrontEndCode && npm run dev

# Check costs
aws ce get-cost-and-usage --time-period Start=2024-02-01,End=2024-02-28 --granularity MONTHLY --metrics BlendedCost
```

---

**Good luck with your deployment! 🚀**
