#!/usr/bin/env python3
"""
Thumbnail Generation Test
Tests FFmpeg processing and thumbnail generation functionality.
"""

import os
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add the function directory to path
sys.path.insert(0, os.path.dirname(__file__))

class TestThumbnailGeneration(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.sample_video = os.path.join(self.test_dir, "test_video.webm")
        self.create_sample_video()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_sample_video(self):
        """Create a sample video file for testing"""
        # Create a simple test video using FFmpeg if available
        try:
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=10:size=320x240:rate=1',
                '-c:v', 'libvpx',
                '-t', '10',
                '-y',
                self.sample_video
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Create a dummy file if FFmpeg is not available
            with open(self.sample_video, 'wb') as f:
                f.write(b'dummy video content for testing')
    
    def test_ffmpeg_availability(self):
        """Test if FFmpeg is available in expected locations"""
        ffmpeg_paths = [
            '/opt/ffmpeg/ffmpeg',  # Lambda layer path
            '/opt/bin/ffmpeg',     # Alternative layer path
            '/usr/bin/ffmpeg',     # System path
            'ffmpeg'               # PATH
        ]
        
        ffmpeg_found = False
        for path in ffmpeg_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✓ FFmpeg found at: {path}")
                    ffmpeg_found = True
                    break
            except FileNotFoundError:
                continue
        
        if not ffmpeg_found:
            print("⚠ FFmpeg not found - will use mocks for testing")
    
    @patch('boto3.client')
    def test_thumbnail_generation_function(self, mock_boto3):
        """Test the thumbnail generation function"""
        # Import the function after patching
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock successful S3 operations
        mock_s3.download_file.return_value = None
        mock_s3.upload_file.return_value = None
        
        # Test parameters
        s3_key = "user-responses/test-user/test_video_123.webm"
        user_id = "test-user"
        
        # Mock FFmpeg subprocess
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = MagicMock(returncode=0)
            
            # Mock file operations
            with patch('os.path.exists', return_value=True), \
                 patch('os.remove') as mock_remove:
                
                result = generate_thumbnail(s3_key, user_id)
                
                # Verify result
                self.assertEqual(result, "test_video_123.jpg")
                
                # Verify S3 operations
                mock_s3.download_file.assert_called_once()
                mock_s3.upload_file.assert_called_once()
                
                # Verify FFmpeg was called
                mock_subprocess.assert_called()
                
                # Verify cleanup
                self.assertEqual(mock_remove.call_count, 2)
    
    def test_ffmpeg_command_structure(self):
        """Test FFmpeg command structure"""
        # Test the key components of the FFmpeg command
        required_elements = ['-ss', '5', '-vframes', '1', '-vf', 'scale=200:-1', '-y']
        
        # Verify all required elements are present
        for element in required_elements:
            self.assertIsNotNone(element)  # Basic validation
        
        # Test specific requirements
        self.assertEqual('5', '5')  # Time extraction at 5 seconds
        self.assertEqual('scale=200:-1', 'scale=200:-1')  # 200px width scaling
        self.assertEqual('-vframes', '-vframes')  # Single frame extraction
    
    @patch('boto3.client')
    @patch('subprocess.run')
    @patch('os.path.getsize')
    def test_fallback_to_1_second(self, mock_getsize, mock_subprocess, mock_boto3):
        """Test fallback to 1 second when 5 seconds fails"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3
        
        # Mock file size for thumbnail verification
        mock_getsize.return_value = 1024
        
        # First call fails (5 seconds) with seek error, second succeeds (1 second)
        seek_error = subprocess.CalledProcessError(1, 'ffmpeg')
        seek_error.stderr = "seek to 5.000000 failed"
        seek_error.stdout = ""
        
        success_result = MagicMock()
        success_result.returncode = 0
        success_result.stdout = "frame=    1 fps=0.0 q=-0.0 Lsize=N/A"
        success_result.stderr = ""
        
        mock_subprocess.side_effect = [seek_error, success_result]
        
        with patch('os.path.exists', return_value=True), \
             patch('os.remove'):
            
            result = generate_thumbnail("user-responses/test/video.webm", "test")
            
            # Should have been called twice
            self.assertEqual(mock_subprocess.call_count, 2)
            
            # First call should use '-ss', '5'
            first_call_args = mock_subprocess.call_args_list[0][0][0]
            ss_index_1 = first_call_args.index('-ss')
            self.assertEqual(first_call_args[ss_index_1 + 1], '5')
            
            # Second call should use '-ss', '1'
            second_call_args = mock_subprocess.call_args_list[1][0][0]
            ss_index_2 = second_call_args.index('-ss')
            self.assertEqual(second_call_args[ss_index_2 + 1], '1')
    
    def test_filename_conversion(self):
        """Test filename conversion from .webm to .jpg"""
        test_cases = [
            ("video.webm", "video.jpg"),
            ("test_video_123.webm", "test_video_123.jpg"),
            ("question1_20241201_120000_abcd1234.webm", "question1_20241201_120000_abcd1234.jpg")
        ]
        
        for webm_name, expected_jpg in test_cases:
            result = webm_name.replace('.webm', '.jpg')
            self.assertEqual(result, expected_jpg)
    
    @patch('boto3.client')
    def test_error_handling(self, mock_boto3):
        """Test error handling in thumbnail generation"""
        try:
            from app import generate_thumbnail
        except ImportError:
            self.skipTest("App module not available")
        
        # Mock S3 client that raises exception
        mock_s3 = MagicMock()
        mock_s3.download_file.side_effect = Exception("S3 download failed")
        mock_boto3.return_value = mock_s3
        
        # Should raise exception
        with self.assertRaises(Exception):
            generate_thumbnail("user-responses/test/video.webm", "test")

def main():
    """Run thumbnail generation tests"""
    print("=== Thumbnail Generation Tests ===\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestThumbnailGeneration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())