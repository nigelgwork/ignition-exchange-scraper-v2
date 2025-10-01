"""
Generate test Excel report using all_exchange_resources.json
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, '/app')

from app.excel_generator import create_excel_report
from app.comparison import compare_resources

# Paths
DATA_DIR = Path('/data')
OUTPUT_DIR = DATA_DIR / 'output'
JSON_FILE = Path('/app/all_exchange_resources.json')

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load the JSON data
print(f"Loading {JSON_FILE}...")
with open(JSON_FILE, 'r') as f:
    all_resources = json.load(f)

print(f"Loaded {len(all_resources)} resources")

# For demonstration: modify a few resources to show as updated
import copy
current_results = copy.deepcopy(all_resources)
past_results = all_resources

# Modify first 5 resources to simulate updates
for i in range(min(5, len(current_results))):
    current_results[i]['version'] = '2.0.0'  # Change version
    current_results[i]['updated_date'] = '2025-10-01'  # Change date

# Use comparison logic to find updated resources
print("Comparing current vs past results...")
updated_results = compare_resources(current_results, past_results)

# Generate output filename
output_filename = "Ignition Exchange Resource Results_251001.xlsx"
output_path = OUTPUT_DIR / output_filename

print(f"Generating Excel report: {output_path}...")
create_excel_report(updated_results, current_results, past_results, output_path)

print(f"✓ Excel report generated successfully: {output_path}")
print(f"  - Updated Resources sheet: {len(updated_results)} rows")
print(f"  - Current Resources sheet: {len(current_results)} rows")
print(f"  - Past Resources sheet: {len(past_results)} rows")
