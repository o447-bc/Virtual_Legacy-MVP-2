"""
Configuration Management
Loads and caches SSM parameters
"""

import boto3
from typing import Dict

ssm = boto3.client('ssm')

# Cache for SSM parameters (Lambda container reuse)
_param_cache: Dict[str, str] = {}

_PARAM_NAMES = [
    '/virtuallegacy/conversation/score-goal',
    '/virtuallegacy/conversation/max-turns',
    '/virtuallegacy/conversation/llm-conversation-model',
    '/virtuallegacy/conversation/llm-scoring-model',
    '/virtuallegacy/conversation/system-prompt',
    '/virtuallegacy/conversation/scoring-prompt',
    '/virtuallegacy/conversation/polly-voice-id',
    '/virtuallegacy/conversation/polly-engine',
]

_DEFAULTS = {
    '/virtuallegacy/conversation/score-goal': '12',
    '/virtuallegacy/conversation/max-turns': '20',
    '/virtuallegacy/conversation/llm-conversation-model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    '/virtuallegacy/conversation/llm-scoring-model': 'anthropic.claude-3-haiku-20240307-v1:0',
    '/virtuallegacy/conversation/polly-voice-id': 'Joanna',
    '/virtuallegacy/conversation/polly-engine': 'neural',
}


def _load_all_params():
    """Batch-fetch all SSM parameters and populate cache."""
    try:
        response = ssm.get_parameters(Names=_PARAM_NAMES)
        for param in response.get('Parameters', []):
            _param_cache[param['Name']] = param['Value']
        # Apply defaults for any that were not found
        for name in _PARAM_NAMES:
            if name not in _param_cache and name in _DEFAULTS:
                _param_cache[name] = _DEFAULTS[name]
        # Log any invalid parameters
        for invalid in response.get('InvalidParameters', []):
            default = _DEFAULTS.get(invalid)
            if default:
                print(f"[CONFIG] Parameter not found, using default: {invalid}")
                _param_cache[invalid] = default
            else:
                print(f"[CONFIG] Required parameter missing and no default: {invalid}")
    except Exception as e:
        print(f"[CONFIG] Error batch-fetching SSM parameters: {e}")
        raise


def get_conversation_config() -> dict:
    """Load all conversation configuration parameters (batched, cached)."""
    if not _param_cache:
        _load_all_params()

    return {
        'score_goal': int(_param_cache.get('/virtuallegacy/conversation/score-goal', '12')),
        'max_turns': int(_param_cache.get('/virtuallegacy/conversation/max-turns', '20')),
        'llm_conversation_model': _param_cache.get(
            '/virtuallegacy/conversation/llm-conversation-model',
            'anthropic.claude-3-5-sonnet-20241022-v2:0'
        ),
        'llm_scoring_model': _param_cache.get(
            '/virtuallegacy/conversation/llm-scoring-model',
            'anthropic.claude-3-haiku-20240307-v1:0'
        ),
        'system_prompt': _param_cache['/virtuallegacy/conversation/system-prompt'],
        'scoring_prompt': _param_cache['/virtuallegacy/conversation/scoring-prompt'],
        'polly_voice_id': _param_cache.get('/virtuallegacy/conversation/polly-voice-id', 'Joanna'),
        'polly_engine': _param_cache.get('/virtuallegacy/conversation/polly-engine', 'neural'),
    }
