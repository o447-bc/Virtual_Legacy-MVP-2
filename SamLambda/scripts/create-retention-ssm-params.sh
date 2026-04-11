#!/bin/bash
set -e

# =============================================================================
# SoulReel — Data Retention SSM Parameter Setup
# =============================================================================
#
# Creates all /soulreel/data-retention/* SSM parameters used by the data
# retention lifecycle Lambda functions. Run once per AWS account/region to
# bootstrap, and re-run safely at any time (--overwrite on every call).
#
# These parameters control time thresholds, rate limits, and feature flags
# for dormancy detection, account deletion, legacy protection, storage
# lifecycle, and data export services.
#
# Usage:
#   chmod +x scripts/create-retention-ssm-params.sh
#   ./scripts/create-retention-ssm-params.sh
#
# Optional: pass a region override
#   AWS_REGION=us-west-2 ./scripts/create-retention-ssm-params.sh
# =============================================================================

REGION="${AWS_REGION:-us-east-1}"

echo "Setting up SoulReel data retention SSM parameters in region: $REGION"
echo ""

# -----------------------------------------------------------------------------
# Dormancy thresholds (days)
# Used by DormantAccountDetector to send escalating re-engagement emails.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/dormancy-threshold-1" \
  --value "180" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/dormancy-threshold-1 (180 days — 6 months)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/dormancy-threshold-2" \
  --value "365" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/dormancy-threshold-2 (365 days — 12 months)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/dormancy-threshold-3" \
  --value "730" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/dormancy-threshold-3 (730 days — 24 months)"

# -----------------------------------------------------------------------------
# Account deletion grace period (days)
# Time between deletion request and permanent data removal.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/deletion-grace-period" \
  --value "30" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/deletion-grace-period (30 days)"

# -----------------------------------------------------------------------------
# Legacy protection thresholds (days)
# Used by LegacyProtectionFunction for auto-activation criteria.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/legacy-protection-dormancy-days" \
  --value "730" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/legacy-protection-dormancy-days (730 days — 24 months dormant)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/legacy-protection-lapse-days" \
  --value "365" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/legacy-protection-lapse-days (365 days — 12 months lapsed)"

# -----------------------------------------------------------------------------
# Storage lifecycle thresholds (days)
# Used by StorageLifecycleManager for Glacier transitions.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/glacier-transition-days" \
  --value "365" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/glacier-transition-days (365 days)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/glacier-no-access-days" \
  --value "180" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/glacier-no-access-days (180 days)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/intelligent-tiering-days" \
  --value "30" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/intelligent-tiering-days (30 days)"

# -----------------------------------------------------------------------------
# Export settings
# Rate limit and link expiry for data export service.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/export-rate-limit-days" \
  --value "30" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/export-rate-limit-days (30 days)"

aws ssm put-parameter \
  --name "/soulreel/data-retention/export-link-expiry-hours" \
  --value "72" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/export-link-expiry-hours (72 hours)"

# -----------------------------------------------------------------------------
# Testing mode flag
# When 'enabled', lifecycle functions accept simulatedCurrentTime parameter.
# Defaults to 'disabled' — admin endpoints return 403 unless explicitly enabled.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/data-retention/testing-mode" \
  --value "disabled" \
  --type String \
  --overwrite \
  --region "$REGION"
echo "✅ /soulreel/data-retention/testing-mode (disabled)"

echo ""
echo "All data retention SSM parameters created successfully."
echo ""
echo "To verify, run:"
echo "  aws ssm get-parameters-by-path --path /soulreel/data-retention/ --region $REGION"
