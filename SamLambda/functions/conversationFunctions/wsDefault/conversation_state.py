"""
Conversation State Management
Tracks conversation progress, turns, scores, and history.
State is persisted in DynamoDB so it survives across Lambda container instances.
"""

import json
import os
import time
import boto3
from decimal import Decimal
from typing import Dict, List, Optional


def _get_table():
    """Return the DynamoDB Table resource for conversation state."""
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('CONVERSATION_STATE_TABLE', 'ConversationStateDB')
    return dynamodb.Table(table_name)


def _decimals_to_floats(obj):
    """Recursively convert Decimal values to int/float for JSON compatibility."""
    if isinstance(obj, list):
        return [_decimals_to_floats(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimals_to_floats(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _floats_to_decimals(obj):
    """Recursively convert float values to Decimal for DynamoDB storage."""
    if isinstance(obj, list):
        return [_floats_to_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj


class ConversationState:
    """Manages state for a single conversation session."""

    def __init__(self, connection_id: str, user_id: str, question_id: str, question_text: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.question_id = question_id
        self.question_text = question_text
        self.turn_number = 0
        self.cumulative_score = 0.0
        self.turns = []  # List of {turn, user_text, ai_text, score, reasoning}
        self.started_at = int(time.time())
        self.completed = False
        self.completion_reason = None
        self.composed_prompt = ""

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationState':
        """Reconstruct a ConversationState from a DynamoDB item dict."""
        # Convert any Decimal values that DynamoDB returns
        data = _decimals_to_floats(data)

        state = cls.__new__(cls)
        state.connection_id = data['connectionId']
        state.user_id = data['userId']
        state.question_id = data['questionId']
        state.question_text = data['questionText']
        state.turn_number = int(data.get('turnNumber', 0))
        state.cumulative_score = float(data.get('cumulativeScore', 0.0))
        state.turns = data.get('turns', [])
        state.started_at = int(data.get('startedAt', 0))
        state.completed = bool(data.get('completed', False))
        state.completion_reason = data.get('completionReason')
        state.composed_prompt = data.get('composedPrompt', '')
        return state

    def add_turn(self, user_text: str, ai_response: str, turn_score: float, reasoning: str):
        """Add a conversation turn."""
        self.turn_number += 1
        self.cumulative_score += turn_score

        self.turns.append({
            'turn': self.turn_number,
            'user_text': user_text,
            'ai_response': ai_response,
            'turn_score': turn_score,
            'cumulative_score': self.cumulative_score,
            'reasoning': reasoning,
            'timestamp': int(time.time())
        })

    def should_continue(self, score_goal: int, max_turns: int) -> tuple[bool, Optional[str]]:
        """Check if conversation should continue."""
        if self.cumulative_score >= score_goal:
            return False, 'score_goal_reached'
        if self.turn_number >= max_turns:
            return False, 'max_turns_reached'
        return True, None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/serialisation."""
        return {
            'connectionId': self.connection_id,
            'userId': self.user_id,
            'questionId': self.question_id,
            'questionText': self.question_text,
            'turnNumber': self.turn_number,
            'cumulativeScore': self.cumulative_score,
            'turns': self.turns,
            'startedAt': self.started_at,
            'completed': self.completed,
            'completionReason': self.completion_reason,
            'composedPrompt': self.composed_prompt
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# TTL: 2 hours — enough for any realistic conversation session
_STATE_TTL_SECONDS = 7200


def get_conversation(connection_id: str) -> Optional[ConversationState]:
    """Fetch conversation state from DynamoDB by connection ID."""
    try:
        table = _get_table()
        response = table.get_item(Key={'connectionId': connection_id})
        item = response.get('Item')
        if not item:
            return None
        return ConversationState.from_dict(item)
    except Exception as e:
        print(f"[STATE] Error getting conversation {connection_id}: {e}")
        return None


def set_conversation(connection_id: str, state: ConversationState):
    """Persist conversation state to DynamoDB."""
    try:
        table = _get_table()
        item = _floats_to_decimals(state.to_dict())
        item['ttl'] = int(time.time()) + _STATE_TTL_SECONDS
        table.put_item(Item=item)
    except Exception as e:
        print(f"[STATE] Error saving conversation {connection_id}: {e}")
        raise


def remove_conversation(connection_id: str):
    """Delete conversation state from DynamoDB."""
    try:
        table = _get_table()
        table.delete_item(Key={'connectionId': connection_id})
    except Exception as e:
        # Non-fatal — TTL will clean it up eventually
        print(f"[STATE] Error removing conversation {connection_id}: {e}")
