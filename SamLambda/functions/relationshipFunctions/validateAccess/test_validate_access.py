"""
Unit tests for ValidateAccess Lambda function with access condition checking.

Tests verify that access validation correctly evaluates different condition types:
- immediate: always satisfied
- time_delayed: check if current_time >= activation_date
- inactivity_trigger: check if status is "activated"
- manual_release: check if released_at is set

Requirements: 2.1, 2.3, 8.4, 8.5, 12.3, 12.6
"""
import unittest
from datetime import datetime, timedelta
import pytz
import sys
import os
import importlib.util

# Load app.py under a unique module name to avoid sys.modules collision
# when pytest runs multiple Lambda test files in the same process
_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
_spec = importlib.util.spec_from_file_location('validate_access_app', _app_path)
_app = importlib.util.module_from_spec(_spec)
sys.modules['validate_access_app'] = _app
_shared = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../shared')
if _shared not in sys.path:
    sys.path.insert(0, os.path.abspath(_shared))
_spec.loader.exec_module(_app)

from validate_access_app import evaluate_access_conditions


class TestAccessConditionEvaluation(unittest.TestCase):
    """Test access condition evaluation logic"""
    
    def test_immediate_access_always_satisfied(self):
        """Test that immediate access conditions are always satisfied"""
        conditions = [
            {
                'condition_type': 'immediate',
                'status': 'pending'
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)
    
    def test_time_delayed_not_yet_reached(self):
        """Test that time_delayed access is denied before activation date"""
        future_date = (datetime.now(pytz.UTC) + timedelta(days=7)).isoformat()
        
        conditions = [
            {
                'condition_type': 'time_delayed',
                'activation_date': future_date,
                'status': 'pending'
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertFalse(all_satisfied)
        self.assertEqual(len(unmet), 1)
        self.assertEqual(unmet[0]['condition_type'], 'time_delayed')
        self.assertIn('activation_date', unmet[0])
    
    def test_time_delayed_already_reached(self):
        """Test that time_delayed access is granted after activation date"""
        past_date = (datetime.now(pytz.UTC) - timedelta(days=7)).isoformat()
        
        conditions = [
            {
                'condition_type': 'time_delayed',
                'activation_date': past_date,
                'status': 'pending'
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)
    
    def test_inactivity_trigger_not_activated(self):
        """Test that inactivity_trigger access is denied when status is pending"""
        conditions = [
            {
                'condition_type': 'inactivity_trigger',
                'status': 'pending',
                'inactivity_months': 6
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertFalse(all_satisfied)
        self.assertEqual(len(unmet), 1)
        self.assertEqual(unmet[0]['condition_type'], 'inactivity_trigger')
    
    def test_inactivity_trigger_activated(self):
        """Test that inactivity_trigger access is granted when status is activated"""
        conditions = [
            {
                'condition_type': 'inactivity_trigger',
                'status': 'activated',
                'inactivity_months': 6
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)
    
    def test_manual_release_not_released(self):
        """Test that manual_release access is denied when not released"""
        conditions = [
            {
                'condition_type': 'manual_release',
                'status': 'pending'
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertFalse(all_satisfied)
        self.assertEqual(len(unmet), 1)
        self.assertEqual(unmet[0]['condition_type'], 'manual_release')
    
    def test_manual_release_released(self):
        """Test that manual_release access is granted when released_at is set"""
        conditions = [
            {
                'condition_type': 'manual_release',
                'status': 'pending',
                'released_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)
    
    def test_multiple_conditions_all_satisfied(self):
        """Test that access is granted when all conditions are satisfied"""
        past_date = (datetime.now(pytz.UTC) - timedelta(days=7)).isoformat()
        
        conditions = [
            {
                'condition_type': 'immediate',
                'status': 'pending'
            },
            {
                'condition_type': 'time_delayed',
                'activation_date': past_date,
                'status': 'pending'
            },
            {
                'condition_type': 'manual_release',
                'status': 'pending',
                'released_at': datetime.now(pytz.UTC).isoformat()
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)
    
    def test_multiple_conditions_some_not_satisfied(self):
        """Test that access is denied when any condition is not satisfied"""
        past_date = (datetime.now(pytz.UTC) - timedelta(days=7)).isoformat()
        future_date = (datetime.now(pytz.UTC) + timedelta(days=7)).isoformat()
        
        conditions = [
            {
                'condition_type': 'time_delayed',
                'activation_date': past_date,
                'status': 'pending'
            },
            {
                'condition_type': 'time_delayed',
                'activation_date': future_date,
                'status': 'pending'
            }
        ]
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertFalse(all_satisfied)
        self.assertEqual(len(unmet), 1)
        self.assertEqual(unmet[0]['condition_type'], 'time_delayed')
    
    def test_no_conditions_grants_access(self):
        """Test that no conditions means access is granted (backward compatibility)"""
        conditions = []
        
        all_satisfied, unmet = evaluate_access_conditions(conditions)
        
        self.assertTrue(all_satisfied)
        self.assertEqual(len(unmet), 0)


if __name__ == '__main__':
    unittest.main()
