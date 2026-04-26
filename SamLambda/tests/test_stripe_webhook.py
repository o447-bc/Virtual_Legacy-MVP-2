"""
Unit tests for stripeWebhook/app.py.

Tests checkout.session.completed, customer.subscription.deleted,
invoice.payment_failed, invalid signature, and idempotency.

Uses pytest + unittest.mock. Shared layer modules (cors) are mocked
via sys.modules before importing the webhook app, since they live at
/opt/python in Lambda.
"""
import sys
import os
import json
from unittest.mock import patch, MagicMock, ANY

import pytest

# ---------------------------------------------------------------------------
# Mock shared layer modules BEFORE importing webhook app
# ---------------------------------------------------------------------------
mock_cors = MagicMock()
mock_cors.cors_headers.return_value = {
    'Access-Control-Allow-Origin': 'https://www.soulreel.net',
}
sys.modules['cors'] = mock_cors

# Mock stripe module if not installed in test environment
if 'stripe' not in sys.modules:
    mock_stripe_module = MagicMock()
    # Wire up the exception class so `except stripe.error.SignatureVerificationError` works
    mock_stripe_module.error.SignatureVerificationError = type(
        'SignatureVerificationError', (Exception,), {},
    )
    sys.modules['stripe'] = mock_stripe_module
    sys.modules['stripe.error'] = mock_stripe_module.error

# Ensure boto3.dynamodb.conditions is importable (used by the webhook app)
import boto3.dynamodb.conditions  # noqa: E402

# Add webhook function directory to sys.path so we can import app
_webhook_dir = os.path.join(
    os.path.dirname(__file__),
    '..', 'functions', 'billingFunctions', 'stripeWebhook',
)
sys.path.insert(0, _webhook_dir)

# Import with a unique name to avoid collision with billing app
import importlib
if 'webhook_app_module' in sys.modules:
    del sys.modules['webhook_app_module']
# Remove any cached 'app' that might be the billing app
if 'app' in sys.modules and hasattr(sys.modules['app'], '_ssm_cache') is False:
    del sys.modules['app']
import app as webhook_app  # noqa: E402
sys.modules['webhook_app_module'] = webhook_app


# ---------------------------------------------------------------------------
# Mock Stripe helpers
# ---------------------------------------------------------------------------

class MockStripeEvent:
    """Minimal Stripe event with attribute access (mirrors real Stripe objects)."""

    def __init__(self, event_type, data_object):
        self.id = 'evt_test_123'
        self.type = event_type
        self.data = MagicMock()
        self.data.object = data_object


class MockSubscription:
    """Minimal Stripe Subscription returned by stripe.Subscription.retrieve."""

    def __init__(self, price_id, current_period_end=1735689600):
        self.current_period_end = current_period_end
        self.items = MagicMock()
        price = MagicMock()
        price.id = price_id
        item = MagicMock()
        item.price = price
        self.items.data = [item]


class MockSession:
    """Minimal Stripe checkout Session."""

    def __init__(self, user_id='user-123', customer='cus_test_abc',
                 subscription='sub_test_xyz'):
        self.metadata = {'userId': user_id}
        self.customer = customer
        self.subscription = subscription


class MockSubscriptionObject:
    """Minimal Stripe subscription object for deleted / updated events."""

    def __init__(self, customer='cus_test_abc', status='active', price_id=None,
                 current_period_end=1735689600):
        self.customer = customer
        self.status = status
        self.current_period_end = current_period_end
        if price_id:
            self.items = MagicMock()
            price = MagicMock()
            price.id = price_id
            item = MagicMock()
            item.price = price
            self.items.data = [item]
        else:
            self.items = None


class MockInvoice:
    """Minimal Stripe invoice object for payment_failed events."""

    def __init__(self, customer='cus_test_abc'):
        self.customer = customer


# ---------------------------------------------------------------------------
# Helper to build API Gateway event
# ---------------------------------------------------------------------------

def _make_webhook_event(body='{}', sig='sig_test_123'):
    """Build a minimal API Gateway proxy event for the webhook endpoint."""
    return {
        'httpMethod': 'POST',
        'headers': {'Stripe-Signature': sig},
        'body': body,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_ssm_cache():
    """Clear module-level SSM cache between every test."""
    webhook_app._ssm_cache.clear()
    yield
    webhook_app._ssm_cache.clear()


@pytest.fixture()
def mock_dynamodb():
    """Patch boto3 dynamodb resource used by webhook app."""
    with patch.object(webhook_app, '_dynamodb') as m:
        mock_table = MagicMock()
        m.Table.return_value = mock_table
        yield mock_table


@pytest.fixture()
def mock_ssm():
    """Patch boto3 SSM client used by webhook app."""
    with patch.object(webhook_app, '_ssm') as m:
        m.get_parameter.return_value = {
            'Parameter': {'Value': 'whsec_test_fake'},
        }
        yield m


@pytest.fixture()
def mock_lambda_client():
    """Patch boto3 Lambda client used by webhook app."""
    with patch.object(webhook_app, '_lambda_client') as m:
        yield m


@pytest.fixture()
def mock_ses():
    """Patch boto3 SES client used by webhook app."""
    with patch.object(webhook_app, '_ses') as m:
        yield m


@pytest.fixture()
def mock_stripe():
    """Patch the stripe module used by webhook app."""
    with patch.object(webhook_app, 'stripe') as m:
        # Wire up the exception so signature verification failures work
        m.error.SignatureVerificationError = type(
            'SignatureVerificationError', (Exception,), {},
        )
        yield m


# ===================================================================
# 1. checkout.session.completed — monthly price
# ===================================================================

class TestCheckoutMonthly:
    """checkout.session.completed with monthly price → billingInterval=monthly."""

    def test_monthly_checkout_sets_billing_interval(
        self, mock_dynamodb, mock_ssm, mock_stripe, mock_lambda_client,
    ):
        session = MockSession()
        stripe_event = MockStripeEvent('checkout.session.completed', session)

        # Subscription.retrieve returns a sub with the monthly price ID
        mock_stripe.Subscription.retrieve.return_value = MockSubscription(
            price_id='price_1TQRZB6hMyNf0PnbX55g9YZy',
        )

        api_event = _make_webhook_event()
        webhook_app._handle_checkout_completed(stripe_event, api_event)

        update_call = mock_dynamodb.update_item.call_args
        expr_values = update_call.kwargs.get('ExpressionAttributeValues') or update_call[1]['ExpressionAttributeValues']

        assert expr_values[':bi'] == 'monthly'
        assert expr_values[':plan'] == 'premium'


# ===================================================================
# 2. checkout.session.completed — annual price
# ===================================================================

class TestCheckoutAnnual:
    """checkout.session.completed with annual price → billingInterval=annual."""

    def test_annual_checkout_sets_billing_interval(
        self, mock_dynamodb, mock_ssm, mock_stripe, mock_lambda_client,
    ):
        session = MockSession()
        stripe_event = MockStripeEvent('checkout.session.completed', session)

        mock_stripe.Subscription.retrieve.return_value = MockSubscription(
            price_id='price_1TQRZU6hMyNf0PnbmD3aQGbL',
        )

        api_event = _make_webhook_event()
        webhook_app._handle_checkout_completed(stripe_event, api_event)

        update_call = mock_dynamodb.update_item.call_args
        expr_values = update_call.kwargs.get('ExpressionAttributeValues') or update_call[1]['ExpressionAttributeValues']

        assert expr_values[':bi'] == 'annual'
        assert expr_values[':plan'] == 'premium'


# ===================================================================
# 3. checkout preserves existing fields (benefactorCount via if_not_exists)
# ===================================================================

class TestCheckoutPreservesFields:
    """checkout.session.completed preserves benefactorCount via if_not_exists."""

    def test_update_expression_uses_if_not_exists_for_benefactor_count(
        self, mock_dynamodb, mock_ssm, mock_stripe, mock_lambda_client,
    ):
        session = MockSession()
        stripe_event = MockStripeEvent('checkout.session.completed', session)

        mock_stripe.Subscription.retrieve.return_value = MockSubscription(
            price_id='price_1TQRZB6hMyNf0PnbX55g9YZy',
        )

        api_event = _make_webhook_event()
        webhook_app._handle_checkout_completed(stripe_event, api_event)

        update_call = mock_dynamodb.update_item.call_args
        update_expr = update_call.kwargs.get('UpdateExpression') or update_call[1]['UpdateExpression']

        assert 'benefactorCount = if_not_exists(benefactorCount, :zero)' in update_expr


# ===================================================================
# 4. customer.subscription.deleted → planId=free, status=canceled
# ===================================================================

class TestSubscriptionDeleted:
    """customer.subscription.deleted sets planId=free, status=canceled."""

    def test_deleted_sets_free_and_canceled(
        self, mock_dynamodb, mock_ssm, mock_stripe, mock_ses, mock_lambda_client,
    ):
        sub_obj = MockSubscriptionObject(customer='cus_test_abc')
        stripe_event = MockStripeEvent('customer.subscription.deleted', sub_obj)

        # GSI lookup returns a user
        mock_dynamodb.query.return_value = {
            'Items': [{'userId': 'user-456', 'email': 'test@example.com'}],
        }

        api_event = _make_webhook_event()
        webhook_app._handle_subscription_deleted(stripe_event, api_event)

        update_call = mock_dynamodb.update_item.call_args
        expr_values = update_call.kwargs.get('ExpressionAttributeValues') or update_call[1]['ExpressionAttributeValues']

        assert expr_values[':plan'] == 'free'
        assert expr_values[':status'] == 'canceled'


# ===================================================================
# 5. invoice.payment_failed → status=past_due
# ===================================================================

class TestPaymentFailed:
    """invoice.payment_failed sets status=past_due."""

    def test_payment_failed_sets_past_due(
        self, mock_dynamodb, mock_ssm, mock_stripe,
    ):
        invoice_obj = MockInvoice(customer='cus_test_abc')
        stripe_event = MockStripeEvent('invoice.payment_failed', invoice_obj)

        # GSI lookup returns a user
        mock_dynamodb.query.return_value = {
            'Items': [{'userId': 'user-789'}],
        }

        api_event = _make_webhook_event()
        webhook_app._handle_payment_failed(stripe_event, api_event)

        update_call = mock_dynamodb.update_item.call_args
        expr_values = update_call.kwargs.get('ExpressionAttributeValues') or update_call[1]['ExpressionAttributeValues']

        assert expr_values[':status'] == 'past_due'


# ===================================================================
# 6. Invalid signature → HTTP 400, no DB writes
# ===================================================================

class TestInvalidSignature:
    """Invalid Stripe signature → 400 response, no DynamoDB calls."""

    def test_invalid_signature_returns_400_no_db(
        self, mock_dynamodb, mock_ssm, mock_stripe,
    ):
        # construct_event raises SignatureVerificationError
        mock_stripe.Webhook.construct_event.side_effect = (
            mock_stripe.error.SignatureVerificationError('bad sig')
        )

        api_event = _make_webhook_event(body='{"bad": "payload"}', sig='bad_sig')
        resp = webhook_app.lambda_handler(api_event, None)

        assert resp['statusCode'] == 400
        body = json.loads(resp['body'])
        assert 'Invalid signature' in body['error']

        # No DynamoDB writes should have occurred
        mock_dynamodb.update_item.assert_not_called()
        mock_dynamodb.put_item.assert_not_called()


# ===================================================================
# 7. Idempotency — processing same checkout event twice → same state
# ===================================================================

class TestIdempotency:
    """Processing the same checkout event twice produces identical update_item args."""

    def test_duplicate_checkout_produces_same_update(
        self, mock_dynamodb, mock_ssm, mock_stripe, mock_lambda_client,
    ):
        session = MockSession(user_id='user-idem')
        stripe_event = MockStripeEvent('checkout.session.completed', session)

        mock_stripe.Subscription.retrieve.return_value = MockSubscription(
            price_id='price_1TQRZB6hMyNf0PnbX55g9YZy',
        )

        api_event = _make_webhook_event()

        # Freeze time so updatedAt is deterministic
        with patch.object(webhook_app, 'datetime') as mock_dt:
            mock_dt.now.return_value = MagicMock(
                isoformat=MagicMock(return_value='2025-01-01T00:00:00+00:00'),
            )
            mock_dt.fromtimestamp = MagicMock(
                return_value=MagicMock(
                    isoformat=MagicMock(return_value='2025-01-01T12:00:00+00:00'),
                ),
            )
            mock_dt.side_effect = lambda *a, **kw: MagicMock()

            webhook_app._handle_checkout_completed(stripe_event, api_event)
            first_call = mock_dynamodb.update_item.call_args

            mock_dynamodb.reset_mock()

            webhook_app._handle_checkout_completed(stripe_event, api_event)
            second_call = mock_dynamodb.update_item.call_args

        assert first_call == second_call
