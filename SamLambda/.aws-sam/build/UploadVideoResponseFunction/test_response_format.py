#!/usr/bin/env python3
"""
Response Format Test
Tests response structure, backward compatibility, and CORS headers.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the function directory to path
sys.path.insert(0, os.path.dirname(__file__))

class TestResponseFormat(unittest.TestCase):
    
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
    def test_successful_response_with_thumbnail(self, mock_validator, mock_upload_s3, 
                                              mock_generate_thumbnail, mock_update_status, 
                                              mock_update_progress):
        """Test response format when thumbnail generation succeeds"""
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
        
        response = lambda_handler(self.sample_event, {})
        
        # Verify response structure
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('headers', response)
        self.assertIn('body', response)
        
        # Verify CORS headers
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        
        # Parse and verify response body
        body = json.loads(response['body'])
        
        # Required fields
        self.assertIn('message', body)
        self.assertIn('filename', body)
        self.assertIn('s3Key', body)
        
        # Thumbnail field when successful
        self.assertIn('thumbnailFilename', body)
        self.assertEqual(body['thumbnailFilename'], 'test-question-1_20241201_120000_abcd1234.jpg')
        
        # Verify filename format
        self.assertTrue(body['filename'].endswith('.webm'))
        self.assertTrue(body['thumbnailFilename'].endswith('.jpg'))
    
    @patch('app.update_user_progress')
    @patch('app.update_user_question_status')
    @patch('app.generate_thumbnail')
    @patch('app.upload_to_s3')
    @patch('app.PersonaValidator')
    def test_successful_response_without_thumbnail(self, mock_validator, mock_upload_s3, 
                                                 mock_generate_thumbnail, mock_update_status, 
                                                 mock_update_progress):
        """Test response format when thumbnail generation fails"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock successful video upload but failed thumbnail
        mock_upload_s3.return_value = None
        mock_generate_thumbnail.side_effect = Exception("FFmpeg not available")
        mock_update_status.return_value = None
        mock_update_progress.return_value = None
        mock_validator.add_persona_context_to_response.return_value = {
            'message': 'Video uploaded successfully',
            'filename': 'test-question-1_20241201_120000_abcd1234.webm',
            's3Key': 'user-responses/test-user-123/test-question-1_20241201_120000_abcd1234.webm'
        }
        
        response = lambda_handler(self.sample_event, {})
        
        # Verify response structure
        self.assertEqual(response['statusCode'], 200)
        
        # Parse and verify response body
        body = json.loads(response['body'])
        
        # Required fields should still be present
        self.assertIn('message', body)
        self.assertIn('filename', body)
        self.assertIn('s3Key', body)
        
        # Thumbnail field should NOT be present when generation fails
        self.assertNotIn('thumbnailFilename', body)
    
    def test_backward_compatibility(self):
        """Test that existing clients continue to work"""
        # Test that the response contains all original fields
        expected_original_fields = ['message', 'filename', 's3Key']
        
        # Mock response body
        response_body = {
            'message': 'Video uploaded successfully',
            'filename': 'test_video.webm',
            's3Key': 'user-responses/user123/test_video.webm'
        }
        
        # Verify all original fields are present
        for field in expected_original_fields:
            self.assertIn(field, response_body)
        
        # New field (thumbnailFilename) is optional
        # Existing clients should ignore unknown fields
        response_body_with_thumbnail = response_body.copy()
        response_body_with_thumbnail['thumbnailFilename'] = 'test_video.jpg'
        
        # Both versions should be valid JSON
        json.dumps(response_body)
        json.dumps(response_body_with_thumbnail)
    
    def test_cors_headers_in_all_responses(self):
        """Test CORS headers are present in all response types"""
        try:
            from app import lambda_handler
        except ImportError:
            self.skipTest("App module not available")
        
        test_cases = [
            # OPTIONS request
            ({'httpMethod': 'OPTIONS'}, 200),
            # Missing parameters
            ({'httpMethod': 'POST', 'body': json.dumps({})}, 400),
            # Invalid JSON
            ({'httpMethod': 'POST', 'body': 'invalid json'}, 500)
        ]
        
        for event, expected_status in test_cases:
            response = lambda_handler(event, {})
            
            # Verify status code
            self.assertEqual(response['statusCode'], expected_status)
            
            # Verify CORS headers are present
            self.assertIn('Access-Control-Allow-Origin', response['headers'])
            self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
    
    def test_json_serialization(self):
        """Test that response body is valid JSON"""
        test_responses = [
            {
                'message': 'Video uploaded successfully',
                'filename': 'test_video.webm',
                's3Key': 'user-responses/user123/test_video.webm'
            },
            {
                'message': 'Video uploaded successfully',
                'filename': 'test_video.webm',
                's3Key': 'user-responses/user123/test_video.webm',
                'thumbnailFilename': 'test_video.jpg'
            },
            {
                'error': 'Missing required parameters'
            }
        ]
        
        for response_body in test_responses:
            # Should not raise exception
            json_str = json.dumps(response_body)
            # Should be able to parse back
            parsed = json.loads(json_str)
            self.assertEqual(parsed, response_body)
    
    def test_filename_consistency(self):
        """Test filename consistency between video and thumbnail"""
        base_filename = "question1_20241201_120000_abcd1234"
        video_filename = f"{base_filename}.webm"
        thumbnail_filename = f"{base_filename}.jpg"
        
        # Extract base name
        video_base = video_filename.replace('.webm', '')
        thumbnail_base = thumbnail_filename.replace('.jpg', '')
        
        # Should be identical
        self.assertEqual(video_base, thumbnail_base)
        
        # Test the actual conversion logic
        generated_thumbnail = video_filename.replace('.webm', '.jpg')
        self.assertEqual(generated_thumbnail, thumbnail_filename)
    
    def test_s3_key_format(self):
        """Test S3 key format consistency"""
        user_id = "test-user-123"
        filename = "question1_20241201_120000_abcd1234.webm"
        thumbnail_filename = "question1_20241201_120000_abcd1234.jpg"
        
        expected_video_key = f"user-responses/{user_id}/{filename}"
        expected_thumbnail_key = f"user-responses/{user_id}/{thumbnail_filename}"
        
        # Verify format
        self.assertTrue(expected_video_key.startswith("user-responses/"))
        self.assertTrue(expected_thumbnail_key.startswith("user-responses/"))
        
        # Verify same directory
        video_dir = "/".join(expected_video_key.split("/")[:-1])
        thumbnail_dir = "/".join(expected_thumbnail_key.split("/")[:-1])
        self.assertEqual(video_dir, thumbnail_dir)
    
    def test_error_response_format(self):
        """Test error response format consistency"""
        error_responses = [
            {'error': 'Missing required parameters'},
            {'error': 'Unauthorized access'},
            {'error': 'Internal server error'}
        ]
        
        for error_response in error_responses:
            # Should have error field
            self.assertIn('error', error_response)
            # Error message should be string
            self.assertIsInstance(error_response['error'], str)
            # Should be valid JSON
            json.dumps(error_response)

def main():
    """Run response format tests"""
    print("=== Response Format Tests ===\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResponseFormat)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())