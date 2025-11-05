#!/usr/bin/env python3
"""
Test CSV Fixer - Duplicate Detection
"""

import sys
sys.path.insert(0, 'src')

from csv_fixer import normalize_csv_for_scheduler

# Test with the November file
print("Testing duplicate detection on req_nov.csv...\n")
result = normalize_csv_for_scheduler('data/input/req_nov.csv', 'request')
print(f"\nOutput file: {result}")
print("\nTest complete!")
