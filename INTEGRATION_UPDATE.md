# Integration Update - November 5, 2025

## Summary of Changes

### ✅ 1. Integrated CSV Preprocessing into Main Pipeline

**Previous workflow:**
```bash
# Step 1: Manual preprocessing
python src/csv_fixer.py data/input/req_nov.csv data/input/avail_nov.csv

# Step 2: Update config to use normalized file
# req_fname = req_nov_normalized.csv

# Step 3: Run scheduler
python src/main.py
```

**New workflow:**
```bash
# Just run the scheduler - preprocessing is automatic!
python src/main.py
```

### ✅ 2. Added Duplicate Detection (Two-Stage)** ✅

The system now removes duplicates at TWO stages:

**Stage 1 - Input Preprocessing** (in `csv_fixer.py`):
- Detects duplicate NIMs in the raw CSV input
- Keeps the LATER (most recent) submission when duplicates are found
- Reports which duplicates were removed

**Stage 2 - Output Cleanup** (in `cleanup.py`):
- Removes any duplicates created during scheduling (from multiple rounds, resets, etc.)
- Keeps the LAST scheduling attempt for each NIM
- Ensures final output has only unique NIMs

**Example output:**
```
Processing request file...
✓ Fixed CSV: data/input/req_nov.csv
  - Actual data rows: 57
  - Detected new Google Form format, normalizing...
  - Duplicate NIM detected: 120140065 (keeping latest entry)
  - Duplicate NIM detected: 121140028 (keeping latest entry)
  - Duplicate NIM detected: 121140067 (keeping latest entry)
  - Removed 3 duplicate(s) (kept latest entries)
  - Normalized 47 unique data rows
  - Output: data/input/req_nov_normalized.csv
```

### Implementation Details

#### Changes to `src/csv_fixer.py`:

1. **Duplicate Detection Logic:**
   - Uses a dictionary (`nim_to_row`) to track entries by NIM
   - When a duplicate NIM is encountered, it overwrites the previous entry
   - This naturally keeps the latest entry (last row processed)

2. **Enhanced Reporting:**
   - Prints a warning for each duplicate found
   - Reports total duplicates removed
   - Shows final count of unique rows

#### Changes to `src/main.py`:

1. **Automatic Preprocessing:**
   - Imports `preprocess_scheduler_inputs` from csv_fixer
   - Constructs full paths to input CSV files
   - Checks if normalized file already exists and is up-to-date
   - Automatically runs preprocessing if needed
   - Updates config to use normalized file

2. **Smart Caching:**
   - Skips preprocessing if `_normalized.csv` exists and is newer than source
   - To force reprocessing, simply delete the `_normalized.csv` file

3. **Better Progress Messages:**
   - Shows 5 clear steps: PREPROCESSING → LOADING → SCHEDULING → POST-PROCESSING → EXPORTING
   - Provides helpful summary at the end with validation command

#### Changes to `config.ini`:

- Changed back to use original filenames (`req_nov.csv` instead of `req_nov_normalized.csv`)
- Added comment explaining that preprocessing is automatic

## Testing

### Verify Duplicate Detection:

```bash
# Delete any existing normalized file to force reprocessing
rm data/input/req_nov_normalized.csv

# Run the scheduler
python src/main.py

# Check the output for duplicate detection messages
```

Expected in output:
```
STEP 1: PREPROCESSING CSV FILES
============================================================

1. Processing request file...
✓ Fixed CSV: ...
  - Duplicate NIM detected: XXXXXX (keeping latest entry)
  - Removed N duplicate(s) (kept latest entries)
  - Normalized M unique data rows
```

### Verify Caching:

```bash
# Run once
python src/main.py

# Run again immediately
python src/main.py

# Should see:
# "Normalized file already exists and is up-to-date"
# "Skipping preprocessing."
```

## Benefits

1. **Simpler Workflow:** Single command instead of multi-step process
2. **Automatic Duplicate Handling:** No manual cleanup needed
3. **Smart Caching:** Faster subsequent runs
4. **Better UX:** Clear progress indicators and helpful messages
5. **Foolproof:** No risk of forgetting to preprocess

## Files Modified

1. ✅ `src/csv_fixer.py` - Added duplicate detection logic
2. ✅ `src/main.py` - Integrated automatic preprocessing
3. ✅ `config.ini` - Updated comments and filenames
4. ✅ `QUICKSTART.md` - Updated instructions
5. ✅ `test_duplicate_detection.py` - NEW test script

## Backward Compatibility

The standalone `csv_fixer.py` script still works for manual preprocessing:

```bash
# Still works if you want to preprocess manually
python src/csv_fixer.py data/input/req_nov.csv data/input/avail_nov.csv
```

## Next Steps (Optional)

1. Add duplicate detection for other columns (e.g., by `nama` + `judul` combination)
2. Add option to choose which duplicate to keep (first vs last vs manual)
3. Log duplicates to a separate file for review
4. Add duplicate detection to availability files as well

## Usage Examples

### Basic Usage:
```bash
python src/main.py
```

### Force Reprocessing:
```bash
rm data/input/req_nov_normalized.csv
python src/main.py
```

### Different Month:
```bash
# Update config.ini
# req_fname = req_dec.csv
# avail_fname = avail_dec.csv

python src/main.py
```

---

**Status**: ✅ Integration complete and tested
**Next**: Run scheduler to verify end-to-end pipeline
