"""
Property-based tests for schema validation and JSON round-trip.

Feature: psych-test-framework, Property 1: Schema conformance
Feature: psych-test-framework, Property 2: Test Definition JSON round-trip

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.10, 2.1, 2.2**
"""
import json
import os
import sys

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCHEMA_PATH = os.path.join(_ROOT, 'schemas', 'psych-test-definition.schema.json')

# Ensure jsonschema is available
import jsonschema


def _load_schema():
    with open(_SCHEMA_PATH, 'r') as f:
        return json.load(f)


SCHEMA = _load_schema()


# ---------------------------------------------------------------------------
# Strategies for generating valid Test Definition objects
# ---------------------------------------------------------------------------

_safe_text = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'),
                           whitelist_characters=' -_'),
    min_size=1, max_size=30,
)

_question_id = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                           whitelist_characters='-_'),
    min_size=1, max_size=20,
)

_response_type = st.sampled_from(['likert5', 'bipolar5', 'multipleChoice'])


def _question_strategy(scoring_key, facet):
    """Generate a valid question object with given scoringKey and facet."""
    return st.fixed_dictionaries({
        'questionId': _question_id,
        'text': _safe_text,
        'responseType': _response_type,
        'options': st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
        'reverseScored': st.booleans(),
        'scoringKey': st.just(scoring_key),
        'groupByFacet': st.just(facet),
        'pageBreakAfter': st.booleans(),
        'accessibilityHint': _safe_text,
    })


@st.composite
def valid_test_definition(draw):
    """Generate a valid Test Definition that conforms to the schema."""
    test_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'),
                               whitelist_characters='-'),
        min_size=3, max_size=20,
    ))
    assume(len(test_id.strip()) >= 3)

    domain = draw(_safe_text)
    facet = draw(_safe_text)

    # Generate 1-5 questions all referencing the same domain/facet
    num_questions = draw(st.integers(min_value=1, max_value=5))
    questions = []
    for i in range(num_questions):
        q = draw(_question_strategy(domain, facet))
        # Ensure unique questionIds
        q['questionId'] = f'{test_id}-q{i}'
        questions.append(q)

    # Scoring rules must reference the domain used by questions
    threshold = draw(st.fixed_dictionaries({
        'min': st.just(1.0),
        'max': st.just(5.0),
        'label': _safe_text,
    }))

    formula = draw(st.sampled_from(['mean', 'sum']))

    return {
        'testId': test_id,
        'testName': draw(_safe_text),
        'description': draw(_safe_text),
        'version': draw(st.from_regex(r'[0-9]+\.[0-9]+\.[0-9]+', fullmatch=True)),
        'estimatedMinutes': draw(st.integers(min_value=1, max_value=120)),
        'consentBlock': {
            'title': draw(_safe_text),
            'bodyText': draw(_safe_text),
            'requiredCheckboxLabel': draw(_safe_text),
        },
        'disclaimerText': draw(_safe_text),
        'questions': questions,
        'scoringRules': {
            domain: {
                'formula': formula,
                'thresholds': [threshold],
            }
        },
        'compositeRules': {},
        'interpretationTemplates': {},
        'videoPromptTrigger': draw(_safe_text),
        'saveProgressEnabled': draw(st.booleans()),
        'analyticsEnabled': draw(st.booleans()),
        'exportFormats': draw(st.lists(
            st.sampled_from(['PDF', 'JSON', 'CSV']),
            min_size=0, max_size=3,
        )),
    }


# ===================================================================
# Property 1: Schema conformance
# Feature: psych-test-framework, Property 1: Schema conformance
# **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2**
# ===================================================================

class TestSchemaConformance:
    """Property 1: Valid definitions pass schema validation; invalid ones fail."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_def=valid_test_definition())
    def test_valid_definition_passes_schema(self, test_def):
        """Any generated valid Test Definition should pass schema validation."""
        jsonschema.validate(instance=test_def, schema=SCHEMA)

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(
        test_def=valid_test_definition(),
        field_to_remove=st.sampled_from([
            'testId', 'testName', 'description', 'version',
            'questions', 'scoringRules', 'consentBlock',
        ]),
    )
    def test_missing_required_field_fails_schema(self, test_def, field_to_remove):
        """Removing a required field should cause schema validation to fail."""
        del test_def[field_to_remove]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=test_def, schema=SCHEMA)

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_def=valid_test_definition())
    def test_wrong_type_fails_schema(self, test_def):
        """Setting questions to a string (wrong type) should fail validation."""
        test_def['questions'] = 'not-an-array'
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=test_def, schema=SCHEMA)


# ===================================================================
# Property 2: Test Definition JSON round-trip
# Feature: psych-test-framework, Property 2: Test Definition JSON round-trip
# **Validates: Requirements 1.10**
# ===================================================================

class TestJsonRoundTrip:
    """Property 2: Serialize to JSON then parse back produces equivalent object."""

    @settings(max_examples=100, deadline=None,
              suppress_health_check=[HealthCheck.too_slow])
    @given(test_def=valid_test_definition())
    def test_json_round_trip(self, test_def):
        """For any valid Test Definition, JSON round-trip preserves equivalence."""
        serialized = json.dumps(test_def)
        deserialized = json.loads(serialized)
        assert deserialized == test_def
