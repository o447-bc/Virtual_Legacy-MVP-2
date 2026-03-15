#!/bin/bash

# Create deployment package
zip -r lambda-deployment.zip lambda_function.py

echo "Deployment package created: lambda-deployment.zip"
echo ""
echo "Next steps:"
echo "1. Go to AWS Lambda Console"
echo "2. Create new function"
echo "3. Upload lambda-deployment.zip"
echo "4. Set up S3 trigger"