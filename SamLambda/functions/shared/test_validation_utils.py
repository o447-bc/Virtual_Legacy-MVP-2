"""
Unit tests for validation_utils module.

Tests validation functions for access conditions, time-delayed dates,
and inactivity durations.
"""
import unittest
from datetime import datetime, timedelta
import pytz
from validation_utils import (
    validate_time_delayed_date,
    validate_inactivity_months,
    validate_access_conditions
)


class TestValidateTimeDelayedDate(unittest.TestCase):
    """Test time-delayed date validation."""
    
    def test_valid_future_date(self):
        """Test that a future date is valid."""
        future_date = (datetime.now(pytz.UTC) + timedelta(days=30)).isoformat()
        is_valid, error_msg = validate_time_delayed_date(future_date)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_past_date_rejected(self):
        """Test that a past date is rejected."""
        past_date = (datetime.now(pytz.UTC) - timedelta(days=1)).isoformat()
        is_valid, error_msg = validate_time_delayed_date(past_date)
        self.assertFalse(is_valid)
        self.assertIn("must be in the future", error_msg)
    
    def test_current_time_rejected(self):
        """Test that current time is rejected (must be future)."""
        current_date = datetime.now(pytz.UTC).isoformat()
        is_valid, error_msg = validate_time_delayed_date(current_date)
        self.assertFalse(is_valid)
        self.assertIn("must be in the future", error_msg)
    
    def test_empty_date_rejected(self):
        """Test that empty date is rejected."""
        is_valid, error_msg = validate_time_delayed_date("")
        self.assertFalse(is_valid)
        self.assertIn("required", error_msg)
    
    def test_invalid_format_rejected(self):
        """Test that invalid date format is rejected."""
        is_valid, error_msg = validate_time_delayed_date("not-a-date")
        self.assertFalse(is_valid)
        self.assertIn("Invalid date format", error_msg)


class TestValidateInactivityMonths(unittest.TestCase):
    """Test inactivity months validation."""
    
    def test_valid_months_1_to_24(self):
        """Test that months 1-24 are valid."""
        for months in [1, 6, 12, 18, 24]:
            is_valid, error_msg = validate_inactivity_months(months)
            self.assertTrue(is_valid, f"Month {months} should be valid")
            self.assertEqual(error_msg, "")
    
    def test_zero_months_rejected(self):
        """Test that 0 months is rejected."""
        is_valid, error_msg = validate_inactivity_months(0)
        self.assertFalse(is_valid)
        self.assertIn("at least 1 month", error_msg)
    
    def test_negative_months_rejected(self):
        """Test that negative months are rejected."""
        is_valid, error_msg = validate_inactivity_months(-5)
        self.assertFalse(is_valid)
        self.assertIn("at least 1 month", error_msg)
    
    def test_over_24_months_rejected(self):
        """Test that over 24 months is rejected."""
        is_valid, error_msg = validate_inactivity_months(25)
        self.assertFalse(is_valid)
        self.assertIn("cannot exceed 24 months", error_msg)
    
    def test_none_value_rejected(self):
        """Test that None value is rejected."""
        is_valid, error_msg = validate_inactivity_months(None)
        self.assertFalse(is_valid)
        self.assertIn("required", error_msg)
    
    def test_string_value_rejected(self):
        """Test that string value is rejected."""
        is_valid, error_msg = validate_inactivity_months("twelve")
        self.assertFalse(is_valid)
        self.assertIn("Invalid inactivity months", error_msg)


class TestValidateAccessConditions(unittest.TestCase):
    """Test access conditions validation."""
    
    def test_immediate_access_valid(self):
        """Test that immediate access condition is valid."""
        conditions = [{'condition_type': 'immediate'}]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_time_delayed_with_future_date_valid(self):
        """Test that time-delayed with future date is valid."""
        future_date = (datetime.now(pytz.UTC) + timedelta(days=30)).isoformat()
        conditions = [{
            'condition_type': 'time_delayed',
            'activation_date': future_date
        }]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_time_delayed_with_past_date_rejected(self):
        """Test that time-delayed with past date is rejected."""
        past_date = (datetime.now(pytz.UTC) - timedelta(days=1)).isoformat()
        conditions = [{
            'condition_type': 'time_delayed',
            'activation_date': past_date
        }]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertFalse(is_valid)
        self.assertIn("must be in the future", error_msg)
    
    def test_inactivity_trigger_valid(self):
        """Test that inactivity trigger with valid months is valid."""
        conditions = [{
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 12,
            'check_in_interval_days': 30
        }]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_inactivity_trigger_invalid_months_rejected(self):
        """Test that inactivity trigger with invalid months is rejected."""
        conditions = [{
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 30
        }]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertFalse(is_valid)
        self.assertIn("cannot exceed 24 months", error_msg)
    
    def test_manual_release_valid(self):
        """Test that manual release condition is valid."""
        conditions = [{'condition_type': 'manual_release'}]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_multiple_conditions_valid(self):
        """Test that multiple valid conditions are accepted."""
        future_date = (datetime.now(pytz.UTC) + timedelta(days=30)).isoformat()
        conditions = [
            {'condition_type': 'immediate'},
            {'condition_type': 'time_delayed', 'activation_date': future_date},
            {'condition_type': 'manual_release'}
        ]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_empty_conditions_rejected(self):
        """Test that empty conditions list is rejected."""
        is_valid, error_msg = validate_access_conditions([])
        self.assertFalse(is_valid)
        self.assertIn("At least one access condition is required", error_msg)
    
    def test_none_conditions_rejected(self):
        """Test that None conditions is rejected."""
        is_valid, error_msg = validate_access_conditions(None)
        self.assertFalse(is_valid)
        self.assertIn("At least one access condition is required", error_msg)
    
    def test_invalid_condition_type_rejected(self):
        """Test that invalid condition type is rejected."""
        conditions = [{'condition_type': 'invalid_type'}]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertFalse(is_valid)
        self.assertIn("Invalid condition_type", error_msg)
    
    def test_missing_condition_type_rejected(self):
        """Test that missing condition_type is rejected."""
        conditions = [{'some_field': 'value'}]
        is_valid, error_msg = validate_access_conditions(conditions)
        self.assertFalse(is_valid)
        self.assertIn("missing 'condition_type'", error_msg)


if __name__ == '__main__':
    unittest.main()
