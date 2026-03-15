"""
Email Utilities

Provides retry logic and error handling for SES email sending operations.
Implements exponential backoff with configurable retry attempts.

Requirements: 13.8
"""
import time
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional


def send_email_with_retry(
    destination: str,
    subject: str,
    html_body: str,
    text_body: str,
    sender_email: str,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> Dict[str, Any]:
    """
    Send email via SES with exponential backoff retry logic.
    
    This function implements a robust retry mechanism for SES email sending:
    - Retries up to max_retries times on failure
    - Uses exponential backoff: delay doubles after each retry
    - Logs all retry attempts for debugging
    - Returns detailed success/failure information
    
    Args:
        destination: Recipient email address
        subject: Email subject line
        html_body: HTML version of email body
        text_body: Plain text version of email body
        sender_email: Sender email address (must be verified in SES)
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        
    Returns:
        dict: Result of email sending operation
        {
            'success': bool,
            'message_id': str (if successful),
            'error': str (if failed),
            'attempts': int,
            'retry_count': int
        }
    """
    ses_client = boto3.client('ses', region_name='us-east-1')
    
    attempt = 0
    retry_count = 0
    delay = initial_delay
    last_error = None
    
    while attempt <= max_retries:
        attempt += 1
        
        try:
            print(f"Email send attempt {attempt}/{max_retries + 1} to {destination}")
            
            response = ses_client.send_email(
                Source=sender_email,
                Destination={'ToAddresses': [destination]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {
                        'Html': {'Data': html_body},
                        'Text': {'Data': text_body}
                    }
                }
            )
            
            message_id = response.get('MessageId')
            print(f"Email sent successfully to {destination}. MessageId: {message_id}")
            
            if retry_count > 0:
                print(f"Email succeeded after {retry_count} retries")
            
            return {
                'success': True,
                'message_id': message_id,
                'attempts': attempt,
                'retry_count': retry_count
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            last_error = f"{error_code}: {error_message}"
            
            print(f"SES ClientError on attempt {attempt}: {last_error}")
            
            # Check if error is retryable
            retryable_errors = [
                'Throttling',
                'ServiceUnavailable',
                'InternalFailure',
                'RequestTimeout'
            ]
            
            if error_code not in retryable_errors:
                print(f"Non-retryable error: {error_code}. Aborting retries.")
                return {
                    'success': False,
                    'error': last_error,
                    'attempts': attempt,
                    'retry_count': retry_count
                }
            
            # If we've exhausted retries, return failure
            if attempt > max_retries:
                print(f"Max retries ({max_retries}) exceeded. Email send failed.")
                return {
                    'success': False,
                    'error': last_error,
                    'attempts': attempt,
                    'retry_count': retry_count
                }
            
            # Wait before retrying (exponential backoff)
            print(f"Retrying in {delay} seconds... (retry {retry_count + 1}/{max_retries})")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
            retry_count += 1
            
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            print(f"Unexpected error on attempt {attempt}: {last_error}")
            
            # For unexpected errors, don't retry
            return {
                'success': False,
                'error': last_error,
                'attempts': attempt,
                'retry_count': retry_count
            }
    
    # Should not reach here, but just in case
    return {
        'success': False,
        'error': last_error or 'Unknown error',
        'attempts': attempt,
        'retry_count': retry_count
    }


def send_email_simple(
    destination: str,
    subject: str,
    html_body: str,
    text_body: str,
    sender_email: str
) -> bool:
    """
    Simplified email sending function that returns boolean success/failure.
    
    This is a convenience wrapper around send_email_with_retry for cases
    where detailed retry information is not needed.
    
    Args:
        destination: Recipient email address
        subject: Email subject line
        html_body: HTML version of email body
        text_body: Plain text version of email body
        sender_email: Sender email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    result = send_email_with_retry(
        destination=destination,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        sender_email=sender_email
    )
    
    return result['success']
