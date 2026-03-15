"""
Unit tests for audit log bucket configuration.

Feature: phase1-security-hardening, Property 8: Audit Log Bucket Configuration

Tests verify that the AuditLogBucket:
- Is encrypted with the DataEncryptionKey
- Has all public access blocked
- Has lifecycle policies configured

Validates: Requirements 4.1, 4.6, 4.7, 4.8
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
def account_id():
    """Get AWS account ID."""
    sts_client = boto3.client('sts', region_name='us-east-1')
    return sts_client.get_caller_identity()['Account']


@pytest.fixture(scope="module")
def bucket_name(account_id):
    """Return the expected audit log bucket name."""
    return f"soulreel-audit-logs-{account_id}"


@pytest.fixture(scope="module")
def bucket_exists(s3_client, bucket_name):
    """Check if the audit log bucket exists."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            pytest.skip(f"Audit log bucket {bucket_name} not found. Deploy CloudFormation stack first.")
        raise


@pytest.fixture(scope="module")
def encryption_config(s3_client, bucket_name, bucket_exists):
    """Get the bucket encryption configuration."""
    try:
        response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        return response.get('ServerSideEncryptionConfiguration', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
            pytest.fail(f"Bucket {bucket_name} does not have encryption configured")
        raise


@pytest.fixture(scope="module")
def public_access_block(s3_client, bucket_name, bucket_exists):
    """Get the bucket public access block configuration."""
    try:
        response = s3_client.get_public_access_block(Bucket=bucket_name)
        return response.get('PublicAccessBlockConfiguration', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
            pytest.fail(f"Bucket {bucket_name} does not have public access block configured")
        raise


@pytest.fixture(scope="module")
def lifecycle_config(s3_client, bucket_name, bucket_exists):
    """Get the bucket lifecycle configuration."""
    try:
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        return response.get('Rules', [])
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            pytest.fail(f"Bucket {bucket_name} does not have lifecycle configuration")
        raise


@pytest.fixture(scope="module")
def data_encryption_key_arn(kms_client):
    """Get the DataEncryptionKey ARN."""
    try:
        response = kms_client.describe_key(KeyId='alias/soulreel-data-encryption')
        return response['KeyMetadata']['Arn']
    except ClientError as e:
        pytest.skip(f"DataEncryptionKey not found: {e}")


class TestAuditLogBucketConfiguration:
    """Test suite for audit log bucket configuration compliance."""
    
    def test_bucket_encrypted_with_kms(self, encryption_config):
        """
        Test that the audit log bucket uses KMS encryption.
        
        Validates: Requirement 4.1
        """
        rules = encryption_config.get('Rules', [])
        assert len(rules) > 0, "Bucket must have encryption rules configured"
        
        # Check the default encryption rule
        default_encryption = rules[0].get('ApplyServerSideEncryptionByDefault', {})
        sse_algorithm = default_encryption.get('SSEAlgorithm')
        
        assert sse_algorithm == 'aws:kms', \
            f"Bucket must use KMS encryption (found: {sse_algorithm})"
    
    def test_bucket_uses_data_encryption_key(self, encryption_config, data_encryption_key_arn):
        """
        Test that the audit log bucket uses the DataEncryptionKey.
        
        Validates: Requirement 4.1
        """
        rules = encryption_config.get('Rules', [])
        default_encryption = rules[0].get('ApplyServerSideEncryptionByDefault', {})
        kms_master_key_id = default_encryption.get('KMSMasterKeyID', '')
        
        # The KMS key ID could be an ARN or key ID
        assert data_encryption_key_arn in kms_master_key_id or \
               kms_master_key_id in data_encryption_key_arn, \
            f"Bucket must use DataEncryptionKey (expected: {data_encryption_key_arn}, found: {kms_master_key_id})"
    
    def test_bucket_key_enabled(self, encryption_config):
        """
        Test that S3 Bucket Key is enabled to reduce KMS costs.
        
        Validates: Requirement 4.1 (cost optimization)
        """
        rules = encryption_config.get('Rules', [])
        bucket_key_enabled = rules[0].get('BucketKeyEnabled', False)
        
        assert bucket_key_enabled is True, \
            "S3 Bucket Key must be enabled to reduce KMS API costs"
    
    def test_public_access_blocked(self, public_access_block):
        """
        Test that all public access is blocked on the audit log bucket.
        
        Validates: Requirement 4.8
        """
        assert public_access_block.get('BlockPublicAcls') is True, \
            "BlockPublicAcls must be enabled"
        
        assert public_access_block.get('IgnorePublicAcls') is True, \
            "IgnorePublicAcls must be enabled"
        
        assert public_access_block.get('BlockPublicPolicy') is True, \
            "BlockPublicPolicy must be enabled"
        
        assert public_access_block.get('RestrictPublicBuckets') is True, \
            "RestrictPublicBuckets must be enabled"
    
    def test_lifecycle_glacier_transition_exists(self, lifecycle_config):
        """
        Test that lifecycle policy transitions logs to Glacier after 30 days.
        
        Validates: Requirements 4.7
        """
        glacier_rule_found = False
        
        for rule in lifecycle_config:
            if rule.get('Status') == 'Enabled':
                transitions = rule.get('Transitions', [])
                for transition in transitions:
                    if transition.get('StorageClass') == 'GLACIER':
                        glacier_rule_found = True
                        assert transition.get('Days') == 30, \
                            "Logs must transition to Glacier after 30 days"
                        break
            
            if glacier_rule_found:
                break
        
        assert glacier_rule_found, \
            "Lifecycle policy must transition logs to Glacier storage after 30 days"
    
    def test_lifecycle_expiration_exists(self, lifecycle_config):
        """
        Test that lifecycle policy deletes logs after 90 days.
        
        Validates: Requirements 4.6
        """
        expiration_rule_found = False
        
        for rule in lifecycle_config:
            if rule.get('Status') == 'Enabled':
                expiration = rule.get('Expiration', {})
                if 'Days' in expiration:
                    expiration_rule_found = True
                    assert expiration.get('Days') == 90, \
                        "Logs must be deleted after 90 days"
                    break
        
        assert expiration_rule_found, \
            "Lifecycle policy must delete logs after 90 days"
    
    def test_bucket_policy_allows_cloudtrail(self, s3_client, bucket_name, bucket_exists):
        """
        Test that bucket policy allows CloudTrail to write logs.
        
        Validates: Requirement 4.1
        """
        try:
            response = s3_client.get_bucket_policy(Bucket=bucket_name)
            policy = response.get('Policy', '{}')
            
            import json
            policy_doc = json.loads(policy)
            
            # Check for CloudTrail service principal
            cloudtrail_statement_found = False
            for statement in policy_doc.get('Statement', []):
                principal = statement.get('Principal', {})
                
                if isinstance(principal, dict):
                    service_principal = principal.get('Service', '')
                    if 'cloudtrail.amazonaws.com' in str(service_principal):
                        cloudtrail_statement_found = True
                        
                        # Verify it has PutObject or GetBucketAcl permissions
                        actions = statement.get('Action', [])
                        if isinstance(actions, str):
                            actions = [actions]
                        
                        has_required_action = any(
                            action in ['s3:PutObject', 's3:GetBucketAcl'] 
                            for action in actions
                        )
                        
                        assert has_required_action, \
                            "CloudTrail must have s3:PutObject or s3:GetBucketAcl permissions"
                        break
            
            assert cloudtrail_statement_found, \
                "Bucket policy must allow CloudTrail service to write logs"
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                pytest.fail(f"Bucket {bucket_name} does not have a bucket policy")
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                pytest.skip(f"Bucket {bucket_name} not found. Deploy CloudFormation stack first.")
            raise
