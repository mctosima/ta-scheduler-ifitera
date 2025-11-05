import pandas as pd
import numpy as np
import random
import os
from pathlib import Path

from config import read_config
from preprocessing import Dataframe
# from scheduler_round import ThesisScheduler
from scheduler import ThesisScheduler
from cleanup import Cleaner
from csv_fixer import preprocess_scheduler_inputs

# Set random seed for reproducibility
RANDOM_SEED = 46
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def run_scheduler():
    # read the `config.ini` file
    config = read_config()
    print("Running scheduler with the following configuration:")
    for key, value in config.items():
        print(f"{key}: {value}")
    print("=" * 50)
    
    # STEP 1: Preprocess CSV files (fix breaks and normalize format)
    print("\n" + "="*60)
    print("STEP 1: PREPROCESSING CSV FILES")
    print("="*60 + "\n")
    
    req_path = os.path.join(os.getcwd(), "data", "input", config['req_fname'])
    avail_path = os.path.join(os.getcwd(), "data", "input", config['avail_fname'])
    
    # Check if files need preprocessing
    # If a _normalized.csv already exists and is newer than the source, skip preprocessing
    req_normalized_path = req_path.replace('.csv', '_normalized.csv')
    needs_preprocessing = True
    
    if Path(req_normalized_path).exists():
        # Check if normalized file is newer than source
        if Path(req_normalized_path).stat().st_mtime > Path(req_path).stat().st_mtime:
            print(f"Normalized file already exists and is up-to-date: {Path(req_normalized_path).name}")
            print(f"Skipping preprocessing. Delete {Path(req_normalized_path).name} to force reprocessing.\n")
            needs_preprocessing = False
    
    if needs_preprocessing:
        try:
            normalized_req, fixed_avail = preprocess_scheduler_inputs(req_path, avail_path)
            # Update config to use normalized file
            config['req_fname'] = Path(normalized_req).name
            print(f"Preprocessing complete. Using normalized file: {config['req_fname']}\n")
        except Exception as e:
            print(f"Warning: Preprocessing failed ({e}). Attempting to use original files...")
            print(f"If you encounter CSV parsing errors, please run: python src/csv_fixer.py {req_path} {avail_path}\n")
    else:
        # Use existing normalized file
        config['req_fname'] = Path(req_normalized_path).name
    
    print("="*60 + "\n")
    
    # STEP 2: Prepare the dataframe
    print("STEP 2: LOADING DATA")
    print("="*60 + "\n")
        
    dataframe_processor = Dataframe(
        avail_fname=config['avail_fname'],
        request_fname=config['req_fname'],
        output_fname=config['out_fname'],
        parallel_event=int(config['parallel_event'])
    )
    
    # Get all prepared dataframes
    dataframes = dataframe_processor.get_all_dataframes()
    
    # Print headers for debugging
    # for df_name, df in dataframes.items():
    #     print(f"{df_name} headers: {list(df.columns)}")
    # print("=" * 50)
    
    
    # Display summary of prepared data
    print(f"✓ Data loaded successfully!")
    print(f"  - Requests: {len(dataframes['request'])} entries")
    print(f"  - Lecturers: {len(dataframes['lecturers'])} available")
    print(f"  - Timeslots: {len(dataframes['timeslots'])} slots")
    print()
    
    print("="*60)
    print("STEP 3: SCHEDULING")
    print("="*60 + "\n")
    
    schedule = ThesisScheduler(
        dataframes=dataframes,
        config=config,
        round2=True  # Enable round 2 and round 3 scheduling
    )
    
    returned_dataframe = schedule.run()
    
    print("\n" + "="*60)
    print("STEP 4: POST-PROCESSING")
    print("="*60 + "\n")
    
    # Print statistics before cleaning (when num_assignment column still exists)
    schedule.print_statistics()
    
    cleaned_dataframe = Cleaner(returned_dataframe, config).clean()
    
    print("\n" + "="*60)
    print("STEP 5: EXPORTING RESULTS")
    print("="*60 + "\n")
    
    export_results(cleaned_dataframe['request'], cleaned_dataframe['timeslots'], cleaned_dataframe['lecturers'], config)
    
    # Verify no duplicates in final output
    duplicate_check = cleaned_dataframe['request']['nim'].duplicated()
    if duplicate_check.any():
        duplicate_nims = cleaned_dataframe['request'][duplicate_check]['nim'].tolist()
        print(f"\n⚠️ WARNING: Found {len(duplicate_nims)} duplicate(s) in final output: {duplicate_nims}")
    else:
        print(f"\n✓ Verification: No duplicates in final output ({len(cleaned_dataframe['request'])} unique entries)")
    
    print("\n" + "="*60)
    print("✓ SCHEDULING COMPLETE!")
    print("="*60)
    print(f"\nOutput files saved to: data/output/")
    print(f"  - {config['out_fname']}")
    print(f"  - {config['out_timeslot']}")
    print(f"  - {config['out_lectureschedule']}")
    print(f"\nTo validate for conflicts, run:")
    print(f"  python validate_timeslots.py data/output/{config['out_timeslot']} {config['parallel_event']}")
    print()

    

def export_results(request_df, timeslot_df, lecturers_df, config):
    """Export the updated request, timeslot, and lecturers dataframes to CSV files."""
    try:
        # Export request dataframe
        request_output_path = config['out_fname']
        request_output_path = os.path.join(os.getcwd(), "data", "output", request_output_path)
        request_df.to_csv(request_output_path, index=False)
        print(f"Request results exported to: {request_output_path}")
        
        # Export timeslot dataframe
        timeslot_output_path = config['out_timeslot']
        timeslot_output_path = os.path.join(os.getcwd(), "data", "output", timeslot_output_path)
        timeslot_df.to_csv(timeslot_output_path, index=False)
        print(f"Timeslot results exported to: {timeslot_output_path}")
        
        # Export lecturers dataframe
        lecturers_output_path = config['out_lectureschedule']
        lecturers_output_path = os.path.join(os.getcwd(), "data", "output", lecturers_output_path)
        lecturers_df.to_csv(lecturers_output_path, index=False)
        print(f"Lecturers results exported to: {lecturers_output_path}")
        
    except Exception as e:
        print(f"Error exporting results: {e}")


if __name__ == "__main__":
    run_scheduler()