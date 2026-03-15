"""
Property-based tests for S3 bucket policy enforcement.

Feature: phase1-security-hardening, Property 5: S3 Bucket Policy Enforcement

Tests verify that the VirtualLegacyBucket bucket policy denies:
- Uploads without encryption headers (s3:x-amz-server-side-encryption)
- Uploads with incorrect KMS key ID

Uses Hypothesis to generate random file content and test scenarios across 100+ iterations.

Validates: Requirements 3.5, 3.6
"""

import boto3
import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings, strategies as st
from hypothesis import HealthCheck
import uuid


@pytest.fixture(scope="module")
def s3_client():
    """Create S3 client for testing."""
    return boto3.client('s3', region_name='us-east-1')


@pytest.fixture(scope="module")
def kms_client():
    """Create KMS client for testing."""
    return boto3.client('kms', region_name='us-east-1')


@pytest.fixture(scope="module")
def bucket_name():
    """Return the bucket name to test."""
    return "virtual-legacy"


@pytest.fixture(scope="module")
def correct_kms_key_arn(kms_client):
    """
    Get the DataEncryptionKey ARN from the alias.
    
    Returns None if the key doesn't exist yet (pre-deployment).
    """
    try:
        response = kms_client.describe_key(KeyId="alias/soulreel-data-encryption")
        return response['KeyMetadata']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            pytest.skip("KMS key not found. Deploy CloudFormation stack first.")
        raise


@pytest.fixture(scope="module")
def wrong_kms_key_arn(kms_client):
    """
    Get a different KMS key ARN to test incorrect key rejection.
    
    Creates a temporary key if needed, or uses an existing one.
    """
    # Try to find any other KMS key in the account
    try:
        response = kms_client.list_keys(Limit=10)
        keys = response.get('Keys', [])
        
        # Get the correct key ARN to exclude it
        try:
            correct_key_response = kms_client.describe_key(KeyId="alias/soulreel-data-encryption")
            correct_key_id = correct_key_response['KeyMetadata']['KeyId']
        except ClientError:
            correct_key_id = None
        
        # Find a different key
        for key in keys:
            key_id = key['KeyId']
            if key_id != correct_key_id:
                key_details = kms_client.describe_key(KeyId=key_id)
                # Only use keys that are enabled and not pending deletion
                if key_details['KeyMetadata']['KeyState'] == 'Enabled':
                    return key_details['KeyMetadata']['Arn']
        
        # If no other key exists, return a fake ARN (will still be rejected by policy)
        # This is acceptable because the policy will deny it regardless
        return "arn:aws:kms:us-east-1:123456789012:key/00000000-0000-0000-0000-000000000000"
        
    except ClientError:
        # If we can't list keys, use a fake ARN
        return "arn:aws:kms:us-east-1:123456789012:key/00000000-0000-0000-0000-000000000000"


class TestS3BucketPolicyEnforcement:
    """
    Property-based test suite for S3 bucket policy enforcement.
    
    These tests verify that the bucket policy correctly denies uploads
    that don't meet encryption requirements.
    """
    
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for AWS API calls
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        file_content=st.binary(min_size=1, max_size=1024),  # Random binary content up to 1KB
        object_suffix=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=5,
            max_size=20
        )
    )
    def test_deny_upload_without_encryption_header(
        self,
        s3_client,
        bucket_name,
        file_content,
        object_suffix
    ):
        """
        Property: For any object upload to VirtualLegacyBucket without encryption headers,
        the upload should be denied by the bucket policy.
        
        This test generates random file content and attempts to upload without
        specifying server-side encryption. The bucket policy should deny all such uploads.
        
        Validates: Requirement 3.5
        """
        # Generate unique object key for this test iteration
        object_key = f"test-uploads/no-encryption-{object_suffix}-{uuid.uuid4()}.bin"
        
        # Attempt to upload without encryption headers
        with pytest.raises(ClientError) as exc_info:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_content
                # Deliberately NOT including ServerSideEncryption parameter
            )
        
        # Verify the upload was denied with AccessDenied error
        error = exc_info.value
        error_code = error.response['Error']['Code']
        
        # The bucket policy should deny with AccessDenied
        assert error_code == 'AccessDenied', (
            f"Expected AccessDenied error for upload without encryption headers, "
            f"but got {error_code}: {error.response['Error']['Message']}"
        )
        
        # Verify the object was not created
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            pytest.fail(f"Object {object_key} should not exist after denied upload")
        except ClientError as e:
            # 404 is expected - object doesn't exist
            assert e.response['Error']['Code'] == '404'
    
    @settings(
        max_examples=100,
        deadline=None,  # Disable deadline for AWS API calls
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        file_content=st.binary(min_size=1, max_size=1024),  # Random binary content up to 1KB
        object_suffix=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=5,
            max_size=20
        )
    )
    def test_deny_upload_with_wrong_kms_key(
        self,
        s3_client,
        bucket_name,
        correct_kms_key_arn,
        wrong_kms_key_arn,
        file_content,
        object_suffix
    ):
        """
        Property: For any object upload to VirtualLegacyBucket with incorrect KMS key,
        the upload should be denied by the bucket policy.
        
        This test generates random file content and attempts to upload with
        a KMS key that is not the DataEncryptionKey. The bucket policy should
        deny all such uploads.
        
        Validates: Requirement 3.6
        """
        # Generate unique object key for this test iteration
        object_key = f"test-uploads/wrong-key-{object_suffix}-{uuid.uuid4()}.bin"
        
        # Attempt to upload with wrong KMS key
        with pytest.raises(ClientError) as exc_info:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_content,
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=wrong_kms_key_arn  # Using wrong key
            )
        
        # Verify the upload was denied with AccessDenied error
        error = exc_info.value
        error_code = error.response['Error']['Code']
        
        # The bucket policy should deny with AccessDenied
        assert error_code == 'AccessDenied', (
            f"Expected AccessDenied error for upload with wrong KMS key, "
            f"but got {error_code}: {error.response['Error']['Message']}"
        )
        
        # Verify the object was not created
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            pytest.fail(f"Object {object_key} should not exist after denied upload")
        except ClientError as e:
            # 404 is expected - object doesn't exist
            assert e.response['Error']['Code'] == '404'
    
    @settings(
        max_examples=50,  # Fewer examples for the positive test
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        file_content=st.binary(min_size=1, max_size=1024),
        object_suffix=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=5,
            max_size=20
        )
    )
    def test_allow_upload_with_correct_encryption(
        self,
        s3_client,
        bucket_name,
        correct_kms_key_arn,
        file_content,
        object_suffix
    ):
        """
        Property: For any object upload to VirtualLegacyBucket with correct encryption,
        the upload should succeed.
        
        This is a positive test to verify that uploads with correct encryption
        headers are allowed. This ensures the bucket policy doesn't block legitimate uploads.
        
        Validates: Requirements 3.5, 3.6 (positive case)
        """
        # Generate unique object key for this test iteration
        object_key = f"test-uploads/correct-encryption-{object_suffix}-{uuid.uuid4()}.bin"
        
        try:
            # Attempt to upload with correct encryption
            response = s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_content,
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=correct_kms_key_arn  # Using correct key
            )
            
            # Verify upload succeeded
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200, \
                "Upload with correct encryption should succeed"
            
            # Verify the object exists and is encrypted
            head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            assert head_response['ServerSideEncryption'] == 'aws:kms', \
                "Object should be encrypted with KMS"
            
        finally:
            # Clean up: delete the test object
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            except ClientError:
                pass  # Ignore cleanup errors
    
    def test_bucket_policy_exists(self, s3_client, bucket_name):
        """
        Prerequisite test: Verify that the bucket has a policy configured.
        
        This test ensures the bucket policy is in place before running property tests.
        """
        try:
            response = s3_client.get_bucket_policy(Bucket=bucket_name)
            policy = response['Policy']
            
            # Verify policy is not empty
            assert policy, "Bucket policy should not be empty"
            
            # Verify policy contains encryption enforcement
            import json
            policy_doc = json.loads(policy)
            
            statements = policy_doc.get('Statement', [])
            assert len(statements) > 0, "Bucket policy should have statements"
            
            # Check for encryption-related statements
            has_encryption_statement = False
            for statement in statements:
                if statement.get('Effect') == 'Deny':
                    condition = statement.get('Condition', {})
                    # Look for encryption-related conditions
                    if any('encryption' in str(k).lower() for k in condition.keys()):
                        has_encryption_statement = True
                        break
            
            assert has_encryption_statement, \
                "Bucket policy should contain encryption enforcement statements"
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                pytest.fail(
                    f"Bucket {bucket_name} does not have a policy configured. "
                    "Deploy s3-bucket-policy-stack.yml first."
                )
            raise
