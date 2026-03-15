"""
Unit tests for DynamoDB table encryption compliance.

Feature: phase1-security-hardening, Property 2: DynamoDB Encryption Compliance

Tests verify that all DynamoDB tables use KMS encryption with the DataEncryptionKey:
- PersonaSignupTempDB uses KMS encryption with DataEncryptionKey ARN
- PersonaRelationshipsDB uses KMS encryption with DataEncryptionKey ARN
- EngagementDB uses KMS encryption with DataEncryptionKey ARN

Validates: Requirements 2.1, 2.2, 2.3, 10.1
"""

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def dynamodb_client():
    """Create DynamoDB client for testing."""
    return boto3.client('dynamodb', region_name='us-east-1')


@pytest.fixture(scope="module")
def kms_client():
    """Create KMS client for testing."""
    return boto3.client('kms', region_name='us-east-1')


@pytest.fixture(scope="module")
def data_encryption_key_arn(kms_client):
    """
    Get the DataEncryptionKey ARN from the alias.
    
    Returns None if the key doesn't exist yet (pre-deployment).
    """
    try:
        response = kms_client.describe_key(KeyId='alias/soulreel-data-encryption')
        return response['KeyMetadata']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            pytest.skip("DataEncryptionKey not found. Deploy CloudFormation stack first.")
        raise


@pytest.fixture(scope="module")
def table_names():
    """Return the list of table names to test."""
    return [
        'PersonaSignupTempDB',
        'PersonaRelationshipsDB',
        'EngagementDB'
    ]


class TestDynamoDBEncryptionCompliance:
    """Test suite for DynamoDB table encryption compliance."""
    
    def test_all_tables_use_kms_encryption(self, dynamodb_client, table_names, data_encryption_key_arn):
        """
        Test that all three DynamoDB tables use KMS encryption.
        
        Validates: Requirements 2.1, 2.2, 2.3, 10.1
        """
        for table_name in table_names:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_description = response['Table']
                
                # Check that SSEDescription exists
                assert 'SSEDescription' in table_description, \
                    f"Table {table_name} must have SSEDescription (encryption configuration)"
                
                sse_description = table_description['SSEDescription']
                
                # Check that SSEType is KMS
                assert 'SSEType' in sse_description, \
                    f"Table {table_name} must have SSEType specified"
                
                assert sse_description['SSEType'] == 'KMS', \
                    f"Table {table_name} must use KMS encryption (found: {sse_description.get('SSEType')})"
                
                # Check that Status is ENABLED
                assert sse_description.get('Status') == 'ENABLED', \
                    f"Table {table_name} encryption must be ENABLED (found: {sse_description.get('Status')})"
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
                raise
    
    def test_all_tables_reference_data_encryption_key(self, dynamodb_client, table_names, data_encryption_key_arn):
        """
        Test that all three DynamoDB tables reference the DataEncryptionKey ARN.
        
        Validates: Requirements 2.1, 2.2, 2.3, 10.1
        """
        for table_name in table_names:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_description = response['Table']
                
                # Check that SSEDescription exists
                assert 'SSEDescription' in table_description, \
                    f"Table {table_name} must have SSEDescription"
                
                sse_description = table_description['SSEDescription']
                
                # Check that KMSMasterKeyArn is present
                assert 'KMSMasterKeyArn' in sse_description, \
                    f"Table {table_name} must have KMSMasterKeyArn specified"
                
                table_key_arn = sse_description['KMSMasterKeyArn']
                
                # Verify it matches the DataEncryptionKey ARN
                assert table_key_arn == data_encryption_key_arn, \
                    f"Table {table_name} must use DataEncryptionKey " \
                    f"(expected: {data_encryption_key_arn}, found: {table_key_arn})"
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
                raise
    
    def test_persona_signup_temp_table_encryption(self, dynamodb_client, data_encryption_key_arn):
        """
        Test that PersonaSignupTempDB is encrypted with DataEncryptionKey.
        
        Validates: Requirement 2.1
        """
        table_name = 'PersonaSignupTempDB'
        
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table_description = response['Table']
            
            # Verify encryption is configured
            assert 'SSEDescription' in table_description, \
                f"Table {table_name} must have encryption configured"
            
            sse_description = table_description['SSEDescription']
            
            # Verify KMS encryption
            assert sse_description.get('SSEType') == 'KMS', \
                f"Table {table_name} must use KMS encryption"
            
            # Verify correct key
            assert sse_description.get('KMSMasterKeyArn') == data_encryption_key_arn, \
                f"Table {table_name} must use DataEncryptionKey"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
            raise
    
    def test_persona_relationships_table_encryption(self, dynamodb_client, data_encryption_key_arn):
        """
        Test that PersonaRelationshipsDB is encrypted with DataEncryptionKey.
        
        Validates: Requirement 2.2
        """
        table_name = 'PersonaRelationshipsDB'
        
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table_description = response['Table']
            
            # Verify encryption is configured
            assert 'SSEDescription' in table_description, \
                f"Table {table_name} must have encryption configured"
            
            sse_description = table_description['SSEDescription']
            
            # Verify KMS encryption
            assert sse_description.get('SSEType') == 'KMS', \
                f"Table {table_name} must use KMS encryption"
            
            # Verify correct key
            assert sse_description.get('KMSMasterKeyArn') == data_encryption_key_arn, \
                f"Table {table_name} must use DataEncryptionKey"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
            raise
    
    def test_engagement_table_encryption(self, dynamodb_client, data_encryption_key_arn):
        """
        Test that EngagementDB is encrypted with DataEncryptionKey.
        
        Validates: Requirement 2.3
        """
        table_name = 'EngagementDB'
        
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table_description = response['Table']
            
            # Verify encryption is configured
            assert 'SSEDescription' in table_description, \
                f"Table {table_name} must have encryption configured"
            
            sse_description = table_description['SSEDescription']
            
            # Verify KMS encryption
            assert sse_description.get('SSEType') == 'KMS', \
                f"Table {table_name} must use KMS encryption"
            
            # Verify correct key
            assert sse_description.get('KMSMasterKeyArn') == data_encryption_key_arn, \
                f"Table {table_name} must use DataEncryptionKey"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
            raise
    
    def test_no_tables_use_aws_managed_keys(self, dynamodb_client, table_names):
        """
        Test that no tables use AWS-managed keys (compliance requirement).
        
        Validates: Requirement 10.1
        """
        for table_name in table_names:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_description = response['Table']
                
                if 'SSEDescription' in table_description:
                    sse_description = table_description['SSEDescription']
                    
                    # If encryption is enabled, it must be KMS (not default AWS-managed)
                    if sse_description.get('Status') == 'ENABLED':
                        sse_type = sse_description.get('SSEType')
                        
                        # AWS-managed keys show as no SSEType or empty
                        # Customer-managed keys show as 'KMS'
                        assert sse_type == 'KMS', \
                            f"Table {table_name} must not use AWS-managed keys " \
                            f"(found SSEType: {sse_type})"
                        
                        # Verify KMSMasterKeyArn is present (confirms customer-managed)
                        assert 'KMSMasterKeyArn' in sse_description, \
                            f"Table {table_name} must use customer-managed key (KMSMasterKeyArn missing)"
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
                raise
