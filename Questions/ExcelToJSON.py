"""
Excel to JSON Converter for Virtual Legacy Questions - SAFE ID VERSION

Converts questions from Excel (one sheet = one theme) to clean per-theme JSON files.
Prioritizes immutability of question IDs.

Critical rules:
- Never changes an existing questionId value
- Only auto-assigns when questionId is blank/empty
- Composite format: {sheet_name}-{number}
- Only includes Valid=1 questions in output
"""

import pandas as pd
import os
import json
from datetime import datetime

# ====================== CONFIG ======================
EXCEL_FILE = '2026-02-14 Questions for Virtual Legacy.xlsx'   # ← update if renamed
OUTPUT_DIR = 'questions_json'                                 # output folder
# ===================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        excel_data = pd.ExcelFile(EXCEL_FILE)
    except FileNotFoundError:
        print(f"Error: Excel file not found: {EXCEL_FILE}")
        return

    for sheet_name in excel_data.sheet_names:
        print(f"\nProcessing sheet: {sheet_name}")
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        df = df.fillna('')  # Replace NaN with empty string
        
        # Ensure questionId is string
        df['questionId'] = df['questionId'].astype(str).str.strip()
        
        # ────────────────────────────────────────────────
        # 1. Auto-assign ONLY to completely blank questionId cells
        # ────────────────────────────────────────────────
        mask_blank = df['questionId'].isin(['', 'nan', None, '<NA>'])
        
        if mask_blank.any():
            # Find highest existing number in this sheet (from composite IDs)
            existing_nums = []
            for val in df['questionId']:
                if '-' in val:
                    try:
                        num_part = val.split('-', 1)[1].strip()
                        if num_part.isdigit():
                            existing_nums.append(int(num_part))
                    except:
                        pass
            
            start_num = max(existing_nums) + 1 if existing_nums else 1
            new_ids = [f"{sheet_name}-{n:04d}" for n in range(start_num, start_num + mask_blank.sum())]
            
            df.loc[mask_blank, 'questionId'] = new_ids
            print(f"  Assigned {mask_blank.sum()} new IDs starting from {start_num}")

        # ────────────────────────────────────────────────
        # 2. One-time upgrade: convert legacy plain numbers to composite
        #    → comment out or remove this block after first successful run
        # ────────────────────────────────────────────────
        legacy_mask = df['questionId'].str.match(r'^\d+$') & (df['questionId'] != '')
        if legacy_mask.any():
            df.loc[legacy_mask, 'questionId'] = df.loc[legacy_mask, 'questionId'].apply(
                lambda x: f"{sheet_name}-{int(float(x)):04d}"
            )
            print(f"  Upgraded {legacy_mask.sum()} legacy numeric IDs to composite format")

        # ────────────────────────────────────────────────
        # 3. Final safety checks
        # ────────────────────────────────────────────────
        active_df = df[df['Valid'] == 1]
        
        if (active_df['questionId'] == '').any():
            raise ValueError(f"Active question (Valid=1) has empty questionId in sheet '{sheet_name}'")
        
        if active_df['questionId'].duplicated().any():
            duplicates = active_df[active_df['questionId'].duplicated(keep=False)]
            print("Duplicate IDs found:")
            print(duplicates[['questionId', 'Question']])
            raise ValueError(f"Duplicate questionIds detected in sheet '{sheet_name}'")

        # ────────────────────────────────────────────────
        # 4. Build clean JSON structure
        # ────────────────────────────────────────────────
        if len(df) < 1:
            print(f"  Skipping empty sheet")
            continue

        theme_name = str(df.iloc[0]['Question']).strip() if not df.empty else sheet_name
        
        questions = []
        for _, row in df.iloc[1:].iterrows():  # skip metadata row
            if int(row['Valid']) != 1:
                continue
                
            diff = row['Difficulty']
            # Handle 'x' or invalid difficulty gracefully
            try:
                diff_value = int(diff) if str(diff).strip().isdigit() else 2
            except:
                diff_value = 2
                
            questions.append({
                "questionId": row['questionId'],
                "difficulty": diff_value,
                "text": str(row['Question']).strip(),
                "active": True
            })

        output = {
            "themeId": sheet_name.lower().replace(' ', ''),
            "themeName": theme_name,
            "questions": questions
        }

        # Write JSON
        json_filename = f"{sheet_name.lower()}.json"
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"  → {json_path}  ({len(questions)} active questions)")

    print("\nConversion complete.")

if __name__ == "__main__":
    main()