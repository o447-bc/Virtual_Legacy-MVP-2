#!/bin/bash
set -e

# =============================================================================
# SoulReel — Stripe & Subscription Plan SSM Parameter Setup
# =============================================================================
#
# This script creates the SSM parameters required by the Stripe subscription
# billing infrastructure. Run it once per AWS account/region to bootstrap the
# parameters, and re-run safely at any time (--overwrite is used on every call).
#
# IMPORTANT: Replace the placeholder Stripe keys below with your actual
# test-mode keys from https://dashboard.stripe.com/test/apikeys before running.
#
#   sk_test_YOUR_KEY_HERE   → your Stripe Secret Key
#   pk_test_YOUR_KEY_HERE   → your Stripe Publishable Key
#   whsec_YOUR_SECRET_HERE  → your Stripe Webhook Signing Secret
#
# Usage:
#   chmod +x scripts/setup-ssm-params.sh
#   ./scripts/setup-ssm-params.sh
#
# Optional: pass a region override
#   AWS_REGION=us-west-2 ./scripts/setup-ssm-params.sh
# =============================================================================

REGION="${AWS_REGION:-us-east-1}"

echo "Setting up SoulReel Stripe & plan SSM parameters in region: $REGION"
echo ""

# -----------------------------------------------------------------------------
# 1. Stripe Secret Key (SecureString)
#    Used by BillingFunction and StripeWebhookFunction to call the Stripe API.
#    Must be kept secret — stored as SecureString (encrypted with default KMS key).
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/stripe/secret-key" \
  --value "sk_test_YOUR_KEY_HERE" \
  --type SecureString \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/stripe/secret-key (SecureString)"

# -----------------------------------------------------------------------------
# 2. Stripe Webhook Signing Secret (SecureString)
#    Used by StripeWebhookFunction to verify incoming webhook event signatures.
#    Must be kept secret — stored as SecureString.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/stripe/webhook-secret" \
  --value "whsec_YOUR_SECRET_HERE" \
  --type SecureString \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/stripe/webhook-secret (SecureString)"

# -----------------------------------------------------------------------------
# 3. Stripe Publishable Key (String)
#    Used by the frontend to initialize Stripe.js. Safe to expose publicly —
#    stored as a plain String (not SecureString).
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/stripe/publishable-key" \
  --value "pk_test_YOUR_KEY_HERE" \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/stripe/publishable-key (String)"

# -----------------------------------------------------------------------------
# 4. Free Plan Definition (String, JSON)
#    Defines limits for the Free tier: L1 Life Story Reflections only,
#    2 benefactors max, immediate access only, basic features.
#    Read by plan_check utility and BillingFunction at runtime.
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/plans/free" \
  --value '{"planId":"free","allowedQuestionCategories":["life_story_reflections_L1"],"maxBenefactors":2,"accessConditionTypes":["immediate"],"features":["basic"]}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/plans/free (String — Free plan definition)"

# -----------------------------------------------------------------------------
# 5. Premium Plan Definition (String, JSON)
#    Defines limits for the Premium tier: all question categories, unlimited
#    benefactors, all access condition types, all features. Includes pricing
#    display fields used by the frontend (never hardcoded in UI code).
# -----------------------------------------------------------------------------
aws ssm put-parameter \
  --name "/soulreel/plans/premium" \
  --value '{"planId":"premium","allowedQuestionCategories":["life_story_reflections","life_events","values_and_emotions"],"maxBenefactors":-1,"accessConditionTypes":["immediate","time_delayed","inactivity_trigger","manual_release"],"features":["basic","dead_mans_switch","pdf_export","priority_ai","legacy_export","psych_profile","avatar"],"monthlyPriceDisplay":"$9.99","annualPriceDisplay":"$79","annualMonthlyEquivalentDisplay":"$6.58","annualSavingsPercent":34}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/plans/premium (String — Premium plan definition)"

echo ""
echo "All SSM parameters created successfully."
echo ""
echo "To verify, run:"
echo "  aws ssm get-parameter --name /soulreel/stripe/publishable-key --region $REGION"
echo "  aws ssm get-parameter --name /soulreel/plans/free --region $REGION"
echo "  aws ssm get-parameter --name /soulreel/plans/premium --region $REGION"
echo "  aws ssm get-parameter --name /soulreel/stripe/secret-key --with-decryption --region $REGION"
echo "  aws ssm get-parameter --name /soulreel/stripe/webhook-secret --with-decryption --region $REGION"
