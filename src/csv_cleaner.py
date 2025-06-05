#!/usr/bin/env python3
"""
CSV Cleaner for Thesis Defense Scheduler.

This module handles cleaning and preprocessing of the availability CSV file
to properly format date/time column headers from merged Excel cells.
"""

import pandas as pd
import re
from typing import List, Dict, Optional


class AvailabilityCSVCleaner:
    """Cleans and preprocesses availability CSV files from Excel exports."""
    
    def __init__(self):
        self.month_mapping = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12'
        }
    
    def clean_availability_csv(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Clean the availability CSV file by properly parsing date/time headers.
        
        Args:
            input_file: Path to the input CSV file
            output_file: Optional path to save the cleaned CSV
            
        Returns:
            Cleaned DataFrame with proper column names
        """
        print(f"Cleaning availability CSV: {input_file}")
        
        # Read the first two rows to analyze structure without treating them as headers
        df_raw = pd.read_csv(input_file, header=None, nrows=2)
        
        # Extract date and time information from the first two rows
        date_row = df_raw.iloc[0]
        time_row = df_raw.iloc[1]
        
        # Create new column names
        new_columns = self._create_column_names(date_row, time_row)
        
        # Read the full file starting from the third row (skip the date/time header rows)
        df_full = pd.read_csv(input_file, header=None, skiprows=2)
        
        # Ensure we have the right number of columns
        if len(new_columns) == len(df_full.columns):
            df_full.columns = new_columns
        else:
            print(f"Warning: Column count mismatch. Expected {len(new_columns)}, got {len(df_full.columns)}")
            # Adjust columns if needed
            min_cols = min(len(new_columns), len(df_full.columns))
            df_full = df_full.iloc[:, :min_cols]
            df_full.columns = new_columns[:min_cols]
        
        # Clean the data
        df_cleaned = self._clean_data(df_full)
        
        # Save if output file specified
        if output_file:
            df_cleaned.to_csv(output_file, index=False)
            print(f"Cleaned CSV saved to: {output_file}")
        
        return df_cleaned
    
    def _create_column_names(self, date_row: pd.Series, time_row: pd.Series) -> List[str]:
        """
        Create proper column names by combining date and time information.
        
        Args:
            date_row: First row containing date information
            time_row: Second row containing time information
            
        Returns:
            List of properly formatted column names
        """
        new_columns = []
        current_date = None
        
        for i in range(len(date_row)):
            if i < 6:  # First 6 columns are metadata (name, code, expertise fields)
                if i == 0:
                    new_columns.append('Nama_Dosen')
                elif i == 1:
                    new_columns.append('Kode_Dosen') 
                elif i == 2:
                    new_columns.append('Sub_Keilmuan_1')
                elif i == 3:
                    new_columns.append('Sub_Keilmuan_2')
                elif i == 4:
                    new_columns.append('Sub_Keilmuan_3')
                elif i == 5:
                    new_columns.append('Sub_Keilmuan_4')
            else:
                # Check if we have a new date (dates appear in first row, times in second row)
                date_val = date_row.iloc[i] if i < len(date_row) else None
                time_val = time_row.iloc[i] if i < len(time_row) else None
                
                # If we have a valid date, update current_date
                if pd.notna(date_val) and str(date_val) != 'nan' and len(str(date_val).strip()) > 5:
                    parsed_date = self._parse_date(str(date_val))
                    if parsed_date:
                        current_date = parsed_date
                        print(f"Found date at column {i}: {date_val} -> {current_date}")
                
                # Get time slot from second row
                time_slot = self._parse_time(str(time_val)) if pd.notna(time_val) else None
                
                # Create column name
                if current_date and time_slot:
                    col_name = f"{current_date}_{time_slot}"
                    new_columns.append(col_name)
                    print(f"Created column: {col_name}")
                else:
                    new_columns.append(f"Unknown_Col_{i}")
        
        return new_columns
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string into standardized format.
        
        Args:
            date_str: Date string like "Tuesday, 10 June 2025"
            
        Returns:
            Formatted date string like "Tuesday_10_June_2025"
        """
        try:
            # Clean the date string
            date_clean = re.sub(r'[^\w\s,]', '', date_str)
            
            # Parse components
            match = re.search(r'(\w+),?\s*(\d+)\s+(\w+)\s+(\d{4})', date_clean)
            if match:
                day, date, month, year = match.groups()
                return f"{day}_{date}_{month}_{year}"
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
        
        return None
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """
        Parse time string into standardized format.
        
        Args:
            time_str: Time string like "08:00" or "8"
            
        Returns:
            Formatted time string like "08:00"
        """
        try:
            if pd.isna(time_str) or str(time_str) == 'nan':
                return None
            
            time_clean = str(time_str).strip()
            
            # Skip non-time values like numbers 1,2,3,4 (which are expertise column indicators)
            if time_clean in ['1', '2', '3', '4']:
                return None
            
            # Handle different time formats
            if ':' in time_clean:
                return time_clean
            elif time_clean.isdigit() and len(time_clean) <= 2:
                hour = int(time_clean)
                if 0 <= hour <= 23:  # Valid hour range
                    return f"{hour:02d}:00"
            elif '.' in time_clean:
                # Handle decimal hours (like 8.0)
                try:
                    hour = int(float(time_clean))
                    if 0 <= hour <= 23:  # Valid hour range
                        return f"{hour:02d}:00"
                except:
                    pass
        except Exception as e:
            print(f"Error parsing time '{time_str}': {e}")
        
        return None
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the data by converting availability values to boolean.
        
        Args:
            df: DataFrame with time slot columns
            
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        
        # Get time slot columns (exclude metadata columns)
        metadata_cols = ['Nama_Dosen', 'Kode_Dosen', 'Sub_Keilmuan_1', 'Sub_Keilmuan_2', 'Sub_Keilmuan_3', 'Sub_Keilmuan_4']
        time_cols = [col for col in df_clean.columns if col not in metadata_cols and '_' in col]
        
        # Convert availability values
        for col in time_cols:
            df_clean[col] = df_clean[col].map(self._convert_to_boolean)
        
        # Clean judge codes and expertise
        if 'Kode_Dosen' in df_clean.columns:
            df_clean['Kode_Dosen'] = df_clean['Kode_Dosen'].fillna('')
        
        # Combine expertise columns into one
        expertise_cols = [col for col in metadata_cols if 'Sub_Keilmuan' in col]
        if expertise_cols:
            df_clean['Sub_Keilmuan'] = df_clean[expertise_cols].apply(
                lambda row: ';'.join([str(val) for val in row if pd.notna(val) and str(val) != '']), 
                axis=1
            )
            # Drop individual expertise columns
            df_clean = df_clean.drop(columns=expertise_cols)
        
        return df_clean
    
    def _convert_to_boolean(self, value) -> bool:
        """
        Convert various value formats to boolean.
        
        Args:
            value: Value to convert
            
        Returns:
            Boolean value
        """
        if pd.isna(value):
            return False
        
        str_val = str(value).upper().strip()
        
        if str_val in ['TRUE', '1', 'YES', 'Y', 'AVAILABLE']:
            return True
        elif str_val in ['FALSE', '0', 'NO', 'N', 'UNAVAILABLE']:
            return False
        else:
            # Assume any other value is False
            return False


def clean_availability_file(input_file: str, output_file: str) -> pd.DataFrame:
    """
    Convenience function to clean an availability CSV file.
    
    Args:
        input_file: Path to the input CSV file
        output_file: Path to save the cleaned CSV
        
    Returns:
        Cleaned DataFrame
    """
    cleaner = AvailabilityCSVCleaner()
    return cleaner.clean_availability_csv(input_file, output_file)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python csv_cleaner.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        clean_availability_file(input_file, output_file)
        print(f"Successfully cleaned {input_file} -> {output_file}")
    except Exception as e:
        print(f"Error cleaning file: {e}")
        sys.exit(1)
