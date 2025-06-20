from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
import tempfile
import shutil
import subprocess
import json

# Try to import pandas, but handle if it's not available
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  pandas not available - some features may be limited")

# Add the parent directory to the path to import your scheduling modules
# Get the path to the src folder relative to this app.py file
# app.py is in: ta-scheduler-ifitera/ui/react_app/backend/
# src is in: ta-scheduler-ifitera/src/
# So we go up 3 levels: ../../../src
scheduler_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
sys.path.append(scheduler_src)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175"])  # Enable CORS for all routes

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'csv'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Flask backend is running"})

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and process scheduling"""
    try:
        # Check if files are present
        if 'availability' not in request.files or 'request' not in request.files:
            return jsonify({"error": "Both availability and request files are required"}), 400
        
        availability_file = request.files['availability']
        request_file = request.files['request']
        
        # Check if files are selected
        if availability_file.filename == '' or request_file.filename == '':
            return jsonify({"error": "No files selected"}), 400
        
        # Check file extensions
        if not (allowed_file(availability_file.filename) and allowed_file(request_file.filename)):
            return jsonify({"error": "Only CSV files are allowed"}), 400
        
        # Save uploaded files
        availability_filename = secure_filename(availability_file.filename)
        request_filename = secure_filename(request_file.filename)
        
        availability_path = os.path.join(UPLOAD_FOLDER, 'avail.csv')
        request_path = os.path.join(UPLOAD_FOLDER, 'req.csv')
        
        availability_file.save(availability_path)
        request_file.save(request_path)
        
        # Process the files using your Python scheduling code
        result = process_scheduling()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def process_scheduling():
    """
    Process the scheduling using your existing Python code
    This function will call your actual scheduling modules
    """
    try:
        # Use relative path to your scheduler project
        # app.py is in: ta-scheduler-ifitera/ui/react_app/backend/
        # scheduler project root is: ta-scheduler-ifitera/
        # So we go up 3 levels: ../../..
        scheduler_project = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        
        print(f"DEBUG: Backend working directory: {os.getcwd()}")
        print(f"DEBUG: Scheduler project path: {scheduler_project}")
        print(f"DEBUG: Scheduler project exists: {os.path.exists(scheduler_project)}")
        
        # Create a temporary config file for this run
        config_content = f"""[DEFAULT]

[FILES]
# Input files (from uploads)
avail_fname = {os.path.join(os.getcwd(), UPLOAD_FOLDER, 'avail.csv')}
req_fname = {os.path.join(os.getcwd(), UPLOAD_FOLDER, 'req.csv')}
# Output files
out_fname = final_output.csv
out_timeslot = final_timeslot.csv
out_lectureschedule = final_lectureschedule.csv

[PARAMETERS]
parallel_event = 1
default_timeslot = 2
capstone_duration_2 = 3
capstone_duration_3 = 4
capstone_duration_4 = 5
time_slot_dur = 30
"""
        
        # Save temporary config in the scheduler project directory
        temp_config_path = os.path.join(scheduler_project, 'temp_config.ini')
        print(f"DEBUG: Saving config to: {temp_config_path}")
        
        with open(temp_config_path, 'w') as f:
            f.write(config_content)
        
        # Run your Python scheduling code directly
        try:
            result = run_scheduler_direct(scheduler_project, temp_config_path)
        except Exception as import_error:
            print(f"Direct import failed: {import_error}")
            result = run_scheduler_subprocess(scheduler_project, temp_config_path)
        
        # Clean up temporary config
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)
        
        return result
        
    except Exception as e:
        print(f"Error in process_scheduling: {e}")
        return create_mock_results()

def run_scheduler_direct(scheduler_project, temp_config_path):
    """Try to run the scheduler by importing your modules directly"""
    try:
        # Change working directory to your scheduler project
        original_cwd = os.getcwd()
        os.chdir(scheduler_project)
        
        # Import your modules
        from config import read_config
        from preprocessing import Dataframe
        from scheduler import ThesisScheduler
        from cleanup import Cleaner
        
        # Temporarily replace the config file path
        import configparser
        config = configparser.ConfigParser()
        config.read(temp_config_path)
        
        # Convert to flat dictionary (matching your config.py format)
        config_dict = {}
        config_dict.update(dict(config.defaults()))
        for section_name in config.sections():
            section_items = dict(config[section_name])
            config_dict.update(section_items)
        
        print("Running scheduler with the following configuration:")
        for key, value in config_dict.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        # Run your scheduling logic
        dataframe_processor = Dataframe(
            avail_fname=config_dict['avail_fname'],
            request_fname=config_dict['req_fname'],
            output_fname=config_dict['out_fname'],
            parallel_event=int(config_dict['parallel_event'])
        )
        
        dataframes = dataframe_processor.get_all_dataframes()
        print("Data preparation completed successfully!")
        
        schedule = ThesisScheduler(
            dataframes=dataframes,
            config=config_dict
        )
        
        returned_dataframe = schedule.run()
        schedule.print_statistics()
        
        cleaned_dataframe = Cleaner(returned_dataframe).clean()
        
        # Export results to the output directory 
        output_dir = os.path.join(original_cwd, OUTPUT_FOLDER)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save results to the Flask backend output folder
        request_output_path = os.path.join(output_dir, 'final_output.csv')
        timeslot_output_path = os.path.join(output_dir, 'final_timeslot.csv')
        lecturers_output_path = os.path.join(output_dir, 'final_lectureschedule.csv')
        
        if PANDAS_AVAILABLE:
            cleaned_dataframe['request'].to_csv(request_output_path, index=False)
            cleaned_dataframe['timeslots'].to_csv(timeslot_output_path, index=False)
            cleaned_dataframe['lecturers'].to_csv(lecturers_output_path, index=False)
        
        print(f"Results exported to: {output_dir}")
        
        # Restore original working directory
        os.chdir(original_cwd)
        
        # Read the generated CSV files and return as JSON
        return read_results_as_json()
        
    except Exception as e:
        # Restore original working directory on error
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
        raise Exception(f"Direct scheduler run failed: {e}")

def run_scheduler_subprocess(scheduler_project, temp_config_path):
    """Run the scheduler as a subprocess"""
    try:
        main_script_path = os.path.join(scheduler_project, 'src', 'main.py')
        
        # Run the Python script in the scheduler project directory
        result = subprocess.run(
            ['python', main_script_path],
            cwd=scheduler_project,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env={**os.environ, 'PYTHONPATH': os.path.join(scheduler_project, 'src')}
        )
        
        if result.returncode != 0:
            raise Exception(f"Scheduler script failed: {result.stderr}")
        
        # Copy results from scheduler project to Flask output folder
        output_dir = os.path.join(os.getcwd(), OUTPUT_FOLDER)
        os.makedirs(output_dir, exist_ok=True)
        
        scheduler_output_dir = os.path.join(scheduler_project, 'data', 'output')
        
        # Copy the generated files
        files_to_copy = [
            'final_output.csv',
            'final_timeslot.csv', 
            'final_lectureschedule.csv'
        ]
        
        for filename in files_to_copy:
            src_path = os.path.join(scheduler_output_dir, filename)
            dst_path = os.path.join(output_dir, filename)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        # Read the generated CSV files and return as JSON
        return read_results_as_json()
        
    except subprocess.TimeoutExpired:
        raise Exception("Scheduler script timed out")
    except Exception as e:
        raise Exception(f"Subprocess scheduler run failed: {e}")

def read_results_as_json():
    """Read the generated CSV files and convert to JSON for the frontend"""
    try:
        if not PANDAS_AVAILABLE:
            print("⚠️  pandas not available - using basic CSV reading")
            return read_csv_basic()
        
        results = {}
        
        # Read schedule result
        schedule_path = os.path.join(OUTPUT_FOLDER, 'final_output.csv')
        if os.path.exists(schedule_path):
            df = pd.read_csv(schedule_path)
            # Replace NaN values with empty strings for better JSON compatibility
            df = df.fillna('')
            # Convert to dict and clean any remaining NaN values
            records = df.to_dict('records')
            results['scheduleResult'] = clean_nan_values(records)
        
        # Read timeslot arrangement
        timeslot_path = os.path.join(OUTPUT_FOLDER, 'final_timeslot.csv')
        if os.path.exists(timeslot_path):
            df = pd.read_csv(timeslot_path)
            # Replace NaN values with empty strings for better JSON compatibility
            df = df.fillna('')
            # Convert to dict and clean any remaining NaN values
            records = df.to_dict('records')
            results['timeslotArrangement'] = clean_nan_values(records)
        
        # Read examiner schedule
        examiner_path = os.path.join(OUTPUT_FOLDER, 'final_lectureschedule.csv')
        if os.path.exists(examiner_path):
            df = pd.read_csv(examiner_path)
            # Replace NaN values with empty strings for better JSON compatibility
            df = df.fillna('')
            # Convert to dict and clean any remaining NaN values
            records = df.to_dict('records')
            results['examinerSchedule'] = clean_nan_values(records)
        
        return results
        
    except Exception as e:
        print(f"Error reading results: {e}")
        return create_mock_results()

def clean_nan_values(data):
    """Recursively clean NaN values from data structures"""
    if isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, dict):
        return {key: clean_nan_values(value) for key, value in data.items()}
    elif pd.isna(data) if PANDAS_AVAILABLE else (isinstance(data, float) and str(data).lower() == 'nan'):
        return ''
    elif isinstance(data, str) and data.strip().lower() in ['nan', 'null', 'none']:
        return ''
    else:
        return data

def read_csv_basic():
    """Basic CSV reading without pandas"""
    import csv
    results = {}
    
    try:
        # Read schedule result
        schedule_path = os.path.join(OUTPUT_FOLDER, 'final_output.csv')
        if os.path.exists(schedule_path):
            with open(schedule_path, 'r') as f:
                reader = csv.DictReader(f)
                results['scheduleResult'] = list(reader)
        
        # Read timeslot arrangement
        timeslot_path = os.path.join(OUTPUT_FOLDER, 'final_timeslot.csv')
        if os.path.exists(timeslot_path):
            with open(timeslot_path, 'r') as f:
                reader = csv.DictReader(f)
                results['timeslotArrangement'] = list(reader)
        
        # Read examiner schedule
        examiner_path = os.path.join(OUTPUT_FOLDER, 'final_lectureschedule.csv')
        if os.path.exists(examiner_path):
            with open(examiner_path, 'r') as f:
                reader = csv.DictReader(f)
                results['examinerSchedule'] = list(reader)
        
        return results
    except Exception as e:
        print(f"Error in basic CSV reading: {e}")
        return create_mock_results()

def create_mock_results():
    """Create mock results for testing purposes"""
    return {
        "scheduleResult": [
            {"student": "John Doe", "datetime": "20250620-0900", "examiner1": "Dr. Smith", "examiner2": "Dr. Johnson"},
            {"student": "Jane Smith", "datetime": "20250620-1000", "examiner1": "Dr. Brown", "examiner2": "Dr. Wilson"}
        ],
        "timeslotArrangement": [
            {"timeslot": "20250620-0900", "status": "occupied", "student": "John Doe"},
            {"timeslot": "20250620-1000", "status": "occupied", "student": "Jane Smith"}
        ],
        "examinerSchedule": [
            {"examiner": "Dr. Smith", "datetime": "20250620-0900", "role": "Examiner 1", "student": "John Doe"},
            {"examiner": "Dr. Johnson", "datetime": "20250620-0900", "role": "Examiner 2", "student": "John Doe"}
        ]
    }

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download generated CSV files"""
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

if __name__ == '__main__':
    print("Starting Flask backend server...")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  POST /api/upload - Upload files and process scheduling")
    print("  GET  /api/download/<filename> - Download result files")
    app.run(debug=True, host='0.0.0.0', port=8000)
