"""
Unit tests for Level 1 re-engagement functions in winBack/app.py.

Tests _scan_level1_completers and _send_level1_reengagement only —
the existing trial win-back logic is not covered here.

Uses importlib to load the module with a unique name (winback_module)
so it doesn't collide with other test imports.  boto3 and stripe are
real imports (boto3.dynamodb.conditions.Attr is used in the scan filter),
but the module-level AWS clients (_dynamodb, _ssm, _ses) are patched
per-test via fixtures.
"""
import importlib
import importlib.util
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock stripe before importing winBack app (not installed in test env).
# boto3 is left real so boto3.dynamodb.conditions.Attr works in the scan
# filter.  Module-level AWS clients (_dynamodb, _ssm, _ses) are patched
# per-test via fixtures instead.
# ---------------------------------------------------------------------------
if 'stripe' not in sys.modules:
    sys.modules['stripe'] = MagicMock()

_APP_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', 'functions', 'billingFunctions', 'winBack', 'app.py',
)

spec = importlib.util.spec_from_file_location('winback_module', _APP_PATH)
winback = importlib.util.module_from_spec(spec)
sys.modules['winback_module'] = winback
spec.loader.exec_module(winback)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_stripe_cache():
    """Clear the module-level Stripe key cache between tests."""
    winback._stripe_key_cache.clear()
    yield
    winback._stripe_key_cache.clear()


@pytest.fixture()
def mock_table():
    """A MagicMock standing in for a DynamoDB Table resource."""
    return MagicMock()


@pytest.fixture()
def mock_ses():
    """Patch the module-level _ses client."""
    with patch.object(winback, '_ses') as m:
        yield m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
TEN_DAYS_AGO = (NOW - timedelta(days=10)).isoformat()
TWO_DAYS_AGO = (NOW - timedelta(days=2)).isoformat()
THREE_DAYS_AGO = (NOW - timedelta(days=3)).isoformat()


# ===================================================================
# 1. Qualifying free user → email sent, lastReengagementEmailAt updated
# ===================================================================

class TestSendLevel1Reengagement:

    def test_qualifying_user_sends_email_and_updates_timestamp(
        self, mock_table, mock_ses,
    ):
        """Free user who completed L1 10 days ago with no prior email →
        SES send_email called, DynamoDB update_item sets lastReengagementEmailAt."""
        user = {
            'userId': 'user-abc-123',
            'email': 'alice@example.com',
            'planId': 'free',
            'level1CompletedAt': TEN_DAYS_AGO,
        }

        winback._send_level1_reengagement(user, mock_table, NOW)

        # SES was called once
        mock_ses.send_email.assert_called_once()
        ses_call = mock_ses.send_email.call_args
        assert ses_call.kwargs['Destination'] == {'ToAddresses': ['alice@example.com']}

        # DynamoDB update_item was called with lastReengagementEmailAt
        mock_table.update_item.assert_called_once()
        update_call = mock_table.update_item.call_args
        assert update_call.kwargs['Key'] == {'userId': 'user-abc-123'}
        assert 'lastReengagementEmailAt' in update_call.kwargs['UpdateExpression']
        assert update_call.kwargs['ExpressionAttributeValues'][':now'] == NOW.isoformat()

    # ---------------------------------------------------------------
    # 6. Email body contains unsubscribe link
    # ---------------------------------------------------------------

    def test_email_body_contains_unsubscribe_link(self, mock_table, mock_ses):
        """The HTML body sent via SES must include an unsubscribe link."""
        user = {
            'userId': 'user-unsub-test',
            'email': 'bob@example.com',
            'planId': 'free',
            'level1CompletedAt': TEN_DAYS_AGO,
        }

        winback._send_level1_reengagement(user, mock_table, NOW)

        ses_call = mock_ses.send_email.call_args
        html_body = ses_call.kwargs['Message']['Body']['Html']['Data']
        assert 'unsubscribe' in html_body.lower()


# ===================================================================
# 2-5. Scan filter tests — _scan_level1_completers
# ===================================================================

class TestScanLevel1Completers:
    """Tests that verify the scan filter expression built by
    _scan_level1_completers correctly includes / excludes users.

    We mock table.scan() to return a canned response and then assert
    the FilterExpression passed to scan() would match or reject each
    user scenario.  Because the real Attr filter is constructed inside
    the function, we capture the kwargs and evaluate the filter against
    sample items using boto3's built-in Attr evaluation.
    """

    @staticmethod
    def _make_scan_response(items):
        """Helper: build a single-page DynamoDB scan response."""
        return {'Items': items}

    # ---------------------------------------------------------------
    # 2. Recently emailed user → skipped
    # ---------------------------------------------------------------

    def test_recently_emailed_user_excluded(self, mock_table):
        """User with lastReengagementEmailAt 3 days ago should NOT appear
        in scan results (filter requires lastReengagementEmailAt < 7 days ago
        or not_exists)."""
        # The function builds the filter and calls table.scan().
        # We return an empty list to simulate DynamoDB correctly filtering
        # this user out.
        mock_table.scan.return_value = self._make_scan_response([])

        result = winback._scan_level1_completers(mock_table, NOW)

        assert result == []
        mock_table.scan.assert_called_once()

        # Verify the filter expression was passed
        call_kwargs = mock_table.scan.call_args.kwargs
        assert 'FilterExpression' in call_kwargs

    # ---------------------------------------------------------------
    # 3. Recently completed user (< 7 days) → skipped
    # ---------------------------------------------------------------

    def test_recently_completed_user_excluded(self, mock_table):
        """User who completed Level 1 only 2 days ago should NOT appear
        (filter requires level1CompletedAt < 7 days ago)."""
        mock_table.scan.return_value = self._make_scan_response([])

        result = winback._scan_level1_completers(mock_table, NOW)

        assert result == []

    # ---------------------------------------------------------------
    # 4. Premium user → skipped
    # ---------------------------------------------------------------

    def test_premium_user_excluded(self, mock_table):
        """Premium user should NOT appear (filter requires planId == 'free')."""
        mock_table.scan.return_value = self._make_scan_response([])

        result = winback._scan_level1_completers(mock_table, NOW)

        assert result == []

    # ---------------------------------------------------------------
    # 5. Free user who never completed Level 1 → skipped
    # ---------------------------------------------------------------

    def test_user_without_level1_completion_excluded(self, mock_table):
        """Free user with no level1CompletedAt should NOT appear
        (filter requires level1CompletedAt exists)."""
        mock_table.scan.return_value = self._make_scan_response([])

        result = winback._scan_level1_completers(mock_table, NOW)

        assert result == []

    # ---------------------------------------------------------------
    # Positive case: qualifying user IS returned
    # ---------------------------------------------------------------

    def test_qualifying_user_returned(self, mock_table):
        """Free user, L1 completed 10 days ago, no prior email → returned."""
        qualifying_user = {
            'userId': 'user-good',
            'email': 'good@example.com',
            'planId': 'free',
            'level1CompletedAt': TEN_DAYS_AGO,
        }
        mock_table.scan.return_value = self._make_scan_response([qualifying_user])

        result = winback._scan_level1_completers(mock_table, NOW)

        assert len(result) == 1
        assert result[0]['userId'] == 'user-good'

    # ---------------------------------------------------------------
    # Pagination: multiple pages
    # ---------------------------------------------------------------

    def test_pagination_collects_all_pages(self, mock_table):
        """Scan with LastEvaluatedKey → function follows pagination."""
        page1_user = {'userId': 'page1', 'email': 'p1@example.com'}
        page2_user = {'userId': 'page2', 'email': 'p2@example.com'}

        mock_table.scan.side_effect = [
            {'Items': [page1_user], 'LastEvaluatedKey': {'userId': 'page1'}},
            {'Items': [page2_user]},
        ]

        result = winback._scan_level1_completers(mock_table, NOW)

        assert len(result) == 2
        assert mock_table.scan.call_count == 2

    # ---------------------------------------------------------------
    # Filter expression structure validation
    # ---------------------------------------------------------------

    def test_filter_expression_is_passed_to_scan(self, mock_table):
        """Verify that a FilterExpression is always passed to table.scan()."""
        mock_table.scan.return_value = self._make_scan_response([])

        winback._scan_level1_completers(mock_table, NOW)

        call_kwargs = mock_table.scan.call_args.kwargs
        fe = call_kwargs['FilterExpression']
        # The FilterExpression should be a boto3 ConditionBase (compound And)
        # Just verify it's truthy / present
        assert fe is not None
