// AWS Amplify v6 configuration
// Environment variables are loaded from .env file (see .env.example for template)

// Validate required environment variables
const requiredEnvVars = {
  VITE_USER_POOL_ID: import.meta.env.VITE_USER_POOL_ID,
  VITE_USER_POOL_CLIENT_ID: import.meta.env.VITE_USER_POOL_CLIENT_ID,
  VITE_IDENTITY_POOL_ID: import.meta.env.VITE_IDENTITY_POOL_ID,
  VITE_AWS_REGION: import.meta.env.VITE_AWS_REGION,
  VITE_S3_BUCKET: import.meta.env.VITE_S3_BUCKET,
};

// Check for missing environment variables
const missingVars = Object.entries(requiredEnvVars)
  .filter(([_, value]) => !value)
  .map(([key]) => key);

if (missingVars.length > 0) {
  throw new Error(
    `Missing required environment variables: ${missingVars.join(', ')}\n` +
    'Please copy .env.example to .env and fill in your values.'
  );
}

export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
      identityPoolId: import.meta.env.VITE_IDENTITY_POOL_ID,
      region: import.meta.env.VITE_AWS_REGION
    }
  },
  Storage: {
    S3: {
      bucket: import.meta.env.VITE_S3_BUCKET,
      region: import.meta.env.VITE_AWS_REGION
    }
  }
};


