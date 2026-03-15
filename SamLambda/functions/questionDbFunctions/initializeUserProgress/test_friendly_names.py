#!/usr/bin/env python3
"""
Test script to verify friendly name collection logic
"""

import boto3
import json

def test_friendly_name_collection():
    """Test the friendly name collection logic"""
    
    # Initialize DynamoDB table
    all_questions_table = boto3.resource('dynamodb').Table('allQuestionDB')
    
    # Scan allQuestionDB to collect question types and friendly names
    print("[TEST] Scanning allQuestionDB for question types and friendly names")
    response = all_questions_table.scan()
    print(f"[TEST] Found {len(response['Items'])} total questions")
    
    # Track all unique question types, friendly names, and valid difficulty-1 questions by type
    question_types = set()  # All unique question types found
    friendly_names = {}  # Friendly names for each question type
    difficulty_one_by_type = {}  # Valid difficulty-1 questions grouped by type
    
    # Process each question to extract types, friendly names, and filter valid difficulty-1 questions
    for item in response['Items']:
        q_type = item.get('questionType')
        if q_type:
            # Add to set of all question types
            question_types.add(q_type)
            
            # Check for friendly name (questionId pattern: questionType-00000)
            question_id = item.get('questionId', '')
            if question_id == f"{q_type}-00000" and 'Question' in item:
                friendly_names[q_type] = item['Question']
                print(f"[TEST] Found friendly name for {q_type}: {item['Question']}")
            
            # Only include questions that are both difficulty=1 AND valid=1
            # These will be the initial questions available to users
            if item.get('Difficulty') == 1 and item.get('Valid') == 1:
                if q_type not in difficulty_one_by_type:
                    difficulty_one_by_type[q_type] = []
                difficulty_one_by_type[q_type].append(item['questionId'])
    
    print(f"[TEST] Found question types: {list(question_types)}")
    print(f"[TEST] Friendly names found: {friendly_names}")
    print(f"[TEST] Difficulty=1 questions by type: {difficulty_one_by_type}")
    
    # Test progress record creation
    print("\n[TEST] Testing progress record creation:")
    for q_type in question_types:
        item_data = {
            'userId': 'test-user-id',
            'questionType': q_type,
            'friendlyName': friendly_names.get(q_type, q_type),
            'maxLevelCompleted': 0,
            'currentQuestLevel': 1,
            'remainQuestAtCurrLevel': difficulty_one_by_type.get(q_type, []),
            'numQuestComplete': 0,
            'totalQuestAtCurrLevel': len(difficulty_one_by_type.get(q_type, []))
        }
        print(f"[TEST] Progress record for {q_type}: {json.dumps(item_data, indent=2)}")

if __name__ == "__main__":
    test_friendly_name_collection()