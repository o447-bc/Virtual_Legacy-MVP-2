"""
Property-based tests for progress TTL and save/load round-trip.

Feature: psych-test-framework, Property 4: Progress TTL calculation
Feature: psych-test-framework, Property 5: Progress save/load round-trip

**Validates: Requirements 5.2, 5.5**
"""
import json
import os
import sys
import time
import importlib.util
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
_SAVE_DIR = os.path.join(
    _ROOT, 'functions', 'psychTestFunctions', 'saveTestProgress')
_GET_DIR = os.path.join(
    _ROOT, 'functions', 'psychTestFunctions', 'getTestProgress')
for _p in [_SHARED, _SAVE_DIR, _GET_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault('ALLOWED_ORIGIN', 'https://www.soulreel.net')
os.environ.setdefault('TABLE_USER_TEST_PROGRESS', 'UserTestProgressDB')
TTL_30_DAYS = 2592000


def _load(name, fp):
    s = importlib.util.spec_from_file_location(name, fp)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


_sm = MagicMock()
with patch('boto3.resource', return_value=_sm):
    save_h = _load('save_app', os.path.join(_SAVE_DIR, 'app.py'))

_gm = MagicMock()
with patch('boto3.resource', return_value=_gm):
    get_h = _load('get_app', os.path.join(_GET_DIR, 'app.py'))


# Strategies
tid = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                           whitelist_characters='-_'),
    min_size=3, max_size=30,
).filter(lambda s: len(s.strip()) >= 3)

uid = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'),
                           whitelist_characters='-_'),
    min_size=5, max_size=40,
)

resp_entry = st.fixed_dictionaries({
    'questionId': st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                               whitelist_characters='-_'),
        min_size=1, max_size=20,
    ),
    'answer': st.integers(min_value=1, max_value=5),
})

resps = st.lists(resp_entry, min_size=0, max_size=20)
qidx = st.integers(min_value=0, max_value=200)


def _save_evt(user_id, test_id, responses, idx):
    return {
        'httpMethod': 'POST',
        'path': '/psych-tests/progress/save',
        'headers': {'origin': 'https://www.soulreel.net'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'pathParameters': None,
        'body': json.dumps({
            'testId': test_id,
            'responses': responses,
            'currentQuestionIndex': idx,
        }),
    }


def _get_evt(user_id, test_id):
    return {
        'httpMethod': 'GET',
        'path': f'/psych-tests/progress/{test_id}',
        'headers': {'origin': 'https://www.soulreel.net'},
        'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
        'pathParameters': {'testId': test_id},
        'body': None,
    }


# ===================================================================
# Property 4: Progress TTL calculation
# Feature: psych-test-framework, Property 4: Progress TTL calculation
# **Validates: Requirements 5.2**
# ===================================================================


class TestProgressTTLCalculation:
    """Property 4: expiresAt equals current epoch + 2,592,000 seconds."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=uid, test_id=tid, responses=resps,
           question_index=qidx)
    def test_ttl_equals_epoch_plus_30_days(
        self, user_id, test_id, responses, question_index
    ):
        captured = []
        tbl = MagicMock()
        tbl.put_item.side_effect = lambda **kw: captured.append(kw.get('Item'))
        save_h._dynamodb = MagicMock()
        save_h._dynamodb.Table.return_value = tbl

        t0 = int(time.time())
        r = save_h.lambda_handler(
            _save_evt(user_id, test_id, responses, question_index), {}
        )
        t1 = int(time.time())

        assert r['statusCode'] == 200, f'Got {r["statusCode"]}: {r.get("body")}'
        assert len(captured) == 1

        item = captured[0]
        ea = item['expiresAt']
        assert (t0 + TTL_30_DAYS) <= ea <= (t1 + TTL_30_DAYS)

        ua = item['updatedAt']
        dt = datetime.fromisoformat(ua)
        ue = int(dt.timestamp())
        assert abs(ea - (ue + TTL_30_DAYS)) <= 5


# ===================================================================
# Property 5: Progress save/load round-trip
# Feature: psych-test-framework, Property 5: Progress save/load round-trip
# **Validates: Requirements 5.5**
# ===================================================================


class TestProgressSaveLoadRoundTrip:
    """Property 5: save then load returns identical data."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=uid, test_id=tid, responses=resps,
           question_index=qidx)
    def test_save_then_load_returns_same_data(
        self, user_id, test_id, responses, question_index
    ):
        store = {}

        def do_put(**kw):
            it = kw.get('Item', {})
            store[(it['userId'], it['testId'])] = it

        def do_get(**kw):
            k = kw.get('Key', {})
            it = store.get((k['userId'], k['testId']))
            return {'Item': it} if it else {}

        stbl = MagicMock()
        stbl.put_item.side_effect = do_put
        save_h._dynamodb = MagicMock()
        save_h._dynamodb.Table.return_value = stbl

        sr = save_h.lambda_handler(
            _save_evt(user_id, test_id, responses, question_index), {}
        )
        assert sr['statusCode'] == 200

        gtbl = MagicMock()
        gtbl.get_item.side_effect = do_get
        get_h._dynamodb = MagicMock()
        get_h._dynamodb.Table.return_value = gtbl

        gr = get_h.lambda_handler(_get_evt(user_id, test_id), {})
        assert gr['statusCode'] == 200

        loaded = json.loads(gr['body'])
        assert loaded['responses'] == responses
        assert loaded['currentQuestionIndex'] == question_index
