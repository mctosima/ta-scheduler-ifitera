import pandas as pd
import numpy as np
import random
import os

from config import read_config
from preprocessing import Dataframe
# from scheduler_round import ThesisScheduler
from scheduler import ThesisScheduler
from cleanup import Cleaner

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
        
    # Prepare the dataframe
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
    # print("Data preparation completed successfully!")
    # print(f"Availability data: {dataframes['availability'].shape}")
    # print(f"Request data: {dataframes['request'].shape}")
    # print(f"Lecturers: {dataframes['lecturers'].shape}")
    # print(f"Lecturer availability: {dataframes['lecturer_availability'].shape}")
    # print(f"Timeslots: {dataframes['timeslots'].shape}")
    print("Data preparation completed successfully!")
    
    schedule = ThesisScheduler(
        dataframes=dataframes,
        config=config,
        # round2=False
    )
    
    returned_dataframe = schedule.run()
    
    # Print statistics before cleaning (when num_assignment column still exists)
    schedule.print_statistics()
    
    cleaned_dataframe = Cleaner(returned_dataframe, config).clean()
    
    export_results(cleaned_dataframe['request'], cleaned_dataframe['timeslots'], cleaned_dataframe['lecturers'], config)

    

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