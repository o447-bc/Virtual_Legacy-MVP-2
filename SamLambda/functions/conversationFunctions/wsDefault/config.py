"""
Configuration Management
Loads and caches SSM parameters
"""

import boto3
from typing import Dict, Optional

ssm = boto3.client('ssm')

# Cache for SSM parameters (Lambda container reuse)
# Updated: 2025-01-12 - Using Claude 3.5 Sonnet v1
_param_cache: Dict[str, str] = {}

def get_parameter(name: str, default: Optional[str] = None) -> str:
    """Get SSM parameter with caching"""
    if name in _param_cache:
        return _param_cache[name]
    
    try:
        response = ssm.get_parameter(Name=name)
        value = response['Parameter']['Value']
        _param_cache[name] = value
        return value
    except Exception as e:
        print(f"[CONFIG] Error getting parameter {name}: {e}")
        if default is not None:
            return default
        raise

def get_conversation_config() -> Dict:
    """Load all conversation configuration parameters"""
    return {
        'score_goal': int(get_parameter('/virtuallegacy/conversation/score-goal', '12')),
        'max_turns': int(get_parameter('/virtuallegacy/conversation/max-turns', '20')),
        'llm_conversation_model': get_parameter(
            '/virtuallegacy/conversation/llm-conversation-model',
            'anthropic.claude-3-5-sonnet-20241022-v2:0'
        ),
        'llm_scoring_model': get_parameter(
            '/virtuallegacy/conversation/llm-scoring-model',
            'anthropic.claude-3-haiku-20240307-v1:0'
        ),
        'system_prompt': get_parameter('/virtuallegacy/conversation/system-prompt'),
        'scoring_prompt': get_parameter('/virtuallegacy/conversation/scoring-prompt'),
        'polly_voice_id': get_parameter('/virtuallegacy/conversation/polly-voice-id', 'Joanna'),
        'polly_engine': get_parameter('/virtuallegacy/conversation/polly-engine', 'neural')
    }
