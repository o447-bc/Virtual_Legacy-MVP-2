#!/bin/bash
set -e

echo "🚀 Deploying Virtual Legacy Backend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Navigate to SAM directory
cd "$(dirname "$0")/SamLambda"

# Build
echo "📦 Building SAM application..."
sam build

# Deploy
echo "🚀 Deploying to AWS..."
sam deploy --no-confirm-changeset

# Get endpoints
echo ""
echo "✅ Backend deployed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 API Endpoints:"
sam list endpoints --output table

echo ""
echo "💡 To view logs: sam logs --stack-name Virtual-Legacy-MVP-1 --tail"
