"""
Unit tests for S3 bucket encryption configuration.

Feature: phase1-security-hardening, Property 4: S3 Bucket Encryption Configuration

Tests verify that the VirtualLegacyBucket (virtual-legacy) has:
- Default encryption enabled with KMS using DataEncryptionKey
- S3 Bucket Key enabled for cost optimization
- Versioning enabled for data protection
- All public access blocked (all 4 settings)

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import boto3
import pytest
from botocore.exceptions import ClientError


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
def kms_key_arn(kms_client):
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


class TestS3BucketConfiguration:
    """Test suite for S3 bucket encryption and security configuration."""
    
    def test_bucket_encryption_uses_kms(self, s3_client, bucket_name, kms_key_arn):
        """
        Test that the bucket has default encryption enabled with KMS.
        
        Validates: Requirement 3.1
        """
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"Bucket {bucket_name} does not have encryption configured. "
                           "Run configure-s3-encryption.sh script first.")
            raise
        
        rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
        assert len(rules) > 0, "Bucket must have at least one encryption rule"
        
        # Check first rule uses KMS
        rule = rules[0]
        sse_default = rule.get('ApplyServerSideEncryptionByDefault', {})
        
        assert sse_default.get('SSEAlgorithm') == 'aws:kms', \
            "Bucket must use aws:kms encryption algorithm"
        
        # Verify it uses the DataEncryptionKey
        configured_key = sse_default.get('KMSMasterKeyID', '')
        assert kms_key_arn in configured_key or configured_key in kms_key_arn, \
            f"Bucket must use DataEncryptionKey (expected {kms_key_arn}, got {configured_key})"
    
    def test_bucket_key_enabled(self, s3_client, bucket_name):
        """
        Test that S3 Bucket Key is enabled for cost optimization.
        
        S3 Bucket Key reduces KMS API calls by 99%, significantly reducing costs.
        
        Validates: Requirement 3.1 (cost optimization aspect)
        """
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"Bucket {bucket_name} does not have encryption configured. "
                           "Run configure-s3-encryption.sh script first.")
            raise
        
        rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
        assert len(rules) > 0, "Bucket must have at least one encryption rule"
        
        # Check if BucketKeyEnabled is true
        rule = rules[0]
        bucket_key_enabled = rule.get('BucketKeyEnabled', False)
        
        assert bucket_key_enabled is True, \
            "S3 Bucket Key must be enabled to reduce KMS API costs by 99%"
    
    def test_versioning_enabled(self, s3_client, bucket_name):
        """
        Test that versioning is enabled on the bucket.
        
        Versioning protects against accidental deletion and provides data recovery.
        
        Validates: Requirement 3.2
        """
        try:
            response = s3_client.get_bucket_versioning(Bucket=bucket_name)
        except ClientError as e:
            pytest.fail(f"Failed to get versioning status for bucket {bucket_name}: {e}")
        
        versioning_status = response.get('Status', 'Disabled')
        
        assert versioning_status == 'Enabled', \
            f"Bucket versioning must be enabled (current status: {versioning_status})"
    
    def test_public_access_blocked(self, s3_client, bucket_name):
        """
        Test that all public access is blocked on the bucket.
        
        All 4 public access block settings must be enabled:
        - BlockPublicAcls
        - IgnorePublicAcls
        - BlockPublicPolicy
        - RestrictPublicBuckets
        
        Validates: Requirements 3.3, 3.4
        """
        try:
            response = s3_client.get_public_access_block(Bucket=bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                pytest.fail(f"Bucket {bucket_name} does not have public access block configured. "
                           "Run configure-s3-encryption.sh script first.")
            raise
        
        config = response.get('PublicAccessBlockConfiguration', {})
        
        # Verify all 4 settings are enabled
        assert config.get('BlockPublicAcls') is True, \
            "BlockPublicAcls must be enabled"
        
        assert config.get('IgnorePublicAcls') is True, \
            "IgnorePublicAcls must be enabled"
        
        assert config.get('BlockPublicPolicy') is True, \
            "BlockPublicPolicy must be enabled"
        
        assert config.get('RestrictPublicBuckets') is True, \
            "RestrictPublicBuckets must be enabled"
    
    def test_bucket_exists(self, s3_client, bucket_name):
        """
        Test that the bucket exists and is accessible.
        
        This is a prerequisite test to ensure the bucket is available.
        """
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                pytest.fail(f"Bucket {bucket_name} does not exist")
            elif error_code == '403':
                pytest.fail(f"Access denied to bucket {bucket_name}")
            else:
                raise
    
    def test_encryption_configuration_complete(self, s3_client, bucket_name, kms_key_arn):
        """
        Comprehensive test that verifies all encryption configuration requirements.
        
        This test combines all requirements to ensure complete configuration.
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4
        """
        # Check encryption
        try:
            enc_response = s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = enc_response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            assert len(rules) > 0, "Encryption rules must be configured"
            
            rule = rules[0]
            sse_default = rule.get('ApplyServerSideEncryptionByDefault', {})
            assert sse_default.get('SSEAlgorithm') == 'aws:kms', "Must use KMS encryption"
            assert rule.get('BucketKeyEnabled') is True, "Bucket Key must be enabled"
        except ClientError:
            pytest.fail("Encryption configuration is incomplete")
        
        # Check versioning
        ver_response = s3_client.get_bucket_versioning(Bucket=bucket_name)
        assert ver_response.get('Status') == 'Enabled', "Versioning must be enabled"
        
        # Check public access block
        try:
            pab_response = s3_client.get_public_access_block(Bucket=bucket_name)
            config = pab_response.get('PublicAccessBlockConfiguration', {})
            assert all([
                config.get('BlockPublicAcls'),
                config.get('IgnorePublicAcls'),
                config.get('BlockPublicPolicy'),
                config.get('RestrictPublicBuckets')
            ]), "All public access block settings must be enabled"
        except ClientError:
            pytest.fail("Public access block configuration is incomplete")
