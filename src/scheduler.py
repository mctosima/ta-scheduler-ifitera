#!/usr/bin/env python3
"""
Core scheduling engine for the Thesis Defense Scheduler.

This module contains the main scheduling logic that matches students
with available judges based on expertise and availability.
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from .models import Judge, Student, ScheduleResult, PanelConfiguration, SchedulingSession
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
        
        for _, row in request_df.iterrows():
            # Find the first available column for each field
            name = self._get_first_available_value(row, student_name_cols)
            student_id = self._get_first_available_value(row, student_id_cols)
            field1 = self._get_first_available_value(row, field1_cols)
            field2 = self._get_first_available_value(row, field2_cols)
            supervisor1 = self._get_first_available_value(row, supervisor1_cols)
            supervisor2 = self._get_first_available_value(row, supervisor2_cols)
            
            student = Student(
                name=name or '',
                student_id=student_id or '',
                field1=field1 or '',
                field2=field2 or '',
                supervisor1=supervisor1 or '',
                supervisor2=supervisor2 or ''
            )
            students.append(student)
        
        return students
    
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
    
    def find_available_time_slots(self, required_judges: List[Judge]) -> List[str]:
        """
        Find time slots where all required judges are available and not scheduled.
        
        Args:
            required_judges: List of judges that must be available
            
        Returns:
            List of available time slot names
        """
        if not required_judges:
            return []
        
        # Get all possible time slots from first judge
        all_time_slots = list(required_judges[0].availability.keys())
        available_slots = []
        
        for time_slot in all_time_slots:
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
    
    def create_panel_configuration(self, student: Student, judges: List[Judge]) -> Optional[PanelConfiguration]:
        """
        Create an optimal panel configuration for a student.
        
        Args:
            student: Student requiring scheduling
            judges: List of all available judges
            
        Returns:
            PanelConfiguration if successful, None otherwise
        """
        print(f"\n--- Creating panel for {student.name} ---")
        
        # Find supervisors
        supervisor_judges = self.find_supervisor_judges(student, judges)
        if not supervisor_judges:
            print("⚠ No supervisors found")
            return None
        
        # Find expertise matches (excluding supervisors)
        expertise_matches = self.find_expertise_matches(student, judges, supervisor_judges)
        
        # Select exactly 2 examiner judges
        constraints = self.config.scheduling_constraints
        required_judges_count = constraints['required_judges']
        
        selected_examiners = self.judge_selector.select_judges_by_expertise(
            expertise_matches,
            student.field1,
            student.field2,
            required_judges_count
        )
        
        # Use selected examiners directly (they're already Judge objects)
        examiner_judges = selected_examiners
        
        print(f"✓ Found {len(supervisor_judges)} supervisors, {len(examiner_judges)} examiners")
        
        # Find available time slots for all required judges
        all_required_judges = supervisor_judges + examiner_judges
        available_slots = self.find_available_time_slots(all_required_judges)
        
        if not available_slots:
            print("✗ No available time slots found")
            return None
        
        # Create panel configuration with first available slot
        panel = PanelConfiguration(
            supervisors=supervisor_judges,
            examiners=examiner_judges,
            time_slot=available_slots[0]
        )
        
        return panel
    
    def schedule_student(self, student: Student, judges: List[Judge]) -> ScheduleResult:
        """
        Schedule a single student's thesis defense.
        
        Args:
            student: Student to schedule
            judges: List of available judges
            
        Returns:
            ScheduleResult with scheduling outcome
        """
        panel = self.create_panel_configuration(student, judges)
        
        if panel and panel.is_valid():
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
                reason="Successfully scheduled"
            )
            
            print(f"✓ Scheduled at {result.time_slot}")
            print(f"✓ Panel: {', '.join(panel.get_all_judge_codes())}")
            print(f"✓ Recommendations: {' | '.join(recommendations)}")
            
        else:
            # Failed to schedule
            result = ScheduleResult(
                student=student,
                scheduled=False,
                recommended_judges=["NONE", "NONE"],
                reason="No available time slot or insufficient judges"
            )
            
            print(f"✗ Failed to schedule: {result.reason}")
        
        return result
    
    def schedule_all_students(self, students: List[Student], judges: List[Judge]) -> List[ScheduleResult]:
        """
        Schedule all students avoiding conflicts.
        
        Args:
            students: List of students to schedule
            judges: List of available judges
            
        Returns:
            List of ScheduleResult objects
        """
        print(f"Processing {len(students)} students for optimal scheduling...")
        results = []
        
        # Process students in order (could add priority sorting here)
        for student in students:
            result = self.schedule_student(student, judges)
            results.append(result)
            self.session.processed_students.append(student)
        
        self.session.results = results
        return results
    
    def get_session_summary(self) -> Dict:
        """Get summary of the current scheduling session."""
        return {
            'total_students': len(self.session.processed_students),
            'scheduled_count': sum(1 for r in self.session.results if r.scheduled),
            'failed_count': sum(1 for r in self.session.results if not r.scheduled),
            'time_slot_utilization': self.session.get_utilization_summary()
        }
