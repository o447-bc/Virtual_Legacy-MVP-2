"""
Unit tests for TimeDelayProcessor Lambda function.

Tests verify that time-delayed access conditions are correctly activated
when the activation date is reached.

Requirements: 11.1, 11.4
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import importlib.util
import pytz
import sys
import os

# Load app.py under a unique module name to avoid sys.modules collision
# when pytest runs multiple Lambda test files in the same process
_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
_spec = importlib.util.spec_from_file_location('time_delay_processor_app', _app_path)
_app = importlib.util.module_from_spec(_spec)
sys.modules['time_delay_processor_app'] = _app
# Also register shared deps path so app.py can import assignment_dal etc.
_shared = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../shared')
if _shared not in sys.path:
    sys.path.insert(0, os.path.abspath(_shared))
_spec.loader.exec_module(_app)

lambda_handler = _app.lambda_handler
get_benefactor_email = _app.get_benefactor_email

_MOD = 'time_delay_processor_app'


class TestTimeDelayProcessor(unittest.TestCase):
    """Test TimeDelayProcessor scheduled job"""

    @patch(f'{_MOD}.boto3')
    def test_no_conditions_ready_to_activate(self, mock_boto3):
        """Test processor when no conditions are ready to activate"""
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
    def test_successful_activation(self, mock_boto3, mock_update_rel, mock_get_email, mock_send_email):
        """Test successful activation of time-delayed condition"""
        past_date = (datetime.now(pytz.UTC) - timedelta(hours=1)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'time_delayed',
            'activation_date': past_date,
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
    def test_invalid_relationship_key_format(self, mock_boto3, mock_update_rel):
        """Test handling of invalid relationship_key format"""
        mock_condition = {
            'relationship_key': 'invalid_key_format',
            'condition_id': 'cond-001',
            'condition_type': 'time_delayed',
            'activation_date': datetime.now(pytz.UTC).isoformat(),
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
        past_date = (datetime.now(pytz.UTC) - timedelta(hours=1)).isoformat()
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'time_delayed',
            'activation_date': past_date,
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

    @patch(f'{_MOD}.boto3')
    def test_get_benefactor_email_from_cognito(self, mock_boto3):
        """Test retrieving email from Cognito"""
        mock_cognito = MagicMock()
        mock_cognito.admin_get_user.return_value = {
            'UserAttributes': [
                {'Name': 'email', 'Value': 'user@example.com'},
                {'Name': 'sub', 'Value': 'user-123'}
            ]
        }
        mock_boto3.client.return_value = mock_cognito
        with patch.dict(os.environ, {'USER_POOL_ID': 'us-east-1_test'}):
            email = get_benefactor_email('user-123')
        self.assertEqual(email, 'user@example.com')
        mock_cognito.admin_get_user.assert_called_once()


if __name__ == '__main__':
    unittest.main()
