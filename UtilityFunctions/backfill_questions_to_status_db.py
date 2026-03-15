#!/usr/bin/env python3
"""
Backfill Question Text to userQuestionStatusDB

This script adds the 'Question' field to existing entries in userQuestionStatusDB
by looking up the question text from allQuestionDB.

Usage:
    # Dry run (no changes):
    python3 backfill_questions_to_status_db.py --dry-run
    
    # Actual update:
    python3 backfill_questions_to_status_db.py
"""

import boto3
import time
import argparse
from datetime import datetime
from botocore.exceptions import ClientError

# Configuration
REGION = 'us-east-1'
STATUS_TABLE = 'userQuestionStatusDB'
QUESTION_TABLE = 'allQuestionDB'

def get_question_text(dynamodb, question_id, question_type):
    """
    Fetch question text from allQuestionDB using composite key.
    
    Args:
        dynamodb: DynamoDB resource
        question_id: Question ID (partition key)
        question_type: Question type (sort key)
        
    Returns:
        str: Question text, or empty string if not found
    """
    try:
        table = dynamodb.Table(QUESTION_TABLE)
        response = table.get_item(
            Key={
                'questionId': question_id,
                'questionType': question_type
            }
        )
        
        if 'Item' in response and 'Question' in response['Item']:
            return response['Item']['Question']
        else:
            print(f"  WARNING: Question not found for {question_id} / {question_type}")
            return ''
            
    except ClientError as e:
        print(f"  ERROR fetching question: {e.response['Error']['Message']}")
        return ''
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return ''

def update_status_item(dynamodb, user_id, question_id, question_text, dry_run=False):
    """
    Update userQuestionStatusDB item with Question field.
    
    Args:
        dynamodb: DynamoDB resource
        user_id: User ID (partition key)
        question_id: Question ID (sort key)
        question_text: Question text to add
        dry_run: If True, don't actually update
        
    Returns:
        bool: True if successful, False otherwise
    """
    if dry_run:
        print(f"  [DRY RUN] Would update with: {question_text[:50]}...")
        return True
        
    try:
        table = dynamodb.Table(STATUS_TABLE)
        table.update_item(
            Key={
                'userId': user_id,
                'questionId': question_id
            },
            UpdateExpression='SET Question = :q',
            ExpressionAttributeValues={
                ':q': question_text
            }
        )
        return True
        
    except ClientError as e:
        print(f"  ERROR updating item: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def scan_status_table(dynamodb):
    """
    Scan userQuestionStatusDB and return all items with pagination.
    
    Args:
        dynamodb: DynamoDB resource
        
    Returns:
        list: All items from the table
    """
    table = dynamodb.Table(STATUS_TABLE)
    items = []
    
    print(f"Scanning {STATUS_TABLE}...")
    
    response = table.scan()
    items.extend(response.get('Items', []))
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        print(f"  Fetched {len(items)} items so far...")
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    print(f"Total items found: {len(items)}")
    return items

def main():
    """Main execution function"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Backfill Question field to userQuestionStatusDB')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    args = parser.parse_args()
    
    print("=" * 80)
    print("Backfill Question Text to userQuestionStatusDB")
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    else:
        print("MODE: LIVE UPDATE")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    
    # Scan all items from userQuestionStatusDB
    items = scan_status_table(dynamodb)
    
    if not items:
        print("No items found in table")
        return
    
    print()
    print("Processing items...")
    print("-" * 80)
    
    # Statistics
    total_items = len(items)
    items_updated = 0
    items_skipped = 0
    items_failed = 0
    
    # Process each item
    for index, item in enumerate(items):
        user_id = item.get('userId', 'UNKNOWN')
        question_id = item.get('questionId', 'UNKNOWN')
        question_type = item.get('questionType', 'UNKNOWN')
        
        print(f"[{index + 1}/{total_items}] Processing: {user_id} / {question_id}")
        
        # Check if Question field already exists
        if 'Question' in item and item['Question']:
            print(f"  SKIP: Question field already exists")
            items_skipped += 1
            continue
        
        # Fetch question text from allQuestionDB
        print(f"  Fetching question text for {question_type}...")
        question_text = get_question_text(dynamodb, question_id, question_type)
        
        if not question_text:
            print(f"  WARNING: No question text found, using empty string")
            items_failed += 1
            # Continue anyway to mark as processed
        
        # Update the item
        success = update_status_item(dynamodb, user_id, question_id, question_text, args.dry_run)
        
        if success:
            if not args.dry_run:
                print(f"  ✓ Updated successfully")
            items_updated += 1
        else:
            print(f"  ✗ Update failed")
            items_failed += 1
        
        # Rate limiting: 1 update per second to avoid throttling
        if index < total_items - 1 and not args.dry_run:
            time.sleep(1)
    
    # Summary
    print()
    print("=" * 80)
    print("Backfill Summary")
    print("=" * 80)
    print(f"Total items:        {total_items}")
    print(f"Updated:            {items_updated}")
    print(f"Skipped (existing): {items_skipped}")
    print(f"Failed/Warning:     {items_failed}")
    print(f"Completed at:       {datetime.now().isoformat()}")
    print("=" * 80)
    
    if args.dry_run:
        print()
        print("This was a DRY RUN. No changes were made.")
        print("Run without --dry-run flag to perform actual updates.")

if __name__ == '__main__':
    main()
