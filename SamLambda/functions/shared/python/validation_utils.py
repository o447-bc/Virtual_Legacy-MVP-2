"""
Validation utilities for access conditions in Legacy Maker Benefactor Assignment feature.
Provides validation functions for time-delayed dates, inactivity durations, and access conditions.
"""
from datetime import datetime
from typing import List, Dict, Tuple, Any
from datetime import timezone


def validate_time_delayed_date(activation_date: str) -> Tuple[bool, str]:
    """
    Validate that a time-delayed activation date is in the future.
    
    Args:
        activation_date: ISO 8601 formatted datetime string (e.g., "2026-03-15T10:00:00Z")
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if date is valid and in the future
        - (False, error_message) if date is invalid or in the past
    
    Requirements: 2.6
    """
    if not activation_date:
        return False, "Activation date is required for time-delayed access"
    
    try:
        # Parse the ISO 8601 datetime string
        activation_dt = datetime.fromisoformat(activation_date.replace('Z', '+00:00'))
        
        # Ensure timezone awareness
        if activation_dt.tzinfo is None:
            activation_dt = activation_dt.replace(tzinfo=timezone.utc)
        
        # Get current time in UTC
        current_dt = datetime.now(timezone.utc)
        
        # Check if activation date is in the future
        if activation_dt <= current_dt:
            return False, f"Activation date must be in the future. Provided: {activation_date}, Current: {current_dt.isoformat()}"
        
        return True, ""
    
    except (ValueError, AttributeError) as e:
        return False, f"Invalid date format. Expected ISO 8601 format (e.g., '2026-03-15T10:00:00Z'). Error: {str(e)}"


def validate_inactivity_months(inactivity_months: int) -> Tuple[bool, str]:
    """
    Validate that inactivity trigger duration is within acceptable range (1-24 months).
    
    Args:
        inactivity_months: Number of months of inactivity before triggering access
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if duration is valid (1-24 months)
        - (False, error_message) if duration is invalid
    
    Requirements: 2.7
    """
    if inactivity_months is None:
        return False, "Inactivity months is required for inactivity trigger"
    
    try:
        months = int(inactivity_months)
        
        if months < 1:
            return False, "Inactivity months must be at least 1 month"
        
        if months > 24:
            return False, "Inactivity months cannot exceed 24 months"
        
        return True, ""
    
    except (ValueError, TypeError) as e:
        return False, f"Invalid inactivity months value. Expected integer between 1 and 24. Error: {str(e)}"


def validate_access_conditions(access_conditions: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validate that at least one access condition is provided and all conditions are properly formatted.
    
    Args:
        access_conditions: List of access condition dictionaries, each containing:
            - condition_type: 'immediate' | 'time_delayed' | 'inactivity_trigger' | 'manual_release'
            - activation_date: (optional) ISO 8601 string for time_delayed
            - inactivity_months: (optional) integer for inactivity_trigger
            - check_in_interval_days: (optional) integer for inactivity_trigger
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if conditions are valid
        - (False, error_message) if conditions are invalid
    
    Requirements: 1.2, 2.6, 2.7
    """
    # Check if access_conditions is provided and not empty
    if not access_conditions:
        return False, "At least one access condition is required"
    
    if not isinstance(access_conditions, list):
        return False, "Access conditions must be a list"
    
    # Valid condition types
    valid_condition_types = {'immediate', 'time_delayed', 'inactivity_trigger', 'manual_release'}
    
    # Validate each condition
    for idx, condition in enumerate(access_conditions):
        if not isinstance(condition, dict):
            return False, f"Access condition at index {idx} must be a dictionary"
        
        # Check condition_type is present and valid
        condition_type = condition.get('condition_type')
        if not condition_type:
            return False, f"Access condition at index {idx} is missing 'condition_type'"
        
        if condition_type not in valid_condition_types:
            return False, f"Invalid condition_type '{condition_type}' at index {idx}. Must be one of: {', '.join(valid_condition_types)}"
        
        # Validate time_delayed specific fields
        if condition_type == 'time_delayed':
            activation_date = condition.get('activation_date')
            is_valid, error_msg = validate_time_delayed_date(activation_date)
            if not is_valid:
                return False, f"Time-delayed condition at index {idx}: {error_msg}"
        
        # Validate inactivity_trigger specific fields
        if condition_type == 'inactivity_trigger':
            inactivity_months = condition.get('inactivity_months')
            is_valid, error_msg = validate_inactivity_months(inactivity_months)
            if not is_valid:
                return False, f"Inactivity trigger condition at index {idx}: {error_msg}"
            
            # Validate check_in_interval_days if provided
            check_in_interval = condition.get('check_in_interval_days')
            if check_in_interval is not None:
                try:
                    interval = int(check_in_interval)
                    if interval < 1:
                        return False, f"Inactivity trigger condition at index {idx}: check_in_interval_days must be at least 1 day"
                    if interval > 365:
                        return False, f"Inactivity trigger condition at index {idx}: check_in_interval_days cannot exceed 365 days"
                except (ValueError, TypeError):
                    return False, f"Inactivity trigger condition at index {idx}: check_in_interval_days must be a valid integer"
    
    return True, ""
