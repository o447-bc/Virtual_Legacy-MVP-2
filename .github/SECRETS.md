# GitHub Actions — Required Secrets

Go to: https://github.com/o447-bc/Virtual_Legacy-MVP-2/settings/secrets/actions

## AWS credentials (used by both workflows)

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | IAM user access key (needs permissions below) |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |

The IAM user needs these policies:
- `AWSCloudFormationFullAccess`
- `AWSLambdaFullAccess`
- `IAMFullAccess` (for SAM to manage Lambda execution roles)
- `AmazonS3FullAccess` (SAM artifact bucket)
- `AmazonAPIGatewayAdministrator`
- `AmazonDynamoDBFullAccess`
- `AWSAmplifyFullAccess` (for frontend deploy)

Or attach the AWS managed `AdministratorAccess` policy to a dedicated CI user
and scope it down later once the pipeline is stable.

## Frontend build env vars

| Secret | Value |
|--------|-------|
| `VITE_API_BASE_URL` | `https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod` |
| `VITE_USER_POOL_ID` | `us-east-1_KsG65yYlo` |
| `VITE_USER_POOL_CLIENT_ID` | Your Cognito app client ID (from AWS Console) |
| `VITE_IDENTITY_POOL_ID` | Your Cognito identity pool ID (if used) |
| `VITE_S3_BUCKET` | `virtual-legacy` |
