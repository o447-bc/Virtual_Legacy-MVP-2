# 🚀 Quick Start: Deploy to AWS

## Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed
- Node.js and npm installed

## First Time Deployment

### 1. Deploy Backend (5 minutes)
```bash
./deploy-backend.sh
```
This deploys all Lambda functions, API Gateway, and DynamoDB tables.

### 2. Set Up Frontend Hosting

**Option A: AWS Amplify Console (Easiest)**
```bash
# Build the frontend
./deploy-frontend.sh

# Then:
# 1. Go to https://console.aws.amazon.com/amplify/
# 2. Click "New app" → "Host web app"
# 3. Choose "Deploy without Git provider"
# 4. Upload the FrontEndCode/dist.zip file
# 5. You'll get a URL like: https://xxxxx.amplifyapp.com
```

**Option B: AWS Amplify CLI (Automated)**
```bash
# One-time setup
npm install -g @aws-amplify/cli
cd FrontEndCode
amplify init
amplify add hosting
# Choose: "Hosting with Amplify Console"
# Choose: "Manual deployment"

# Deploy
amplify publish
```

### 3. Update CORS (Important!)
After getting your Amplify URL, update CORS:

1. Edit `SamLambda/template.yml`
2. Find the `Globals` section
3. Update `AllowOrigin` from `'*'` to your Amplify URL:
   ```yaml
   AllowOrigin: "'https://your-app-id.amplifyapp.com'"
   ```
4. Redeploy backend:
   ```bash
   ./deploy-backend.sh
   ```

---

## Updating Your App (After Bugs/Changes)

### Backend Changes Only
```bash
./deploy-backend.sh
```
Takes ~2-3 minutes. Updates Lambda functions and APIs.

### Frontend Changes Only
```bash
./deploy-frontend.sh
# Then upload dist.zip to Amplify Console
# OR run: cd FrontEndCode && amplify publish
```
Takes ~1-2 minutes.

### Both Backend & Frontend
```bash
./deploy-all.sh
# Then upload dist.zip to Amplify Console
```

---

## Common Workflows

### Fix a Bug in Lambda Function
```bash
# 1. Edit the Lambda function code in SamLambda/functions/
# 2. Deploy
./deploy-backend.sh
# Done! Changes are live in ~2 minutes
```

### Fix a Bug in React Frontend
```bash
# 1. Edit the React code in FrontEndCode/src/
# 2. Build and deploy
./deploy-frontend.sh
# 3. Upload dist.zip to Amplify Console
# Done! Changes are live in ~1 minute
```

### Add a New Lambda Function
```bash
# 1. Add function code in SamLambda/functions/
# 2. Add function definition in SamLambda/template.yml
# 3. Deploy
./deploy-backend.sh
```

---

## Viewing Logs

### Backend Logs (Lambda)
```bash
cd SamLambda

# View specific function logs
sam logs -n GetNumQuestionTypesFunction --tail

# View all logs
sam logs --tail
```

### Frontend Logs
- Go to [Amplify Console](https://console.aws.amazon.com/amplify/)
- Select your app
- Click "Hosting" → "Deployments"

---

## Testing Locally Before Deployment

### Test Backend Locally
```bash
cd SamLambda
sam local start-api
# API runs at http://localhost:3000
```

### Test Frontend Locally
```bash
cd FrontEndCode
npm run dev
# App runs at http://localhost:8080
```

---

## Rollback (If Something Breaks)

### Rollback Backend
```bash
cd SamLambda
# View previous versions
aws cloudformation describe-stack-events --stack-name Virtual-Legacy-MVP-1

# Rollback to previous version
aws cloudformation cancel-update-stack --stack-name Virtual-Legacy-MVP-1
```

### Rollback Frontend
- Go to Amplify Console
- Click "Hosting" → "Deployments"
- Find previous successful deployment
- Click "Redeploy this version"

---

## Cost Monitoring

Check your AWS costs:
```bash
# View current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-02-01,End=2024-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

Or visit: https://console.aws.amazon.com/billing/

---

## Getting Your API URLs

```bash
cd SamLambda
sam list endpoints
```

Or check AWS Console:
- API Gateway: https://console.aws.amazon.com/apigateway/
- Lambda: https://console.aws.amazon.com/lambda/

---

## Troubleshooting

### "sam: command not found"
Install AWS SAM CLI:
```bash
brew install aws-sam-cli  # macOS
```

### "amplify: command not found"
Install Amplify CLI:
```bash
npm install -g @aws-amplify/cli
```

### CORS Errors in Browser
Update `AllowOrigin` in `SamLambda/template.yml` to your Amplify URL, then:
```bash
./deploy-backend.sh
```

### Lambda Function Timeout
Increase timeout in `template.yml`:
```yaml
Timeout: 30  # seconds
```

---

## Next Steps

1. ✅ Deploy backend: `./deploy-backend.sh`
2. ✅ Deploy frontend: `./deploy-frontend.sh` + upload to Amplify
3. ✅ Update CORS in template.yml
4. ✅ Test your app at your Amplify URL
5. ✅ Set up custom domain (optional)
6. ✅ Set up CloudWatch alarms (optional)

---

## Support

- Full guide: See `DEPLOYMENT_GUIDE.md`
- AWS SAM: https://docs.aws.amazon.com/serverless-application-model/
- Amplify: https://docs.amplify.aws/
