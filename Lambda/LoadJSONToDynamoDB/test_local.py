#!/usr/bin/env python3

# Test the questionId formatting logic locally
def test_question_id_formatting():
    test_cases = [
        {'questionId': 3, 'questionType': 'multiple-choice'},
        {'questionId': '3', 'questionType': 'multiple-choice'},
        {'questionId': 123, 'questionType': 'true-false'},
        {'questionId': 'custom-id', 'questionType': 'essay'}
    ]
    
    for item in test_cases:
        # Apply the same logic as in lambda_function.py line 27
        question_id = str(item['questionId']).zfill(5) if str(item['questionId']).isdigit() else str(item['questionId'])
        print(f"Original: {item['questionId']} -> Formatted: {question_id}")

if __name__ == "__main__":
    test_question_id_formatting()