#!/bin/bash
# Deploy psychological test definition JSON files to S3.
#
# Usage:
#   ./deploy-test-definitions.sh [bucket-name]
#
# Default bucket: virtual-legacy
# Files are uploaded to s3://<bucket>/psych-tests/

set -euo pipefail

BUCKET="${1:-virtual-legacy}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Deploying test definitions to s3://${BUCKET}/psych-tests/"

aws s3 sync "$SCRIPT_DIR" "s3://${BUCKET}/psych-tests/" \
  --exclude "*.py" \
  --exclude "*.sh" \
  --exclude "*.md" \
  --exclude "__pycache__/*" \
  --include "*.json" \
  --content-type "application/json"

echo "Done. Deployed test definitions:"
aws s3 ls "s3://${BUCKET}/psych-tests/" --human-readable