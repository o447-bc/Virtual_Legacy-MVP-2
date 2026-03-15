# CI/CD Setup Guide (Optional)

This guide helps you set up automated deployments so you can push code and have it automatically deploy to AWS.

## Option 1: GitHub Actions (Recommended)

### Setup Steps

1. **Create GitHub Repository** (if not already done)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/virtual-legacy.git
   git push -u origin main
   ```

2. **Add AWS Credentials to GitHub Secrets**
   - Go to your GitHub repo → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `AWS_REGION` (value: `us-east-1`)

3. **Create GitHub Actions Workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Setup SAM CLI
        uses: aws-actions/setup-sam@v2
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Build and Deploy Backend
        run: |
          cd SamLambda
          sam build
          sam deploy --no-confirm-changeset --no-fail-on-empty-changeset

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: FrontEndCode/package-lock.json
      
      - name: Install Dependencies
        run: |
          cd FrontEndCode
          npm ci
      
      - name: Build Frontend
        run: |
          cd FrontEndCode
          npm run build
      
      - name: Deploy to Amplify
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Upload to Amplify
        run: |
          cd FrontEndCode/dist
          zip -r ../dist.zip .
          # You'll need to set up Amplify CLI or use manual upload
          echo "Upload dist.zip to Amplify Console"
```

4. **Push to GitHub**
   ```bash
   git add .github/workflows/deploy.yml
   git commit -m "Add CI/CD workflow"
   git push
   ```

Now every push to `main` will automatically deploy!

---

## Option 2: AWS CodePipeline

### Setup Steps

1. **Create CodeCommit Repository**
   ```bash
   aws codecommit create-repository --repository-name virtual-legacy
   ```

2. **Create buildspec.yml for Backend**

Create `SamLambda/buildspec.yml`:

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.12
    commands:
      - pip install aws-sam-cli
  
  build:
    commands:
      - sam build
      - sam deploy --no-confirm-changeset --no-fail-on-empty-changeset

artifacts:
  files:
    - '**/*'
```

3. **Create buildspec.yml for Frontend**

Create `FrontEndCode/buildspec.yml`:

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
    commands:
      - npm install -g @aws-amplify/cli
  
  pre_build:
    commands:
      - cd FrontEndCode
      - npm ci
  
  build:
    commands:
      - npm run build
  
  post_build:
    commands:
      - cd dist
      - zip -r ../dist.zip .

artifacts:
  files:
    - FrontEndCode/dist/**/*
```

4. **Create CodePipeline**
   - Go to AWS CodePipeline Console
   - Create new pipeline
   - Connect to CodeCommit repository
   - Add build stage with CodeBuild
   - Add deploy stage

---

## Option 3: Simple Git Hooks (Local Automation)

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash

echo "🔍 Running pre-push checks..."

# Run tests if you have them
# cd FrontEndCode && npm test

# Optionally auto-deploy
read -p "Deploy to AWS? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    ./deploy-all.sh
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-push
```

---

## Option 4: Amplify Git-Based Deployment

### Setup Steps

1. **Connect Amplify to Git**
   - Go to [Amplify Console](https://console.aws.amazon.com/amplify/)
   - Click "New app" → "Host web app"
   - Choose "GitHub" (or GitLab, Bitbucket)
   - Authorize and select your repository
   - Select branch: `main`

2. **Configure Build Settings**

Amplify will auto-detect your build settings. Verify:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd FrontEndCode
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: FrontEndCode/dist
    files:
      - '**/*'
  cache:
    paths:
      - FrontEndCode/node_modules/**/*
```

3. **Enable Auto-Deploy**
   - Every push to `main` will automatically build and deploy
   - You'll get preview URLs for pull requests

---

## Deployment Strategies

### Strategy 1: Manual (Current)
- You run `./deploy-backend.sh` and `./deploy-frontend.sh`
- Full control, good for learning
- Best for: Small teams, infrequent updates

### Strategy 2: Semi-Automated
- Backend: Manual (`./deploy-backend.sh`)
- Frontend: Auto-deploy via Amplify Git integration
- Best for: Frequent frontend changes, stable backend

### Strategy 3: Fully Automated
- Both backend and frontend auto-deploy on git push
- Uses GitHub Actions or CodePipeline
- Best for: Production apps, frequent updates

### Strategy 4: Staged Deployment
- Dev branch → Dev environment
- Main branch → Production environment
- Best for: Teams, testing before production

---

## Recommended Workflow for Your Use Case

Since you mentioned finding bugs and pushing updates easily:

**Phase 1 (Now): Manual Deployment**
```bash
# Fix bug in code
git add .
git commit -m "Fix: description"
git push

# Deploy manually
./deploy-all.sh
```

**Phase 2 (Later): Semi-Automated**
- Set up Amplify Git integration for frontend
- Keep backend manual for now
```bash
# Fix bug in frontend
git push  # Auto-deploys frontend

# Fix bug in backend
./deploy-backend.sh
```

**Phase 3 (Future): Fully Automated**
- Set up GitHub Actions
- All deployments automatic on push

---

## Testing Before Deployment

### Add Pre-Deployment Tests

Create `test-before-deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Running tests..."

# Backend tests
cd SamLambda
# Add your backend tests here
# python -m pytest tests/

# Frontend tests
cd ../FrontEndCode
npm run lint
# npm test

echo "✅ All tests passed!"
```

Update deployment scripts to run tests first:
```bash
./test-before-deploy.sh && ./deploy-all.sh
```

---

## Monitoring Deployments

### CloudWatch Alarms

Create alarms for:
- Lambda errors
- API Gateway 5xx errors
- High latency

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### Deployment Notifications

Set up SNS topic for deployment notifications:
```bash
aws sns create-topic --name deployment-notifications
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:xxx:deployment-notifications \
  --protocol email --notification-endpoint your-email@example.com
```

---

## Rollback Automation

Create `rollback.sh`:

```bash
#!/bin/bash

echo "🔄 Rolling back deployment..."

# Rollback backend
cd SamLambda
aws cloudformation cancel-update-stack --stack-name Virtual-Legacy-MVP-1

# Rollback frontend (manual in Amplify Console)
echo "Go to Amplify Console to rollback frontend"
```

---

## Best Practices

1. **Always test locally first**
   ```bash
   cd SamLambda && sam local start-api
   cd FrontEndCode && npm run dev
   ```

2. **Use git tags for releases**
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

3. **Keep deployment logs**
   ```bash
   ./deploy-all.sh 2>&1 | tee deployment-$(date +%Y%m%d-%H%M%S).log
   ```

4. **Monitor costs after each deployment**
   ```bash
   aws ce get-cost-and-usage --time-period Start=2024-02-01,End=2024-02-28 \
     --granularity DAILY --metrics BlendedCost
   ```

---

## Quick Reference

```bash
# Manual deployment (current)
./deploy-all.sh

# With GitHub Actions (future)
git push  # Automatically deploys

# Rollback
./rollback.sh

# View deployment status
aws cloudformation describe-stacks --stack-name Virtual-Legacy-MVP-1
```

---

## Next Steps

1. Start with manual deployment (current scripts)
2. Once comfortable, set up Amplify Git integration for frontend
3. Later, add GitHub Actions for full automation
4. Set up monitoring and alerts
5. Add automated tests

Choose the level of automation that fits your workflow!
