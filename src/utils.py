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
        for _, judge in availability_df.iterrows():
            if supervisor_name.lower() in judge['Nama_Dosen'].lower():
                return self.get_judge_code(judge['Sub_Keilmuan'])
        
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
        # Extract date and time from column name
        parts = time_slot.split('_')
        if len(parts) >= 5:
            day = parts[0]
            date = parts[1]
            month = parts[2]
            year = parts[3]
            time = parts[4]
            
            # Get month mapping from config
            month_map = self.config.time_format['month_mapping']
            month_num = month_map.get(month, '01')
            date_padded = date.zfill(2)
            time_formatted = time.replace(':', '')
            
            return f"{year}{month_num}{date_padded}-{time_formatted}"
        return time_slot


class JudgeSelector:
    """Handles judge selection logic."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def select_judges_by_expertise(self, available_judges: List[Dict], 
                                 field1: str, field2: str, max_judges: int = 2) -> List[Dict]:
        """
        Select judges based on expertise matching with priority system.
        
        Args:
            available_judges: List of available judge dictionaries
            field1: First required field
            field2: Second required field
            max_judges: Maximum number of judges to select
            
        Returns:
            List of selected judges
        """
        if not available_judges:
            return []
        
        field1_upper = field1.upper()
        field2_upper = field2.upper()
        
        # Create data processor for expertise parsing
        from .config import Config
        processor = DataProcessor(Config())
        
        # Separate judges by expertise match
        field1_matches = []
        field2_matches = []
        other_judges = []
        
        for judge in available_judges:
            expertise = processor.parse_expertise_codes(judge.get('Sub_Keilmuan', ''))
            
            if field1_upper in expertise:
                field1_matches.append(judge)
            elif field2_upper in expertise:
                field2_matches.append(judge)
            else:
                other_judges.append(judge)
        
        # Select judges with priority
        selected_judges = []
        
        # Priority 1: Field 1 matches
        if field1_matches and len(selected_judges) < max_judges:
            selected_judges.append(field1_matches[0])
        
        # Priority 2: Field 2 matches (different from field 1 match)
        if field2_matches and len(selected_judges) < max_judges:
            for judge in field2_matches:
                if judge not in selected_judges:
                    selected_judges.append(judge)
                    break
        
        # Priority 3: Fill remaining slots with any available judges
        if len(selected_judges) < max_judges:
            remaining_judges = [j for j in available_judges if j not in selected_judges]
            for judge in remaining_judges:
                if len(selected_judges) >= max_judges:
                    break
                selected_judges.append(judge)
        
        return selected_judges


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
    def validate_student_data(row: Dict[str, Any]) -> bool:
        """
        Validate student request data.
        
        Args:
            row: Dictionary containing student data
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['Nama', 'Nim', 'Field 1', 'Field 2', 'SPV 1']
        
        for field in required_fields:
            if not row.get(field) or pd.isna(row.get(field)):
                print(f"Missing required field: {field} for student {row.get('Nama', 'Unknown')}")
                return False
        
        return True


class ReportGenerator:
    """Generates summary reports and statistics."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_scheduling_summary(self, results: List, scheduled_slots: Dict[str, List[str]]) -> str:
        """
        Generate a comprehensive scheduling summary.
        
        Args:
            results: List of scheduling results
            scheduled_slots: Dictionary of scheduled time slots
            
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
        
        if scheduled_count > 0:
            summary.append("\n🗓️  SCHEDULED DEFENSES:")
            for result in results:
                if result.get('scheduled', False):
                    name = result.get('student_name', 'Unknown')
                    time_slot = result.get('recommended_times', ['Unknown'])[0]
                    judges = ' | '.join(result.get('recommended_judges', ['NONE', 'NONE']))
                    summary.append(f"   • {name} - {time_slot} - Judges: {judges}")
        
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
        
        return "\n".join(summary)
