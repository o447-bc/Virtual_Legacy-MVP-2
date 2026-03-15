# Test Audio Samples

## Required Files

These audio files are needed for testing streaming transcription:

1. **short_3sec.webm** - 3 seconds of clear speech (e.g., "Hello, this is a test")
2. **medium_10sec.webm** - 10 seconds of clear speech
3. **long_30sec.webm** - 30 seconds of clear speech
4. **silent_5sec.webm** - 5 seconds of silence
5. **noisy_5sec.webm** - 5 seconds with background noise

## How to Generate

### Option 1: Record via Browser (Recommended)
Use the ConversationInterface component to record actual audio samples that match production format.

### Option 2: Use existing conversation audio
Copy audio files from S3 bucket: `s3://virtual-legacy/conversations/*/audio/`

### Option 3: Generate with ffmpeg
```bash
# Install ffmpeg if needed
brew install ffmpeg

# Generate 3-second test audio with speech-like tone
ffmpeg -f lavfi -i "sine=frequency=440:duration=3" -c:a libopus short_3sec.webm

# Generate silent audio
ffmpeg -f lavfi -i "anullsrc=duration=5" -c:a libopus silent_5sec.webm
```

## Upload to S3 for Integration Tests

```bash
aws s3 cp short_3sec.webm s3://virtual-legacy/test-audio/
aws s3 cp medium_10sec.webm s3://virtual-legacy/test-audio/
aws s3 cp long_30sec.webm s3://virtual-legacy/test-audio/
aws s3 cp silent_5sec.webm s3://virtual-legacy/test-audio/
```

## Current Status

⚠️ Audio samples not yet created. Need to generate before running integration tests.
