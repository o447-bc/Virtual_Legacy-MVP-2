"""
Unit tests for email_utils module.

Tests retry logic, exponential backoff, and error handling for SES email sending.
"""
import unittest
from unittest.mock import Mock, patch, call
from botocore.exceptions import ClientError
import time

# Import the module to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))
from email_utils import send_email_with_retry, send_email_simple


class TestEmailRetryLogic(unittest.TestCase):
    """Test email retry logic with exponential backoff."""
    
    @patch('email_utils.boto3.client')
    def test_successful_send_first_attempt(self, mock_boto_client):
        """Test successful email send on first attempt."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id-123'}
        
        result = send_email_with_retry(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id-123')
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['retry_count'], 0)
        mock_ses.send_email.assert_called_once()
    
    @patch('email_utils.boto3.client')
    @patch('email_utils.time.sleep')
    def test_retry_on_throttling_error(self, mock_sleep, mock_boto_client):
        """Test retry logic when SES returns throttling error."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        
        # First call fails with throttling, second succeeds
        mock_ses.send_email.side_effect = [
            ClientError(
                {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
                'SendEmail'
            ),
            {'MessageId': 'test-message-id-456'}
        ]
        
        result = send_email_with_retry(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message_id'], 'test-message-id-456')
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(mock_ses.send_email.call_count, 2)
        mock_sleep.assert_called_once_with(1.0)  # Initial delay
    
    @patch('email_utils.boto3.client')
    @patch('email_utils.time.sleep')
    def test_exponential_backoff(self, mock_sleep, mock_boto_client):
        """Test exponential backoff delays between retries."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        
        # Fail twice, then succeed
        mock_ses.send_email.side_effect = [
            ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
                'SendEmail'
            ),
            ClientError(
                {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
                'SendEmail'
            ),
            {'MessageId': 'test-message-id-789'}
        ]
        
        result = send_email_with_retry(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com',
            initial_delay=0.5
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['attempts'], 3)
        self.assertEqual(result['retry_count'], 2)
        
        # Verify exponential backoff: 0.5s, then 1.0s
        expected_calls = [call(0.5), call(1.0)]
        mock_sleep.assert_has_calls(expected_calls)
    
    @patch('email_utils.boto3.client')
    @patch('email_utils.time.sleep')
    def test_max_retries_exceeded(self, mock_sleep, mock_boto_client):
        """Test failure when max retries are exceeded."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        
        # Always fail with throttling
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'SendEmail'
        )
        
        result = send_email_with_retry(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com',
            max_retries=2
        )
        
        self.assertFalse(result['success'])
        self.assertIn('Throttling', result['error'])
        self.assertEqual(result['attempts'], 3)  # Initial + 2 retries
        self.assertEqual(result['retry_count'], 2)
        self.assertEqual(mock_ses.send_email.call_count, 3)
    
    @patch('email_utils.boto3.client')
    def test_non_retryable_error(self, mock_boto_client):
        """Test that non-retryable errors don't trigger retries."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        
        # Fail with non-retryable error (invalid email)
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email address is not verified'}},
            'SendEmail'
        )
        
        result = send_email_with_retry(
            destination='invalid@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('MessageRejected', result['error'])
        self.assertEqual(result['attempts'], 1)  # No retries
        self.assertEqual(result['retry_count'], 0)
        mock_ses.send_email.assert_called_once()
    
    @patch('email_utils.boto3.client')
    def test_unexpected_error(self, mock_boto_client):
        """Test handling of unexpected errors."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        
        # Raise unexpected exception
        mock_ses.send_email.side_effect = ValueError("Unexpected error")
        
        result = send_email_with_retry(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('Unexpected error', result['error'])
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['retry_count'], 0)
    
    @patch('email_utils.boto3.client')
    def test_send_email_simple_success(self, mock_boto_client):
        """Test simplified email sending function returns True on success."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
        
        result = send_email_simple(
            destination='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertTrue(result)
    
    @patch('email_utils.boto3.client')
    def test_send_email_simple_failure(self, mock_boto_client):
        """Test simplified email sending function returns False on failure."""
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Invalid email'}},
            'SendEmail'
        )
        
        result = send_email_simple(
            destination='invalid@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text',
            sender_email='sender@example.com'
        )
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
