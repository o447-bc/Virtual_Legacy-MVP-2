"""
Property-based tests for admin import correctness.

Feature: psych-test-framework, Property 3: Admin import correctness

**Validates: Requirements 3.1, 3.2, 3.3, 3.5**
"""
import json
import os
import sys
import importlib.util
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Path setup — import admin import functions directly from the Lambda module
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SHARED = os.path.join(_ROOT, 'functions', 'shared', 'python')
_IMPORT_DIR = os.path.join(
    _ROOT, 'functions', 'psychTestFunctions', 'adminImportTest')

for _p in [_SHARED, _IMPORT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault('ALLOWED_ORIGIN', 'https://www.soulreel.net')
os.environ.setdefault('TABLE_PSYCH_TESTS', 'PsychTestsDB')
os.environ.setdefault('TABLE_ALL_QUESTIONS', 'allQuestionDB')
os.environ.setdefault('S3_BUCKET', 'virtual-legacy')


def _load_module(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load the admin import module with mocked AWS clients
_mock_dynamo = MagicMock()
_mock_s3 = MagicMock()

with patch('boto3.resource', return_value=_mock_dynamo), \
     patch('boto3.client', return_value=_mock_s3):
    import_mod = _load_module('import_app', os.path.join(_IMPORT_DIR, 'app.py'))


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_safe_id = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                           whitelist_characters='-_'),
    min_size=3, max_size=20,
).filter(lambda s: len(s.strip()) >= 3)

_version = st.from_regex(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', fullmatch=True)

_facet_name = st.text(
    alphabet=st.characters(whitelist_categories=('Ll',),
                           whitelist_characters='-_'),
    min_size=2, max_size=15,
)


def _make_question(qid, scoring_key, facet):
    """Build a minimal valid question object."""
    return {
        'questionId': qid,
        'text': f'Question {qid}',
        'responseType': 'likert5',
        'options': ['SD', 'D', 'N', 'A', 'SA'],
        'reverseScored': False,
        'scoringKey': scoring_key,
        'groupByFacet': facet,
        'pageBreakAfter': False,
        'accessibilityHint': f'Hint for {qid}',
    }


def _make_test_definition(test_id, version, questions):
    """Build a minimal valid Test Definition."""
    # Collect unique scoring keys for scoringRules
    scoring_keys = {q['scoringKey'] for q in questions}
    scoring_rules = {}
    for key in scoring_keys:
        scoring_rules[key] = {
            'formula': 'mean',
            'thresholds': [{'min': 0, 'max': 999, 'label': 'any'}],
        }

    return {
        'testId': test_id,
        'testName': f'Test {test_id}',
        'description': f'Description for {test_id}',
        'version': version,
        'estimatedMinutes': 10,
        'consentBlock': {
            'title': 'Consent',
            'bodyText': 'Please consent.',
            'requiredCheckboxLabel': 'I agree',
        },
        'disclaimerText': 'This is a disclaimer.',
        'questions': questions,
        'scoringRules': scoring_rules,
        'compositeRules': {},
        'interpretationTemplates': {},
        'videoPromptTrigger': 'Record a video about {domain}',
        'saveProgressEnabled': True,
        'analyticsEnabled': False,
        'exportFormats': ['JSON'],
    }


@st.composite
def valid_test_definitions(draw):
    """Strategy that generates valid Test Definitions with 1-15 questions."""
    test_id = draw(_safe_id)
    version = draw(_version)
    num_questions = draw(st.integers(min_value=1, max_value=15))

    domain = draw(_safe_id)
    facets = draw(st.lists(
        _facet_name,
        min_size=1,
        max_size=min(num_questions, 5),
    ).filter(lambda fs: all(len(f.strip()) >= 2 for f in fs)))
    assume(len(facets) >= 1)

    questions = []
    for i in range(num_questions):
        facet = facets[i % len(facets)]
        qid = f'{test_id}-q{i}'
        questions.append(_make_question(qid, domain, facet))

    return _make_test_definition(test_id, version, questions)


# ===================================================================
# Property 3: Admin import correctness
# Feature: psych-test-framework, Property 3: Admin import correctness
# **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
# ===================================================================

class TestAdminImportCorrectness:
    """Property 3: Importing a valid Test Definition with N questions produces
    exactly N question records in allQuestionDB with correct questionType and
    facet, plus a metadata record in PsychTests table."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_def=valid_test_definitions())
    def test_import_produces_correct_records(self, test_def):
        """For any valid Test Definition with N questions, import produces
        N question records with questionType=testId and facet=groupByFacet,
        plus a metadata record with testId, version, status, s3Path."""

        test_id = test_def['testId']
        version = test_def['version']
        questions = test_def['questions']
        n = len(questions)

        # Track put_item calls per table
        psych_puts = []
        question_puts = []

        mock_psych_table = MagicMock()
        mock_psych_table.get_item.return_value = {}  # no duplicate
        mock_psych_table.put_item.side_effect = lambda **kw: psych_puts.append(kw)

        mock_question_table = MagicMock()
        mock_question_table.put_item.side_effect = lambda **kw: question_puts.append(kw)

        def table_factory(name):
            if 'PsychTests' in name:
                return mock_psych_table
            if 'allQuestion' in name or 'Question' in name:
                return mock_question_table
            return MagicMock()

        import_mod._dynamodb = MagicMock()
        import_mod._dynamodb.Table.side_effect = table_factory
        import_mod._s3 = MagicMock()

        event = {
            'httpMethod': 'POST',
            'path': '/psych-tests/admin/import',
            'headers': {'origin': 'https://www.soulreel.net'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-user-123',
                        'cognito:groups': 'SoulReelAdmins',
                    }
                }
            },
            'body': json.dumps(test_def),
        }

        result = import_mod.lambda_handler(event, {})
        assert result['statusCode'] == 200, (
            f'Expected 200, got {result["statusCode"]}: {result.get("body")}'
        )

        body = json.loads(result['body'])
        assert body['testId'] == test_id
        assert body['version'] == version
        assert body['questionCount'] == n

        # --- Verify question records ---
        assert len(question_puts) == n, (
            f'Expected {n} question records, got {len(question_puts)}'
        )

        for i, put_call in enumerate(question_puts):
            item = put_call['Item']
            assert item['questionType'] == test_id, (
                f'Question {i}: questionType should be {test_id}, '
                f'got {item["questionType"]}'
            )
            # facet tag must match the question's groupByFacet
            expected_facet = questions[i]['groupByFacet']
            assert item['facet'] == expected_facet, (
                f'Question {i}: facet should be {expected_facet}, '
                f'got {item["facet"]}'
            )
            assert item['groupByFacet'] == expected_facet

        # --- Verify metadata record ---
        assert len(psych_puts) == 1, (
            f'Expected 1 metadata record, got {len(psych_puts)}'
        )
        meta = psych_puts[0]['Item']
        assert meta['testId'] == test_id
        assert meta['version'] == version
        assert meta['status'] == 'active'
        assert 's3Path' in meta
        assert meta['s3Path'] == f'psych-tests/{test_id}.json'

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_def=valid_test_definitions())
    def test_import_preserves_previous_version_mapping(self, test_def):
        """When previousVersionMapping is present, it is stored in metadata."""
        # Add a previousVersionMapping
        test_def['previousVersionMapping'] = {'old-q1': 'new-q1', 'old-q2': 'new-q2'}

        psych_puts = []

        mock_psych_table = MagicMock()
        mock_psych_table.get_item.return_value = {}
        mock_psych_table.put_item.side_effect = lambda **kw: psych_puts.append(kw)

        mock_question_table = MagicMock()

        def table_factory(name):
            if 'PsychTests' in name:
                return mock_psych_table
            return mock_question_table

        import_mod._dynamodb = MagicMock()
        import_mod._dynamodb.Table.side_effect = table_factory
        import_mod._s3 = MagicMock()

        event = {
            'httpMethod': 'POST',
            'path': '/psych-tests/admin/import',
            'headers': {'origin': 'https://www.soulreel.net'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-user-456',
                        'cognito:groups': 'SoulReelAdmins',
                    }
                }
            },
            'body': json.dumps(test_def),
        }

        result = import_mod.lambda_handler(event, {})
        assert result['statusCode'] == 200

        meta = psych_puts[0]['Item']
        assert 'previousVersionMapping' in meta
        assert meta['previousVersionMapping'] == {'old-q1': 'new-q1', 'old-q2': 'new-q2'}
