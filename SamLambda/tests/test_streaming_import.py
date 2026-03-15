"""
Test that streaming module can be imported
"""

import sys
import os

# Add the wsDefault directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/conversationFunctions/wsDefault'))

def test_import_streaming_module():
    """Test that transcribe_streaming module can be imported"""
    try:
        import transcribe_streaming
        print("✅ transcribe_streaming module imported successfully")
        assert hasattr(transcribe_streaming, 'transcribe_audio_streaming')
        print("✅ transcribe_audio_streaming function exists")
        return True
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False

def test_import_app_with_streaming():
    """Test that app.py can import with streaming module"""
    try:
        import app
        print("✅ app module imported successfully with streaming support")
        return True
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        return False

if __name__ == "__main__":
    print("Testing streaming module imports...")
    print("="*60)
    
    success = True
    success = test_import_streaming_module() and success
    success = test_import_app_with_streaming() and success
    
    print("="*60)
    if success:
        print("✅ All import tests passed!")
    else:
        print("❌ Some tests failed")
        sys.exit(1)
