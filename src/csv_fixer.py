"""
CSV Fixer Module
-----------------
Fixes CSV files with embedded newlines and commas in cells that break proper CSV parsing.

The issue: When a cell contains a comma or newline, Excel wraps it in quotes. However,
text editors and simple parsers may interpret the newline as a row break, causing visual
and parsing issues.

This module properly parses such CSV files and reconstructs them with proper escaping.
"""

import csv
import io
from pathlib import Path


def fix_csv_breaks(input_path: str, output_path: str | None = None) -> str:
    """
    Fix CSV file with embedded newlines and commas in quoted cells.
    
    Args:
        input_path: Path to the broken CSV file
        output_path: Path to save the fixed CSV (if None, overwrites input)
    
    Returns:
        Path to the fixed CSV file
    """
    if output_path is None:
        output_path = input_path
    
    input_file = Path(input_path)
    
    # Read the file with proper CSV parsing
    # This handles quoted fields with newlines correctly
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        # Try to detect dialect
        sample = f.read(8192)
        f.seek(0)
        
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            # Fall back to excel dialect
            dialect = csv.excel
        
        reader = csv.reader(f, dialect=dialect)
        rows = list(reader)
    
    # Write back with standard formatting
    # This ensures all special characters are properly escaped
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)
    
    print(f"✓ Fixed CSV: {input_path}")
    print(f"  - Original rows (visual): unknown due to breaks")
    print(f"  - Actual data rows: {len(rows)}")
    print(f"  - Output: {output_path}")
    
    return output_path


def normalize_csv_for_scheduler(csv_path: str, csv_type: str = 'request') -> str:
    """
    Normalize CSV file to match the expected format for the scheduler.
    
    For request files:
    - Maps new Google Form columns to old scheduler columns
    - Extracts only necessary fields
    
    For availability files:
    - No changes needed, just fixes breaks
    
    Args:
        csv_path: Path to the CSV file
        csv_type: Type of CSV ('request' or 'availability')
    
    Returns:
        Path to the normalized CSV file
    """
    # First fix any CSV breaks
    fix_csv_breaks(csv_path)
    
    if csv_type != 'request':
        return csv_path
    
    # Read the fixed CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check if this is the new format (has 'Timestamp' column)
    if not rows or 'Timestamp' not in rows[0]:
        print(f"  - Already in old format, no normalization needed")
        return csv_path
    
    print(f"  - Detected new Google Form format, normalizing...")
    
    # Map new format to old format
    # Use a dict to track duplicates - key is nim, value is the row data
    nim_to_row = {}
    duplicate_count = 0
    
    for row in rows:
        # Skip header-like rows
        if row.get('Nim', '').lower() in ['nim', '']:
            continue
        
        nim = row.get('Nim', '').strip()
        
        # Skip rows without nim
        if not nim:
            continue
        
        # Extract supervisor 2 from the cell (it might have newlines)
        spv_2 = row.get('Pembimbing 2 (jika ada)', '').strip()
        
        normalized = {
            'nama': row.get('Nama', '').strip(),
            'nim': nim,
            'judul': row.get('Judul', '').replace('\n', ' ').replace('\r', ' ').strip(),
            'capstone_code': row.get('Masukkan Kode Capstone', '').strip(),
            'type': row.get('Jenis Pendaftaran', '').strip(),
            'field_1': row.get('Kata Kunci Keilmuan - Opsi 1', '').strip(),
            'field_2': row.get('Kata Kunci Keilmuan - Opsi 2', '').strip(),
            'spv_1': row.get('Pembimbing 1', '').strip(),
            'spv_2': spv_2,
            'date_time': '',  # Empty for unscheduled
            'examiner_1': row.get('Penguji 1 Ketika Seminar Proposal', '').strip(),
            'examiner_2': row.get('Penguji 2 Ketika Seminar Proposal', '').strip(),
            'status': ''
        }
        
        # Only add if has required fields
        if normalized['nim'] and normalized['nama']:
            # Check for duplicates - keep the later entry (overwrites earlier one)
            if nim in nim_to_row:
                duplicate_count += 1
                print(f"  - Duplicate NIM detected: {nim} (keeping latest entry)")
            nim_to_row[nim] = normalized
    
    # Convert dict back to list (this preserves only the latest entry for each NIM)
    normalized_rows = list(nim_to_row.values())
    
    # Write normalized CSV
    output_path = csv_path.replace('.csv', '_normalized.csv')
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['nama', 'nim', 'judul', 'capstone_code', 'type', 
                      'field_1', 'field_2', 'spv_1', 'spv_2', 'date_time', 
                      'examiner_1', 'examiner_2', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)
    
    if duplicate_count > 0:
        print(f"  - Removed {duplicate_count} duplicate(s) (kept latest entries)")
    print(f"  - Normalized {len(normalized_rows)} unique data rows")
    print(f"  - Output: {output_path}")
    
    return output_path


def preprocess_scheduler_inputs(req_path: str, avail_path: str):
    """
    Preprocess both request and availability CSV files for the scheduler.
    
    Args:
        req_path: Path to request CSV
        avail_path: Path to availability CSV
    
    Returns:
        Tuple of (normalized_req_path, fixed_avail_path)
    """
    print("\n" + "="*60)
    print("CSV PREPROCESSING FOR SCHEDULER")
    print("="*60 + "\n")
    
    print("1. Processing request file...")
    normalized_req = normalize_csv_for_scheduler(req_path, 'request')
    
    print("\n2. Processing availability file...")
    fixed_avail = fix_csv_breaks(avail_path)
    
    print("\n" + "="*60)
    print("PREPROCESSING COMPLETE")
    print("="*60)
    print(f"\nUse these files for scheduling:")
    print(f"  - Request: {normalized_req}")
    print(f"  - Availability: {fixed_avail}")
    print()
    
    return normalized_req, fixed_avail


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python csv_fixer.py <csv_file>                    # Fix a single CSV")
        print("  python csv_fixer.py <req_csv> <avail_csv>        # Preprocess both files")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        # Single file mode
        fix_csv_breaks(sys.argv[1])
    else:
        # Dual file mode (for scheduler)
        preprocess_scheduler_inputs(sys.argv[1], sys.argv[2])
