"""
Canonical Life Event Key Registry (Python)

Single source of truth for all valid Life_Event_Keys used across admin
Lambdas, survey Lambda, and assignment Lambda. Must stay in sync with
the TypeScript version at FrontEndCode/src/constants/lifeEventRegistry.ts.
"""

# All valid Life_Event_Keys organized by category
LIFE_EVENT_KEYS = [
    # Core Relationship & Family
    'got_married', 'had_children', 'became_grandparent',
    'death_of_child', 'death_of_parent', 'death_of_sibling',
    'death_of_friend_mentor', 'estranged_family_member',
    'infertility_or_pregnancy_loss', 'raised_child_special_needs',
    'falling_out_close_friend',
    # Education & Early Life
    'graduated_high_school', 'graduated_college', 'graduate_degree',
    'studied_abroad', 'influential_mentor',
    # Career & Professional
    'first_job', 'career_change', 'started_business',
    'got_fired', 'retired', 'became_mentor',
    # Health & Resilience
    'serious_illness', 'mental_health_challenge', 'caregiver',
    'addiction_recovery', 'financial_hardship', 'major_legal_issue',
    # Relocation & Transitions
    'moved_city', 'immigrated', 'lived_abroad', 'learned_second_language',
    # Spiritual, Creative & Legacy
    'spiritual_awakening', 'changed_religion', 'creative_work',
    'major_award', 'experienced_discrimination',
    # Other
    'military_service', 'survived_disaster', 'near_death', 'act_of_kindness',
    # Status-derived (virtual — generated from got_married instance statuses)
    'spouse_divorced', 'spouse_deceased', 'spouse_still_married',
]

# Frozen set for O(1) lookups
_LIFE_EVENT_KEY_SET = frozenset(LIFE_EVENT_KEYS)

# Keys that support question instancing (per-person question stamping)
INSTANCEABLE_KEYS = [
    'got_married', 'had_children',
    'death_of_child', 'death_of_parent', 'death_of_sibling',
    'death_of_friend_mentor',
]

_INSTANCEABLE_KEY_SET = frozenset(INSTANCEABLE_KEYS)

# Valid placeholder tokens for instanceable questions
VALID_PLACEHOLDERS = ['{spouse_name}', '{child_name}', '{deceased_name}']

# Maps each instanceable key to its placeholder token
INSTANCEABLE_KEY_TO_PLACEHOLDER = {
    'got_married': '{spouse_name}',
    'had_children': '{child_name}',
    'death_of_child': '{deceased_name}',
    'death_of_parent': '{deceased_name}',
    'death_of_sibling': '{deceased_name}',
    'death_of_friend_mentor': '{deceased_name}',
}


def validate_life_event_keys(keys):
    """
    Validate a list of Life_Event_Key strings.

    Args:
        keys: list of strings to validate

    Returns:
        list of invalid keys (empty list if all valid)
    """
    if not keys:
        return []
    return [k for k in keys if k not in _LIFE_EVENT_KEY_SET]


def is_instanceable_key(key):
    """Check if a Life_Event_Key supports instancing."""
    return key in _INSTANCEABLE_KEY_SET


def get_placeholder_for_key(key):
    """
    Get the instance placeholder for an instanceable key.

    Returns:
        placeholder string (e.g., '{spouse_name}') or None if not instanceable
    """
    return INSTANCEABLE_KEY_TO_PLACEHOLDER.get(key)
