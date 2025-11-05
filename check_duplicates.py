#!/usr/bin/env python3
"""
Test Duplicate Removal in Output
"""

import pandas as pd
import sys

# Read the output CSV
output_file = 'data/output/final_output_nov.csv'

try:
    df = pd.read_csv(output_file)
    
    print(f"\n{'='*60}")
    print("DUPLICATE CHECK FOR OUTPUT FILE")
    print(f"{'='*60}\n")
    print(f"File: {output_file}")
    print(f"Total rows: {len(df)}")
    
    # Check for duplicates
    duplicate_mask = df['nim'].duplicated(keep=False)
    duplicates = df[duplicate_mask]
    
    if len(duplicates) > 0:
        print(f"\n❌ DUPLICATES FOUND: {len(duplicates)} rows with duplicate NIMs\n")
        
        # Group by NIM to show which NIMs are duplicated
        duplicate_nims = duplicates['nim'].unique()
        print(f"Duplicate NIMs: {duplicate_nims.tolist()}\n")
        
        for nim in duplicate_nims:
            nim_rows = df[df['nim'] == nim]
            print(f"NIM: {nim} - Found {len(nim_rows)} times")
            print(nim_rows[['nim', 'nama', 'type', 'status']].to_string(index=False))
            print()
        
        sys.exit(1)
    else:
        unique_count = df['nim'].nunique()
        print(f"\n✅ NO DUPLICATES: All {unique_count} NIMs are unique")
        print(f"{'='*60}\n")
        sys.exit(0)
        
except FileNotFoundError:
    print(f"❌ Error: File not found: {output_file}")
    print("Run the scheduler first: python src/main.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
