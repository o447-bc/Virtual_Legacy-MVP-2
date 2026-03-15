"""
Unit tests for KMS key configuration.

Feature: phase1-security-hardening, Property 1: KMS Key Configuration

Tests verify that the DataEncryptionKey resource has:
- Automatic rotation enabled
- Alias "alias/soulreel-data-encryption" pointing to the key
- Key policy with required statements for root account and AWS services

Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""

import boto3
import pytest
from botocore.exceptions import ClientError


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
def key_alias():
    """Return the expected key alias name."""
    return "alias/soulreel-data-encryption"


@pytest.fixture(scope="module")
def key_id(kms_client, key_alias):
    """
    Get the KMS key ID from the alias.
    
    Returns None if the key doesn't exist yet (pre-deployment).
    """
    try:
        response = kms_client.describe_key(KeyId=key_alias)
        return response['KeyMetadata']['KeyId']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            pytest.skip(f"KMS key with alias {key_alias} not found. Deploy CloudFormation stack first.")
        raise


class TestKMSKeyConfiguration:
    """Test suite for KMS key configuration compliance."""
    
    def test_key_rotation_enabled(self, kms_client, key_id):
        """
        Test that automatic key rotation is enabled on the DataEncryptionKey.
        
        Validates: Requirement 1.1
        """
        response = kms_client.get_key_rotation_status(KeyId=key_id)
        assert response['KeyRotationEnabled'] is True, \
            "KMS key rotation must be enabled for compliance"
    
    def test_key_alias_exists(self, kms_client, key_alias, key_id):
        """
        Test that the alias 'alias/soulreel-data-encryption' exists and points to the correct key.
        
        Validates: Requirement 1.4
        """
        response = kms_client.describe_key(KeyId=key_alias)
        
        # Verify alias resolves to a key
        assert 'KeyMetadata' in response, "Alias must resolve to a valid KMS key"
        
        # Verify alias points to the expected key
        alias_key_id = response['KeyMetadata']['KeyId']
        assert alias_key_id == key_id, \
            f"Alias must point to the DataEncryptionKey (expected {key_id}, got {alias_key_id})"
    
    def test_key_policy_root_access(self, kms_client, key_id, account_id):
        """
        Test that the key policy grants root account full administrative access.
        
        Validates: Requirement 1.3
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        # Check for root account statement
        import json
        policy_doc = json.loads(policy)
        
        root_statement_found = False
        for statement in policy_doc.get('Statement', []):
            principal = statement.get('Principal', {})
            
            # Check if this is the root account statement
            if isinstance(principal, dict):
                aws_principal = principal.get('AWS', '')
                if isinstance(aws_principal, str):
                    if f"arn:aws:iam::{account_id}:root" in aws_principal:
                        root_statement_found = True
                        # Verify it has full access
                        assert statement.get('Effect') == 'Allow', \
                            "Root account statement must have Allow effect"
                        assert 'kms:*' in statement.get('Action', []), \
                            "Root account must have kms:* permissions"
                        break
                elif isinstance(aws_principal, list):
                    if any(f"arn:aws:iam::{account_id}:root" in arn for arn in aws_principal):
                        root_statement_found = True
                        assert statement.get('Effect') == 'Allow', \
                            "Root account statement must have Allow effect"
                        assert 'kms:*' in statement.get('Action', []), \
                            "Root account must have kms:* permissions"
                        break
        
        assert root_statement_found, \
            f"Key policy must contain statement granting root account (arn:aws:iam::{account_id}:root) full access"
    
    def test_key_policy_cloudwatch_logs_access(self, kms_client, key_id):
        """
        Test that the key policy allows CloudWatch Logs service to encrypt/decrypt.
        
        Validates: Requirement 1.2 (CloudWatch Logs service access)
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        import json
        policy_doc = json.loads(policy)
        
        cloudwatch_statement_found = False
        for statement in policy_doc.get('Statement', []):
            principal = statement.get('Principal', {})
            
            # Check if this is the CloudWatch Logs service statement
            if isinstance(principal, dict):
                service_principal = principal.get('Service', '')
                if 'logs.amazonaws.com' in str(service_principal):
                    cloudwatch_statement_found = True
                    
                    # Verify it has encryption/decryption permissions
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    required_actions = ['kms:Encrypt', 'kms:Decrypt', 'kms:GenerateDataKey*']
                    for required_action in required_actions:
                        assert any(required_action in action for action in actions), \
                            f"CloudWatch Logs must have {required_action} permission"
                    break
        
        assert cloudwatch_statement_found, \
            "Key policy must contain statement allowing CloudWatch Logs service access"
    
    def test_key_policy_lambda_access(self, kms_client, key_id):
        """
        Test that the key policy allows Lambda service to decrypt.
        
        Validates: Requirement 1.2 (Lambda service access)
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        import json
        policy_doc = json.loads(policy)
        
        lambda_statement_found = False
        for statement in policy_doc.get('Statement', []):
            principal = statement.get('Principal', {})
            
            # Check if this is the Lambda service statement
            if isinstance(principal, dict):
                service_principal = principal.get('Service', '')
                if 'lambda.amazonaws.com' in str(service_principal):
                    lambda_statement_found = True
                    
                    # Verify it has decryption permissions
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    assert any('kms:Decrypt' in action for action in actions), \
                        "Lambda service must have kms:Decrypt permission"
                    break
        
        assert lambda_statement_found, \
            "Key policy must contain statement allowing Lambda service access"
    
    def test_key_policy_dynamodb_access(self, kms_client, key_id):
        """
        Test that the key policy allows DynamoDB service to encrypt/decrypt.
        
        Validates: Requirement 1.2 (DynamoDB service access)
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        import json
        policy_doc = json.loads(policy)
        
        dynamodb_statement_found = False
        for statement in policy_doc.get('Statement', []):
            principal = statement.get('Principal', {})
            
            # Check if this is the DynamoDB service statement
            if isinstance(principal, dict):
                service_principal = principal.get('Service', '')
                if 'dynamodb.amazonaws.com' in str(service_principal):
                    dynamodb_statement_found = True
                    
                    # Verify it has encryption/decryption permissions
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    required_actions = ['kms:Encrypt', 'kms:Decrypt', 'kms:GenerateDataKey*']
                    for required_action in required_actions:
                        assert any(required_action in action for action in actions), \
                            f"DynamoDB must have {required_action} permission"
                    break
        
        assert dynamodb_statement_found, \
            "Key policy must contain statement allowing DynamoDB service access"
    
    def test_key_policy_s3_access(self, kms_client, key_id):
        """
        Test that the key policy allows S3 service to encrypt/decrypt.
        
        Validates: Requirement 1.2 (S3 service access)
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        import json
        policy_doc = json.loads(policy)
        
        s3_statement_found = False
        for statement in policy_doc.get('Statement', []):
            principal = statement.get('Principal', {})
            
            # Check if this is the S3 service statement
            if isinstance(principal, dict):
                service_principal = principal.get('Service', '')
                if 's3.amazonaws.com' in str(service_principal):
                    s3_statement_found = True
                    
                    # Verify it has encryption/decryption permissions
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    required_actions = ['kms:Encrypt', 'kms:Decrypt', 'kms:GenerateDataKey*']
                    for required_action in required_actions:
                        assert any(required_action in action for action in actions), \
                            f"S3 must have {required_action} permission"
                    break
        
        assert s3_statement_found, \
            "Key policy must contain statement allowing S3 service access"
    
    def test_key_policy_has_condition_keys(self, kms_client, key_id):
        """
        Test that service access statements use condition keys to restrict access.
        
        Validates: Requirement 1.2 (condition keys for service access)
        """
        response = kms_client.get_key_policy(KeyId=key_id, PolicyName='default')
        policy = response['Policy']
        
        import json
        policy_doc = json.loads(policy)
        
        # Check that service statements have conditions
        service_principals = [
            'logs.amazonaws.com',
            'lambda.amazonaws.com', 
            'dynamodb.amazonaws.com',
            's3.amazonaws.com'
        ]
        
        for service in service_principals:
            service_statement_found = False
            has_condition = False
            
            for statement in policy_doc.get('Statement', []):
                principal = statement.get('Principal', {})
                
                if isinstance(principal, dict):
                    service_principal = principal.get('Service', '')
                    if service in str(service_principal):
                        service_statement_found = True
                        
                        # Check for condition keys
                        if 'Condition' in statement:
                            has_condition = True
                        break
            
            if service_statement_found:
                assert has_condition, \
                    f"Service statement for {service} should have condition keys to restrict access"
