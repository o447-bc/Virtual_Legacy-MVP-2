#!/bin/bash
# Wrapper script to run streaming test with correct Python interpreter

echo "Streaming Transcription E2E Test"
echo "================================="
echo ""

# Try to find Python with boto3
if python3 -c "import boto3" 2>/dev/null; then
    echo "✅ Using system python3 (has boto3)"
    python3 test_streaming_e2e.py
elif /Users/Oliver/anaconda3/bin/python3 -c "import boto3" 2>/dev/null; then
    echo "✅ Using anaconda python3 (has boto3)"
    /Users/Oliver/anaconda3/bin/python3 test_streaming_e2e.py
else
    echo "❌ Error: boto3 not found in any Python installation"
    echo ""
    echo "Please install boto3:"
    echo "  pip3 install boto3 websockets"
    echo ""
    echo "Or use anaconda Python:"
    echo "  /Users/Oliver/anaconda3/bin/python3 test_streaming_e2e.py"
    exit 1
fi
