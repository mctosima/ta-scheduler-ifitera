import pandas as pd
import os

class Dataframe:
    def __init__(self,
                 avail_fname: str,
                 request_fname: str,
                 output_fname: str,
                 parallel_event: int = 1):

        self.availibility_path = os.path.join(os.getcwd(), "data", "input", avail_fname)
        self.request_path = os.path.join(os.getcwd(), "data", "input", request_fname)
        self.output_path = os.path.join(os.getcwd(), "data", "output", output_fname)
        self.parallel_event = parallel_event

        # Check if the availability file exists
        if not os.path.exists(self.availibility_path):
            raise FileNotFoundError(f"Availability file not found: {self.availibility_path}")
        # Check if the request file exists
        if not os.path.exists(self.request_path):
            raise FileNotFoundError(f"Request file not found: {self.request_path}")

        # Prepare all dataframes
        self.availability_df = self.read_and_clean_availability()
        self.request_df = self.read_and_clean_request()
        self.lecture_df = self.lecture_field()
        self.lecture_avail_df = self.get_lecture_availability()
        self.timeslot_df = self.create_timeslot_dataframe()

    def read_and_clean_availability(self):
        """
        Reads the availability CSV file and cleans it by removing the second and third rows.
        """
        # Read CSV and remove second and third rows (index 1 and 2)
        df = pd.read_csv(self.availibility_path, header=None)
        df = df.drop([1, 2]).reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df[1:]
        return df

    def read_and_clean_request(self):
        """
        Reads the request CSV file and cleans it by removing the second and third rows.
        """
        # Read CSV and remove second and third rows (index 1 and 2)
        df = pd.read_csv(self.request_path, header=None)
        df = df.drop([1]).reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df[1:]
        
        # drop all columns if the header is nan
        df = df.loc[:, df.columns.notna()]
        
        # add new columns for `original_idx`
        df['original_idx'] = df.index
        return df

    def lecture_field(self):
        """
        Creates a new dataframe with lecturer information including name, code, and expertise.
        """
        # Extract lecturer names and codes
        lecturer_names = self.availability_df["nama_dosen"]
        lecturer_codes = self.availability_df["kode_dosen"]
        
        # Extract expertise from sk_1 to sk_4 columns
        expertise_columns = [col for col in self.availability_df.columns if col.startswith("sk_") and col[3:].isdigit()]
        expertise_data = self.availability_df[expertise_columns]
        
        # Combine expertise into a single column (you can modify this logic as needed)
        expertise_combined = expertise_data.apply(lambda row: [val for val in row if pd.notna(val) and val != ''], axis=1)
        
        # Create new dataframe
        lecture_df = pd.DataFrame({
            'kode_dosen': lecturer_codes,
            'nama_dosen': lecturer_names,
            'expertise': expertise_combined
        })
        
        return lecture_df
    
    def get_lecture_availability(self):
        """
        Creates lecturer availability dataframe with 30-minute time slots.
        
        Returns:
            pd.DataFrame: Lecturer availability with 30-minute intervals
        """
        # Step 1: Copy the availability dataframe
        lecture_avail_df = self.availability_df.copy()
        
        # Step 2: Remove specified columns
        columns_to_remove = ['nama_dosen'] + [col for col in lecture_avail_df.columns if col.startswith('sk_') and col[3:].isdigit()]
        lecture_avail_df = lecture_avail_df.drop(columns=columns_to_remove, errors='ignore')
        
        # Step 3 & 4: Identify time slot columns and expand to 30-minute intervals
        time_columns = []
        for col in lecture_avail_df.columns:
            if col != 'kode_dosen' and '_' in col:
                try:
                    # Check if column follows YYYYMMDD_HHMM format
                    date_part, time_part = col.split('_')
                    if len(date_part) == 8 and len(time_part) == 4:
                        time_columns.append(col)
                except:
                    continue
        
        # Create new dataframe with expanded time slots
        expanded_data = {'kode_dosen': lecture_avail_df['kode_dosen']}
        
        for time_col in time_columns:
            date_part, time_part = time_col.split('_')
            hour = int(time_part[:2])
            minute = int(time_part[2:])
            
            # Create two 30-minute slots for each hour slot
            slot_1 = f"{date_part}_{hour:02d}{minute:02d}"
            slot_2 = f"{date_part}_{hour:02d}{minute+30:02d}"
            
            # Both slots get the same availability value as the original hour slot
            expanded_data[slot_1] = lecture_avail_df[time_col]
            expanded_data[slot_2] = lecture_avail_df[time_col]
        
        # Step 5: Create and return the new dataframe
        expanded_df = pd.DataFrame(expanded_data)
        
        # Step 6: Count the number of 'True' values in each row (from the third column onwards)
        # Handle both string "TRUE" and boolean True values
        expanded_df.insert(1, 'availability_count', expanded_df.iloc[:, 2:].apply(
            lambda row: sum((row == True) | (row == "TRUE") | (row == "True")), axis=1
        ))
        
        return expanded_df

    def create_timeslot_dataframe(self):
        """
        Creates a timeslot dataframe based on lecturer availability columns.
        
        Returns:
            pd.DataFrame: Timeslot dataframe with date, time, and parallel slots
        """
        # Get time columns from lecture_avail_df (excluding kode_dosen)
        time_columns = [col for col in self.lecture_avail_df.columns if col != 'kode_dosen']
        
        # Parse time columns to extract date and time
        timeslot_data = []
        for time_col in time_columns:
            if '_' in time_col:
                try:
                    date_part, time_part = time_col.split('_')
                    if len(date_part) == 8 and len(time_part) == 4:
                        # Format date as YYYY-MM-DD for better readability
                        formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                        # Format time as HH:MM
                        formatted_time = f"{time_part[:2]}:{time_part[2:]}"
                        
                        timeslot_data.append({
                            'date': formatted_date,
                            'time': formatted_time,
                            'original_slot': time_col
                        })
                except:
                    continue
        
        # Create DataFrame from timeslot data
        timeslot_df = pd.DataFrame(timeslot_data)
        
        # Sort by date and time
        timeslot_df = timeslot_df.sort_values(['date', 'time']).reset_index(drop=True)
        
        # Add parallel event slots
        slot_columns = {}
        for i in range(self.parallel_event):
            slot_name = f"slot_{chr(65 + i)}"  # slot_A, slot_B, slot_C, etc.
            slot_columns[slot_name] = 'none'
        
        # Add slot columns to the dataframe
        for slot_name, default_value in slot_columns.items():
            timeslot_df[slot_name] = default_value
        
        # Remove the temporary original_slot column
        timeslot_df = timeslot_df.drop('original_slot', axis=1)
        
        return timeslot_df

    def get_all_dataframes(self):
        """
        Returns all prepared dataframes as a dictionary.
        
        Returns:
            dict: Dictionary containing all prepared dataframes
        """
        return {
            'availability': self.availability_df,
            'request': self.request_df,
            'lecturers': self.lecture_df,
            'lecturer_availability': self.lecture_avail_df,
            'timeslots': self.timeslot_df
        }