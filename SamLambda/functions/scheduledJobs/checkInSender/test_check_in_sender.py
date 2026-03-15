"""
Unit tests for CheckInSender Lambda function.

Tests verify that check-in emails are sent at correct intervals and
consecutive missed check-in counters are incremented.

Requirements: 3.1, 3.4, 3.5, 13.6
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import lambda_handler, get_user_email


class TestCheckInSender(unittest.TestCase):
    """Test CheckInSender scheduled job"""
    
    @patch('app.boto3')
    def test_no_inactivity_conditions(self, mock_boto3):
        """Test processor when no inactivity trigger conditions exist"""
        # Mock DynamoDB response with no items
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['emails_processed'], 0)
        self.assertEqual(body['emails_sent'], 0)
        self.assertEqual(body['emails_failed'], 0)
    
    @patch('app.send_check_in_email')
    @patch('app.get_user_email')
    @patch('app.boto3')
    def test_check_in_not_yet_due(self, mock_boto3, mock_get_email, mock_send_email):
        """Test that check-in is not sent when interval hasn't elapsed"""
        # Setup - last check-in sent 10 days ago, interval is 30 days
        last_sent = (datetime.now(pytz.UTC) - timedelta(days=10)).isoformat()
        
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'check_in_interval_days': 30,
            'last_check_in_sent': last_sent,
            'consecutive_missed_check_ins': 0,
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_conditions_table = MagicMock()
        mock_conditions_table.query.return_value = {'Items': [mock_condition]}
        
        mock_temp_table = MagicMock()
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_conditions_table if name == 'AccessConditionsDB' else mock_temp_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['emails_processed'], 1)
        self.assertEqual(body['emails_sent'], 0)  # Not sent because interval not reached
        
        # Verify email was NOT sent
        mock_send_email.assert_not_called()
    
    @patch('app.send_check_in_email')
    @patch('app.get_user_email')
    @patch('app.boto3')
    def test_successful_check_in_send(self, mock_boto3, mock_get_email, mock_send_email):
        """Test successful check-in email send"""
        # Setup - last check-in sent 31 days ago, interval is 30 days
        last_sent = (datetime.now(pytz.UTC) - timedelta(days=31)).isoformat()
        
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'check_in_interval_days': 30,
            'last_check_in_sent': last_sent,
            'consecutive_missed_check_ins': 2,
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_conditions_table = MagicMock()
        mock_conditions_table.query.return_value = {'Items': [mock_condition]}
        
        mock_temp_table = MagicMock()
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_conditions_table if name == 'AccessConditionsDB' else mock_temp_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock email functions
        mock_get_email.return_value = 'maker@example.com'
        mock_send_email.return_value = True
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['emails_processed'], 1)
        self.assertEqual(body['emails_sent'], 1)
        self.assertEqual(body['emails_failed'], 0)
        
        # Verify token was stored in temp table
        mock_temp_table.put_item.assert_called_once()
        stored_item = mock_temp_table.put_item.call_args[1]['Item']
        self.assertTrue(stored_item['userName'].startswith('checkin#'))
        self.assertEqual(stored_item['user_id'], 'maker123')
        self.assertEqual(stored_item['condition_id'], 'cond-001')
        
        # Verify email was sent
        mock_send_email.assert_called_once()
        
        # Verify condition was updated with incremented counter
        mock_conditions_table.update_item.assert_called_once()
        update_call = mock_conditions_table.update_item.call_args
        self.assertEqual(update_call[1]['ExpressionAttributeValues'][':missed_count'], 3)  # 2 + 1
    
    @patch('app.send_check_in_email')
    @patch('app.get_user_email')
    @patch('app.boto3')
    def test_first_check_in_uses_created_at(self, mock_boto3, mock_get_email, mock_send_email):
        """Test that first check-in uses created_at when last_check_in_sent is not set"""
        # Setup - no last_check_in_sent, created 31 days ago
        created_at = (datetime.now(pytz.UTC) - timedelta(days=31)).isoformat()
        
        mock_condition = {
            'relationship_key': 'maker123#benefactor456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'check_in_interval_days': 30,
            'created_at': created_at,
            'consecutive_missed_check_ins': 0,
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_conditions_table = MagicMock()
        mock_conditions_table.query.return_value = {'Items': [mock_condition]}
        
        mock_temp_table = MagicMock()
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_conditions_table if name == 'AccessConditionsDB' else mock_temp_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Mock email functions
        mock_get_email.return_value = 'maker@example.com'
        mock_send_email.return_value = True
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['emails_sent'], 1)
        
        # Verify consecutive_missed_check_ins was incremented from 0 to 1
        update_call = mock_conditions_table.update_item.call_args
        self.assertEqual(update_call[1]['ExpressionAttributeValues'][':missed_count'], 1)
    
    @patch('app.get_user_email')
    @patch('app.boto3')
    def test_invalid_relationship_key_format(self, mock_boto3, mock_get_email):
        """Test handling of invalid relationship_key format"""
        # Setup - missing # separator
        mock_condition = {
            'relationship_key': 'invalid_key',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'check_in_interval_days': 30,
            'created_at': (datetime.now(pytz.UTC) - timedelta(days=31)).isoformat(),
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': [mock_condition]}
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler({}, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        body = eval(result['body'])
        self.assertEqual(body['emails_processed'], 1)
        self.assertEqual(body['emails_sent'], 0)
        self.assertEqual(body['emails_failed'], 1)
        self.assertGreater(len(body['errors']), 0)
    
    @patch('app.boto3')
    def test_get_user_email_from_cognito(self, mock_boto3):
        """Test retrieving user email from Cognito"""
        # Mock Cognito response
        mock_cognito = MagicMock()
        mock_cognito.admin_get_user.return_value = {
            'UserAttributes': [
                {'Name': 'email', 'Value': 'user@example.com'},
                {'Name': 'sub', 'Value': 'user-123'}
            ]
        }
        mock_boto3.client.return_value = mock_cognito
        
        # Mock environment variable
        with patch.dict(os.environ, {'USER_POOL_ID': 'us-east-1_test'}):
            email = get_user_email('user-123')
        
        self.assertEqual(email, 'user@example.com')
        mock_cognito.admin_get_user.assert_called_once()


if __name__ == '__main__':
    unittest.main()
