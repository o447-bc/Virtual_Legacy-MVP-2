"""
Excel to JSON Converter for Virtual Legacy Questions

This script converts Virtual Legacy questions from Excel format to JSON files.
Each Excel tab represents a question category (e.g., childhood, schooling, values)
and gets converted to a separate JSON file for use in the application.

Purpose:
- Convert structured question data from Excel to JSON format
- Generate unique composite question IDs for database storage
- Validate data integrity during conversion
- Create separate JSON files per question category

Key Features:
- Auto-generates missing question IDs
- Creates composite IDs (category-number format)
- Validates for duplicate IDs
- Handles empty cells gracefully
"""

import pandas as pd
import os

# Configuration: File paths for input Excel and output JSON files
path = '/Users/Oliver/Library/Mobile Documents/com~apple~CloudDocs/Documents - Mac/AI/Virtual-Legacy/Virtual-Legacy-MVP-1/Questions/'
excel_file = path + '2025-06-22 Questions for Virtual Legacy.xlsx'
output_dir = path

# Step 1: Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Step 2: Load Excel file with all sheets
excel_data = pd.ExcelFile(excel_file)

# Step 3: Process each Excel tab (question category) separately
for sheet_name in excel_data.sheet_names:
    # Load data from current sheet
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    
    # Step 4: Validate required columns exist
    if 'questionId' not in df.columns:
        raise ValueError(f"No 'questionId' column in sheet '{sheet_name}'")
    
    # Step 5: Auto-generate missing question IDs
    # Only fills null values, preserves existing IDs
    if df['questionId'].isnull().any():
        null_mask = df['questionId'].isnull()
        # Find highest existing ID to continue sequence
        max_id = df['questionId'].dropna().max() if not df['questionId'].dropna().empty else 0
        # Generate sequential IDs for missing values
        df.loc[null_mask, 'questionId'] = range(int(max_id) + 1, int(max_id) + 1 + null_mask.sum())
    
    # Step 6: Validate no duplicate IDs exist
    if df['questionId'].duplicated().any():
        raise ValueError(f"Duplicate IDs in sheet '{sheet_name}'")
    
    # Step 7: Create composite questionID format: category-number
    # This ensures unique IDs across all question categories
    df['questionId'] = df['questionId'].apply(lambda x: f"{sheet_name}-{int(x)}")
    
    # Step 8: Add question category metadata
    df['questionType'] = sheet_name
    
    # Step 9: Clean data - replace empty cells with empty strings
    df = df.fillna('')
    
    # Step 10: Export to JSON file
    json_path = f'{output_dir}/{sheet_name}.json'
    df.to_json(json_path, orient='records', lines=False, indent=4, force_ascii=False)
    
    print(f"Converted sheet '{sheet_name}' to {json_path}")