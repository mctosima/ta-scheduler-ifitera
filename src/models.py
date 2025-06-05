#!/usr/bin/env python3
"""
Data models for the Thesis Defense Scheduler.

This module contains classes that represent the core data structures
used throughout the scheduling system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import pandas as pd


@dataclass
class Judge:
    """Represents a judge/lecturer with their availability and expertise."""
    
    name: str
    code: str
    expertise: List[str]
    availability: Dict[str, bool] = field(default_factory=dict)
    
    def is_available_at(self, time_slot: str) -> bool:
        """Check if judge is available at specific time slot."""
        return self.availability.get(time_slot, False)
    
    def has_expertise_in(self, field: str) -> bool:
        """Check if judge has expertise in specific field."""
        return field.upper() in [exp.upper() for exp in self.expertise]


@dataclass
class Student:
    """Represents a student with their thesis defense request."""
    
    name: str
    student_id: str
    field1: str
    field2: str
    supervisor1: str
    supervisor2: Optional[str] = None
    
    def get_required_fields(self) -> List[str]:
        """Get list of required expertise fields."""
        fields = [self.field1.upper(), self.field2.upper()]
        return [f for f in fields if f]
    
    def get_supervisors(self) -> List[str]:
        """Get list of supervisors (excluding '-' placeholders)."""
        supervisors = []
        if self.supervisor1 and self.supervisor1.strip() != "-":
            supervisors.append(self.supervisor1)
        if self.supervisor2 and self.supervisor2.strip() != "-":
            supervisors.append(self.supervisor2)
        return supervisors


@dataclass
class ScheduleResult:
    """Represents the result of a scheduling attempt."""
    
    student: Student
    scheduled: bool = False
    time_slot: Optional[str] = None
    panel_judges: List[str] = field(default_factory=list)
    recommended_judges: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    
    def get_formatted_time(self) -> str:
        """Get formatted time slot string."""
        if not self.time_slot:
            return "NOT_SCHEDULED"
        return self.time_slot
    
    def get_recommendations_string(self) -> str:
        """Get recommendations as formatted string."""
        if len(self.recommended_judges) >= 2:
            return f"{self.recommended_judges[0]} | {self.recommended_judges[1]}"
        elif len(self.recommended_judges) == 1:
            return f"{self.recommended_judges[0]} | NONE"
        else:
            return "NONE | NONE"
    
    def get_penguji_1(self) -> str:
        """Get first judge (Penguji 1)."""
        if len(self.recommended_judges) >= 1:
            return self.recommended_judges[0]
        else:
            return "NONE"
    
    def get_penguji_2(self) -> str:
        """Get second judge (Penguji 2)."""
        if len(self.recommended_judges) >= 2:
            return self.recommended_judges[1]
        else:
            return "NONE"


@dataclass
class PanelConfiguration:
    """Represents a panel configuration for thesis defense."""
    
    supervisors: List[Judge] = field(default_factory=list)
    examiners: List[Judge] = field(default_factory=list)
    time_slot: Optional[str] = None
    
    def get_all_judges(self) -> List[Judge]:
        """Get all judges in the panel."""
        return self.supervisors + self.examiners
    
    def get_all_judge_codes(self) -> List[str]:
        """Get all judge codes in the panel."""
        return [judge.code for judge in self.get_all_judges()]
    
    def is_valid(self) -> bool:
        """Check if panel configuration is valid."""
        return len(self.supervisors) > 0 and self.time_slot is not None


@dataclass
class SchedulingSession:
    """Represents a scheduling session with conflict tracking."""
    
    scheduled_slots: Dict[str, List[str]] = field(default_factory=dict)
    processed_students: List[Student] = field(default_factory=list)
    results: List[ScheduleResult] = field(default_factory=list)
    
    def reserve_time_slot(self, time_slot: str, judge_codes: List[str]):
        """Reserve a time slot for specific judges."""
        if time_slot not in self.scheduled_slots:
            self.scheduled_slots[time_slot] = []
        
        for code in judge_codes:
            if code not in self.scheduled_slots[time_slot]:
                self.scheduled_slots[time_slot].append(code)
    
    def is_judge_available(self, judge_code: str, time_slot: str) -> bool:
        """Check if judge is available at time slot (not already scheduled)."""
        return (time_slot not in self.scheduled_slots or 
                judge_code not in self.scheduled_slots[time_slot])
    
    def get_utilization_summary(self) -> Dict[str, List[str]]:
        """Get summary of time slot utilization."""
        return dict(self.scheduled_slots)


class DataLoader:
    """Handles loading and parsing CSV data."""
    
    @staticmethod
    def load_availability_data(file_path: str) -> pd.DataFrame:
        """Load judge availability data from CSV."""
        try:
            df = pd.read_csv(file_path)
            print(f"Loaded availability data: {len(df)} judges")
            return df
        except Exception as e:
            raise Exception(f"Error loading availability data: {e}")
    
    @staticmethod
    def load_request_data(file_path: str) -> pd.DataFrame:
        """Load thesis defense requests from CSV."""
        try:
            # Try to load with comment handling first
            try:
                df = pd.read_csv(file_path, comment='//')
            except:
                df = pd.read_csv(file_path)
            
            # Remove empty rows
            df = df.dropna(subset=['Nama', 'Nim'])
            print(f"Loaded request data: {len(df)} requests")
            return df
        except Exception as e:
            raise Exception(f"Error loading request data: {e}")
    
    @staticmethod
    def save_results(results: List[ScheduleResult], original_df: pd.DataFrame, 
                    output_path: str) -> pd.DataFrame:
        """Save scheduling results to CSV."""
        try:
            updated_rows = []
            
            for i, result in enumerate(results):
                # Get original row data
                original_row = original_df.iloc[i].to_dict()
                
                # Update with scheduling results
                if result.scheduled:
                    original_row['Tanggal dan Waktu (Format: YYYYMMDD-HHMM)'] = result.get_formatted_time()
                    original_row['Penguji 1'] = result.get_penguji_1()
                    original_row['Penguji 2'] = result.get_penguji_2()
                else:
                    original_row['Tanggal dan Waktu (Format: YYYYMMDD-HHMM)'] = f"NOT_SCHEDULED: {result.reason}"
                    original_row['Penguji 1'] = result.get_penguji_1()
                    original_row['Penguji 2'] = result.get_penguji_2()
                
                updated_rows.append(original_row)
            
            # Create DataFrame and save
            updated_df = pd.DataFrame(updated_rows)
            updated_df.to_csv(output_path, index=False)
            
            print(f"✅ Results saved to: {output_path}")
            return updated_df
            
        except Exception as e:
            raise Exception(f"Error saving results: {e}")
