#!/usr/bin/env python3
"""Test script to verify S3 signature version configuration"""

import boto3
from botocore.client import Config

# Test 1: Default client (should use Signature Version 2)
print("Test 1: Default S3 client")
s3_default = boto3.client('s3', region_name='us-east-1')
url_default = s3_default.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': 'virtual-legacy',
        'Key': 'conversations/8448e4f8-40f1-7011-4b7d-a9f6c8e40b4f/childhood-00010/ai-audio/turn-0-1771699967.mp3'
    },
    ExpiresIn=3600
)
print(f"URL length: {len(url_default)}")
print(f"Contains 'X-Amz-Algorithm': {'X-Amz-Algorithm' in url_default}")
print(f"Contains 'AWSAccessKeyId': {'AWSAccessKeyId' in url_default}")
print(f"First 200 chars: {url_default[:200]}")
print()

# Test 2: Client with Signature Version 4
print("Test 2: S3 client with signature_version='s3v4'")
s3_v4 = boto3.client('s3', region_name='us-east-1', config=Config(signature_version='s3v4'))
url_v4 = s3_v4.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': 'virtual-legacy',
        'Key': 'conversations/8448e4f8-40f1-7011-4b7d-a9f6c8e40b4f/childhood-00010/ai-audio/turn-0-1771699967.mp3'
    },
    ExpiresIn=3600
)
print(f"URL length: {len(url_v4)}")
print(f"Contains 'X-Amz-Algorithm': {'X-Amz-Algorithm' in url_v4}")
print(f"Contains 'AWSAccessKeyId': {'AWSAccessKeyId' in url_v4}")
print(f"First 200 chars: {url_v4[:200]}")
print()

# Test 3: Try to access the file with both URLs
print("Test 3: Testing URL accessibility")
import urllib.request
import urllib.error

for name, url in [("Default", url_default), ("SigV4", url_v4)]:
    try:
        req = urllib.request.Request(url, method='HEAD')
        response = urllib.request.urlopen(req)
        print(f"{name} URL: SUCCESS (status {response.status})")
    except urllib.error.HTTPError as e:
        print(f"{name} URL: FAILED (status {e.code}, reason: {e.reason})")
    except Exception as e:
        print(f"{name} URL: ERROR ({type(e).__name__}: {e})")
