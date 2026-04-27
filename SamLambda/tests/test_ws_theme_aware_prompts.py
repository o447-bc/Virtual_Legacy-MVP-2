"""
Unit and property tests for WebSocket Lambda theme-aware prompt logic.
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5, 4.6, 4.8, 7.4

Tests cover:
- SafeDict.__missing__ behaviour
- handle_start_conversation theme metadata fetch and prompt composition
- handle_user_response / handle_audio_response composed prompt usage
- Property 3: SafeDict prompt composition preserves {question}
- Property 2: questionId type derivation
"""
import sys
import os
import importlib
from unittest.mock import patch, MagicMock, call

import pytest

# ---------------------------------------------------------------------------
# Import app with mocked sibling modules (same pattern as test_level1_tracking)
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

_saved = {name: sys.modules.get(name) for name in _SIBLING_MODS}

for _mod in _SIBLING_MODS:
    sys.modules[_mod] = MagicMock()

_ws_default_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'conversationFunctions', 'wsDefault')
)
if _ws_default_dir not in sys.path:
    sys.path.insert(0, _ws_default_dir)

# Force fresh import to pick up our mocked modules
if 'app' in sys.modules:
    del sys.modules['app']

import importlib.util
_spec = importlib.util.spec_from_file_location(
    'wsdefault_app_theme',
    os.path.join(_ws_default_dir, 'app.py'),
)
app = importlib.util.module_from_spec(_spec)
sys.modules['wsdefault_app_theme'] = app
_spec.loader.exec_module(app)

# Restore original modules
for _mod in _SIBLING_MODS:
    if _saved[_mod] is not None:
        sys.modules[_mod] = _saved[_mod]
    else:
        sys.modules.pop(_mod, None)


# ---------------------------------------------------------------------------
# Unit tests — Task 4.4
# ---------------------------------------------------------------------------

class TestSafeDict:
    """Test SafeDict.__missing__ returns '{key}' for unknown keys."""

    def test_missing_returns_placeholder(self):
        sd = app.SafeDict(a=1)
        assert sd['b'] == '{b}'

    def test_known_key_returned_normally(self):
        sd = app.SafeDict(theme_name='Childhood')
        assert sd['theme_name'] == 'Childhood'

    def test_missing_question_key(self):
        sd = app.SafeDict(theme_name='X', theme_description='Y')
        assert sd['question'] == '{question}'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_config(system_prompt="You are interviewing about {theme_name}. {theme_description} Question: {question}"):
    return {
        'system_prompt': system_prompt,
        'scoring_prompt': 'score this',
        'score_goal': 12,
        'max_turns': 20,
        'llm_conversation_model': 'model-conv',
        'llm_scoring_model': 'model-score',
        'polly_voice_id': 'Joanna',
        'polly_engine': 'neural',
    }


def _mock_dynamodb_with_theme(theme_name='Childhood Memories', prompt_description='Focus on early memories'):
    """Return a mock _dynamodb resource that returns theme metadata from get_item."""
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        'Item': {
            'questionId': 'childhood-memories-3',
            'questionType': 'childhood-memories',
            'themeName': theme_name,
            'promptDescription': prompt_description,
        }
    }
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table
    return mock_db, mock_table


def _mock_dynamodb_error():
    """Return a mock _dynamodb resource that raises on get_item."""
    mock_table = MagicMock()
    mock_table.get_item.side_effect = Exception('DynamoDB is down')
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table
    return mock_db


def _mock_dynamodb_no_attributes():
    """Return a mock _dynamodb resource that returns an item with no themeName/promptDescription."""
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        'Item': {
            'questionId': 'childhood-memories-3',
            'questionType': 'childhood-memories',
        }
    }
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table
    return mock_db, mock_table


class TestHandleStartConversationTheme:
    """Test handle_start_conversation fetches theme metadata and composes prompt."""

    @patch.object(app, 'check_question_category_access', return_value={'allowed': True})
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'text_to_speech', return_value='https://audio.url')
    @patch.object(app, 'send_message')
    def test_fetches_theme_and_composes_prompt(self, mock_send, mock_tts, mock_set_conv, mock_access):
        mock_db, mock_table = _mock_dynamodb_with_theme('Childhood Memories', 'Focus on early memories')
        config = _mock_config()

        with patch.object(app, '_dynamodb', mock_db):
            app.handle_start_conversation(
                'conn-1', 'user-1',
                {'questionId': 'childhood-memories-3', 'questionText': 'What is your earliest memory?'},
                config,
            )

        # Verify DynamoDB was called with correct keys
        mock_table.get_item.assert_called_once_with(
            Key={'questionId': 'childhood-memories-3', 'questionType': 'childhood-memories'}
        )

        # Verify composed prompt was stored in state
        state_arg = mock_set_conv.call_args[0][1]
        assert 'Childhood Memories' in state_arg.composed_prompt
        assert 'Focus on early memories' in state_arg.composed_prompt
        assert '{question}' in state_arg.composed_prompt

    @patch.object(app, 'check_question_category_access', return_value={'allowed': True})
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'text_to_speech', return_value='https://audio.url')
    @patch.object(app, 'send_message')
    def test_falls_back_on_get_item_error(self, mock_send, mock_tts, mock_set_conv, mock_access):
        mock_db = _mock_dynamodb_error()
        config = _mock_config()

        with patch.object(app, '_dynamodb', mock_db):
            app.handle_start_conversation(
                'conn-1', 'user-1',
                {'questionId': 'childhood-memories-3', 'questionText': 'What is your earliest memory?'},
                config,
            )

        # Should still succeed — composed prompt uses empty strings
        state_arg = mock_set_conv.call_args[0][1]
        assert state_arg.composed_prompt is not None
        assert '{question}' in state_arg.composed_prompt

    @patch.object(app, 'check_question_category_access', return_value={'allowed': True})
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'text_to_speech', return_value='https://audio.url')
    @patch.object(app, 'send_message')
    def test_handles_missing_attributes(self, mock_send, mock_tts, mock_set_conv, mock_access):
        mock_db, _ = _mock_dynamodb_no_attributes()
        config = _mock_config()

        with patch.object(app, '_dynamodb', mock_db):
            app.handle_start_conversation(
                'conn-1', 'user-1',
                {'questionId': 'childhood-memories-3', 'questionText': 'What is your earliest memory?'},
                config,
            )

        state_arg = mock_set_conv.call_args[0][1]
        # Theme placeholders should be substituted with empty strings
        assert '{theme_name}' not in state_arg.composed_prompt
        assert '{theme_description}' not in state_arg.composed_prompt
        assert '{question}' in state_arg.composed_prompt

    @patch.object(app, 'check_question_category_access', return_value={'allowed': True})
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'text_to_speech', return_value='https://audio.url')
    @patch.object(app, 'send_message')
    def test_question_type_derivation_with_hyphens(self, mock_send, mock_tts, mock_set_conv, mock_access):
        """childhood-memories-3 → childhood-memories"""
        mock_db, mock_table = _mock_dynamodb_with_theme()
        config = _mock_config()

        with patch.object(app, '_dynamodb', mock_db):
            app.handle_start_conversation(
                'conn-1', 'user-1',
                {'questionId': 'childhood-memories-3', 'questionText': 'Q?'},
                config,
            )

        mock_table.get_item.assert_called_once_with(
            Key={'questionId': 'childhood-memories-3', 'questionType': 'childhood-memories'}
        )

    @patch.object(app, 'check_question_category_access', return_value={'allowed': True})
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'text_to_speech', return_value='https://audio.url')
    @patch.object(app, 'send_message')
    def test_curly_braces_in_theme_values(self, mock_send, mock_tts, mock_set_conv, mock_access):
        """Theme values with literal curly braces should not cause KeyError."""
        mock_db, _ = _mock_dynamodb_with_theme(
            theme_name='Test Theme',
            prompt_description='Focus on {family} dynamics',
        )
        config = _mock_config()

        with patch.object(app, '_dynamodb', mock_db):
            app.handle_start_conversation(
                'conn-1', 'user-1',
                {'questionId': 'test-3', 'questionText': 'Q?'},
                config,
            )

        state_arg = mock_set_conv.call_args[0][1]
        assert '{family}' in state_arg.composed_prompt
        assert '{question}' in state_arg.composed_prompt


# ---------------------------------------------------------------------------
# Tests for handle_user_response composed prompt usage
# ---------------------------------------------------------------------------

class TestHandleUserResponseComposedPrompt:

    @patch.object(app, 'send_message')
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'process_user_response_parallel', return_value=('AI reply', 5.0, 'good'))
    @patch.object(app, 'get_conversation')
    def test_uses_composed_prompt_when_set(self, mock_get_conv, mock_parallel, mock_set_conv, mock_send):
        state = app.ConversationState('conn-1', 'user-1', 'q-1', 'Question?')
        state.composed_prompt = 'Themed prompt with {question}'
        mock_get_conv.return_value = state
        config = _mock_config()

        app.handle_user_response('conn-1', 'user-1', {'text': 'My answer'}, config)

        # The 4th positional arg to process_user_response_parallel is system_prompt
        call_args = mock_parallel.call_args[0]
        assert call_args[3] == 'Themed prompt with {question}'

    @patch.object(app, 'send_message')
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'process_user_response_parallel', return_value=('AI reply', 5.0, 'good'))
    @patch.object(app, 'get_conversation')
    def test_falls_back_to_config_when_empty(self, mock_get_conv, mock_parallel, mock_set_conv, mock_send):
        state = app.ConversationState('conn-1', 'user-1', 'q-1', 'Question?')
        state.composed_prompt = ''
        mock_get_conv.return_value = state
        config = _mock_config()

        app.handle_user_response('conn-1', 'user-1', {'text': 'My answer'}, config)

        call_args = mock_parallel.call_args[0]
        assert call_args[3] == config['system_prompt']


# ---------------------------------------------------------------------------
# Tests for handle_audio_response composed prompt usage
# ---------------------------------------------------------------------------

class TestHandleAudioResponseComposedPrompt:

    @patch.object(app, 'send_message')
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'process_user_response_parallel', return_value=('AI reply', 5.0, 'good'))
    @patch.object(app, 'transcribe_audio_deepgram', return_value={'transcript': 'Hello', 'audio_url': 'url'})
    @patch.object(app, 'get_conversation')
    def test_uses_composed_prompt_when_set(self, mock_get_conv, mock_transcribe, mock_parallel, mock_set_conv, mock_send):
        state = app.ConversationState('conn-1', 'user-1', 'q-1', 'Question?')
        state.composed_prompt = 'Themed prompt with {question}'
        mock_get_conv.return_value = state
        config = _mock_config()

        app.handle_audio_response('conn-1', 'user-1', {'s3Key': 'audio/key.webm'}, config)

        call_args = mock_parallel.call_args[0]
        assert call_args[3] == 'Themed prompt with {question}'

    @patch.object(app, 'send_message')
    @patch.object(app, 'set_conversation')
    @patch.object(app, 'process_user_response_parallel', return_value=('AI reply', 5.0, 'good'))
    @patch.object(app, 'transcribe_audio_deepgram', return_value={'transcript': 'Hello', 'audio_url': 'url'})
    @patch.object(app, 'get_conversation')
    def test_falls_back_to_config_when_empty(self, mock_get_conv, mock_transcribe, mock_parallel, mock_set_conv, mock_send):
        state = app.ConversationState('conn-1', 'user-1', 'q-1', 'Question?')
        state.composed_prompt = ''
        mock_get_conv.return_value = state
        config = _mock_config()

        app.handle_audio_response('conn-1', 'user-1', {'s3Key': 'audio/key.webm'}, config)

        call_args = mock_parallel.call_args[0]
        assert call_args[3] == config['system_prompt']


# ---------------------------------------------------------------------------
# Property tests — Task 4.5
# Feature: theme-aware-ai-prompts, Property 3: SafeDict Prompt Composition
# Preserves {question} and Substitutes Theme Values
# **Validates: Requirements 4.1, 4.2, 4.3, 4.8**
# ---------------------------------------------------------------------------

from hypothesis import given, settings as h_settings, HealthCheck
import hypothesis.strategies as st


@given(
    theme_name=st.text(),
    theme_description=st.text(),
)
@h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_property_safedict_composition_preserves_question(theme_name, theme_description):
    """Property 3: SafeDict Prompt Composition Preserves {question} and Substitutes Theme Values.

    For any theme_name/theme_description (including strings with literal curly braces):
    - {question} is preserved as a literal placeholder in the output
    - {theme_name} is substituted with the escaped theme_name value
    - {theme_description} is substituted with the escaped theme_description value
    - No KeyError is raised
    - After a second .format(question=...) pass, the original theme values appear in the final output
    """
    base_prompt = "You are interviewing about {theme_name}. {theme_description} Question: {question}"

    escaped_name = theme_name.replace('{', '{{').replace('}', '}}')
    escaped_desc = theme_description.replace('{', '{{').replace('}', '}}')

    # This must not raise
    result = base_prompt.format_map(
        app.SafeDict(theme_name=escaped_name, theme_description=escaped_desc)
    )

    # {question} must survive as a literal placeholder
    assert '{question}' in result

    # The escaped values must appear in the composed prompt
    assert escaped_name in result
    assert escaped_desc in result

    # The original placeholders must not remain
    assert '{theme_name}' not in result
    assert '{theme_description}' not in result

    # After the second formatting pass (simulating generate_ai_response),
    # the original unescaped theme values must appear in the final output
    final = result.format(question='test question')
    assert theme_name in final
    assert theme_description in final
    assert 'test question' in final


# ---------------------------------------------------------------------------
# Property tests — Task 4.6
# Feature: theme-aware-ai-prompts, Property 2: questionId Type Derivation
# **Validates: Requirements 3.1**
# ---------------------------------------------------------------------------

@given(
    type_prefix=st.from_regex(r'[a-z]+(-[a-z]+)*', fullmatch=True),
    number=st.from_regex(r'[0-9]+', fullmatch=True),
)
@h_settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_property_question_id_type_derivation(type_prefix, number):
    """Property 2: questionId Type Derivation.

    For any valid questionId in format "{type}-{number}" (where type may contain hyphens),
    questionId.rsplit('-', 1)[0] SHALL produce the correct questionType prefix.
    """
    question_id = f"{type_prefix}-{number}"
    derived_type = question_id.rsplit('-', 1)[0]
    assert derived_type == type_prefix
