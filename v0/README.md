# Thesis Defense Scheduler

A comprehensive scheduling system for thesis defense sessions that matches students with available judges based on supervisor availability and expertise fields.

## Features

- **Two-Tier Scheduling System**: Advanced field+time matching with intelligent time-only fallback
- **Smart Workload Balancing**: Ensures fair assignment distribution across all judges with real-time tracking
- **Expertise-based Judge Matching**: Prioritizes judges with matching Field 1 and Field 2 expertise
- **Conflict-free Scheduling**: Prevents double-booking with comprehensive time slot tracking
- **Parallel Defense Management**: Configurable maximum concurrent defenses per time slot
- **Exactly 2 Judge Recommendations**: Guarantees 2 examiner recommendations with intelligent fallback
- **Supervisor Management**: Supports single/dual supervisors with automatic conflict exclusion
- **Comprehensive Analytics**: Detailed workload distribution, success rates, and utilization metrics
- **Status Transparency**: Clear indication of scheduling quality (Field+Time Match vs Time-Only)
- **Automated File Processing**: Auto-detects and cleans raw Excel availability files
- **Dynamic Path Handling**: Cross-platform compatible with automatic directory creation
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
├── config.ini                 # Configuration file for paths and settings
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── config.py             # Configuration management (reads config.ini)
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

The system generates CSV files with comprehensive scheduling information:

### Standard Output Columns

- **`Tanggal dan Waktu (Format: YYYYMMDD-HHMM)`**: Scheduled time slot or error message
- **`Penguji 1`**: First recommended judge code or "NONE"
- **`Penguji 2`**: Second recommended judge code or "NONE"
- **`Status`**: Scheduling quality indicator

### Status Column Values

- **"Field and Time Match"**: Optimal scheduling with both expertise and time alignment
- **"Time Match Only"**: Successful scheduling with workload balancing but no expertise match
- **"Not Scheduled"**: Failed scheduling with specific reason provided

### Sample Output Records

```csv
Nama,Nim,Field 1,Field 2,SPV 1,SPV 2,Tanggal dan Waktu,Penguji 1,Penguji 2,Status
Yondika Vio Landa,121140161,MLTR,TEXT,IFA,,20250612-1100,ANS,HBF,Field and Time Match
M Rizki Alfaina,121140228,DLNL,TEXT,ANS,WIY,20250617-0900,HTA,IWW,Time Match Only
Rivaldi Nainggolan,121140012,WEBI,HCIU,AWJ,IFA,NOT_SCHEDULED: No available time slot,NONE,NONE,Not Scheduled
```

### Workload Distribution Reports

The system also generates detailed workload analytics:

- **Individual judge assignment counts** with visual indicators
- **Workload distribution statistics** (total, average, range)
- **Time slot utilization details** showing parallel defense management
- **Scheduling performance metrics** (success rates, tier breakdown)

## Scheduling Algorithm & Logic

The thesis defense scheduler implements a sophisticated two-tier scheduling system with advanced workload balancing and fairness mechanisms.

### Overview: Two-Tier Scheduling System

The system uses a hierarchical approach to maximize both expertise matching and workload fairness:

1. **Tier 1: Field and Time Match** - Prioritizes both expertise alignment and time availability
2. **Tier 2: Time Match Only** - Falls back to time-only scheduling with smart workload balancing

### Phase 1: Supervisor Identification

For each student, the system first identifies their supervisors:

1. **Supervisor Matching Logic**:
   - Matches SPV 1 and SPV 2 names against judge database
   - Uses fuzzy matching (code, expertise field, or name similarity)
   - Supports both single and dual supervisor configurations
   - Excludes supervisors from examiner pool to avoid conflicts

2. **Supervisor Validation**:
   - Ensures supervisors exist in the judge availability pool
   - Logs warnings for missing supervisors
   - Continues scheduling with available supervisors if some are missing

### Phase 2: Tier 1 - Field and Time Matching

The primary scheduling attempt prioritizes expertise alignment:

#### 2.1 Expertise-Based Judge Selection

1. **Field Matching Process**:
   - Identifies judges with expertise in student's Field 1 or Field 2
   - Excludes supervisors from examiner consideration
   - Creates pools of field-specific expert judges

2. **Workload-Balanced Selection**:
   - **Priority 1**: Judge with Field 1 expertise (lowest workload first)
   - **Priority 2**: Judge with Field 2 expertise (different from Field 1 selection, lowest workload first)
   - **Priority 3**: Any available expert judge to fill remaining slots (lowest workload first)

3. **Smart Workload Balancing**:
   ```
   Selection Logic:
   • Sort candidates by current assignment count (ascending)
   • Select least-loaded judge from each expertise category
   • Log workload information during selection process
   • Track real-time assignment distribution
   ```

#### 2.2 Time Slot Validation

1. **Availability Checking**:
   - Verifies all required judges (supervisors + examiners) are available at the same time
   - Enforces parallel defense limits per time slot
   - Ensures no judge double-booking across sessions

2. **Parallel Defense Management**:
   - Configurable maximum concurrent defenses per time slot (`max_parallel_defenses`)
   - Tracks defense count per time slot to prevent over-scheduling
   - Balances room/resource utilization

### Phase 3: Tier 2 - Time Match Only (Fallback)

When Tier 1 fails, the system uses intelligent time-only matching:

#### 3.1 Smart Combination Generation

1. **Available Judge Pool**:
   - Includes all non-supervisor judges regardless of expertise
   - Sorts judges by current workload (ascending - least loaded first)
   - Generates combinations of required size (typically 2 examiners)

2. **Intelligent Combination Evaluation**:
   ```python
   For each possible examiner combination:
   • Calculate total workload sum for the combination
   • Check time slot availability for supervisors + examiners
   • Select combination with lowest total workload
   • Log workload comparisons during selection
   ```

3. **Workload Optimization**:
   - Evaluates all valid combinations before selection
   - Prioritizes combinations with lowest cumulative workload
   - Implements early termination for very low workload combinations
   - Ensures fair distribution even without expertise matching

#### 3.2 Time-Only Scheduling Benefits

- **Fairness**: Ensures even judges without matching expertise get balanced assignments
- **Utilization**: Maximizes successful scheduling by ignoring expertise constraints
- **Transparency**: Clearly indicates when expertise matching was not possible
- **Reporting**: Distinguishes between "Field and Time Match" vs "Time Match Only" in output

### Workload Balancing & Fairness Mechanisms

#### 4.1 Real-Time Workload Tracking

1. **Assignment Counting**:
   - Tracks assignment count per judge across the entire session
   - Updates workload immediately upon each scheduling decision
   - Maintains running totals for all judges throughout the process

2. **Dynamic Priority Adjustment**:
   - Continuously sorts judge candidates by current workload
   - Prioritizes least-loaded judges in all selection scenarios
   - Prevents any judge from being overwhelmed with assignments

#### 4.2 Fairness Distribution Algorithm

1. **Workload Balancing Logic**:
   ```
   Selection Priority (for both tiers):
   1. Expertise match (Tier 1 only)
   2. Current workload (ascending - least loaded first)
   3. Availability at required time slot
   4. No prior assignment conflicts
   ```

2. **Visual Workload Reporting**:
   - 🔴 High workload (significantly above average)
   - 🟡 Medium workload (slightly above average)  
   - 🟢 Balanced workload (at or below average)

#### 4.3 Workload Distribution Metrics

The system provides comprehensive workload analytics:

- **Total assignments** across all judges
- **Average assignments per judge**
- **Individual workload breakdown** with visual indicators
- **Range analysis** (minimum to maximum assignments)
- **Distribution quality assessment**

### Judge Priority & Selection Logic

#### 5.1 Multi-Criteria Priority System

Judge selection follows a sophisticated priority hierarchy:

1. **Tier 1 (Field and Time Match) Priority**:
   ```
   Priority Level 1: Field 1 expertise + lowest workload
   Priority Level 2: Field 2 expertise + lowest workload (≠ Field 1 selection)
   Priority Level 3: Any expertise match + lowest workload
   Priority Level 4: Fallback to Tier 2 if insufficient experts
   ```

2. **Tier 2 (Time Match Only) Priority**:
   ```
   Priority Level 1: Lowest total combination workload
   Priority Level 2: Best individual workload distribution
   Priority Level 3: Time slot availability
   Priority Level 4: No expertise requirements
   ```

#### 5.2 Conflict Resolution

1. **Double-booking Prevention**:
   - Maintains real-time judge schedule tracking
   - Prevents scheduling the same judge for overlapping time slots
   - Validates availability before finalizing assignments

2. **Supervisor Exclusion**:
   - Automatically excludes student supervisors from examiner pool
   - Prevents conflicts of interest in evaluation
   - Ensures proper panel composition

### Parallel Defense Management

#### 6.1 Configurable Concurrency Control

1. **Configuration**:
   - `max_parallel_defenses` setting in config.ini
   - Controls maximum simultaneous defenses per time slot
   - Balances resource utilization with quality control

2. **Enforcement Logic**:
   - Tracks defense count per time slot in real-time
   - Rejects time slots that exceed parallel defense limits
   - Provides clear feedback when parallel limits prevent scheduling

#### 6.2 Resource Optimization

1. **Efficient Judge Utilization**:
   - Maximizes judge availability across multiple concurrent defenses
   - Balances between utilization efficiency and workload fairness
   - Optimizes time slot allocation for maximum throughput

2. **Quality Assurance**:
   - Prevents over-scheduling that could compromise defense quality
   - Ensures adequate attention and resources for each defense
   - Maintains proper supervision ratios

### Status Reporting & Transparency

#### 7.1 Scheduling Quality Indicators

The system provides clear status indicators for each scheduling result:

- **"Field and Time Match"**: Optimal scheduling with expertise alignment
- **"Time Match Only"**: Successful scheduling with workload balancing but no expertise match
- **"Not Scheduled"**: Failed scheduling with specific reason provided

#### 7.2 Comprehensive Analytics

1. **Success Rate Tracking**:
   - Overall scheduling success percentage
   - Breakdown by scheduling tier (Field+Time vs Time-only)
   - Failure analysis with specific reasons

2. **Workload Distribution Reports**:
   - Visual workload indicators for each judge
   - Statistical distribution analysis
   - Fairness metrics and balance assessment

3. **Time Slot Utilization**:
   - Per-slot judge allocation details
   - Parallel defense tracking
   - Resource utilization efficiency metrics

## Configuration

The system supports comprehensive configuration through both configuration files and dynamic code configuration:

### Configuration File (`config.ini`)

The system reads settings from a `config.ini` file in the project root:

```ini
[PATHS]
input_dir = input
output_dir = output

[FILES]
availability_file = availability.csv
single_request_file = schedule_request.csv
multiple_request_file = request.csv
output_suffix = scheduling_output.csv

[SCHEDULING]
required_judges = 2              # Number of examiner judges required per student
max_panel_size = 5              # Maximum total panel size (supervisors + examiners)
max_recommendations = 5          # Maximum examiner recommendations to generate
max_parallel_defenses = 1       # Maximum concurrent defenses per time slot

[COLUMNS]
# CSV column mappings for flexible input file formats
availability_name_col = Nama_Dosen
availability_expertise_col = Sub_Keilmuan
request_student_name_cols = Nama,nama
request_field1_cols = Field 1,field1
request_field2_cols = Field 2,field2

[TIME_FORMAT]
output_format = %%Y%%m%%d-%%H%%M  # Output date-time format
```

### Key Configuration Parameters

#### Scheduling Constraints
- **`required_judges`**: Number of examiner judges needed per defense (typically 2)
- **`max_parallel_defenses`**: Controls concurrent defenses per time slot for resource management
- **`max_panel_size`**: Upper limit on total panel members (supervisors + examiners)

#### Workload Balancing
- **Automatic**: Real-time workload tracking with no configuration needed
- **Dynamic Priority**: Continuously adjusts judge selection based on current assignments
- **Fair Distribution**: Ensures balanced assignment distribution across all available judges

#### File Processing
- **Auto-detection**: Automatically identifies and cleans raw Excel availability files
- **Flexible Mapping**: Configurable column names for different CSV formats
- **Output Customization**: Configurable output file naming and formatting

### Dynamic Configuration (`src/config.py`)

The system also uses dynamic configuration for runtime flexibility:

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
============================================================
THESIS DEFENSE SCHEDULER
============================================================
📋 Detecting raw availability file format - cleaning required
🔧 Automatically cleaning availability file...
✅ Cleaned availability file saved to: input/availability_cleaned.csv

Loading availability data from: input/availability_cleaned.csv
Loaded availability data: 27 judges
Loading request data from: input/request.csv
Loaded request data: 51 requests
Converting data to internal models...
Loaded 27 judges and 51 students

Starting scheduling process...
Processing 51 students for optimal scheduling...

--- Creating panel for Yondika Vio Landa ---
✓ Found supervisor: IFA (Ilham Firman Ashari, S.Kom., M.T)
🎯 Attempting field and time matching...
🔹 Selected ANS for field1 'MLTR' (workload: 0)
🔹 Selected HBF as fallback (workload: 0)
✓ Found 1 supervisors, 2 examiners with field expertise
✅ Successfully matched both field expertise and time!
✓ Scheduled at 20250612-1100
✓ Panel: IFA, ANS, HBF
✓ Recommendations: ANS | HBF
✓ Status: Field and Time Match

--- Creating panel for M Rizki Alfaina ---
✓ Found supervisor: AAF (Aidil Afriansyah, S.Kom., M.Kom)
✓ Found supervisor: WIY (Winda Yulita, S.Pd., M.Cs.)
🎯 Attempting field and time matching...
🔹 Selected IEW for field1 'DLNL' (workload: 0)
🔹 Selected RIK as fallback (workload: 0)
✓ Found 2 supervisors, 2 examiners with field expertise
✗ No available time slots found for field-matched judges
⏰ Field matching failed, trying time-only matching...
🔹 Found better combo with total workload 0: HTA(0) + IWW(0)
✓ Selected best workload combo: HTA(0) + IWW(0) (total: 0)
✓ Found 2 supervisors, 2 examiners (time-only match)
✅ Successfully matched time schedule (ignoring field expertise)
✓ Scheduled at 20250617-0900
✓ Panel: AAF, WIY, HTA, IWW
✓ Recommendations: HTA | IWW
✓ Status: Time Match Only

Saving results to: output/requestscheduling_output.csv
✅ Results saved to: output/requestscheduling_output.csv

============================================================
THESIS DEFENSE SCHEDULING SUMMARY
============================================================
Total requests: 51
Successfully scheduled: 48
Failed to schedule: 3
Success rate: 94.1%

🗓️  SCHEDULED DEFENSES:
   • Yondika Vio Landa - 20250612-1100 - Judges: ANS | HBF - Field and Time Match
   • M Rizki Alfaina - 20250617-0900 - Judges: HTA | IWW - Time Match Only
   • Juan Verrel Tanuwijaya - 20250613-1500 - Judges: MIV | HBF - Field and Time Match
   [... 45 more successful schedulings ...]

❌ FAILED TO SCHEDULE:
   • Rivaldi Yonathan Nainggolan - No available time slot or insufficient judges
   • Muhammad Shahih Indra Sakti - No available time slot or insufficient judges
   • Muhammad Widyantoro Wiryawan - No available time slot or insufficient judges

⏰ TIME SLOT UTILIZATION:
   • 20250612-1100: IFA | ANS | HBF | MCT | IWW | RAY (6 judges)
   • 20250613-1400: WIY | IFA | AAF | AFO | MHA | HBF | MCT | MCU (8 judges, 3 parallel defenses)
   • 20250610-0900: AAF | MHA | EDN | MIR (4 judges, 1 defense)

⚖️  JUDGE WORKLOAD DISTRIBUTION:
   Total assignments: 175
   Average per judge: 8.3
   Individual workloads:
     🔴 AAF: 21 assignments (high workload)
     🔴 HBF: 14 assignments (high workload)
     🔴 IFA: 12 assignments (high workload)
     🟡 AFO: 9 assignments (medium workload)
     🟢 ANS: 8 assignments (balanced)
     🟢 WIY: 8 assignments (balanced)
     🟢 MHA: 8 assignments (balanced)
     [... 14 more judges with balanced workload ...]
     🟢 HLS: 1 assignments (low workload)

🎯 SCHEDULING PERFORMANCE:
   • Field and Time Matches: 29 students (60.4%)
   • Time Match Only: 19 students (39.6%)
   • Workload Balance Quality: Good (range 1-21, average 8.3)
   • Parallel Defense Utilization: 85% of time slots used efficiently

✅ Scheduling completed successfully!
Scheduled 48/51 students with excellent workload distribution
```

## Error Handling & Troubleshooting

The system provides comprehensive error handling and diagnostic information:

### Automatic Error Recovery

- **Missing Supervisors**: Continues with available supervisors, logs detailed warnings
- **Insufficient Judges**: Uses intelligent fallback mechanisms and "NONE" placeholders
- **No Available Time Slots**: Provides specific failure reasons and alternative suggestions
- **Invalid Data**: Validates CSV structure with detailed error messages

### Common Issues & Solutions

#### 1. **"No supervisors found"**
   - **Cause**: Supervisor names don't match judge database entries
   - **Solution**: Check supervisor name spelling and format consistency
   - **Debug**: Monitor supervisor matching logs for fuzzy match attempts

#### 2. **"No available time slots" (Field and Time Match)**
   - **Cause**: Expertise-matched judges have conflicting schedules
   - **System Response**: Automatically falls back to Time Match Only scheduling
   - **Outcome**: Still achieves successful scheduling with workload balancing

#### 3. **"No available time slots" (Time Match Only)**
   - **Cause**: All possible judge combinations are unavailable or over parallel defense limit
   - **Solutions**: 
     - Increase `max_parallel_defenses` in config.ini
     - Check judge availability data for errors
     - Consider expanding time slot options

#### 4. **High Workload Concentration**
   - **Detection**: System reports workload distribution with visual indicators
   - **Causes**: Limited judge availability or expertise constraints
   - **Monitoring**: Check 🔴/🟡/🟢 indicators in workload summary

#### 5. **Low Success Rate**
   - **Analysis**: System provides detailed failure reasons
   - **Common Causes**: Insufficient parallel defense limits, limited judge availability
   - **Solutions**: Adjust configuration parameters or expand judge pool

### Debug Information

The system provides extensive logging during execution:

#### Judge Loading & Validation
```
Loading availability data from: input/availability_cleaned.csv
Loaded availability data: 27 judges
✓ Found supervisor: IFA (Ilham Firman Ashari, S.Kom., M.T)
⚠ Supervisor 'Missing Name' not found
```

#### Scheduling Decision Process
```
🎯 Attempting field and time matching...
🔹 Selected ANS for field1 'MLTR' (workload: 0)
🔹 Selected HBF as fallback (workload: 0)
✗ No available time slots found for field-matched judges
⏰ Field matching failed, trying time-only matching...
🔹 Found better combo with total workload 0: HTA(0) + IWW(0)
✓ Selected best workload combo: HTA(0) + IWW(0) (total: 0)
```

#### Workload Distribution Tracking
```
⚖️  JUDGE WORKLOAD DISTRIBUTION:
   🔴 AAF: 21 assignments (high workload)
   🟡 AFO: 9 assignments (medium workload)
   🟢 ANS: 8 assignments (balanced)
```

### Performance Optimization

#### Configuration Tuning
- **`max_parallel_defenses`**: Balance between utilization and quality
- **`required_judges`**: Adjust based on institutional requirements
- **Judge pool expansion**: Add more judges to improve distribution

#### Workload Balance Monitoring
- Monitor visual indicators (🔴🟡🟢) in workload reports
- Target: Most judges in 🟢 (balanced) category
- Investigate: High concentration of 🔴 (overloaded) judges

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
