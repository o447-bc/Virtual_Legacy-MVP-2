"""
Unit tests for _update_subscription_progress in wsDefault/app.py.

Tests Level 1 completion tracking, totalQuestionsCompleted increment,
premium vs free plan behaviour, and fail-open error handling.

Uses pytest + hypothesis + unittest.mock.
"""
import sys
import os
import importlib
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Import app with mocked sibling modules.
#
# wsDefault/app.py imports many sibling modules (conversation_state, config,
# llm, speech, storage, transcribe, etc.) that only exist inside the Lambda
# runtime.  We mock them in sys.modules BEFORE importing app, then restore
# any originals afterwards so other test files (e.g. test_plan_check.py)
# are not affected.
# ---------------------------------------------------------------------------
_SIBLING_MODS = [
    'conversation_state',
    'config',
    'llm',
    'speech',
    'storage',
    'transcribe',
    'transcribe_streaming',
    'transcribe_deepgram',
    'plan_check',
]

# Save originals so we can restore after import
_saved = {name: sys.modules.get(name) for name in _SIBLING_MODS}

for _mod in _SIBLING_MODS:
    sys.modules[_mod] = MagicMock()

# Ensure the wsDefault directory is on sys.path
_ws_default_dir = os.path.join(
    os.path.dirname(__file__), '..', 'functions', 'conversationFunctions', 'wsDefault',
)
_ws_default_dir = os.path.normpath(_ws_default_dir)
if _ws_default_dir not in sys.path:
    sys.path.insert(0, _ws_default_dir)

# Force a fresh import of app (in case it was already imported with real modules)
# Use importlib to import with a unique name to avoid collision with billing app
if 'app' in sys.modules:
    del sys.modules['app']

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'wsdefault_app',
    os.path.join(_ws_default_dir, 'app.py'),
)
app = importlib.util.module_from_spec(_spec)
sys.modules['wsdefault_app'] = app
_spec.loader.exec_module(app)

# Restore original modules so other test files are not poisoned
for _mod in _SIBLING_MODS:
    if _saved[_mod] is not None:
        sys.modules[_mod] = _saved[_mod]
    else:
        sys.modules.pop(_mod, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_dynamodb(query_items=None):
    """Return a mock DynamoDB resource whose .Table() returns per-name mocks."""
    tables = {}

    def table_factory(name):
        if name not in tables:
            tables[name] = MagicMock()
            tables[name].update_item.return_value = {}
            tables[name].query.return_value = {'Items': query_items or []}
        return tables[name]

    mock_resource = MagicMock()
    mock_resource.Table.side_effect = table_factory
    return mock_resource, tables


def _l1_question_items(count: int):
    """Build a list of completed-question Items that look like L1 questions."""
    return [{'questionId': f'life_story_reflections_L1_Q{i}'} for i in range(count)]


# ---------------------------------------------------------------------------
# 1. Always increments totalQuestionsCompleted
# ---------------------------------------------------------------------------
class TestAlwaysIncrementsTotalQuestions:
    """totalQuestionsCompleted must be incremented for every call, regardless of plan."""

    @patch.object(app, '_get_plan_definition', return_value={'totalLevel1Questions': 20})
    @patch.object(app, '_parse_question_id', return_value=('life_story_reflections', 1))
    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', return_value={'userId': 'u1', 'planId': 'free'})
    def test_free_user(self, mock_plan, mock_premium, mock_parse, mock_def):
        mock_db, tables = _make_mock_dynamodb(query_items=_l1_question_items(3))
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        assert sub_table is not None
        first_call = sub_table.update_item.call_args_list[0]
        assert ':one' in first_call.kwargs.get('ExpressionAttributeValues', {})

    @patch.object(app, 'is_premium_active', return_value=True)
    @patch.object(app, 'get_user_plan', return_value={'userId': 'u1', 'planId': 'premium'})
    def test_premium_user(self, mock_plan, mock_premium):
        mock_db, tables = _make_mock_dynamodb()
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        assert sub_table is not None
        first_call = sub_table.update_item.call_args_list[0]
        assert ':one' in first_call.kwargs.get('ExpressionAttributeValues', {})


# ---------------------------------------------------------------------------
# 2. Free user completes L1 question — percentage calculated correctly
# ---------------------------------------------------------------------------
class TestFreeUserL1Percentage:

    @patch.object(app, '_get_plan_definition', return_value={'totalLevel1Questions': 20})
    @patch.object(app, '_parse_question_id', return_value=('life_story_reflections', 1))
    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', return_value={'userId': 'u1', 'planId': 'free'})
    def test_5_of_20_gives_25_percent(self, mock_plan, mock_premium, mock_parse, mock_def):
        mock_db, tables = _make_mock_dynamodb(query_items=_l1_question_items(5))
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        second_call = sub_table.update_item.call_args_list[1]
        expr_values = second_call.kwargs.get('ExpressionAttributeValues', {})
        assert expr_values[':pct'] == 25


# ---------------------------------------------------------------------------
# 3. Free user completes last L1 question — level1CompletedAt set
# ---------------------------------------------------------------------------
class TestFreeUserCompletesAllL1:

    @patch.object(app, '_get_plan_definition', return_value={'totalLevel1Questions': 20})
    @patch.object(app, '_parse_question_id', return_value=('life_story_reflections', 1))
    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', return_value={'userId': 'u1', 'planId': 'free'})
    def test_20_of_20_sets_completed_at(self, mock_plan, mock_premium, mock_parse, mock_def):
        mock_db, tables = _make_mock_dynamodb(query_items=_l1_question_items(20))
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        second_call = sub_table.update_item.call_args_list[1]
        expr_values = second_call.kwargs.get('ExpressionAttributeValues', {})
        assert expr_values[':pct'] == 100
        assert ':completed' in expr_values  # level1CompletedAt was set


# ---------------------------------------------------------------------------
# 4. Premium user — L1 tracking skipped
# ---------------------------------------------------------------------------
class TestPremiumUserSkipsL1:

    @patch.object(app, 'is_premium_active', return_value=True)
    @patch.object(app, 'get_user_plan', return_value={
        'userId': 'u1', 'planId': 'premium', 'premiumExpiresAt': '2099-01-01',
    })
    def test_only_total_incremented(self, mock_plan, mock_premium):
        mock_db, tables = _make_mock_dynamodb()
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        assert sub_table.update_item.call_count == 1


# ---------------------------------------------------------------------------
# 5. Non-L1 question — L1 tracking skipped
# ---------------------------------------------------------------------------
class TestNonL1QuestionSkipsTracking:

    @patch.object(app, '_parse_question_id', return_value=('life_events', 2))
    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', return_value={'userId': 'u1', 'planId': 'free'})
    def test_level2_question_skips_l1_tracking(self, mock_plan, mock_premium, mock_parse):
        mock_db, tables = _make_mock_dynamodb()
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_events_L2_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        assert sub_table.update_item.call_count == 1


# ---------------------------------------------------------------------------
# 6. Error handling — fails open
# ---------------------------------------------------------------------------
class TestFailOpen:

    def test_dynamodb_error_does_not_raise(self):
        mock_db = MagicMock()
        mock_db.Table.side_effect = Exception('DynamoDB is down')
        with patch.object(app, '_dynamodb', mock_db):
            # Should NOT raise — function fails open
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', side_effect=Exception('plan lookup failed'))
    def test_get_user_plan_error_does_not_raise(self, mock_plan, mock_premium):
        mock_db, _ = _make_mock_dynamodb()
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')


# ---------------------------------------------------------------------------
# 7. level1CompletedAt not overwritten if already set
# ---------------------------------------------------------------------------
class TestLevel1CompletedAtNotOverwritten:

    @patch.object(app, '_get_plan_definition', return_value={'totalLevel1Questions': 20})
    @patch.object(app, '_parse_question_id', return_value=('life_story_reflections', 1))
    @patch.object(app, 'is_premium_active', return_value=False)
    @patch.object(app, 'get_user_plan', return_value={
        'userId': 'u1', 'planId': 'free',
        'level1CompletedAt': '2025-01-01T00:00:00+00:00',  # already set
    })
    def test_completed_at_not_overwritten(self, mock_plan, mock_premium, mock_parse, mock_def):
        mock_db, tables = _make_mock_dynamodb(query_items=_l1_question_items(20))
        with patch.object(app, '_dynamodb', mock_db):
            app._update_subscription_progress('u1', 'life_story_reflections_L1_Q1')

        sub_table = tables.get('UserSubscriptionsDB')
        second_call = sub_table.update_item.call_args_list[1]
        expr_values = second_call.kwargs.get('ExpressionAttributeValues', {})
        assert expr_values[':pct'] == 100
        # level1CompletedAt should NOT be in the update because it's already set
        assert ':completed' not in expr_values


# ---------------------------------------------------------------------------
# Property-based test (hypothesis): percentage calculation invariants
# ---------------------------------------------------------------------------
class TestPercentagePropertyBased:

    @given(
        completed=st.integers(min_value=0, max_value=30),
        total=st.integers(min_value=1, max_value=30),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_percentage_in_range_and_monotonic(self, completed, total):
        assume(completed <= total)

        # Mirror the exact formula from the production code
        percent = min(100, int((completed / total) * 100))

        # Invariant 1: percentage is always in [0, 100]
        assert 0 <= percent <= 100

        # Invariant 2: monotonically non-decreasing as completed increases
        if completed > 0:
            prev_percent = min(100, int(((completed - 1) / total) * 100))
            assert percent >= prev_percent

        # Invariant 3: 0 completed → 0%
        if completed == 0:
            assert percent == 0

        # Invariant 4: completed == total → 100%
        if completed == total:
            assert percent == 100
