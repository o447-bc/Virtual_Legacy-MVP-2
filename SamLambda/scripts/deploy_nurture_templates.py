#!/usr/bin/env python3
"""
Deploy SES email templates for the SoulReel nurture sequence.

Creates or updates all 12 SES templates (stages 0-5, variants A and B).
Run manually after deployment — not part of CloudFormation.

Usage:
    python deploy_nurture_templates.py [--region us-east-1]
"""

import argparse
import boto3
from botocore.exceptions import ClientError

# Brand colors
PURPLE = '#7C3AED'
NAVY = '#1E1B4B'
WHITE = '#FFFFFF'
LIGHT_BG = '#F5F3FF'
GRAY_TEXT = '#6B7280'

SIGNUP_URL = 'https://www.soulreel.net/?signup=create-legacy'
SENDER = 'SoulReel <noreply@soulreel.net>'


def _base_html(preheader, body_content):
    """Wrap body content in a mobile-responsive email shell with SoulReel branding."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SoulReel</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:{LIGHT_BG};font-family:Arial,Helvetica,sans-serif;">
<span style="display:none;font-size:1px;color:{LIGHT_BG};max-height:0;overflow:hidden;">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{LIGHT_BG};">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:{WHITE};border-radius:8px;overflow:hidden;">
<!-- Header -->
<tr><td style="background-color:{NAVY};padding:32px 24px;text-align:center;">
<h1 style="margin:0;color:{WHITE};font-size:28px;font-weight:700;">SoulReel</h1>
</td></tr>
<!-- Body -->
<tr><td style="padding:32px 24px;color:#1F2937;font-size:16px;line-height:1.6;">
{body_content}
</td></tr>
<!-- Footer -->
<tr><td style="padding:24px;border-top:1px solid #E5E7EB;text-align:center;font-size:13px;color:{GRAY_TEXT};line-height:1.5;">
<p style="margin:0 0 8px;">Know someone who should preserve their story?<br>
<a href="{{{{referral_url}}}}" style="color:{PURPLE};text-decoration:underline;">Share SoulReel with them</a></p>
<p style="margin:0;"><a href="{{{{unsubscribe_url}}}}" style="color:{GRAY_TEXT};text-decoration:underline;">Unsubscribe</a></p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _cta_button(text, url='{{{{signup_url}}}}'):
    """Render a CTA button with 44x44px minimum touch target."""
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto;">
<tr><td align="center" style="background-color:{PURPLE};border-radius:6px;">
<a href="{url}" target="_blank" style="display:inline-block;min-width:44px;min-height:44px;padding:14px 32px;color:{WHITE};font-size:16px;font-weight:600;text-decoration:none;line-height:1.2;">
{text}</a>
</td></tr>
</table>"""


def _question_block(question):
    """Render a highlighted question block."""
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
<tr><td style="background-color:{LIGHT_BG};border-left:4px solid {PURPLE};padding:16px 20px;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:18px;font-style:italic;color:{NAVY};font-weight:600;">
&ldquo;{question}&rdquo;</p>
</td></tr>
</table>"""


# ---------------------------------------------------------------------------
# Template content definitions — stages 0-5
# ---------------------------------------------------------------------------

TEMPLATES = {
    0: {
        'subject': 'Your first SoulReel question is here',
        'preheader': 'A question worth thinking about today.',
        'body': lambda: (
            '<p style="margin:0 0 16px;">Welcome to SoulReel!</p>'
            '<p style="margin:0 0 16px;">We believe every life holds stories worth preserving. '
            'To get you started, here is your first question:</p>'
            + _question_block("What's the bravest thing you've ever done?")
            + '<p style="margin:0 0 16px;">When you are ready to record your answer — and unlock '
            'dozens more questions designed to capture the moments that matter — '
            'create your free account.</p>'
            + _cta_button('Start Preserving Your Story')
        ),
        'text': (
            "Welcome to SoulReel!\n\n"
            "We believe every life holds stories worth preserving. "
            "To get you started, here is your first question:\n\n"
            "\"What's the bravest thing you've ever done?\"\n\n"
            "When you are ready to record your answer, create your free account:\n"
            "{{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
    1: {
        'subject': 'Why I built SoulReel \u2014 and a question for you',
        'preheader': 'A personal note from our founder.',
        'body': lambda: (
            '<p style="margin:0 0 16px;">Hi there,</p>'
            '<p style="margin:0 0 16px;">I built SoulReel because I realized the stories '
            'my grandparents never recorded are gone forever. I don\u2019t want that to happen '
            'to anyone else\u2019s family.</p>'
            '<p style="margin:0 0 16px;">That\u2019s why we created a simple way to answer '
            'meaningful questions on video — so the people you love can hear your voice '
            'and see your face for generations to come.</p>'
            '<p style="margin:0 0 16px;">Here\u2019s a question to think about today:</p>'
            + _question_block("What was it really like growing up in your family?")
            + '<p style="margin:0 0 16px;">Your story matters. Let\u2019s make sure it\u2019s heard.</p>'
            + _cta_button('Start Recording Your Story')
        ),
        'text': (
            "Hi there,\n\n"
            "I built SoulReel because I realized the stories my grandparents never recorded "
            "are gone forever. I don\u2019t want that to happen to anyone else\u2019s family.\n\n"
            "That\u2019s why we created a simple way to answer meaningful questions on video "
            "\u2014 so the people you love can hear your voice and see your face for generations "
            "to come.\n\n"
            "Here\u2019s a question to think about today:\n\n"
            "\"What was it really like growing up in your family?\"\n\n"
            "Your story matters. Let\u2019s make sure it\u2019s heard.\n"
            "{{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
    2: {
        'subject': 'A question your grandchildren will thank you for',
        'preheader': 'Families are using SoulReel to preserve what matters most.',
        'body': lambda: (
            '<p style="margin:0 0 16px;">Families across the country are using SoulReel '
            'to preserve the stories that matter most — the ones that get told at dinner tables, '
            'the ones that make everyone laugh, and the ones that deserve to live on.</p>'
            '<p style="margin:0 0 16px;">Here\u2019s a question they\u2019re answering:</p>'
            + _question_block("Tell me about the day you became a parent.")
            + '<p style="margin:0 0 16px;">Your family\u2019s story is one of a kind. '
            'Don\u2019t let it go untold.</p>'
            + _cta_button('Preserve Your Story')
        ),
        'text': (
            "Families across the country are using SoulReel to preserve the stories that "
            "matter most \u2014 the ones that get told at dinner tables, the ones that make "
            "everyone laugh, and the ones that deserve to live on.\n\n"
            "Here\u2019s a question they\u2019re answering:\n\n"
            "\"Tell me about the day you became a parent.\"\n\n"
            "Your family\u2019s story is one of a kind. Don\u2019t let it go untold.\n"
            "{{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
    3: {
        'subject': 'Every day holds stories worth preserving',
        'preheader': "Stories don\u2019t wait \u2014 and neither should you.",
        'body': lambda: (
            '<p style="margin:0 0 16px;">Stories don\u2019t wait. Every day, memories fade '
            'a little more. The details get fuzzy. The voices get quieter.</p>'
            '<p style="margin:0 0 16px;">But it doesn\u2019t have to be that way. '
            'SoulReel makes it easy to capture what matters — one question at a time.</p>'
            '<p style="margin:0 0 16px;">Here\u2019s one worth thinking about:</p>'
            + _question_block("What value do you most want to pass on to the next generation?")
            + '<p style="margin:0 0 16px;">Take five minutes today. Your future family '
            'will be grateful you did.</p>'
            + _cta_button('Start Today')
        ),
        'text': (
            "Stories don\u2019t wait. Every day, memories fade a little more. "
            "The details get fuzzy. The voices get quieter.\n\n"
            "But it doesn\u2019t have to be that way. SoulReel makes it easy to capture "
            "what matters \u2014 one question at a time.\n\n"
            "Here\u2019s one worth thinking about:\n\n"
            "\"What value do you most want to pass on to the next generation?\"\n\n"
            "Take five minutes today. Your future family will be grateful you did.\n"
            "{{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
    4: {
        'subject': 'One last question \u2014 and a gift from us',
        'preheader': 'A special offer and one final question.',
        'body': lambda: (
            '<p style="margin:0 0 16px;">We\u2019ve loved sharing these questions with you. '
            'This is our last one — and it\u2019s a big one:</p>'
            + _question_block("What would you want your family to remember about you?")
            + '<p style="margin:0 0 16px;">If that question stirred something in you, '
            'we\u2019d love to help you answer it.</p>'
            '<p style="margin:0 0 16px;">As a thank-you for being part of this journey, '
            'here\u2019s a gift:</p>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:16px 0;">'
            '<tr><td style="background-color:{light};border:2px dashed {purple};'
            'border-radius:8px;padding:20px;text-align:center;">'.format(
                light=LIGHT_BG, purple=PURPLE)
            + f'<p style="margin:0 0 4px;font-size:14px;color:{GRAY_TEXT};">Your coupon code</p>'
            f'<p style="margin:0;font-size:24px;font-weight:700;color:{PURPLE};'
            f'letter-spacing:2px;">COMEBACK20</p>'
            f'<p style="margin:8px 0 0;font-size:14px;color:{GRAY_TEXT};">'
            '20% off your first 3 months</p>'
            '</td></tr></table>'
            + _cta_button('Claim Your Discount & Start')
        ),
        'text': (
            "We\u2019ve loved sharing these questions with you. "
            "This is our last one \u2014 and it\u2019s a big one:\n\n"
            "\"What would you want your family to remember about you?\"\n\n"
            "If that question stirred something in you, we\u2019d love to help you answer it.\n\n"
            "As a thank-you, here\u2019s a gift:\n"
            "Use coupon code COMEBACK20 for 20% off your first 3 months.\n\n"
            "Claim your discount: {{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
    5: {
        'subject': "Still thinking about preserving your story? Here\u2019s a gift",
        'preheader': "We\u2019re still here — and we have a gift for you.",
        'body': lambda: (
            '<p style="margin:0 0 16px;">It\u2019s been a while, and we\u2019re still here — '
            'ready whenever you are.</p>'
            '<p style="margin:0 0 16px;">We have one more question for you:</p>'
            + _question_block(
                "If you could tell your grandchildren one thing about your life, "
                "what would it be?"
            )
            + '<p style="margin:0 0 16px;">If you\u2019re ready to answer that question '
            '(and many more), we\u2019d love to welcome you back with a special offer:</p>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:16px 0;">'
            '<tr><td style="background-color:{light};border:2px dashed {purple};'
            'border-radius:8px;padding:20px;text-align:center;">'.format(
                light=LIGHT_BG, purple=PURPLE)
            + f'<p style="margin:0;font-size:20px;font-weight:700;color:{PURPLE};">'
            'Your first month is free</p>'
            f'<p style="margin:8px 0 0;font-size:14px;color:{GRAY_TEXT};">'
            'No coupon needed — just sign up</p>'
            '</td></tr></table>'
            + _cta_button('Come Back & Start Free')
        ),
        'text': (
            "It\u2019s been a while, and we\u2019re still here \u2014 "
            "ready whenever you are.\n\n"
            "We have one more question for you:\n\n"
            "\"If you could tell your grandchildren one thing about your life, "
            "what would it be?\"\n\n"
            "If you\u2019re ready to answer that question, we\u2019d love to welcome you back "
            "with a special offer: your first month is free. No coupon needed \u2014 "
            "just sign up.\n\n"
            "{{signup_url}}\n\n"
            "Know someone who should preserve their story? Share SoulReel: {{referral_url}}\n\n"
            "Unsubscribe: {{unsubscribe_url}}"
        ),
    },
}


def build_template(stage, variant):
    """Build an SES template dict for the given stage and variant."""
    t = TEMPLATES[stage]
    name = f'soulreel-nurture-stage-{stage}-{variant}'
    html_body = _base_html(t['preheader'], t['body']())
    return {
        'TemplateName': name,
        'SubjectPart': t['subject'],
        'HtmlPart': html_body,
        'TextPart': t['text'],
    }


def deploy_templates(region='us-east-1'):
    """Create or update all 12 nurture email templates in SES."""
    ses = boto3.client('ses', region_name=region)
    results = {'created': [], 'updated': [], 'failed': []}

    for stage in range(6):
        for variant in ('A', 'B'):
            template = build_template(stage, variant)
            name = template['TemplateName']
            try:
                ses.create_template(Template=template)
                results['created'].append(name)
                print(f'  [CREATED] {name}')
            except ClientError as e:
                if e.response['Error']['Code'] == 'AlreadyExistsException':
                    try:
                        ses.update_template(Template=template)
                        results['updated'].append(name)
                        print(f'  [UPDATED] {name}')
                    except ClientError as ue:
                        results['failed'].append((name, str(ue)))
                        print(f'  [FAILED]  {name}: {ue}')
                else:
                    results['failed'].append((name, str(e)))
                    print(f'  [FAILED]  {name}: {e}')

    print(f'\nDone. Created: {len(results["created"])}, '
          f'Updated: {len(results["updated"])}, '
          f'Failed: {len(results["failed"])}')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deploy SoulReel nurture SES templates')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    args = parser.parse_args()
    print(f'Deploying 12 nurture email templates to SES in {args.region}...\n')
    deploy_templates(region=args.region)
