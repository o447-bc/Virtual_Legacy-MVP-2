# GitHub Actions — Required Secrets

Go to: https://github.com/o447-bc/Virtual_Legacy-MVP-2/settings/secrets/actions

## AWS credentials

Both workflows authenticate via OIDC — no long-lived access keys stored in GitHub.

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the `soulreel-github-actions-oidc` IAM role (e.g. `arn:aws:iam::ACCOUNT_ID:role/soulreel-github-actions-oidc`) |

The role is assumed via GitHub's OIDC token. See **OIDC setup** below for how to create it.
Once OIDC is working, delete the old `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets
and deactivate the `soulreel-github-actions` IAM user's access keys.

### OIDC setup (one-time, run from your local AWS CLI)

```bash
# 1. Create the OIDC provider (only needed once per AWS account)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 2. Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 3. Create the trust policy file
cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:o447-bc/Virtual_Legacy-MVP-2:ref:refs/heads/master"
        }
      }
    }
  ]
}
EOF
# Replace placeholder with real account ID
sed -i '' "s/ACCOUNT_ID/$ACCOUNT_ID/g" /tmp/trust-policy.json

# 4. Create the role
aws iam create-role \
  --role-name soulreel-github-actions-oidc \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Assumed by GitHub Actions via OIDC for Virtual Legacy deploys"

# 5. Attach the same permissions the old IAM user had
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AWSCloudFormationFullAccess
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name soulreel-github-actions-oidc --policy-arn arn:aws:iam::aws:policy/AdministratorAccess-Amplify

# 6. Print the role ARN to add as the AWS_DEPLOY_ROLE_ARN secret
aws iam get-role --role-name soulreel-github-actions-oidc --query Role.Arn --output text
```

Add the printed ARN as the `AWS_DEPLOY_ROLE_ARN` secret in GitHub, then push to master to test.

## Frontend build env vars

| Secret | Value |
|--------|-------|
| `VITE_API_BASE_URL` | `https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod` |
| `VITE_USER_POOL_ID` | `us-east-1_KsG65yYlo` |
| `VITE_USER_POOL_CLIENT_ID` | Your Cognito app client ID (from AWS Console) |
| `VITE_IDENTITY_POOL_ID` | Your Cognito identity pool ID (if used) |
| `VITE_S3_BUCKET` | `virtual-legacy` |
