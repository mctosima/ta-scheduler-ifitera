#!/usr/bin/env python3
"""
Script to clean up the TA availability CSV file with merged cells.
This script will:
1. Parse the CSV with merged cell headers
2. Create proper column names for each time slot
3. Consolidate sub-specialization fields
4. Generate a cleaned CSV with proper structure
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os

def clean_availability_csv(input_file_path, output_file_path):
    """
    Clean the availability CSV file with merged cells and generate a new cleaned CSV.
    
    Args:
        input_file_path (str): Path to the input CSV file
        output_file_path (str): Path to save the cleaned CSV file
    """
    
    # Read the CSV file
    print(f"Reading CSV file: {input_file_path}")
    df = pd.read_csv(input_file_path)
    
    # Get the header rows (first two rows contain the structure)
    header_row1 = df.columns.tolist()  # Dates
    header_row2 = df.iloc[0].tolist()  # Time slots
    
    # Extract date information from the first header row
    dates = []
    current_date = None
    
    for col in header_row1:
        if "June 2025" in str(col):
            current_date = col
        dates.append(current_date)
    
    # Create proper column names
    new_columns = []
    
    # First few columns are special (name and sub-specializations)
    new_columns.append("Nama_Dosen")
    new_columns.append("Sub_Keilmuan_1")
    new_columns.append("Sub_Keilmuan_2") 
    new_columns.append("Sub_Keilmuan_3")
    new_columns.append("Sub_Keilmuan_4")
    
    # Create time slot columns
    for i, (date, time) in enumerate(zip(dates[5:], header_row2[5:])):
        if date and time:
            # Clean up the date string
            clean_date = date.replace(",", "").replace(" ", "_")
            # Create column name like "Tuesday_10_June_2025_08:00"
            new_columns.append(f"{clean_date}_{time}")
        else:
            new_columns.append(f"Unknown_Col_{i+5}")
    
    # Remove the time slot row (first row of data)
    cleaned_df = df.iloc[1:].copy()
    
    # Assign new column names
    cleaned_df.columns = new_columns[:len(cleaned_df.columns)]
    
    # Clean up the data
    cleaned_df = cleaned_df.reset_index(drop=True)
    
    # Remove rows where Nama_Dosen is empty or NaN
    cleaned_df = cleaned_df[cleaned_df['Nama_Dosen'].notna()]
    cleaned_df = cleaned_df[cleaned_df['Nama_Dosen'] != '']
    
    # Consolidate sub-specialization columns into a single column
    def consolidate_sub_specializations(row):
        sub_specs = []
        for i in range(1, 5):  # Sub_Keilmuan_1 to Sub_Keilmuan_4
            col_name = f"Sub_Keilmuan_{i}"
            if col_name in row and pd.notna(row[col_name]) and row[col_name] != '':
                sub_specs.append(str(row[col_name]))
        return "; ".join(sub_specs) if sub_specs else ""
    
    cleaned_df['Sub_Keilmuan'] = cleaned_df.apply(consolidate_sub_specializations, axis=1)
    
    # Drop the individual sub-specialization columns
    cols_to_drop = ['Sub_Keilmuan_1', 'Sub_Keilmuan_2', 'Sub_Keilmuan_3', 'Sub_Keilmuan_4']
    cleaned_df = cleaned_df.drop(columns=cols_to_drop)
    
    # Convert TRUE/FALSE values to boolean
    for col in cleaned_df.columns:
        if col not in ['Nama_Dosen', 'Sub_Keilmuan']:
            cleaned_df[col] = cleaned_df[col].map({'TRUE': True, 'FALSE': False, True: True, False: False})
    
    # Save the cleaned CSV
    print(f"Saving cleaned CSV to: {output_file_path}")
    cleaned_df.to_csv(output_file_path, index=False)
    
    # Print summary
    print(f"\nCleaning completed!")
    print(f"Original shape: {df.shape}")
    print(f"Cleaned shape: {cleaned_df.shape}")
    print(f"Number of lecturers: {len(cleaned_df)}")
    print(f"Number of time slots: {len([col for col in cleaned_df.columns if col not in ['Nama_Dosen', 'Sub_Keilmuan']])}")
    
    return cleaned_df

def create_summary_report(cleaned_df, output_dir):
    """
    Create a summary report of the availability data.
    
    Args:
        cleaned_df (pd.DataFrame): The cleaned DataFrame
        output_dir (str): Directory to save the report
    """
    
    report_path = Path(output_dir) / "availability_summary.txt"
    
    with open(report_path, 'w') as f:
        f.write("TA AVAILABILITY SUMMARY REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total number of lecturers: {len(cleaned_df)}\n")
        f.write(f"Total number of time slots: {len([col for col in cleaned_df.columns if col not in ['Nama_Dosen', 'Sub_Keilmuan']])}\n\n")
        
        f.write("LECTURERS AND THEIR SPECIALIZATIONS:\n")
        f.write("-" * 40 + "\n")
        for _, row in cleaned_df.iterrows():
            f.write(f"{row['Nama_Dosen']}\n")
            if row['Sub_Keilmuan']:
                f.write(f"  Specializations: {row['Sub_Keilmuan']}\n")
            else:
                f.write("  Specializations: None specified\n")
            f.write("\n")
        
        # Calculate availability statistics
        time_cols = [col for col in cleaned_df.columns if col not in ['Nama_Dosen', 'Sub_Keilmuan']]
        availability_counts = {}
        
        for col in time_cols:
            available_count = cleaned_df[col].sum()
            availability_counts[col] = available_count
        
        f.write("TIME SLOT AVAILABILITY (Number of available lecturers):\n")
        f.write("-" * 50 + "\n")
        for time_slot, count in sorted(availability_counts.items()):
            f.write(f"{time_slot}: {count} lecturers available\n")
    
    print(f"Summary report saved to: {report_path}")

def main():
    """Main function to run the CSV cleaning process."""
    
    # File paths
    input_file = os.path.join(os.getcwd(), "avail_20250610.csv")
    output_dir = os.path.join(os.getcwd())
    input_filename = Path(input_file).stem
    output_file = Path(output_dir) / f"{input_filename}_clean.csv"
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Clean the CSV
        cleaned_df = clean_availability_csv(input_file, output_file)
        
        # Create summary report
        # create_summary_report(cleaned_df, output_dir)
        
        print("\n" + "="*60)
        print("SUCCESS: CSV cleaning completed successfully!")
        print(f"Cleaned file: {output_file}")
        # print(f"Summary report: {Path(output_dir) / 'availability_summary.txt'}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
        print("Please check the file path and try again.")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Please check the CSV file format and try again.")

if __name__ == "__main__":
    main()
