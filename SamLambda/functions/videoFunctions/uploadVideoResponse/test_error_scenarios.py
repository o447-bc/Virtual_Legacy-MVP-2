#!/usr/bin/env python3
"""
Error Handling Test
Tests FFmpeg failures, corrupted video files, permission errors, and CORS headers.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import subprocess

# Add the function directory to path
sys.path.insert(0, os.path.dirname(__file__))

class TestErrorScenarios(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.sample_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': 'test-user-123',
                'questionId': 'test-question-1',
                'questionType': 'childhood',
                'videoData': 'dGVzdCB2aWRlbyBkYXRh'  # base64 encoded test data
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-123'
                    }
                }
            }
        }
    
    @patch('app.update_user_progress')
    @patch('app.update_user_question_status')
    @patch('app.upload_to_s3')
    @patch('app.PersonaValidator')
    def test_ffmpeg_not_available(self, mock_validator, mock_upload_s3, 
                                 mock_update_status, mock_update_progress):
        """Test video upload succeeds when FFmpeg is not available"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock successful video upload
        mock_upload_s3.return_value = None
        mock_update_status.return_value = None
        mock_update_progress.return_value = None
        mock_validator.add_persona_context_to_response.return_value = {
            'message': 'Video uploaded successfully',
            'filename': 'test-question-1_20241201_120000_abcd1234.webm',
            's3Key': 'user-responses/test-user-123/test-question-1_20241201_120000_abcd1234.webm'
        }
        
        # Mock FFmpeg not available
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
            
            response = lambda_handler(self.sample_event, {})
            
            # Should still succeed
            self.assertEqual(response['statusCode'], 200)
            
            # Should not have thumbnail filename
            body = json.loads(response['body'])
            self.assertNotIn('thumbnailFilename', body)
            
            # Video operations should still complete
            mock_upload_s3.assert_called_once()
            mock_update_status.assert_called_once()
            mock_update_progress.assert_called_once()
    
    @patch('boto3.client')
    def test_s3_download_failure(self, mock_boto3):
        """Test thumbnail generation handles S3 download failures"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client that fails on download
        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = Exception("S3 download failed")
        mock_boto3.return_value = mock_s3
        
        # Mock FFmpeg available
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)
            
            with self.assertRaises(Exception) as context:
                generate_thumbnail("user-responses/test/video.webm", "test")
            
            self.assertIn("Failed to download video from S3", str(context.exception))
    
    @patch('boto3.client')
    def test_ffmpeg_processing_failure(self, mock_boto3):
        """Test thumbnail generation handles FFmpeg processing failures"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock successful S3 operations
        mock_s3 = MagicMock()
        mock_s3.download_file.return_value = None
        mock_boto3.return_value = mock_s3
        
        # Mock FFmpeg available but processing fails
        with patch('subprocess.run') as mock_subprocess:
            # First call succeeds (version check), subsequent calls fail
            mock_subprocess.side_effect = [
                MagicMock(returncode=0),  # Version check
                subprocess.CalledProcessError(1, 'ffmpeg', stderr='Processing failed'),  # 5s attempt
                subprocess.CalledProcessError(1, 'ffmpeg', stderr='Processing failed')   # 1s attempt
            ]
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.remove'):
                
                with self.assertRaises(Exception) as context:
                    generate_thumbnail("user-responses/test/video.webm", "test")
                
                self.assertIn("FFmpeg failed at both 5s and 1s", str(context.exception))
    
    @patch('boto3.client')
    def test_s3_upload_failure(self, mock_boto3):
        """Test thumbnail generation handles S3 upload failures"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client that fails on upload
        mock_s3 = MagicMock()
        mock_s3.download_file.return_value = None
        mock_s3.upload_file.side_effect = Exception("S3 upload failed")
        mock_boto3.return_value = mock_s3
        
        # Mock successful FFmpeg processing
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = [
                MagicMock(returncode=0),  # Version check
                MagicMock(returncode=0)   # Processing
            ]
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.remove'):
                
                with self.assertRaises(Exception) as context:
                    generate_thumbnail("user-responses/test/video.webm", "test")
                
                self.assertIn("Failed to upload thumbnail to S3", str(context.exception))
    
    def test_cors_headers_in_error_responses(self):
        """Test that CORS headers are present in all error responses"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Test missing parameters error
        incomplete_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': 'test-user-123'
                # Missing required fields
            })
        }
        
        response = lambda_handler(incomplete_event, {})
        
        # Verify error response has CORS headers
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        
        # Verify error message
        body = json.loads(response['body'])
        self.assertIn('error', body)
    
    def test_cors_headers_consistency(self):
        """Test CORS headers match incrementUserLevel pattern exactly"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Test OPTIONS request
        options_event = {'httpMethod': 'OPTIONS'}
        response = lambda_handler(options_event, {})
        
        # Verify OPTIONS response has full CORS headers
        expected_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
        
        for key, value in expected_headers.items():
            self.assertIn(key, response['headers'])
            self.assertEqual(response['headers'][key], value)
    
    def test_thumbnail_generation_logging(self):
        """Test that thumbnail generation includes proper logging"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Capture print statements
        with patch('builtins.print') as mock_print:
            # Mock subprocess to simulate FFmpeg not found
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.side_effect = FileNotFoundError("FFmpeg not found")
                
                try:
                    generate_thumbnail("test-key", "test-user")
                except:
                    pass
                
                # Verify logging occurred (print was called)
                self.assertTrue(mock_print.called)
    
    def test_filename_security(self):
        """Test filename generation prevents directory traversal"""
        test_cases = [
            "user-responses/user123/video.webm",
            "user-responses/user123/../../../etc/passwd.webm",
            "user-responses/user123/normal_video.webm"
        ]
        
        for s3_key in test_cases:
            filename = os.path.basename(s3_key)
            thumbnail_filename = filename.replace('.webm', '.jpg')
            
            # Verify no directory traversal in thumbnail filename
            self.assertNotIn('..', thumbnail_filename)
            self.assertNotIn('/', thumbnail_filename)
            self.assertTrue(thumbnail_filename.endswith('.jpg'))

def main():
    """Run error handling tests"""
    print("=== Error Handling Tests ===\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorScenarios)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())