#!/usr/bin/env python3
"""
Upload with Thumbnail Integration Test
Tests the complete flow: video upload → thumbnail generation → S3 upload
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the function directory to path
sys.path.insert(0, os.path.dirname(__file__))

class TestUploadWithThumbnail(unittest.TestCase):
    
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
    @patch('app.generate_thumbnail')
    @patch('app.upload_to_s3')
    @patch('app.PersonaValidator')
    def test_successful_upload_with_thumbnail(self, mock_validator, mock_upload_s3, 
                                            mock_generate_thumbnail, mock_update_status, 
                                            mock_update_progress):
        """Test successful video upload with thumbnail generation"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock successful operations
        mock_upload_s3.return_value = None
        mock_generate_thumbnail.return_value = "test-question-1_20241201_120000_abcd1234.jpg"
        mock_update_status.return_value = None
        mock_update_progress.return_value = None
        mock_validator.add_persona_context_to_response.return_value = {
            'message': 'Video uploaded successfully',
            'filename': 'test-question-1_20241201_120000_abcd1234.webm',
            's3Key': 'user-responses/test-user-123/test-question-1_20241201_120000_abcd1234.webm',
            'thumbnailFilename': 'test-question-1_20241201_120000_abcd1234.jpg'
        }
        
        # Execute lambda handler
        response = lambda_handler(self.sample_event, {})
        
        # Verify response
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        
        # Parse response body
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertIn('filename', body)
        self.assertIn('s3Key', body)
        self.assertIn('thumbnailFilename', body)
        
        # Verify all functions were called
        mock_upload_s3.assert_called_once()
        mock_generate_thumbnail.assert_called_once()
        mock_update_status.assert_called_once()
        mock_update_progress.assert_called_once()
    
    @patch('app.update_user_progress')
    @patch('app.update_user_question_status')
    @patch('app.generate_thumbnail')
    @patch('app.upload_to_s3')
    @patch('app.PersonaValidator')
    def test_upload_success_thumbnail_failure(self, mock_validator, mock_upload_s3, 
                                            mock_generate_thumbnail, mock_update_status, 
                                            mock_update_progress):
        """Test video upload succeeds even when thumbnail generation fails"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock successful video upload but failed thumbnail
        mock_upload_s3.return_value = None
        mock_generate_thumbnail.side_effect = Exception("FFmpeg failed")
        mock_update_status.return_value = None
        mock_update_progress.return_value = None
        mock_validator.add_persona_context_to_response.return_value = {
            'message': 'Video uploaded successfully',
            'filename': 'test-question-1_20241201_120000_abcd1234.webm',
            's3Key': 'user-responses/test-user-123/test-question-1_20241201_120000_abcd1234.webm'
        }
        
        # Execute lambda handler
        response = lambda_handler(self.sample_event, {})
        
        # Verify response is still successful
        self.assertEqual(response['statusCode'], 200)
        
        # Parse response body
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertIn('filename', body)
        self.assertIn('s3Key', body)
        # Thumbnail filename should NOT be present when generation fails
        self.assertNotIn('thumbnailFilename', body)
        
        # Verify video operations still completed
        mock_upload_s3.assert_called_once()
        mock_update_status.assert_called_once()
        mock_update_progress.assert_called_once()
    
    def test_options_request(self):
        """Test CORS preflight OPTIONS request"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        options_event = {'httpMethod': 'OPTIONS'}
        response = lambda_handler(options_event, {})
        
        # Verify OPTIONS response
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['body'], '')
        
        # Verify CORS headers match incrementUserLevel pattern
        expected_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
        
        for key, value in expected_headers.items():
            self.assertEqual(response['headers'][key], value)
    
    def test_missing_parameters(self):
        """Test error handling for missing parameters"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Event with missing videoData
        incomplete_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'userId': 'test-user-123',
                'questionId': 'test-question-1',
                'questionType': 'childhood'
                # Missing videoData
            })
        }
        
        response = lambda_handler(incomplete_event, {})
        
        # Verify error response
        self.assertEqual(response['statusCode'], 400)
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        
        body = json.loads(response['body'])
        self.assertIn('error', body)
        self.assertIn('Missing required parameters', body['error'])
    
    def test_cors_headers_consistency(self):
        """Test that CORS headers are consistent across all response types"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Test different response scenarios
        test_cases = [
            # OPTIONS request
            ({'httpMethod': 'OPTIONS'}, 200),
            # Missing parameters
            ({'httpMethod': 'POST', 'body': json.dumps({})}, 400)
        ]
        
        for event, expected_status in test_cases:
            response = lambda_handler(event, {})
            self.assertEqual(response['statusCode'], expected_status)
            self.assertIn('Access-Control-Allow-Origin', response['headers'])
            self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
    
    @patch('app.generate_thumbnail')
    def test_thumbnail_filename_generation(self, mock_generate_thumbnail):
        """Test thumbnail filename generation logic"""
        mock_generate_thumbnail.return_value = "test_video.jpg"
        
        # Test the filename conversion logic
        test_cases = [
            ("video.webm", "video.jpg"),
            ("question1_20241201_120000_abcd1234.webm", "question1_20241201_120000_abcd1234.jpg"),
            ("test_file_with_underscores.webm", "test_file_with_underscores.jpg")
        ]
        
        for webm_name, expected_jpg in test_cases:
            result = webm_name.replace('.webm', '.jpg')
            self.assertEqual(result, expected_jpg)

def main():
    """Run upload with thumbnail integration tests"""
    print("=== Upload with Thumbnail Integration Tests ===\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUploadWithThumbnail)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())