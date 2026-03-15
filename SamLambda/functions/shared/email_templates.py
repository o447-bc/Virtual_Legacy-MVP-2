"""
Email Templates for Legacy Maker Benefactor Assignment Feature

This module provides centralized email templates for all assignment-related notifications.
Each template function returns a tuple of (subject, html_body, text_body).

Requirements: 1.3, 3.1, 3.4, 5.8, 6.2, 6.3, 6.8, 7.4, 7.5, 8.6, 13.1-13.6
"""

import os
from datetime import datetime
from typing import List, Dict, Tuple


def get_base_url() -> str:
    """
    Get the base URL for the application from environment variables.
    
    Returns:
        str: Base URL (defaults to localhost for development)
    """
    return os.environ.get('APP_BASE_URL', 'http://localhost:8080')


def get_sender_email() -> str:
    """
    Get the sender email address from environment variables.
    
    Returns:
        str: Sender email address
    """
    return os.environ.get('SENDER_EMAIL', 'noreply@virtuallegacy.com')


def format_access_conditions_html(access_conditions: List[Dict]) -> str:
    """
    Format access conditions into HTML list for email display.
    
    Args:
        access_conditions: List of access condition dictionaries
        
    Returns:
        str: HTML formatted list of access conditions
    """
    if not access_conditions:
        return "<p>No specific conditions - access will be granted upon acceptance.</p>"
    
    conditions_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
    
    for condition in access_conditions:
        condition_type = condition.get('condition_type')
        
        if condition_type == 'immediate':
            conditions_html += "<li style='margin: 8px 0;'><strong>Immediate Access:</strong> Content will be accessible immediately upon acceptance</li>"
        
        elif condition_type == 'time_delayed':
            activation_date = condition.get('activation_date', 'Not specified')
            # Format date if it's an ISO string
            try:
                dt = datetime.fromisoformat(activation_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%B %d, %Y at %I:%M %p UTC')
                conditions_html += f"<li style='margin: 8px 0;'><strong>Time-Delayed Access:</strong> Content will become accessible on {formatted_date}</li>"
            except:
                conditions_html += f"<li style='margin: 8px 0;'><strong>Time-Delayed Access:</strong> Content will become accessible on {activation_date}</li>"
        
        elif condition_type == 'inactivity_trigger':
            months = condition.get('inactivity_months', 'Not specified')
            check_in_days = condition.get('check_in_interval_days', 30)
            conditions_html += f"<li style='margin: 8px 0;'><strong>Inactivity Trigger:</strong> Content will become accessible if the Legacy Maker is inactive for {months} months (verified through periodic check-ins every {check_in_days} days)</li>"
        
        elif condition_type == 'manual_release':
            conditions_html += "<li style='margin: 8px 0;'><strong>Manual Release:</strong> Content will become accessible when the Legacy Maker manually releases it</li>"
    
    conditions_html += "</ul>"
    return conditions_html


def format_access_conditions_text(access_conditions: List[Dict]) -> str:
    """
    Format access conditions into plain text for email display.
    
    Args:
        access_conditions: List of access condition dictionaries
        
    Returns:
        str: Plain text formatted list of access conditions
    """
    if not access_conditions:
        return "No specific conditions - access will be granted upon acceptance."
    
    conditions_text = ""
    
    for i, condition in enumerate(access_conditions, 1):
        condition_type = condition.get('condition_type')
        
        if condition_type == 'immediate':
            conditions_text += f"{i}. Immediate Access: Content will be accessible immediately upon acceptance\n"
        
        elif condition_type == 'time_delayed':
            activation_date = condition.get('activation_date', 'Not specified')
            # Format date if it's an ISO string
            try:
                dt = datetime.fromisoformat(activation_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%B %d, %Y at %I:%M %p UTC')
                conditions_text += f"{i}. Time-Delayed Access: Content will become accessible on {formatted_date}\n"
            except:
                conditions_text += f"{i}. Time-Delayed Access: Content will become accessible on {activation_date}\n"
        
        elif condition_type == 'inactivity_trigger':
            months = condition.get('inactivity_months', 'Not specified')
            check_in_days = condition.get('check_in_interval_days', 30)
            conditions_text += f"{i}. Inactivity Trigger: Content will become accessible if the Legacy Maker is inactive for {months} months (verified through periodic check-ins every {check_in_days} days)\n"
        
        elif condition_type == 'manual_release':
            conditions_text += f"{i}. Manual Release: Content will become accessible when the Legacy Maker manually releases it\n"
    
    return conditions_text


def get_email_styles() -> str:
    """
    Get common CSS styles for email templates.
    
    Returns:
        str: CSS style block
    """
    return """
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #6366f1; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 30px; background-color: #f9fafb; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; }
        .content h2 { color: #1f2937; margin-top: 0; }
        .button { display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }
        .button:hover { background-color: #4f46e5; }
        .conditions { background-color: white; padding: 15px; border-left: 4px solid #6366f1; margin: 20px 0; border-radius: 4px; }
        .conditions h3 { margin-top: 0; color: #1f2937; }
        .info-box { background-color: #eff6ff; padding: 15px; border-left: 4px solid #3b82f6; margin: 20px 0; border-radius: 4px; }
        .warning-box { background-color: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0; border-radius: 4px; }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; background-color: #f3f4f6; border-radius: 0 0 8px 8px; }
        .footer p { margin: 5px 0; }
    """


# Template 1: Assignment Invitation (Unregistered Benefactor)
def assignment_invitation_email(
    benefactor_email: str,
    legacy_maker_name: str,
    invitation_token: str,
    access_conditions: List[Dict]
) -> Tuple[str, str, str]:
    """
    Email template for inviting an unregistered benefactor to create an account.
    
    Requirements: 1.3, 6.2, 6.8, 13.1
    
    Args:
        benefactor_email: Email address of the benefactor
        legacy_maker_name: Name of the Legacy Maker who created the assignment
        invitation_token: Unique token for registration
        access_conditions: List of access condition dictionaries
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    signup_url = f"{base_url}/signup?invite={invitation_token}"
    
    conditions_html = format_access_conditions_html(access_conditions)
    conditions_text = format_access_conditions_text(access_conditions)
    
    subject = "You've been invited to access a Virtual Legacy"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>You've been invited to preserve memories</h2>
                <p>Hello,</p>
                <p><strong>{legacy_maker_name}</strong> has assigned you as a Benefactor to access their Virtual Legacy content.</p>
                <p>Virtual Legacy helps people record their memories, stories, and wisdom to share with future generations. As a Benefactor, you'll be able to access their legacy content according to the conditions they've set.</p>
                
                <div class="conditions">
                    <h3>Access Conditions:</h3>
                    {conditions_html}
                </div>
                
                <div class="info-box">
                    <p><strong>What you need to do:</strong></p>
                    <p>Create your Virtual Legacy account to accept or decline this assignment. Once you accept, you'll be able to access the content when the conditions are met.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{signup_url}" class="button">Create Your Account</a>
                </p>
                
                <p style="font-size: 14px; color: #666;">This invitation will expire in 7 days.</p>
            </div>
            <div class="footer">
                <p>This invitation was sent on behalf of {legacy_maker_name}</p>
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
You've been invited to access a Virtual Legacy

Hello,

{legacy_maker_name} has assigned you as a Benefactor to access their Virtual Legacy content.

Virtual Legacy helps people record their memories, stories, and wisdom to share with future generations. As a Benefactor, you'll be able to access their legacy content according to the conditions they've set.

Access Conditions:
{conditions_text}

What you need to do:
Create your Virtual Legacy account to accept or decline this assignment. Once you accept, you'll be able to access the content when the conditions are met.

Create your account here:
{signup_url}

This invitation will expire in 7 days.

---
This invitation was sent on behalf of {legacy_maker_name}
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 2: Assignment Notification (Registered Benefactor)
def assignment_notification_email(
    benefactor_email: str,
    benefactor_name: str,
    legacy_maker_name: str,
    legacy_maker_id: str,
    access_conditions: List[Dict]
) -> Tuple[str, str, str]:
    """
    Email template for notifying a registered benefactor of a new assignment.
    
    Requirements: 1.3, 6.3, 13.1
    
    Args:
        benefactor_email: Email address of the benefactor
        benefactor_name: Name of the benefactor
        legacy_maker_name: Name of the Legacy Maker who created the assignment
        legacy_maker_id: User ID of the Legacy Maker
        access_conditions: List of access condition dictionaries
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    dashboard_url = f"{base_url}/dashboard"
    
    conditions_html = format_access_conditions_html(access_conditions)
    conditions_text = format_access_conditions_text(access_conditions)
    
    subject = "New Legacy Assignment - Action Required"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>You've been assigned access to a Virtual Legacy</h2>
                <p>Hello {benefactor_name},</p>
                <p><strong>{legacy_maker_name}</strong> has assigned you as a Benefactor to access their Virtual Legacy content.</p>
                
                <div class="conditions">
                    <h3>Access Conditions:</h3>
                    {conditions_html}
                </div>
                
                <div class="info-box">
                    <p><strong>Action Required:</strong></p>
                    <p>Please log in to your Virtual Legacy account to review and accept or decline this assignment. Once you accept, you'll be able to access the content when the conditions are met.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{dashboard_url}" class="button">View Assignment</a>
                </p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
You've been assigned access to a Virtual Legacy

Hello {benefactor_name},

{legacy_maker_name} has assigned you as a Benefactor to access their Virtual Legacy content.

Access Conditions:
{conditions_text}

Action Required:
Please log in to your Virtual Legacy account to review and accept or decline this assignment. Once you accept, you'll be able to access the content when the conditions are met.

View your assignments here:
{dashboard_url}

---
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 3: Assignment Accepted
def assignment_accepted_email(
    legacy_maker_email: str,
    legacy_maker_name: str,
    benefactor_name: str,
    benefactor_email: str
) -> Tuple[str, str, str]:
    """
    Email template for notifying Legacy Maker that benefactor accepted assignment.
    
    Requirements: 7.4, 13.2
    
    Args:
        legacy_maker_email: Email address of the Legacy Maker
        legacy_maker_name: Name of the Legacy Maker
        benefactor_name: Name of the benefactor who accepted
        benefactor_email: Email address of the benefactor
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    manage_url = f"{base_url}/manage-benefactors"
    
    subject = "Assignment Accepted - Benefactor Confirmed"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>Your assignment has been accepted</h2>
                <p>Hello {legacy_maker_name},</p>
                <p>Good news! <strong>{benefactor_name}</strong> ({benefactor_email}) has accepted your assignment to access your Virtual Legacy content.</p>
                
                <div class="info-box">
                    <p><strong>What this means:</strong></p>
                    <p>Your benefactor will be able to access your legacy content once all the access conditions you've set are met. You can view and manage all your assignments at any time.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{manage_url}" class="button">Manage Benefactors</a>
                </p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Your assignment has been accepted

Hello {legacy_maker_name},

Good news! {benefactor_name} ({benefactor_email}) has accepted your assignment to access your Virtual Legacy content.

What this means:
Your benefactor will be able to access your legacy content once all the access conditions you've set are met. You can view and manage all your assignments at any time.

Manage your benefactors here:
{manage_url}

---
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 4: Assignment Declined
def assignment_declined_email(
    legacy_maker_email: str,
    legacy_maker_name: str,
    benefactor_name: str,
    benefactor_email: str
) -> Tuple[str, str, str]:
    """
    Email template for notifying Legacy Maker that benefactor declined assignment.
    
    Requirements: 7.5, 13.3
    
    Args:
        legacy_maker_email: Email address of the Legacy Maker
        legacy_maker_name: Name of the Legacy Maker
        benefactor_name: Name of the benefactor who declined
        benefactor_email: Email address of the benefactor
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    manage_url = f"{base_url}/manage-benefactors"
    
    subject = "Assignment Declined - Benefactor Response"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>Your assignment has been declined</h2>
                <p>Hello {legacy_maker_name},</p>
                <p><strong>{benefactor_name}</strong> ({benefactor_email}) has declined your assignment to access your Virtual Legacy content.</p>
                
                <div class="info-box">
                    <p><strong>What you can do:</strong></p>
                    <p>You can assign other benefactors to access your content, or reach out to {benefactor_name} directly if you'd like to discuss their decision.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{manage_url}" class="button">Manage Benefactors</a>
                </p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Your assignment has been declined

Hello {legacy_maker_name},

{benefactor_name} ({benefactor_email}) has declined your assignment to access your Virtual Legacy content.

What you can do:
You can assign other benefactors to access your content, or reach out to {benefactor_name} directly if you'd like to discuss their decision.

Manage your benefactors here:
{manage_url}

---
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 5: Assignment Revoked
def assignment_revoked_email(
    benefactor_email: str,
    benefactor_name: str,
    legacy_maker_name: str
) -> Tuple[str, str, str]:
    """
    Email template for notifying benefactor that assignment has been revoked.
    
    Requirements: 5.8, 13.4
    
    Args:
        benefactor_email: Email address of the benefactor
        benefactor_name: Name of the benefactor
        legacy_maker_name: Name of the Legacy Maker who revoked
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    dashboard_url = f"{base_url}/dashboard"
    
    subject = "Legacy Assignment Revoked"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>Assignment has been revoked</h2>
                <p>Hello {benefactor_name},</p>
                <p><strong>{legacy_maker_name}</strong> has revoked your assignment to access their Virtual Legacy content.</p>
                
                <div class="info-box">
                    <p><strong>What this means:</strong></p>
                    <p>You no longer have access to {legacy_maker_name}'s legacy content. If you believe this was done in error, please reach out to them directly.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{dashboard_url}" class="button">View Dashboard</a>
                </p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Assignment has been revoked

Hello {benefactor_name},

{legacy_maker_name} has revoked your assignment to access their Virtual Legacy content.

What this means:
You no longer have access to {legacy_maker_name}'s legacy content. If you believe this was done in error, please reach out to them directly.

View your dashboard here:
{dashboard_url}

---
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 6: Access Granted
def access_granted_email(
    benefactor_email: str,
    benefactor_name: str,
    legacy_maker_name: str,
    trigger_reason: str = "access conditions have been met"
) -> Tuple[str, str, str]:
    """
    Email template for notifying benefactor that access has been granted.
    
    Requirements: 8.6, 13.5
    
    Args:
        benefactor_email: Email address of the benefactor
        benefactor_name: Name of the benefactor
        legacy_maker_name: Name of the Legacy Maker
        trigger_reason: Reason why access was granted (e.g., "time delay expired", "manual release")
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    dashboard_url = f"{base_url}/dashboard"
    
    subject = "Legacy Content Now Available"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>You now have access to legacy content</h2>
                <p>Hello {benefactor_name},</p>
                <p>The access conditions for <strong>{legacy_maker_name}</strong>'s Virtual Legacy content have been satisfied.</p>
                
                <div class="info-box">
                    <p><strong>Access Granted:</strong></p>
                    <p>{trigger_reason.capitalize()}</p>
                    <p>You can now view their legacy content including videos, audio recordings, and written responses to life questions.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{dashboard_url}" class="button">View Legacy Content</a>
                </p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
You now have access to legacy content

Hello {benefactor_name},

The access conditions for {legacy_maker_name}'s Virtual Legacy content have been satisfied.

Access Granted:
{trigger_reason.capitalize()}

You can now view their legacy content including videos, audio recordings, and written responses to life questions.

View legacy content here:
{dashboard_url}

---
Virtual Legacy - Preserving memories for future generations
{base_url}
    """
    
    return subject, html_body, text_body


# Template 7: Check-In Email
def check_in_email(
    legacy_maker_email: str,
    legacy_maker_name: str,
    check_in_token: str,
    check_in_interval_days: int = 30
) -> Tuple[str, str, str]:
    """
    Email template for periodic check-in to verify Legacy Maker activity.
    
    Requirements: 3.1, 3.4, 13.6
    
    Args:
        legacy_maker_email: Email address of the Legacy Maker
        legacy_maker_name: Name of the Legacy Maker
        check_in_token: Unique token for check-in verification
        check_in_interval_days: Number of days between check-ins
        
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    base_url = get_base_url()
    check_in_url = f"{base_url}/check-in?token={check_in_token}"
    
    subject = "Virtual Legacy - Activity Check-In Required"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>{get_email_styles()}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Virtual Legacy</h1>
            </div>
            <div class="content">
                <h2>Activity Check-In</h2>
                <p>Hello {legacy_maker_name},</p>
                <p>This is a periodic check-in to verify your activity on Virtual Legacy.</p>
                
                <div class="info-box">
                    <p><strong>Why am I receiving this?</strong></p>
                    <p>You've configured one or more benefactor assignments with inactivity triggers. These check-ins help ensure your legacy content is released to your benefactors if you become unable to access your account.</p>
                    <p>We send these check-ins every {check_in_interval_days} days to verify you're still active.</p>
                </div>
                
                <div class="warning-box">
                    <p><strong>Action Required:</strong></p>
                    <p>Please click the button below to confirm your activity. If we don't receive a response to multiple consecutive check-ins, your benefactors will be granted access according to your configured settings.</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{check_in_url}" class="button">Confirm I'm Active</a>
                </p>
                
                <p style="font-size: 14px; color: #666;">This check-in link will expire in 7 days. You can also log in to your account at any time to reset the inactivity counter.</p>
            </div>
            <div class="footer">
                <p>Virtual Legacy - Preserving memories for future generations</p>
                <p><a href="{base_url}" style="color: #6366f1;">Visit Virtual Legacy</a></p>
                <p style="margin-top: 10px; font-size: 11px;">If you no longer wish to receive these check-ins, please log in and update your benefactor assignment settings.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Virtual Legacy - Activity Check-In Required

Hello {legacy_maker_name},

This is a periodic check-in to verify your activity on Virtual Legacy.

Why am I receiving this?
You've configured one or more benefactor assignments with inactivity triggers. These check-ins help ensure your legacy content is released to your benefactors if you become unable to access your account.

We send these check-ins every {check_in_interval_days} days to verify you're still active.

Action Required:
Please click the link below to confirm your activity. If we don't receive a response to multiple consecutive check-ins, your benefactors will be granted access according to your configured settings.

Confirm you're active here:
{check_in_url}

This check-in link will expire in 7 days. You can also log in to your account at any time to reset the inactivity counter.

---
Virtual Legacy - Preserving memories for future generations
{base_url}

If you no longer wish to receive these check-ins, please log in and update your benefactor assignment settings.
    """
    
    return subject, html_body, text_body
