import pandas as pd
import os
import re

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

        # Verify CSV formats before processing
        self.verify_csv_formats()

        # Prepare all dataframes
        self.availability_df = self.read_and_clean_availability()
        self.request_df = self.read_and_clean_request()
        self.lecture_df = self.lecture_field()
        self.lecture_avail_df = self.get_lecture_availability()
        self.timeslot_df = self.create_timeslot_dataframe()

    def verify_csv_formats(self):
        """
        Verifies the format of both availability and request CSV files.
        Raises ValueError if format is incorrect.
        """
        # Verify availability CSV format
        self._verify_availability_format()
        
        # Verify request CSV format
        self._verify_request_format()

    def _verify_availability_format(self):
        """
        Verifies the availability CSV format.
        """
        # Read the raw CSV to check headers
        df = pd.read_csv(self.availibility_path, header=None)
        
        if df.empty:
            raise ValueError("Availability CSV file is empty")
        
        # Get the first row (header)
        header = df.iloc[0].tolist()
        
        # Check basic required columns
        required_start = ['nama_dosen', 'kode_dosen', 'sk_1', 'sk_2', 'sk_3', 'sk_4']
        
        if len(header) < len(required_start):
            raise ValueError(f"Availability CSV header too short. Expected at least {len(required_start)} columns")
        
        # Check if required columns are present at the start
        for i, expected in enumerate(required_start):
            if header[i] != expected:
                raise ValueError(f"Availability CSV header mismatch at position {i}. Expected '{expected}', got '{header[i]}'")
        
        # Check datetime columns format (after sk_4)
        datetime_columns = header[6:]  # Skip first 6 columns
        datetime_pattern = re.compile(r'^\d{8}_\d{4}$')
        
        for col in datetime_columns:
            if col and not datetime_pattern.match(str(col)):
                raise ValueError(f"Availability CSV datetime column '{col}' does not match format YYYYMMDD_HHMM")
        
        # Verify data format (skip rows 1 and 2 as they will be deleted)
        data_rows = df.iloc[3:] if len(df) > 3 else pd.DataFrame()
        
        if not data_rows.empty:
            # Check kode_dosen format (should be 3 letters)
            kode_dosen_col = data_rows.iloc[:, 1]  # Second column
            for idx, code in enumerate(kode_dosen_col):
                if pd.notna(code) and (not isinstance(code, str) or len(str(code)) != 3):
                    raise ValueError(f"Availability CSV row {idx + 4}: kode_dosen '{code}' should be exactly 3 letters")
            
            # Check sk_1 to sk_4 format (should be 4 letters if not empty)
            for sk_idx in range(2, 6):  # Columns 2-5 are sk_1 to sk_4
                sk_col = data_rows.iloc[:, sk_idx]
                for idx, sk_value in enumerate(sk_col):
                    if pd.notna(sk_value) and sk_value != '' and (not isinstance(sk_value, str) or len(str(sk_value)) != 4):
                        raise ValueError(f"Availability CSV row {idx + 4}: sk_{sk_idx-1} '{sk_value}' should be exactly 4 letters or empty")
            
            # Check availability values (should be TRUE, FALSE, or empty)
            availability_cols = data_rows.iloc[:, 6:]  # Datetime columns
            valid_values = {'TRUE', 'FALSE', True, False, '', None}
            
            for col_idx in range(availability_cols.shape[1]):
                col_data = availability_cols.iloc[:, col_idx]
                for row_idx, value in enumerate(col_data):
                    if pd.isna(value):
                        continue
                    if value not in valid_values:
                        raise ValueError(f"Availability CSV row {row_idx + 4}, column {col_idx + 7}: value '{value}' should be TRUE, FALSE, or empty")

    def _verify_request_format(self):
        """
        Verifies the request CSV format.
        """
        # Read the raw CSV to check headers
        df = pd.read_csv(self.request_path, header=None)
        
        if df.empty:
            raise ValueError("Request CSV file is empty")
        
        # Get the first row (header)
        header = df.iloc[0].tolist()
        
        # Check required header format
        expected_header = ['nama', 'nim', 'judul', 'capstone_code', 'type', 'field_1', 'field_2', 
                          'spv_1', 'spv_2', 'date_time', 'examiner_1', 'examiner_2', 'status']
        
        if len(header) < len(expected_header):
            raise ValueError(f"Request CSV header too short. Expected {len(expected_header)} columns")
        
        # Check if headers match (only check defined columns, ignore extra columns)
        for i, expected in enumerate(expected_header):
            if i < len(header) and header[i] != expected:
                raise ValueError(f"Request CSV header mismatch at position {i}. Expected '{expected}', got '{header[i]}'")
        
        # Get availability CSV to check lecturer codes
        avail_df = pd.read_csv(self.availibility_path, header=None)
        avail_header = avail_df.iloc[0].tolist()
        
        # Extract lecturer codes from availability CSV (skip rows 1 and 2)
        valid_lecturer_codes = set()
        if len(avail_df) > 3:
            kode_dosen_idx = avail_header.index('kode_dosen') if 'kode_dosen' in avail_header else 1
            lecturer_codes = avail_df.iloc[3:, kode_dosen_idx]
            valid_lecturer_codes = set(code for code in lecturer_codes if pd.notna(code) and str(code).strip())
        
        # Verify data format (skip row 1 as it will be deleted)
        data_rows = df.iloc[2:] if len(df) > 2 else pd.DataFrame()
        
        if not data_rows.empty:
            # Find column indices
            date_time_idx = header.index('date_time') if 'date_time' in header else 8
            spv_1_idx = header.index('spv_1') if 'spv_1' in header else 6
            spv_2_idx = header.index('spv_2') if 'spv_2' in header else 7
            examiner_1_idx = header.index('examiner_1') if 'examiner_1' in header else 9
            examiner_2_idx = header.index('examiner_2') if 'examiner_2' in header else 10
            
            for idx, row in data_rows.iterrows():
                # Check date_time column should be blank
                if idx < len(data_rows) + 2:  # Adjust for actual row number
                    date_time_value = row.iloc[date_time_idx] if date_time_idx < len(row) else None
                    if pd.notna(date_time_value) and str(date_time_value).strip():
                        raise ValueError(f"Request CSV row {idx + 1}: date_time column should be blank, got '{date_time_value}'")
                
                # Check lecturer codes
                lecturer_columns = [
                    ('spv_1', spv_1_idx),
                    ('spv_2', spv_2_idx),
                    ('examiner_1', examiner_1_idx),
                    ('examiner_2', examiner_2_idx)
                ]
                
                for col_name, col_idx in lecturer_columns:
                    if col_idx < len(row):
                        value = row.iloc[col_idx]
                        if pd.notna(value) and str(value).strip():
                            lecturer_code = str(value).strip()
                            # Check if it's exactly 3 letters
                            if len(lecturer_code) != 3:
                                raise ValueError(f"Request CSV row {idx + 1}: {col_name} '{lecturer_code}' should be exactly 3 letters")
                            # Check if lecturer code exists in availability CSV
                            if lecturer_code not in valid_lecturer_codes:
                                raise ValueError(f"Request CSV row {idx + 1}: {col_name} '{lecturer_code}' not found in availability CSV lecturer codes")

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