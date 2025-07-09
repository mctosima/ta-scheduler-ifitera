import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

class ThesisScheduler:
    def __init__(self, dataframes, config, round2=True):
        self.dataframes = dataframes
        self.config = config
        self.round2 = round2
        
        # Track Statistics
        self.unscheduled_before_round_1 = 0
        self.unscheduled_before_round_2 = 0
        self.unscheduled_after_round_2 = 0
        
        
        # add new column `num_assignment` and `used_timeslot` to lecturers dataframe
        self.dataframes['lecturers']['num_assignment'] = 0
        self.dataframes['lecturers']['used_timeslot'] = pd.NaT
        self.lect_pool = self.dataframes['lecturers']['kode_dosen'].copy().to_numpy()

        
    def run(self):
        # Count unscheduled requests before round 1
        self.unscheduled_before_round_1 = self._count_unscheduled_requests()
        
        # Keep track of processed capstone groups to avoid duplicate processing
        processed_capstone_groups = set()
        
        # Iterate through each request
        for index, request in self.dataframes['request'].iterrows():
            print(f"Processing request {index}: {request['nim']}")
            
            
            # if the request['date_time'] is not NaN, skip this request
            if pd.notna(request['date_time']):
                print(f"Skipping request {index} as it has already been scheduled.")
                continue
            
            # Check if this is a capstone project and if we've already processed this group
            if pd.notna(request.get('capstone_code')):
                capstone_code = request['capstone_code']
                if capstone_code in processed_capstone_groups:
                    print(f"Skipping request {index} as capstone group {capstone_code} has already been processed.")
                    continue
                else:
                    processed_capstone_groups.add(capstone_code)
            
            print(f"Processing request {index}: {request['nim']}")
            print(f"Request details: {request}")
            temp_lect_pool = self.lect_pool.copy()
            
            # check if the request is capstone
            capstone_status, request_id = self._check_capstone(request)
            
            # check the timeslot needed for this request
            required_timeslot = self._check_timeslot_needed(request_id)
            print(f"required_timeslot for request {index} ({request['nim']}): {required_timeslot} slots")
            
            # check what actors are assigned and to be assigned
            assigned_actor, to_be_assigned_actor = self._check_list_actor(request)
            assigned_actor_name = []
            for actor in assigned_actor:
                assigned_actor_name.append(self.dataframes['request'][actor].loc[index])
            print(f"Assigned actors role: {assigned_actor} | name --> {index}: {assigned_actor_name}")
            
            # remove the actor that has been assigned from the pool
            if assigned_actor:
                for actor in assigned_actor:
                    actor_name = self.dataframes['request'][actor].loc[index]
                    if actor_name in temp_lect_pool:
                        temp_lect_pool = temp_lect_pool[temp_lect_pool != actor_name]
            
            # SCHEDULING LOGIC 1 - REMOVING LECTURES WHO ARE NOT ON THE SAME FIELD
            temp_lect_pool = self._check_same_field(
                temp_lect_pool,
                request['field_1'],
                request['field_2'],
                assigned_actor
            )
            
            # SCHEDULING LOGIC 2 - RANKING THE LECTURERS BASED ON:
            # - Criteria A: Most matched schedule with assigned actors (More match - Less Score)
            # - Criteria B: Least number of assignments: (Less assignments - More Score)
            # - Criteria C: Least available timeslots: (Less available - More Score)
            if len(temp_lect_pool) > 0:
                assigned_act_avail, ranked_pool_df = self._rank_lecturer(temp_lect_pool, request, assigned_actor, round_num=1)
                ranked_pool_df_display = ranked_pool_df.drop(columns=['matched_timeslots'])
            else:
                print("No lecturers available after field filtering")
                continue
            
            # Assign the highest ranked from the pool to serve as examiner
            assignment_success = self._assign_actor(request, index, ranked_pool_df, request_id, round_num=1)
            
            # Check if both examiners were assigned in round 1
            updated_request = self.dataframes['request'].loc[index]
            if pd.notna(updated_request['examiner_1']) and pd.notna(updated_request['examiner_2']) and assignment_success:
                print(f"===COMPLETED=== Both examiners assigned in round 1: {updated_request}")
            else:
                # Cancel partial assignment - reset examiners and datetime for round 2
                print(f"===INCOMPLETE=== Only partial assignment in round 1, resetting for round 2: {updated_request}")
                self._reset_partial_assignment(index, updated_request)
            
            # if index == 1:
            #     break
            
        
        if self.round2:
            # Count unscheduled requests before round 2
            self.unscheduled_before_round_2 = self._count_unscheduled_requests()
            print(f"Unscheduled requests before round 2: {self.unscheduled_before_round_2}")
            
            # ROUND 2 SCHEDULING IF THE REQUEST STILL HAS UNASSIGNED SCHEDULE BECAUSE EXPERTISE FIELD DOES NOT MATCH
            print(f" ==== Starting round 2 scheduling for requests with unassigned examiners... ====")
            for index, request in self.dataframes['request'].iterrows():
                
                
                # check if the request['date_time'] is not NaN, skip this request
                if pd.notna(request['date_time']):
                    print(f"Skipping request {index} as it has already been scheduled.")
                    continue
                
                print(f"Processing request {index} in round 2: {request['nim']}")
                print(f"Request details: {request}")
                temp_lect_pool = self.lect_pool.copy()
                
                # check if the request is capstone
                capstone_status, request_id = self._check_capstone(request)
                
                # check what actors are assigned and to be assigned
                assigned_actor, to_be_assigned_actor = self._check_list_actor(request)
                
                # check the timeslot needed for this request
                required_timeslot = self._check_timeslot_needed(request_id)
                print(f"required_timeslot for request {index} ({request['nim']}): {required_timeslot} slots")
                
                # ROUND 2: SKIP FIELD FILTERING - Use all available lecturers
                
                # SCHEDULING LOGIC 2 - RANKING THE LECTURERS BASED ON:
                # - Criteria A: Most matched schedule with assigned actors (More match - Less Score)
                # - Criteria B: Least number of assignments: (Less assignments - More Score)
                # - Criteria C: Least available timeslots: (Less available - More Score)
                # - Criteria D (Round 2): Expertise match bonus - double score if expertise matches
                if len(temp_lect_pool) > 0:
                    assigned_act_avail, ranked_pool_df = self._rank_lecturer(temp_lect_pool, request, assigned_actor, round_num=2)
                    ranked_pool_df_display = ranked_pool_df.drop(columns=['matched_timeslots'])
                else:
                    print("No lecturers available in round 2 scheduling")
                    continue
                
                # Assign the highest ranked from the pool to serve as examiner
                self._assign_actor(request, index, ranked_pool_df, request_id, round_num=2)
                print(f"Updated Request (round 2): {self.dataframes['request'].loc[index]}")
        
        # Count unscheduled requests after round 2
        self.unscheduled_after_round_2 = self._count_unscheduled_requests()
        
        return self.dataframes

    def _assign_actor(self, current_request, request_index, ranked_pool_df, request_id, round_num=1):
        """
        Assign actors (examiners) based on the highest scores in ranked_pool_df
        and update related dataframes accordingly.
        
        Args:
            current_request (pandas.Series): Current request being processed
            request_index (int): Index of current request in the dataframe
            ranked_pool_df (pandas.DataFrame): Ranked lecturers with scores for current request
            request_id: Single student ID (str) or list of student IDs for capstone projects
            round_num (int): Round number (1 or 2) to determine status message
            
        Returns:
            bool: True if assignment was successful, False otherwise
        """
        if ranked_pool_df.empty:
            return False
        
        # Get the current request details
        request_type = 'capstone' if pd.notna(current_request.get('capstone_code')) else 'individual'
        capstone_code = current_request.get('capstone_code', None)
        nim = current_request['nim']
        
        # Sort by score (best first - highest total_score is best)
        sorted_candidates = ranked_pool_df.sort_values('total_score', ascending=False)
        
        print(f"Sorted Candidates: {sorted_candidates.head()}")
        
        # Get the number of examiners needed
        num_examiners_needed = len([role for role in ['examiner_1', 'examiner_2'] 
                                   if pd.isna(current_request.get(role))])
        
        print(f"Number of examiners needed for request {nim}: {num_examiners_needed}")
        
        # Handle case where all examiners are already assigned
        if num_examiners_needed == 0:
            print(f"All examiners already assigned for request {nim}. Finding suitable time for existing actors.")
            # Use the best candidate from ranked pool to get available timeslots
            if not sorted_candidates.empty:
                best_candidate_timeslots = sorted_candidates.iloc[0]['matched_timeslots']
                assigned_datetime = best_candidate_timeslots[0] if best_candidate_timeslots else None
                examiner_codes = []  # No new examiners to assign
            else:
                print(f"No available timeslots found for request {nim}")
                return False
        else:
            # For round 1, ensure we can assign BOTH examiners or fail
            if round_num == 1 and num_examiners_needed > 0:
                if num_examiners_needed < 2:
                    # This shouldn't happen in round 1 based on our logic, but safety check
                    print(f"Warning: Unexpected state in round 1 - only {num_examiners_needed} examiners needed")
                    return False
                
                # We need exactly 2 examiners - check if we have enough candidates
                if len(sorted_candidates) < 2:
                    print(f"Insufficient candidates for round 1 assignment: {len(sorted_candidates)} < 2")
                    return False
            
            # Select top candidates for examiner assignment
            selected_examiners = sorted_candidates.head(num_examiners_needed)
            
            # Get examiner codes
            examiner_codes = selected_examiners['kode_dosen'].tolist()
            
            # Get assigned datetime from matched timeslots (use first available from best candidate)
            first_examiner_timeslots = selected_examiners.iloc[0]['matched_timeslots']
            assigned_datetime = first_examiner_timeslots[0] if first_examiner_timeslots else None
        
        print(f"Assigning examiners: {examiner_codes} for datetime: {assigned_datetime}")
        
        # Determine status based on round number and examiner assignment status
        if num_examiners_needed == 0:
            # All examiners are pre-assigned, only finding time
            status = "Time Match Only (Examiner Already Assigned)"
        else:
            # Assigning new examiners based on round
            status = "Time and Expertise Match" if round_num == 1 else "Time Match Only"
        
        # Update request dataframe
        if request_type == 'capstone' and capstone_code:
            # Update all requests in the same capstone group
            group_mask = self.dataframes['request']['capstone_code'] == capstone_code
            
            # Assign examiners only if there are new examiners to assign
            if examiner_codes:
                examiner_idx = 0
                if pd.isna(current_request.get('examiner_1')) and examiner_idx < len(examiner_codes):
                    self.dataframes['request'].loc[group_mask, 'examiner_1'] = examiner_codes[examiner_idx]
                    examiner_idx += 1
                if pd.isna(current_request.get('examiner_2')) and examiner_idx < len(examiner_codes):
                    self.dataframes['request'].loc[group_mask, 'examiner_2'] = examiner_codes[examiner_idx]
            
            # Update datetime and status
            self.dataframes['request'].loc[group_mask, 'date_time'] = assigned_datetime
            self.dataframes['request'].loc[group_mask, 'status'] = status
        else:
            # Update individual request
            request_mask = self.dataframes['request']['nim'] == nim
            
            # Assign examiners only if there are new examiners to assign
            if examiner_codes:
                examiner_idx = 0
                if pd.isna(current_request.get('examiner_1')) and examiner_idx < len(examiner_codes):
                    self.dataframes['request'].loc[request_mask, 'examiner_1'] = examiner_codes[examiner_idx]
                    examiner_idx += 1
                if pd.isna(current_request.get('examiner_2')) and examiner_idx < len(examiner_codes):
                    self.dataframes['request'].loc[request_mask, 'examiner_2'] = examiner_codes[examiner_idx]
            
            # Update datetime and status
            self.dataframes['request'].loc[request_mask, 'date_time'] = assigned_datetime
            self.dataframes['request'].loc[request_mask, 'status'] = status
        
        # Update timeslot dataframe
        if assigned_datetime:
            # Parse datetime to match timeslots format
            try:
                date_part, time_part = assigned_datetime.split('_')
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                formatted_time = f"{time_part[:2]}:{time_part[2:]}"
                
                # Get required timeslot duration for this request using the passed request_id
                required_timeslot = self._check_timeslot_needed(request_id)
                
                assignment_name = capstone_code if request_type == 'capstone' else nim
                
                # Find consecutive available slots starting from the assigned datetime
                self._assign_consecutive_timeslots(
                    formatted_date, 
                    formatted_time, 
                    required_timeslot, 
                    assignment_name
                )
                
            except Exception as e:
                print(f"Error updating timeslot: {e}")
        
        # Update lecturer_availability dataframe (lecturers table) - only for newly assigned examiners
        for examiner_code in examiner_codes:
            lecturer_mask = self.dataframes['lecturers']['kode_dosen'] == examiner_code
            
            if lecturer_mask.any():
                # Get the index of the lecturer row
                lecturer_idx = self.dataframes['lecturers'][lecturer_mask].index[0]
                
                # Get current used_timeslot list
                current_used = self.dataframes['lecturers'].loc[lecturer_idx, 'used_timeslot']
                
                # Handle different types of current_used values
                if current_used is None or (hasattr(current_used, '__len__') and len(current_used) == 0):
                    used_timeslots = []
                elif isinstance(current_used, list):
                    used_timeslots = current_used.copy()
                elif pd.isna(current_used) if not isinstance(current_used, (list, np.ndarray)) else False:
                    used_timeslots = []
                else:
                    # Handle single values or convert to list
                    used_timeslots = [current_used] if current_used else []
                
                # Add new timeslot if not already present
                if assigned_datetime and assigned_datetime not in used_timeslots:
                    used_timeslots.append(assigned_datetime)
                
                # Update used_timeslot and num_assignment - assign directly to the specific row
                self.dataframes['lecturers'].at[lecturer_idx, 'used_timeslot'] = used_timeslots
                self.dataframes['lecturers'].at[lecturer_idx, 'num_assignment'] = len(used_timeslots)
                
                print(f"Updated lecturer {examiner_code}: assignments={len(used_timeslots)}, timeslots={used_timeslots}")
        
        return True

    def _check_same_field(self, temp_lect_pool, field_1, field_2, assigned_actors):
        """
        Filter lecturers based on field expertise matching and remove already assigned actors.
        
        Args:
            temp_lect_pool (numpy.ndarray): Array of lecturer codes to filter
            field_1 (str): First field requirement
            field_2 (str): Second field requirement  
            assigned_actors (list): List of already assigned actor names to remove
            
        Returns:
            numpy.ndarray: Filtered array of lecturer codes that match field requirements
                          and are not already assigned
        """
        
        # Remove already assigned actors from temp_lect_pool
        for actor in assigned_actors:
            if actor in ['spv_1', 'spv_2', 'examiner_1', 'examiner_2']:
                # Get lecturer code from the request (assuming it's available in current context)
                # This would need to be passed as parameter or accessed differently
                pass
        
        # Create boolean mask for lecturers that match field requirements
        matching_lecturers = []
        
        # Find expertise columns dynamically
        expertise_columns = [col for col in self.dataframes['lecturers'].columns if 'expertise' in col.lower()]
        
        for lecturer_code in temp_lect_pool:
            # Get lecturer row
            lecturer_row = self.dataframes['lecturers'][
                self.dataframes['lecturers']['kode_dosen'] == lecturer_code
            ]
            
            if not lecturer_row.empty:
                lecturer_row = lecturer_row.iloc[0]
                
                # Check if lecturer's expertise matches either field_1 OR field_2
                expertise_match = False
                
                # Check all expertise columns
                for expertise_col in expertise_columns:
                    if expertise_col in lecturer_row:
                        expertise_value = lecturer_row[expertise_col]
                        
                        # Handle different types of expertise values - check type first
                        if isinstance(expertise_value, (list, np.ndarray)):
                            # If it's a list/array, check each element
                            for expertise_item in expertise_value:
                                if pd.notna(expertise_item):
                                    expertise_str = str(expertise_item).strip()
                                    field_1_str = str(field_1).strip() if pd.notna(field_1) else ""
                                    field_2_str = str(field_2).strip() if pd.notna(field_2) else ""
                                    
                                    if expertise_str == field_1_str or expertise_str == field_2_str:
                                        expertise_match = True
                                        break
                        elif pd.notna(expertise_value):
                            # Single value - handle as before
                            expertise_str = str(expertise_value).strip()
                            field_1_str = str(field_1).strip() if pd.notna(field_1) else ""
                            field_2_str = str(field_2).strip() if pd.notna(field_2) else ""
                            
                            if expertise_str == field_1_str or expertise_str == field_2_str:
                                expertise_match = True
                                break
                        
                        if expertise_match:
                            break
                
                if expertise_match:
                    matching_lecturers.append(lecturer_code)
        return np.array(matching_lecturers)
    
    def _rank_lecturer(self, temp_lect_pool, request, assigned_actors, round_num=1):
        """
        Rank lecturers based on availability match with assigned actors, assignments, and overall availability.
        
        Args:
            temp_lect_pool (numpy.ndarray): Array of lecturer codes to rank
            request (pandas.Series): Current request being processed
            assigned_actors (list): List of already assigned actor roles
            round_num (int): Round number (1 or 2) to determine scoring logic
            
        Returns:
            pandas.DataFrame: Ranked lecturers with scores for each criteria
        """
        
        # Get required duration for this request
        capstone_status, request_id = self._check_capstone(request)
        required_duration = self._check_timeslot_needed(request_id)
        
        # Step 1: Get availability times for assigned actors
        assigned_actor_availability = self._get_assigned_actor_availability(request, assigned_actors, required_duration)
        
        # Step 2: Match with free timeslots
        available_timeslots = self._get_free_timeslots(assigned_actor_availability, required_duration)
        
        # Step 3: Convert temp_lect_pool to DataFrame
        ranked_pool_df = pd.DataFrame({
            'kode_dosen': temp_lect_pool
        })
        
        # Step 4: Calculate scores for each criteria
        ranked_pool_df = self._calculate_criteria_scores(ranked_pool_df, available_timeslots, required_duration, request, round_num)
        
        # Check if DataFrame is empty after filtering
        if ranked_pool_df.empty:
            print("No lecturers available after availability filtering")
            return assigned_actor_availability, ranked_pool_df
        
        # Sort by total score (descending - higher is better)
        ranked_pool_df = ranked_pool_df.sort_values('total_score', ascending=False).reset_index(drop=True)

        return assigned_actor_availability, ranked_pool_df

    def _get_assigned_actor_availability(self, request, assigned_actors, required_duration):
        """
        Get common available timeslots for all assigned actors considering event duration.
        
        Args:
            request (pandas.Series): Current request
            assigned_actors (list): List of assigned actor roles
            required_duration (int): Number of consecutive 30-minute slots needed
            
        Returns:
            list: List of starting timeslot column names where all assigned actors 
                  are available for the full duration
        """
        if not assigned_actors:
            # If no assigned actors, return all timeslots that have sufficient consecutive availability
            time_columns = [col for col in self.dataframes['lecturer_availability'].columns 
                           if col not in ['kode_dosen', 'availability_count']]
            return self._get_consecutive_timeslots(time_columns, required_duration)
        
        # Get lecturer codes for assigned actors
        assigned_lecturer_codes = []
        for actor in assigned_actors:
            if actor in request and pd.notna(request[actor]):
                assigned_lecturer_codes.append(request[actor])
        
        if not assigned_lecturer_codes:
            time_columns = [col for col in self.dataframes['lecturer_availability'].columns 
                           if col not in ['kode_dosen', 'availability_count']]
            return self._get_consecutive_timeslots(time_columns, required_duration)
        
        # Get availability for each assigned lecturer
        time_columns = [col for col in self.dataframes['lecturer_availability'].columns 
                       if col not in ['kode_dosen', 'availability_count']]
        
        # Get consecutive available slots for each lecturer
        lecturer_consecutive_slots = []
        for lecturer_code in assigned_lecturer_codes:
            lecturer_avail = self.dataframes['lecturer_availability'][
                self.dataframes['lecturer_availability']['kode_dosen'] == lecturer_code
            ]
            
            if not lecturer_avail.empty:
                lecturer_avail = lecturer_avail.iloc[0]
                # Get available timeslots for this lecturer
                available_slots = []
                for time_col in time_columns:
                    if time_col in lecturer_avail and (lecturer_avail[time_col] == True or 
                                                      lecturer_avail[time_col] == "TRUE" or 
                                                      lecturer_avail[time_col] == "True"):
                        available_slots.append(time_col)
                
                # Get consecutive slots for this lecturer
                consecutive_slots = self._get_consecutive_timeslots(available_slots, required_duration)
                lecturer_consecutive_slots.append(set(consecutive_slots))
        
        # Find intersection of all lecturers' consecutive available slots
        if lecturer_consecutive_slots:
            common_availability = lecturer_consecutive_slots[0]
            for slots in lecturer_consecutive_slots[1:]:
                common_availability = common_availability.intersection(slots)
            return list(common_availability)
        
        return []

    def _get_consecutive_timeslots(self, timeslots, required_duration):
        """
        Get starting timeslots that have sufficient consecutive availability.
        
        Args:
            timeslots (list): List of available timeslot column names
            required_duration (int): Number of consecutive slots needed
            
        Returns:
            list: List of starting timeslot column names that have sufficient consecutive slots
        """
        if not timeslots or required_duration <= 0:
            return []
        
        # Sort timeslots chronologically
        sorted_timeslots = self._sort_timeslots_chronologically(timeslots)
        consecutive_starts = []
        
        for i in range(len(sorted_timeslots) - required_duration + 1):
            # Check if we have consecutive slots starting from this position
            is_consecutive = True
            start_slot = sorted_timeslots[i]
            
            for j in range(1, required_duration):
                expected_next = self._get_next_timeslot(sorted_timeslots[i + j - 1])
                if expected_next != sorted_timeslots[i + j]:
                    is_consecutive = False
                    break
            
            if is_consecutive:
                consecutive_starts.append(start_slot)
        
        return consecutive_starts

    def _sort_timeslots_chronologically(self, timeslots):
        """
        Sort timeslot column names chronologically.
        
        Args:
            timeslots (list): List of timeslot column names
            
        Returns:
            list: Chronologically sorted timeslot column names
        """
        def parse_timeslot(timeslot):
            if '_' in timeslot:
                date_part, time_part = timeslot.split('_')
                date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                time = f"{time_part[:2]}:{time_part[2:]}"
                return pd.to_datetime(f"{date} {time}")
            return pd.to_datetime('1900-01-01')  # Default for invalid format
        
        return sorted(timeslots, key=parse_timeslot)

    def _get_next_timeslot(self, current_timeslot):
        """
        Get the next 30-minute timeslot after the current one.
        
        Args:
            current_timeslot (str): Current timeslot in format YYYYMMDD_HHMM
            
        Returns:
            str: Next timeslot in the same format
        """
        try:
            if '_' in current_timeslot:
                date_part, time_part = current_timeslot.split('_')
                current_time = pd.to_datetime(f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:]}")
                next_time = current_time + pd.Timedelta(minutes=30)
                return f"{next_time.strftime('%Y%m%d')}_{next_time.strftime('%H%M')}"
        except:
            pass
        return ""

    def _get_free_timeslots(self, assigned_availability, required_duration):
        """
        Filter timeslots that are actually free (not occupied) from assigned actor availability,
        considering the required duration.
        
        Args:
            assigned_availability (list): List of starting timeslot column names
            required_duration (int): Number of consecutive slots needed
            
        Returns:
            list: List of free starting timeslot column names
        """
        free_timeslots = []
        
        for timeslot_col in assigned_availability:
            # Check if this starting timeslot and all consecutive slots are free
            is_free_for_duration = True
            current_slot = timeslot_col
            
            for slot_num in range(required_duration):
                if not self._is_timeslot_free(current_slot):
                    is_free_for_duration = False
                    break
                
                # Move to next slot for next iteration
                if slot_num < required_duration - 1:
                    current_slot = self._get_next_timeslot(current_slot)
                    if not current_slot:  # Invalid next slot
                        is_free_for_duration = False
                        break
            
            if is_free_for_duration:
                free_timeslots.append(timeslot_col)
        
        return free_timeslots

    def _is_timeslot_free(self, timeslot_col):
        """
        Check if a single timeslot is free in the timeslots dataframe.
        
        Args:
            timeslot_col (str): Timeslot column name
            
        Returns:
            bool: True if the timeslot has available slots
        """
        if '_' in timeslot_col:
            try:
                date_part, time_part = timeslot_col.split('_')
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                formatted_time = f"{time_part[:2]}:{time_part[2:]}"
                
                # Check if this timeslot is free in the timeslots dataframe
                matching_timeslot = self.dataframes['timeslots'][
                    (self.dataframes['timeslots']['date'] == formatted_date) & 
                    (self.dataframes['timeslots']['time'] == formatted_time)
                ]
                
                if not matching_timeslot.empty:
                    # Check if any slot is available (value is 'none')
                    slot_columns = [col for col in self.dataframes['timeslots'].columns 
                                   if col.startswith('slot_')]
                    row = matching_timeslot.iloc[0]
                    
                    # If any slot is 'none', this timeslot is available
                    return any(row[slot_col] == 'none' for slot_col in slot_columns)
                        
            except Exception as e:
                print(f"Error parsing timeslot {timeslot_col}: {e}")
                
        return False

    def _calculate_criteria_scores(self, lecturers_df, available_timeslots, required_duration, request, round_num=1):
        """
        Calculate scores for each criteria and add them to the lecturers dataframe.
        
        Args:
            lecturers_df (pandas.DataFrame): DataFrame with lecturer codes
            available_timeslots (list): List of available starting timeslot column names
            required_duration (int): Number of consecutive slots needed
            request (pandas.Series): Current request being processed
            round_num (int): Round number (1 or 2) to determine scoring logic
            
        Returns:
            pandas.DataFrame: DataFrame with added scoring columns
        """
        # Initialize score columns
        lecturers_df['criteria_a_matches'] = 0
        lecturers_df['criteria_b_assignments'] = 0
        lecturers_df['criteria_c_availability'] = 0
        lecturers_df['matched_timeslots'] = None
        lecturers_df['criteria_a_score'] = 0
        lecturers_df['criteria_b_score'] = 0
        lecturers_df['criteria_c_score'] = 0
        lecturers_df['expertise_match'] = False  # New column for expertise matching
        
        
        # Calculate raw values for each criteria
        for idx, row in lecturers_df.iterrows():
            lecturer_code = row['kode_dosen']
            
            # Criteria A: Availability match with assigned actors (considering duration)
            lecturer_avail = self.dataframes['lecturer_availability'][
                self.dataframes['lecturer_availability']['kode_dosen'] == lecturer_code
            ]
            
            if not lecturer_avail.empty:
                lecturer_avail = lecturer_avail.iloc[0]
                matches = 0
                matched_slots = []
                
                for start_timeslot in available_timeslots:
                    # Check if lecturer is available for the full duration starting from this slot
                    is_available_for_duration = True
                    current_slot = start_timeslot
                    
                    for slot_num in range(required_duration):
                        if current_slot in lecturer_avail:
                            if not (lecturer_avail[current_slot] == True or 
                                   lecturer_avail[current_slot] == "TRUE" or 
                                   lecturer_avail[current_slot] == "True"):
                                is_available_for_duration = False
                                break
                        else:
                            is_available_for_duration = False
                            break
                        
                        # Move to next slot for next iteration
                        if slot_num < required_duration - 1:
                            current_slot = self._get_next_timeslot(current_slot)
                            if not current_slot:
                                is_available_for_duration = False
                                break
                    
                    if is_available_for_duration:
                        matches += 1
                        matched_slots.append(start_timeslot)
                
                lecturers_df.at[idx, 'criteria_a_matches'] = matches
                lecturers_df.at[idx, 'matched_timeslots'] = matched_slots
                
            
            # Criteria B: Number of assignments
            lecturer_info = self.dataframes['lecturers'][
                self.dataframes['lecturers']['kode_dosen'] == lecturer_code
            ]
            if not lecturer_info.empty:
                assignments = lecturer_info.iloc[0]['num_assignment']
                lecturers_df.at[idx, 'criteria_b_assignments'] = assignments
            
            # Criteria C: Overall availability
            if not lecturer_avail.empty:
                availability_count = lecturer_avail['availability_count']
                lecturers_df.at[idx, 'criteria_c_availability'] = availability_count
            
            # Check expertise match for Round 2 bonus
            if round_num == 2:
                expertise_match = self._check_lecturer_expertise_match(lecturer_code, request)
                lecturers_df.at[idx, 'expertise_match'] = expertise_match
        
        # Filter out lecturers with no availability matches (criteria_a_matches = 0)
        lecturers_df = lecturers_df[lecturers_df['criteria_a_matches'] > 0].reset_index(drop=True)
        
        # Only calculate scores if we have remaining lecturers
        if not lecturers_df.empty:
            # Calculate scores using ranking (higher score = better candidate)
            # For criteria A: More matches = worse (lower score)
            lecturers_df['criteria_a_score'] = lecturers_df['criteria_a_matches'].rank(method='max', ascending=False)
            
            # For criteria B: Fewer assignments = better (higher score)  
            lecturers_df['criteria_b_score'] = lecturers_df['criteria_b_assignments'].rank(method='min', ascending=False)
            
            # For criteria C: Less overall availability = better (higher score) - prioritize busy lecturers
            lecturers_df['criteria_c_score'] = lecturers_df['criteria_c_availability'].rank(method='min', ascending=False)
            
            # Calculate total score
            lecturers_df['total_score'] = (lecturers_df['criteria_a_score'] + 4 *
                                          lecturers_df['criteria_b_score'] + 
                                          lecturers_df['criteria_c_score'])
            
            # Apply expertise bonus for Round 2
            if round_num == 2:
                # Double the total score for lecturers with expertise match
                expertise_bonus_mask = lecturers_df['expertise_match']
                lecturers_df.loc[expertise_bonus_mask, 'total_score'] *= 2
                print(f"Applied expertise bonus to {expertise_bonus_mask.sum()} lecturers in round 2")
        
        return lecturers_df

    def _assign_consecutive_timeslots(self, start_date, start_time, duration, assignment_name):
        """
        Assign consecutive timeslots for the given duration.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            start_time (str): Start time in HH:MM format
            duration (int): Number of 30-minute slots needed
            assignment_name (str): Name to assign to the slots
        """
        # Convert start time to minutes for calculation
        start_hour, start_minute = map(int, start_time.split(':'))
        start_minutes = start_hour * 60 + start_minute
        
        slots_assigned = 0
        current_minutes = start_minutes
        
        for slot_num in range(duration):
            # Calculate current slot time
            current_hour = current_minutes // 60
            current_min = current_minutes % 60
            current_time_str = f"{current_hour:02d}:{current_min:02d}"
            
            # Find matching timeslot row
            timeslot_mask = ((self.dataframes['timeslots']['date'] == start_date) & 
                           (self.dataframes['timeslots']['time'] == current_time_str))
            
            if timeslot_mask.any():
                slot_columns = [col for col in self.dataframes['timeslots'].columns if col.startswith('slot_')]
                row_idx = self.dataframes['timeslots'][timeslot_mask].index[0]
                
                # Find first available slot and assign
                slot_assigned = False
                for slot_col in slot_columns:
                    if self.dataframes['timeslots'].loc[row_idx, slot_col] == 'none':
                        self.dataframes['timeslots'].loc[row_idx, slot_col] = assignment_name
                        slots_assigned += 1
                        slot_assigned = True
                        print(f"Updated timeslot {start_date} {current_time_str} ({slot_col}) with {assignment_name}")
                        break
                
                if not slot_assigned:
                    print(f"Warning: No available slot found for {start_date} {current_time_str}")
                    break
            else:
                print(f"Warning: Timeslot not found for {start_date} {current_time_str}")
                break
            
            # Move to next 30-minute slot
            current_minutes += 30
        
        print(f"Assigned {slots_assigned} out of {duration} required timeslots for {assignment_name}")

    def _check_timeslot_needed(self, request_id):
        """
        Determine the timeslot needed for a request based on whether it's a capstone project or not,
        and the type of event (Proposal vs Sidang Akhir).
        
        Args:
            request_id: Single student ID (str) or list of student IDs for capstone projects
            
        Returns:
            int: The timeslot duration needed for this request
        """
        # Get the request type from the current request being processed
        # We need to find the request row to get the type
        if isinstance(request_id, str):
            # Single student - find the request row
            request_row = self.dataframes['request'][
                self.dataframes['request']['nim'] == request_id
            ]
        else:
            # Capstone project - use the first student to get the type
            request_row = self.dataframes['request'][
                self.dataframes['request']['nim'] == request_id[0]
            ]
        
        if request_row.empty:
            # Fallback to default if request not found
            return int(self.config['default_timeslot'])
        
        request_type = request_row.iloc[0].get('type', 'Proposal')  # Default to Proposal if type not found
        
        if isinstance(request_id, str):  # Single student (not a capstone project)
            if request_type == 'Sidang Akhir':
                return int(self.config['default_timeslot_sidang'])
            else:  # Proposal or any other type
                return int(self.config['default_timeslot'])
        else:  # Capstone project (list of student IDs)
            # Get number of students in the capstone group
            num_students = len(request_id)
            
            # Get timeslot based on number of students and type from config
            if request_type == 'Sidang Akhir':
                # Use sidang configurations
                if num_students == 2:
                    return int(self.config['capstone_duration_sidang_2'])
                elif num_students == 3:
                    return int(self.config['capstone_duration_sidang_3'])
                elif num_students == 4:
                    return int(self.config['capstone_duration_sidang_4'])
                else:
                    # Default to single student sidang timeslot for other numbers
                    return int(self.config['default_timeslot_sidang'])
            else:
                # Use proposal configurations (default)
                if num_students == 2:
                    return int(self.config['capstone_duration_2'])
                elif num_students == 3:
                    return int(self.config['capstone_duration_3'])
                elif num_students == 4:
                    return int(self.config['capstone_duration_4'])
                else:
                    # Default to single student proposal timeslot for other numbers
                    return int(self.config['default_timeslot'])

    def _check_capstone(self, request):
        """
        Check if the request is for a capstone project and return relevant information.

        Args:
            request (dict or pandas.Series): A request containing student information
            
        Returns:
            tuple: A tuple containing:
                - capstone_status: Group name (e.g. 'A', 'B') if capstone, None otherwise
                - request_id: Array of student IDs in same group if capstone, single student ID otherwise
                
        Raises:
            ValueError: If capstone group members have inconsistent actor or field assignments
        """
        if pd.notna(request.get('capstone_code')):
            capstone_status = request['capstone_code']
            # Get all rows with the same capstone group
            same_group_requests = self.dataframes['request'][
                self.dataframes['request']['capstone_code'] == capstone_status
            ]
            
            # Verify integrity of capstone group data
            self._verify_capstone_integrity(same_group_requests, capstone_status)
            
            request_id = same_group_requests['nim'].tolist()
        else:
            capstone_status = None
            request_id = request['nim']

        return capstone_status, request_id
    
    def _verify_capstone_integrity(self, group_requests, capstone_code):
        """
        Verify that all members of a capstone group have consistent actor and field assignments.
        
        Args:
            group_requests (pandas.DataFrame): All requests for the same capstone group
            capstone_code (str): The capstone group identifier
            
        Raises:
            ValueError: If group members have inconsistent data
        """
        fields_to_check = ['spv_1', 'spv_2', 'examiner_1', 'examiner_2', 'field_1', 'field_2']
        
        # Get the first row as reference
        reference_row = group_requests.iloc[0]
        
        # Check each field for consistency across all group members
        for field in fields_to_check:
            reference_value = reference_row[field]
            
            # Check if all values in this field are the same (handling NaN values)
            field_values = group_requests[field]
            
            # Use pandas comparison that handles NaN properly
            if not (field_values.isna().all() or 
                   (field_values.notna() & (field_values == reference_value)).all() or
                   field_values.isna().equals(reference_row[field] if pd.isna(reference_value) else pd.Series([False] * len(field_values)))):
                
                inconsistent_values = field_values.unique()
                raise ValueError(
                    f"Capstone group '{capstone_code}' has inconsistent '{field}' values: {inconsistent_values}. "
                    f"All members must have the same {field} assignment."
                )
    
    def _check_list_actor(self, request):
        """
        Check and categorize actors (supervisors and examiners) based on their assignment status.
        This method analyzes a request to determine which actors are already assigned
        and which ones still need to be assigned for a thesis defense or similar academic event.
        Args:
            request (dict or pandas.Series): A dictionary or pandas Series containing
                actor assignment information with keys 'spv_1', 'spv_2', 'examiner_1', 
                and 'examiner_2'.
        Returns:
            tuple: A tuple containing two lists:
                - assigned_actor (list): List of actor keys that are already assigned
                  (have non-null values)
                - to_be_assigned_actor (list): List of actor keys that need to be assigned
                  (have null/NaN values)
        Note:
            - Supervisors ('spv_1', 'spv_2') are checked for assignment status only
            - Examiners ('examiner_1', 'examiner_2') are checked for unassigned status only
            - Uses pandas.notna() and pandas.isna() for null value checking
        """
        assigned_actor = []
        to_be_assigned_actor = []

        # Check supervisors
        if pd.notna(request['spv_1']):
            assigned_actor.append('spv_1')
            
        if pd.notna(request['spv_2']):
            assigned_actor.append('spv_2')

        # Check examiners
        if pd.isna(request['examiner_1']):
            to_be_assigned_actor.append('examiner_1')
            
        if pd.isna(request['examiner_2']):
            to_be_assigned_actor.append('examiner_2')
        
        return assigned_actor, to_be_assigned_actor

    def _count_unscheduled_requests(self):
        """Count the number of unscheduled requests (those without date_time)."""
        unscheduled_count = self.dataframes['request']['date_time'].isna().sum()
        return unscheduled_count

    def get_statistics(self):
        """Get all statistics for the scheduling process."""
        # Calculate lecturer statistics (excluding those with 0 assignments)
        lecturers_with_assignments = self.dataframes['lecturers'][
            self.dataframes['lecturers']['num_assignment'] > 0
        ]
        
        if len(lecturers_with_assignments) > 0:
            average_assignments = lecturers_with_assignments['num_assignment'].mean()
            total_lecturers_with_assignments = len(lecturers_with_assignments)
            total_assignments = lecturers_with_assignments['num_assignment'].sum()
        else:
            average_assignments = 0
            total_lecturers_with_assignments = 0
            total_assignments = 0
        
        total_lecturers = len(self.dataframes['lecturers'])
        total_requests = len(self.dataframes['request'])
        
        statistics = {
            'total_requests': total_requests,
            'unscheduled_before_round_1': self.unscheduled_before_round_1,
            'unscheduled_before_round_2': self.unscheduled_before_round_2,
            'unscheduled_after_round_2': self.unscheduled_after_round_2,
            'scheduled_after_round_1': self.unscheduled_before_round_1 - self.unscheduled_before_round_2,
            'scheduled_after_round_2': self.unscheduled_before_round_2 - self.unscheduled_after_round_2,
            'total_scheduled': total_requests - self.unscheduled_after_round_2,
            'total_lecturers': total_lecturers,
            'lecturers_with_assignments': total_lecturers_with_assignments,
            'lecturers_without_assignments': total_lecturers - total_lecturers_with_assignments,
            'total_assignments': total_assignments,
            'average_assignments_per_active_lecturer': round(average_assignments, 2)
        }
        
        return statistics

    def print_statistics(self):
        """Print detailed statistics about the scheduling process."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("THESIS SCHEDULING STATISTICS")
        print("="*60)
        
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Unscheduled before Round 1: {stats['unscheduled_before_round_1']}")
        print(f"Unscheduled before Round 2: {stats['unscheduled_before_round_2']}")
        print(f"Unscheduled after Round 2: {stats['unscheduled_after_round_2']}")
        
        print(f"\nScheduling Success Rate:")
        print(f"  - Scheduled in Round 1: {stats['scheduled_after_round_1']}")
        print(f"  - Scheduled in Round 2: {stats['scheduled_after_round_2']}")
        print(f"  - Total Scheduled: {stats['total_scheduled']}")
        print(f"  - Success Rate: {(stats['total_scheduled'] / stats['total_requests'] * 100):.1f}%")
        
        print(f"\nLecturer Assignment Statistics:")
        print(f"  - Total Lecturers: {stats['total_lecturers']}")
        print(f"  - Lecturers with Assignments: {stats['lecturers_with_assignments']}")
        print(f"  - Lecturers without Assignments: {stats['lecturers_without_assignments']}")
        print(f"  - Total Assignments: {stats['total_assignments']}")
        print(f"  - Average Assignments per Active Lecturer: {stats['average_assignments_per_active_lecturer']}")
        
        if stats['lecturers_with_assignments'] > 0:
            utilization_rate = (stats['lecturers_with_assignments'] / stats['total_lecturers'] * 100)
            print(f"  - Lecturer Utilization Rate: {utilization_rate:.1f}%")
        
        print("="*60)
    
    def _reset_partial_assignment(self, request_index, current_request):
        """
        Reset partial assignments when only one examiner was assigned in round 1.
        This ensures requests with incomplete examiner assignments go to round 2.
        
        Args:
            request_index (int): Index of the request in the dataframe
            current_request (pandas.Series): Current request data
        """
        # Get request details
        nim = current_request['nim']
        capstone_code = current_request.get('capstone_code', None)
        request_type = 'capstone' if pd.notna(capstone_code) else 'individual'
        
        # Get assigned examiners that need to be reset
        assigned_examiners = []
        if pd.notna(current_request.get('examiner_1')):
            assigned_examiners.append(current_request['examiner_1'])
        if pd.notna(current_request.get('examiner_2')):
            assigned_examiners.append(current_request['examiner_2'])
        
        # Get assigned datetime to revert timeslot changes
        assigned_datetime = current_request.get('date_time')
        
        # Reset request dataframe
        if request_type == 'capstone' and capstone_code:
            # Reset all requests in the same capstone group
            group_mask = self.dataframes['request']['capstone_code'] == capstone_code
            self.dataframes['request'].loc[group_mask, 'examiner_1'] = pd.NaT
            self.dataframes['request'].loc[group_mask, 'examiner_2'] = pd.NaT
            self.dataframes['request'].loc[group_mask, 'date_time'] = pd.NaT
            self.dataframes['request'].loc[group_mask, 'status'] = pd.NaT
        else:
            # Reset individual request
            request_mask = self.dataframes['request']['nim'] == nim
            self.dataframes['request'].loc[request_mask, 'examiner_1'] = pd.NaT
            self.dataframes['request'].loc[request_mask, 'examiner_2'] = pd.NaT
            self.dataframes['request'].loc[request_mask, 'date_time'] = pd.NaT
            self.dataframes['request'].loc[request_mask, 'status'] = pd.NaT
        
        # Revert timeslot assignments
        if assigned_datetime:
            try:
                date_part, time_part = assigned_datetime.split('_')
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                formatted_time = f"{time_part[:2]}:{time_part[2:]}"
                
                # Get required timeslot duration 
                capstone_status, request_id = self._check_capstone(current_request)
                required_timeslot = self._check_timeslot_needed(request_id)
                
                # Revert consecutive timeslots
                self._revert_consecutive_timeslots(
                    formatted_date, 
                    formatted_time, 
                    required_timeslot, 
                    capstone_code if request_type == 'capstone' else nim
                )
                
            except Exception as e:
                print(f"Error reverting timeslot: {e}")
        
        # Revert lecturer assignments
        for examiner_code in assigned_examiners:
            lecturer_mask = self.dataframes['lecturers']['kode_dosen'] == examiner_code
            
            if lecturer_mask.any():
                lecturer_idx = self.dataframes['lecturers'][lecturer_mask].index[0]
                current_used = self.dataframes['lecturers'].loc[lecturer_idx, 'used_timeslot']
                
                # Remove the assigned datetime from used_timeslot list
                if isinstance(current_used, list) and assigned_datetime in current_used:
                    updated_used = [slot for slot in current_used if slot != assigned_datetime]
                    self.dataframes['lecturers'].at[lecturer_idx, 'used_timeslot'] = updated_used
                    self.dataframes['lecturers'].at[lecturer_idx, 'num_assignment'] = len(updated_used)
                    print(f"Reverted lecturer {examiner_code}: assignments={len(updated_used)}")
        
        print(f"Reset partial assignment for request {nim}")

    def _revert_consecutive_timeslots(self, start_date, start_time, duration, assignment_name):
        """
        Revert consecutive timeslots that were previously assigned.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            start_time (str): Start time in HH:MM format
            duration (int): Number of 30-minute slots to revert
            assignment_name (str): Name of the assignment to remove
        """
        # Convert start time to minutes for calculation
        start_hour, start_minute = map(int, start_time.split(':'))
        start_minutes = start_hour * 60 + start_minute
        
        slots_reverted = 0
        current_minutes = start_minutes
        
        for slot_num in range(duration):
            # Calculate current slot time
            current_hour = current_minutes // 60
            current_min = current_minutes % 60
            current_time_str = f"{current_hour:02d}:{current_min:02d}"
            
            # Find matching timeslot row
            timeslot_mask = ((self.dataframes['timeslots']['date'] == start_date) & 
                           (self.dataframes['timeslots']['time'] == current_time_str))
            
            if timeslot_mask.any():
                slot_columns = [col for col in self.dataframes['timeslots'].columns if col.startswith('slot_')]
                row_idx = self.dataframes['timeslots'][timeslot_mask].index[0]
                
                # Find and revert slots assigned to this assignment
                for slot_col in slot_columns:
                    if self.dataframes['timeslots'].loc[row_idx, slot_col] == assignment_name:
                        self.dataframes['timeslots'].loc[row_idx, slot_col] = 'none'
                        slots_reverted += 1
                        print(f"Reverted timeslot {start_date} {current_time_str} ({slot_col})")
                        break
            
            # Move to next 30-minute slot
            current_minutes += 30
        
        print(f"Reverted {slots_reverted} timeslots for {assignment_name}")
    
    def _check_lecturer_expertise_match(self, lecturer_code, request):
        """
        Check if a lecturer's expertise matches the request's field requirements.
        
        Args:
            lecturer_code (str): Code of the lecturer to check
            request (pandas.Series): Current request being processed
            
        Returns:
            bool: True if lecturer's expertise matches any of the request fields
        """
        # Get lecturer row
        lecturer_row = self.dataframes['lecturers'][
            self.dataframes['lecturers']['kode_dosen'] == lecturer_code
        ]
        
        if lecturer_row.empty:
            return False
        
        lecturer_row = lecturer_row.iloc[0]
        field_1 = request['field_1']
        field_2 = request['field_2']
        
        # Find expertise columns dynamically
        expertise_columns = [col for col in self.dataframes['lecturers'].columns if 'expertise' in col.lower()]
        
        # Check if lecturer's expertise matches either field_1 OR field_2
        for expertise_col in expertise_columns:
            if expertise_col in lecturer_row:
                expertise_value = lecturer_row[expertise_col]
                
                # Handle different types of expertise values
                if isinstance(expertise_value, (list, np.ndarray)):
                    # If it's a list/array, check each element
                    for expertise_item in expertise_value:
                        if pd.notna(expertise_item):
                            expertise_str = str(expertise_item).strip()
                            field_1_str = str(field_1).strip() if pd.notna(field_1) else ""
                            field_2_str = str(field_2).strip() if pd.notna(field_2) else ""
                            
                            if expertise_str == field_1_str or expertise_str == field_2_str:
                                return True
                elif pd.notna(expertise_value):
                    # Single value
                    expertise_str = str(expertise_value).strip()
                    field_1_str = str(field_1).strip() if pd.notna(field_1) else ""
                    field_2_str = str(field_2).strip() if pd.notna(field_2) else ""
                    
                    if expertise_str == field_1_str or expertise_str == field_2_str:
                        return True
        
        return False