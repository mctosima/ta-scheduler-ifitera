#!/usr/bin/env python3
"""
Main application interface for the Thesis Defense Scheduler.

This module provides the high-level API for running the scheduling system
with different input/output configurations.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import Config
from .models import DataLoader, ScheduleResult
from .scheduler import SchedulingEngine
from .utils import ReportGenerator, ValidationHelper
from .csv_cleaner import AvailabilityCSVCleaner


class ThesisSchedulerApp:
    """Main application class for the thesis scheduler."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the scheduler application.
        
        Args:
            base_dir: Base directory for the project. If None, uses current working directory.
        """
        self.config = Config(base_dir)
        self.engine = SchedulingEngine(self.config)
        self.report_generator = ReportGenerator(self.config)
        
        # Ensure directories exist
        if not self.config.validate_paths():
            raise RuntimeError("Failed to create required directories")
    
    def schedule_from_files(self, availability_file: str, request_file: str, 
                          output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run scheduling from input CSV files.
        
        Args:
            availability_file: Path to judge availability CSV file
            request_file: Path to student requests CSV file  
            output_file: Optional path for output CSV file
            
        Returns:
            Dictionary with scheduling results and summary
        """
        print("="*60)
        print("THESIS DEFENSE SCHEDULER")
        print("="*60)
        
        try:
            # Clean availability file first if it's the raw file
            cleaned_availability_file = self._clean_availability_file_if_needed(availability_file)
            
            # Load data
            print(f"Loading availability data from: {cleaned_availability_file}")
            availability_df = DataLoader.load_availability_data(cleaned_availability_file)
            
            print(f"Loading request data from: {request_file}")
            request_df = DataLoader.load_request_data(request_file)
            
            # Validate data structure
            self._validate_input_data(availability_df, request_df)
            
            # Convert to model objects
            print("Converting data to internal models...")
            judges = self.engine.load_judges(availability_df)
            students = self.engine.load_students(request_df)
            
            print(f"Loaded {len(judges)} judges and {len(students)} students")
            
            # Run scheduling
            print("\nStarting scheduling process...")
            results = self.engine.schedule_all_students(students, judges)
            
            # Save results if output file specified
            if output_file:
                print(f"\nSaving results to: {output_file}")
                DataLoader.save_results(results, request_df, output_file)
            
            # Generate summary
            session_summary = self.engine.get_session_summary()
            summary_text = self.report_generator.generate_scheduling_summary(
                [self._result_to_dict(r) for r in results],
                session_summary['time_slot_utilization'],
                session_summary['judge_workload']
            )
            
            print(f"\n{summary_text}")
            
            return {
                'success': True,
                'results': results,
                'summary': session_summary,
                'summary_text': summary_text
            }
            
        except Exception as e:
            error_msg = f"Scheduling failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'results': [],
                'summary': {}
            }
    
    def schedule_with_default_files(self, use_multiple: bool = True) -> Dict[str, Any]:
        """
        Run scheduling with default file names in input/output directories.
        
        Args:
            use_multiple: If True, uses multiple requests file, otherwise single request
            
        Returns:
            Dictionary with scheduling results and summary
        """
        # Build file paths
        availability_file = str(self.config.get_input_file_path(
            self.config.default_files['availability']
        ))
        
        if use_multiple:
            request_file = str(self.config.get_input_file_path(
                self.config.default_files['multiple_requests']
            ))
            output_filename = self.config.default_files['multiple_requests'].replace(
                '.csv', self.config.default_files['output_suffix']
            )
        else:
            request_file = str(self.config.get_input_file_path(
                self.config.default_files['single_request']
            ))
            output_filename = self.config.default_files['single_request'].replace(
                '.csv', self.config.default_files['output_suffix']
            )
        
        output_file = str(self.config.get_output_file_path(output_filename))
        
        return self.schedule_from_files(availability_file, request_file, output_file)
    
    def _validate_input_data(self, availability_df, request_df):
        """Validate input data structure."""
        # Validate availability data
        required_avail_cols = [
            self.config.column_mappings['availability']['name'],
            self.config.column_mappings['availability']['expertise']
        ]
        if not ValidationHelper.validate_csv_structure(availability_df, required_avail_cols):
            raise ValueError("Invalid availability data structure")
        
        # Validate request data
        # Use the first option from the config lists for validation
        required_request_cols = [
            self.config.column_mappings['request']['student_name'][0],
            self.config.column_mappings['request']['student_id'][0],
            self.config.column_mappings['request']['field1'][0],
            self.config.column_mappings['request']['field2'][0],
            self.config.column_mappings['request']['supervisor1'][0]
        ]
        if not ValidationHelper.validate_csv_structure(request_df, required_request_cols):
            raise ValueError("Invalid request data structure")
        
        # Validate individual student records
        student_required_fields = [
            self.config.column_mappings['request']['student_name'][0],
            self.config.column_mappings['request']['student_id'][0],
            self.config.column_mappings['request']['field1'][0],
            self.config.column_mappings['request']['field2'][0],
            self.config.column_mappings['request']['supervisor1'][0]
        ]
        for _, row in request_df.iterrows():
            if not ValidationHelper.validate_student_data(row.to_dict(), student_required_fields):
                student_name = row.get(student_required_fields[0], 'Unknown')
                raise ValueError(f"Invalid student data for {student_name}")
    
    def _result_to_dict(self, result: ScheduleResult) -> Dict[str, Any]:
        """Convert ScheduleResult to dictionary for reporting."""
        return {
            'student_name': result.student.name,
            'scheduled': result.scheduled,
            'recommended_times': [result.time_slot] if result.time_slot else [],
            'recommended_judges': result.recommended_judges,
            'reason': result.reason
        }
    
    def setup_project_structure(self):
        """Setup the project directory structure with sample files."""
        print("Setting up project directory structure...")
        
        # Create directories
        self.config.validate_paths()
        
        # Copy existing files to appropriate directories
        import shutil
        import os
        
        base_path = self.config.base_dir
        
        # Files to move to input directory
        input_files = [
            'avail_20250610_clean.csv',
            'schedule_request.csv', 
            'schedule_request_multiple.csv'
        ]
        
        # Files to move to output directory
        output_files = [
            'schedule_request_with_recommendations.csv',
            'schedule_request_multiple_with_recommendations.csv'
        ]
        
        # Move files if they exist
        for filename in input_files:
            src = base_path / filename
            dst = self.config.input_dir / filename
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                print(f"Copied {filename} to input directory")
        
        for filename in output_files:
            src = base_path / filename  
            dst = self.config.output_dir / filename
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                print(f"Moved {filename} to output directory")
        
        print("✅ Project structure setup complete!")
        print(f"Input directory: {self.config.input_dir}")
        print(f"Output directory: {self.config.output_dir}")
    
    def _clean_availability_file_if_needed(self, availability_file: str) -> str:
        """
        Clean the availability file if it's in raw format (with merged cells).
        
        Args:
            availability_file: Path to the availability file
            
        Returns:
            Path to the cleaned file (either the original if already clean, or new cleaned file)
        """
        import pandas as pd
        from pathlib import Path
        
        # Check if the file needs cleaning by reading the first few rows
        try:
            # Read first 3 rows to check the format
            sample_df = pd.read_csv(availability_file, nrows=3)
            
            # Check if this looks like a raw file (has merged cell indicators)
            # Raw files have dates like "Tuesday, 10 June 2025" in the header
            needs_cleaning = False
            
            # Check column headers for date patterns
            for col in sample_df.columns:
                if col and (
                    'June 2025' in str(col) or 
                    'July 2025' in str(col) or
                    col.startswith('Unnamed:') or
                    col in ['1', '2', '3', '4']  # Common unnamed columns from merged cells
                ):
                    needs_cleaning = True
                    break
            
            # Also check if first row contains date information
            if not needs_cleaning:
                first_row = sample_df.iloc[0] if len(sample_df) > 0 else None
                if first_row is not None:
                    for value in first_row:
                        if value and ('June 2025' in str(value) or 'July 2025' in str(value)):
                            needs_cleaning = True
                            break
            
            if not needs_cleaning:
                print("✓ Availability file is already in clean format")
                return availability_file
            
            # File needs cleaning
            print("📋 Detecting raw availability file format - cleaning required")
            print("🔧 Automatically cleaning availability file...")
            
            # Create cleaned file path
            input_path = Path(availability_file)
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
            
            # Clean the file
            cleaner = AvailabilityCSVCleaner()
            cleaner.clean_availability_csv(availability_file, str(output_path))
            
            print(f"✅ Cleaned availability file saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"⚠️  Error checking/cleaning availability file: {e}")
            print("📋 Proceeding with original file...")
            return availability_file

def main():
    """Main entry point for the scheduler application."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Thesis Defense Scheduler')
    parser.add_argument('--availability', '-a', 
                       help='Path to availability CSV file')
    parser.add_argument('--requests', '-r',
                       help='Path to requests CSV file')
    parser.add_argument('--output', '-o',
                       help='Path to output CSV file')
    parser.add_argument('--setup', action='store_true',
                       help='Setup project directory structure')
    parser.add_argument('--multiple', action='store_true',
                       help='Use multiple requests file (default)')
    parser.add_argument('--single', action='store_true',
                       help='Use single request file')
    
    args = parser.parse_args()
    
    try:
        app = ThesisSchedulerApp()
        
        if args.setup:
            app.setup_project_structure()
            return
        
        if args.availability and args.requests:
            # Use specified files
            result = app.schedule_from_files(
                args.availability, 
                args.requests, 
                args.output
            )
        else:
            # Use default files
            use_multiple = not args.single  # Default to multiple unless --single specified
            result = app.schedule_with_default_files(use_multiple)
        
        if result['success']:
            print(f"\n✅ Scheduling completed successfully!")
            scheduled = result['summary']['scheduled_count']
            total = result['summary']['total_students']
            print(f"Scheduled {scheduled}/{total} students")
        else:
            print(f"\n❌ Scheduling failed: {result['error']}")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
