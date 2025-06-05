#!/usr/bin/env python3
"""
Configuration module for the Thesis Defense Scheduler.

This module handles all configuration settings including file paths,
constraints, and system parameters.
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from typing import Dict, List


class Config:
    """Configuration class for the thesis scheduler."""
    
    def __init__(self, base_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize configuration with dynamic path resolution.
        
        Args:
            base_dir: Base directory for the project. If None, uses current working directory.
            config_file: Path to config.ini file. If None, uses default location.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_file = config_file or str(self.base_dir / "config.ini")
        self.config = configparser.ConfigParser()
        
        # Load configuration from INI file if it exists
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        
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
        """Get default file names from config file or use defaults."""
        return {
            'availability': self.config.get('FILES', 'availability_file', fallback='avail_20250610_clean.csv'),
            'single_request': self.config.get('FILES', 'single_request_file', fallback='schedule_request.csv'),
            'multiple_requests': self.config.get('FILES', 'multiple_request_file', fallback='schedule_request_multiple.csv'),
            'output_suffix': self.config.get('FILES', 'output_suffix', fallback='_with_recommendations.csv')
        }
    
    @property
    def scheduling_constraints(self) -> Dict[str, int]:
        """Get scheduling constraints from config file or use defaults."""
        return {
            'required_judges': self.config.getint('SCHEDULING', 'required_judges', fallback=2),
            'max_panel_size': self.config.getint('SCHEDULING', 'max_panel_size', fallback=5),
            'max_recommendations': self.config.getint('SCHEDULING', 'max_recommendations', fallback=5)
        }
    
    @property
    def column_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get column name mappings for CSV files from config file or use defaults."""
        return {
            'availability': {
                'name': self.config.get('COLUMNS', 'availability_name_col', fallback='Nama_Dosen'),
                'expertise': self.config.get('COLUMNS', 'availability_expertise_col', fallback='Sub_Keilmuan'),
                'excluded': self.config.get('COLUMNS', 'availability_excluded_cols', fallback='Nama_Dosen,Unknown_Col_5,Sub_Keilmuan').split(',')
            },
            'request': {
                'student_name': self.config.get('COLUMNS', 'request_student_name_cols', fallback='Nama,nama').split(','),
                'student_id': self.config.get('COLUMNS', 'request_student_id_cols', fallback='Nim,nim').split(','),
                'field1': self.config.get('COLUMNS', 'request_field1_cols', fallback='Field 1,field1').split(','),
                'field2': self.config.get('COLUMNS', 'request_field2_cols', fallback='Field 2,field2').split(','),
                'supervisor1': self.config.get('COLUMNS', 'request_supervisor1_cols', fallback='SPV 1,spv1').split(','),
                'supervisor2': self.config.get('COLUMNS', 'request_supervisor2_cols', fallback='SPV 2,spv2').split(',')
            },
            'output': {
                'datetime': self.config.get('COLUMNS', 'output_datetime_col', fallback='Date Time (YYYYMMDD-HHMM)'),
                'recommendations': 'List of recommendation'
            }
        }
    
    @property
    def time_format(self) -> Dict[str, str]:
        """Get time formatting configuration from config file or use defaults."""
        return {
            'output_format': self.config.get('TIME_FORMAT', 'output_format', fallback='%Y%m%d-%H%M'),
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
