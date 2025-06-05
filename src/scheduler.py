#!/usr/bin/env python3
"""
Core scheduling engine for the Thesis Defense Scheduler.

This module contains the main scheduling logic that matches students
with available judges based on expertise and availability.
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from itertools import combinations
from .models import Judge, Student, ScheduleResult, PanelConfiguration, SchedulingSession, GroupDefense
from .utils import DataProcessor, TimeFormatter, JudgeSelector
from .config import Config


class SchedulingEngine:
    """Core scheduling engine that handles the matching logic."""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_processor = DataProcessor(config)
        self.time_formatter = TimeFormatter(config)
        self.judge_selector = JudgeSelector(config)
        self.session = SchedulingSession()
        
        # Connect the session to judge selector for workload balancing
        self.judge_selector.set_session(self.session)
    
    def load_judges(self, availability_df: pd.DataFrame) -> List[Judge]:
        """
        Convert availability DataFrame to Judge objects.
        
        Args:
            availability_df: DataFrame with judge availability data
            
        Returns:
            List of Judge objects
        """
        judges = []
        time_cols = self.data_processor.get_time_slot_columns(availability_df)
        
        for _, row in availability_df.iterrows():
            # Parse judge information using config column names
            name_col = self.config.column_mappings['availability']['name']
            expertise_col = self.config.column_mappings['availability']['expertise']
            
            name = row[name_col]
            expertise_str = row.get(expertise_col, '')
            expertise_codes = self.data_processor.parse_expertise_codes(expertise_str)
            
            # Get judge code from column 2 (index 1) instead of deriving from expertise
            judge_code = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            
            # Parse availability
            availability = {}
            for time_col in time_cols:
                availability[time_col] = bool(row[time_col])
            
            judge = Judge(
                name=name,
                code=judge_code,
                expertise=expertise_codes,
                availability=availability
            )
            judges.append(judge)
        
        return judges
    
    def load_students(self, request_df: pd.DataFrame) -> List[Student]:
        """
        Convert request DataFrame to Student objects.
        
        Args:
            request_df: DataFrame with student requests
            
        Returns:
            List of Student objects
        """
        students = []
        
        # Get column mappings from config
        student_name_cols = self.config.column_mappings['request']['student_name']
        student_id_cols = self.config.column_mappings['request']['student_id']
        field1_cols = self.config.column_mappings['request']['field1']
        field2_cols = self.config.column_mappings['request']['field2']
        supervisor1_cols = self.config.column_mappings['request']['supervisor1']
        supervisor2_cols = self.config.column_mappings['request']['supervisor2']
        capstone_cols = self.config.column_mappings['request']['capstone']
        
        for _, row in request_df.iterrows():
            # Find the first available column for each field
            name = self._get_first_available_value(row, student_name_cols)
            student_id = self._get_first_available_value(row, student_id_cols)
            field1 = self._get_first_available_value(row, field1_cols)
            field2 = self._get_first_available_value(row, field2_cols)
            supervisor1 = self._get_first_available_value(row, supervisor1_cols)
            supervisor2 = self._get_first_available_value(row, supervisor2_cols)
            capstone = self._get_first_available_value(row, capstone_cols)
            
            student = Student(
                name=name or '',
                student_id=student_id or '',
                field1=field1 or '',
                field2=field2 or '',
                supervisor1=supervisor1 or '',
                supervisor2=supervisor2 or '',
                capstone=capstone
            )
            students.append(student)
        
        return students
    
    def group_students_by_capstone(self, students: List[Student]) -> Tuple[List[GroupDefense], List[Student]]:
        """
        Group students by their capstone identifier and separate individual students.
        
        Args:
            students: List of all students
            
        Returns:
            Tuple of (grouped_defenses, individual_students)
        """
        groups_dict = {}
        individual_students = []
        
        for student in students:
            if student.is_group_defense():
                group_id = student.get_group_id()
                if group_id and group_id not in groups_dict:
                    groups_dict[group_id] = GroupDefense(group_id=group_id)
                if group_id:
                    groups_dict[group_id].students.append(student)
            else:
                individual_students.append(student)
        
        grouped_defenses = list(groups_dict.values())
        
        # Log group information
        if grouped_defenses:
            print(f"\n📊 Found {len(grouped_defenses)} group defenses:")
            for group in grouped_defenses:
                time_req = self.config.get_group_time_requirement(group.get_group_size())
                print(f"  Group {group.group_id}: {group.get_group_size()} students, {time_req}h required")
                for student in group.students:
                    print(f"    - {student.name}")
        
        if individual_students:
            print(f"\n👤 Found {len(individual_students)} individual defenses")
        
        return grouped_defenses, individual_students
    
    def _get_first_available_value(self, row: pd.Series, column_names: List[str]) -> Optional[str]:
        """
        Get the first non-null value from a list of possible column names.
        
        Args:
            row: Pandas Series representing a row of data
            column_names: List of column names to check
            
        Returns:
            First non-null value found, or None if all are null
        """
        for col_name in column_names:
            if col_name in row and pd.notna(row[col_name]):
                return str(row[col_name])
        return None
    
    def find_supervisor_judges(self, student: Student, judges: List[Judge]) -> List[Judge]:
        """
        Find judges that match the student's supervisors.
        
        Args:
            student: Student object
            judges: List of available judges
            
        Returns:
            List of supervisor judges
        """
        supervisor_judges = []
        supervisors = student.get_supervisors()
        
        for supervisor_name in supervisors:
            # Normalize supervisor code
            supervisor_code = self.data_processor.normalize_supervisor_code(
                supervisor_name, pd.DataFrame([judge.__dict__ for judge in judges])
            )
            
            # Find matching judge
            for judge in judges:
                # Check by code, expertise, or name match
                # Ensure supervisor_name and judge.name are not null before string operations
                supervisor_name_str = str(supervisor_name) if pd.notna(supervisor_name) else ""
                judge_name_str = str(judge.name) if pd.notna(judge.name) else ""
                
                if (supervisor_code in judge.expertise or 
                    (supervisor_name_str and judge_name_str and 
                     supervisor_name_str.lower() in judge_name_str.lower()) or
                    supervisor_code.upper() == judge_name_str.upper() or
                    supervisor_code.upper() == judge.code.upper()):
                    if judge not in supervisor_judges:
                        supervisor_judges.append(judge)
                        print(f"✓ Found supervisor: {judge.code} ({judge.name})")
                    break
            else:
                print(f"⚠ Supervisor '{supervisor_name}' not found")
        
        return supervisor_judges
    
    def find_expertise_matches(self, student: Student, judges: List[Judge], 
                             exclude_supervisors: List[Judge]) -> List[Judge]:
        """
        Find judges with matching expertise (excluding supervisors).
        
        Args:
            student: Student object
            judges: List of all judges
            exclude_supervisors: List of supervisor judges to exclude
            
        Returns:
            List of judges with matching expertise
        """
        required_fields = student.get_required_fields()
        expertise_matches = []
        supervisor_codes = [judge.code for judge in exclude_supervisors]
        
        for judge in judges:
            # Skip supervisors
            if judge.code in supervisor_codes:
                continue
            
            # Check expertise match
            for field in required_fields:
                if judge.has_expertise_in(field):
                    if judge not in expertise_matches:
                        expertise_matches.append(judge)
                    break
        
        return expertise_matches
    
    def find_available_time_slots(self, required_judges: List[Judge], group_size: int = 1) -> List[str]:
        """
        Find time slots where all required judges are available and not scheduled.
        Now considers group size for time allocation.
        
        Args:
            required_judges: List of judges that must be available
            group_size: Size of the group (affects time slot allocation)
            
        Returns:
            List of available time slot names
        """
        if not required_judges:
            return []
        
        # Get all possible time slots from first judge
        all_time_slots = list(required_judges[0].availability.keys())
        available_slots = []
        
        constraints = self.config.scheduling_constraints
        max_parallel = constraints.get('max_parallel_defenses', 3)
        time_requirement = self.config.get_group_time_requirement(group_size)
        
        for time_slot in all_time_slots:
            # Check if we can schedule another parallel defense in this time slot
            if not self.session.can_schedule_parallel_defense(time_slot, max_parallel):
                continue
            
            # For group defenses, check if we have enough consecutive time slots
            if group_size > 1 and time_requirement > 1:
                # For now, we'll use the same logic but could be extended for consecutive slots
                # This is a simplified approach - in practice, you might need to check consecutive time slots
                pass
                
            # Check if all judges are available
            all_available = True
            for judge in required_judges:
                if (not judge.is_available_at(time_slot) or 
                    not self.session.is_judge_available(judge.code, time_slot)):
                    all_available = False
                    break
            
            if all_available:
                available_slots.append(time_slot)
        
        return available_slots
    
    def create_panel_configuration(self, student: Student, judges: List[Judge]) -> Optional[Tuple[PanelConfiguration, str]]:
        """
        Create an optimal panel configuration for a student.
        
        Args:
            student: Student requiring scheduling
            judges: List of all available judges
            
        Returns:
            Tuple of (PanelConfiguration, status) if successful, None otherwise
            Status can be "Field and Time Match" or "Time Match Only"
        """
        print(f"\n--- Creating panel for {student.name} ---")
        
        # Find supervisors
        supervisor_judges = self.find_supervisor_judges(student, judges)
        if not supervisor_judges:
            print("⚠ No supervisors found")
            return None
        
        # TIER 1: Try field and time matching first
        print("🎯 Attempting field and time matching...")
        panel_result = self._try_field_and_time_match(student, judges, supervisor_judges)
        if panel_result:
            print("✅ Successfully matched both field expertise and time!")
            return panel_result, "Field and Time Match"
        
        # TIER 2: Try time-only matching as fallback
        print("⏰ Field matching failed, trying time-only matching...")
        panel_result = self._try_time_only_match(student, judges, supervisor_judges)
        if panel_result:
            print("✅ Successfully matched time schedule (ignoring field expertise)")
            return panel_result, "Time Match Only"
        
        print("❌ Failed to find any suitable panel configuration")
        return None
    
    def _try_field_and_time_match(self, student: Student, judges: List[Judge], 
                                 supervisor_judges: List[Judge]) -> Optional[PanelConfiguration]:
        """
        Try to create a panel with both field expertise and time matching.
        
        Args:
            student: Student requiring scheduling
            judges: List of all available judges
            supervisor_judges: List of supervisor judges
            
        Returns:
            PanelConfiguration if successful, None otherwise
        """
        # Find expertise matches (excluding supervisors)
        expertise_matches = self.find_expertise_matches(student, judges, supervisor_judges)
        
        # Select exactly 2 examiner judges based on expertise
        constraints = self.config.scheduling_constraints
        required_judges_count = constraints['required_judges']
        
        selected_examiners = self.judge_selector.select_judges_by_expertise(
            expertise_matches,
            student.field1,
            student.field2,
            required_judges_count
        )
        
        examiner_judges = selected_examiners
        print(f"✓ Found {len(supervisor_judges)} supervisors, {len(examiner_judges)} examiners with field expertise")
        
        if len(examiner_judges) < required_judges_count:
            print(f"⚠ Insufficient examiners with field expertise ({len(examiner_judges)}/{required_judges_count})")
            return None
        
        # Find available time slots for all required judges
        all_required_judges = supervisor_judges + examiner_judges
        group_size = 1  # Individual defense
        available_slots = self.find_available_time_slots(all_required_judges, group_size)
        
        if not available_slots:
            print("✗ No available time slots found for field-matched judges")
            return None
        
        # Create panel configuration with first available slot
        panel = PanelConfiguration(
            supervisors=supervisor_judges,
            examiners=examiner_judges,
            time_slot=available_slots[0]
        )
        
        return panel
    
    def _try_time_only_match(self, student: Student, judges: List[Judge], 
                           supervisor_judges: List[Judge]) -> Optional[PanelConfiguration]:
        """
        Try to create a panel with time matching only (ignoring field expertise).
        Prioritizes judges with lower workload for better distribution.
        
        Args:
            student: Student requiring scheduling
            judges: List of all available judges
            supervisor_judges: List of supervisor judges
            
        Returns:
            PanelConfiguration if successful, None otherwise
        """
        # Get all non-supervisor judges (ignore expertise for now)
        supervisor_codes = [judge.code for judge in supervisor_judges]
        available_examiners = [judge for judge in judges if judge.code not in supervisor_codes]
        
        # Sort available examiners by workload (ascending - least loaded first)
        available_examiners = sorted(available_examiners, 
                                   key=lambda j: self.session.get_judge_workload(j.code))
        
        constraints = self.config.scheduling_constraints
        required_judges_count = constraints['required_judges']
        
        if len(available_examiners) < required_judges_count:
            print(f"⚠ Insufficient total examiners ({len(available_examiners)}/{required_judges_count})")
            return None
        
        # Try combinations starting with least loaded judges
        # Use a smarter approach: try combinations prioritizing low workload judges
        best_combo = None
        best_time_slot = None
        best_workload_sum = float('inf')
        
        for examiner_combo in combinations(available_examiners, required_judges_count):
            examiner_judges = list(examiner_combo)
            all_required_judges = supervisor_judges + examiner_judges
            group_size = 1  # Individual defense
            available_slots = self.find_available_time_slots(all_required_judges, group_size)
            
            if available_slots:
                # Calculate total workload for this combination
                combo_workload = sum(self.session.get_judge_workload(judge.code) for judge in examiner_judges)
                
                if combo_workload < best_workload_sum:
                    best_combo = examiner_judges
                    best_time_slot = available_slots[0]
                    best_workload_sum = combo_workload
                    
                    # Log the workload information
                    workload_info = [f"{judge.code}({self.session.get_judge_workload(judge.code)})" for judge in examiner_judges]
                    print(f"🔹 Found better combo with total workload {combo_workload}: {' + '.join(workload_info)}")
                    
                    # If we found a combination with very low workload, use it immediately
                    if combo_workload <= required_judges_count:  # Very low workload
                        break
        
        if best_combo and best_time_slot:
            workload_info = [f"{judge.code}({self.session.get_judge_workload(judge.code)})" for judge in best_combo]
            print(f"✓ Selected best workload combo: {' + '.join(workload_info)} (total: {best_workload_sum})")
            print(f"✓ Found {len(supervisor_judges)} supervisors, {len(best_combo)} examiners (time-only match)")
            
            # Create panel configuration with the best combination
            panel = PanelConfiguration(
                supervisors=supervisor_judges,
                examiners=best_combo,
                time_slot=best_time_slot
            )
            return panel
        
        print("✗ No available time slots found for any examiner combination")
        return None
    
    def schedule_group_defense(self, group: GroupDefense, judges: List[Judge]) -> List[ScheduleResult]:
        """
        Schedule a group defense for multiple students.
        
        Args:
            group: GroupDefense object containing multiple students
            judges: List of available judges
            
        Returns:
            List of ScheduleResult objects (one per student in the group)
        """
        print(f"\n--- Scheduling Group {group.group_id} ({group.get_group_size()} students) ---")
        
        # Use the primary student for panel configuration
        primary_student = group.get_primary_student()
        if not primary_student:
            return [ScheduleResult(
                student=student,
                scheduled=False,
                reason="Empty group",
                status="Failed"
            ) for student in group.students]
        
        # Find supervisors for the group (combine all supervisors)
        all_supervisors = group.get_all_supervisors()
        supervisor_judges = []
        for supervisor_name in all_supervisors:
            found_supervisors = self.find_supervisor_judges(primary_student, judges)
            supervisor_judges.extend(found_supervisors)
        
        # Remove duplicates
        supervisor_judges = list({judge.code: judge for judge in supervisor_judges}.values())
        
        if not supervisor_judges:
            print("⚠ No supervisors found for group")
            return [ScheduleResult(
                student=student,
                scheduled=False,
                reason="No supervisors found",
                status="Failed"
            ) for student in group.students]
        
        # Try to create panel configuration using combined fields
        combined_fields = group.get_combined_fields()
        if len(combined_fields) >= 2:
            primary_student.field1 = combined_fields[0]
            primary_student.field2 = combined_fields[1]
        
        # TIER 1: Try field and time matching first
        print("🎯 Attempting field and time matching for group...")
        panel_result = self._try_field_and_time_match_group(primary_student, judges, supervisor_judges, group.get_group_size())
        if panel_result:
            print("✅ Successfully matched both field expertise and time for group!")
            return self._create_group_results(group, panel_result, "Field and Time Match")
        
        # TIER 2: Try time-only matching as fallback
        print("⏰ Field matching failed, trying time-only matching for group...")
        panel_result = self._try_time_only_match_group(primary_student, judges, supervisor_judges, group.get_group_size())
        if panel_result:
            print("✅ Successfully matched time schedule for group (ignoring field expertise)")
            return self._create_group_results(group, panel_result, "Time Match Only")
        
        print("❌ Failed to find any suitable panel configuration for group")
        return [ScheduleResult(
            student=student,
            scheduled=False,
            reason="No available time slots",
            status="Failed"
        ) for student in group.students]
    
    def _try_field_and_time_match_group(self, primary_student: Student, judges: List[Judge], 
                                       supervisor_judges: List[Judge], group_size: int) -> Optional[PanelConfiguration]:
        """Try to create a panel with both field expertise and time matching for group defense."""
        # Find expertise matches (excluding supervisors)
        expertise_matches = self.find_expertise_matches(primary_student, judges, supervisor_judges)
        
        # Select exactly 2 examiner judges based on expertise
        constraints = self.config.scheduling_constraints
        required_judges_count = constraints['required_judges']
        
        selected_examiners = self.judge_selector.select_judges_by_expertise(
            expertise_matches,
            primary_student.field1,
            primary_student.field2,
            required_judges_count
        )
        
        examiner_judges = selected_examiners
        print(f"✓ Found {len(supervisor_judges)} supervisors, {len(examiner_judges)} examiners with field expertise")
        
        if len(examiner_judges) < required_judges_count:
            print(f"⚠ Insufficient examiners with field expertise ({len(examiner_judges)}/{required_judges_count})")
            return None
        
        # Find available time slots for all required judges (considering group size)
        all_required_judges = supervisor_judges + examiner_judges
        available_slots = self.find_available_time_slots(all_required_judges, group_size)
        
        if not available_slots:
            print("✗ No available time slots found for field-matched judges")
            return None
        
        # Create panel configuration with first available slot
        panel = PanelConfiguration(
            supervisors=supervisor_judges,
            examiners=examiner_judges,
            time_slot=available_slots[0]
        )
        
        return panel
    
    def _try_time_only_match_group(self, primary_student: Student, judges: List[Judge], 
                                  supervisor_judges: List[Judge], group_size: int) -> Optional[PanelConfiguration]:
        """Try to create a panel with time matching only for group defense."""
        # Get all non-supervisor judges (ignore expertise for now)
        supervisor_codes = [judge.code for judge in supervisor_judges]
        available_examiners = [judge for judge in judges if judge.code not in supervisor_codes]
        
        # Sort available examiners by workload (ascending - least loaded first)
        available_examiners = sorted(available_examiners, 
                                   key=lambda j: self.session.get_judge_workload(j.code))
        
        constraints = self.config.scheduling_constraints
        required_judges_count = constraints['required_judges']
        
        if len(available_examiners) < required_judges_count:
            print(f"⚠ Insufficient total examiners ({len(available_examiners)}/{required_judges_count})")
            return None
        
        # Try combinations starting with least loaded judges
        best_combo = None
        best_time_slot = None
        best_workload_sum = float('inf')
        
        for examiner_combo in combinations(available_examiners, required_judges_count):
            examiner_judges = list(examiner_combo)
            all_required_judges = supervisor_judges + examiner_judges
            available_slots = self.find_available_time_slots(all_required_judges, group_size)
            
            if available_slots:
                # Calculate total workload for this combination
                combo_workload = sum(self.session.get_judge_workload(judge.code) for judge in examiner_judges)
                
                if combo_workload < best_workload_sum:
                    best_combo = examiner_judges
                    best_time_slot = available_slots[0]
                    best_workload_sum = combo_workload
                    
                    # Log the workload information
                    workload_info = [f"{judge.code}({self.session.get_judge_workload(judge.code)})" for judge in examiner_judges]
                    print(f"🔹 Found better group combo with total workload {combo_workload}: {' + '.join(workload_info)}")
                    
                    # If we found a combination with very low workload, use it immediately
                    if combo_workload <= required_judges_count:  # Very low workload
                        break
        
        if best_combo and best_time_slot:
            workload_info = [f"{judge.code}({self.session.get_judge_workload(judge.code)})" for judge in best_combo]
            print(f"✓ Selected best workload combo for group: {' + '.join(workload_info)} (total: {best_workload_sum})")
            print(f"✓ Found {len(supervisor_judges)} supervisors, {len(best_combo)} examiners (time-only match)")
            
            # Create panel configuration with the best combination
            panel = PanelConfiguration(
                supervisors=supervisor_judges,
                examiners=best_combo,
                time_slot=best_time_slot
            )
            return panel
        
        print("✗ No available time slots found for any examiner combination")
        return None
    
    def _create_group_results(self, group: GroupDefense, panel: PanelConfiguration, status: str) -> List[ScheduleResult]:
        """Create ScheduleResult objects for all students in a group."""
        if not panel or not panel.is_valid() or not panel.time_slot:
            return [ScheduleResult(
                student=student,
                scheduled=False,
                reason="Invalid panel configuration",
                status="Failed"
            ) for student in group.students]
        
        # Reserve the time slot
        self.session.reserve_time_slot(panel.time_slot, panel.get_all_judge_codes())
        
        # Create results for all students in the group
        results = []
        examiner_codes = [judge.code for judge in panel.examiners]
        
        # Ensure exactly 2 judges (fill with NONE if needed)
        recommendations = []
        recommendations.append(examiner_codes[0] if len(examiner_codes) > 0 else "NONE")
        recommendations.append(examiner_codes[1] if len(examiner_codes) > 1 else "NONE")
        
        for student in group.students:
            result = ScheduleResult(
                student=student,
                scheduled=True,
                time_slot=self.time_formatter.format_time_slot(panel.time_slot),
                panel_judges=panel.get_all_judge_codes(),
                recommended_judges=recommendations,
                reason="Successfully scheduled (group defense)",
                status=f"{status} (Group {group.group_id})"
            )
            results.append(result)
        
        # Log group scheduling success
        student_names = ', '.join([s.name for s in group.students])
        print(f"✓ Group {group.group_id} scheduled at {results[0].time_slot}")
        print(f"✓ Students: {student_names}")
        print(f"✓ Panel: {', '.join(panel.get_all_judge_codes())}")
        print(f"✓ Recommendations: {' | '.join(recommendations)}")
        print(f"✓ Status: {status}")
        
        return results
    
    def schedule_student(self, student: Student, judges: List[Judge]) -> ScheduleResult:
        """
        Schedule a single student's thesis defense.
        
        Args:
            student: Student to schedule
            judges: List of available judges
            
        Returns:
            ScheduleResult with scheduling outcome
        """
        panel_result = self.create_panel_configuration(student, judges)
        
        if panel_result:
            panel, status = panel_result
            
            if panel and panel.is_valid() and panel.time_slot:
                # Reserve the time slot
                self.session.reserve_time_slot(panel.time_slot, panel.get_all_judge_codes())
                
                # Create result with exactly 2 examiner recommendations
                examiner_codes = [judge.code for judge in panel.examiners]
                
                # Ensure exactly 2 judges (fill with NONE if needed)
                recommendations = []
                recommendations.append(examiner_codes[0] if len(examiner_codes) > 0 else "NONE")
                recommendations.append(examiner_codes[1] if len(examiner_codes) > 1 else "NONE")
                
                result = ScheduleResult(
                    student=student,
                    scheduled=True,
                    time_slot=self.time_formatter.format_time_slot(panel.time_slot),
                    panel_judges=panel.get_all_judge_codes(),
                    recommended_judges=recommendations,
                    reason="Successfully scheduled",
                    status=status
                )
                
                print(f"✓ Scheduled at {result.time_slot}")
                print(f"✓ Panel: {', '.join(panel.get_all_judge_codes())}")
                print(f"✓ Recommendations: {' | '.join(recommendations)}")
                print(f"✓ Status: {status}")
                
                return result
        
        # Failed to schedule
        result = ScheduleResult(
            student=student,
            scheduled=False,
            recommended_judges=["NONE", "NONE"],
            reason="No available time slot or insufficient judges",
            status="Not Scheduled"
        )
        
        print(f"✗ Failed to schedule: {result.reason}")
        return result
    
    def schedule_all_students(self, students: List[Student], judges: List[Judge]) -> List[ScheduleResult]:
        """
        Schedule all students avoiding conflicts. Handles both group and individual defenses.
        
        Args:
            students: List of students to schedule
            judges: List of available judges
            
        Returns:
            List of ScheduleResult objects
        """
        # Group students by capstone and separate individuals
        grouped_defenses, individual_students = self.group_students_by_capstone(students)
        
        total_entities = len(grouped_defenses) + len(individual_students)
        print(f"\nProcessing {total_entities} scheduling entities ({len(grouped_defenses)} groups, {len(individual_students)} individuals)...")
        
        results = []
        
        # Process group defenses first (they have more constraints)
        for group in grouped_defenses:
            group_results = self.schedule_group_defense(group, judges)
            results.extend(group_results)
            # Add all students from the group to processed list
            self.session.processed_students.extend(group.students)
        
        # Process individual students
        for student in individual_students:
            result = self.schedule_student(student, judges)
            results.append(result)
            self.session.processed_students.append(student)
        
        self.session.results = results
        return results
    
    def get_session_summary(self) -> Dict:
        """Get summary of the current scheduling session."""
        scheduled_count = sum(1 for r in self.session.results if r.scheduled)
        failed_count = sum(1 for r in self.session.results if not r.scheduled)
        
        # Count group vs individual defenses
        group_defenses = sum(1 for r in self.session.results if r.scheduled and "Group" in (r.status or ""))
        individual_defenses = scheduled_count - group_defenses
        
        return {
            'total_students': len(self.session.processed_students),
            'scheduled_count': scheduled_count,
            'failed_count': failed_count,
            'group_defenses': group_defenses,
            'individual_defenses': individual_defenses,
            'time_slot_utilization': self.session.get_utilization_summary(),
            'judge_workload': self.session.get_workload_summary(),
            'parallel_defenses': self.session.get_parallel_defenses_summary()
        }
