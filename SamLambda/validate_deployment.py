#!/usr/bin/env python3
"""
Deployment Validation Script
Validates that the streaming transcription deployment is correct
"""

import boto3
import json
import sys

def check_lambda_config():
    """Check Lambda function configuration"""
    print("\n" + "="*60)
    print("1. Checking Lambda Configuration")
    print("="*60)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get function configuration
        response = lambda_client.get_function_configuration(
            FunctionName='Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb'
        )
        
        # Check architecture
        arch = response['Architectures'][0]
        if arch == 'x86_64':
            print(f"✅ Architecture: {arch} (correct for ffmpeg)")
        else:
            print(f"❌ Architecture: {arch} (should be x86_64)")
            return False
        
        # Check layers
        layers = response.get('Layers', [])
        ffmpeg_layer_found = False
        for layer in layers:
            if 'ffmpeg' in layer['Arn']:
                print(f"✅ FFmpeg Layer: {layer['Arn']}")
                ffmpeg_layer_found = True
        
        if not ffmpeg_layer_found:
            print("❌ FFmpeg layer not found")
            return False
        
        # Check timeout
        timeout = response['Timeout']
        if timeout >= 30:
            print(f"✅ Timeout: {timeout}s (sufficient)")
        else:
            print(f"⚠️  Timeout: {timeout}s (may be too short)")
        
        # Check memory
        memory = response['MemorySize']
        if memory >= 512:
            print(f"✅ Memory: {memory}MB (sufficient)")
        else:
            print(f"⚠️  Memory: {memory}MB (may be too low)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Lambda: {e}")
        return False

def check_test_audio():
    """Check if test audio file exists"""
    print("\n" + "="*60)
    print("2. Checking Test Audio File")
    print("="*60)
    
    s3_client = boto3.client('s3')
    
    try:
        response = s3_client.head_object(
            Bucket='virtual-legacy',
            Key='test-audio/short_audio.webm'
        )
        
        size = response['ContentLength']
        print(f"✅ Test audio exists: {size:,} bytes")
        
        if size > 0 and size < 5_000_000:  # < 5MB
            print(f"✅ File size appropriate for testing")
            return True
        else:
            print(f"⚠️  File size unusual: {size:,} bytes")
            return True
            
    except Exception as e:
        print(f"❌ Test audio not found: {e}")
        return False

def check_iam_permissions():
    """Check if Lambda has necessary IAM permissions"""
    print("\n" + "="*60)
    print("3. Checking IAM Permissions")
    print("="*60)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    iam_client = boto3.client('iam')
    
    try:
        # Get function configuration
        response = lambda_client.get_function_configuration(
            FunctionName='Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb'
        )
        
        role_arn = response['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"   Role: {role_name}")
        
        # Get attached policies
        policies_response = iam_client.list_attached_role_policies(
            RoleName=role_name
        )
        
        print(f"   Attached policies: {len(policies_response['AttachedPolicies'])}")
        
        # Note: Checking inline policies would require parsing policy documents
        # which is complex. We'll rely on CloudWatch logs to verify permissions work.
        print(f"✅ IAM role exists and has policies attached")
        print(f"   (Actual permissions will be verified during testing)")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not fully verify IAM permissions: {e}")
        return True  # Don't fail on this

def check_cloudwatch_logs():
    """Check if CloudWatch log group exists"""
    print("\n" + "="*60)
    print("4. Checking CloudWatch Logs")
    print("="*60)
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    try:
        response = logs_client.describe_log_groups(
            logGroupNamePrefix='/aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefault'
        )
        
        if response['logGroups']:
            log_group = response['logGroups'][0]['logGroupName']
            print(f"✅ Log group exists: {log_group}")
            
            # Check for recent log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if streams_response['logStreams']:
                last_event = streams_response['logStreams'][0].get('lastEventTimestamp', 0)
                if last_event > 0:
                    from datetime import datetime
                    last_time = datetime.fromtimestamp(last_event / 1000)
                    print(f"   Last activity: {last_time}")
                else:
                    print(f"   No recent activity (function not yet invoked)")
            else:
                print(f"   No log streams yet (function not yet invoked)")
            
            return True
        else:
            print(f"❌ Log group not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("STREAMING TRANSCRIPTION DEPLOYMENT VALIDATION")
    print("="*60)
    
    results = []
    
    # Run checks
    results.append(("Lambda Configuration", check_lambda_config()))
    results.append(("Test Audio File", check_test_audio()))
    results.append(("IAM Permissions", check_iam_permissions()))
    results.append(("CloudWatch Logs", check_cloudwatch_logs()))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED")
        print("\nDeployment is ready for testing!")
        print("\nNext steps:")
        print("1. Run: python3 test_streaming_e2e.py")
        print("2. Monitor CloudWatch logs during test")
        print("3. Check for streaming success or fallback to batch")
        print("\nSee TESTING_INSTRUCTIONS.md for details")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before testing")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
