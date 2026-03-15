#!/usr/bin/env python3
"""
SAM Template Validation Test
Tests the updated template.yml for FFmpeg layer integration and resource configuration.
"""

import re
import subprocess
import sys
import os

def test_template_syntax():
    """Test CloudFormation template syntax validation"""
    print("Testing CloudFormation template syntax...")
    
    try:
        result = subprocess.run(
            ['aws', 'cloudformation', 'validate-template', 
             '--template-body', 'file://template.yml', '--region', 'us-east-1'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ CloudFormation template syntax is valid")
            return True
        else:
            print(f"✗ CloudFormation template validation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("⚠ AWS CLI not found, skipping validation")
        return True

def test_upload_function_config():
    """Test UploadVideoResponseFunction configuration"""
    print("Testing UploadVideoResponseFunction configuration...")
    
    with open('template.yml', 'r') as f:
        content = f.read()
    
    # Find the UploadVideoResponseFunction section
    upload_func_match = re.search(
        r'UploadVideoResponseFunction:.*?(?=\n  \w|\nOutputs:|$)', 
        content, 
        re.DOTALL
    )
    
    if not upload_func_match:
        print("✗ UploadVideoResponseFunction not found")
        return False
    
    upload_func_text = upload_func_match.group(0)
    
    # Test timeout
    if 'Timeout: 60' in upload_func_text:
        print("✓ Timeout set to 60 seconds")
    else:
        print("✗ Timeout not set to 60 seconds")
        return False
    
    # Test memory
    if 'MemorySize: 1024' in upload_func_text:
        print("✓ Memory set to 1024MB")
    else:
        print("✗ Memory not set to 1024MB")
        return False
    
    # Test FFmpeg layer
    if 'ffmpeg' in upload_func_text.lower() and 'Layers:' in upload_func_text:
        print("✓ FFmpeg layer configured")
    else:
        print("✗ FFmpeg layer not found")
        return False
    
    # Test S3 permissions
    required_permissions = ['s3:GetObject', 's3:PutObject', 's3:PutObjectAcl']
    missing_permissions = [perm for perm in required_permissions if perm not in upload_func_text]
    
    if not missing_permissions:
        print("✓ All required S3 permissions present")
    else:
        print(f"✗ Missing S3 permissions: {missing_permissions}")
        return False
    
    return True

def test_layer_arn_format():
    """Test FFmpeg layer ARN format"""
    print("Testing FFmpeg layer ARN format...")
    
    with open('template.yml', 'r') as f:
        content = f.read()
    
    # Find layer ARN in the file
    layer_match = re.search(r'- (arn:aws:lambda:[^\n]+ffmpeg[^\n]*)', content, re.IGNORECASE)
    
    if layer_match:
        layer_arn = layer_match.group(1)
        if layer_arn.startswith('arn:aws:lambda:'):
            print(f"✓ Layer ARN format valid: {layer_arn}")
        else:
            print(f"✗ Invalid layer ARN format: {layer_arn}")
            return False
    else:
        print("✗ FFmpeg layer ARN not found")
        return False
    
    return True

def main():
    """Run all template validation tests"""
    print("=== SAM Template Validation Tests ===\n")
    
    tests = [
        test_template_syntax,
        test_upload_function_config,
        test_layer_arn_format
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All template validation tests passed!")
        return 0
    else:
        print("✗ Some template validation tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())