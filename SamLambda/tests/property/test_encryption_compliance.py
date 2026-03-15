"""
Property-based tests for encryption compliance across all resources.

Feature: phase1-security-hardening, Property 14: Compliance - All Data Encrypted

Tests verify that:
- All DynamoDB tables use customer-managed KMS encryption (not AWS-managed keys)
- All S3 buckets use customer-managed KMS encryption (not AWS-managed keys)
- No resources use AWS default encryption

Uses Hypothesis to test compliance properties across all data storage resources.

Validates: Requirements 10.1
"""

import boto3
import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings, strategies as st
from hypothesis import HealthCheck


@pytest.fixture(scope="module")
def dynamodb_client():
    """Create DynamoDB client for testing."""
    return boto3.client('dynamodb', region_name='us-east-1')


@pytest.fixture(scope="module")
def s3_client():
    """Create S3 client for testing."""
    return boto3.client('s3', region_name='us-east-1')


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
def soulreel_table_names():
    """
    Return the list of SoulReel DynamoDB table names to test for Phase 1.
    
    These are the tables that were updated in Phase 1 to use DataEncryptionKey:
    - PersonaSignupTempDB (new encryption)
    - PersonaRelationshipsDB (upgraded to CMK)
    - EngagementDB (upgraded to CMK)
    
    Note: Other tables (userQuestionStatusDB, userQuestionLevelProgressDB, userStatusDB)
    are managed outside CloudFormation and are not in Phase 1 scope.
    """
    return [
        'PersonaSignupTempDB',
        'PersonaRelationshipsDB',
        'EngagementDB'
    ]


@pytest.fixture(scope="module")
def soulreel_bucket_names(s3_client):
    """
    Return the list of SoulReel S3 bucket names to test.
    
    These are the buckets that should be encrypted with the DataEncryptionKey.
    The audit log bucket name includes the AWS account ID.
    """
    # Get account ID from STS
    import boto3
    sts_client = boto3.client('sts', region_name='us-east-1')
    try:
        account_id = sts_client.get_caller_identity()['Account']
        audit_bucket_name = f'soulreel-audit-logs-{account_id}'
    except Exception:
        # If we can't get account ID, just use a placeholder
        audit_bucket_name = 'soulreel-audit-logs'
    
    return [
        'virtual-legacy',
        audit_bucket_name
    ]


class TestEncryptionCompliance:
    """
    Property-based test suite for encryption compliance.
    
    These tests verify that all data storage resources use customer-managed
    encryption keys, not AWS-managed keys.
    """
    
    def test_all_dynamodb_tables_use_cmk(
        self,
        dynamodb_client,
        soulreel_table_names,
        data_encryption_key_arn
    ):
        """
        Property: For all DynamoDB tables, they must use customer-managed KMS encryption.
        
        This test verifies that:
        1. All tables have encryption enabled
        2. All tables use KMS encryption (SSEType: KMS)
        3. All tables specify a KMSMasterKeyArn (confirms customer-managed)
        4. No tables use AWS-managed keys (default encryption)
        
        Validates: Requirement 10.1 (DynamoDB encryption compliance)
        """
        tables_checked = 0
        tables_with_issues = []
        
        for table_name in soulreel_table_names:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_description = response['Table']
                tables_checked += 1
                
                # Check 1: Table must have SSEDescription
                if 'SSEDescription' not in table_description:
                    tables_with_issues.append(
                        f"{table_name}: No SSEDescription found (encryption not configured)"
                    )
                    continue
                
                sse_description = table_description['SSEDescription']
                
                # Check 2: Encryption must be enabled
                if sse_description.get('Status') != 'ENABLED':
                    tables_with_issues.append(
                        f"{table_name}: Encryption status is {sse_description.get('Status')}, "
                        f"expected ENABLED"
                    )
                    continue
                
                # Check 3: Must use KMS encryption (not AWS-managed)
                sse_type = sse_description.get('SSEType')
                if sse_type != 'KMS':
                    tables_with_issues.append(
                        f"{table_name}: SSEType is {sse_type}, expected KMS "
                        f"(customer-managed key required)"
                    )
                    continue
                
                # Check 4: Must have KMSMasterKeyArn (confirms customer-managed key)
                if 'KMSMasterKeyArn' not in sse_description:
                    tables_with_issues.append(
                        f"{table_name}: No KMSMasterKeyArn found "
                        f"(customer-managed key required)"
                    )
                    continue
                
                # Check 5: Verify it's using the DataEncryptionKey
                table_key_arn = sse_description['KMSMasterKeyArn']
                if table_key_arn != data_encryption_key_arn:
                    tables_with_issues.append(
                        f"{table_name}: Using wrong KMS key. "
                        f"Expected {data_encryption_key_arn}, "
                        f"found {table_key_arn}"
                    )
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # Table doesn't exist yet - skip it
                    continue
                raise
        
        # Assert that we checked at least some tables
        assert tables_checked > 0, \
            "No DynamoDB tables found. Deploy CloudFormation stack first."
        
        # Assert that all checked tables passed compliance
        if tables_with_issues:
            failure_message = (
                f"Encryption compliance failed for {len(tables_with_issues)} "
                f"out of {tables_checked} DynamoDB tables:\n" +
                "\n".join(f"  - {issue}" for issue in tables_with_issues)
            )
            pytest.fail(failure_message)
    
    def test_all_s3_buckets_use_cmk(
        self,
        s3_client,
        soulreel_bucket_names,
        data_encryption_key_arn
    ):
        """
        Property: For all S3 buckets, they must use customer-managed KMS encryption.
        
        This test verifies that:
        1. All buckets have default encryption configured
        2. All buckets use aws:kms encryption algorithm
        3. All buckets specify a KMSMasterKeyID (confirms customer-managed)
        4. No buckets use AWS-managed keys (AES256)
        
        Validates: Requirement 10.1 (S3 encryption compliance)
        """
        buckets_checked = 0
        buckets_with_issues = []
        
        for bucket_name in soulreel_bucket_names:
            try:
                # Check if bucket exists first
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] in ['404', 'NoSuchBucket']:
                        # Bucket doesn't exist yet - skip it
                        continue
                    raise
                
                buckets_checked += 1
                
                # Get bucket encryption configuration
                try:
                    response = s3_client.get_bucket_encryption(Bucket=bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                        buckets_with_issues.append(
                            f"{bucket_name}: No encryption configuration found "
                            f"(default encryption not enabled)"
                        )
                        continue
                    raise
                
                rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
                
                # Check 1: Must have at least one encryption rule
                if not rules:
                    buckets_with_issues.append(
                        f"{bucket_name}: No encryption rules configured"
                    )
                    continue
                
                # Check the first rule (should be the default)
                rule = rules[0]
                sse_default = rule.get('ApplyServerSideEncryptionByDefault', {})
                
                # Check 2: Must use aws:kms algorithm (not AES256)
                sse_algorithm = sse_default.get('SSEAlgorithm')
                if sse_algorithm != 'aws:kms':
                    buckets_with_issues.append(
                        f"{bucket_name}: SSEAlgorithm is {sse_algorithm}, expected aws:kms "
                        f"(customer-managed key required, not AWS-managed AES256)"
                    )
                    continue
                
                # Check 3: Must have KMSMasterKeyID (confirms customer-managed key)
                if 'KMSMasterKeyID' not in sse_default:
                    buckets_with_issues.append(
                        f"{bucket_name}: No KMSMasterKeyID found "
                        f"(customer-managed key required)"
                    )
                    continue
                
                # Check 4: Verify it's using the DataEncryptionKey
                bucket_key_id = sse_default['KMSMasterKeyID']
                # The bucket may store key ID or ARN, so check if they match
                if data_encryption_key_arn not in bucket_key_id and bucket_key_id not in data_encryption_key_arn:
                    buckets_with_issues.append(
                        f"{bucket_name}: Using wrong KMS key. "
                        f"Expected {data_encryption_key_arn}, "
                        f"found {bucket_key_id}"
                    )
                
            except ClientError as e:
                # Unexpected error - re-raise
                raise
        
        # Assert that we checked at least some buckets
        assert buckets_checked > 0, \
            "No S3 buckets found. Deploy resources first."
        
        # Assert that all checked buckets passed compliance
        if buckets_with_issues:
            failure_message = (
                f"Encryption compliance failed for {len(buckets_with_issues)} "
                f"out of {buckets_checked} S3 buckets:\n" +
                "\n".join(f"  - {issue}" for issue in buckets_with_issues)
            )
            pytest.fail(failure_message)
    
    def test_no_resources_use_aws_managed_keys(
        self,
        dynamodb_client,
        s3_client,
        soulreel_table_names,
        soulreel_bucket_names
    ):
        """
        Property: No data storage resources should use AWS-managed keys.
        
        This is a negative test that verifies we're not using:
        - DynamoDB default encryption (AWS-managed keys)
        - S3 AES256 encryption (AWS-managed keys)
        
        All resources must use customer-managed KMS keys for compliance.
        
        Validates: Requirement 10.1 (no AWS-managed keys)
        """
        resources_with_aws_managed_keys = []
        
        # Check DynamoDB tables
        for table_name in soulreel_table_names:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table_description = response['Table']
                
                if 'SSEDescription' in table_description:
                    sse_description = table_description['SSEDescription']
                    sse_type = sse_description.get('SSEType')
                    
                    # If SSEType is not 'KMS', it's using AWS-managed keys
                    if sse_type and sse_type != 'KMS':
                        resources_with_aws_managed_keys.append(
                            f"DynamoDB table {table_name}: Using AWS-managed keys "
                            f"(SSEType: {sse_type})"
                        )
                    
                    # If no KMSMasterKeyArn, it's using AWS-managed keys
                    if sse_type == 'KMS' and 'KMSMasterKeyArn' not in sse_description:
                        resources_with_aws_managed_keys.append(
                            f"DynamoDB table {table_name}: Using AWS-managed KMS key "
                            f"(no KMSMasterKeyArn specified)"
                        )
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    continue
                raise
        
        # Check S3 buckets
        for bucket_name in soulreel_bucket_names:
            try:
                # Check if bucket exists
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                except ClientError as e:
                    if e.response['Error']['Code'] in ['404', 'NoSuchBucket']:
                        continue
                    raise
                
                # Get encryption configuration
                try:
                    response = s3_client.get_bucket_encryption(Bucket=bucket_name)
                    rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
                    
                    if rules:
                        rule = rules[0]
                        sse_default = rule.get('ApplyServerSideEncryptionByDefault', {})
                        sse_algorithm = sse_default.get('SSEAlgorithm')
                        
                        # If using AES256, it's AWS-managed
                        if sse_algorithm == 'AES256':
                            resources_with_aws_managed_keys.append(
                                f"S3 bucket {bucket_name}: Using AWS-managed keys "
                                f"(SSEAlgorithm: AES256)"
                            )
                        
                        # If using aws:kms but no KMSMasterKeyID, it's AWS-managed
                        if sse_algorithm == 'aws:kms' and 'KMSMasterKeyID' not in sse_default:
                            resources_with_aws_managed_keys.append(
                                f"S3 bucket {bucket_name}: Using AWS-managed KMS key "
                                f"(no KMSMasterKeyID specified)"
                            )
                
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                        # No encryption = using AWS-managed keys by default
                        resources_with_aws_managed_keys.append(
                            f"S3 bucket {bucket_name}: No encryption configured "
                            f"(defaults to AWS-managed keys)"
                        )
                        continue
                    raise
                
            except ClientError:
                raise
        
        # Assert that no resources are using AWS-managed keys
        if resources_with_aws_managed_keys:
            failure_message = (
                f"Found {len(resources_with_aws_managed_keys)} resources using "
                f"AWS-managed keys (compliance violation):\n" +
                "\n".join(f"  - {issue}" for issue in resources_with_aws_managed_keys)
            )
            pytest.fail(failure_message)
    
    @settings(
        max_examples=10,  # Run 10 iterations to verify consistency
        deadline=None,  # Disable deadline for AWS API calls
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        # Generate random table indices to test (0-2 for 3 tables)
        table_index=st.integers(min_value=0, max_value=2)
    )
    def test_property_dynamodb_encryption_consistency(
        self,
        dynamodb_client,
        soulreel_table_names,
        data_encryption_key_arn,
        table_index
    ):
        """
        Property: For any DynamoDB table in the system, if it exists, it must use CMK encryption.
        
        This property-based test randomly selects tables and verifies they consistently
        use customer-managed encryption across multiple test runs.
        
        Validates: Requirement 10.1 (consistency check)
        """
        # Select a table based on the generated index
        if table_index >= len(soulreel_table_names):
            return  # Skip if index out of range
        
        table_name = soulreel_table_names[table_index]
        
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table_description = response['Table']
            
            # If table exists, it must have proper encryption
            assert 'SSEDescription' in table_description, \
                f"Table {table_name} must have encryption configured"
            
            sse_description = table_description['SSEDescription']
            
            # Must use KMS encryption
            assert sse_description.get('SSEType') == 'KMS', \
                f"Table {table_name} must use KMS encryption (customer-managed key)"
            
            # Must have KMSMasterKeyArn
            assert 'KMSMasterKeyArn' in sse_description, \
                f"Table {table_name} must specify KMSMasterKeyArn (customer-managed key)"
            
            # Must use the correct key
            assert sse_description['KMSMasterKeyArn'] == data_encryption_key_arn, \
                f"Table {table_name} must use DataEncryptionKey"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist - skip this iteration
                return
            raise
    
    @settings(
        max_examples=10,  # Run 10 iterations to verify consistency
        deadline=None,  # Disable deadline for AWS API calls
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        # Generate random bucket indices to test
        bucket_index=st.integers(min_value=0, max_value=1)
    )
    def test_property_s3_encryption_consistency(
        self,
        s3_client,
        soulreel_bucket_names,
        data_encryption_key_arn,
        bucket_index
    ):
        """
        Property: For any S3 bucket in the system, if it exists, it must use CMK encryption.
        
        This property-based test randomly selects buckets and verifies they consistently
        use customer-managed encryption across multiple test runs.
        
        Validates: Requirement 10.1 (consistency check)
        """
        # Select a bucket based on the generated index
        if bucket_index >= len(soulreel_bucket_names):
            return  # Skip if index out of range
        
        bucket_name = soulreel_bucket_names[bucket_index]
        
        try:
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] in ['404', 'NoSuchBucket']:
                    # Bucket doesn't exist - skip this iteration
                    return
                raise
            
            # Get encryption configuration
            response = s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            
            # If bucket exists, it must have encryption rules
            assert len(rules) > 0, \
                f"Bucket {bucket_name} must have encryption rules configured"
            
            rule = rules[0]
            sse_default = rule.get('ApplyServerSideEncryptionByDefault', {})
            
            # Must use aws:kms algorithm
            assert sse_default.get('SSEAlgorithm') == 'aws:kms', \
                f"Bucket {bucket_name} must use aws:kms encryption (customer-managed key)"
            
            # Must have KMSMasterKeyID
            assert 'KMSMasterKeyID' in sse_default, \
                f"Bucket {bucket_name} must specify KMSMasterKeyID (customer-managed key)"
            
            # Must use the correct key (check if ARN is contained in the key ID or vice versa)
            bucket_key_id = sse_default['KMSMasterKeyID']
            assert (data_encryption_key_arn in bucket_key_id or 
                    bucket_key_id in data_encryption_key_arn), \
                f"Bucket {bucket_name} must use DataEncryptionKey"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(
                    f"Bucket {bucket_name} exists but has no encryption configured "
                    f"(compliance violation)"
                )
            raise
