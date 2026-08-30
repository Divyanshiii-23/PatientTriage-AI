#!/usr/bin/env python3
"""
Fix validation issues in test patient data
"""

import json
from pathlib import Path

# Load test patients
data_file = Path('data/test_patients.json')
patients = json.load(data_file.open())

print("Fixing test patient data...\n")

# Fix 1: Clamp RR values to max 60
print("1. Clamping RR values > 60:")
for patient in patients:
    if patient['vitals']['rr'] > 60:
        old_rr = patient['vitals']['rr']
        patient['vitals']['rr'] = 60
        print(f"   ✓ {patient['name']}: RR {old_rr} → 60")

# Fix 2: Convert private_vehicle to walk_in (closest equivalent)
print("\n2. Converting invalid arrival_mode values:")
for patient in patients:
    mode = patient['clinical'].get('arrival_mode', 'walk_in')
    if mode == 'private_vehicle':
        patient['clinical']['arrival_mode'] = 'walk_in'
        print(f"   ✓ {patient['name']}: private_vehicle → walk_in")

# Save fixed data
json.dump(patients, data_file.open('w'), indent=2)

print("\n✅ Test patient data fixed and saved!")
print(f"   File: {data_file}")
