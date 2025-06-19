#!/usr/bin/env python3
"""
Thesis Defense Scheduler - Main Entry Point

A comprehensive scheduling system for thesis defense sessions that matches
students with available judges based on supervisor availability and expertise fields.

Features:
- Expertise-based judge matching
- Conflict-free time slot scheduling  
- Exactly 2 judge recommendations per student
- Supervisor exclusion from examiner recommendations
- Dynamic path handling for cross-platform compatibility
- Modular, clean code architecture

Usage:
    python main.py --setup                    # Setup project structure
    python main.py                            # Use default files (multiple requests)
    python main.py --single                   # Use single request file
    python main.py -a avail.csv -r req.csv    # Use specific files
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from src.main import main

if __name__ == "__main__":
    main()
