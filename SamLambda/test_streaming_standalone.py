#!/usr/bin/env python3
"""
Standalone Streaming Transcription Test
Tests streaming transcription without WebSocket/UI dependencies

Usage:
    python test_streaming_standalone.py <s3_key>
    
Example:
    python test_streaming_standalone.py conversations/user-123/q-456/audio/turn-1-1234567890.webm
"""

import sys
import os
import time

# Add function path
sys.path.insert(0, 'functions/conversationFunctions/wsDefault')

from transcribe_streaming import transcribe_audio_streaming
from transcribe import transcribe_audio


def test_streaming_only(s3_key):
    """Test streaming transcription in isolation"""
    print("\n" + "="*70)
    print("STREAMING TRANSCRIPTION TEST")
    print("="*70)
    print(f"S3 Key: {s3_key}")
    print("="*70 + "\n")
    
    try:
        start = time.time()
        
        result = transcribe_audio_streaming(
            s3_key=s3_key,
            user_id='test-user',
            question_id='test-question',
            turn_number=1
        )
        
        duration = time.time() - start
        
        print("\n" + "="*70)
        print("✅ STREAMING SUCCESSFUL")
        print("="*70)
        print(f"Duration:    {duration:.2f}s")
        print(f"Transcript:  {result['transcript']}")
        print(f"Length:      {len(result['transcript'])} chars")
        print("="*70 + "\n")
        
        return True, duration, result
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ STREAMING FAILED")
        print("="*70)
        print(f"Error: {e}")
        print("="*70 + "\n")
        
        import traceback
        print(traceback.format_exc())
        
        return False, None, None


def test_batch_comparison(s3_key):
    """Test batch transcription for comparison"""
    print("\n" + "="*70)
    print("BATCH TRANSCRIPTION TEST (Comparison)")
    print("="*70)
    print(f"S3 Key: {s3_key}")
    print("="*70 + "\n")
    
    try:
        start = time.time()
        
        result = transcribe_audio(
            s3_key=s3_key,
            user_id='test-user',
            question_id='test-question',
            turn_number=2
        )
        
        duration = time.time() - start
        
        print("\n" + "="*70)
        print("✅ BATCH SUCCESSFUL")
        print("="*70)
        print(f"Duration:    {duration:.2f}s")
        print(f"Transcript:  {result['transcript']}")
        print(f"Length:      {len(result['transcript'])} chars")
        print("="*70 + "\n")
        
        return True, duration, result
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ BATCH FAILED")
        print("="*70)
        print(f"Error: {e}")
        print("="*70 + "\n")
        
        return False, None, None


def compare_results(streaming_success, streaming_time, streaming_result,
                   batch_success, batch_time, batch_result):
    """Compare streaming vs batch results"""
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)
    
    if streaming_success and batch_success:
        improvement = ((batch_time - streaming_time) / batch_time) * 100
        
        print(f"\n⏱️  Performance:")
        print(f"   Streaming: {streaming_time:.2f}s")
        print(f"   Batch:     {batch_time:.2f}s")
        print(f"   Improvement: {improvement:.1f}% faster")
        
        if improvement > 0:
            print(f"   ✅ Streaming is {improvement:.1f}% faster!")
        else:
            print(f"   ⚠️  Streaming is slower by {abs(improvement):.1f}%")
        
        streaming_text = streaming_result['transcript'].lower().strip()
        batch_text = batch_result['transcript'].lower().strip()
        
        print(f"\n📝 Transcripts:")
        print(f"   Streaming: {streaming_text}")
        print(f"   Batch:     {batch_text}")
        
        if streaming_text == batch_text:
            print(f"   ✅ Transcripts match exactly")
        else:
            words_streaming = set(streaming_text.split())
            words_batch = set(batch_text.split())
            
            if len(words_streaming) > 0 and len(words_batch) > 0:
                overlap = len(words_streaming & words_batch)
                total = len(words_streaming | words_batch)
                similarity = (overlap / total) * 100
                
                print(f"   ⚠️  Transcripts differ - Similarity: {similarity:.1f}%")
        
        print(f"\n🎯 Success Criteria:")
        print(f"   Streaming works: ✅")
        print(f"   Faster than batch: {'✅' if improvement > 0 else '❌'}")
        print(f"   At least 50% faster: {'✅' if improvement > 50 else '❌'}")
        
    elif streaming_success:
        print(f"✅ Streaming succeeded")
        print(f"❌ Batch failed - cannot compare")
    elif batch_success:
        print(f"❌ Streaming failed")
        print(f"✅ Batch succeeded")
    else:
        print(f"❌ Both methods failed")
    
    print("="*70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_streaming_standalone.py <s3_key>")
        print("\nExample:")
        print("  python test_streaming_standalone.py conversations/user-123/q-456/audio/turn-1-1234567890.webm")
        sys.exit(1)
    
    s3_key = sys.argv[1]
    
    print("\n" + "="*70)
    print("TRANSCRIPTION TEST SUITE")
    print("="*70)
    print(f"Target: s3://virtual-legacy/{s3_key}")
    print("="*70)
    
    # Test streaming
    streaming_success, streaming_time, streaming_result = test_streaming_only(s3_key)
    
    # Test batch for comparison
    batch_success, batch_time, batch_result = test_batch_comparison(s3_key)
    
    # Compare
    compare_results(
        streaming_success, streaming_time, streaming_result,
        batch_success, batch_time, batch_result
    )
    
    sys.exit(0 if (streaming_success and batch_success) else 1)


if __name__ == "__main__":
    main()
