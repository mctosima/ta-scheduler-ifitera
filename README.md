# Thesis Defense Scheduler

A comprehensive scheduling system for thesis defense sessions that matches students with available judges based on supervisor availability and expertise fields.

## Features

- **Expertise-based Judge Matching**: Matches students with judges based on Field 1 and Field 2 expertise requirements
- **Conflict-free Scheduling**: Prevents double-booking by tracking scheduled time slots for each judge
- **Exactly 2 Judge Recommendations**: Ensures each student gets exactly 2 examiner recommendations (uses "NONE" placeholder when insufficient judges available)
- **Supervisor Management**: Supports both single and dual supervisor configurations, excludes supervisors from examiner recommendations
- **Dynamic Path Handling**: Cross-platform compatible with automatic directory creation and flexible file paths
- **Modular Architecture**: Clean, maintainable code structure with separated concerns

## Quick Start

### 1. Setup Project Structure

```bash
python main.py --setup
```

This will create the necessary `input/` and `output/` directories and move your CSV files to the appropriate locations.

### 2. Run Scheduling

For multiple student requests (default):
```bash
python main.py
```

For a single student request:
```bash
python main.py --single
```

For custom files:
```bash
python main.py -a input/your_availability.csv -r input/your_requests.csv -o output/results.csv
```

## File Structure

```
ta-scheduler/
├── main.py                    # Main entry point
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── config.py             # Configuration management
│   ├── models.py             # Data models and structures
│   ├── scheduler.py          # Core scheduling engine
│   ├── utils.py              # Utility functions
│   └── main.py               # Application interface
├── input/                    # Input CSV files
│   ├── avail_20250610_clean.csv
│   ├── schedule_request.csv
│   └── schedule_request_multiple.csv
├── output/                   # Generated results
│   └── *_with_recommendations.csv
└── README.md
```

## Input File Formats

### Judge Availability File (`avail_20250610_clean.csv`)

| Nama_Dosen | Sub_Keilmuan | Tuesday_10_June_2025_08:00 | ... |
|------------|--------------|----------------------------|-----|
| Dr. Smith  | ABC;XYZ;DEF  | TRUE                       | ... |

- `Nama_Dosen`: Judge name
- `Sub_Keilmuan`: Semicolon-separated expertise codes
- Time columns: Boolean availability for each time slot

### Student Request File (`schedule_request.csv` or `schedule_request_multiple.csv`)

| Nama     | Nim      | Field 1 | Field 2 | SPV 1   | SPV 2   |
|----------|----------|---------|---------|---------|---------|
| John Doe | 12345678 | ABC     | XYZ     | Dr. A   | Dr. B   |

- `Nama`: Student name
- `Nim`: Student ID number
- `Field 1`, `Field 2`: Required expertise fields
- `SPV 1`, `SPV 2`: Supervisor names or codes (use "-" for single supervisor)

## Output Format

The system generates CSV files with additional columns:

- `Date Time (YYYYMMDD-HHMM)`: Scheduled time slot or error message
- `List of recommendation`: Exactly 2 judges in format "JUDGE1 | JUDGE2" or "JUDGE1 | NONE"

## Scheduling Algorithm

### 1. Judge Selection Priority

For each student, the system:

1. **Finds Supervisors**: Matches SPV 1 and SPV 2 with available judges
2. **Identifies Expertise Matches**: Finds judges with Field 1 or Field 2 expertise (excluding supervisors)
3. **Selects Exactly 2 Examiners**:
   - Priority 1: Judge with Field 1 expertise
   - Priority 2: Judge with Field 2 expertise (different from Field 1 selection)
   - Priority 3: Any available judge to fill remaining slots
   - Uses "NONE" placeholder if fewer than 2 judges available

### 2. Time Slot Assignment

- Finds time slots where all required judges (supervisors + examiners) are available
- Reserves time slots to prevent conflicts with later scheduling
- Assigns single time slot per student (no multiple options in final output)

### 3. Conflict Prevention

- Tracks scheduled judges for each time slot
- Prevents double-booking of any judge
- Processes students sequentially to avoid conflicts

## Configuration

The system uses dynamic configuration through `src/config.py`:

- **Paths**: Automatically resolves input/output directories
- **Constraints**: Configurable number of required judges, panel sizes
- **Column Mappings**: Flexible CSV column name handling
- **Time Formatting**: Customizable date/time output formats

## Architecture

### Core Components

1. **`config.py`**: Configuration management with dynamic path resolution
2. **`models.py`**: Data structures (Judge, Student, ScheduleResult, etc.)
3. **`scheduler.py`**: Main scheduling engine with conflict resolution
4. **`utils.py`**: Helper functions for data processing and reporting
5. **`main.py`**: Application interface and command-line handling

### Key Classes

- **`Judge`**: Represents lecturer with availability and expertise
- **`Student`**: Represents thesis defense request
- **`SchedulingEngine`**: Core scheduling logic
- **`ThesisSchedulerApp`**: High-level application interface

## Command Line Options

```bash
python main.py [OPTIONS]

Options:
  -a, --availability PATH    Path to availability CSV file
  -r, --requests PATH        Path to requests CSV file  
  -o, --output PATH          Path to output CSV file
  --setup                    Setup project directory structure
  --multiple                 Use multiple requests file (default)
  --single                   Use single request file
  -h, --help                 Show help message
```

## Examples

### Example 1: Default Multiple Student Scheduling

```bash
python main.py
```

Uses:
- Input: `input/avail_20250610_clean.csv` and `input/schedule_request_multiple.csv`
- Output: `output/schedule_request_multiple_with_recommendations.csv`

### Example 2: Custom File Scheduling

```bash
python main.py -a input/availability.csv -r input/requests.csv -o output/results.csv
```

### Example 3: Single Student Request

```bash
python main.py --single
```

Uses:
- Input: `input/avail_20250610_clean.csv` and `input/schedule_request.csv`
- Output: `output/schedule_request_with_recommendations.csv`

## Sample Output

```
==========================================================
THESIS DEFENSE SCHEDULER
==========================================================
Loading availability data from: input/avail_20250610_clean.csv
Loaded availability data: 25 judges
Loading request data from: input/schedule_request_multiple.csv
Loaded request data: 3 requests
Converting data to internal models...
Loaded 25 judges and 3 students

Starting scheduling process...

--- Creating panel for John Doe ---
✓ Found supervisor: ABC (Dr. Smith)
✓ Found supervisor: XYZ (Dr. Jones)  
✓ Found 2 supervisors, 2 examiners
✓ Scheduled at 20250610-0800
✓ Panel: ABC, XYZ, DEF, GHI
✓ Recommendations: DEF | GHI

📊 SCHEDULING SUMMARY:
   Successfully scheduled: 3/3
   Success rate: 100.0%

🗓️  SCHEDULED DEFENSES:
   • John Doe - 20250610-0800 - Judges: DEF | GHI
   • Jane Smith - 20250610-1000 - Judges: JKL | MNO
   • Bob Wilson - 20250610-1400 - Judges: PQR | STU

⏰ TIME SLOT UTILIZATION:
   • 20250610-0800: ABC | XYZ | DEF | GHI
   • 20250610-1000: JKL | MNO | UVW | XYZ
   • 20250610-1400: PQR | STU | ABC | DEF

✅ Scheduling completed successfully!
Scheduled 3/3 students
```

## Error Handling

The system handles various error conditions:

- **Missing Supervisors**: Continues with available supervisors, logs warnings
- **Insufficient Judges**: Uses "NONE" placeholders for missing examiner slots
- **No Available Time Slots**: Reports scheduling failure with reason
- **Invalid Data**: Validates CSV structure and student data integrity

## Troubleshooting

### Common Issues

1. **"No supervisors found"**
   - Check supervisor names match judge names in availability file
   - Verify supervisor codes exist in expertise field

2. **"No available time slots"**
   - Check if supervisors have overlapping availability
   - Verify judge availability data is correct

3. **"Invalid CSV structure"**
   - Ensure required columns exist in input files
   - Check for proper CSV formatting

### Debug Mode

The system provides detailed logging during execution. Monitor console output for:
- Judge loading confirmation
- Supervisor matching results  
- Expertise match findings
- Time slot availability checks
- Final scheduling outcomes

## Requirements

- Python 3.7+
- pandas
- numpy

Install dependencies:
```bash
pip install pandas numpy
```

## Migration from Monolithic Version

If you have the old `thesis_scheduler.py`, the new system maintains compatibility:

1. Run `python main.py --setup` to create directory structure
2. Place your CSV files in the `input/` directory
3. Run scheduling with `python main.py`

Your existing CSV files and column formats are fully supported.

## License

This project is licensed under the MIT License.
