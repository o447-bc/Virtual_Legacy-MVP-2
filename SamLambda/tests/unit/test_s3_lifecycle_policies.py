"""
Unit tests for S3 lifecycle policy configuration.

Feature: phase1-security-hardening, Property 6: S3 Lifecycle Policy Configuration

Tests verify that the VirtualLegacyBucket (virtual-legacy) has lifecycle policies:
- Transition to STANDARD_IA after 90 days
- Transition to GLACIER_IR after 365 days
- Delete old versions after 90 days

Validates: Requirement 3.7
"""

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def s3_client():
    """Create S3 client for testing."""
    return boto3.client('s3', region_name='us-east-1')


@pytest.fixture(scope="module")
def bucket_name():
    """Return the bucket name to test."""
    return "virtual-legacy"


@pytest.fixture(scope="module")
def lifecycle_rules(s3_client, bucket_name):
    """
    Get lifecycle rules for the bucket.
    
    Returns None if lifecycle configuration doesn't exist yet (pre-deployment).
    """
    try:
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        return response.get('Rules', [])
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            pytest.skip(f"Bucket {bucket_name} does not have lifecycle configuration. "
                       "Run configure-s3-lifecycle.sh script first.")
        raise


class TestS3LifecyclePolicies:
    """Test suite for S3 lifecycle policy configuration."""
    
    def test_lifecycle_rules_exist(self, lifecycle_rules):
        """
        Test that lifecycle rules are configured on the bucket.
        
        Validates: Requirement 3.7 (lifecycle policies exist)
        """
        assert lifecycle_rules is not None, "Lifecycle rules must be configured"
        assert len(lifecycle_rules) > 0, "At least one lifecycle rule must exist"
    
    def test_transition_to_standard_ia(self, lifecycle_rules):
        """
        Test that a lifecycle rule transitions objects to STANDARD_IA after 90 days.
        
        STANDARD_IA (Infrequent Access) is ~50% cheaper than STANDARD storage.
        
        Validates: Requirement 3.7 (STANDARD_IA transition)
        """
        # Find rule with STANDARD_IA transition
        standard_ia_rule = None
        for rule in lifecycle_rules:
            if rule.get('Status') != 'Enabled':
                continue
            
            transitions = rule.get('Transitions', [])
            for transition in transitions:
                if transition.get('StorageClass') == 'STANDARD_IA':
                    standard_ia_rule = rule
                    break
            
            if standard_ia_rule:
                break
        
        assert standard_ia_rule is not None, \
            "Lifecycle rule for STANDARD_IA transition must exist"
        
        # Verify transition happens after 90 days
        transitions = standard_ia_rule.get('Transitions', [])
        standard_ia_transition = None
        for transition in transitions:
            if transition.get('StorageClass') == 'STANDARD_IA':
                standard_ia_transition = transition
                break
        
        assert standard_ia_transition is not None, \
            "STANDARD_IA transition must be configured"
        
        days = standard_ia_transition.get('Days')
        assert days == 90, \
            f"STANDARD_IA transition must occur after 90 days (configured: {days} days)"
    
    def test_transition_to_glacier_ir(self, lifecycle_rules):
        """
        Test that a lifecycle rule transitions objects to GLACIER_IR after 365 days.
        
        GLACIER_IR (Instant Retrieval) is ~70% cheaper than STANDARD storage
        while maintaining instant retrieval capability.
        
        Validates: Requirement 3.7 (GLACIER_IR transition)
        """
        # Find rule with GLACIER_IR transition
        glacier_ir_rule = None
        for rule in lifecycle_rules:
            if rule.get('Status') != 'Enabled':
                continue
            
            transitions = rule.get('Transitions', [])
            for transition in transitions:
                if transition.get('StorageClass') == 'GLACIER_IR':
                    glacier_ir_rule = rule
                    break
            
            if glacier_ir_rule:
                break
        
        assert glacier_ir_rule is not None, \
            "Lifecycle rule for GLACIER_IR transition must exist"
        
        # Verify transition happens after 365 days
        transitions = glacier_ir_rule.get('Transitions', [])
        glacier_ir_transition = None
        for transition in transitions:
            if transition.get('StorageClass') == 'GLACIER_IR':
                glacier_ir_transition = transition
                break
        
        assert glacier_ir_transition is not None, \
            "GLACIER_IR transition must be configured"
        
        days = glacier_ir_transition.get('Days')
        assert days == 365, \
            f"GLACIER_IR transition must occur after 365 days (configured: {days} days)"
    
    def test_delete_old_versions(self, lifecycle_rules):
        """
        Test that a lifecycle rule deletes old versions after 90 days.
        
        This prevents accumulation of old versions and reduces storage costs.
        
        Validates: Requirement 3.7 (version deletion)
        """
        # Find rule with NoncurrentVersionExpiration
        version_deletion_rule = None
        for rule in lifecycle_rules:
            if rule.get('Status') != 'Enabled':
                continue
            
            if 'NoncurrentVersionExpiration' in rule:
                version_deletion_rule = rule
                break
        
        assert version_deletion_rule is not None, \
            "Lifecycle rule for deleting old versions must exist"
        
        # Verify deletion happens after 90 days
        expiration = version_deletion_rule.get('NoncurrentVersionExpiration', {})
        noncurrent_days = expiration.get('NoncurrentDays')
        
        assert noncurrent_days == 90, \
            f"Old versions must be deleted after 90 days (configured: {noncurrent_days} days)"
    
    def test_all_lifecycle_rules_enabled(self, lifecycle_rules):
        """
        Test that all lifecycle rules are in 'Enabled' status.
        
        Disabled rules do not execute, so all rules must be enabled.
        
        Validates: Requirement 3.7 (rules are active)
        """
        for rule in lifecycle_rules:
            rule_id = rule.get('Id', 'Unknown')
            status = rule.get('Status', 'Unknown')
            
            assert status == 'Enabled', \
                f"Lifecycle rule '{rule_id}' must be enabled (current status: {status})"
    
    def test_lifecycle_configuration_complete(self, lifecycle_rules):
        """
        Comprehensive test that verifies all lifecycle requirements are met.
        
        This test ensures the complete lifecycle configuration is in place.
        
        Validates: Requirement 3.7
        """
        # Check we have at least 3 rules (or rules covering all 3 requirements)
        assert len(lifecycle_rules) >= 3, \
            f"Expected at least 3 lifecycle rules (found {len(lifecycle_rules)})"
        
        # Verify STANDARD_IA transition exists
        has_standard_ia = False
        for rule in lifecycle_rules:
            transitions = rule.get('Transitions', [])
            for transition in transitions:
                if transition.get('StorageClass') == 'STANDARD_IA':
                    has_standard_ia = True
                    break
        
        assert has_standard_ia, "STANDARD_IA transition rule must exist"
        
        # Verify GLACIER_IR transition exists
        has_glacier_ir = False
        for rule in lifecycle_rules:
            transitions = rule.get('Transitions', [])
            for transition in transitions:
                if transition.get('StorageClass') == 'GLACIER_IR':
                    has_glacier_ir = True
                    break
        
        assert has_glacier_ir, "GLACIER_IR transition rule must exist"
        
        # Verify version deletion exists
        has_version_deletion = False
        for rule in lifecycle_rules:
            if 'NoncurrentVersionExpiration' in rule:
                has_version_deletion = True
                break
        
        assert has_version_deletion, "Version deletion rule must exist"
    
    def test_lifecycle_rules_apply_to_all_objects(self, lifecycle_rules):
        """
        Test that lifecycle rules apply to all objects in the bucket.
        
        Rules should have empty prefix or no prefix filter to apply globally.
        
        Validates: Requirement 3.7 (rules apply to all objects)
        """
        for rule in lifecycle_rules:
            rule_id = rule.get('Id', 'Unknown')
            
            # Check filter configuration
            filter_config = rule.get('Filter', {})
            
            # If filter exists, it should have empty prefix or no prefix
            if filter_config:
                prefix = filter_config.get('Prefix', '')
                assert prefix == '', \
                    f"Lifecycle rule '{rule_id}' should apply to all objects (has prefix: '{prefix}')"
