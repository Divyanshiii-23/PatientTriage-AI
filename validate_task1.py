#!/usr/bin/env python3
"""Validate Task 1 completion."""
import json
import sys

def main():
    # Load data
    with open('data/test_patients.json') as f:
        test = json.load(f)
    with open('data/training_patients.json') as f:
        training = json.load(f)
    
    print("TASK 1 VALIDATION")
    print("=" * 60)
    
    # Check counts
    assert len(training) == 500, f"Training set should have 500 patients, got {len(training)}"
    assert len(test) == 20, f"Test set should have 20 patients, got {len(test)}"
    print(f"✓ Training patients: {len(training)}")
    print(f"✓ Test patients: {len(test)}")
    
    # Req 1.2: Ambiguous case
    ambiguous = [p for p in test if 'improved with rest' in p['clinical']['chief_complaint'].lower()]
    assert len(ambiguous) >= 1, "Need at least 1 ambiguous case"
    print(f"✓ Ambiguous cases: {len(ambiguous)}")
    
    # Req 1.3: Pediatric
    pediatric = [p for p in test if p['demographics']['age'] < 18]
    assert len(pediatric) >= 2, f"Need at least 2 pediatric, got {len(pediatric)}"
    print(f"✓ Pediatric patients: {len(pediatric)}")
    
    # Req 1.4: Geriatric
    geriatric = [p for p in test if p['demographics']['age'] >= 65]
    assert len(geriatric) >= 2, f"Need at least 2 geriatric, got {len(geriatric)}"
    print(f"✓ Geriatric patients: {len(geriatric)}")
    
    # Req 1.5: Zero history
    zero_hist = [p for p in test if not p['medical_history']]
    assert len(zero_hist) >= 1, "Need at least 1 zero-history patient"
    print(f"✓ Zero-history patients: {len(zero_hist)}")
    
    # Req 1.6: ESI distribution
    test_esi = {}
    for p in test:
        esi = p['ground_truth_esi']
        test_esi[esi] = test_esi.get(esi, 0) + 1
    
    for esi in [1, 2, 3, 4, 5]:
        count = test_esi.get(esi, 0)
        assert count >= 2, f"ESI {esi} needs at least 2 patients, got {count}"
    print(f"✓ ESI distribution: {dict(sorted(test_esi.items()))}")
    
    # Req 1.8: Chief complaints
    complaints = set()
    for p in training + test:
        complaints.add(p['clinical']['chief_complaint_category'])
    assert len(complaints) >= 50, f"Need 50+ complaint categories, got {len(complaints)}"
    print(f"✓ Chief complaint categories: {len(complaints)}")
    
    # Req 1.10: Unique IDs
    all_ids = [p['patient_id'] for p in training + test]
    assert len(all_ids) == len(set(all_ids)), "Patient IDs must be unique"
    print(f"✓ All patient IDs unique")
    
    print("\n✅ ALL REQUIREMENTS MET!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
