#!/usr/bin/env python3
"""
Configuration module for the Thesis Defense Scheduler.

This module handles all configuration settings including file paths,
constraints, and system parameters.
"""

import os
from pathlib import Path
from typing import Dict, List


class Config:
    """Configuration class for the thesis scheduler."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize configuration with dynamic path resolution.
        
        Args:
            base_dir: Base directory for the project. If None, uses current working directory.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self._setup_directories()
    
    def _setup_directories(self):
        """Setup input and output directories."""
        self.input_dir = self.base_dir / "input"
        self.output_dir = self.base_dir / "output"
        self.src_dir = self.base_dir / "src"
        
        # Create directories if they don't exist
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.src_dir.mkdir(exist_ok=True)
    
    @property
    def paths(self) -> Dict[str, Path]:
        """Get all configured paths."""
        return {
            'base': self.base_dir,
            'input': self.input_dir,
            'output': self.output_dir,
            'src': self.src_dir
        }
    
    @property
    def default_files(self) -> Dict[str, str]:
        """Get default file names."""
        return {
            'availability': 'avail_20250610_clean.csv',
            'single_request': 'schedule_request.csv',
            'multiple_requests': 'schedule_request_multiple.csv',
            'output_suffix': '_with_recommendations.csv'
        }
    
    @property
    def scheduling_constraints(self) -> Dict[str, int]:
        """Get scheduling constraints."""
        return {
            'required_judges': 2,  # Exactly 2 judges required
            'max_panel_size': 5,   # Maximum panel size including supervisors
            'max_recommendations': 5  # Maximum time slot recommendations
        }
    
    @property
    def column_mappings(self) -> Dict[str, List[str]]:
        """Get column name mappings for CSV files."""
        return {
            'availability': {
                'name': 'Nama_Dosen',
                'expertise': 'Sub_Keilmuan',
                'excluded': ['Nama_Dosen', 'Unknown_Col_5', 'Sub_Keilmuan']
            },
            'request': {
                'student_name': ['Nama', 'nama'],
                'student_id': ['Nim', 'nim'],
                'field1': ['Field 1', 'field1'],
                'field2': ['Field 2', 'field2'],
                'supervisor1': ['SPV 1', 'spv1'],
                'supervisor2': ['SPV 2', 'spv2']
            },
            'output': {
                'datetime': 'Date Time (YYYYMMDD-HHMM)',
                'recommendations': 'List of recommendation'
            }
        }
    
    @property
    def time_format(self) -> Dict[str, str]:
        """Get time formatting configuration."""
        return {
            'output_format': '%Y%m%d-%H%M',
            'month_mapping': {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
        }
    
    def get_input_file_path(self, filename: str) -> Path:
        """Get full path for input file."""
        return self.input_dir / filename
    
    def get_output_file_path(self, filename: str) -> Path:
        """Get full path for output file."""
        return self.output_dir / filename
    
    def validate_paths(self) -> bool:
        """Validate that all required directories exist."""
        try:
            required_dirs = [self.input_dir, self.output_dir]
            for directory in required_dirs:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error validating paths: {e}")
            return False
