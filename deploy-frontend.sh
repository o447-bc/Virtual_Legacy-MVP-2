#!/bin/bash
set -e

echo "🎨 Building Virtual Legacy Frontend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Navigate to frontend directory
cd "$(dirname "$0")/FrontEndCode"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build
echo "🔨 Building production bundle..."
npm run build

# Create zip for manual upload
echo "📦 Creating deployment package..."
cd dist
zip -r ../dist.zip . > /dev/null 2>&1
cd ..

echo ""
echo "✅ Frontend built successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 Build output: FrontEndCode/dist/"
echo "📦 Deployment package: FrontEndCode/dist.zip"
echo ""
echo "Next steps:"
echo "  1. Go to https://console.aws.amazon.com/amplify/"
echo "  2. Upload dist.zip to your Amplify app"
echo "  OR"
echo "  Run: cd FrontEndCode && amplify publish"
