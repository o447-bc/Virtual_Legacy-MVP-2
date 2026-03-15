#!/usr/bin/env python3
"""
Test for Short Video Thumbnail Generation Fix
Tests the fallback mechanism for videos shorter than 5 seconds.
"""

import os
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call

# Add the function directory to path
sys.path.insert(0, os.path.dirname(__file__))

class TestShortVideoThumbnailFix(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.sample_video = os.path.join(self.test_dir, "short_video.webm")
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('boto3.client')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_short_video_fallback_to_1_second(self, mock_remove, mock_getsize, mock_exists, mock_subprocess, mock_boto3):
        """Test fallback from 5s to 1s for short videos"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock file operations
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # 1KB thumbnail
        
        # First call (5s) fails with seek error, second call (1s) succeeds
        seek_error = subprocess.CalledProcessError(1, 'ffmpeg')
        seek_error.stderr = "Invalid seek position: duration is 3.2 seconds"
        seek_error.stdout = ""
        
        success_result = MagicMock()
        success_result.returncode = 0
        success_result.stdout = "frame=    1 fps=0.0 q=-0.0 Lsize=N/A time=00:00:00.04 bitrate=N/A speed=   0x"
        success_result.stderr = ""
        
        mock_subprocess.side_effect = [seek_error, success_result]
        
        # Test parameters
        s3_key = "user-responses/test-user/short_video_3sec.webm"
        user_id = "test-user"
        
        # Execute thumbnail generation
        result = generate_thumbnail(s3_key, user_id)
        
        # Verify result
        self.assertEqual(result, "short_video_3sec.jpg")
        
        # Verify FFmpeg was called twice (5s failed, 1s succeeded)
        self.assertEqual(mock_subprocess.call_count, 2)
        
        # Verify first call used 5 seconds
        first_call_args = mock_subprocess.call_args_list[0][0][0]
        ss_index_1 = first_call_args.index('-ss')
        self.assertEqual(first_call_args[ss_index_1 + 1], '5')
        
        # Verify second call used 1 second
        second_call_args = mock_subprocess.call_args_list[1][0][0]
        ss_index_2 = second_call_args.index('-ss')
        self.assertEqual(second_call_args[ss_index_2 + 1], '1')
        
        # Verify S3 operations
        mock_s3.download_file.assert_called_once()
        mock_s3.upload_file.assert_called_once()
    
    @patch('boto3.client')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_very_short_video_fallback_to_half_second(self, mock_remove, mock_getsize, mock_exists, mock_subprocess, mock_boto3):
        """Test fallback to 0.5s for very short videos"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock file operations
        mock_exists.return_value = True
        mock_getsize.return_value = 512  # 512B thumbnail
        
        # First two calls fail (5s, 1s), third call (0.5s) succeeds
        seek_error_5s = subprocess.CalledProcessError(1, 'ffmpeg')
        seek_error_5s.stderr = "seek to 5.000000 failed"
        seek_error_5s.stdout = ""
        
        seek_error_1s = subprocess.CalledProcessError(1, 'ffmpeg')
        seek_error_1s.stderr = "seek to 1.000000 failed"
        seek_error_1s.stdout = ""
        
        success_result = MagicMock()
        success_result.returncode = 0
        success_result.stdout = "frame=    1 fps=0.0 q=-0.0 Lsize=N/A time=00:00:00.04 bitrate=N/A speed=   0x"
        success_result.stderr = ""
        
        mock_subprocess.side_effect = [seek_error_5s, seek_error_1s, success_result]
        
        # Test parameters
        s3_key = "user-responses/test-user/very_short_video_0.8sec.webm"
        user_id = "test-user"
        
        # Execute thumbnail generation
        result = generate_thumbnail(s3_key, user_id)
        
        # Verify result
        self.assertEqual(result, "very_short_video_0.8sec.jpg")
        
        # Verify FFmpeg was called three times
        self.assertEqual(mock_subprocess.call_count, 3)
        
        # Verify seek times: 5s -> 1s -> 0.5s
        call_args_list = mock_subprocess.call_args_list
        
        # First call: 5 seconds
        first_call_args = call_args_list[0][0][0]
        ss_index_1 = first_call_args.index('-ss')
        self.assertEqual(first_call_args[ss_index_1 + 1], '5')
        
        # Second call: 1 second
        second_call_args = call_args_list[1][0][0]
        ss_index_2 = second_call_args.index('-ss')
        self.assertEqual(second_call_args[ss_index_2 + 1], '1')
        
        # Third call: 0.5 seconds
        third_call_args = call_args_list[2][0][0]
        ss_index_3 = third_call_args.index('-ss')
        self.assertEqual(third_call_args[ss_index_3 + 1], '0.5')
    
    @patch('boto3.client')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_all_seek_times_fail(self, mock_remove, mock_exists, mock_subprocess, mock_boto3):
        """Test behavior when all seek times fail"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock file operations - file doesn't exist after all attempts
        mock_exists.return_value = False
        
        # All calls fail with different errors
        error_5s = subprocess.CalledProcessError(1, 'ffmpeg')
        error_5s.stderr = "seek failed"
        error_5s.stdout = ""
        
        error_1s = subprocess.CalledProcessError(1, 'ffmpeg')
        error_1s.stderr = "seek failed"
        error_1s.stdout = ""
        
        error_05s = subprocess.CalledProcessError(1, 'ffmpeg')
        error_05s.stderr = "invalid data found when processing input"
        error_05s.stdout = ""
        
        mock_subprocess.side_effect = [error_5s, error_1s, error_05s]
        
        # Test parameters
        s3_key = "user-responses/test-user/corrupted_video.webm"
        user_id = "test-user"
        
        # Should raise exception after all attempts fail
        with self.assertRaises(Exception) as context:
            generate_thumbnail(s3_key, user_id)
        
        # Verify all three seek times were attempted
        self.assertEqual(mock_subprocess.call_count, 3)
        
        # Verify error message indicates the issue
        error_message = str(context.exception)
        self.assertIn("FFmpeg processing failed", error_message)
    
    @patch('boto3.client')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_normal_video_succeeds_on_first_try(self, mock_remove, mock_getsize, mock_exists, mock_subprocess, mock_boto3):
        """Test that normal videos (>5s) still work on first try"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock file operations
        mock_exists.return_value = True
        mock_getsize.return_value = 2048  # 2KB thumbnail
        
        # First call (5s) succeeds immediately
        success_result = MagicMock()
        success_result.returncode = 0
        success_result.stdout = "frame=    1 fps=0.0 q=-0.0 Lsize=N/A time=00:00:05.04 bitrate=N/A speed=   0x"
        success_result.stderr = ""
        
        mock_subprocess.return_value = success_result
        
        # Test parameters
        s3_key = "user-responses/test-user/normal_video_10sec.webm"
        user_id = "test-user"
        
        # Execute thumbnail generation
        result = generate_thumbnail(s3_key, user_id)
        
        # Verify result
        self.assertEqual(result, "normal_video_10sec.jpg")
        
        # Verify FFmpeg was called only once (succeeded on first try)
        self.assertEqual(mock_subprocess.call_count, 1)
        
        # Verify it used 5 seconds (the preferred seek time)
        call_args = mock_subprocess.call_args[0][0]
        ss_index = call_args.index('-ss')
        self.assertEqual(call_args[ss_index + 1], '5')

def main():
    """Run short video thumbnail fix tests"""
    print("=== Short Video Thumbnail Generation Fix Tests ===\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShortVideoThumbnailFix)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())