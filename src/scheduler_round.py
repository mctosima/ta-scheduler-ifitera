import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta

class ThesisScheduler:
    def __init__(self, dataframes, config):
        self.dataframes = dataframes
        self.config = config
        self.lecturer_assignments = defaultdict(int)  # Track number of assignments per lecturer
        self.capstone_groups = {}  # Track capstone groups and their assignments
        self.scheduled_timeslots = set()  # Track used timeslots
        self.lecturer_timeslot_assignments = defaultdict(set)  # Track lecturer assignments per timeslot
        
        # Parse capstone duration from config
        self.capstone_duration = {}
        for key, value in config.items():
            if key.startswith('capstone_duration_'):
                student_count = key.split('_')[-1]
                self.capstone_duration[student_count] = int(value)
        
        # Set defaults if not found in config
        if not self.capstone_duration:
            self.capstone_duration = {
                "2": 3,
                "3": 4,
                "4": 5,
            }
        
        self.default_timeslot = int(config.get('default_timeslot', 2))
        self.parallel_event = int(config.get('parallel_event', 1))
    
    def run(self):
        """Main scheduling method using chronological order"""
        print("Starting chronological thesis defense scheduling...")
        
        # Process capstone groups
        self._process_capstone_groups()
        
        # Get request list in chronological order (by index)
        request_list = list(self.dataframes['request'].iterrows())
        request_list.sort(key=lambda x: x[0])  # Sort by index (chronological order)
        
        scheduled_count = 0
        total_count = len(request_list)
        
        # Process each request in chronological order
        for index, request_row in request_list:
            try:
                # Check if already scheduled (for capstone groups)
                capstone_code = request_row.get('capstone_code', '')
                if pd.notna(capstone_code) and capstone_code != '':
                    if self.capstone_groups.get(capstone_code, {}).get('assigned_slot'):
                        # Already scheduled as part of capstone group, just update
                        timeslot = self.capstone_groups[capstone_code]['assigned_slot']
                        assigned_lecturers = self.capstone_groups[capstone_code]['assigned_lecturers']
                        self._update_request_dataframe(index, assigned_lecturers, timeslot)
                        scheduled_count += 1
                        continue
                
                # Try to schedule the request
                self._schedule_request(request_row, index)
                
                # Check if successfully scheduled
                new_status = self.dataframes['request'].loc[index, 'status']
                if new_status == 'Field and Time Matching':
                    scheduled_count += 1
                    
            except Exception as e:
                print(f"  Error scheduling request {index}: {e}")
                continue
        
        success_rate = scheduled_count / total_count if total_count > 0 else 0
        print(f"\n✓ Chronological scheduling completed")
        
        return self.dataframes
    
    def _process_capstone_groups(self):
        """Process and validate capstone groups"""
        capstone_groups = {}
        
        for index, row in self.dataframes['request'].iterrows():
            capstone_code = row.get('capstone_code', '')
            if pd.notna(capstone_code) and capstone_code != '':
                field_1 = row.get('field_1', '')
                field_2 = row.get('field_2', '')
                
                if capstone_code not in capstone_groups:
                    capstone_groups[capstone_code] = {
                        'field_1': field_1,
                        'field_2': field_2,
                        'members': [],
                        'assigned_slot': None,
                        'assigned_lecturers': None
                    }
                else:
                    # Validate that field_1 and field_2 are consistent
                    if (capstone_groups[capstone_code]['field_1'] != field_1 or 
                        capstone_groups[capstone_code]['field_2'] != field_2):
                        raise ValueError(f"Inconsistent field_1/field_2 for capstone_code {capstone_code}")
                
                capstone_groups[capstone_code]['members'].append(index)
        
        self.capstone_groups = capstone_groups
    
    def _schedule_request(self, request_row, request_index):
        """Schedule a single request"""
        print(f"Scheduling request {request_index}: {request_row.get('nim', 'Unknown')}")
        
        # Check if this is part of a capstone group
        capstone_code = request_row.get('capstone_code', '')
        if pd.notna(capstone_code) and capstone_code != '':
            if self.capstone_groups[capstone_code]['assigned_slot']:
                # Already scheduled as part of capstone group, update this member's info
                timeslot = self.capstone_groups[capstone_code]['assigned_slot']
                assigned_lecturers = self.capstone_groups[capstone_code]['assigned_lecturers']
                self._update_request_dataframe(request_index, assigned_lecturers, timeslot)
                print(f"✓ Updated capstone member {request_row.get('nim', 'Unknown')} with existing schedule at {timeslot}")
                return
        
        # Step 3: Create examiner pool
        examiner_pool = self._create_examiner_pool(request_row)
        
        # Step 4: Assign lecturers
        assigned_lecturers = self._assign_lecturers(request_row, examiner_pool)
        
        # Step 5: Find available timeslot
        timeslot = self._find_available_timeslot(assigned_lecturers, request_row)
        
        if timeslot:
            # Step 6: Assign to timeslots dataframe
            self._assign_to_timeslot(request_row, timeslot, capstone_code)
            
            # Step 7: Update request dataframe with assigned information
            self._update_request_dataframe(request_index, assigned_lecturers, timeslot)
            
            # Track the scheduled timeslot and all consecutive slots
            self._track_timeslot_usage(timeslot, assigned_lecturers)
            
            # If this is a capstone group, store the assigned lecturers for other members
            if capstone_code and capstone_code != '':
                self.capstone_groups[capstone_code]['assigned_lecturers'] = assigned_lecturers
            
            print(f"✓ Scheduled {request_row.get('nim', 'Unknown')} at {timeslot}")
        else:
            print(f"✗ Could not find available timeslot for {request_row.get('nim', 'Unknown')}")
    
    def _update_request_dataframe(self, request_index, assigned_lecturers, timeslot):
        """Update request dataframe with assigned information"""
        # Convert timeslot to readable format
        try:
            date_part, time_part = timeslot.split('_')
            formatted_datetime = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:]}"
        except:
            formatted_datetime = timeslot
        
        # Update the request dataframe with assigned information using existing columns
        self.dataframes['request'].loc[request_index, 'date_time'] = formatted_datetime
        self.dataframes['request'].loc[request_index, 'examiner_1'] = assigned_lecturers.get('examiner_1', '')
        self.dataframes['request'].loc[request_index, 'examiner_2'] = assigned_lecturers.get('examiner_2', '')
        self.dataframes['request'].loc[request_index, 'status'] = 'Field and Time Matching'
    
    def _create_examiner_pool(self, request_row):
        """Create pool of eligible examiners based on expertise"""
        field_1 = request_row.get('field_1', '')
        field_2 = request_row.get('field_2', '')
        
        eligible_lecturers = []
        
        for _, lecturer in self.dataframes['lecturers'].iterrows():
            lecturer_code = lecturer['kode_dosen']
            expertise_list = lecturer['expertise']
            
            # Check if lecturer expertise matches field_1 or field_2
            if isinstance(expertise_list, list):
                if field_1 in expertise_list or field_2 in expertise_list:
                    eligible_lecturers.append(lecturer_code)
        
        return eligible_lecturers
    
    def _assign_lecturers(self, request_row, examiner_pool):
        """Assign lecturers to request"""
        assigned = {
            'spv_1': request_row.get('spv_1', ''),
            'spv_2': request_row.get('spv_2', ''),
            'examiner_1': request_row.get('examiner_1', ''),
            'examiner_2': request_row.get('examiner_2', '')
        }
        
        # spv_1 cannot be empty - if empty, assign from pool
        if not assigned['spv_1'] or pd.isna(assigned['spv_1']):
            if examiner_pool:
                assigned['spv_1'] = min(examiner_pool, key=lambda x: self.lecturer_assignments[x])
                examiner_pool.remove(assigned['spv_1'])
        
        # Assign examiner_1 if empty
        if not assigned['examiner_1'] or pd.isna(assigned['examiner_1']):
            available_pool = [lec for lec in examiner_pool if lec != assigned['spv_1'] and lec != assigned['spv_2']]
            if available_pool:
                assigned['examiner_1'] = min(available_pool, key=lambda x: self.lecturer_assignments[x])
                examiner_pool.remove(assigned['examiner_1'])
        
        # Assign examiner_2 if empty
        if not assigned['examiner_2'] or pd.isna(assigned['examiner_2']):
            available_pool = [lec for lec in examiner_pool if lec not in assigned.values()]
            if available_pool:
                assigned['examiner_2'] = min(available_pool, key=lambda x: self.lecturer_assignments[x])
        
        return assigned
    
    def _find_available_timeslot(self, assigned_lecturers, request_row):
        """Find available timeslot for assigned lecturers"""
        # Get all assigned lecturer codes (excluding empty ones)
        lecturer_codes = [lec for lec in assigned_lecturers.values() if lec and not pd.isna(lec)]
        
        if not lecturer_codes:
            return None
        
        # Get timeslot columns from lecturer availability
        time_columns = [col for col in self.dataframes['lecturer_availability'].columns if col != 'kode_dosen']
        
        for time_col in sorted(time_columns):
            # Check if timeslot has reached parallel event limit
            current_parallel_count = len([slot for slot in self.scheduled_timeslots if slot.startswith(time_col)])
            if current_parallel_count >= self.parallel_event:
                continue
            
            # Check if any lecturer is already assigned to this timeslot
            lecturer_conflict = False
            for lecturer_code in lecturer_codes:
                if lecturer_code in self.lecturer_timeslot_assignments[time_col]:
                    lecturer_conflict = True
                    break
            
            if lecturer_conflict:
                continue
            
            # Check if all lecturers are available at this time
            all_available = True
            for lecturer_code in lecturer_codes:
                lecturer_row = self.dataframes['lecturer_availability'][
                    self.dataframes['lecturer_availability']['kode_dosen'] == lecturer_code
                ]
                
                if lecturer_row.empty:
                    all_available = False
                    break
                
                availability = lecturer_row[time_col].iloc[0]
                if not (availability == True or availability == 'TRUE' or availability == 'true'):
                    all_available = False
                    break
            
            if all_available:
                # Check if enough consecutive slots are available
                if self._check_consecutive_slots(time_col, lecturer_codes):
                    return time_col
        
        return None
    
    def _check_consecutive_slots(self, start_time_col, lecturer_codes):
        """Check if enough consecutive timeslots are available"""
        required_slots = self.default_timeslot
        
        # Parse the start time
        try:
            date_part, time_part = start_time_col.split('_')
            start_hour = int(time_part[:2])
            start_minute = int(time_part[2:])
        except:
            return False
        
        # Check consecutive slots
        for slot_offset in range(required_slots):
            current_minute = start_minute + (slot_offset * 30)
            current_hour = start_hour + (current_minute // 60)
            current_minute = current_minute % 60
            
            current_time_col = f"{date_part}_{current_hour:02d}{current_minute:02d}"
            
            # Check if this timeslot exists
            if current_time_col not in self.dataframes['lecturer_availability'].columns:
                return False
            
            # Check if any lecturer is already assigned to this consecutive timeslot
            for lecturer_code in lecturer_codes:
                if lecturer_code in self.lecturer_timeslot_assignments[current_time_col]:
                    return False
            
            # Check if all lecturers are available at this consecutive timeslot
            for lecturer_code in lecturer_codes:
                lecturer_row = self.dataframes['lecturer_availability'][
                    self.dataframes['lecturer_availability']['kode_dosen'] == lecturer_code
                ]
                
                if lecturer_row.empty:
                    return False
                
                availability = lecturer_row[current_time_col].iloc[0]
                if not (availability == True or availability == 'TRUE' or availability == 'true'):
                    return False
        
        return True
    
    def _assign_to_timeslot(self, request_row, timeslot, capstone_code):
        """Assign request to timeslot dataframe for all consecutive slots"""
        # Convert timeslot format to match timeslots dataframe
        try:
            date_part, time_part = timeslot.split('_')
            formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            start_hour = int(time_part[:2])
            start_minute = int(time_part[2:])
        except:
            return False
        
        # Determine the number of slots needed
        if pd.notna(capstone_code) and capstone_code != '' and str(capstone_code).strip() != '':
            # For capstone, determine duration based on number of members
            group_size = len(self.capstone_groups.get(capstone_code, {}).get('members', []))
            required_slots = self.capstone_duration.get(str(group_size), self.default_timeslot)
            slot_value = str(capstone_code).strip()
        else:
            # For individual requests, use default timeslot
            required_slots = self.default_timeslot
            slot_value = str(request_row.get('nim', 'Unknown'))
        
        # Fill all consecutive timeslots
        for slot_offset in range(required_slots):
            # Calculate current time
            current_minute = start_minute + (slot_offset * 30)
            current_hour = start_hour + (current_minute // 60)
            current_minute = current_minute % 60
            
            formatted_time = f"{current_hour:02d}:{current_minute:02d}"
            
            # Find matching row in timeslots dataframe
            mask = (self.dataframes['timeslots']['date'] == formatted_date) & \
                   (self.dataframes['timeslots']['time'] == formatted_time)
            
            matching_rows = self.dataframes['timeslots'][mask]
            
            if matching_rows.empty:
                continue
            
            # Find available slot
            row_idx = matching_rows.index[0]
            slot_columns = [col for col in self.dataframes['timeslots'].columns if col.startswith('slot_')]
            
            for slot_col in slot_columns:
                if self.dataframes['timeslots'].loc[row_idx, slot_col] == 'none':
                    self.dataframes['timeslots'].loc[row_idx, slot_col] = slot_value
                    break
        
        # Mark capstone group as assigned if applicable
        if pd.notna(capstone_code) and capstone_code != '' and str(capstone_code).strip() != '':
            self.capstone_groups[capstone_code]['assigned_slot'] = timeslot
        
        return True
    
    def _track_timeslot_usage(self, start_timeslot, assigned_lecturers):
        """Track timeslot usage for all consecutive slots"""
        required_slots = self.default_timeslot
        
        # Parse the start time
        try:
            date_part, time_part = start_timeslot.split('_')
            start_hour = int(time_part[:2])
            start_minute = int(time_part[2:])
        except:
            return
        
        # Track all consecutive slots
        for slot_offset in range(required_slots):
            current_minute = start_minute + (slot_offset * 30)
            current_hour = start_hour + (current_minute // 60)
            current_minute = current_minute % 60
            
            current_time_col = f"{date_part}_{current_hour:02d}{current_minute:02d}"
            
            # Track this timeslot as scheduled
            self.scheduled_timeslots.add(current_time_col)
            
            # Track lecturer assignments for this timeslot
            for lecturer in assigned_lecturers.values():
                if lecturer and lecturer != '':
                    self.lecturer_timeslot_assignments[current_time_col].add(lecturer)
        
        # Update overall lecturer assignment count (only once per session)
        for lecturer in assigned_lecturers.values():
            if lecturer and lecturer != '':
                self.lecturer_assignments[lecturer] += 1
