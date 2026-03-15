"""
Unit tests for InactivityProcessor Lambda function.

Tests verify that inactivity triggers are correctly activated when
Legacy Makers fail to respond to check-ins for the configured duration.

Requirements: 3.3, 3.6, 11.3, 11.4
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import importlib.util
import pytz
import sys
import os

# Load app.py under a unique module name to avoid sys.modules collision
# when pytest runs multiple Lambda test files in the same process
_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
_spec = importlib.util.spec_from_file_location('inactivity_processor_app', _app_path)
_app = importlib.util.module_from_spec(_spec)
sys.modules['inactivity_processor_app'] = _app
_shared = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../shared')
if _shared not in sys.path:
    sys.path.insert(0, os.path.abspath(_shared))
_spec.loader.exec_module(_app)

lambda_handler = _app.lambda_handler
get_benefactor_email = _app.get_benefactor_email

_MOD = 'inactivity_processor_app'


class TestInactivityProcessor(unittest.TestCase):
    """Test InactivityProcessor scheduled job"""

    @patch(f'{_MOD}.boto3')
    def test_no_inactivity_conditions(self, mock_boto3):
        """Test processor when no inactivity trigger conditions exist"""
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_processed'], 0)
        self.assertEqual(body['activations_successful'], 0)
        self.assertEqual(body['activations_failed'], 0)

    @patch(f'{_MOD}.send_access_granted_email')
    @patch(f'{_MOD}.get_benefactor_email')
    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_threshold_not_met_insufficient_months(self, mock_boto3, mock_update_rel, mock_get_email, mock_send_email):
        """Test that activation doesn't occur when months threshold not met"""
        last_check_in = (datetime.now(pytz.UTC) - relativedelta(months=3)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'check_in_interval_days': 30,
            'last_check_in': last_check_in,
            'consecutive_missed_check_ins': 3,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_processed'], 1)
        self.assertEqual(body['activations_successful'], 0)
        mock_update_rel.assert_not_called()

    @patch(f'{_MOD}.send_access_granted_email')
    @patch(f'{_MOD}.get_benefactor_email')
    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_threshold_not_met_insufficient_missed_checkins(self, mock_boto3, mock_update_rel, mock_get_email, mock_send_email):
        """Test that activation doesn't occur when missed check-ins threshold not met"""
        last_check_in = (datetime.now(pytz.UTC) - relativedelta(months=7)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'check_in_interval_days': 30,
            'last_check_in': last_check_in,
            'consecutive_missed_check_ins': 1,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_successful'], 0)
        mock_update_rel.assert_not_called()

    @patch(f'{_MOD}.send_access_granted_email')
    @patch(f'{_MOD}.get_benefactor_email')
    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_successful_activation(self, mock_boto3, mock_update_rel, mock_get_email, mock_send_email):
        """Test successful activation when both thresholds are met"""
        last_check_in = (datetime.now(pytz.UTC) - relativedelta(months=7)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'check_in_interval_days': 30,
            'last_check_in': last_check_in,
            'consecutive_missed_check_ins': 6,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        mock_update_rel.return_value = (True, {'message': 'Updated'})
        mock_get_email.return_value = 'benefactor@example.com'
        mock_send_email.return_value = True

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_processed'], 1)
        self.assertEqual(body['activations_successful'], 1)
        self.assertEqual(body['activations_failed'], 0)
        mock_update_rel.assert_called_once_with(
            initiator_id='maker123',
            related_user_id='benefactor456',
            new_status='active'
        )
        mock_table.update_item.assert_called_once()
        mock_send_email.assert_called_once()

    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_uses_created_at_when_no_last_check_in(self, mock_boto3, mock_update_rel):
        """Test that created_at is used when last_check_in is not set"""
        created_at = (datetime.now(pytz.UTC) - relativedelta(months=7)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'check_in_interval_days': 30,
            'created_at': created_at,
            'consecutive_missed_check_ins': 5,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        mock_update_rel.return_value = (True, {'message': 'Updated'})

        result = lambda_handler({}, {})

        body = eval(result['body'])
        self.assertGreater(body['activations_successful'], 0)

    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_invalid_relationship_key_format(self, mock_boto3, mock_update_rel):
        """Test handling of invalid relationship_key format"""
        last_check_in = (datetime.now(pytz.UTC) - relativedelta(months=7)).isoformat()
        mock_condition = {
            'relationship_key': 'invalid_key_format',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'last_check_in': last_check_in,
            'consecutive_missed_check_ins': 6,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_processed'], 1)
        self.assertEqual(body['activations_successful'], 0)
        self.assertEqual(body['activations_failed'], 1)
        self.assertGreater(len(body['errors']), 0)
        mock_update_rel.assert_not_called()

    @patch(f'{_MOD}.send_access_granted_email')
    @patch(f'{_MOD}.get_benefactor_email')
    @patch(f'{_MOD}.update_relationship_status')
    @patch(f'{_MOD}.boto3')
    def test_relationship_update_failure(self, mock_boto3, mock_update_rel, mock_get_email, mock_send_email):
        """Test handling when relationship status update fails"""
        last_check_in = (datetime.now(pytz.UTC) - relativedelta(months=7)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'inactivity_months': 6,
            'check_in_interval_days': 30,
            'last_check_in': last_check_in,
            'consecutive_missed_check_ins': 6,
            'status': 'pending'
        }
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        mock_update_rel.return_value = (False, {'error': 'Update failed'})

        result = lambda_handler({}, {})

        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['activations_processed'], 1)
        self.assertEqual(body['activations_successful'], 0)
        self.assertEqual(body['activations_failed'], 1)
        mock_table.update_item.assert_not_called()
        mock_send_email.assert_not_called()

    @patch(f'{_MOD}.boto3')
    def test_get_benefactor_email_from_pending_user(self, mock_boto3):
        """Test extracting email from pending user ID"""
        email = get_benefactor_email('pending#test@example.com')
        self.assertEqual(email, 'test@example.com')


if __name__ == '__main__':
    unittest.main()
