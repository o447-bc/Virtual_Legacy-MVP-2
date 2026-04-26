"""
Comprehensive unit tests for billing/app.py (V2 pricing model).

Tests status, checkout, plans, portal, and coupon endpoints.

Uses pytest + unittest.mock. Shared layer modules (cors, responses,
structured_logger) are mocked via sys.modules before importing the
billing app, since they live at /opt/python in Lambda.
"""
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, ANY

import pytest

# ---------------------------------------------------------------------------
# Mock shared layer modules BEFORE importing billing app
# ---------------------------------------------------------------------------
mock_cors = MagicMock()
mock_cors.cors_headers.return_value = {
    'Access-Control-Allow-Origin': 'https://www.soulreel.net',
}
sys.modules['cors'] = mock_cors

mock_responses = MagicMock()
mock_responses.error_response.return_value = {
    'statusCode': 500,
    'headers': {'Access-Control-Allow-Origin': 'https://www.soulreel.net'},
    'body': json.dumps({'error': 'Internal server error'}),
}
sys.modules['responses'] = mock_responses

mock_structured_logger = MagicMock()
mock_structured_logger.StructuredLog.return_value = MagicMock()
sys.modules['structured_logger'] = mock_structured_logger

# Mock stripe module if not installed in test environment
if 'stripe' not in sys.modules:
    sys.modules['stripe'] = MagicMock()

# Add billing function directory to sys.path so we can import app
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), '..', 'functions', 'billingFunctions', 'billing',
    ),
)

import app as billing_app  # noqa: E402


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
    'foundingMemberCouponCode': 'FOUNDING50',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    path='/billing/status',
    method='GET',
    body=None,
    user_id='user-123',
):
    """Build a minimal API Gateway proxy event."""
    event = {
        'path': path,
        'httpMethod': method,
        'headers': {'Origin': 'https://www.soulreel.net'},
        'body': json.dumps(body) if body is not None else None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                },
            },
        },
    }
    return event


def _parse_body(response: dict) -> dict:
    """Parse the JSON body from a Lambda response."""
    return json.loads(response['body'])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_caches():
    """Clear module-level SSM caches between every test."""
    billing_app._plan_cache.clear()
    billing_app._plans_loaded = False
    billing_app._stripe_key_cache.clear()
    yield
    billing_app._plan_cache.clear()
    billing_app._plans_loaded = False
    billing_app._stripe_key_cache.clear()


@pytest.fixture()
def mock_dynamodb():
    """Patch boto3 dynamodb resource used by billing app."""
    with patch.object(billing_app, '_dynamodb') as m:
        mock_table = MagicMock()
        m.Table.return_value = mock_table
        yield mock_table


class _ParameterNotFound(Exception):
    """Stand-in for botocore's ParameterNotFound client exception."""
    pass


@pytest.fixture()
def mock_ssm():
    """Patch boto3 SSM client used by billing app."""
    with patch.object(billing_app, '_ssm') as m:
        # Wire up a real exception class so `except _ssm.exceptions.ParameterNotFound` works
        m.exceptions.ParameterNotFound = _ParameterNotFound

        # Default: return free + premium plan definitions
        m.get_parameters.return_value = {
            'Parameters': [
                {'Name': '/soulreel/plans/free', 'Value': json.dumps(FREE_PLAN_DEF)},
                {'Name': '/soulreel/plans/premium', 'Value': json.dumps(PREMIUM_PLAN_DEF)},
            ],
        }
        # Default: return a fake stripe key
        m.get_parameter.return_value = {
            'Parameter': {'Value': 'sk_test_fake123'},
        }
        yield m


@pytest.fixture()
def mock_stripe():
    """Patch the stripe module used by billing app."""
    with patch.object(billing_app, 'stripe') as m:
        # Stripe Customer.create
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test_abc'
        m.Customer.create.return_value = mock_customer

        # Stripe checkout.Session.create
        mock_checkout_session = MagicMock()
        mock_checkout_session.url = 'https://checkout.stripe.com/session/test123'
        m.checkout.Session.create.return_value = mock_checkout_session

        # Stripe billing_portal.Session.create
        mock_portal_session = MagicMock()
        mock_portal_session.url = 'https://billing.stripe.com/portal/test456'
        m.billing_portal.Session.create.return_value = mock_portal_session

        yield m


# ===================================================================
# Status endpoint — handle_status
# ===================================================================

class TestHandleStatus:
    """Tests for GET /billing/status."""

    def test_no_record_returns_free_plan(self, mock_dynamodb, mock_ssm):
        """User with no subscription record → free plan defaults."""
        mock_dynamodb.get_item.return_value = {}

        event = _make_event(path='/billing/status', method='GET')
        resp = billing_app.handle_status(event, 'user-123')
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['planId'] == 'free'
        assert body['status'] == 'active'
        assert body['level1CompletionPercent'] == 0
        assert body['billingInterval'] is None
        assert body['totalQuestionsCompleted'] == 0

    def test_no_record_excludes_removed_fields(self, mock_dynamodb, mock_ssm):
        """Free plan response does NOT include V1 fields."""
        mock_dynamodb.get_item.return_value = {}

        event = _make_event(path='/billing/status', method='GET')
        resp = billing_app.handle_status(event, 'user-123')
        body = _parse_body(resp)

        assert 'conversationsThisWeek' not in body
        assert 'weekResetDate' not in body
        assert 'trialExpiresAt' not in body

    def test_premium_record_returns_correct_fields(self, mock_dynamodb, mock_ssm):
        """User with premium record → correct planId, status, completion, interval."""
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'userId': 'user-123',
                'planId': 'premium',
                'status': 'active',
                'level1CompletionPercent': 75,
                'billingInterval': 'monthly',
                'totalQuestionsCompleted': 42,
                'benefactorCount': 3,
                'currentPeriodEnd': '2026-04-01T00:00:00+00:00',
            },
        }

        event = _make_event(path='/billing/status', method='GET')
        resp = billing_app.handle_status(event, 'user-123')
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['planId'] == 'premium'
        assert body['status'] == 'active'
        assert body['level1CompletionPercent'] == 75
        assert body['billingInterval'] == 'monthly'
        assert body['totalQuestionsCompleted'] == 42
        assert body['benefactorCount'] == 3

    def test_free_plan_fallback_limits(self, mock_dynamodb, mock_ssm):
        """Free plan fallback has maxLevel=1, maxBenefactors=1."""
        # Force SSM to return nothing so fallback kicks in
        mock_ssm.get_parameters.return_value = {'Parameters': []}

        mock_dynamodb.get_item.return_value = {}

        event = _make_event(path='/billing/status', method='GET')
        resp = billing_app.handle_status(event, 'user-123')
        body = _parse_body(resp)

        assert body['planLimits']['maxLevel'] == 1
        assert body['planLimits']['maxBenefactors'] == 1
        assert body['freePlanLimits']['maxLevel'] == 1
        assert body['freePlanLimits']['maxBenefactors'] == 1


# ===================================================================
# Checkout endpoint — handle_create_checkout
# ===================================================================

class TestHandleCreateCheckout:
    """Tests for POST /billing/create-checkout-session."""

    def test_valid_price_creates_session(self, mock_dynamodb, mock_ssm, mock_stripe):
        """Valid priceId → creates Stripe Customer + Checkout Session, returns sessionUrl."""
        # No existing record → will create new customer
        mock_dynamodb.get_item.return_value = {'Item': {}}

        event = _make_event(
            path='/billing/create-checkout-session',
            method='POST',
            body={'priceId': 'price_test_monthly'},
        )
        log = MagicMock()
        resp = billing_app.handle_create_checkout(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['sessionUrl'] == 'https://checkout.stripe.com/session/test123'
        mock_stripe.Customer.create.assert_called_once()
        mock_stripe.checkout.Session.create.assert_called_once()

    def test_missing_price_id_returns_400(self, mock_dynamodb, mock_ssm, mock_stripe):
        """Missing priceId → HTTP 400."""
        event = _make_event(
            path='/billing/create-checkout-session',
            method='POST',
            body={},
        )
        log = MagicMock()
        resp = billing_app.handle_create_checkout(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 400
        assert 'Missing priceId' in body['error']

    def test_coupon_id_sets_discounts(self, mock_dynamodb, mock_ssm, mock_stripe):
        """Optional couponId → included in discounts, allow_promotion_codes=False."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'stripeCustomerId': 'cus_existing'},
        }

        event = _make_event(
            path='/billing/create-checkout-session',
            method='POST',
            body={'priceId': 'price_test_monthly', 'couponId': 'FOUNDING50'},
        )
        log = MagicMock()
        resp = billing_app.handle_create_checkout(event, 'user-123', log)

        assert resp['statusCode'] == 200
        call_kwargs = mock_stripe.checkout.Session.create.call_args
        assert call_kwargs.kwargs.get('discounts') == [{'coupon': 'FOUNDING50'}]
        assert call_kwargs.kwargs.get('allow_promotion_codes') is False

    def test_no_coupon_allows_promotion_codes(self, mock_dynamodb, mock_ssm, mock_stripe):
        """No couponId → allow_promotion_codes is True."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'stripeCustomerId': 'cus_existing'},
        }

        event = _make_event(
            path='/billing/create-checkout-session',
            method='POST',
            body={'priceId': 'price_test_monthly'},
        )
        log = MagicMock()
        resp = billing_app.handle_create_checkout(event, 'user-123', log)

        assert resp['statusCode'] == 200
        call_kwargs = mock_stripe.checkout.Session.create.call_args
        assert call_kwargs.kwargs.get('allow_promotion_codes') is True


# ===================================================================
# Plans endpoint — handle_get_plans
# ===================================================================

class TestHandleGetPlans:
    """Tests for GET /billing/plans (public, no auth)."""

    def test_returns_plans_with_founding_member_available(self, mock_ssm):
        """Returns plan defs with foundingMemberAvailable=true when coupon has slots."""
        # Mock the coupon lookup for founding member code
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/FOUNDING50':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'maxRedemptions': 100,
                            'currentRedemptions': 42,
                        }),
                    },
                }
            # Stripe key
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        event = _make_event(path='/billing/plans', method='GET', user_id=None)
        resp = billing_app.handle_get_plans(event)
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['foundingMemberAvailable'] is True
        assert 'plans' in body

    def test_founding_member_unavailable_when_exhausted(self, mock_ssm):
        """foundingMemberAvailable=false when coupon exhausted."""
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/FOUNDING50':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'maxRedemptions': 100,
                            'currentRedemptions': 100,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        event = _make_event(path='/billing/plans', method='GET', user_id=None)
        resp = billing_app.handle_get_plans(event)
        body = _parse_body(resp)

        assert body['foundingMemberAvailable'] is False
        assert body['foundingMemberSlotsRemaining'] == 0

    def test_founding_member_slots_remaining_count(self, mock_ssm):
        """Returns correct foundingMemberSlotsRemaining count."""
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/FOUNDING50':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'maxRedemptions': 100,
                            'currentRedemptions': 42,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        event = _make_event(path='/billing/plans', method='GET', user_id=None)
        resp = billing_app.handle_get_plans(event)
        body = _parse_body(resp)

        assert body['foundingMemberSlotsRemaining'] == 58

    def test_cors_headers_present(self, mock_ssm):
        """CORS headers present on plans response."""
        # Make coupon lookup raise ParameterNotFound so _get_coupon returns None
        mock_ssm.get_parameter.side_effect = _ParameterNotFound('not found')

        event = _make_event(path='/billing/plans', method='GET', user_id=None)
        resp = billing_app.handle_get_plans(event)

        assert 'headers' in resp
        assert 'Access-Control-Allow-Origin' in resp['headers']


# ===================================================================
# Portal endpoint — handle_portal
# ===================================================================

class TestHandlePortal:
    """Tests for GET /billing/portal."""

    def test_user_with_stripe_customer_returns_portal_url(
        self, mock_dynamodb, mock_ssm, mock_stripe,
    ):
        """User with stripeCustomerId → returns portalUrl."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'stripeCustomerId': 'cus_existing_456'},
        }

        event = _make_event(path='/billing/portal', method='GET')
        resp = billing_app.handle_portal(event, 'user-123')
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['portalUrl'] == 'https://billing.stripe.com/portal/test456'
        mock_stripe.billing_portal.Session.create.assert_called_once()

    def test_user_without_stripe_customer_returns_400(
        self, mock_dynamodb, mock_ssm, mock_stripe,
    ):
        """User without stripeCustomerId → HTTP 400."""
        mock_dynamodb.get_item.return_value = {'Item': {}}

        event = _make_event(path='/billing/portal', method='GET')
        resp = billing_app.handle_portal(event, 'user-123')
        body = _parse_body(resp)

        assert resp['statusCode'] == 400
        assert 'No billing account found' in body['error']


# ===================================================================
# Coupon endpoint — handle_apply_coupon
# ===================================================================

class TestHandleApplyCoupon:
    """Tests for POST /billing/apply-coupon."""

    def test_valid_forever_free_coupon(self, mock_dynamodb, mock_ssm):
        """Valid forever_free coupon → writes record with planId=premium, status=comped."""
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/LIFETIME':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'type': 'forever_free',
                            'maxRedemptions': 50,
                            'currentRedemptions': 10,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        # User has no active premium plan
        mock_dynamodb.get_item.return_value = {'Item': {}}

        event = _make_event(
            path='/billing/apply-coupon',
            method='POST',
            body={'code': 'LIFETIME'},
        )
        log = MagicMock()
        resp = billing_app.handle_apply_coupon(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 200
        assert body['success'] is True
        assert body['type'] == 'forever_free'
        assert body['planId'] == 'premium'

        # Verify DynamoDB put_item was called with correct data
        put_call = mock_dynamodb.put_item.call_args
        item = put_call.kwargs.get('Item') or put_call[1].get('Item')
        assert item['planId'] == 'premium'
        assert item['status'] == 'comped'
        assert item['couponCode'] == 'LIFETIME'

    def test_expired_coupon_returns_400(self, mock_dynamodb, mock_ssm):
        """Expired coupon → HTTP 400."""
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/EXPIRED':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'type': 'forever_free',
                            'expiresAt': past,
                            'maxRedemptions': 50,
                            'currentRedemptions': 10,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        event = _make_event(
            path='/billing/apply-coupon',
            method='POST',
            body={'code': 'EXPIRED'},
        )
        log = MagicMock()
        resp = billing_app.handle_apply_coupon(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 400
        assert 'expired' in body['error'].lower()

    def test_coupon_at_max_redemptions_returns_400(self, mock_dynamodb, mock_ssm):
        """Coupon at maxRedemptions → HTTP 400."""
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/MAXED':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'type': 'forever_free',
                            'maxRedemptions': 10,
                            'currentRedemptions': 10,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        event = _make_event(
            path='/billing/apply-coupon',
            method='POST',
            body={'code': 'MAXED'},
        )
        log = MagicMock()
        resp = billing_app.handle_apply_coupon(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 400
        assert 'redemption limit' in body['error'].lower()

    def test_user_already_active_premium_returns_400(self, mock_dynamodb, mock_ssm):
        """User already on active premium → HTTP 400."""
        def _get_param_side_effect(**kwargs):
            name = kwargs.get('Name', '')
            if name == '/soulreel/coupons/VALID':
                return {
                    'Parameter': {
                        'Value': json.dumps({
                            'type': 'forever_free',
                            'maxRedemptions': 50,
                            'currentRedemptions': 5,
                        }),
                    },
                }
            return {'Parameter': {'Value': 'sk_test_fake123'}}

        mock_ssm.get_parameter.side_effect = _get_param_side_effect

        # User already has active premium
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'userId': 'user-123',
                'planId': 'premium',
                'status': 'active',
            },
        }

        event = _make_event(
            path='/billing/apply-coupon',
            method='POST',
            body={'code': 'VALID'},
        )
        log = MagicMock()
        resp = billing_app.handle_apply_coupon(event, 'user-123', log)
        body = _parse_body(resp)

        assert resp['statusCode'] == 400
        assert 'already have an active plan' in body['error'].lower()
