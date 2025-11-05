#!/usr/bin/env python3
"""
Timeslot Conflict Validator
---------------------------
Validates that no timeslots have more events than the configured parallel_event limit.

Usage:
    python validate_timeslots.py [timeslot_csv_file] [parallel_event_limit]
    
Example:
    python validate_timeslots.py data/output/final_timeslot_nov.csv 1
"""

import sys
import pandas as pd
from pathlib import Path


def validate_timeslots(csv_path: str, max_parallel: int = 1) -> bool:
    """
    Validate that no timeslot exceeds the parallel event limit.
    
    Args:
        csv_path: Path to the timeslot CSV file
        max_parallel: Maximum number of parallel events allowed
    
    Returns:
        True if valid (no conflicts), False if conflicts found
    """
    if not Path(csv_path).exists():
        print(f"❌ Error: File not found: {csv_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"TIMESLOT CONFLICT VALIDATION")
    print(f"{'='*60}\n")
    print(f"File: {csv_path}")
    print(f"Maximum parallel events: {max_parallel}\n")
    
    # Read the timeslot dataframe
    df = pd.read_csv(csv_path)
    
    # Get slot columns
    slot_columns = [col for col in df.columns if col.startswith('slot_')]
    
    if not slot_columns:
        print("❌ Error: No slot columns found in CSV")
        return False
    
    print(f"Analyzing {len(df)} timeslots with {len(slot_columns)} parallel slots each...\n")
    
    conflicts = []
    total_events = 0
    
    for idx, row in df.iterrows():
        # Count occupied slots
        occupied_count = 0
        occupants = []
        
        for slot_col in slot_columns:
            value = row[slot_col]
            if pd.notna(value) and str(value).lower() != 'none':
                occupied_count += 1
                occupants.append(str(value))
        
        total_events += occupied_count
        
        # Check if exceeded limit
        if occupied_count > max_parallel:
            conflict = {
                'date': row.get('date', 'Unknown'),
                'time': row.get('time', 'Unknown'),
                'occupied': occupied_count,
                'limit': max_parallel,
                'excess': occupied_count - max_parallel,
                'events': occupants
            }
            conflicts.append(conflict)
    
    # Report results
    print(f"Total events scheduled: {total_events}")
    print(f"Total timeslots used: {sum(1 for _, row in df.iterrows() if any(pd.notna(row[col]) and str(row[col]).lower() != 'none' for col in slot_columns))}")
    print(f"\n{'='*60}")
    
    if conflicts:
        print(f"❌ CONFLICTS FOUND: {len(conflicts)} timeslot(s) exceed limit\n")
        
        for i, conflict in enumerate(conflicts, 1):
            print(f"{i}. {conflict['date']} {conflict['time']}")
            print(f"   Occupied: {conflict['occupied']} | Limit: {conflict['limit']} | Excess: {conflict['excess']}")
            print(f"   Events: {', '.join(conflict['events'])}")
            print()
        
        print(f"{'='*60}")
        print(f"❌ VALIDATION FAILED: {len(conflicts)} conflict(s) detected")
        print(f"{'='*60}\n")
        return False
    else:
        print(f"✅ VALIDATION PASSED: No conflicts detected")
        print(f"{'='*60}\n")
        return True


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nNo file specified. Using default...")
        csv_path = "data/output/final_timeslot_nov.csv"
        max_parallel = 1
    else:
        csv_path = sys.argv[1]
        max_parallel = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    # Run validation
    is_valid = validate_timeslots(csv_path, max_parallel)
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
