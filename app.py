from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import json
from pathlib import Path
import subprocess
import threading
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/input'
app.config['OUTPUT_FOLDER'] = 'data/output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store the current job status
job_status = {
    'running': False,
    'progress': '',
    'output': [],
    'error': None,
    'completed': False
}

def read_config():
    """Read current configuration from config.ini"""
    config = {}
    current_section = None
    
    with open('config.ini', 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
            elif '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config

def write_config(config_data):
    """Write configuration to config.ini"""
    config_template = """[DEFAULT]

[FILES]
# Default input files
# NOTE: CSV preprocessing (fixing breaks and normalizing format) is now automatic!
# The scheduler will automatically create req_XXX_normalized.csv if needed.
avail_fname = {avail_fname}
req_fname = {req_fname}
# Default output files (final two-round results)
out_fname = {out_fname}
out_timeslot = {out_timeslot}
out_lectureschedule = {out_lectureschedule}

[PARAMETERS]
parallel_event = {parallel_event}
default_timeslot = {default_timeslot}
# Capstone duration mapping (number_of_students: time_slots)
capstone_duration_2 = {capstone_duration_2}
capstone_duration_3 = {capstone_duration_3}
capstone_duration_4 = {capstone_duration_4}

default_timeslot_sidang = {default_timeslot_sidang}
capstone_duration_sidang_2 = {capstone_duration_sidang_2}
capstone_duration_sidang_3 = {capstone_duration_sidang_3}
capstone_duration_sidang_4 = {capstone_duration_sidang_4}

# time slot duration in minutes
time_slot_dur = {time_slot_dur}
"""
    
    with open('config.ini', 'w') as f:
        f.write(config_template.format(**config_data))

@app.route('/')
def index():
    """Main page"""
    config = read_config()
    
    # Get list of available input files
    input_files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        input_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                      if f.endswith('.csv') and not f.endswith('_normalized.csv')]
    
    # Get list of output files
    output_files = []
    if os.path.exists(app.config['OUTPUT_FOLDER']):
        output_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) 
                       if f.endswith('.csv')]
    
    return render_template('index.html', 
                          config=config, 
                          input_files=input_files,
                          output_files=output_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and file.filename.endswith('.csv'):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'success': False, 'error': 'Invalid file type. Only CSV files allowed.'})

@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        config_data = request.json
        write_config(config_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/run', methods=['POST'])
def run_scheduler():
    """Run the scheduler"""
    global job_status
    
    if job_status['running']:
        return jsonify({'success': False, 'error': 'Scheduler is already running'})
    
    # Reset job status
    job_status = {
        'running': True,
        'progress': 'Starting scheduler...',
        'output': [],
        'error': None,
        'completed': False
    }
    
    # Run scheduler in a separate thread
    thread = threading.Thread(target=execute_scheduler)
    thread.start()
    
    return jsonify({'success': True})

def execute_scheduler():
    """Execute the scheduler script"""
    global job_status
    
    try:
        # Run the scheduler
        process = subprocess.Popen(
            ['python', 'src/main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Read output line by line
        for line in process.stdout:
            line = line.strip()
            if line:
                job_status['output'].append(line)
                job_status['progress'] = line
        
        process.wait()
        
        if process.returncode == 0:
            job_status['completed'] = True
            job_status['progress'] = 'Scheduler completed successfully!'
        else:
            job_status['error'] = f'Scheduler exited with code {process.returncode}'
            job_status['progress'] = 'Scheduler failed'
        
    except Exception as e:
        job_status['error'] = str(e)
        job_status['progress'] = f'Error: {str(e)}'
    
    finally:
        job_status['running'] = False

@app.route('/status')
def get_status():
    """Get current job status"""
    return jsonify(job_status)

@app.route('/download/<filename>')
def download_file(filename):
    """Download output file"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'success': False, 'error': 'File not found'})

@app.route('/validate/<filename>')
def validate_timeslots(filename):
    """Validate timeslots for conflicts"""
    try:
        # Read config to get parallel_event
        config = read_config()
        parallel_event = config.get('parallel_event', '1')
        
        # Run validation script
        result = subprocess.run(
            ['python', 'validate_timeslots.py', 
             os.path.join(app.config['OUTPUT_FOLDER'], filename),
             parallel_event],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    print("\n" + "="*60)
    print("TA SCHEDULER WEB INTERFACE")
    print("="*60)
    print("\nStarting server...")
    print("Open your browser and go to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
