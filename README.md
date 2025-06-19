# Thesis Scheduling System (TA-Scheduler-IFITERA)

An intelligent thesis defense scheduling system that automatically assigns examiners and schedules thesis defense sessions based on lecturer availability and expertise matching.

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [Input Files](#input-files)
- [Output Files](#output-files)
- [Scheduling Algorithm](#scheduling-algorithm)
- [Configuration](#configuration)
- [Development Workplan](#development-workplan)

## Overview

The Thesis Scheduling System is designed to automate the complex task of scheduling thesis defense sessions in academic institutions. The system considers multiple factors including:

- Lecturer availability and time constraints
- Academic field expertise matching
- Existing supervisor and examiner assignments
- Capstone project group requirements
- Time slot duration requirements
- Parallel event scheduling capabilities

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ta-scheduler-ifitera
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install pandas numpy configparser
   ```

4. **Create directory structure:**
   ```bash
   mkdir -p data/input data/output
   ```

5. **Prepare input files:**
   - Place your availability CSV file in `data/input/`
   - Place your request CSV file in `data/input/`
   - Update `config.ini` with correct file names

## Usage

### Basic Usage

1. **Configure the system:**
   Edit `config.ini` to specify your input files and parameters:
   ```ini
   [FILES]
   avail_fname = your_availability_file.csv
   req_fname = your_request_file.csv
   ```

2. **Run the scheduler:**
   ```bash
   python src/main.py
   ```

3. **Check results:**
   Output files will be generated in `data/output/` directory.

### Command Line Execution
```bash
cd /path/to/ta-scheduler-ifitera
python src/main.py
```

## Input Files

### 1. Availability File (`avail3.csv`)

**Format:** CSV file with lecturer availability information

**Required columns:**
- `nama_dosen`: Lecturer name
- `kode_dosen`: Lecturer code/ID
- `sk_1`, `sk_2`, `sk_3`, `sk_4`: Expertise fields (skill areas)
- Time slot columns: `YYYYMMDD_HHMM` format (e.g., `20240315_0900`)

**Time slot values:**
- `TRUE`/`True`/`true`: Available
- `FALSE`/`False`/`false` or empty: Not available

**Example structure:**
```csv
nama_dosen,kode_dosen,sk_1,sk_2,sk_3,sk_4,20240315_0900,20240315_1000,...
Dr. John Doe,JD001,Machine Learning,Data Science,AI,NLP,TRUE,FALSE,...
Prof. Jane Smith,JS002,Software Engineering,Web Development,,,TRUE,TRUE,...
```

### 2. Request File (`req.csv`)

**Format:** CSV file with thesis defense requests

**Required columns:**
- `nim`: Student ID number
- `nama`: Student name
- `capstone_code`: Group code for capstone projects (empty for individual)
- `spv_1`: First supervisor code
- `spv_2`: Second supervisor code (optional)
- `examiner_1`: First examiner code (usually empty - to be assigned)
- `examiner_2`: Second examiner code (usually empty - to be assigned)
- `field_1`: Primary research field
- `field_2`: Secondary research field
- `status`: Initial status (usually empty)

**Example structure:**
```csv
nim,nama,capstone_code,spv_1,spv_2,examiner_1,examiner_2,field_1,field_2,status
12345678,Alice Johnson,A,JD001,JS002,,,Machine Learning,Data Science,
87654321,Bob Smith,,JD001,,,,Software Engineering,Web Development,
```

## Output Files

The system generates three main output files:

### 1. Final Output (`final_output2.csv`)
Contains scheduled thesis defense information with:
- Student details with assigned date/time
- Complete examiner assignments
- Indonesian-formatted dates and times
- Status indicating match quality

### 2. Timeslot Schedule (`final_timeslot2.csv`)
Shows the complete schedule with:
- Date and time slots
- Parallel event assignments
- Slot occupancy information

### 3. Lecturer Schedule (`final_lectureschedule2.csv`)
Displays lecturer workload with:
- Lecturer information
- Number of assignments
- Detailed schedule in Indonesian format

## Scheduling Algorithm

The system uses a sophisticated two-round scheduling algorithm:

### Round 1: Expertise-Based Matching

1. **Field Filtering:**
   - Filters lecturers based on expertise matching (`field_1` or `field_2`)
   - Removes already assigned supervisors from examiner pool

2. **Availability Analysis:**
   - Identifies common time slots between assigned actors (supervisors)
   - Considers required duration (individual: 2 slots, capstone: 3-5 slots)
   - Ensures consecutive time slot availability

3. **Lecturer Ranking:**
   Uses multi-criteria scoring system:
   - **Criteria A:** Schedule compatibility with assigned actors
   - **Criteria B:** Current workload (fewer assignments = higher score)
   - **Criteria C:** Overall availability (less available = higher priority)

4. **Assignment Process:**
   - Assigns top-ranked examiners
   - Updates timeslot occupancy
   - Records lecturer assignments

### Round 2: Availability-Only Matching

For unscheduled requests from Round 1:
- Removes expertise filtering requirement
- Uses same ranking criteria focusing on availability
- Marks assignments as "Time Match Only"

### Scheduling Logic Details

**Time Slot Management:**
- 30-minute intervals for precise scheduling
- Automatic consecutive slot allocation
- Parallel event support (configurable)

**Capstone Project Handling:**
- Groups students by `capstone_code`
- Ensures consistent examiner assignment across group
- Adjusts duration based on group size (2-4 students)

**Conflict Resolution:**
- Prevents double-booking of lecturers
- Validates time slot availability
- Maintains data integrity across related requests

## Configuration

The `config.ini` file contains all configurable parameters:

```ini
[FILES]
# Input files (placed in data/input/)
avail_fname = avail3.csv
req_fname = req3.csv

# Output files (generated in data/output/)
out_fname = final_output2.csv
out_timeslot = final_timeslot2.csv
out_lectureschedule = final_lectureschedule2.csv

[PARAMETERS]
# Number of parallel events per time slot
parallel_event = 1

# Default time slots for individual thesis (30-minute slots)
default_timeslot = 2

# Capstone project durations based on group size
capstone_duration_2 = 3  # 2 students = 3 slots (90 minutes)
capstone_duration_3 = 4  # 3 students = 4 slots (120 minutes)
capstone_duration_4 = 5  # 4 students = 5 slots (150 minutes)

# Time slot duration in minutes
time_slot_dur = 30
```

## Development Workplan

### Completed Features ✅
- [x] Core scheduling algorithm with two-round approach
- [x] Multi-criteria lecturer ranking system
- [x] Capstone project group handling
- [x] CSV input/output processing
- [x] Indonesian date/time formatting
- [x] Comprehensive data validation
- [x] Statistical reporting
- [x] Configuration management
- [x] Error handling and logging

### Planned Features 🚧

#### Phase 1: Web Interface Development
- [ ] **Static Web Application**
  - [ ] HTML/CSS/JavaScript frontend
  - [ ] File upload interface for CSV inputs
  - [ ] Real-time scheduling progress display
  - [ ] Interactive schedule visualization
  - [ ] Download links for output files

#### Phase 2: Enhanced Web Features
- [ ] **Advanced Web Interface**
  - [ ] Drag-and-drop file upload
  - [ ] Data validation feedback
  - [ ] Schedule editing capabilities
  - [ ] Conflict resolution interface
  - [ ] Export options (PDF, Excel)

#### Phase 3: Deployment
- [ ] **Production Deployment**
  - [ ] Cloud hosting setup (AWS/GCP/Azure)
  - [ ] Domain configuration
  - [ ] SSL certificate installation
  - [ ] Performance optimization
  - [ ] Monitoring and logging setup

#### Phase 4: Advanced Features
- [ ] **System Enhancements**
  - [ ] Database integration
  - [ ] User authentication system
  - [ ] API development for integration
  - [ ] Mobile-responsive design
  - [ ] Automated email notifications

### Technical Architecture (Planned)

**Frontend:**
- HTML5/CSS3/JavaScript
- Bootstrap for responsive design
- Chart.js for schedule visualization

**Backend:**
- Python Flask/Django web framework
- RESTful API design
- File processing endpoints

**Deployment:**
- Docker containerization
- Cloud platform deployment
- CI/CD pipeline setup

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please:
1. Check the documentation above
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem

## System Requirements

- **Python:** 3.7+
- **Memory:** 512MB RAM minimum
- **Storage:** 50MB free space
- **OS:** Windows, macOS, or Linux

## Troubleshooting

**Common Issues:**

1. **File Not Found Error:**
   - Ensure input files are in `data/input/` directory
   - Check file names in `config.ini`

2. **Permission Errors:**
   - Ensure write permissions for `data/output/` directory

3. **Import Errors:**
   - Verify all dependencies are installed
   - Check Python version compatibility

4. **Data Format Issues:**
   - Validate CSV file structure
   - Ensure proper encoding (UTF-8)
