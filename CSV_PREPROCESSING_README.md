# CSV Preprocessing Guide

## Problem Overview

The scheduler expects CSV files in a specific format, but Google Forms exports data with:
1. **Embedded newlines** in cells (especially in the `Judul` field when titles span multiple lines)
2. **Different column structure** (many additional columns like Timestamp, Email, file URLs, etc.)

### The "Break Character" Issue

CSV files have a rule: if a cell contains a comma or newline, the entire cell must be wrapped in double quotes (`"`).

- **Microsoft Excel** understands this and displays multi-line cells correctly
- **VS Code** (and basic text editors) see the newline and visually "break" the row into multiple lines
- **Simple CSV parsers** may incorrectly interpret these breaks as new rows

## Solution: CSV Fixer Module

The `src/csv_fixer.py` script solves both issues:

### 1. Fix CSV Break Characters
Uses Python's built-in `csv` module to properly parse quoted fields with newlines, then rewrites the file with proper escaping.

### 2. Normalize Google Form Format
Maps the new Google Form columns to the expected scheduler format:

**New Format (Google Forms)**:
- `Timestamp`, `Email address`, `Nama`, `Nim`, `Judul`, `Apakah tugas akhir bersifat Capstone?`, etc.

**Old Format (Scheduler Expected)**:
- `nama`, `nim`, `judul`, `capstone_code`, `type`, `field_1`, `field_2`, `spv_1`, `spv_2`, `date_time`, `examiner_1`, `examiner_2`, `status`

## Usage

### Quick Start (Preprocess Both Files)

```bash
python src/csv_fixer.py data/input/req_nov.csv data/input/avail_nov.csv
```

**Output**:
- `data/input/req_nov_normalized.csv` - Cleaned and normalized request file
- `data/input/avail_nov.csv` - Fixed availability file (in-place)

### Single File Fix

```bash
python src/csv_fixer.py data/input/your_file.csv
```

This fixes the CSV break characters without normalization.

## Running the Scheduler

After preprocessing, update `config.ini`:

```ini
[FILES]
avail_fname = avail_nov.csv
req_fname = req_nov_normalized.csv  # Use the normalized version
```

Then run the scheduler as usual:

```bash
python src/main.py
```

## What Gets Normalized

| Original Column | Mapped To | Notes |
|----------------|-----------|-------|
| `Timestamp` | *(removed)* | Not needed for scheduling |
| `Email address` | *(removed)* | Not needed |
| `Nama` | `nama` | Direct mapping |
| `Nim` | `nim` | Direct mapping |
| `Judul` | `judul` | **Newlines replaced with spaces** |
| `Masukkan Kode Capstone` | `capstone_code` | Direct mapping |
| `Jenis Pendaftaran` | `type` | Direct mapping |
| `Kata Kunci Keilmuan - Opsi 1` | `field_1` | Direct mapping |
| `Kata Kunci Keilmuan - Opsi 2` | `field_2` | Direct mapping |
| `Pembimbing 1` | `spv_1` | Direct mapping |
| `Pembimbing 2 (jika ada)` | `spv_2` | Direct mapping |
| `Penguji 1 Ketika Seminar Proposal` | `examiner_1` | Pre-assigned examiner |
| `Penguji 2 Ketika Seminar Proposal` | `examiner_2` | Pre-assigned examiner |
| *(new)* | `date_time` | Empty (to be scheduled) |
| *(new)* | `status` | Empty (to be filled) |

## Verification

After preprocessing, check the normalized file:

```bash
# View first 10 rows
head -n 10 data/input/req_nov_normalized.csv

# Count rows
wc -l data/input/req_nov_normalized.csv
```

Expected: 1 header row + N data rows (where N = number of valid submissions)

## Troubleshooting

### "Multiple rows visually shown for one entry"
**Cause**: Cell contains embedded newlines
**Fix**: Run `csv_fixer.py` on the file

### "Missing columns in scheduler"
**Cause**: Using raw Google Form export without normalization
**Fix**: Use the `*_normalized.csv` output

### "Examiner assignments getting replaced"
**Cause**: Scheduler bug (being addressed separately)
**Fix**: The scheduler now preserves pre-assigned examiners for Sidang Akhir events

## For Future Months

1. Export new data from Google Forms
2. Run preprocessing:
   ```bash
   python src/csv_fixer.py data/input/req_dec.csv data/input/avail_dec.csv
   ```
3. Update `config.ini` to use `req_dec_normalized.csv`
4. Run scheduler: `python src/main.py`

## Technical Details

### CSV Module Advantage
The Python `csv` module follows RFC 4180 (CSV standard), which properly handles:
- Quoted fields with commas
- Quoted fields with newlines
- Escaped quotes within fields

This is more robust than simple string splitting or regex parsing.

### Preserving Data Integrity
- All original data is preserved (except removed columns)
- Newlines in `judul` are converted to spaces (single-line format)
- Empty cells remain empty
- Pre-assigned examiners are preserved
