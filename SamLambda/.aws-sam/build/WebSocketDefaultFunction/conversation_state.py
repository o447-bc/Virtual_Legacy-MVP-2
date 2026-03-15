"""
Conversation State Management
Tracks conversation progress, turns, scores, and history
"""

import json
import time
from typing import Dict, List, Optional

class ConversationState:
    """Manages state for a single conversation session"""
    
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
    
    def add_turn(self, user_text: str, ai_response: str, turn_score: float, reasoning: str):
        """Add a conversation turn"""
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
        """Check if conversation should continue"""
        if self.cumulative_score >= score_goal:
            return False, 'score_goal_reached'
        if self.turn_number >= max_turns:
            return False, 'max_turns_reached'
        return True, None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
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
            'completionReason': self.completion_reason
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

# In-memory cache for active conversations (Lambda container reuse)
_active_conversations: Dict[str, ConversationState] = {}

def get_conversation(connection_id: str) -> Optional[ConversationState]:
    """Get active conversation by connection ID"""
    return _active_conversations.get(connection_id)

def set_conversation(connection_id: str, state: ConversationState):
    """Store conversation state"""
    _active_conversations[connection_id] = state

def remove_conversation(connection_id: str):
    """Remove conversation from cache"""
    _active_conversations.pop(connection_id, None)
