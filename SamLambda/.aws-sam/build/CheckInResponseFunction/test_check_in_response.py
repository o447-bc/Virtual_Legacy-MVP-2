"""
Unit tests for CheckInResponse Lambda function.

Tests verify that check-in responses correctly reset inactivity counters
and update last check-in timestamps.

Requirements: 3.2, 3.5
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytz
import importlib.util
import sys
import os

# Load app.py under a unique module name to avoid sys.modules collision
# when pytest runs multiple Lambda test files in the same process
_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
_spec = importlib.util.spec_from_file_location('check_in_response_app', _app_path)
_app = importlib.util.module_from_spec(_spec)
sys.modules['check_in_response_app'] = _app
_spec.loader.exec_module(_app)

lambda_handler = _app.lambda_handler

_MOD = 'check_in_response_app'


class TestCheckInResponse(unittest.TestCase):
    """Test CheckInResponse Lambda function"""

    @patch(f'{_MOD}.boto3')
    def test_missing_token_parameter(self, mock_boto3):
        """Test error handling when token parameter is missing"""
        # Setup event with no query parameters
        event = {}
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 400)
        self.assertIn('Missing token parameter', result['body'])
    
    @patch(f'{_MOD}.boto3')
    def test_invalid_token(self, mock_boto3):
        """Test error handling when token is not found or expired"""
        # Setup
        event = {
            'queryStringParameters': {
                'token': 'invalid-token-123'
            }
        }
        
        # Mock DynamoDB - token not found
        mock_temp_table = MagicMock()
        mock_temp_table.get_item.return_value = {}  # No Item
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_temp_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 404)
        self.assertIn('Invalid or expired', result['body'])
    
    @patch(f'{_MOD}.boto3')
    def test_successful_check_in_response(self, mock_boto3):
        """Test successful check-in response processing"""
        # Setup
        event = {
            'queryStringParameters': {
                'token': 'valid-token-123'
            }
        }
        
        # Mock token data
        token_data = {
            'userName': 'checkin#valid-token-123',
            'user_id': 'maker-123',
            'condition_id': 'cond-001',
            'relationship_key': 'maker-123#benefactor-456',
            'token_type': 'check_in'
        }
        
        # Mock condition data
        condition_data = {
            'relationship_key': 'maker-123#benefactor-456',
            'condition_id': 'cond-001',
            'condition_type': 'inactivity_trigger',
            'consecutive_missed_check_ins': 3,
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_temp_table = MagicMock()
        mock_temp_table.get_item.return_value = {'Item': token_data}
        
        mock_conditions_table = MagicMock()
        mock_conditions_table.get_item.return_value = {'Item': condition_data}
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_temp_table if name == 'PersonaSignupTempDB' else mock_conditions_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('Check-In Confirmed', result['body'])
        
        # Verify condition was updated
        mock_conditions_table.update_item.assert_called_once()
        update_call = mock_conditions_table.update_item.call_args
        
        # Verify consecutive_missed_check_ins was reset to 0
        self.assertEqual(
            update_call[1]['ExpressionAttributeValues'][':zero'],
            0
        )
        
        # Verify last_check_in was updated
        self.assertIn(':check_in_time', update_call[1]['ExpressionAttributeValues'])
        
        # Verify token was deleted (one-time use)
        mock_temp_table.delete_item.assert_called_once()
    
    @patch(f'{_MOD}.boto3')
    def test_condition_not_found(self, mock_boto3):
        """Test error handling when condition is not found"""
        # Setup
        event = {
            'queryStringParameters': {
                'token': 'valid-token-123'
            }
        }
        
        # Mock token data
        token_data = {
            'userName': 'checkin#valid-token-123',
            'user_id': 'maker-123',
            'condition_id': 'cond-001',
            'relationship_key': 'maker-123#benefactor-456'
        }
        
        # Mock DynamoDB
        mock_temp_table = MagicMock()
        mock_temp_table.get_item.return_value = {'Item': token_data}
        
        mock_conditions_table = MagicMock()
        mock_conditions_table.get_item.return_value = {}  # No Item
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_temp_table if name == 'PersonaSignupTempDB' else mock_conditions_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 404)
        self.assertIn('condition not found', result['body'])
    
    @patch(f'{_MOD}.boto3')
    def test_invalid_condition_type(self, mock_boto3):
        """Test error handling when condition is not inactivity_trigger type"""
        # Setup
        event = {
            'queryStringParameters': {
                'token': 'valid-token-123'
            }
        }
        
        # Mock token data
        token_data = {
            'userName': 'checkin#valid-token-123',
            'user_id': 'maker-123',
            'condition_id': 'cond-001',
            'relationship_key': 'maker-123#benefactor-456'
        }
        
        # Mock condition data with wrong type
        condition_data = {
            'relationship_key': 'maker-123#benefactor-456',
            'condition_id': 'cond-001',
            'condition_type': 'time_delayed',  # Wrong type
            'status': 'pending'
        }
        
        # Mock DynamoDB
        mock_temp_table = MagicMock()
        mock_temp_table.get_item.return_value = {'Item': token_data}
        
        mock_conditions_table = MagicMock()
        mock_conditions_table.get_item.return_value = {'Item': condition_data}
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.side_effect = lambda name: (
            mock_temp_table if name == 'PersonaSignupTempDB' else mock_conditions_table
        )
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 400)
        self.assertIn('Invalid condition type', result['body'])
    
    @patch(f'{_MOD}.boto3')
    def test_incomplete_token_data(self, mock_boto3):
        """Test error handling when token data is incomplete"""
        # Setup
        event = {
            'queryStringParameters': {
                'token': 'valid-token-123'
            }
        }
        
        # Mock incomplete token data (missing condition_id)
        token_data = {
            'userName': 'checkin#valid-token-123',
            'user_id': 'maker-123',
            'relationship_key': 'maker-123#benefactor-456'
            # Missing condition_id
        }
        
        # Mock DynamoDB
        mock_temp_table = MagicMock()
        mock_temp_table.get_item.return_value = {'Item': token_data}
        
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_temp_table
        mock_boto3.resource.return_value = mock_dynamodb
        
        # Execute
        result = lambda_handler(event, {})
        
        # Verify
        self.assertEqual(result['statusCode'], 500)
        self.assertIn('Invalid token data', result['body'])


if __name__ == '__main__':
    unittest.main()
