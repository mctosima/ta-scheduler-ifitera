# Quick Start Guide - November 2025 Scheduling

## TL;DR

```bash
# 1. Run scheduler (preprocessing is now automatic!)
python src/main.py

# 2. Validate no conflicts
python validate_timeslots.py data/output/final_timeslot_nov.csv 1
```

**Note**: CSV preprocessing (fixing breaks, normalizing format, removing duplicates) now happens automatically!

## What Was Fixed

### Problem 1: CSV Format Issues ✅ SOLVED
Google Forms exports have embedded newlines that break CSV parsing.

**Solution**: Two-stage duplicate removal integrated into `main.py`
- Stage 1 (Input): Fixes CSV breaks, normalizes format, removes duplicate submissions
- Stage 2 (Output): Removes any duplicates created during scheduling
- **Result**: Guaranteed unique NIMs in final output

### Problem 2: Timeslot Conflicts ⚠️ IDENTIFIED
Same timeslot can have multiple events when `parallel_event=1`

**Root Cause**: Non-atomic check-and-assign in `src/scheduler.py:920-930`

**Temporary Workaround**: Increase `parallel_event` in config.ini
**Permanent Fix**: Implement atomic assignment (see NOVEMBER_2025_UPDATE.md)

### Problem 3: Examiner Overwriting ✅ PREVIOUSLY FIXED
Pre-assigned examiners were being replaced

**Solution**: Already implemented in scheduler.py (preservation logic)

## New Files Created

1. **`src/csv_fixer.py`** - Preprocessing script
2. **`CSV_PREPROCESSING_README.md`** - Full preprocessing documentation
3. **`NOVEMBER_2025_UPDATE.md`** - Technical summary of all changes
4. **`validate_timeslots.py`** - Conflict detection tool
5. **`data/input/req_nov_normalized.csv`** - Normalized November requests

## Verification Steps

After running the scheduler:

```bash
# Check if output files exist
ls -lh data/output/final_*_nov.csv

# Validate no double-bookings
python validate_timeslots.py data/output/final_timeslot_nov.csv 1

# Check specific student schedule
grep "121140089" data/output/final_output_nov.csv

# Count scheduled vs unscheduled
python -c "
import pandas as pd
df = pd.read_csv('data/output/final_output_nov.csv')
scheduled = df['status'].notna().sum()
total = len(df)
print(f'Scheduled: {scheduled}/{total} ({100*scheduled/total:.1f}%)')
"
```

## For Future Months

Just update `config.ini` with the new file names and run:

```bash
# Update config.ini:
# req_fname = req_dec.csv
# avail_fname = avail_dec.csv
# out_fname = final_output_dec.csv
# ...etc

# Then simply run:
python src/main.py
```

The preprocessing (fixing breaks, normalizing, removing duplicates) happens automatically!

## If You See Conflicts

Run the validator first:
```bash
python validate_timeslots.py data/output/final_timeslot_nov.csv 1
```

If conflicts are detected:
1. Check if they're acceptable (e.g., different rooms)
2. If not, consider increasing `parallel_event` temporarily
3. For permanent fix, implement atomic assignment from NOVEMBER_2025_UPDATE.md

## Documentation

- **CSV Issues**: See `CSV_PREPROCESSING_README.md`
- **Technical Details**: See `NOVEMBER_2025_UPDATE.md`
- **This Guide**: `QUICKSTART.md` (this file)

---

**Ready to schedule?** Run the 3 commands at the top! 🚀
