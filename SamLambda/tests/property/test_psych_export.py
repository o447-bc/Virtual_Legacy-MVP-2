"""
Property-based tests for export logic.

Feature: psych-test-framework, Property 11: Export path construction
Feature: psych-test-framework, Property 12: JSON export excludes rawResponses
Feature: psych-test-framework, Property 13: CSV export structure

**Validates: Requirements 9.2, 9.4, 9.5**
"""
import json
import os
import sys
import csv
import io
import importlib.util
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
_EXPORT_DIR = os.path.join(
    _ROOT, 'functions', 'psychTestFunctions', 'exportTestResults')
for _p in [_SHARED, _EXPORT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault('ALLOWED_ORIGIN', 'https://www.soulreel.net')
os.environ.setdefault('TABLE_USER_TEST_RESULTS', 'UserTestResultsDB')
os.environ.setdefault('S3_BUCKET', 'virtual-legacy')


def _load(name, fp):
    s = importlib.util.spec_from_file_location(name, fp)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


_mock_dynamo = MagicMock()
_mock_s3 = MagicMock()
with patch('boto3.resource', return_value=_mock_dynamo), \
     patch('boto3.client', return_value=_mock_s3):
    export_mod = _load('export_app', os.path.join(_EXPORT_DIR, 'app.py'))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_ASCII_ALNUM = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

safe_text = st.text(
    alphabet=_ASCII_ALNUM + '-_',
    min_size=1, max_size=30,
).filter(lambda s: len(s.strip()) >= 1)

uid = safe_text
tid = safe_text
ts = st.text(
    alphabet='0123456789-T:Z.',
    min_size=10, max_size=30,
).filter(lambda s: len(s.strip()) >= 10)

export_format = st.sampled_from(['PDF', 'JSON', 'CSV'])

score_entry = st.fixed_dictionaries({
    'raw': st.floats(min_value=0, max_value=100, allow_nan=False,
                     allow_infinity=False),
    'normalized': st.floats(min_value=0, max_value=100, allow_nan=False,
                            allow_infinity=False),
    'label': st.sampled_from(['Low', 'Average', 'High', 'unclassified']),
})

domain_scores_st = st.dictionaries(
    keys=st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz_',
        min_size=2, max_size=20,
    ),
    values=score_entry,
    min_size=1, max_size=8,
)

facet_scores_st = st.dictionaries(
    keys=st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz_',
        min_size=2, max_size=20,
    ),
    values=score_entry,
    min_size=0, max_size=12,
)

narrative_st = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Z'),
                           whitelist_characters='.,;:!? '),
    min_size=0, max_size=200,
)


def _build_result(test_id, version, timestamp, domain_scores, facet_scores,
                  narrative_text):
    """Build a mock DynamoDB result item."""
    threshold_classifications = {}
    for name, entry in domain_scores.items():
        threshold_classifications[name] = entry['label']
    for name, entry in facet_scores.items():
        threshold_classifications[name] = entry['label']
    return {
        'userId': 'test-user',
        'testIdVersionTimestamp': f'{test_id}#{version}#{timestamp}',
        'testId': test_id,
        'version': version,
        'timestamp': timestamp,
        'domainScores': domain_scores,
        'facetScores': facet_scores,
        'compositeScores': {},
        'thresholdClassifications': threshold_classifications,
        'narrativeText': narrative_text,
        'narrativeSource': 'template',
        'rawResponses': [{'questionId': 'q1', 'answer': 3}],
    }


# ===================================================================
# Property 11: Export path construction
# Feature: psych-test-framework, Property 11: Export path construction
# **Validates: Requirements 9.2**
# ===================================================================


class TestExportPathConstruction:
    """Property 11: S3 path matches psych-exports/{userId}/{testId}/{timestamp}.{format_lower}."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(user_id=uid, test_id=tid, version=safe_text,
           timestamp=ts, fmt=export_format)
    def test_export_path_matches_pattern(
        self, user_id, test_id, version, timestamp, fmt
    ):
        """For any userId, testId, timestamp, format — the S3 key follows the pattern."""
        result_item = _build_result(
            test_id, version, timestamp,
            {'domain_a': {'raw': 3.0, 'normalized': 3.0, 'label': 'Average'}},
            {},
            'narrative',
        )

        captured_keys = []

        tbl = MagicMock()
        tbl.get_item.return_value = {'Item': result_item}
        tbl.update_item.return_value = {}
        export_mod._dynamodb = MagicMock()
        export_mod._dynamodb.Table.return_value = tbl

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://example.com/presigned'

        def capture_put(**kwargs):
            captured_keys.append(kwargs.get('Key'))

        mock_s3.put_object.side_effect = capture_put
        export_mod._s3 = mock_s3

        event = {
            'httpMethod': 'POST',
            'path': '/psych-tests/export',
            'headers': {'origin': 'https://www.soulreel.net'},
            'requestContext': {
                'authorizer': {'claims': {'sub': user_id}}
            },
            'body': json.dumps({
                'testId': test_id,
                'version': version,
                'timestamp': timestamp,
                'format': fmt,
            }),
        }

        r = export_mod.lambda_handler(event, {})
        assert r['statusCode'] == 200, f'Got {r["statusCode"]}: {r.get("body")}'

        assert len(captured_keys) == 1
        expected_key = f'psych-exports/{user_id}/{test_id}/{timestamp}.{fmt.lower()}'
        assert captured_keys[0] == expected_key


# ===================================================================
# Property 12: JSON export excludes rawResponses
# Feature: psych-test-framework, Property 12: JSON export excludes rawResponses
# **Validates: Requirements 9.4**
# ===================================================================


class TestJsonExportExcludesRawResponses:
    """Property 12: JSON export contains result fields but NOT rawResponses."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_id=tid, version=safe_text, timestamp=ts,
           domain_scores=domain_scores_st, facet_scores=facet_scores_st,
           narrative=narrative_st)
    def test_json_export_excludes_raw_responses(
        self, test_id, version, timestamp, domain_scores, facet_scores,
        narrative
    ):
        """For any test result, JSON export has scores but not rawResponses."""
        result = _build_result(
            test_id, version, timestamp, domain_scores, facet_scores, narrative
        )

        content_bytes, content_type = export_mod._generate_json_export(result)
        assert content_type == 'application/json'

        parsed = json.loads(content_bytes.decode('utf-8'))

        # Must contain these fields
        assert 'domainScores' in parsed
        assert 'facetScores' in parsed
        assert 'compositeScores' in parsed
        assert 'thresholdClassifications' in parsed
        assert 'narrativeText' in parsed

        # Must NOT contain rawResponses
        assert 'rawResponses' not in parsed


# ===================================================================
# Property 13: CSV export structure
# Feature: psych-test-framework, Property 13: CSV export structure
# **Validates: Requirements 9.5**
# ===================================================================


class TestCsvExportStructure:
    """Property 13: CSV has (D + F) data rows plus header with correct columns."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_id=tid, version=safe_text, timestamp=ts,
           domain_scores=domain_scores_st, facet_scores=facet_scores_st,
           narrative=narrative_st)
    def test_csv_has_correct_row_count_and_columns(
        self, test_id, version, timestamp, domain_scores, facet_scores,
        narrative
    ):
        """For D domains and F facets, CSV has D+F data rows + header."""
        result = _build_result(
            test_id, version, timestamp, domain_scores, facet_scores, narrative
        )

        content_bytes, content_type = export_mod._generate_csv_export(result)
        assert content_type == 'text/csv'

        reader = csv.reader(io.StringIO(content_bytes.decode('utf-8')))
        rows = list(reader)

        D = len(domain_scores)
        F = len(facet_scores)

        # Header + D + F data rows
        expected_total = 1 + D + F
        assert len(rows) == expected_total, (
            f'Expected {expected_total} rows (1 header + {D} domains + {F} facets), '
            f'got {len(rows)}'
        )

        # Verify header columns
        header = rows[0]
        assert header == ['name', 'raw_score', 'threshold_label', 'percentile']
