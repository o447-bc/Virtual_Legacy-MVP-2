# Virtual Legacy - AWS Deployment Documentation

## 📖 Documentation Overview

This project includes comprehensive deployment documentation to help you deploy and maintain your Virtual Legacy application on AWS.

### 🚀 Getting Started

**New to deployment?** Start here:
1. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step checklist for your first deployment
2. **[QUICK_START.md](QUICK_START.md)** - Quick commands and common workflows

**Need detailed information?**
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive deployment guide with all details

**Want automation?**
- **[CICD_SETUP.md](CICD_SETUP.md)** - Set up automated deployments with GitHub Actions or AWS CodePipeline

---

## ⚡ Quick Deploy

### First Time Deployment

```bash
# 1. Deploy backend
./deploy-backend.sh

# 2. Build frontend
./deploy-frontend.sh

# 3. Upload FrontEndCode/dist.zip to AWS Amplify Console
# Go to: https://console.aws.amazon.com/amplify/

# 4. Update CORS in SamLambda/template.yml with your Amplify URL
# Then redeploy backend:
./deploy-backend.sh
```

### Update After Bug Fixes

```bash
# For backend changes
./deploy-backend.sh

# For frontend changes
./deploy-frontend.sh
# Then upload dist.zip to Amplify Console

# For both
./deploy-all.sh
```

---

## 📁 Project Structure

```
Virtual-Legacy-MVP-1/
├── FrontEndCode/          # React/Vite frontend
│   ├── src/               # Source code
│   ├── public/            # Static assets
│   └── package.json       # Dependencies
│
├── SamLambda/             # AWS SAM backend
│   ├── functions/         # Lambda functions
│   ├── template.yml       # Infrastructure as Code
│   └── samconfig.toml     # SAM configuration
│
├── deploy-backend.sh      # Deploy backend script
├── deploy-frontend.sh     # Build frontend script
├── deploy-all.sh          # Deploy everything script
│
└── Documentation/
    ├── DEPLOYMENT_CHECKLIST.md  # First deployment checklist
    ├── QUICK_START.md           # Quick reference
    ├── DEPLOYMENT_GUIDE.md      # Detailed guide
    └── CICD_SETUP.md            # Automation setup
```

---

## 🛠️ Technology Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Radix UI + Tailwind CSS
- **State Management**: React Query
- **Auth**: AWS Amplify
- **Hosting**: AWS Amplify Hosting

### Backend
- **Runtime**: Python 3.12
- **Framework**: AWS SAM (Serverless Application Model)
- **API**: API Gateway (REST + WebSocket)
- **Functions**: AWS Lambda
- **Database**: DynamoDB
- **Storage**: S3
- **Auth**: Cognito
- **AI/ML**: Amazon Bedrock (Claude), Amazon Polly, Amazon Transcribe

---

## 🌐 Architecture

```
User Browser
    ↓
AWS Amplify (Frontend Hosting)
    ↓
API Gateway (REST + WebSocket)
    ↓
AWS Lambda Functions
    ↓
├── DynamoDB (Database)
├── S3 (File Storage)
├── Cognito (Authentication)
├── Bedrock (AI/LLM)
├── Polly (Text-to-Speech)
└── Transcribe (Speech-to-Text)
```

---

## 💰 Estimated Costs

### Low Traffic (< 1000 users/month)
- Lambda: $0-5/month (1M requests free)
- API Gateway: $0-5/month (1M requests free)
- DynamoDB: $0-5/month (25GB free)
- Amplify Hosting: $0 (free tier)
- S3: $0-2/month
- **Total: ~$5-20/month**

### Medium Traffic (1000-10000 users/month)
- **Total: ~$50-200/month**

Monitor costs at: https://console.aws.amazon.com/billing/

---

## 🔧 Prerequisites

### Required Tools
- **AWS CLI**: `aws --version`
- **AWS SAM CLI**: `sam --version`
- **Node.js**: `node --version` (v18+)
- **npm**: `npm --version`
- **Git**: `git --version`

### AWS Account Setup
- AWS account with admin access
- AWS CLI configured: `aws configure`
- Region: `us-east-1`

### Installation

**macOS:**
```bash
# AWS CLI
brew install awscli

# SAM CLI
brew install aws-sam-cli

# Node.js
brew install node
```

**Windows:**
```powershell
# Use installers from:
# AWS CLI: https://aws.amazon.com/cli/
# SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
# Node.js: https://nodejs.org/
```

---

## 📝 Common Commands

### Deployment
```bash
./deploy-backend.sh          # Deploy backend
./deploy-frontend.sh         # Build frontend
./deploy-all.sh              # Deploy everything
```

### Local Development
```bash
# Backend
cd SamLambda
sam local start-api          # Run API locally

# Frontend
cd FrontEndCode
npm run dev                  # Run dev server
```

### Monitoring
```bash
# View logs
cd SamLambda
sam logs --tail

# View specific function
sam logs -n FunctionName --tail

# Check costs
aws ce get-cost-and-usage \
  --time-period Start=2024-02-01,End=2024-02-28 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

### Troubleshooting
```bash
# Check AWS credentials
aws sts get-caller-identity

# List deployed endpoints
cd SamLambda
sam list endpoints

# Validate SAM template
sam validate
```

---

## 🐛 Bug Fix Workflow

1. **Identify the bug** (frontend or backend)
2. **Fix the code** locally
3. **Test locally**:
   - Backend: `cd SamLambda && sam local start-api`
   - Frontend: `cd FrontEndCode && npm run dev`
4. **Deploy the fix**:
   - Backend: `./deploy-backend.sh`
   - Frontend: `./deploy-frontend.sh` + upload to Amplify
5. **Test in production** at your Amplify URL
6. **Monitor logs** for any issues

---

## 🔐 Security Best Practices

- ✅ Use Cognito for authentication (already configured)
- ✅ API Gateway with Cognito authorizer (already configured)
- ✅ DynamoDB encryption at rest (already configured)
- ✅ S3 bucket policies (already configured)
- ⚠️ Update CORS to specific domain (not `*`)
- ⚠️ Enable CloudWatch alarms
- ⚠️ Regular security audits
- ⚠️ Keep dependencies updated

---

## 📊 Monitoring & Logging

### CloudWatch Logs
```bash
# View all logs
cd SamLambda
sam logs --tail

# View specific function
sam logs -n GetNumQuestionTypesFunction --tail
```

### CloudWatch Metrics
- Go to: https://console.aws.amazon.com/cloudwatch/
- View Lambda metrics, API Gateway metrics, DynamoDB metrics

### Cost Monitoring
- Go to: https://console.aws.amazon.com/billing/
- Set up billing alerts

---

## 🚀 Next Steps

### Immediate (Required)
1. ✅ Complete first deployment using [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. ✅ Test all features end-to-end
3. ✅ Update CORS settings
4. ✅ Set up cost monitoring

### Short Term (Recommended)
1. ⚠️ Set up CloudWatch alarms
2. ⚠️ Configure custom domain
3. ⚠️ Set up automated backups
4. ⚠️ Create staging environment

### Long Term (Optional)
1. 📋 Set up CI/CD pipeline (see [CICD_SETUP.md](CICD_SETUP.md))
2. 📋 Add automated testing
3. 📋 Set up monitoring dashboard
4. 📋 Implement blue-green deployments

---

## 📚 Additional Resources

### AWS Documentation
- [AWS SAM](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Amplify](https://docs.amplify.aws/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB](https://docs.aws.amazon.com/dynamodb/)
- [Amazon Cognito](https://docs.aws.amazon.com/cognito/)

### Pricing
- [AWS Pricing Calculator](https://calculator.aws/)
- [Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [Amplify Pricing](https://aws.amazon.com/amplify/pricing/)

### Support
- [AWS Support](https://console.aws.amazon.com/support/)
- [AWS Forums](https://forums.aws.amazon.com/)

---

## 🤝 Contributing

When making changes:
1. Test locally first
2. Deploy to staging (if available)
3. Test in staging
4. Deploy to production
5. Monitor logs and metrics

---

## 📄 License

[Your License Here]

---

## 📞 Support

For deployment issues:
1. Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) troubleshooting section
2. Review CloudWatch logs
3. Check AWS Service Health Dashboard
4. Contact AWS Support

---

**Happy Deploying! 🎉**
