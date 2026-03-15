#!/usr/bin/env python3
"""
Fix current user's database state
- Sync userStatusDB to level 2
- Remove completed schooling-00004 from progress
"""

import boto3
import json

dynamodb = boto3.resource('dynamodb')
user_id = '34c884b8-7041-7009-dd6d-0a1f6b652e1c'

print("=" * 60)
print("PHASE 1: Database Fix for Current User")
print("=" * 60)

# Step 1: Fix userStatusDB
print("\n[1] Fixing userStatusDB...")
status_table = dynamodb.Table('userStatusDB')

# Read current state
current_status = status_table.get_item(Key={'userId': user_id})
if 'Item' in current_status:
    print(f"   Current level: {current_status['Item'].get('currLevel')}")
else:
    print("   No existing status record")

# Update to level 2
status_table.put_item(Item={'userId': user_id, 'currLevel': 2})
print("   ✓ Updated to level 2")

# Step 2: Fix userQuestionLevelProgressDB
print("\n[2] Fixing userQuestionLevelProgressDB for schooling...")
progress_table = dynamodb.Table('userQuestionLevelProgressDB')

response = progress_table.get_item(Key={'userId': user_id, 'questionType': 'schooling'})
if 'Item' not in response:
    print("   ERROR: No progress record found for schooling")
    exit(1)

item = response['Item']
print(f"   Current remaining: {item.get('remainQuestAtCurrLevel', [])}")
print(f"   Current completed: {item.get('numQuestComplete', 0)}")

# Remove schooling-00004
remain_ids = [q for q in item.get('remainQuestAtCurrLevel', []) if q != 'schooling-00004']
remain_texts = item.get('remainQuestTextAtCurrLevel', [])

# Ensure array lengths match
if len(remain_texts) > len(remain_ids):
    remain_texts = remain_texts[:len(remain_ids)]

item['remainQuestAtCurrLevel'] = remain_ids
item['remainQuestTextAtCurrLevel'] = remain_texts
item['numQuestComplete'] = int(item.get('numQuestComplete', 0)) + 1

progress_table.put_item(Item=item)
print(f"   ✓ Removed schooling-00004")
print(f"   ✓ New remaining count: {len(remain_ids)}")
print(f"   ✓ New completed count: {item['numQuestComplete']}")

# Step 3: Verify all progress items
print("\n[3] Verifying all Level 2 progress...")
response = progress_table.query(
    KeyConditionExpression='userId = :uid',
    ExpressionAttributeValues={':uid': user_id}
)

all_complete = True
for item in response['Items']:
    remaining = len(item.get('remainQuestAtCurrLevel', []))
    print(f"   {item['questionType']}: {remaining} remaining")
    if remaining > 0:
        all_complete = False

print("\n" + "=" * 60)
if all_complete:
    print("✓ ALL LEVEL 2 QUESTIONS COMPLETE!")
    print("  Refresh dashboard to advance to Level 3")
else:
    print("⚠ Some questions still remaining at Level 2")
print("=" * 60)
