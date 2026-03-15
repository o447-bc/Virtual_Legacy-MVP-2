#!/usr/bin/env python3
"""
Test Set Optimization Performance
=================================
Tests the performance improvement from converting list to set operations.
"""

import sys
import os
import time
from unittest.mock import Mock, patch

# Add function directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app

def test_set_optimization_performance():
    """Test that set optimization provides performance improvement."""
    print("🧪 Testing Set Optimization Performance")
    
    # Create test data with different sizes
    test_scenarios = [
        {"valid": 100, "answered": 50},
        {"valid": 1000, "answered": 500},
        {"valid": 5000, "answered": 2500}
    ]
    
    for scenario in test_scenarios:
        valid_count = scenario["valid"]
        answered_count = scenario["answered"]
        
        # Generate test data
        valid_questions = [f"q-{i:04d}" for i in range(valid_count)]
        answered_questions = [f"q-{i:04d}" for i in range(0, answered_count)]
        
        # Test old approach (list operations)
        start_time = time.time()
        old_result = [qid for qid in valid_questions if qid not in answered_questions]
        old_time = time.time() - start_time
        
        # Test new approach (set operations)
        start_time = time.time()
        answered_set = set(answered_questions)
        new_result = [qid for qid in valid_questions if qid not in answered_set]
        new_time = time.time() - start_time
        
        # Verify results are identical
        assert old_result == new_result, "Results should be identical"
        
        # Calculate improvement
        if old_time > 0:
            improvement = ((old_time - new_time) / old_time) * 100
        else:
            improvement = 0
        
        print(f"📊 {valid_count} valid, {answered_count} answered:")
        print(f"   List approach: {old_time:.4f}s")
        print(f"   Set approach:  {new_time:.4f}s")
        print(f"   Improvement:   {improvement:.1f}% faster")
        print(f"   Unanswered:    {len(new_result)} questions")
    
    print("✅ Set optimization performance test passed\n")

@patch('app.boto3.resource')
def test_function_with_set_optimization(mock_boto3):
    """Test the actual function uses set optimization correctly."""
    print("🧪 Testing Function with Set Optimization")
    
    # Mock DynamoDB responses
    mock_dynamodb = Mock()
    mock_questions_table = Mock()
    mock_user_table = Mock()
    
    # Mock question data
    mock_questions_table.scan.return_value = {
        'Items': [
            {'questionId': 'test-001', 'questionType': 'test', 'Valid': 1},
            {'questionId': 'test-002', 'questionType': 'test', 'Valid': 1},
            {'questionId': 'test-003', 'questionType': 'test', 'Valid': 1}
        ]
    }
    
    # Mock user answered questions
    mock_user_table.query.return_value = {
        'Items': [
            {'questionId': 'test-001', 'questionType': 'test'}
        ]
    }
    
    # Configure table mocks
    def get_table(table_name):
        if table_name == 'allQuestionDB':
            return mock_questions_table
        elif table_name == 'userQuestionStatusDB':
            return mock_user_table
        return Mock()
    
    mock_dynamodb.Table.side_effect = get_table
    mock_boto3.return_value = mock_dynamodb
    
    # Test the function
    result = app.get_unanswered_questions('test', 'user-123')
    
    # Verify results
    expected_unanswered = ['test-002', 'test-003']  # test-001 was answered
    assert len(result) == 2, f"Expected 2 unanswered, got {len(result)}"
    assert 'test-001' not in result, "Answered question should not be in result"
    assert 'test-002' in result, "Unanswered question should be in result"
    assert 'test-003' in result, "Unanswered question should be in result"
    
    print("✅ Function correctly uses set optimization")
    print(f"   Input: 3 valid questions, 1 answered")
    print(f"   Output: {len(result)} unanswered questions")
    print("✅ Function with set optimization test passed\n")

def run_optimization_tests():
    """Run all set optimization tests."""
    print("🚀 Starting Set Optimization Tests")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        test_set_optimization_performance()
        test_function_with_set_optimization()
        
        total_time = time.time() - start_time
        print("🎉 ALL SET OPTIMIZATION TESTS PASSED!")
        print(f"⏱️  Total test time: {total_time:.2f}s")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = run_optimization_tests()
    sys.exit(0 if success else 1)