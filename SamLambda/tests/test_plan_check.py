"""
Comprehensive unit tests for plan_check.py (V2 pricing model).

Tests level gating, premium status detection, benefactor limits,
access condition types, removed features, and property-based invariants.

Uses pytest + hypothesis + unittest.mock.
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Ensure shared python layer is importable
# ---------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'shared', 'python'),
)


# ---------------------------------------------------------------------------
# Plan definitions used across tests
# ---------------------------------------------------------------------------

FREE_PLAN_DEF = {
    'planId': 'free',
    'maxLevel': 1,
    'allowedQuestionCategories': ['life_story_reflections'],
    'maxBenefactors': 1,
    'accessConditionTypes': ['immediate'],
    'features': ['basic'],
}

PREMIUM_PLAN_DEF = {
    'planId': 'premium',
    'maxLevel': 10,
    'allowedQuestionCategories': [
        'life_story_reflections',
        'life_events',
        'values_and_emotions',
    ],
    'maxBenefactors': -1,
    'accessConditionTypes': [
        'immediate',
        'time_delayed',
        'inactivity_trigger',
        'manual_release',
    ],
    'features': ['basic', 'dead_mans_switch', 'pdf_export'],
}


def _mock_get_plan_definition(plan_id):
    if plan_id == 'premium':
        return dict(PREMIUM_PLAN_DEF)
    return dict(FREE_PLAN_DEF)


def _make_subscription(
    user_id='user-1',
    plan_id='free',
    status='free',
    benefactor_count=0,
    trial_expires_at=None,
    coupon_expires_at=None,
):
    """Build a mock subscription record.

    Default status is 'free' — a non-premium status.  ``is_premium_active``
    treats 'active' and 'comped' as premium regardless of planId, so free-tier
    tests must use a status that is NOT in that set.
    """
    rec = {
        'userId': user_id,
        'planId': plan_id,
        'status': status,
        'benefactorCount': benefactor_count,
    }
    if trial_expires_at is not None:
        rec['trialExpiresAt'] = trial_expires_at
    if coupon_expires_at is not None:
        rec['couponExpiresAt'] = coupon_expires_at
    return rec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_plan_cache():
    """Clear the module-level SSM cache between every test."""
    import plan_check
    plan_check._plan_cache = {}
    plan_check._plans_loaded = False
    yield
    plan_check._plan_cache = {}
    plan_check._plans_loaded = False


# ===================================================================
# Level gating — check_question_category_access
# ===================================================================

class TestLevelGating:
    """Level gating for free users via check_question_category_access."""

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_level1_life_story_allowed(self, mock_get_user_plan, mock_plan_def):
        """Free user (maxLevel=1) on Level 1 life_story_reflections → allowed."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'life_story_reflections-general-L1-Q3')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_level2_life_story_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user (maxLevel=1) on Level 2 life_story_reflections → denied, reason=question_level."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'life_story_reflections-general-L2-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_level'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_level5_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user on Level 5 question → denied."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'life_story_reflections-deep-L5-Q2')

        assert result['allowed'] is False
        assert result['reason'] == 'question_level'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_life_events_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user on life_events category → denied, reason=question_category."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_values_and_emotions_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user on values_and_emotions category → denied, reason=question_category."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'values_and_emotions-core-L1-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_life_story_level1_both_pass(self, mock_get_user_plan, mock_plan_def):
        """Free user on life_story_reflections Level 1 → allowed (both category and level pass)."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_question_category_access('user-1', 'life_story_reflections-childhood-L1-Q7')

        assert result['allowed'] is True
        assert result['reason'] is None


# ===================================================================
# Premium status — is_premium_active + check_question_category_access
# ===================================================================

class TestPremiumStatus:
    """Premium status detection and its effect on access checks."""

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_active_premium_any_level_allowed(self, mock_get_user_plan, mock_plan_def):
        """Premium user (status: active) on any level → allowed."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='active',
        )
        result = check_question_category_access('user-1', 'life_events-career-L8-Q3')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_comped_premium_any_level_allowed(self, mock_get_user_plan, mock_plan_def):
        """Premium user (status: comped) on any level → allowed."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='comped',
        )
        result = check_question_category_access('user-1', 'values_and_emotions-deep-L10-Q1')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_trialing_valid_trial_expires_at_allowed(self, mock_get_user_plan, mock_plan_def):
        """Trialing user with future trialExpiresAt → allowed (backward compat)."""
        from plan_check import check_question_category_access

        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='trialing', trial_expires_at=future,
        )
        result = check_question_category_access('user-1', 'life_events-milestones-L5-Q1')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_trialing_expired_trial_expires_at_denied(self, mock_get_user_plan, mock_plan_def):
        """Trialing user with past trialExpiresAt → denied (treated as free)."""
        from plan_check import check_question_category_access

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', status='trialing', trial_expires_at=past,
        )
        result = check_question_category_access('user-1', 'life_events-milestones-L5-Q1')

        assert result['allowed'] is False

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_trialing_valid_coupon_expires_at_allowed(self, mock_get_user_plan, mock_plan_def):
        """Trialing user with future couponExpiresAt → allowed."""
        from plan_check import check_question_category_access

        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='trialing', coupon_expires_at=future,
        )
        result = check_question_category_access('user-1', 'values_and_emotions-core-L3-Q2')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_trialing_expired_coupon_expires_at_denied(self, mock_get_user_plan, mock_plan_def):
        """Trialing user with past couponExpiresAt → denied."""
        from plan_check import check_question_category_access

        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', status='trialing', coupon_expires_at=past,
        )
        result = check_question_category_access('user-1', 'life_events-career-L2-Q1')

        assert result['allowed'] is False

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_canceled_user_denied(self, mock_get_user_plan, mock_plan_def):
        """Canceled user → denied (treated as free)."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', status='canceled',
        )
        result = check_question_category_access('user-1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_no_subscription_record_fail_open(self, mock_get_user_plan, mock_plan_def):
        """User with no subscription record → _FREE_PLAN_DEFAULT has planId='free',
        status='active'. Since planId is 'free', is_premium_active returns False,
        so the user is gated by plan limits (Level 1 only)."""
        from plan_check import check_question_category_access

        # get_user_plan returns the free default when no record exists
        mock_get_user_plan.return_value = {
            'userId': 'user-1',
            'planId': 'free',
            'status': 'active',
            'benefactorCount': 0,
        }
        # Level 1 allowed for free users
        result = check_question_category_access('user-1', 'life_story_reflections-general-L1-Q1')
        assert result['allowed'] is True

        # Level 2 denied for free users (planId='free' → not premium → level check applies)
        result = check_question_category_access('user-1', 'life_story_reflections-general-L2-Q1')
        assert result['allowed'] is False
        assert result['reason'] == 'question_level'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_explicit_free_user_level1_only(self, mock_get_user_plan, mock_plan_def):
        """User with an explicit free subscription (non-premium status) → Level 1 only."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', status='free',
        )
        result = check_question_category_access('user-1', 'life_story_reflections-general-L1-Q1')
        assert result['allowed'] is True

        result = check_question_category_access('user-1', 'life_story_reflections-general-L2-Q1')
        assert result['allowed'] is False
        assert result['reason'] == 'question_level'


# ===================================================================
# is_premium_active — direct unit tests
# ===================================================================

class TestIsPremiumActive:
    """Direct tests for the is_premium_active helper."""

    def test_active_status(self):
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'premium', 'status': 'active'}) is True

    def test_comped_status(self):
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'premium', 'status': 'comped'}) is True

    def test_trialing_with_future_trial_expires(self):
        from plan_check import is_premium_active
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        assert is_premium_active({'planId': 'premium', 'status': 'trialing', 'trialExpiresAt': future}) is True

    def test_trialing_with_past_trial_expires(self):
        from plan_check import is_premium_active
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert is_premium_active({'planId': 'premium', 'status': 'trialing', 'trialExpiresAt': past}) is False

    def test_trialing_with_future_coupon_expires(self):
        from plan_check import is_premium_active
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        assert is_premium_active({'planId': 'premium', 'status': 'trialing', 'couponExpiresAt': future}) is True

    def test_trialing_with_past_coupon_expires(self):
        from plan_check import is_premium_active
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        assert is_premium_active({'planId': 'premium', 'status': 'trialing', 'couponExpiresAt': past}) is False

    def test_trialing_no_expiry_fields(self):
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'premium', 'status': 'trialing'}) is False

    def test_canceled_status(self):
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'premium', 'status': 'canceled'}) is False

    def test_empty_status(self):
        from plan_check import is_premium_active
        assert is_premium_active({'status': ''}) is False

    def test_missing_status(self):
        from plan_check import is_premium_active
        assert is_premium_active({}) is False

    def test_free_plan_active_status_returns_false(self):
        """Free plan with status=active should NOT be premium."""
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'free', 'status': 'active'}) is False

    def test_free_plan_comped_status_returns_false(self):
        """Free plan with status=comped should NOT be premium."""
        from plan_check import is_premium_active
        assert is_premium_active({'planId': 'free', 'status': 'comped'}) is False


# ===================================================================
# Benefactor limits — check_benefactor_limit
# ===================================================================

class TestBenefactorLimit:
    """Benefactor limit enforcement via check_benefactor_limit."""

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_zero_benefactors_allowed(self, mock_get_user_plan, mock_plan_def):
        """Free user with 0 benefactors → allowed (limit is 1)."""
        from plan_check import check_benefactor_limit

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', benefactor_count=0,
        )
        result = check_benefactor_limit('user-1')

        assert result['allowed'] is True
        assert result['currentCount'] == 0
        assert result['limit'] == 1

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_at_limit_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user with 1 benefactor → denied (at limit)."""
        from plan_check import check_benefactor_limit

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='free', benefactor_count=1,
        )
        result = check_benefactor_limit('user-1')

        assert result['allowed'] is False
        assert result['currentCount'] == 1
        assert result['limit'] == 1

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_premium_user_unlimited_benefactors(self, mock_get_user_plan, mock_plan_def):
        """Premium user with any count → allowed (unlimited, maxBenefactors=-1)."""
        from plan_check import check_benefactor_limit

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='active', benefactor_count=50,
        )
        result = check_benefactor_limit('user-1')

        assert result['allowed'] is True
        assert result['limit'] == -1
        assert result['currentCount'] == 50


# ===================================================================
# Access condition types — check_access_condition_type
# ===================================================================

class TestAccessConditionType:
    """Access condition type enforcement via check_access_condition_type."""

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_immediate_allowed(self, mock_get_user_plan, mock_plan_def):
        """Free user with 'immediate' → allowed."""
        from plan_check import check_access_condition_type

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_access_condition_type('user-1', 'immediate')

        assert result['allowed'] is True

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_time_delayed_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user with 'time_delayed' → denied, reason=access_condition_restricted."""
        from plan_check import check_access_condition_type

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_access_condition_type('user-1', 'time_delayed')

        assert result['allowed'] is False
        assert result['reason'] == 'access_condition_restricted'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_premium_user_any_condition_allowed(self, mock_get_user_plan, mock_plan_def):
        """Premium user with any condition type → allowed."""
        from plan_check import check_access_condition_type

        mock_get_user_plan.return_value = _make_subscription(
            plan_id='premium', status='active',
        )
        for cond in ('immediate', 'time_delayed', 'inactivity_trigger', 'manual_release'):
            result = check_access_condition_type('user-1', cond)
            assert result['allowed'] is True, f"Premium should allow {cond}"

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_free_user_inactivity_trigger_denied(self, mock_get_user_plan, mock_plan_def):
        """Free user with 'inactivity_trigger' → denied."""
        from plan_check import check_access_condition_type

        mock_get_user_plan.return_value = _make_subscription(plan_id='free')
        result = check_access_condition_type('user-1', 'inactivity_trigger')

        assert result['allowed'] is False
        assert result['reason'] == 'access_condition_restricted'


# ===================================================================
# Removed features — verify old V1 logic no longer exists
# ===================================================================

class TestRemovedFeatures:
    """Verify that deprecated V1 features have been removed from plan_check."""

    def test_no_conversations_per_week_enforcement(self):
        """No conversationsPerWeek enforcement exists in any function."""
        import plan_check
        source = open(plan_check.__file__).read()
        assert 'conversationsPerWeek' not in source

    def test_no_has_completed_preview_function(self):
        """No _has_completed_preview function exists."""
        import plan_check
        assert not hasattr(plan_check, '_has_completed_preview')

    def test_no_preview_questions_logic(self):
        """No previewQuestions logic exists."""
        import plan_check
        source = open(plan_check.__file__).read()
        assert 'previewQuestions' not in source
        assert 'isPreview' not in source


# ===================================================================
# Fail-open behaviour
# ===================================================================

class TestFailOpen:
    """Verify fail-open semantics on internal errors."""

    @patch('plan_check.get_user_plan', side_effect=Exception('DynamoDB down'))
    def test_check_question_category_access_fails_open(self, mock_get_user_plan):
        from plan_check import check_question_category_access

        result = check_question_category_access('user-1', 'life_events-career-L5-Q1')
        assert result['allowed'] is True

    @patch('plan_check.get_user_plan', side_effect=Exception('DynamoDB down'))
    def test_check_benefactor_limit_fails_open(self, mock_get_user_plan):
        from plan_check import check_benefactor_limit

        result = check_benefactor_limit('user-1')
        assert result['allowed'] is True

    @patch('plan_check.get_user_plan', side_effect=Exception('DynamoDB down'))
    def test_check_access_condition_type_fails_open(self, mock_get_user_plan):
        from plan_check import check_access_condition_type

        result = check_access_condition_type('user-1', 'time_delayed')
        assert result['allowed'] is True


# ===================================================================
# Question-ID parsing
# ===================================================================

class TestParseQuestionId:
    """Unit tests for _parse_question_id."""

    def test_standard_format(self):
        from plan_check import _parse_question_id
        cat, level = _parse_question_id('life_story_reflections-general-L2-Q5')
        assert cat == 'life_story_reflections'
        assert level == 2

    def test_no_level_segment_defaults_to_1(self):
        from plan_check import _parse_question_id
        cat, level = _parse_question_id('life_story_reflections-general-Q1')
        assert cat == 'life_story_reflections'
        assert level == 1

    def test_high_level(self):
        from plan_check import _parse_question_id
        cat, level = _parse_question_id('values_and_emotions-core-L10-Q3')
        assert cat == 'values_and_emotions'
        assert level == 10

    def test_single_segment(self):
        from plan_check import _parse_question_id
        cat, level = _parse_question_id('standalone')
        assert cat == 'standalone'
        assert level == 1


# ===================================================================
# get_user_plan — DynamoDB interaction
# ===================================================================

class TestGetUserPlan:
    """Tests for get_user_plan DynamoDB reads."""

    @patch('plan_check._dynamodb')
    def test_returns_item_when_found(self, mock_dynamodb):
        from plan_check import get_user_plan

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {'userId': 'u1', 'planId': 'premium', 'status': 'active'},
        }
        result = get_user_plan('u1')
        assert result['planId'] == 'premium'

    @patch('plan_check._dynamodb')
    def test_returns_free_default_when_no_item(self, mock_dynamodb):
        from plan_check import get_user_plan

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        result = get_user_plan('u1')
        assert result['planId'] == 'free'
        assert result['userId'] == 'u1'

    @patch('plan_check._dynamodb')
    def test_returns_free_default_on_error(self, mock_dynamodb):
        from plan_check import get_user_plan

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.side_effect = Exception('timeout')

        result = get_user_plan('u1')
        assert result['planId'] == 'free'


# ===================================================================
# SSM plan loading
# ===================================================================

class TestPlanLoading:
    """Tests for _load_all_plans and _get_plan_definition."""

    @patch('plan_check._ssm')
    def test_load_all_plans_caches(self, mock_ssm):
        import plan_check

        mock_ssm.get_parameters.return_value = {
            'Parameters': [
                {'Name': '/soulreel/plans/free', 'Value': '{"planId":"free","maxLevel":1}'},
                {'Name': '/soulreel/plans/premium', 'Value': '{"planId":"premium","maxLevel":10}'},
            ],
        }
        plan_check._load_all_plans()

        assert plan_check._plans_loaded is True
        assert plan_check._plan_cache['free']['maxLevel'] == 1
        assert plan_check._plan_cache['premium']['maxLevel'] == 10

        # Second call should not hit SSM again
        mock_ssm.get_parameters.reset_mock()
        plan_check._load_all_plans()
        mock_ssm.get_parameters.assert_not_called()

    @patch('plan_check._ssm')
    def test_get_plan_definition_fallback_on_ssm_error(self, mock_ssm):
        import plan_check

        mock_ssm.get_parameters.side_effect = Exception('SSM down')
        result = plan_check._get_plan_definition('free')

        # Should return the hardcoded safe default
        assert result['planId'] == 'free'
        assert result['maxLevel'] == 1

    @patch('plan_check._ssm')
    def test_get_plan_definition_unknown_plan_returns_free_default(self, mock_ssm):
        import plan_check

        mock_ssm.get_parameters.return_value = {'Parameters': []}
        result = plan_check._get_plan_definition('enterprise')

        assert result['planId'] == 'free'
        assert result['maxLevel'] == 1


# ===================================================================
# Property-based tests (hypothesis)
# ===================================================================

class TestLevelGatingProperties:
    """Property tests: level gating is consistent for all (level, maxLevel) pairs."""

    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        level=st.integers(min_value=1, max_value=10),
        max_level=st.integers(min_value=1, max_value=10),
    )
    def test_level_le_max_allowed_else_denied(self, level, max_level):
        """For all L in 1..10 and M in 1..10: L <= M → allowed, L > M → denied."""
        from plan_check import check_question_category_access

        plan_def = dict(FREE_PLAN_DEF, maxLevel=max_level)

        with patch('plan_check.get_user_plan') as mock_gup, \
             patch('plan_check._get_plan_definition', return_value=plan_def):
            mock_gup.return_value = _make_subscription(plan_id='free')

            qid = f'life_story_reflections-general-L{level}-Q1'
            result = check_question_category_access('user-1', qid)

            if level <= max_level:
                assert result['allowed'] is True, (
                    f"Level {level} should be allowed with maxLevel {max_level}"
                )
            else:
                assert result['allowed'] is False, (
                    f"Level {level} should be denied with maxLevel {max_level}"
                )
                assert result['reason'] == 'question_level'

    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        level=st.integers(min_value=1, max_value=10),
        max_level_a=st.integers(min_value=1, max_value=10),
        max_level_b=st.integers(min_value=1, max_value=10),
    )
    def test_monotonic_increasing_max_level(self, level, max_level_a, max_level_b):
        """Increasing maxLevel only increases the allowed set (monotonic)."""
        assume(max_level_a <= max_level_b)

        from plan_check import check_question_category_access

        qid = f'life_story_reflections-general-L{level}-Q1'

        with patch('plan_check.get_user_plan') as mock_gup, \
             patch('plan_check._get_plan_definition') as mock_plan:
            mock_gup.return_value = _make_subscription(plan_id='free')

            # Check with lower maxLevel
            mock_plan.return_value = dict(FREE_PLAN_DEF, maxLevel=max_level_a)
            result_a = check_question_category_access('user-1', qid)

            # Check with higher maxLevel
            mock_plan.return_value = dict(FREE_PLAN_DEF, maxLevel=max_level_b)
            result_b = check_question_category_access('user-1', qid)

            # If allowed at lower maxLevel, must be allowed at higher maxLevel
            if result_a['allowed']:
                assert result_b['allowed'] is True, (
                    f"Level {level}: allowed at maxLevel={max_level_a} but denied "
                    f"at maxLevel={max_level_b} — violates monotonicity"
                )
