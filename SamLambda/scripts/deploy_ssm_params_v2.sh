#!/bin/bash
set -e

# =============================================================================
# SoulReel — Pricing & Billing V2: SSM Parameter Updates
# =============================================================================
#
# Updates SSM parameters for the new 2-tier pricing model:
#   - Free: Level 1 only, 1 benefactor, immediate access
#   - Premium: $14.99/month or $149/year, all levels, unlimited benefactors
#
# Also sets cost optimization model parameters and creates coupon definitions.
#
# SAFE TO RE-RUN: Uses --overwrite on all calls.
# DOES NOT TOUCH: Stripe secret keys (those are in setup-ssm-params.sh)
#
# PREREQUISITE: Before running this script, create new Stripe products/prices
# in the Stripe Dashboard:
#   1. Product: "SoulReel Premium" (or update existing)
#   2. Price: $14.99/month recurring
#   3. Price: $149/year recurring
#   4. Coupon: FOUNDING100 — 33% off forever (makes $149 → ~$99)
#   5. Coupon: WINBACK99 — 33% off forever (makes $149 → ~$99)
#   Note the new Price IDs and update FrontEndCode/.env and
#   SamLambda/functions/billingFunctions/stripeWebhook/app.py PRICE_PLAN_MAP
#
# Usage:
#   chmod +x scripts/deploy_ssm_params_v2.sh
#   ./scripts/deploy_ssm_params_v2.sh
#
# Optional: pass a region override
#   AWS_REGION=us-west-2 ./scripts/deploy_ssm_params_v2.sh
# =============================================================================

REGION="${AWS_REGION:-us-east-1}"

echo "============================================================"
echo "SoulReel — Pricing & Billing V2: SSM Parameter Updates"
echo "Region: $REGION"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------------
# 1. Free Plan Definition (updated)
#    Changes from v1:
#      - allowedQuestionCategories: removed _L1 suffix (level gating via maxLevel)
#      - maxLevel: 1 (NEW — restricts free users to Level 1 questions)
#      - maxBenefactors: 2 → 1
#      - Removed: previewQuestions, conversationsPerWeek
# -----------------------------------------------------------------------------
echo "Updating Free plan definition..."
aws ssm put-parameter \
  --name "/soulreel/plans/free" \
  --value '{"planId":"free","maxLevel":1,"allowedQuestionCategories":["life_story_reflections"],"maxBenefactors":1,"accessConditionTypes":["immediate"],"features":["basic"],"totalLevel1Questions":20}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/plans/free"

# -----------------------------------------------------------------------------
# 2. Premium Plan Definition (updated)
#    Changes from v1:
#      - maxLevel: 10 (NEW — premium users access all levels)
#      - monthlyPriceDisplay: "$9.99" → "$14.99"
#      - annualPriceDisplay: "$79" → "$149"
#      - annualMonthlyEquivalentDisplay: "$6.58" → "$12.42"
#      - annualSavingsPercent: 34 → 17
#      - foundingMemberPrice: 99 (NEW)
#      - foundingMemberCouponCode: "FOUNDING100" (NEW)
#      - Removed: conversationsPerWeek
# -----------------------------------------------------------------------------
echo "Updating Premium plan definition..."
aws ssm put-parameter \
  --name "/soulreel/plans/premium" \
  --value '{"planId":"premium","maxLevel":10,"allowedQuestionCategories":["life_story_reflections","life_events","values_and_emotions"],"maxBenefactors":-1,"accessConditionTypes":["immediate","time_delayed","inactivity_trigger","manual_release"],"features":["basic","dead_mans_switch","pdf_export","priority_ai","legacy_export","psych_profile","avatar"],"monthlyPriceDisplay":"$14.99","annualPriceDisplay":"$149","annualMonthlyEquivalentDisplay":"$12.42","annualSavingsPercent":17,"foundingMemberPrice":99,"foundingMemberCouponCode":"FOUNDING100"}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/plans/premium"

# -----------------------------------------------------------------------------
# 3. Founding Member Coupon (NEW)
#    First 100 users get $99/year (33% off $149). Auto-expires when
#    currentRedemptions reaches maxRedemptions. The Stripe coupon
#    FOUNDING100 must be created in the Stripe Dashboard first.
# -----------------------------------------------------------------------------
echo "Creating FOUNDING100 coupon..."
aws ssm put-parameter \
  --name "/soulreel/coupons/FOUNDING100" \
  --value '{"code":"FOUNDING100","type":"percentage","percentOff":33,"stripeCouponId":"FOUNDING100","maxRedemptions":100,"currentRedemptions":0,"expiresAt":null,"createdBy":"system-config"}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/coupons/FOUNDING100"

# -----------------------------------------------------------------------------
# 4. Win-Back Coupon (NEW)
#    For churned users — $99/year (33% off $149). The Stripe coupon
#    WINBACK99 must be created in the Stripe Dashboard first.
# -----------------------------------------------------------------------------
echo "Creating WINBACK99 coupon..."
aws ssm put-parameter \
  --name "/soulreel/coupons/WINBACK99" \
  --value '{"code":"WINBACK99","type":"percentage","percentOff":33,"stripeCouponId":"WINBACK99","maxRedemptions":1000,"currentRedemptions":0,"expiresAt":null,"createdBy":"system-config"}' \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /soulreel/coupons/WINBACK99"

# -----------------------------------------------------------------------------
# 5. Cost Optimization: Depth Scoring Model (updated)
#    Switch from Claude 3 Haiku to Amazon Nova Micro for the simple
#    0-3 scoring task. ~85% cost reduction on scoring.
# -----------------------------------------------------------------------------
echo "Updating depth scoring model to Nova Micro..."
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-scoring-model" \
  --value "amazon.nova-micro-v1:0" \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /virtuallegacy/conversation/llm-scoring-model → amazon.nova-micro-v1:0"

# -----------------------------------------------------------------------------
# 6. Cost Optimization: Conversation Model (updated)
#    Switch from Claude 3.5 Sonnet v2 to Claude 3.5 Haiku for response
#    generation. ~85% cost reduction on the largest per-turn cost.
# -----------------------------------------------------------------------------
echo "Updating conversation model to Haiku..."
aws ssm put-parameter \
  --name "/virtuallegacy/conversation/llm-conversation-model" \
  --value "us.anthropic.claude-3-5-haiku-20241022-v1:0" \
  --type String \
  --overwrite \
  --region "$REGION"

echo "✅ /virtuallegacy/conversation/llm-conversation-model → us.anthropic.claude-3-5-haiku-20241022-v1:0"

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "All V2 SSM parameters updated successfully."
echo "============================================================"
echo ""
echo "To verify, run:"
echo "  aws ssm get-parameter --name /soulreel/plans/free --region $REGION --query 'Parameter.Value' --output text | python3 -m json.tool"
echo "  aws ssm get-parameter --name /soulreel/plans/premium --region $REGION --query 'Parameter.Value' --output text | python3 -m json.tool"
echo "  aws ssm get-parameter --name /soulreel/coupons/FOUNDING100 --region $REGION --query 'Parameter.Value' --output text | python3 -m json.tool"
echo "  aws ssm get-parameter --name /soulreel/coupons/WINBACK99 --region $REGION --query 'Parameter.Value' --output text | python3 -m json.tool"
echo "  aws ssm get-parameter --name /virtuallegacy/conversation/llm-scoring-model --region $REGION"
echo "  aws ssm get-parameter --name /virtuallegacy/conversation/llm-conversation-model --region $REGION"
echo ""
echo "NEXT STEPS:"
echo "  1. Create Stripe products/prices for \$14.99/month and \$149/year"
echo "  2. Create Stripe coupons FOUNDING100 and WINBACK99 (33% off forever)"
echo "  3. Update FrontEndCode/.env with new Stripe Price IDs"
echo "  4. Update PRICE_PLAN_MAP in stripeWebhook/app.py with new Price IDs"
echo "  5. Deploy backend: sam build && sam deploy --no-confirm-changeset"
