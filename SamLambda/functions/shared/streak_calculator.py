"""
Streak calculation logic for video submission tracking.
Pure functions with no AWS dependencies for easy testing.
"""
from typing import Tuple, Optional

MILESTONES = [7, 30, 100]

def calculate_new_streak(
    current_streak: int,
    days_since_last: int,
    freeze_available: bool,
    last_video_date: str,
    current_date: str
) -> Tuple[int, bool, bool]:
    """
    Calculate new streak based on days since last video.
    
    Args:
        current_streak: Current streak count
        days_since_last: Days between last video and today
        freeze_available: Whether streak freeze is available
        last_video_date: Last video submission date (ISO format)
        current_date: Current date (ISO format)
    
    Returns:
        Tuple of (new_streak, freeze_used, freeze_available)
    """
    # Same day - no change
    if days_since_last == 0 or last_video_date == current_date:
        return current_streak, False, freeze_available
    
    # Exactly one day - increment streak
    if days_since_last == 1:
        return current_streak + 1, False, freeze_available
    
    # More than one day - check freeze
    if days_since_last > 1:
        if freeze_available:
            # Use freeze - maintain streak
            return current_streak, True, False
        else:
            # Reset streak to 1 (today's video counts)
            return 1, False, freeze_available
    
    return current_streak, False, freeze_available

def check_milestone(streak_count: int, previous_streak: int) -> Optional[int]:
    """Check if a milestone was just hit. Returns milestone value or None."""
    for milestone in MILESTONES:
        if streak_count >= milestone and previous_streak < milestone:
            return milestone
    return None
