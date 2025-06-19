import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Global Indonesian day and month mappings
INDONESIAN_DAYS = {
    'Monday': 'Senin',
    'Tuesday': 'Selasa', 
    'Wednesday': 'Rabu',
    'Thursday': 'Kamis',
    'Friday': 'Jumat',
    'Saturday': 'Sabtu',
    'Sunday': 'Minggu'
}

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

class Cleaner:
    def __init__(self, dataframe):
        self.dataframe = dataframe

    def clean(self):
        self._clean_request()
        self._clean_timeslot()
        self._clean_lecturerschedule()
        return self.dataframe
    
    def _clean_lecturerschedule(self):
        # Remove the expertise column
        self.dataframe['lecturers'].drop(columns=['expertise'], inplace=True, errors='ignore')
        
        # Transform used_timeslot to Indonesian format
        for index, row in self.dataframe['lecturers'].iterrows():
            used_timeslot = row['used_timeslot']
            
            # Handle different types of used_timeslot values more carefully
            if used_timeslot is None:
                self.dataframe['lecturers'].at[index, 'used_timeslot'] = ""
                continue
            elif hasattr(used_timeslot, '__len__') and len(used_timeslot) == 0:
                # Empty list, array, or series
                self.dataframe['lecturers'].at[index, 'used_timeslot'] = ""
                continue
            elif isinstance(used_timeslot, (list, np.ndarray)) or hasattr(used_timeslot, 'tolist'):
                # Handle list, numpy array, or pandas Series
                timeslot_list = used_timeslot.tolist() if hasattr(used_timeslot, 'tolist') else used_timeslot
                
                if len(timeslot_list) > 0:
                    formatted_schedules = []
                    
                    for datetime_str in timeslot_list:
                        if pd.notna(datetime_str):
                            try:
                                # Parse the datetime format (YYYYMMDD_HHMM)
                                date_part, time_part = str(datetime_str).split('_')
                                
                                # Extract date components
                                year = int(date_part[:4])
                                month = int(date_part[4:6])
                                day = int(date_part[6:8])
                                
                                # Extract time components
                                hour = int(time_part[:2])
                                minute = int(time_part[2:])
                                
                                # Create datetime object
                                dt = datetime(year, month, day, hour, minute)
                                
                                # Format Indonesian date and time
                                day_name = INDONESIAN_DAYS[dt.strftime('%A')]
                                month_name = INDONESIAN_MONTHS[month]
                                formatted_datetime = f"{day_name}, {day:02d} {month_name} {year}, {hour:02d}:{minute:02d}"
                                
                                formatted_schedules.append(formatted_datetime)
                                
                            except (ValueError, IndexError, KeyError) as e:
                                print(f"Error processing datetime {datetime_str} for lecturer row {index}: {e}")
                                continue
                    
                    # Join all formatted schedules with semicolons
                    self.dataframe['lecturers'].at[index, 'used_timeslot'] = "; ".join(formatted_schedules)
                else:
                    self.dataframe['lecturers'].at[index, 'used_timeslot'] = ""
            elif pd.isna(used_timeslot):
                # Single NaN/None value
                self.dataframe['lecturers'].at[index, 'used_timeslot'] = ""
            else:
                # Handle single value
                self.dataframe['lecturers'].at[index, 'used_timeslot'] = ""
        
        # Rename columns
        column_mapping = {
            'kode_dosen': 'CODE',
            'nama_dosen': 'Nama',
            'num_assignment': 'Total Dijadwalkan',
            'used_timeslot': 'Jadwal'
        }
        
        self.dataframe['lecturers'].rename(columns=column_mapping, inplace=True)
        
        # Rearrange columns
        columns_order = ['CODE', 'Nama', 'Total Dijadwalkan', 'Jadwal']
        self.dataframe['lecturers'] = self.dataframe['lecturers'][columns_order]

    def _clean_timeslot(self):
        # Initialize new Date column
        self.dataframe['timeslots']['Date'] = None
        
        # Process each row in the timeslots dataframe
        for index, row in self.dataframe['timeslots'].iterrows():
            date_str = row['date']
            
            # Skip if date is NaN or None
            if pd.isna(date_str):
                continue
                
            try:
                # Parse the date format (assumed to be YYYY-MM-DD)
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Format Indonesian date
                day_name = INDONESIAN_DAYS[dt.strftime('%A')]
                month_name = INDONESIAN_MONTHS[dt.month]
                formatted_date = f"{day_name}, {dt.day:02d} {month_name} {dt.year}"
                
                # Assign formatted date to dataframe
                self.dataframe['timeslots'].at[index, 'Date'] = formatted_date
                
            except (ValueError, KeyError) as e:
                print(f"Error processing date for timeslot row {index}: {e}")
                continue
    
        # Drop the original date column
        self.dataframe['timeslots'].drop(columns=['date'], inplace=True, errors='ignore')
        
        # Rearrange columns - put Date first, then time, then slot columns
        columns_order = ['Date', 'time'] + [col for col in self.dataframe['timeslots'].columns 
                                           if col not in ['Date', 'time']]
        self.dataframe['timeslots'] = self.dataframe['timeslots'][columns_order]

    def _clean_request(self):
        # Initialize new columns
        self.dataframe['request']['Date'] = None
        self.dataframe['request']['Start Time'] = None  
        self.dataframe['request']['End Time'] = None
        
        # Process each row in the request dataframe
        for index, row in self.dataframe['request'].iterrows():
            date_time = row['date_time']
            
            # Skip if date_time is NaN or None
            if pd.isna(date_time):
                continue
                
            try:
                # Parse the date_time format (assumed to be YYYYMMDD_HHMM)
                date_part, time_part = str(date_time).split('_')
                
                # Extract date components
                year = int(date_part[:4])
                month = int(date_part[4:6])
                day = int(date_part[6:8])
                
                # Extract time components
                hour = int(time_part[:2])
                minute = int(time_part[2:])
                
                # Create datetime object
                dt = datetime(year, month, day, hour, minute)
                
                # Format Indonesian date
                day_name = INDONESIAN_DAYS[dt.strftime('%A')]
                month_name = INDONESIAN_MONTHS[month]
                formatted_date = f"{day_name}, {day:02d} {month_name} {year}"
                
                # Format start time
                start_time = f"{hour:02d}:{minute:02d}"
                
                # Calculate end time based on timeslot duration
                # Get timeslot duration from config or default to 2 slots (60 minutes)
                timeslot_duration = self._get_timeslot_duration(row)
                end_dt = dt + timedelta(minutes=timeslot_duration * 30)  # 30 minutes per slot
                end_time = f"{end_dt.hour:02d}:{end_dt.minute:02d}"
                
                # Assign values to dataframe
                self.dataframe['request'].at[index, 'Date'] = formatted_date
                self.dataframe['request'].at[index, 'Start Time'] = start_time
                self.dataframe['request'].at[index, 'End Time'] = end_time
                
            except (ValueError, IndexError) as e:
                print(f"Error processing date_time for row {index}: {e}")
                continue

        # sort by date_time
        self.dataframe['request'].sort_values(by=['date_time'], inplace=True)

        # drop the original date_time column
        self.dataframe['request'].drop(columns=['date_time'], inplace=True, errors='ignore')
        
        # Rearrange the columns from left to right
        columns_order = ['original_idx', 'nim', 'nama', 
                         'capstone_code', 'Date', 'Start Time', 
                         'End Time', 'spv_1', 'spv_2', 'examiner_1', 'examiner_2',
                         'status', 'field_1', 'field_2',
        ]
        self.dataframe['request'] = self.dataframe['request'][columns_order]
    
    def _get_timeslot_duration(self, row):
        """
        Get the timeslot duration for a specific request based on whether it's capstone or individual.
        
        Args:
            row (pandas.Series): Request row data
            
        Returns:
            int: Number of 30-minute timeslots needed
        """
        # Check if it's a capstone project
        if pd.notna(row.get('capstone_code')):
            # Get all rows with same capstone code to count students
            same_group = self.dataframe['request'][
                self.dataframe['request']['capstone_code'] == row['capstone_code']
            ]
            num_students = len(same_group)
            
            # Return duration based on number of students (matching scheduler logic)
            if num_students == 2:
                return 3  # capstone_duration_2
            elif num_students == 3:
                return 4  # capstone_duration_3
            elif num_students == 4:
                return 5  # capstone_duration_4
            else:
                return 2  # default_timeslot
        else:
            return 2  # default_timeslot for individual students
