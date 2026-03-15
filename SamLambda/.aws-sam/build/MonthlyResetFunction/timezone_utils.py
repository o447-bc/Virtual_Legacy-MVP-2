"""
Timezone utilities for streak tracking system.
Handles timezone-aware date calculations with caching for performance.
"""
import pytz
from datetime import datetime
from typing import Optional
import boto3
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_timezone(user_id: str) -> str:
    """Fetch user timezone with caching. Returns 'UTC' if not found."""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('userStatusDB')
        response = table.get_item(Key={'userId': user_id})
        
        if 'Item' in response and 'timeZone' in response['Item']:
            return response['Item']['timeZone']
        return 'UTC'
    except Exception as e:
        print(f"Error fetching timezone for {user_id}: {e}")
        return 'UTC'

def get_current_date_in_timezone(timezone_str: str) -> str:
    """Returns current date in ISO format (YYYY-MM-DD) for given timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Invalid timezone {timezone_str}, using UTC: {e}")
        return datetime.now(pytz.UTC).strftime('%Y-%m-%d')

def calculate_days_between(date1_str: str, date2_str: str) -> int:
    """Calculate days between two ISO date strings."""
    try:
        date1 = datetime.fromisoformat(date1_str)
        date2 = datetime.fromisoformat(date2_str)
        return abs((date2 - date1).days)
    except Exception as e:
        print(f"Error calculating days between {date1_str} and {date2_str}: {e}")
        return 0

def is_first_of_month(timezone_str: str) -> bool:
    """Check if today is the first day of the month in given timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now.day == 1
    except Exception:
        return False
