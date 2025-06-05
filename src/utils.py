#!/usr/bin/env python3
"""
Utility functions for the Thesis Defense Scheduler.

This module contains helper functions for data processing, parsing,
and formatting operations.
"""

import re
import pandas as pd
from typing import List, Dict, Optional, Any
from .config import Config


class DataProcessor:
    """Handles data processing and parsing operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def parse_expertise_codes(self, expertise_string: str) -> List[str]:
        """
        Parse expertise codes from a string.
        
        Args:
            expertise_string: String containing expertise codes separated by semicolons
            
        Returns:
            List of expertise codes
        """
        if pd.isna(expertise_string) or expertise_string == '':
            return []
        
        # Split by semicolon and clean up
        codes = [code.strip() for code in str(expertise_string).split(';')]
        return [code for code in codes if len(code) >= 3]
    
    def get_judge_code(self, expertise_string: str) -> str:
        """
        Extract the primary judge code from expertise string.
        
        Args:
            expertise_string: String containing expertise information
            
        Returns:
            Primary judge code or empty string
        """
        expertise_list = self.parse_expertise_codes(expertise_string)
        if expertise_list:
            return expertise_list[0]  # Return first code (usually the judge code)
        return ""
    
    def normalize_supervisor_code(self, supervisor_name: str, availability_df: pd.DataFrame) -> str:
        """
        Get the supervisor's code from their name or return the name if it's already a code.
        
        Args:
            supervisor_name: Supervisor name or code
            availability_df: DataFrame with judge availability data
            
        Returns:
            Normalized supervisor code
        """
        if len(supervisor_name) <= 4:  # Likely already a code
            return supervisor_name.upper()
        
        # Try to match with judge names to get their code
        name_col = self.config.column_mappings['availability']['name']
        expertise_col = self.config.column_mappings['availability']['expertise']
        for _, judge in availability_df.iterrows():
            # Check if both supervisor_name and judge name are not null/NaN
            judge_name = judge[name_col]
            if (pd.notna(supervisor_name) and pd.notna(judge_name) and 
                str(supervisor_name).lower() in str(judge_name).lower()):
                return self.get_judge_code(judge[expertise_col])
        
        return supervisor_name.upper()
    
    def get_time_slot_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Get time slot column names from availability DataFrame.
        
        Args:
            df: Availability DataFrame
            
        Returns:
            List of time slot column names
        """
        excluded_cols = self.config.column_mappings['availability']['excluded']
        return [col for col in df.columns if col not in excluded_cols]
    
    def convert_availability_to_boolean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert availability columns to boolean values.
        
        Args:
            df: Availability DataFrame
            
        Returns:
            DataFrame with boolean availability columns
        """
        time_cols = self.get_time_slot_columns(df)
        df_copy = df.copy()
        
        for col in time_cols:
            df_copy[col] = df_copy[col].astype(bool)
        
        return df_copy


class TimeFormatter:
    """Handles time formatting operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def format_time_slot(self, time_slot: str) -> str:
        """
        Convert time slot column name to YYYYMMDD-HHMM format.
        
        Args:
            time_slot: Time slot column name (e.g., "Tuesday_10_June_2025_08:00")
            
        Returns:
            Formatted time string
        """
        # Handle the new cleaned format: "Tuesday_10_June_2025_08:00"
        parts = time_slot.split('_')
        if len(parts) >= 5:
            # parts[0] = weekday (Tuesday)
            # parts[1] = date (10)
            # parts[2] = month (June)
            # parts[3] = year (2025)
            # parts[4] = time (08:00)
            
            date = parts[1]
            month = parts[2]
            year = parts[3]
            time = parts[4]
            
            # Define month mapping directly here for now
            month_map = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            month_num = month_map.get(month, '01')
            date_padded = date.zfill(2)
            time_formatted = time.replace(':', '')
            
            return f"{year}{month_num}{date_padded}-{time_formatted}"
        
        # Fallback: if the format doesn't match expected pattern, return as-is
        return time_slot


class JudgeSelector:
    """Handles judge selection logic with workload balancing."""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = None  # Will be set by SchedulingEngine
    
    def set_session(self, session):
        """Set the scheduling session for workload tracking."""
        self.session = session
    
    def select_judges_by_expertise(self, available_judges, 
                                 field1: str, field2: str, max_judges: int = 2):
        """
        Select judges based on expertise matching with priority system and workload balancing.
        
        Args:
            available_judges: List of available Judge objects or dictionaries
            field1: First required field
            field2: Second required field
            max_judges: Maximum number of judges to select
            
        Returns:
            List of selected judges (same type as input)
        """
        if not available_judges:
            return []
        
        field1_upper = field1.upper()
        field2_upper = field2.upper()
        
        # Separate judges by expertise match
        field1_matches = []
        field2_matches = []
        other_judges = []
        
        for judge in available_judges:
            # Handle both Judge objects and dictionaries
            if hasattr(judge, 'has_expertise_in'):
                # Judge object
                if judge.has_expertise_in(field1_upper):
                    field1_matches.append(judge)
                elif judge.has_expertise_in(field2_upper):
                    field2_matches.append(judge)
                else:
                    other_judges.append(judge)
            else:
                # Dictionary - use existing logic
                from .config import Config
                processor = DataProcessor(Config())
                expertise = processor.parse_expertise_codes(judge.get('Sub_Keilmuan', ''))
                
                if field1_upper in expertise:
                    field1_matches.append(judge)
                elif field2_upper in expertise:
                    field2_matches.append(judge)
                else:
                    other_judges.append(judge)
        
        # Sort each category by workload (ascending - least loaded first)
        if self.session:
            field1_matches = self._sort_by_workload(field1_matches)
            field2_matches = self._sort_by_workload(field2_matches)
            other_judges = self._sort_by_workload(other_judges)
        
        # Select judges with priority
        selected_judges: List[Any] = []
        
        # Priority 1: Field 1 matches (least loaded first)
        if field1_matches and len(selected_judges) < max_judges:
            selected_judges.append(field1_matches[0])
            if self.session:
                print(f"🔹 Selected {self._get_judge_code(field1_matches[0])} for field1 '{field1}' (workload: {self.session.get_judge_workload(self._get_judge_code(field1_matches[0]))})")
        
        # Priority 2: Field 2 matches (different from field 1 match, least loaded first)
        if field2_matches and len(selected_judges) < max_judges:
            for judge in field2_matches:
                if judge not in selected_judges:
                    selected_judges.append(judge)
                    if self.session:
                        print(f"🔹 Selected {self._get_judge_code(judge)} for field2 '{field2}' (workload: {self.session.get_judge_workload(self._get_judge_code(judge))})")
                    break
        
        # Priority 3: Fill remaining slots with any available judges (least loaded first)
        if len(selected_judges) < max_judges:
            remaining_judges = [j for j in available_judges if j not in selected_judges]
            remaining_judges = self._sort_by_workload(remaining_judges) if self.session else remaining_judges
            
            for judge in remaining_judges:
                if len(selected_judges) >= max_judges:
                    break
                selected_judges.append(judge)
                if self.session:
                    print(f"🔹 Selected {self._get_judge_code(judge)} as fallback (workload: {self.session.get_judge_workload(self._get_judge_code(judge))})")
        
        return selected_judges
    
    def _sort_by_workload(self, judges):
        """Sort judges by current workload (ascending - least loaded first)."""
        if not self.session:
            return judges
        
        return sorted(judges, key=lambda j: self.session.get_judge_workload(self._get_judge_code(j)))
    
    def _get_judge_code(self, judge):
        """Get judge code from either Judge object or dictionary."""
        if hasattr(judge, 'code'):
            return judge.code
        else:
            # Handle dictionary format
            return judge.get('code', judge.get('Sub_Keilmuan', 'Unknown'))


class ValidationHelper:
    """Provides validation utilities."""
    
    @staticmethod
    def validate_csv_structure(df: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        Validate that DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            True if valid, False otherwise
        """
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            return False
        return True
    
    @staticmethod
    def validate_student_data(row: Dict[str, Any], required_fields: Optional[List[str]] = None) -> bool:
        """
        Validate student request data.
        
        Args:
            row: Dictionary containing student data
            required_fields: List of required field names (defaults to hardcoded values for backward compatibility)
            
        Returns:
            True if valid, False otherwise
        """
        if required_fields is None:
            required_fields = ['Nama', 'Nim', 'Field 1', 'Field 2', 'SPV 1']
        
        for field in required_fields:
            if not row.get(field) or pd.isna(row.get(field)):
                student_name = row.get(required_fields[0] if required_fields else 'Nama', 'Unknown')
                print(f"Missing required field: {field} for student {student_name}")
                return False
        
        return True


class ReportGenerator:
    """Generates summary reports and statistics."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_scheduling_summary(self, results: List, scheduled_slots: Dict[str, List[str]], 
                                  judge_workload: Optional[Dict[str, int]] = None,
                                  parallel_defenses: Optional[Dict[str, int]] = None) -> str:
        """
        Generate a comprehensive scheduling summary.
        
        Args:
            results: List of scheduling results
            scheduled_slots: Dictionary of scheduled time slots
            judge_workload: Dictionary of judge workload counts (optional)
            
        Returns:
            Formatted summary string
        """
        total_count = len(results)
        scheduled_count = sum(1 for r in results if r.get('scheduled', False))
        failed_count = total_count - scheduled_count
        
        summary = []
        summary.append("="*60)
        summary.append("THESIS DEFENSE SCHEDULING SUMMARY")  
        summary.append("="*60)
        summary.append(f"Total requests: {total_count}")
        summary.append(f"Successfully scheduled: {scheduled_count}")
        summary.append(f"Failed to schedule: {failed_count}")
        summary.append(f"Success rate: {(scheduled_count/total_count*100):.1f}%")
        
        # Add status breakdown if available
        if results and any(r.get('status') for r in results):
            status_counts: Dict[str, int] = {}
            for result in results:
                status = result.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            summary.append("\n📊 SCHEDULING STATUS BREAKDOWN:")
            for status, count in status_counts.items():
                percentage = (count/total_count*100)
                summary.append(f"   • {status}: {count} students ({percentage:.1f}%)")
        
        if scheduled_count > 0:
            summary.append("\n🗓️  SCHEDULED DEFENSES:")
            for result in results:
                if result.get('scheduled', False):
                    name = result.get('student_name', 'Unknown')
                    time_slot = result.get('recommended_times', ['Unknown'])[0]
                    judges = ' | '.join(result.get('recommended_judges', ['NONE', 'NONE']))
                    status = result.get('status', '')
                    summary.append(f"   • {name} - {time_slot} - Judges: {judges} - {status}")
        
        if failed_count > 0:
            summary.append("\n❌ FAILED TO SCHEDULE:")
            for result in results:
                if not result.get('scheduled', False):
                    name = result.get('student_name', 'Unknown')
                    reason = result.get('reason', 'Unknown error')
                    judges = ' | '.join(result.get('recommended_judges', ['NONE', 'NONE']))
                    summary.append(f"   • {name} - {reason} - Judges: {judges}")
        
        if scheduled_slots:
            summary.append("\n⏰ TIME SLOT UTILIZATION:")
            time_formatter = TimeFormatter(self.config)
            for time_slot, judges in scheduled_slots.items():
                formatted_time = time_formatter.format_time_slot(time_slot)
                summary.append(f"   • {formatted_time}: {' | '.join(judges)}")
        
        # Add workload balancing summary
        if judge_workload:
            summary.append("\n⚖️  JUDGE WORKLOAD DISTRIBUTION:")
            # Sort judges by workload (descending)
            sorted_workload = sorted(judge_workload.items(), key=lambda x: x[1], reverse=True)
            
            total_assignments = sum(judge_workload.values())
            avg_workload = total_assignments / len(judge_workload) if judge_workload else 0
            
            summary.append(f"   Total assignments: {total_assignments}")
            summary.append(f"   Average per judge: {avg_workload:.1f}")
            summary.append("   Individual workloads:")
            
            for judge_code, count in sorted_workload:
                if count > 0:  # Only show judges with assignments
                    deviation = count - avg_workload
                    indicator = "🔴" if deviation > 1 else "🟡" if deviation > 0 else "🟢"
                    summary.append(f"     {indicator} {judge_code}: {count} assignments")
        
        return "\n".join(summary)
