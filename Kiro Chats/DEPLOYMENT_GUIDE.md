# Deployment Guide: Legacy Maker Benefactor Assignment Feature

This guide covers the deployment of both backend (SAM) and frontend (Amplify) for the Legacy Maker Benefactor Assignment feature.

## Pre-Deployment Checklist

### Backend (SAM) Verification
- [x] All Lambda functions defined in template.yml
- [x] AccessConditionsDB table defined
- [x] IAM permissions configured
- [x] EventBridge rules for scheduled jobs
- [x] API Gateway endpoints configured
- [x] Environment variables set

### Frontend Verification
- [x] New components created (ManageBenefactors, CreateAssignmentDialog)
- [x] Service layer implemented (assignmentService.ts)
- [x] Routes configured in App.tsx
- [x] UserMenu updated with new menu item
- [x] BenefactorDashboard enhanced

## Deployment Steps

### Step 1: Backend (SAM) Deployment

#### 1.1 Validate SAM Template

```bash
cd SamLambda
sam validate --lint
```

#### 1.2 Build SAM Application

```bash
sam build
```

This will:
- Package all Lambda functions
- Install Python dependencies
- Prepare deployment artifacts

#### 1.3 Deploy to AWS

```bash
sam deploy --guided
```

Or if you have existing configuration:

```bash
sam deploy
```

**Expected Resources to be Created/Updated:**
- AccessConditionsDB DynamoDB table (NEW)
- CreateAssignmentFunction Lambda (NEW)
- GetAssignmentsFunction Lambda (NEW)
- UpdateAssignmentFunction Lambda (NEW)
- AcceptDeclineAssignmentFunction Lambda (NEW)
- ManualReleaseFunction Lambda (NEW)
- ResendInvitationFunction Lambda (NEW)
- TimeDelayProcessorFunction Lambda (NEW)
- CheckInSenderFunction Lambda (NEW)
- InactivityProcessorFunction Lambda (NEW)
- CheckInResponseFunction Lambda (NEW)
- PostConfirmationFunction Lambda (UPDATED)
- ValidateAccessFunction Lambda (UPDATED)
- API Gateway endpoints (NEW routes)
- EventBridge rules for scheduled jobs (NEW)

#### 1.4 Verify Deployment

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name [your-stack-name]

# List Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `Assignment`) || contains(FunctionName, `CheckIn`) || contains(FunctionName, `Processor`)].FunctionName'

# Verify DynamoDB table
aws dynamodb describe-table --table-name AccessConditionsDB

# Check EventBridge rules
aws events list-rules --name-prefix TimeDelay
aws events list-rules --name-prefix CheckIn
aws events list-rules --name-prefix Inactivity
```

### Step 2: Frontend Deployment

#### 2.1 Install Dependencies (if needed)

```bash
cd FrontEndCode
npm install
```

#### 2.2 Build Frontend

```bash
npm run build
```

This will:
- Compile TypeScript
- Bundle assets
- Optimize for production
- Output to `dist/` directory

#### 2.3 Verify Build

```bash
# Check build output
ls -la dist/

# Verify no build errors
echo $?  # Should be 0
```

#### 2.4 Deploy to AWS Amplify

The deployment to soulreel.net happens automatically via AWS Amplify when you push to the connected Git branch.

**Option A: Automatic Deployment (Recommended)**

```bash
# Commit changes
git add .
git commit -m "feat: Add Legacy Maker Benefactor Assignment feature

- Add assignment creation, management, and acceptance flows
- Add time-delayed, inactivity trigger, and manual release access conditions
- Add scheduled jobs for access condition processing
- Add check-in email system for inactivity monitoring
- Update PostConfirmation trigger for invitation handling
- Enhance ValidateAccess for access condition evaluation
- Add ManageBenefactors page and CreateAssignmentDialog component
- Update BenefactorDashboard to show assignments"

# Push to deployment branch
git push origin [your-branch-name]
```

Amplify will automatically:
- Detect the push
- Run build process
- Deploy to soulreel.net
- Update CloudFront distribution

**Option B: Manual Amplify Deployment**

If automatic deployment is not configured:

```bash
# Using Amplify CLI
amplify publish

# Or via AWS Console:
# 1. Go to AWS Amplify Console
# 2. Select your app
# 3. Click "Run build" or trigger deployment manually
```

#### 2.5 Verify Frontend Deployment

1. **Check Amplify Console:**
   - Go to AWS Amplify Console
   - Verify build succeeded
   - Check deployment status

2. **Test on soulreel.net:**
   - Navigate to https://soulreel.net
   - Log in as Legacy Maker
   - Check UserMenu for "Manage Benefactors" option
   - Navigate to Manage Benefactors page
   - Verify page loads without errors

3. **Browser Console Check:**
   - Open browser DevTools
   - Check for JavaScript errors
   - Verify API calls are working

### Step 3: Post-Deployment Verification

#### 3.1 Backend Health Checks

```bash
# Test CreateAssignment endpoint
curl -X POST https://[api-url]/assignments \
  -H "Authorization: Bearer [token]" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email":"test@example.com","access_conditions":[{"condition_type":"immediate"}]}'

# Test GetAssignments endpoint
curl -X GET "https://[api-url]/assignments?userId=[user-id]" \
  -H "Authorization: Bearer [token]"

# Check Lambda logs
aws logs tail /aws/lambda/CreateAssignmentFunction --follow
```

#### 3.2 Frontend Health Checks

1. **Legacy Maker Flow:**
   - Log in as Legacy Maker
   - Navigate to "Manage Benefactors"
   - Create a test assignment
   - Verify assignment appears in list

2. **Benefactor Flow:**
   - Log in as Benefactor
   - Check dashboard for assignments
   - Verify accept/decline options appear

3. **API Integration:**
   - Open browser Network tab
   - Perform actions
   - Verify API calls succeed (200 status)
   - Check response data

#### 3.3 Scheduled Jobs Verification

```bash
# Manually invoke scheduled jobs to test
aws lambda invoke \
  --function-name TimeDelayProcessorFunction \
  --payload '{}' \
  response.json

aws lambda invoke \
  --function-name CheckInSenderFunction \
  --payload '{}' \
  response.json

aws lambda invoke \
  --function-name InactivityProcessorFunction \
  --payload '{}' \
  response.json

# Check EventBridge rules are enabled
aws events describe-rule --name [rule-name]
```

## Rollback Procedures

### Backend Rollback

```bash
# Rollback SAM deployment
aws cloudformation update-stack \
  --stack-name [stack-name] \
  --use-previous-template

# Or delete new resources if needed
aws cloudformation delete-stack --stack-name [stack-name]
```

### Frontend Rollback

```bash
# Via Amplify Console:
# 1. Go to Amplify Console
# 2. Select your app
# 3. Go to "Deployments"
# 4. Find previous successful deployment
# 5. Click "Redeploy this version"

# Or via Git:
git revert [commit-hash]
git push origin [branch-name]
```

## Troubleshooting

### Common Backend Issues

1. **Lambda Function Errors:**
   ```bash
   # Check CloudWatch logs
   aws logs tail /aws/lambda/[FunctionName] --follow
   
   # Check function configuration
   aws lambda get-function --function-name [FunctionName]
   ```

2. **DynamoDB Access Issues:**
   ```bash
   # Verify table exists
   aws dynamodb describe-table --table-name AccessConditionsDB
   
   # Check IAM permissions
   aws iam get-role-policy --role-name [LambdaExecutionRole] --policy-name [PolicyName]
   ```

3. **API Gateway Issues:**
   ```bash
   # Test endpoint directly
   aws apigateway test-invoke-method \
     --rest-api-id [api-id] \
     --resource-id [resource-id] \
     --http-method POST
   ```

### Common Frontend Issues

1. **Build Failures:**
   ```bash
   # Clear cache and rebuild
   rm -rf node_modules dist
   npm install
   npm run build
   ```

2. **API Connection Issues:**
   - Check API endpoint URL in environment variables
   - Verify CORS configuration
   - Check authentication tokens

3. **Component Not Rendering:**
   - Check browser console for errors
   - Verify imports are correct
   - Check route configuration

## Environment Variables

### Backend Environment Variables

Set in SAM template or Lambda configuration:
- `PERSONA_RELATIONSHIPS_TABLE`: PersonaRelationshipsDB
- `ACCESS_CONDITIONS_TABLE`: AccessConditionsDB
- `PERSONA_SIGNUP_TEMP_TABLE`: PersonaSignupTempDB
- `USER_POOL_ID`: [Cognito User Pool ID]
- `KMS_KEY_ARN`: [KMS Key ARN]

### Frontend Environment Variables

Set in Amplify Console or `.env` file:
- `VITE_API_URL`: API Gateway base URL
- `VITE_USER_POOL_ID`: Cognito User Pool ID
- `VITE_USER_POOL_CLIENT_ID`: Cognito App Client ID

## Monitoring

### CloudWatch Dashboards

Create dashboards to monitor:
- Lambda invocation counts
- Lambda error rates
- API Gateway request counts
- DynamoDB read/write capacity
- EventBridge rule executions

### Alarms

Set up CloudWatch alarms for:
- Lambda function errors > threshold
- API Gateway 5xx errors
- DynamoDB throttling
- Scheduled job failures

## Next Steps

After successful deployment:

1. **Run Integration Tests:**
   - Follow the Integration Testing Guide
   - Verify all flows work end-to-end

2. **Monitor Initial Usage:**
   - Watch CloudWatch logs
   - Check for errors or unexpected behavior
   - Monitor performance metrics

3. **User Acceptance Testing:**
   - Have stakeholders test the feature
   - Gather feedback
   - Address any issues

4. **Documentation:**
   - Update user documentation
   - Create training materials if needed
   - Document any deployment-specific configurations

## Support

For issues or questions:
- Check CloudWatch logs first
- Review this deployment guide
- Consult the Integration Testing Guide
- Check AWS service health dashboard

