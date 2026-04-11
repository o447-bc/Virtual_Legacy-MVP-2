"""
Property-based tests for scoring logic and progress cleanup.

Feature: psych-test-framework, Property 7: Reverse scoring transformation
Feature: psych-test-framework, Property 8: Domain and facet score calculation
Feature: psych-test-framework, Property 9: Threshold classification
Feature: psych-test-framework, Property 10: Scoring idempotence
Feature: psych-test-framework, Property 6: Progress cleanup after scoring

**Validates: Requirements 5.6, 6.3, 6.4, 6.5, 6.6, 6.12**
"""
import json
import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock
from collections import defaultdict

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Path setup — import scoring functions directly from the Lambda module
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
_SCORE_DIR = os.path.join(
    _ROOT, 'functions', 'psychTestFunctions', 'scorePsychTest')

for _p in [_SHARED, _SCORE_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault('ALLOWED_ORIGIN', 'https://www.soulreel.net')
os.environ.setdefault('TABLE_USER_TEST_RESULTS', 'UserTestResultsDB')
os.environ.setdefault('TABLE_USER_TEST_PROGRESS', 'UserTestProgressDB')
os.environ.setdefault('TABLE_PSYCH_TESTS', 'PsychTestsDB')


def _load_module(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load the scoring module with mocked AWS clients
_mock_dynamo = MagicMock()
_mock_s3 = MagicMock()
_mock_bedrock = MagicMock()

with patch('boto3.resource', return_value=_mock_dynamo), \
     patch('boto3.client') as mock_client:
    def _client_factory(service, **kwargs):
        if service == 's3':
            return _mock_s3
        if service == 'bedrock-runtime':
            return _mock_bedrock
        return MagicMock()
    mock_client.side_effect = _client_factory
    score_mod = _load_module('score_app', os.path.join(_SCORE_DIR, 'app.py'))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

likert_value = st.integers(min_value=1, max_value=5)

_qid = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                           whitelist_characters='-_'),
    min_size=1, max_size=15,
)

_domain_name = st.text(
    alphabet=st.characters(whitelist_categories=('Ll',),
                           whitelist_characters='-_'),
    min_size=2, max_size=15,
)

_facet_name = st.text(
    alphabet=st.characters(whitelist_categories=('Ll',),
                           whitelist_characters='-_'),
    min_size=2, max_size=15,
)


# ===================================================================
# Property 7: Reverse scoring transformation
# Feature: psych-test-framework, Property 7: Reverse scoring transformation
# **Validates: Requirements 6.3**
# ===================================================================

class TestReverseScoring:
    """Property 7: reverseScored=true with likert5 → (6 - V); false → V."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(value=likert_value, reverse=st.booleans())
    def test_reverse_scoring_transformation(self, value, reverse):
        """For any Likert-5 value V, reverse scoring produces (6-V) or V."""
        questions = [{
            'questionId': 'q1',
            'text': 'test',
            'responseType': 'likert5',
            'options': [],
            'reverseScored': reverse,
            'scoringKey': 'domain',
            'groupByFacet': 'facet',
            'pageBreakAfter': False,
            'accessibilityHint': '',
        }]
        response_map = {'q1': value}

        scored = score_mod._apply_reverse_scoring(questions, response_map)

        if reverse:
            assert scored['q1'] == 6 - value
        else:
            assert scored['q1'] == value


# ===================================================================
# Property 8: Domain and facet score calculation
# Feature: psych-test-framework, Property 8: Domain and facet score calculation
# **Validates: Requirements 6.4, 6.5**
# ===================================================================

class TestDomainFacetScores:
    """Property 8: Domain score = mean of scored responses grouped by scoringKey."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        values=st.lists(likert_value, min_size=1, max_size=20),
        formula=st.sampled_from(['mean', 'sum']),
    )
    def test_domain_score_calculation(self, values, formula):
        """For any set of responses, domain score matches expected formula result."""
        domain = 'test-domain'
        facet = 'test-facet'

        questions = []
        response_map = {}
        scored_values = {}
        for i, v in enumerate(values):
            qid = f'q{i}'
            questions.append({
                'questionId': qid,
                'text': f'Question {i}',
                'responseType': 'likert5',
                'options': [],
                'reverseScored': False,
                'scoringKey': domain,
                'groupByFacet': facet,
                'pageBreakAfter': False,
                'accessibilityHint': '',
            })
            response_map[qid] = v
            scored_values[qid] = v

        scoring_rules = {
            domain: {
                'formula': formula,
                'thresholds': [{'min': 0, 'max': 999, 'label': 'any'}],
            }
        }

        domain_scores = score_mod._calculate_domain_scores(
            questions, scored_values, scoring_rules
        )

        assert domain in domain_scores
        raw = domain_scores[domain]['raw']

        if formula == 'mean':
            expected = sum(values) / len(values)
        else:
            expected = sum(values)

        assert abs(raw - expected) < 0.001

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        values=st.lists(likert_value, min_size=1, max_size=20),
    )
    def test_facet_score_calculation(self, values):
        """For any set of responses, facet score = mean grouped by groupByFacet."""
        domain = 'test-domain'
        facet = 'test-facet'

        questions = []
        scored_values = {}
        for i, v in enumerate(values):
            qid = f'q{i}'
            questions.append({
                'questionId': qid,
                'text': f'Question {i}',
                'responseType': 'likert5',
                'options': [],
                'reverseScored': False,
                'scoringKey': domain,
                'groupByFacet': facet,
                'pageBreakAfter': False,
                'accessibilityHint': '',
            })
            scored_values[qid] = v

        scoring_rules = {
            domain: {
                'formula': 'mean',
                'thresholds': [{'min': 0, 'max': 999, 'label': 'any'}],
            }
        }

        facet_scores = score_mod._calculate_facet_scores(
            questions, scored_values, scoring_rules
        )

        assert facet in facet_scores
        expected = sum(values) / len(values)
        assert abs(facet_scores[facet]['raw'] - expected) < 0.001


# ===================================================================
# Property 9: Threshold classification
# Feature: psych-test-framework, Property 9: Threshold classification
# **Validates: Requirements 6.6**
# ===================================================================

class TestThresholdClassification:
    """Property 9: Correct label for in-range; 'unclassified' for out-of-range."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        score=st.floats(min_value=1.0, max_value=5.0, allow_nan=False,
                        allow_infinity=False),
    )
    def test_in_range_classification(self, score):
        """Score within a threshold range gets the correct label."""
        thresholds = [
            {'min': 1.0, 'max': 2.5, 'label': 'Low'},
            {'min': 2.5, 'max': 3.5, 'label': 'Average'},
            {'min': 3.5, 'max': 5.0, 'label': 'High'},
        ]
        result = score_mod._classify(score, thresholds)
        assert result in ('Low', 'Average', 'High')

        # Verify correct label
        if 1.0 <= score <= 2.5:
            assert result == 'Low'
        elif 2.5 < score <= 3.5:
            # score == 2.5 matches Low (first match wins)
            assert result == 'Average'
        else:
            assert result == 'High'

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        score=st.floats(min_value=6.0, max_value=100.0, allow_nan=False,
                        allow_infinity=False),
    )
    def test_out_of_range_returns_unclassified(self, score):
        """Score outside all threshold ranges returns 'unclassified'."""
        thresholds = [
            {'min': 1.0, 'max': 2.5, 'label': 'Low'},
            {'min': 2.5, 'max': 3.5, 'label': 'Average'},
            {'min': 3.5, 'max': 5.0, 'label': 'High'},
        ]
        result = score_mod._classify(score, thresholds)
        assert result == 'unclassified'


# ===================================================================
# Property 10: Scoring idempotence
# Feature: psych-test-framework, Property 10: Scoring idempotence
# **Validates: Requirements 6.12**
# ===================================================================

class TestScoringIdempotence:
    """Property 10: Scoring the same responses twice produces identical results."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        values=st.lists(likert_value, min_size=1, max_size=10),
        reverse_flags=st.lists(st.booleans(), min_size=1, max_size=10),
    )
    def test_scoring_idempotence(self, values, reverse_flags):
        """Scoring twice with identical inputs produces identical outputs."""
        # Align lengths
        n = min(len(values), len(reverse_flags))
        values = values[:n]
        reverse_flags = reverse_flags[:n]

        domain = 'idempotent-domain'
        facet = 'idempotent-facet'

        questions = []
        response_map = {}
        for i in range(n):
            qid = f'q{i}'
            questions.append({
                'questionId': qid,
                'text': f'Q{i}',
                'responseType': 'likert5',
                'options': [],
                'reverseScored': reverse_flags[i],
                'scoringKey': domain,
                'groupByFacet': facet,
                'pageBreakAfter': False,
                'accessibilityHint': '',
            })
            response_map[qid] = values[i]

        scoring_rules = {
            domain: {
                'formula': 'mean',
                'thresholds': [
                    {'min': 1.0, 'max': 2.5, 'label': 'Low'},
                    {'min': 2.5, 'max': 3.5, 'label': 'Average'},
                    {'min': 3.5, 'max': 5.0, 'label': 'High'},
                ],
            }
        }

        # First scoring pass
        scored1 = score_mod._apply_reverse_scoring(questions, response_map)
        domain1 = score_mod._calculate_domain_scores(questions, scored1, scoring_rules)
        facet1 = score_mod._calculate_facet_scores(questions, scored1, scoring_rules)
        thresh1 = score_mod._apply_thresholds(domain1, facet1, scoring_rules)

        # Second scoring pass
        scored2 = score_mod._apply_reverse_scoring(questions, response_map)
        domain2 = score_mod._calculate_domain_scores(questions, scored2, scoring_rules)
        facet2 = score_mod._calculate_facet_scores(questions, scored2, scoring_rules)
        thresh2 = score_mod._apply_thresholds(domain2, facet2, scoring_rules)

        assert domain1 == domain2
        assert facet1 == facet2
        assert thresh1 == thresh2


# ===================================================================
# Property 6: Progress cleanup after scoring
# Feature: psych-test-framework, Property 6: Progress cleanup after scoring
# **Validates: Requirements 5.6**
# ===================================================================

_uid = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'),
                           whitelist_characters='-_'),
    min_size=5, max_size=40,
)

_tid = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                           whitelist_characters='-_'),
    min_size=3, max_size=30,
).filter(lambda s: len(s.strip()) >= 3)


class TestProgressCleanupAfterScoring:
    """Property 6: After successful scoring, progress record is deleted."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        user_id=_uid,
        test_id=_tid,
        values=st.lists(likert_value, min_size=1, max_size=5),
    )
    def test_progress_deleted_after_scoring(self, user_id, test_id, values):
        """For any completed test, the progress record is deleted."""
        domain = 'cleanup-domain'
        facet = 'cleanup-facet'

        questions = []
        responses = []
        for i, v in enumerate(values):
            qid = f'{test_id}-q{i}'
            questions.append({
                'questionId': qid,
                'text': f'Q{i}',
                'responseType': 'likert5',
                'options': ['SD', 'D', 'N', 'A', 'SA'],
                'reverseScored': False,
                'scoringKey': domain,
                'groupByFacet': facet,
                'pageBreakAfter': False,
                'accessibilityHint': f'Hint {i}',
            })
            responses.append({'questionId': qid, 'answer': v})

        test_def = {
            'testId': test_id,
            'testName': 'Cleanup Test',
            'description': 'Test for cleanup',
            'version': '1.0.0',
            'estimatedMinutes': 5,
            'consentBlock': {
                'title': 'Consent',
                'bodyText': 'Body',
                'requiredCheckboxLabel': 'I agree',
            },
            'disclaimerText': 'Disclaimer',
            'questions': questions,
            'scoringRules': {
                domain: {
                    'formula': 'mean',
                    'thresholds': [{'min': 0, 'max': 999, 'label': 'any'}],
                }
            },
            'compositeRules': {},
            'interpretationTemplates': {},
            'videoPromptTrigger': '',
            'saveProgressEnabled': True,
            'analyticsEnabled': False,
            'exportFormats': ['JSON'],
        }

        # Track delete_item calls
        delete_calls = []
        put_calls = []

        mock_progress_table = MagicMock()
        mock_progress_table.delete_item.side_effect = lambda **kw: delete_calls.append(kw)

        mock_results_table = MagicMock()
        mock_results_table.put_item.side_effect = lambda **kw: put_calls.append(kw)

        def table_factory(name):
            if 'Progress' in name:
                return mock_progress_table
            return mock_results_table

        score_mod._dynamodb = MagicMock()
        score_mod._dynamodb.Table.side_effect = table_factory

        # Mock S3 to return the test definition
        score_mod._s3 = MagicMock()
        score_mod._s3.get_object.return_value = {
            'Body': MagicMock(
                read=MagicMock(
                    return_value=json.dumps(test_def).encode('utf-8')
                )
            )
        }

        event = {
            'httpMethod': 'POST',
            'path': '/psych-tests/score',
            'headers': {'origin': 'https://www.soulreel.net'},
            'requestContext': {'authorizer': {'claims': {'sub': user_id}}},
            'body': json.dumps({
                'testId': test_id,
                'responses': responses,
            }),
        }

        result = score_mod.lambda_handler(event, {})
        assert result['statusCode'] == 200, f'Got {result["statusCode"]}: {result.get("body")}'

        # Verify progress was deleted
        assert len(delete_calls) == 1, (
            f'Expected 1 delete_item call, got {len(delete_calls)}'
        )
        key = delete_calls[0].get('Key', {})
        assert key.get('userId') == user_id
        assert key.get('testId') == test_id

        # Verify results were stored
        assert len(put_calls) == 1
