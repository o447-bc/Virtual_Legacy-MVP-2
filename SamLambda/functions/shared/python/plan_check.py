"""
Shared plan-check utility for subscription access enforcement.

Used by WebSocketDefaultFunction, CreateAssignmentFunction, and BillingFunction
to verify a user's subscription tier before allowing operations.

Design principle: FAIL-OPEN on all DynamoDB/SSM errors — never block users
due to billing infrastructure issues. Log the error and allow access.
"""
import os
import json
import logging

import boto3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
_dynamodb = boto3.resource('dynamodb')
_ssm = boto3.client('ssm')

_TABLE_NAME = os.environ.get('TABLE_SUBSCRIPTIONS', 'UserSubscriptionsDB')

# ---------------------------------------------------------------------------
# Module-level SSM cache (survives warm Lambda invocations)
# ---------------------------------------------------------------------------
_plan_cache: dict = {}
_plans_loaded: bool = False

# ---------------------------------------------------------------------------
# Default free-plan record returned when no subscription exists
# ---------------------------------------------------------------------------
_FREE_PLAN_DEFAULT = {
    'userId': None,
    'planId': 'free',
    'status': 'active',
    'benefactorCount': 0,
    'trialExpiresAt': None,
}


# ===================================================================
# SSM plan-definition helpers
# ===================================================================

def _load_all_plans() -> None:
    """Batch-load free + premium plan definitions from SSM in one call."""
    global _plans_loaded
    if _plans_loaded:
        return
    try:
        resp = _ssm.get_parameters(
            Names=['/soulreel/plans/free', '/soulreel/plans/premium']
        )
        for param in resp.get('Parameters', []):
            plan_id = param['Name'].split('/')[-1]
            _plan_cache[plan_id] = json.loads(param['Value'])
        _plans_loaded = True
    except Exception as exc:
        logger.error('[PLAN_CHECK] Failed to load plan definitions from SSM: %s', exc)


def _get_plan_definition(plan_id: str) -> dict:
    """Return the plan definition for *plan_id*, falling back to a minimal free default."""
    _load_all_plans()
    if plan_id in _plan_cache:
        return _plan_cache[plan_id]
    # Fallback: if SSM failed or plan_id is unknown, return a safe free default
    return {
        'planId': 'free',
        'allowedQuestionCategories': ['life_story_reflections_L1'],
        'maxBenefactors': 2,
        'accessConditionTypes': ['immediate'],
        'features': ['basic'],
    }


# ===================================================================
# Question-ID parsing
# ===================================================================

def _parse_question_id(question_id: str) -> tuple:
    """
    Parse a question ID into (category, level).

    Pattern: ``{category_parts}-{subcategory}-L{level}-Q{number}``
    Example: ``life_story_reflections-general-L2-Q5`` → ``('life_story_reflections', 2)``

    If no ``L{n}`` segment is found the default level is 1.
    """
    parts = question_id.split('-')
    category_parts: list = []
    level = 1
    for part in parts:
        if part.startswith('L') and len(part) > 1 and part[1:].isdigit():
            level = int(part[1:])
            break
        category_parts.append(part)
    # Rejoin with underscores — the first segment is the true category
    # e.g. ['life_story_reflections', 'general'] → 'life_story_reflections'
    # The category is the first part only (underscore-delimited within itself)
    category = category_parts[0] if category_parts else question_id
    return category, level


# ===================================================================
# Subscription record helpers
# ===================================================================

def get_user_plan(user_id: str) -> dict:
    """
    Read the user's subscription record from UserSubscriptionsDB.

    Returns the DynamoDB item dict, or a free-plan default if no record
    exists or if DynamoDB is unreachable (fail-open).
    """
    try:
        table = _dynamodb.Table(_TABLE_NAME)
        resp = table.get_item(Key={'userId': user_id})
        item = resp.get('Item')
        if item:
            return item
    except Exception as exc:
        logger.error('[PLAN_CHECK] DynamoDB error reading subscription for %s: %s', user_id, exc)

    # No record or error → free-plan default
    return {**_FREE_PLAN_DEFAULT, 'userId': user_id}


def is_trial_active(subscription_record: dict) -> bool:
    """Return True when the record represents an active (non-expired) trial."""
    if subscription_record.get('status') != 'trialing':
        return False
    expires_at = subscription_record.get('trialExpiresAt')
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return expiry > datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        return False


def is_premium_active(subscription_record: dict) -> bool:
    """Return True when the user should be treated as having Premium access."""
    status = subscription_record.get('status')
    if status in ('active', 'comped'):
        return True
    if status == 'trialing' and is_trial_active(subscription_record):
        return True
    return False


# ===================================================================
# Access-check public API
# ===================================================================

def check_question_category_access(user_id: str, question_id: str) -> dict:
    """
    Verify whether *user_id* may start a conversation for *question_id*.

    Returns ``{'allowed': True}`` or
    ``{'allowed': False, 'reason': ..., 'message': ...}``.

    Fail-open: any internal error returns ``{'allowed': True}``.
    """
    try:
        record = get_user_plan(user_id)

        # Premium users have unrestricted access
        if is_premium_active(record):
            return {'allowed': True, 'reason': None, 'message': None}

        plan_def = _get_plan_definition(record.get('planId', 'free'))
        allowed_categories = plan_def.get('allowedQuestionCategories', [])

        category, level = _parse_question_id(question_id)

        # Check 1: is the full category allowed (no level suffix)?
        if category in allowed_categories:
            return {'allowed': True, 'reason': None, 'message': None}

        # Check 2: is a level-restricted variant allowed?
        for entry in allowed_categories:
            if entry.startswith(category + '_L'):
                # e.g. 'life_story_reflections_L1'
                try:
                    allowed_level = int(entry.split('_L')[-1])
                except (ValueError, IndexError):
                    continue
                if level <= allowed_level:
                    return {'allowed': True, 'reason': None, 'message': None}
                else:
                    # Level too high
                    return {
                        'allowed': False,
                        'reason': 'question_level',
                        'message': (
                            "You've explored the first chapter. "
                            "Upgrade to Premium to go deeper into your life story."
                        ),
                    }

        # Category not in the allowed list at all
        return {
            'allowed': False,
            'reason': 'question_category',
            'message': (
                "Life Events questions are available with Premium. "
                "Upgrade to preserve the moments that shaped who you are."
            ),
        }

    except Exception as exc:
        logger.error('[PLAN_CHECK] Error in check_question_category_access for %s: %s', user_id, exc)
        return {'allowed': True, 'reason': None, 'message': None}


def check_benefactor_limit(user_id: str) -> dict:
    """
    Verify whether *user_id* may add another benefactor.

    Returns ``{'allowed': True, ...}`` or ``{'allowed': False, ...}``
    with ``message``, ``currentCount``, and ``limit`` keys.

    Fail-open: any internal error returns ``{'allowed': True, ...}``.
    """
    try:
        record = get_user_plan(user_id)
        plan_def = _get_plan_definition(record.get('planId', 'free'))

        max_benefactors = plan_def.get('maxBenefactors', 2)
        current_count = int(record.get('benefactorCount', 0))

        # -1 means unlimited
        if max_benefactors == -1:
            return {
                'allowed': True,
                'message': None,
                'currentCount': current_count,
                'limit': max_benefactors,
            }

        if current_count >= max_benefactors:
            return {
                'allowed': False,
                'message': (
                    f"You've chosen {max_benefactors} people to receive your legacy. "
                    "Upgrade to share your story with everyone who matters."
                ),
                'currentCount': current_count,
                'limit': max_benefactors,
            }

        return {
            'allowed': True,
            'message': None,
            'currentCount': current_count,
            'limit': max_benefactors,
        }

    except Exception as exc:
        logger.error('[PLAN_CHECK] Error in check_benefactor_limit for %s: %s', user_id, exc)
        return {
            'allowed': True,
            'message': None,
            'currentCount': 0,
            'limit': -1,
        }
