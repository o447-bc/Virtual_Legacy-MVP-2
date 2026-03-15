"""
Test script for email templates.

This script verifies that all email templates generate valid output.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_templates import (
    assignment_invitation_email,
    assignment_notification_email,
    assignment_accepted_email,
    assignment_declined_email,
    assignment_revoked_email,
    access_granted_email,
    check_in_email
)


def test_all_templates():
    """Test all email templates to ensure they generate valid output."""
    
    print("Testing Email Templates...")
    print("=" * 60)
    
    # Sample data
    access_conditions = [
        {'condition_type': 'immediate'},
        {'condition_type': 'time_delayed', 'activation_date': '2026-03-01T12:00:00Z'},
        {'condition_type': 'inactivity_trigger', 'inactivity_months': 6, 'check_in_interval_days': 30},
        {'condition_type': 'manual_release'}
    ]
    
    # Test 1: Assignment Invitation
    print("\n1. Testing assignment_invitation_email...")
    subject, html, text = assignment_invitation_email(
        benefactor_email="benefactor@example.com",
        legacy_maker_name="John Doe",
        invitation_token="test-token-123",
        access_conditions=access_conditions
    )
    assert subject, "Subject should not be empty"
    assert "John Doe" in html, "HTML should contain legacy maker name"
    assert "test-token-123" in html, "HTML should contain invitation token"
    assert len(text) > 0, "Text body should not be empty"
    print("   ✓ Passed")
    
    # Test 2: Assignment Notification
    print("\n2. Testing assignment_notification_email...")
    subject, html, text = assignment_notification_email(
        benefactor_email="benefactor@example.com",
        benefactor_name="Jane Smith",
        legacy_maker_name="John Doe",
        legacy_maker_id="user-123",
        access_conditions=access_conditions
    )
    assert subject, "Subject should not be empty"
    assert "Jane Smith" in html, "HTML should contain benefactor name"
    assert "John Doe" in html, "HTML should contain legacy maker name"
    print("   ✓ Passed")
    
    # Test 3: Assignment Accepted
    print("\n3. Testing assignment_accepted_email...")
    subject, html, text = assignment_accepted_email(
        legacy_maker_email="maker@example.com",
        legacy_maker_name="John Doe",
        benefactor_name="Jane Smith",
        benefactor_email="benefactor@example.com"
    )
    assert subject, "Subject should not be empty"
    assert "accepted" in subject.lower(), "Subject should mention acceptance"
    assert "Jane Smith" in html, "HTML should contain benefactor name"
    print("   ✓ Passed")
    
    # Test 4: Assignment Declined
    print("\n4. Testing assignment_declined_email...")
    subject, html, text = assignment_declined_email(
        legacy_maker_email="maker@example.com",
        legacy_maker_name="John Doe",
        benefactor_name="Jane Smith",
        benefactor_email="benefactor@example.com"
    )
    assert subject, "Subject should not be empty"
    assert "declined" in subject.lower(), "Subject should mention decline"
    assert "Jane Smith" in html, "HTML should contain benefactor name"
    print("   ✓ Passed")
    
    # Test 5: Assignment Revoked
    print("\n5. Testing assignment_revoked_email...")
    subject, html, text = assignment_revoked_email(
        benefactor_email="benefactor@example.com",
        benefactor_name="Jane Smith",
        legacy_maker_name="John Doe"
    )
    assert subject, "Subject should not be empty"
    assert "revoked" in subject.lower(), "Subject should mention revocation"
    assert "John Doe" in html, "HTML should contain legacy maker name"
    print("   ✓ Passed")
    
    # Test 6: Access Granted
    print("\n6. Testing access_granted_email...")
    subject, html, text = access_granted_email(
        benefactor_email="benefactor@example.com",
        benefactor_name="Jane Smith",
        legacy_maker_name="John Doe",
        trigger_reason="time delay expired"
    )
    assert subject, "Subject should not be empty"
    assert "Jane Smith" in html, "HTML should contain benefactor name"
    assert "time delay expired" in html.lower(), "HTML should contain trigger reason"
    print("   ✓ Passed")
    
    # Test 7: Check-In Email
    print("\n7. Testing check_in_email...")
    subject, html, text = check_in_email(
        legacy_maker_email="maker@example.com",
        legacy_maker_name="John Doe",
        check_in_token="check-in-token-456",
        check_in_interval_days=30
    )
    assert subject, "Subject should not be empty"
    assert "check-in-token-456" in html, "HTML should contain check-in token"
    assert "30" in html, "HTML should contain check-in interval"
    print("   ✓ Passed")
    
    print("\n" + "=" * 60)
    print("✅ All email template tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_all_templates()
