"""
One-time migration: update the description field of the CONVERSATION_SYSTEM_PROMPT
record in SystemSettingsDB to document the available placeholders.

Run once after deploying the theme-aware-ai-prompts feature:

    python migrate_prompt_description.py

Or with a custom table name:

    TABLE_SYSTEM_SETTINGS=MyTable python migrate_prompt_description.py

Alternatively, run via AWS CLI:

    aws dynamodb update-item \
        --table-name SystemSettingsDB \
        --key '{"settingKey": {"S": "CONVERSATION_SYSTEM_PROMPT"}}' \
        --update-expression "SET description = :d" \
        --expression-attribute-values '{":d": {"S": "System prompt used to guide the AI during conversations. Available placeholders: {question} (replaced with the current question text), {theme_name} (replaced with the current theme name), {theme_description} (replaced with the per-theme prompt description)."}}' \
        --region us-east-1
"""
import os
import boto3


def migrate():
    table_name = os.environ.get('TABLE_SYSTEM_SETTINGS', 'SystemSettingsDB')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    new_description = (
        'System prompt used to guide the AI during conversations. '
        'Available placeholders: {question} (replaced with the current question text), '
        '{theme_name} (replaced with the current theme name), '
        '{theme_description} (replaced with the per-theme prompt description).'
    )

    table.update_item(
        Key={'settingKey': 'CONVERSATION_SYSTEM_PROMPT'},
        UpdateExpression='SET description = :d',
        ExpressionAttributeValues={':d': new_description},
    )
    print(f"Updated CONVERSATION_SYSTEM_PROMPT description in {table_name}")


if __name__ == '__main__':
    migrate()
