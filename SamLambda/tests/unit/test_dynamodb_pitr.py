"""
Unit tests for DynamoDB Point-in-Time Recovery (PITR) configuration.

Feature: phase1-security-hardening, Property 3: DynamoDB Point-in-Time Recovery

Tests verify that PersonaSignupTempDB has PITR enabled for data recovery.

Validates: Requirements 2.4
"""

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def dynamodb_client():
    """Create DynamoDB client for testing."""
    return boto3.client('dynamodb', region_name='us-east-1')


class TestDynamoDBPITR:
    """Test suite for DynamoDB Point-in-Time Recovery configuration."""
    
    def test_persona_signup_temp_table_has_pitr_enabled(self, dynamodb_client):
        """
        Test that PersonaSignupTempDB has Point-in-Time Recovery enabled.
        
        PITR allows recovery of the table to any point in time within the last 35 days,
        protecting against accidental data deletion or corruption.
        
        Validates: Requirement 2.4
        """
        table_name = 'PersonaSignupTempDB'
        
        try:
            response = dynamodb_client.describe_continuous_backups(TableName=table_name)
            continuous_backups = response['ContinuousBackupsDescription']
            
            # Check that ContinuousBackupsStatus is ENABLED
            assert 'ContinuousBackupsStatus' in continuous_backups, \
                f"Table {table_name} must have ContinuousBackupsStatus"
            
            assert continuous_backups['ContinuousBackupsStatus'] == 'ENABLED', \
                f"Table {table_name} must have continuous backups ENABLED " \
                f"(found: {continuous_backups.get('ContinuousBackupsStatus')})"
            
            # Check that PointInTimeRecoveryDescription exists
            assert 'PointInTimeRecoveryDescription' in continuous_backups, \
                f"Table {table_name} must have PointInTimeRecoveryDescription"
            
            pitr_description = continuous_backups['PointInTimeRecoveryDescription']
            
            # Check that PointInTimeRecoveryStatus is ENABLED
            assert 'PointInTimeRecoveryStatus' in pitr_description, \
                f"Table {table_name} must have PointInTimeRecoveryStatus"
            
            assert pitr_description['PointInTimeRecoveryStatus'] == 'ENABLED', \
                f"Table {table_name} must have PITR ENABLED " \
                f"(found: {pitr_description.get('PointInTimeRecoveryStatus')})"
            
            # Verify that EarliestRestorableDateTime exists (confirms PITR is active)
            assert 'EarliestRestorableDateTime' in pitr_description, \
                f"Table {table_name} must have EarliestRestorableDateTime (confirms PITR is active)"
            
            # Verify that LatestRestorableDateTime exists
            assert 'LatestRestorableDateTime' in pitr_description, \
                f"Table {table_name} must have LatestRestorableDateTime"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
            raise
    
    def test_pitr_provides_recovery_window(self, dynamodb_client):
        """
        Test that PITR provides a valid recovery window for PersonaSignupTempDB.
        
        When PITR is enabled, AWS maintains continuous backups for 35 days.
        This test verifies that the recovery window is available.
        
        Validates: Requirement 2.4
        """
        table_name = 'PersonaSignupTempDB'
        
        try:
            response = dynamodb_client.describe_continuous_backups(TableName=table_name)
            continuous_backups = response['ContinuousBackupsDescription']
            
            # Get PITR description
            pitr_description = continuous_backups.get('PointInTimeRecoveryDescription', {})
            
            # Verify recovery window exists
            earliest = pitr_description.get('EarliestRestorableDateTime')
            latest = pitr_description.get('LatestRestorableDateTime')
            
            assert earliest is not None, \
                f"Table {table_name} must have EarliestRestorableDateTime"
            
            assert latest is not None, \
                f"Table {table_name} must have LatestRestorableDateTime"
            
            # Verify that latest is after earliest (valid recovery window)
            assert latest > earliest, \
                f"Table {table_name} must have valid recovery window " \
                f"(latest: {latest}, earliest: {earliest})"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                pytest.skip(f"Table {table_name} not found. Deploy CloudFormation stack first.")
            raise
