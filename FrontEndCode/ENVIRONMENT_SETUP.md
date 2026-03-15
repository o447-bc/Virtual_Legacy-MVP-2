# Environment Variables Setup Guide

## Overview

This project uses environment variables to manage configuration for different environments (development, staging, production). This approach keeps sensitive credentials out of source control and allows easy configuration changes without code modifications.

## Quick Start

### 1. Copy the Environment Template

```bash
cd FrontEndCode
cp .env.example .env
```

### 2. Fill in Your Values

Edit `.env` and replace the placeholder values with your actual AWS credentials:

```bash
# API Configuration
VITE_API_BASE_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod

# AWS Cognito Configuration
VITE_USER_POOL_ID=us-east-1_YourPoolId
VITE_USER_POOL_CLIENT_ID=your-client-id-here
VITE_IDENTITY_POOL_ID=us-east-1:your-identity-pool-id
VITE_AWS_REGION=us-east-1

# AWS S3 Configuration
VITE_S3_BUCKET=your-bucket-name
```

### 3. Run the Application

```bash
npm install
npm run dev
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | API Gateway base URL | `https://abc123.execute-api.us-east-1.amazonaws.com/Prod` |
| `VITE_USER_POOL_ID` | Cognito User Pool ID | `us-east-1_ABC123XYZ` |
| `VITE_USER_POOL_CLIENT_ID` | Cognito App Client ID | `1a2b3c4d5e6f7g8h9i0j` |
| `VITE_IDENTITY_POOL_ID` | Cognito Identity Pool ID | `us-east-1:12345678-1234-1234-1234-123456789012` |
| `VITE_AWS_REGION` | AWS Region | `us-east-1` |
| `VITE_S3_BUCKET` | S3 Bucket Name | `virtual-legacy-user-data` |

## Finding Your AWS Values

### API Gateway URL
1. Go to AWS Console → API Gateway
2. Select your API
3. Click "Stages" → "Prod"
4. Copy the "Invoke URL"

### Cognito User Pool ID
1. Go to AWS Console → Cognito
2. Select your User Pool
3. Copy the "Pool Id" from the General Settings

### Cognito App Client ID
1. In your User Pool, go to "App integration" → "App clients"
2. Copy the "Client ID"

### Identity Pool ID
1. Go to AWS Console → Cognito → Federated Identities
2. Select your Identity Pool
3. Copy the Identity Pool ID

### S3 Bucket Name
1. Go to AWS Console → S3
2. Find your bucket in the list
3. Copy the bucket name

## Different Environments

### Development (Local)
Use `.env` file (not committed to Git)

### Production Build
```bash
npm run build
```
This uses values from `.env` file

### CI/CD Deployment
Set environment variables in your CI/CD platform:
- GitHub Actions: Repository Secrets
- AWS Amplify: Environment Variables section
- Vercel/Netlify: Environment Variables in dashboard

## Security Best Practices

1. ✅ **Never commit `.env` to Git** - It's in `.gitignore`
2. ✅ **Use `.env.example` as template** - Safe to commit
3. ✅ **Rotate credentials regularly** - Update `.env` when credentials change
4. ✅ **Use different credentials per environment** - Dev, staging, prod should be separate
5. ✅ **Validate environment variables** - App will throw error if variables are missing

## Troubleshooting

### Error: "Missing required environment variable"
- Make sure you've created `.env` file
- Check that all variables are defined
- Restart dev server after changing `.env`

### Changes to `.env` not taking effect
- Restart the dev server (`npm run dev`)
- Clear browser cache
- Check for typos in variable names (must start with `VITE_`)

### TypeScript errors about `import.meta.env`
- Make sure `vite-env.d.ts` includes type definitions
- Restart TypeScript server in your editor

## Migration from Hardcoded Values

If you're migrating from hardcoded configuration:

1. ✅ Created `.env.example` template
2. ✅ Created `.env` with current production values
3. ✅ Updated `aws-config.ts` to use environment variables
4. ✅ Updated `api.ts` to use environment variables
5. ✅ Added TypeScript type definitions
6. ✅ Updated `.gitignore` to exclude `.env` files

## Additional Resources

- [Vite Environment Variables Documentation](https://vitejs.dev/guide/env-and-mode.html)
- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
