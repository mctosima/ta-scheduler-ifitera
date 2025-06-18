import pandas as pd
import numpy as np
import os

from config import read_config
from preprocessing import Dataframe
from scheduler_round import ThesisScheduler

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
    for df_name, df in dataframes.items():
        print(f"{df_name} headers: {list(df.columns)}")
    print("=" * 50)
    
    
    # Display summary of prepared data
    # print("Data preparation completed successfully!")
    # print(f"Availability data: {dataframes['availability'].shape}")
    # print(f"Request data: {dataframes['request'].shape}")
    # print(f"Lecturers: {dataframes['lecturers'].shape}")
    # print(f"Lecturer availability: {dataframes['lecturer_availability'].shape}")
    # print(f"Timeslots: {dataframes['timeslots'].shape}")
    print("Data preparation completed successfully!")

    # Initialize and run Round 1 scheduler
    print("=" * 50)
    print("STARTING ROUND 1: Field and Time Matching")
    print("=" * 50)
    scheduler_round1 = ThesisScheduler(dataframes, config)
    updated_dataframes = scheduler_round1.run()
    updated_timeslots = updated_dataframes['timeslots']
    updated_requests = updated_dataframes['request']
    
    print("\nRound 1 scheduling completed!")
    
    # Count unscheduled requests after Round 1
    unscheduled_count = 0
    for index, request_row in updated_requests.iterrows():
        current_status = request_row.get('status', '')
        if pd.isna(current_status) or current_status == '':
            unscheduled_count += 1
    
    print(f"Requests still unscheduled after Round 1: {unscheduled_count}")
    
    print("=" * 50)
    print("FINAL SCHEDULING SUMMARY")
    print("=" * 50)
    
    # Count final scheduling status - check for any assigned date_time
    scheduled_count = 0
    unscheduled_count = 0
    
    for index, request_row in updated_requests.iterrows():
        # Check if request has been assigned a date_time (not NaN/empty)
        date_time = request_row.get('date_time', '')
        if pd.notna(date_time) and date_time != '':
            scheduled_count += 1
        else:
            unscheduled_count += 1
    
    total_requests = len(updated_requests)
    
    print(f"Total requests: {total_requests}")
    print(f"Successfully scheduled: {scheduled_count}")
    print(f"Still unscheduled: {unscheduled_count}")
    print(f"Overall success rate: {(scheduled_count/total_requests*100):.1f}%")
    
    # Save updated requests to CSV
    output_path = os.path.join(os.getcwd(), "data", "output", config['out_fname'])
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the updated requests dataframe
    updated_requests.to_csv(output_path, index=False)
    print(f"Updated requests saved to: {output_path}")
    
    # Save updated timeslots to CSV
    timeslot_output_path = os.path.join(os.getcwd(), "data", "output", config['out_timeslot'])
    updated_timeslots.to_csv(timeslot_output_path, index=False)
    print(f"Updated timeslots saved to: {timeslot_output_path}")
    
    # Return all dataframes from the final state
    final_dataframes = {
        'timeslots': updated_timeslots,
        'request': updated_requests,
        'lecturers': updated_dataframes.get('lecturers', dataframes['lecturers']),
        'lecturer_availability': updated_dataframes.get('lecturer_availability', dataframes['lecturer_availability']),
        'availability': updated_dataframes.get('availability', dataframes['availability'])
    }
    
    return final_dataframes

if __name__ == "__main__":
    run_scheduler()