"""
SES Event Tracking — SNS-triggered Lambda

Processes SES open, click, and bounce events from the nurture email system.
Updates EmailCapture records with tracking data.
"""
import os
import sys
import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import boto3

TABLE_EMAIL_CAPTURE = os.environ.get('TABLE_EMAIL_CAPTURE', 'EmailCaptureDB')

dynamodb = boto3.resource('dynamodb')
email_capture_table = dynamodb.Table(TABLE_EMAIL_CAPTURE)


def _extract_stage(template_name: str) -> str:
    """Extract stage number from template name like 'soulreel-nurture-stage-2-A'."""
    match = re.search(r'stage-(\d+)', template_name or '')
    return match.group(1) if match else '0'


def _extract_email_from_event(ses_event: dict) -> str:
    """Extract recipient email from SES event data."""
    mail = ses_event.get('mail', {})
    destinations = mail.get('destination', [])
    return destinations[0].lower() if destinations else ''


def _extract_template_name(ses_event: dict) -> str:
    """Extract template name from SES mail tags or headers."""
    mail = ses_event.get('mail', {})
    tags = mail.get('tags', {})
    # SES includes template name in ses:configuration-set or custom tags
    template_tag = tags.get('ses:template-name', [''])[0] if isinstance(tags.get('ses:template-name'), list) else ''
    if not template_tag:
        # Try common headers
        for header in mail.get('headers', []):
            if header.get('name') == 'X-SES-TEMPLATE-NAME':
                template_tag = header.get('value', '')
                break
    return template_tag


def _handle_open(email: str, stage: str):
    """Handle an email open event."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        email_capture_table.update_item(
            Key={'email': email},
            UpdateExpression='SET openCount = if_not_exists(openCount, :zero) + :inc, '
                           'lastOpenedAt = :now, '
                           'stageOpens.#stage = if_not_exists(stageOpens.#stage, :zero) + :inc',
            ExpressionAttributeNames={'#stage': stage},
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':now': now_iso,
            },
        )
    except Exception as e:
        print(f'[ERROR] Failed to track open for {email}: {e}')


def _handle_click(email: str, stage: str):
    """Handle an email click event."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        email_capture_table.update_item(
            Key={'email': email},
            UpdateExpression='SET clickCount = if_not_exists(clickCount, :zero) + :inc, '
                           'lastClickedAt = :now, '
                           'stageClicks.#stage = if_not_exists(stageClicks.#stage, :zero) + :inc',
            ExpressionAttributeNames={'#stage': stage},
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':now': now_iso,
            },
        )
    except Exception as e:
        print(f'[ERROR] Failed to track click for {email}: {e}')


def _handle_bounce(email: str, bounce_type: str):
    """Handle a bounce event. Escalates soft→hard on second soft bounce."""
    try:
        if bounce_type == 'Permanent':
            # Hard bounce — mark immediately
            email_capture_table.update_item(
                Key={'email': email},
                UpdateExpression='SET bounceStatus = :status, statusGsi = :gsi',
                ExpressionAttributeValues={
                    ':status': 'hard',
                    ':gsi': 'bounced',
                },
            )
        else:
            # Soft bounce — check if already soft (escalate to hard)
            resp = email_capture_table.get_item(Key={'email': email})
            item = resp.get('Item')
            if not item:
                return

            current_status = item.get('bounceStatus')
            if current_status == 'soft':
                # Second soft bounce → escalate to hard
                email_capture_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET bounceStatus = :status, statusGsi = :gsi',
                    ExpressionAttributeValues={
                        ':status': 'hard',
                        ':gsi': 'bounced',
                    },
                )
            else:
                # First soft bounce
                email_capture_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET bounceStatus = :status',
                    ExpressionAttributeValues={':status': 'soft'},
                )
    except Exception as e:
        print(f'[ERROR] Failed to handle bounce for {email}: {e}')


def lambda_handler(event, context):
    """Process SNS messages containing SES event notifications."""
    for record in event.get('Records', []):
        try:
            sns_message = json.loads(record.get('Sns', {}).get('Message', '{}'))
            event_type = sns_message.get('eventType', '').lower()

            email = _extract_email_from_event(sns_message)
            template_name = _extract_template_name(sns_message)
            stage = _extract_stage(template_name)

            if not email:
                print(f'[WARN] No email found in SES event: {event_type}')
                continue

            if event_type == 'open':
                _handle_open(email, stage)
            elif event_type == 'click':
                _handle_click(email, stage)
            elif event_type == 'bounce':
                bounce_type = sns_message.get('bounce', {}).get('bounceType', 'Transient')
                _handle_bounce(email, bounce_type)
            elif event_type == 'complaint':
                # Treat complaints like hard bounces
                _handle_bounce(email, 'Permanent')
            else:
                print(f'[WARN] Unknown SES event type: {event_type}')

        except Exception as e:
            print(f'[ERROR] Failed to process SNS record: {e}')
            continue  # Don't fail the entire batch

    # Always return 200 to SNS to prevent retries
    return {'statusCode': 200}
