# TA Scheduler - November 2025 Update Summary

## Date: November 5, 2025

## Issues Addressed

### 1. ✅ CSV Format Compatibility
**Problem**: New Google Form exports have a different column structure and embedded newlines in cells

**Solution**: Created `src/csv_fixer.py` preprocessing script that:
- Fixes "broken" CSV rows caused by embedded newlines
- Normalizes Google Form column names to scheduler-expected format
- Preserves all essential data while removing unnecessary columns

**Usage**:
```bash
python src/csv_fixer.py data/input/req_nov.csv data/input/avail_nov.csv
```

**Output**:
- `data/input/req_nov_normalized.csv` - Ready for scheduler
- `data/input/avail_nov.csv` - Fixed in-place

### 2. ⚠️ Timeslot Double-Booking Issue
**Problem**: Multiple events can be scheduled in the same timeslot even when `parallel_event=1`

**Root Cause Analysis**:
The scheduler checks availability BEFORE assignment, but doesn't re-verify atomically at assignment time. Between the availability check and the actual slot assignment, another request might fill the slot.

**Location**: `src/scheduler.py`, lines 920-930 in `_update_timeslot_from_request_examiners()`

**Current Logic**:
```python
for slot_col in slot_columns:
    if self.dataframes['timeslots'].loc[row_idx, slot_col] == 'none':
        self.dataframes['timeslots'].loc[row_idx, slot_col] = assignment_name
        break  # Assigns to first available slot
```

**Issue**: No re-check if slot is still 'none' right before assignment (race condition)

### 3. ✅ Examiner Preservation for Sidang Akhir
**Status**: Previously addressed
**Solution**: Scheduler now preserves pre-assigned examiners for Sidang Akhir events

## Recommended Fixes for Timeslot Conflicts

### Option A: Atomic Check-and-Assign (Recommended)
Modify `src/scheduler.py` around line 919:

```python
# BEFORE (problematic):
for slot_col in slot_columns:
    if self.dataframes['timeslots'].loc[row_idx, slot_col] == 'none':
        self.dataframes['timeslots'].loc[row_idx, slot_col] = assignment_name
        slot_assigned = True
        break

# AFTER (atomic):
# Pre-verify all consecutive slots before ANY assignment
slots_to_fill = []
for i in range(duration):
    # ... calculate time for each slot ...
    # ... find row_idx for this time ...
    
    # Find available slot at this specific time
    slot_found = False
    for slot_col in slot_columns:
        if self.dataframes['timeslots'].loc[row_idx, slot_col] == 'none':
            slots_to_fill.append((row_idx, slot_col, assignment_name))
            slot_found = True
            break
    
    if not slot_found:
        print(f"Cannot assign: timeslot fully occupied")
        return False  # Abort entire assignment

# All verified - now assign atomically
for row_idx, slot_col, name in slots_to_fill:
    self.dataframes['timeslots'].loc[row_idx, slot_col] = name
```

### Option B: Increase parallel_event Temporarily
If double-booking is acceptable temporarily:

```ini
# config.ini
[PARAMETERS]
parallel_event = 2  # Allow 2 events per timeslot
```

### Option C: Post-Processing Validation
Add validation after scheduling to detect and report conflicts:

```python
def validate_timeslots(timeslots_df, parallel_event):
    """Check for over-booking"""
    for idx, row in timeslots_df.iterrows():
        slot_cols = [col for col in row.index if col.startswith('slot_')]
        occupied = sum(1 for col in slot_cols if row[col] != 'none')
        if occupied > parallel_event:
            print(f"⚠️ CONFLICT at {row['date']} {row['time']}: {occupied} events (max: {parallel_event})")
```

## Files Modified

1. **`src/csv_fixer.py`** - NEW: CSV preprocessing module
2. **`config.ini`** - Updated to use `req_nov_normalized.csv`
3. **`CSV_PREPROCESSING_README.md`** - NEW: Comprehensive preprocessing guide
4. **`data/input/req_nov_normalized.csv`** - NEW: Normalized November requests

## Testing Checklist

- [x] CSV fixer successfully parses Google Form exports
- [x] Column normalization maps all required fields
- [x] Embedded newlines handled correctly
- [ ] Scheduler runs without Python environment errors
- [ ] No timeslot conflicts in output
- [ ] Pre-assigned examiners preserved
- [ ] Capstone groups scheduled together

## Next Steps

1. **Immediate**: Fix Python environment issue (numpy import error)
   ```bash
   cd /Users/martinmanullang/Developer/ta-scheduler-ifitera
   python -m pip install --upgrade numpy pandas
   ```

2. **Short-term**: Implement atomic assignment fix (Option A above)

3. **Long-term**: Add unit tests for:
   - CSV preprocessing
   - Timeslot assignment logic
   - Examiner preservation
   - Parallel event limits

## Usage Instructions

### For November 2025 Scheduling:

```bash
# 1. Preprocess CSV files
python src/csv_fixer.py data/input/req_nov.csv data/input/avail_nov.csv

# 2. Verify config.ini points to normalized file
cat config.ini  # Should show req_fname = req_nov_normalized.csv

# 3. Run scheduler
python src/main.py

# 4. Check outputs
ls -lh data/output/final_output_nov.csv
ls -lh data/output/final_timeslot_nov.csv
ls -lh data/output/final_lectureschedule_nov.csv

# 5. Validate no double-bookings
python -c "
import pandas as pd
df = pd.read_csv('data/output/final_timeslot_nov.csv')
for idx, row in df.iterrows():
    slots = [col for col in df.columns if col.startswith('slot_')]
    occupied = sum(1 for s in slots if row[s] != 'none')
    if occupied > 1:  # parallel_event = 1
        print(f'Conflict: {row[\"date\"]} {row[\"time\"]} has {occupied} events')
"
```

### For Future Months:

1. Export new data from Google Forms
2. Run preprocessing: `python src/csv_fixer.py data/input/req_XXX.csv data/input/avail_XXX.csv`
3. Update `config.ini` to use `req_XXX_normalized.csv`
4. Run scheduler: `python src/main.py`

## Documentation

- **CSV Preprocessing**: See `CSV_PREPROCESSING_README.md`
- **Main README**: See `README.md` (if exists)
- **Config Reference**: See `config.ini` comments

## Contact

For questions about:
- **CSV preprocessing**: Review `src/csv_fixer.py` and `CSV_PREPROCESSING_README.md`
- **Scheduler logic**: Review `src/scheduler.py` (main scheduling algorithm)
- **Timeslot conflicts**: See "Recommended Fixes" section above

---

**Status**: ✅ CSV preprocessing complete | ⚠️ Scheduler pending environment fix and atomic assignment update
