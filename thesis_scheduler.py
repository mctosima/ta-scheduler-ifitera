#!/usr/bin/env python3
"""
Thesis Defense Scheduler

This script matches thesis defense requests with available judges based on:
1. Supervisor (SPV) availability
2. Field expertise matching (Field 1 and Field 2)
3. Available time slots

The script generates recommendations for optimal scheduling.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
import re

class ThesisScheduler:
    def __init__(self, availability_file: str, request_file: str):
        """
        Initialize the scheduler with availability and request data.
        
        Args:
            availability_file: Path to the cleaned availability CSV
            request_file: Path to the schedule request CSV
        """
        self.availability_file = availability_file
        self.request_file = request_file
        self.availability_df = None
        self.request_df = None
        self.scheduled_slots = {}  # Track assigned time slots: {time_slot: [judge_codes]}
        self.load_data()
    
    def load_data(self):
        """Load and parse the CSV files."""
        print("Loading availability data...")
        self.availability_df = pd.read_csv(self.availability_file)
        
        print("Loading request data...")
        # Skip comment lines that start with //
        try:
            self.request_df = pd.read_csv(self.request_file, comment='//')
        except:
            # If that fails, try without comment handling
            self.request_df = pd.read_csv(self.request_file)
        
        # Clean up the data
        self._clean_availability_data()
        self._clean_request_data()
        
        # Debug: Print column names to verify structure
        print(f"Request CSV columns: {list(self.request_df.columns)}")
        
        # Standardize column names to handle variations
        if 'SPV 1' in self.request_df.columns and 'SPV 2' in self.request_df.columns:
            print("Found SPV 1 and SPV 2 columns - using two supervisor format")
        elif 'SPV' in self.request_df.columns:
            print("Found single SPV column - converting to two supervisor format")
            # Add empty SPV 2 column for compatibility
            self.request_df['SPV 2'] = ''
            # Rename SPV to SPV 1
            self.request_df = self.request_df.rename(columns={'SPV': 'SPV 1'})
    
    def _clean_availability_data(self):
        """Clean and process the availability data."""
        # Extract time slot columns (all columns except first, second, and last)
        time_cols = [col for col in self.availability_df.columns 
                    if col not in ['Nama_Dosen', 'Unknown_Col_5', 'Sub_Keilmuan']]
        
        # Convert availability to boolean
        for col in time_cols:
            self.availability_df[col] = self.availability_df[col].astype(bool)
        
        print(f"Loaded {len(self.availability_df)} judges with {len(time_cols)} time slots")
    
    def _clean_request_data(self):
        """Clean and process the request data."""
        # Remove any empty rows
        self.request_df = self.request_df.dropna(subset=['Nama', 'Nim'])
        print(f"Loaded {len(self.request_df)} thesis defense requests")
    
    def _parse_expertise(self, expertise_string: str) -> List[str]:
        """Parse expertise codes from a string."""
        if pd.isna(expertise_string) or expertise_string == '':
            return []
        
        # Split by semicolon and clean up
        codes = [code.strip() for code in str(expertise_string).split(';')]
        return [code for code in codes if len(code) >= 3]
    
    def _get_judge_code(self, judge_expertise: str) -> str:
        """Extract the judge code from expertise string."""
        expertise_list = self._parse_expertise(judge_expertise)
        if expertise_list:
            return expertise_list[0]  # Return first code which is usually the judge code
        return ""
    
    def _get_supervisor_code(self, supervisor_name: str) -> str:
        """Get the supervisor's code from their name or return the name if it's already a code."""
        if len(supervisor_name) <= 4:  # Likely already a code
            return supervisor_name.upper()
        
        # Try to match with judge names to get their code
        for _, judge in self.availability_df.iterrows():
            if supervisor_name.lower() in judge['Nama_Dosen'].lower():
                return self._get_judge_code(judge['Sub_Keilmuan'])
        
        return supervisor_name.upper()
    
    def find_available_judges(self, field1: str, field2: str, spv1: str, spv2: str = "") -> Dict:
        """
        Find judges available for the given fields and supervisors.
        
        Args:
            field1: First expertise field required
            field2: Second expertise field required
            spv1: First supervisor name or code
            spv2: Second supervisor name or code (optional, "-" indicates no second supervisor)
            
        Returns:
            Dictionary with available judges and their time slots
        """
        supervisor1_code = self._get_supervisor_code(spv1)
        # Treat "-" as no supervisor (common convention for indicating single supervisor)
        supervisor2_code = self._get_supervisor_code(spv2) if spv2 and spv2.strip() != "-" else ""
        
        # Find judges with matching expertise
        matching_judges = []
        supervisor1_judge = None
        supervisor2_judge = None
        
        for _, judge in self.availability_df.iterrows():
            # Convert Series to dict for easier handling
            judge_dict = judge.to_dict()
            judge_expertise = self._parse_expertise(judge_dict['Sub_Keilmuan'])
            judge_name = judge_dict['Nama_Dosen']
            
            # Check if this is supervisor 1
            if (supervisor1_code in judge_expertise or 
                spv1.lower() in judge_name.lower() or
                supervisor1_code.upper() == judge_name.upper()):
                supervisor1_judge = judge_dict
            
            # Check if this is supervisor 2 (if provided and not "-")
            if spv2 and spv2.strip() != "-" and (supervisor2_code in judge_expertise or 
                spv2.lower() in judge_name.lower() or
                supervisor2_code.upper() == judge_name.upper()):
                supervisor2_judge = judge_dict
            
            # Check if judge has matching expertise for field1 or field2
            if any(exp in [field1.upper(), field2.upper()] for exp in judge_expertise):
                matching_judges.append(judge_dict)
        
        return {
            'supervisor1': supervisor1_judge,
            'supervisor2': supervisor2_judge,
            'expertise_matches': matching_judges,
            'all_judges': self.availability_df.to_dict('records')
        }
    
    def is_judge_available_at_time(self, judge_code: str, time_slot: str) -> bool:
        """
        Check if a judge is available at a specific time slot and not already scheduled.
        
        Args:
            judge_code: The judge's code
            time_slot: The time slot column name
            
        Returns:
            True if judge is available and not scheduled, False otherwise
        """
        # Check if already scheduled at this time
        if time_slot in self.scheduled_slots:
            if judge_code in self.scheduled_slots[time_slot]:
                return False
        
        # Check availability in the CSV
        for _, judge in self.availability_df.iterrows():
            if self._get_judge_code(judge['Sub_Keilmuan']) == judge_code:
                return bool(judge[time_slot])
        
        return False
    
    def reserve_time_slot(self, time_slot: str, judge_codes: List[str]):
        """
        Reserve a time slot for specific judges.
        
        Args:
            time_slot: The time slot to reserve
            judge_codes: List of judge codes to reserve the slot for
        """
        if time_slot not in self.scheduled_slots:
            self.scheduled_slots[time_slot] = []
        
        for code in judge_codes:
            if code not in self.scheduled_slots[time_slot]:
                self.scheduled_slots[time_slot].append(code)
    
    def find_optimal_schedule(self, requests: List[Dict]) -> List[Dict]:
        """
        Find optimal schedule for all requests avoiding conflicts.
        
        Args:
            requests: List of thesis defense requests
            
        Returns:
            List of scheduled recommendations
        """
        scheduled_recommendations = []
        
        # Sort requests by priority (could be by date requested, etc.)
        # For now, process in order
        
        for request in requests:
            print(f"\n--- Scheduling for {request['student_name']} ---")
            
            # Find available judges for this request
            judges_info = self.find_available_judges(
                request['fields'][0], 
                request['fields'][1], 
                request['supervisor1'],
                request['supervisor2']
            )
            
            # Check if supervisors are found
            supervisors_found = []
            supervisor_codes = []
            
            if judges_info['supervisor1']:
                supervisors_found.append(judges_info['supervisor1'])
                supervisor_codes.append(self._get_judge_code(judges_info['supervisor1']['Sub_Keilmuan']))
                print(f"✓ Supervisor 1: {supervisor_codes[-1]}")
            else:
                print(f"⚠ Supervisor 1 '{request['supervisor1']}' not found")
            
            if judges_info['supervisor2']:
                supervisors_found.append(judges_info['supervisor2'])
                supervisor_codes.append(self._get_judge_code(judges_info['supervisor2']['Sub_Keilmuan']))
                print(f"✓ Supervisor 2: {supervisor_codes[-1]}")
            elif request['supervisor2'] and request['supervisor2'].strip() != "-":  # Only warn if supervisor2 was actually provided (not "-")
                print(f"⚠ Supervisor 2 '{request['supervisor2']}' not found")
            
            if not supervisors_found:
                print(f"⚠ No supervisors found")
                request['scheduled'] = False
                request['reason'] = "No supervisors found"
                scheduled_recommendations.append(request)
                continue
            
            # Find suitable judges (excluding supervisors)
            suitable_judges = []
            for judge in judges_info['expertise_matches']:
                judge_code = self._get_judge_code(judge['Sub_Keilmuan'])
                # Exclude all supervisors
                if judge_code not in supervisor_codes:
                    suitable_judges.append(judge)
            
            # Need exactly 2 judges (non-supervisors) - can have 0, 1, or 2 available
            # We'll proceed even with 0 or 1 judges and fill with "NONE" as needed
            print(f"✓ Found {len(suitable_judges)} suitable judges (need exactly 2 for recommendations)")
            
            # Try to find a time slot that works for supervisors + additional judges
            best_slot = None
            best_judges = None
            
            # Get all time slot columns
            time_cols = [col for col in self.availability_df.columns 
                        if col not in ['Nama_Dosen', 'Unknown_Col_5', 'Sub_Keilmuan']]
            
            for time_slot in time_cols:
                # Check if all supervisors are available and not scheduled
                supervisors_available = True
                for supervisor_code in supervisor_codes:
                    if not self.is_judge_available_at_time(supervisor_code, time_slot):
                        supervisors_available = False
                        break
                
                if not supervisors_available:
                    continue
                
                # Find available judges for this time slot
                available_judges_for_slot = []
                for judge in suitable_judges:
                    judge_code = self._get_judge_code(judge['Sub_Keilmuan'])
                    if self.is_judge_available_at_time(judge_code, time_slot):
                        available_judges_for_slot.append(judge)
                
                # We'll take whatever judges are available (0, 1, or 2+) and ensure exactly 2 in output
                best_slot = time_slot
                # Select exactly 2 judges (prioritize field matches)
                field1, field2 = request['fields'][0].upper(), request['fields'][1].upper()
                
                # Prioritize judges with exact field matches
                field1_matches = [j for j in available_judges_for_slot 
                                if field1 in self._parse_expertise(j['Sub_Keilmuan'])]
                field2_matches = [j for j in available_judges_for_slot 
                                if field2 in self._parse_expertise(j['Sub_Keilmuan'])]
                
                # Select exactly 2 judges
                selected_judges = []
                
                # First priority: field1 match
                if field1_matches:
                    selected_judges.append(field1_matches[0])
                
                # Second priority: field2 match (different from field1 match)
                if len(selected_judges) < 2 and field2_matches:
                    for judge in field2_matches:
                        if judge not in selected_judges:
                            selected_judges.append(judge)
                            break
                
                # Fill remaining slots from available judges
                if len(selected_judges) < 2:
                    for judge in available_judges_for_slot:
                        if judge not in selected_judges:
                            selected_judges.append(judge)
                            if len(selected_judges) == 2:
                                break
                
                best_judges = supervisors_found.copy()  # Include supervisors
                best_judges.extend(selected_judges)  # Add the selected judges
                
                break  # Found a suitable slot
            
            if best_slot and best_judges:
                # Reserve the time slot
                all_judge_codes = [self._get_judge_code(j['Sub_Keilmuan']) for j in best_judges]
                self.reserve_time_slot(best_slot, all_judge_codes)
                
                # Create successful recommendation with exactly 2 non-supervisor judges
                # Separate supervisors from other judges
                non_supervisor_judges = [j for j in best_judges if j not in supervisors_found]
                
                # Ensure exactly 2 judges in recommendation (fill with NONE if needed)
                judge_recommendations = []
                if len(non_supervisor_judges) >= 1:
                    judge_recommendations.append(self._get_judge_code(non_supervisor_judges[0]['Sub_Keilmuan']))
                else:
                    judge_recommendations.append("NONE")
                    
                if len(non_supervisor_judges) >= 2:
                    judge_recommendations.append(self._get_judge_code(non_supervisor_judges[1]['Sub_Keilmuan']))
                else:
                    judge_recommendations.append("NONE")
                
                request['scheduled'] = True
                request['scheduled_time'] = self.format_time_slot(best_slot)
                request['scheduled_judges'] = [
                    {
                        'code': self._get_judge_code(judge['Sub_Keilmuan']),
                        'role': 'Supervisor' if judge in supervisors_found else 'Examiner'
                    }
                    for judge in best_judges
                ]
                request['judge_recommendations'] = judge_recommendations  # Exactly 2 judges
                
                print(f"✓ Scheduled at {request['scheduled_time']}")
                print(f"✓ Panel: {', '.join([j['code'] for j in request['scheduled_judges']])}")
                print(f"✓ Judge Recommendations: {' | '.join(judge_recommendations)}")
                
            else:
                request['scheduled'] = False
                request['reason'] = "No available time slot found for required panel"
                request['judge_recommendations'] = ["NONE", "NONE"]  # Default to NONE when can't schedule
                print(f"✗ Could not find suitable time slot")
            
            scheduled_recommendations.append(request)
        
        return scheduled_recommendations
    
    def find_common_available_slots(self, judges: List[Dict]) -> List[str]:
        """
        Find time slots where all specified judges are available.
        
        Args:
            judges: List of judge records (dictionaries)
            
        Returns:
            List of time slot column names where all judges are available
        """
        if not judges:
            return []
        
        # Get time slot columns
        time_cols = [col for col in self.availability_df.columns 
                    if col not in ['Nama_Dosen', 'Unknown_Col_5', 'Sub_Keilmuan']]
        
        available_slots = []
        
        for time_col in time_cols:
            # Check if all judges are available at this time
            all_available = True
            for judge in judges:
                if isinstance(judge, dict):
                    if not judge.get(time_col, False):
                        all_available = False
                        break
                else:
                    # If it's still a Series, convert to dict
                    judge_dict = judge.to_dict() if hasattr(judge, 'to_dict') else judge
                    if not judge_dict.get(time_col, False):
                        all_available = False
                        break
            
            if all_available:
                available_slots.append(time_col)
        
        return available_slots
    
    def format_time_slot(self, time_slot: str) -> str:
        """Convert time slot column name to YYYYMMDD-HHMM format."""
        # Extract date and time from column name
        # Format: "Tuesday_10_June_2025_08:00"
        parts = time_slot.split('_')
        if len(parts) >= 5:
            day = parts[0]
            date = parts[1]
            month = parts[2]
            year = parts[3]
            time = parts[4]
            
            # Convert month name to number
            month_map = {
                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                'September': '09', 'October': '10', 'November': '11', 'December': '12'
            }
            
            month_num = month_map.get(month, '01')
            date_padded = date.zfill(2)
            time_formatted = time.replace(':', '')
            
            return f"{year}{month_num}{date_padded}-{time_formatted}"
        return time_slot
    
    def generate_recommendations(self, request_row: Dict) -> Dict:
        """
        Generate scheduling recommendations for a thesis defense request.
        
        Args:
            request_row: Dictionary containing request information
            
        Returns:
            Dictionary with recommendations
        """
        # Debug: print the keys in request_row
        print(f"Debug - Request row keys: {list(request_row.keys())}")
        
        # Handle potential key variations
        nama = request_row.get('Nama', request_row.get('nama', ''))
        nim = request_row.get('Nim', request_row.get('nim', ''))
        field1 = request_row.get('Field 1', request_row.get('field1', ''))
        field2 = request_row.get('Field 2', request_row.get('field2', ''))
        spv1 = request_row.get('SPV 1', request_row.get('spv1', ''))
        spv2 = request_row.get('SPV 2', request_row.get('spv2', ''))
        
        print(f"\nProcessing request for {nama} (NIM: {nim})")
        print(f"Fields: {field1}, {field2} | Supervisors: {spv1}, {spv2}")
        
        # Find available judges
        judges_info = self.find_available_judges(field1, field2, spv1, spv2)
        
        recommendations = {
            'student_name': nama,
            'nim': nim,
            'supervisor1': spv1,
            'supervisor2': spv2,
            'fields': [field1, field2],
            'supervisor_found': judges_info['supervisor1'] is not None or judges_info['supervisor2'] is not None,
            'recommended_times': [],
            'recommended_judges': [],
            'all_possible_judges': []
        }
        
        # Collect all supervisors found
        supervisors_found = []
        supervisor_codes = []
        
        if judges_info['supervisor1']:
            supervisors_found.append(judges_info['supervisor1'])
            supervisor1_code = self._get_judge_code(judges_info['supervisor1']['Sub_Keilmuan'])
            supervisor_codes.append(supervisor1_code)
            print(f"✓ Supervisor 1 found: {supervisor1_code}")
        else:
            print(f"⚠ Supervisor 1 '{spv1}' not found in availability data")
            
        if judges_info['supervisor2']:
            supervisors_found.append(judges_info['supervisor2'])
            supervisor2_code = self._get_judge_code(judges_info['supervisor2']['Sub_Keilmuan'])
            supervisor_codes.append(supervisor2_code)
            print(f"✓ Supervisor 2 found: {supervisor2_code}")
        elif spv2 and spv2.strip() != "-":  # Only warn if supervisor2 was actually provided (not "-")
            print(f"⚠ Supervisor 2 '{spv2}' not found in availability data")
        
        # If at least one supervisor is found, prioritize slots where supervisors are available
        if supervisors_found:
            
            # Find expertise-matching judges (excluding the supervisors)
            expertise_judges = []
            for judge in judges_info['expertise_matches']:
                judge_code = self._get_judge_code(judge['Sub_Keilmuan'])
                judge_expertise = self._parse_expertise(judge['Sub_Keilmuan'])
                
                # Skip if this is any of the supervisors
                if judge_code in supervisor_codes:
                    continue
                    
                if any(exp in [field1.upper(), field2.upper()] for exp in judge_expertise):
                    expertise_judges.append(judge)
            
            # Combine supervisors with expertise-matching judges
            required_judges = supervisors_found.copy()
            
            # Add best matching expertise judges (aim for 3-5 total judges)
            field1_judges = [j for j in expertise_judges if field1.upper() in self._parse_expertise(j['Sub_Keilmuan'])]
            field2_judges = [j for j in expertise_judges if field2.upper() in self._parse_expertise(j['Sub_Keilmuan'])]
            
            # Prioritize judges with exact field matches
            for judge in field1_judges[:2]:  # Max 2 from field1
                if judge not in required_judges:
                    required_judges.append(judge)
            
            for judge in field2_judges[:2]:  # Max 2 from field2
                if judge not in required_judges and len(required_judges) < 5:
                    required_judges.append(judge)
            
            # Find common available time slots
            available_slots = self.find_common_available_slots(required_judges)
            
            recommendations['recommended_times'] = [
                self.format_time_slot(slot) for slot in available_slots[:5]  # Top 5 recommendations
            ]
            
            recommendations['recommended_judges'] = [
                {
                    'code': self._get_judge_code(judge['Sub_Keilmuan']),
                    'role': 'Supervisor' if judge in supervisors_found else 'Examiner'
                }
                for judge in required_judges
            ]
            
        else:
            print(f"⚠ No supervisors found")
            
            # Still try to find expertise-matching judges
            expertise_judges = judges_info['expertise_matches'][:4]  # Limit to 4 judges
            
            if expertise_judges:
                available_slots = self.find_common_available_slots(expertise_judges)
                recommendations['recommended_times'] = [
                    self.format_time_slot(slot) for slot in available_slots[:5]
                ]
                
                recommendations['recommended_judges'] = [
                    {
                        'code': self._get_judge_code(judge['Sub_Keilmuan']),
                        'role': 'Examiner'
                    }
                    for judge in expertise_judges
                ]
        
        # Store all possible judges for reference
        recommendations['all_possible_judges'] = [
            {
                'name': judge['Nama_Dosen'],
                'expertise': self._parse_expertise(judge['Sub_Keilmuan'])
            }
            for judge in judges_info['expertise_matches']
        ]
        
        return recommendations
    
    def process_all_requests(self) -> List[Dict]:
        """Process all thesis defense requests and generate a conflict-free schedule."""
        print("Converting requests to standardized format...")
        
        # Convert all requests to a standardized format
        requests = []
        for _, request in self.request_df.iterrows():
            request_dict = {
                'student_name': request.get('Nama', ''),
                'nim': request.get('Nim', ''),
                'fields': [request.get('Field 1', ''), request.get('Field 2', '')],
                'supervisor1': request.get('SPV 1', ''),
                'supervisor2': request.get('SPV 2', ''),
                'original_row': request.to_dict()
            }
            requests.append(request_dict)
        
        print(f"Processing {len(requests)} requests for optimal scheduling...")
        
        # Use the find_optimal_schedule method to handle conflicts
        scheduled_requests = self.find_optimal_schedule(requests)
        
        # Convert back to the expected format for saving
        final_recommendations = []
        for request in scheduled_requests:
            if request.get('scheduled', False):
                recommendation = {
                    'student_name': request['student_name'],
                    'nim': request['nim'],
                    'supervisor1': request['supervisor1'],
                    'supervisor2': request['supervisor2'],
                    'fields': request['fields'],
                    'recommended_times': [request['scheduled_time']],  # Single time slot
                    'recommended_judges': request.get('judge_recommendations', ['NONE', 'NONE']),  # Exactly 2 judges
                    'scheduled': True,
                    'reason': 'Successfully scheduled'
                }
            else:
                recommendation = {
                    'student_name': request['student_name'],
                    'nim': request['nim'],
                    'supervisor1': request['supervisor1'],
                    'supervisor2': request['supervisor2'],
                    'fields': request['fields'],
                    'recommended_times': [],
                    'recommended_judges': request.get('judge_recommendations', ['NONE', 'NONE']),  # Exactly 2 judges
                    'scheduled': False,
                    'reason': request.get('reason', 'Unknown error')
                }
            
            final_recommendations.append(recommendation)
        
        return final_recommendations
    
    def save_updated_csv(self, recommendations: List[Dict], output_file: str):
        """Save the updated CSV with scheduling recommendations."""
        print(f"\nSaving results to {output_file}...")
        
        # Create updated rows
        updated_rows = []
        
        for i, recommendation in enumerate(recommendations):
            # Get original row data
            original_row = self.request_df.iloc[i].to_dict()
            
            # Update with recommendations
            if recommendation['scheduled']:
                # Single time slot (not multiple)
                original_row['Date Time (YYYYMMDD-HHMM)'] = recommendation['recommended_times'][0]
                # Exactly 2 judges (with NONE as placeholder if needed)
                judges_list = recommendation['recommended_judges']
                if len(judges_list) >= 2:
                    original_row['List of recommendation'] = f"{judges_list[0]} | {judges_list[1]}"
                elif len(judges_list) == 1:
                    original_row['List of recommendation'] = f"{judges_list[0]} | NONE"
                else:
                    original_row['List of recommendation'] = "NONE | NONE"
            else:
                original_row['Date Time (YYYYMMDD-HHMM)'] = f"NOT_SCHEDULED: {recommendation['reason']}"
                original_row['List of recommendation'] = "NONE | NONE"
            
            updated_rows.append(original_row)
        
        # Create DataFrame and save
        updated_df = pd.DataFrame(updated_rows)
        updated_df.to_csv(output_file, index=False)
        
        print(f"✅ Updated CSV saved to: {output_file}")
        
        # Print summary
        scheduled_count = sum(1 for r in recommendations if r['scheduled'])
        total_count = len(recommendations)
        print(f"\n📊 SCHEDULING SUMMARY:")
        print(f"   Successfully scheduled: {scheduled_count}/{total_count}")
        print(f"   Failed to schedule: {total_count - scheduled_count}/{total_count}")
        
        if scheduled_count > 0:
            print(f"\n🗓️  SCHEDULED DEFENSES:")
            for recommendation in recommendations:
                if recommendation['scheduled']:
                    judges_display = ' | '.join(recommendation['recommended_judges'])
                    print(f"   • {recommendation['student_name']} - {recommendation['recommended_times'][0]} - Judges: {judges_display}")
        
        if total_count - scheduled_count > 0:
            print(f"\n❌ FAILED TO SCHEDULE:")
            for recommendation in recommendations:
                if not recommendation['scheduled']:
                    judges_display = ' | '.join(recommendation['recommended_judges'])
                    print(f"   • {recommendation['student_name']} - {recommendation['reason']} - Judges: {judges_display}")
        
        # Show scheduling conflicts summary
        if self.scheduled_slots:
            print(f"\n⏰ TIME SLOT UTILIZATION:")
            for time_slot, judges in self.scheduled_slots.items():
                formatted_time = self.format_time_slot(time_slot)
                print(f"   • {formatted_time}: {' | '.join(judges)}")
        
        return updated_df

def main():
    """Main function to run the thesis scheduler."""
    # File paths
    availability_file = "/Users/martinmanullang/Developer/ta-scheduler/avail_20250610_clean.csv"
    request_file = "/Users/martinmanullang/Developer/ta-scheduler/schedule_request_multiple.csv"
    output_file = "/Users/martinmanullang/Developer/ta-scheduler/schedule_request_multiple_with_recommendations.csv"
    
    # Initialize scheduler
    scheduler = ThesisScheduler(availability_file, request_file)
    
    # Process all requests
    print("=" * 60)
    print("THESIS DEFENSE SCHEDULER")
    print("=" * 60)
    
    recommendations = scheduler.process_all_requests()
    
    # Save the updated CSV with fixed schedule
    scheduler.save_updated_csv(recommendations, output_file)
    
    print(f"\n✓ Processing complete!")
    print(f"✓ Fixed schedule saved to: {output_file}")

if __name__ == "__main__":
    main()
