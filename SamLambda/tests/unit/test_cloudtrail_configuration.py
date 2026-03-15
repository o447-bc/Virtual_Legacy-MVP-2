"""
Unit tests for CloudTrail configuration.

Feature: phase1-security-hardening, Property 7: CloudTrail Configuration

Tests verify that the DataAccessTrail resource:
- Is enabled and multi-region
- Has log file validation enabled
- Has event selectors configured for S3 and DynamoDB data events

Validates: Requirements 4.2, 4.3, 4.4, 4.5
"""

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def cloudtrail_client():
    """Create CloudTrail client for testing."""
    return boto3.client('cloudtrail', region_name='us-east-1')


@pytest.fixture(scope="module")
def trail_name():
    """Return the expected trail name."""
    return "soulreel-data-access-trail"


@pytest.fixture(scope="module")
def trail_info(cloudtrail_client, trail_name):
    """
    Get the CloudTrail trail information.
    
    Returns None if the trail doesn't exist yet (pre-deployment).
    """
    try:
        response = cloudtrail_client.describe_trails(trailNameList=[trail_name])
        if not response['trailList']:
            pytest.skip(f"CloudTrail trail {trail_name} not found. Deploy CloudFormation stack first.")
        return response['trailList'][0]
    except ClientError as e:
        pytest.skip(f"Error accessing CloudTrail: {e}")


@pytest.fixture(scope="module")
def trail_status(cloudtrail_client, trail_name):
    """Get the CloudTrail trail status."""
    try:
        response = cloudtrail_client.get_trail_status(Name=trail_name)
        return response
    except ClientError as e:
        pytest.skip(f"Error getting trail status: {e}")


@pytest.fixture(scope="module")
def event_selectors(cloudtrail_client, trail_name):
    """Get the CloudTrail event selectors."""
    try:
        response = cloudtrail_client.get_event_selectors(TrailName=trail_name)
        return response.get('EventSelectors', [])
    except ClientError as e:
        pytest.skip(f"Error getting event selectors: {e}")


class TestCloudTrailConfiguration:
    """Test suite for CloudTrail configuration compliance."""
    
    def test_trail_is_logging(self, trail_status):
        """
        Test that the CloudTrail trail is actively logging.
        
        Validates: Requirement 4.4
        """
        assert trail_status['IsLogging'] is True, \
            "CloudTrail trail must be actively logging"
    
    def test_trail_is_multi_region(self, trail_info):
        """
        Test that the CloudTrail trail is configured as multi-region.
        
        Validates: Requirement 4.5
        """
        assert trail_info.get('IsMultiRegionTrail') is True, \
            "CloudTrail trail must be configured as multi-region"
    
    def test_log_file_validation_enabled(self, trail_info):
        """
        Test that log file validation is enabled to detect tampering.
        
        Validates: Requirement 4.4
        """
        assert trail_info.get('LogFileValidationEnabled') is True, \
            "CloudTrail log file validation must be enabled"
    
    def test_s3_event_selector_exists(self, event_selectors):
        """
        Test that event selector for S3 data events exists.
        
        Validates: Requirement 4.2
        """
        s3_selector_found = False
        
        for selector in event_selectors:
            data_resources = selector.get('DataResources', [])
            for resource in data_resources:
                if resource.get('Type') == 'AWS::S3::Object':
                    values = resource.get('Values', [])
                    # Check if virtual-legacy bucket is monitored
                    if any('virtual-legacy' in value for value in values):
                        s3_selector_found = True
                        
                        # Verify ReadWriteType is All
                        assert selector.get('ReadWriteType') == 'All', \
                            "S3 event selector must monitor all read/write operations"
                        
                        # Verify IncludeManagementEvents is true
                        assert selector.get('IncludeManagementEvents') is True, \
                            "S3 event selector must include management events"
                        break
            
            if s3_selector_found:
                break
        
        assert s3_selector_found, \
            "CloudTrail must have event selector for S3 data events on virtual-legacy bucket"
    
    def test_dynamodb_event_selector_exists(self, event_selectors):
        """
        Test that event selector for DynamoDB data events exists.
        
        Validates: Requirement 4.3
        """
        dynamodb_selector_found = False
        
        for selector in event_selectors:
            data_resources = selector.get('DataResources', [])
            for resource in data_resources:
                if resource.get('Type') == 'AWS::DynamoDB::Table':
                    dynamodb_selector_found = True
                    
                    # Verify ReadWriteType is All
                    assert selector.get('ReadWriteType') == 'All', \
                        "DynamoDB event selector must monitor all read/write operations"
                    
                    # Verify IncludeManagementEvents is false (as per design)
                    assert selector.get('IncludeManagementEvents') is False, \
                        "DynamoDB event selector should not include management events"
                    break
            
            if dynamodb_selector_found:
                break
        
        assert dynamodb_selector_found, \
            "CloudTrail must have event selector for DynamoDB data events"
    
    def test_dynamodb_tables_monitored(self, event_selectors):
        """
        Test that all required DynamoDB tables are monitored.
        
        Validates: Requirement 4.3
        """
        expected_tables = [
            'PersonaRelationshipsDB',
            'EngagementDB',
            'userQuestionStatusDB',
            'userQuestionLevelProgressDB',
            'userStatusDB'
        ]
        
        monitored_tables = []
        
        for selector in event_selectors:
            data_resources = selector.get('DataResources', [])
            for resource in data_resources:
                if resource.get('Type') == 'AWS::DynamoDB::Table':
                    values = resource.get('Values', [])
                    for value in values:
                        # Extract table name from ARN
                        if 'table/' in value:
                            table_name = value.split('table/')[-1]
                            monitored_tables.append(table_name)
        
        # Check that all expected tables are monitored
        for table in expected_tables:
            assert any(table in monitored for monitored in monitored_tables), \
                f"DynamoDB table {table} must be monitored by CloudTrail"
    
    def test_trail_references_audit_bucket(self, trail_info):
        """
        Test that the trail writes logs to the audit log bucket.
        
        Validates: Requirement 4.1
        """
        s3_bucket_name = trail_info.get('S3BucketName', '')
        assert 'soulreel-audit-logs' in s3_bucket_name, \
            "CloudTrail must write logs to the soulreel-audit-logs bucket"
