"""
Unit tests for preview question logic in plan_check.py.

Tests the _has_completed_preview helper and the preview check path
inside check_question_category_access.
"""
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure shared python layer is importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..', '..', 'functions', 'shared', 'python'),
)

import pytest


# ---------------------------------------------------------------------------
# Fixtures — reload plan_check with a clean SSM cache for each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_plan_cache():
    """Clear the module-level SSM cache between tests."""
    import plan_check
    plan_check._plan_cache.clear()
    plan_check._plans_loaded = False
    yield
    plan_check._plan_cache.clear()
    plan_check._plans_loaded = False


FREE_PLAN_DEF = {
    'planId': 'free',
    'allowedQuestionCategories': ['life_story_reflections_L1'],
    'maxBenefactors': 2,
    'accessConditionTypes': ['immediate'],
    'features': ['basic'],
    'previewQuestions': [
        'life_events-milestones-L1-Q1',
        'psych_values_emotions-core-L1-Q1',
    ],
}


def _mock_get_plan_definition(plan_id):
    """Return the free plan definition with previewQuestions."""
    if plan_id == 'free':
        return dict(FREE_PLAN_DEF)
    return {
        'planId': 'premium',
        'allowedQuestionCategories': ['life_story_reflections', 'life_events', 'psych_values_emotions'],
        'maxBenefactors': -1,
    }


# ---------------------------------------------------------------------------
# Tests for _has_completed_preview
# ---------------------------------------------------------------------------

class TestHasCompletedPreview:
    """Tests for the _has_completed_preview helper."""

    @patch('plan_check._dynamodb')
    def test_returns_true_when_item_exists(self, mock_dynamodb):
        from plan_check import _has_completed_preview

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            'Item': {'userId': 'u1', 'questionId': 'q1'},
        }

        assert _has_completed_preview('u1', 'q1') is True
        mock_table.get_item.assert_called_once_with(
            Key={'userId': 'u1', 'questionId': 'q1'},
        )

    @patch('plan_check._dynamodb')
    def test_returns_false_when_no_item(self, mock_dynamodb):
        from plan_check import _has_completed_preview

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        assert _has_completed_preview('u1', 'q1') is False

    @patch('plan_check._dynamodb')
    def test_returns_false_on_error(self, mock_dynamodb):
        """Fail-open: errors should return False (allow the preview)."""
        from plan_check import _has_completed_preview

        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.side_effect = Exception('DynamoDB error')

        assert _has_completed_preview('u1', 'q1') is False


# ---------------------------------------------------------------------------
# Tests for preview path in check_question_category_access
# ---------------------------------------------------------------------------

class TestPreviewAccessInCheckQuestionCategoryAccess:
    """Tests for the preview question check inside check_question_category_access."""

    @patch('plan_check._has_completed_preview', return_value=False)
    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_preview_question_allowed_for_free_user(
        self, mock_get_user_plan, mock_get_plan_def, mock_completed
    ):
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is True
        assert result['isPreview'] is True
        assert result['reason'] is None

    @patch('plan_check._has_completed_preview', return_value=True)
    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_completed_preview_denied(
        self, mock_get_user_plan, mock_get_plan_def, mock_completed
    ):
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_non_preview_locked_question_denied(
        self, mock_get_user_plan, mock_get_plan_def
    ):
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_events-career-L1-Q5')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_premium_user_no_preview_flag(
        self, mock_get_user_plan, mock_get_plan_def
    ):
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'premium', 'status': 'active',
        }

        result = check_question_category_access('u1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is True
        assert 'isPreview' not in result

    @patch('plan_check._get_plan_definition', side_effect=_mock_get_plan_definition)
    @patch('plan_check.get_user_plan')
    def test_allowed_category_still_works(
        self, mock_get_user_plan, mock_get_plan_def
    ):
        """Normal allowed category access should not be affected."""
        from plan_check import check_question_category_access

        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_story_reflections-general-L1-Q3')

        assert result['allowed'] is True
        assert 'isPreview' not in result

    @patch('plan_check._has_completed_preview', return_value=False)
    @patch('plan_check._get_plan_definition')
    @patch('plan_check.get_user_plan')
    def test_preview_check_covers_level_too_high_deny(
        self, mock_get_user_plan, mock_get_plan_def, mock_completed
    ):
        """Preview check should intercept the 'level too high' deny path too."""
        from plan_check import check_question_category_access

        # Plan allows L1 only, question is L2 but is in preview list
        mock_get_plan_def.return_value = {
            'planId': 'free',
            'allowedQuestionCategories': ['life_story_reflections_L1'],
            'previewQuestions': ['life_story_reflections-deep-L2-Q1'],
        }
        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_story_reflections-deep-L2-Q1')

        assert result['allowed'] is True
        assert result['isPreview'] is True

    @patch('plan_check._get_plan_definition')
    @patch('plan_check.get_user_plan')
    def test_no_preview_questions_field_defaults_empty(
        self, mock_get_user_plan, mock_get_plan_def
    ):
        """Missing previewQuestions in plan def should default to empty list."""
        from plan_check import check_question_category_access

        mock_get_plan_def.return_value = {
            'planId': 'free',
            'allowedQuestionCategories': ['life_story_reflections_L1'],
            # No previewQuestions field
        }
        mock_get_user_plan.return_value = {
            'userId': 'u1', 'planId': 'free', 'status': 'free',
        }

        result = check_question_category_access('u1', 'life_events-milestones-L1-Q1')

        assert result['allowed'] is False
        assert result['reason'] == 'question_category'
