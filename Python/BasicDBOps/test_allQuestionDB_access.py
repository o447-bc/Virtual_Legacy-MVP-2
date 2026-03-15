#!/usr/bin/env python3
"""
Test script for allQuestionDB access functions
"""

import sys
import json
from basicDBOpsFuncs import getUniqueQuestionTypes

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing allQuestionDB Access Functions")
    print("=" * 60)
    
    try:
        print("\n1. Testing getUniqueQuestionTypes()...")
        print("-" * 40)
        
        # Call the function
        result = getUniqueQuestionTypes()
        
        # Display results
        question_types = result['questionTypes']
        friendly_names = result['friendlyNames']
        
        print(f"\nFound {len(question_types)} unique question types:")
        print("-" * 40)
        
        for i, q_type in enumerate(question_types, 1):
            friendly_name = friendly_names.get(q_type, "Unknown")
            print(f"{i:2d}. {q_type}")
            print(f"    Friendly Name: {friendly_name}")
        
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"Total Question Types: {len(question_types)}")
        print(f"Question Types: {question_types}")
        print("=" * 60)
        
        # Optional: Save results to JSON file for further analysis
        output_data = {
            'timestamp': str(datetime.now()),
            'total_count': len(question_types),
            'question_types': question_types,
            'friendly_names': friendly_names
        }
        
        with open('question_types_results.json', 'w') as f:
            json.dump(output_data, f, indent=2)
        print("Results saved to 'question_types_results.json'")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    main()