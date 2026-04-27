"""
Unit and property tests for ConversationState composed_prompt serialization.
Validates: Requirements 4.4, 7.1, 7.2, 7.3
"""
import pytest
from conversation_state import ConversationState


# ---------------------------------------------------------------------------
# Unit tests (Task 2.2)
# ---------------------------------------------------------------------------

def _make_state(**overrides):
    """Helper to create a ConversationState with sensible defaults."""
    state = ConversationState(
        connection_id="conn-1",
        user_id="user-1",
        question_id="childhood-3",
        question_text="What is your earliest memory?",
    )
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


def test_to_dict_includes_composed_prompt_key():
    state = _make_state()
    d = state.to_dict()
    assert 'composedPrompt' in d
    assert d['composedPrompt'] == ""


def test_from_dict_restores_composed_prompt():
    state = _make_state(composed_prompt="You are a themed interviewer.")
    d = state.to_dict()
    restored = ConversationState.from_dict(d)
    assert restored.composed_prompt == "You are a themed interviewer."


def test_from_dict_defaults_to_empty_when_key_absent():
    """Backward compat: existing DynamoDB items won't have composedPrompt."""
    d = {
        'connectionId': 'conn-1',
        'userId': 'user-1',
        'questionId': 'childhood-3',
        'questionText': 'What is your earliest memory?',
    }
    restored = ConversationState.from_dict(d)
    assert restored.composed_prompt == ""


def test_round_trip_preserves_composed_prompt():
    original = _make_state(composed_prompt="Theme: Childhood Memories. Focus on {question}")
    d = original.to_dict()
    restored = ConversationState.from_dict(d)
    assert restored.composed_prompt == original.composed_prompt


# ---------------------------------------------------------------------------
# Property tests (Task 2.3)
# Feature: theme-aware-ai-prompts, Property 4: ConversationState composed_prompt Serialization Round-Trip
# **Validates: Requirements 4.4, 7.1, 7.2, 7.3**
# ---------------------------------------------------------------------------

from hypothesis import given, settings
import hypothesis.strategies as st


@given(prompt=st.text())
@settings(max_examples=200)
def test_property_round_trip_composed_prompt(prompt):
    """Property 4: For any composed_prompt string, to_dict → from_dict preserves it."""
    state = _make_state(composed_prompt=prompt)
    d = state.to_dict()
    restored = ConversationState.from_dict(d)
    assert restored.composed_prompt == prompt


@given(data=st.fixed_dictionaries({
    'connectionId': st.just('conn-1'),
    'userId': st.just('user-1'),
    'questionId': st.just('q-1'),
    'questionText': st.just('text'),
}))
@settings(max_examples=100)
def test_property_missing_key_defaults_to_empty(data):
    """Property 4: For any dict without composedPrompt key, from_dict produces composed_prompt == ''."""
    assert 'composedPrompt' not in data
    restored = ConversationState.from_dict(data)
    assert restored.composed_prompt == ""
