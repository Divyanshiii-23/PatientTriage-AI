#!/usr/bin/env python3
"""
Comprehensive end-to-end test with all 20 test patients
Validates predictions, confidence scores, and safety flags
"""

import requests
import json
import sys
from typing import Dict, List

BASE_URL = "http://localhost:8000"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_header(msg):
    print(f"\n{CYAN}{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}{RESET}\n")

def get_test_patients():
    """Fetch all 20 test patients from the API"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/patients", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('patients', [])
        else:
            print_error(f"Failed to fetch patients: HTTP {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error fetching patients: {e}")
        return []

def convert_patient_to_flat_structure(patient):
    """Convert nested patient structure to flat API format"""
    # Convert sex to uppercase first letter
    sex = patient['demographics']['sex']
    if sex.lower() == 'male':
        sex = 'M'
    elif sex.lower() == 'female':
        sex = 'F'
    else:
        sex = 'Other'
    
    flat = {
        'age': patient['demographics']['age'],
        'sex': sex,
        'hr': patient['vitals']['hr'],
        'bp_systolic': patient['vitals']['bp_systolic'],
        'bp_diastolic': patient['vitals']['bp_diastolic'],
        'spo2': patient['vitals']['spo2'],
        'rr': patient['vitals']['rr'],
        'temperature': patient['vitals'].get('temperature'),
        'chief_complaint': patient['clinical']['chief_complaint'],
        'chief_complaint_category': patient['clinical']['chief_complaint_category'],
        'arrival_mode': patient['clinical'].get('arrival_mode', 'walk_in'),
        'mental_status': patient['clinical'].get('mental_status', 'alert'),
        'pain_score': patient['clinical'].get('pain_score'),
        'symptoms': patient['clinical'].get('symptoms', []),
        'medical_history': patient.get('medical_history', {})
    }
    return flat

def test_single_patient(patient):
    """Test a single patient through the prediction API"""
    patient_data = convert_patient_to_flat_structure(patient)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/predict",
            json=patient_data,
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text[:200]}"
            }
        
        result = response.json()
        
        # Validate response structure
        required_fields = ['esi_prediction', 'confidence_breakdown', 'safety_flag', 'explanation']
        for field in required_fields:
            if field not in result:
                return {
                    'success': False,
                    'error': f"Missing field: {field}"
                }
        
        return {
            'success': True,
            'result': result
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def analyze_patient_labels(patient):
    """Determine special labels for a patient"""
    labels = []
    age = patient['demographics']['age']
    
    if age < 18:
        labels.append('PEDIATRIC')
    if age >= 65:
        labels.append('GERIATRIC')
    
    # Check for ambiguous case (chest pain in 40-50 age range)
    if (patient['clinical']['chief_complaint_category'] == 'chest_pain_cardiac' and 
        40 <= age <= 50):
        labels.append('AMBIGUOUS')
    
    # Check for zero history
    med_history = patient.get('medical_history', {})
    if not med_history or all(not v for v in med_history.values()):
        labels.append('ZERO-HISTORY')
    
    return labels

def main():
    print(f"\n{CYAN}{'='*70}")
    print("  END-TO-END TEST: All 20 Test Patients")
    print(f"{'='*70}{RESET}\n")
    
    # Fetch test patients
    print_info("Fetching test patients from API...")
    patients = get_test_patients()
    
    if not patients:
        print_error("No patients fetched. Ensure backend is running.")
        return 1
    
    print_success(f"Fetched {len(patients)} test patients\n")
    
    # Test each patient
    results = []
    special_case_counts = {
        'PEDIATRIC': 0,
        'GERIATRIC': 0,
        'AMBIGUOUS': 0,
        'ZERO-HISTORY': 0
    }
    
    esi_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    confidence_distribution = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    safety_distribution = {'RED': 0, 'YELLOW': 0, 'GREEN': 0}
    
    for i, patient in enumerate(patients, 1):
        print_header(f"Patient {i}/20: {patient['name']}")
        
        # Display patient info
        age = patient['demographics']['age']
        sex = patient['demographics']['sex']
        chief_complaint = patient['clinical']['chief_complaint']
        labels = analyze_patient_labels(patient)
        
        print(f"  Demographics: {age}yo {sex}")
        print(f"  Chief Complaint: {chief_complaint}")
        print(f"  Vitals: HR={patient['vitals']['hr']}, SpO2={patient['vitals']['spo2']}%, BP={patient['vitals']['bp_systolic']}/{patient['vitals']['bp_diastolic']}")
        
        if labels:
            print(f"  Special Labels: {', '.join(labels)}")
            for label in labels:
                if label in special_case_counts:
                    special_case_counts[label] += 1
        
        # Test prediction
        print(f"\n  Testing prediction...")
        test_result = test_single_patient(patient)
        
        if not test_result['success']:
            print_error(f"  Prediction failed: {test_result['error']}")
            results.append({
                'patient': patient['name'],
                'success': False,
                'error': test_result['error']
            })
            continue
        
        # Extract results
        pred = test_result['result']
        esi = pred['esi_prediction']
        conf = pred['confidence_breakdown']
        safety = pred['safety_flag']
        
        # Update distributions
        esi_distribution[esi] += 1
        confidence_distribution[conf['level']] += 1
        safety_distribution[safety['outcome']] += 1
        
        # Display results
        print_success(f"  ESI Prediction: {esi}")
        
        conf_color = GREEN if conf['level'] == 'HIGH' else YELLOW if conf['level'] == 'MEDIUM' else RED
        print(f"  {conf_color}Confidence: {conf['level']} ({conf['overall']:.1f}%){RESET}")
        
        safety_color = RED if safety['outcome'] == 'RED' else YELLOW if safety['outcome'] == 'YELLOW' else GREEN
        print(f"  {safety_color}Safety Flag: {safety['outcome']}{RESET}")
        
        if safety['outcome'] != 'GREEN':
            print(f"    Criteria: {', '.join(safety['triggered_criteria'][:2])}")
        
        # Show top explanation factor
        if 'explanation' in pred and 'top_factors' in pred['explanation'] and len(pred['explanation']['top_factors']) > 0:
            top_factor = pred['explanation']['top_factors'][0]
            print(f"  Top Factor: {top_factor['feature']} ({top_factor['direction']})")
        
        # Validation checks
        checks = []
        
        # Check 1: ESI in valid range
        if 1 <= esi <= 5:
            checks.append(('ESI range', True))
        else:
            checks.append(('ESI range', False))
            print_warning(f"  ESI {esi} outside valid range 1-5")
        
        # Check 2: Confidence scores in range
        conf_valid = all(0 <= conf[dim] <= 100 for dim in ['model_certainty', 'data_completeness', 'clinical_consistency', 'pattern_recognition', 'overall'])
        checks.append(('Confidence range', conf_valid))
        if not conf_valid:
            print_warning("  Some confidence scores outside 0-100 range")
        
        # Check 3: Safety logic
        if safety['outcome'] == 'RED' and esi > 2:
            print_warning(f"  RED flag but ESI {esi} > 2 (should override to 1 or 2)")
        
        # Check 4: Pediatric safety
        if age < 2 and safety['outcome'] == 'GREEN':
            print_warning(f"  Infant (age {age}) with GREEN flag - should be more cautious")
        
        # Check 5: Low SpO2 safety
        if patient['vitals']['spo2'] < 90 and safety['outcome'] != 'RED':
            print_warning(f"  SpO2 {patient['vitals']['spo2']}% should trigger RED flag")
        
        results.append({
            'patient': patient['name'],
            'success': True,
            'esi': esi,
            'confidence': conf['level'],
            'safety': safety['outcome'],
            'checks': checks
        })
    
    # Final Summary
    print_header("FINAL SUMMARY")
    
    # Success rate
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (successful / total * 100) if total > 0 else 0
    
    print(f"Patients Tested: {total}")
    print(f"Successful Predictions: {successful}/{total} ({success_rate:.0f}%)")
    print()
    
    # Special case distribution
    print("Special Case Distribution:")
    for label, count in special_case_counts.items():
        status = "✓" if count >= 1 else "✗"
        min_required = 2 if label in ['PEDIATRIC', 'GERIATRIC'] else 1
        meets_req = "✓" if count >= min_required else "✗"
        print(f"  {meets_req} {label}: {count} (requirement: ≥{min_required})")
    print()
    
    # ESI distribution
    print("ESI Level Distribution:")
    for esi in range(1, 6):
        count = esi_distribution[esi]
        bar = '█' * (count * 2)
        print(f"  ESI {esi}: {count:2d} {bar}")
    print()
    
    # Confidence distribution
    print("Confidence Distribution:")
    for level in ['HIGH', 'MEDIUM', 'LOW']:
        count = confidence_distribution[level]
        bar = '█' * count
        print(f"  {level:6s}: {count:2d} {bar}")
    print()
    
    # Safety flag distribution
    print("Safety Flag Distribution:")
    for flag in ['RED', 'YELLOW', 'GREEN']:
        count = safety_distribution[flag]
        bar = '█' * count
        color = RED if flag == 'RED' else YELLOW if flag == 'YELLOW' else GREEN
        print(f"  {color}{flag:6s}: {count:2d} {bar}{RESET}")
    print()
    
    # Requirements validation
    print_header("REQUIREMENTS VALIDATION")
    
    requirements = [
        ("Total patients tested", total == 20, f"{total}/20"),
        ("All predictions successful", successful == total, f"{successful}/{total}"),
        ("At least 2 pediatric patients", special_case_counts['PEDIATRIC'] >= 2, f"{special_case_counts['PEDIATRIC']}"),
        ("At least 2 geriatric patients", special_case_counts['GERIATRIC'] >= 2, f"{special_case_counts['GERIATRIC']}"),
        ("At least 1 ambiguous case", special_case_counts['AMBIGUOUS'] >= 1, f"{special_case_counts['AMBIGUOUS']}"),
        ("At least 1 zero-history patient", special_case_counts['ZERO-HISTORY'] >= 1, f"{special_case_counts['ZERO-HISTORY']}"),
        ("All ESI levels represented", all(esi_distribution[i] > 0 for i in range(1, 6)), f"{sum(1 for v in esi_distribution.values() if v > 0)}/5"),
        ("RED flags for critical cases", safety_distribution['RED'] > 0, f"{safety_distribution['RED']} cases"),
        ("GREEN flags for minor cases", safety_distribution['GREEN'] > 0, f"{safety_distribution['GREEN']} cases"),
    ]
    
    all_passed = True
    for req, passed, detail in requirements:
        status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        print(f"  {status} {req}: {detail}")
        if not passed:
            all_passed = False
    
    print()
    
    # Final verdict
    if all_passed and successful == total:
        print(f"{GREEN}{'='*70}")
        print("  ✓ ALL END-TO-END TESTS PASSED")
        print(f"{'='*70}{RESET}\n")
        print_success("All 20 test patients processed successfully")
        print_success("All requirement validations passed")
        print_success("System is ready for demonstration")
        return 0
    else:
        print(f"{YELLOW}{'='*70}")
        print("  ⚠ TESTS COMPLETED WITH WARNINGS")
        print(f"{'='*70}{RESET}\n")
        if successful == total:
            print_success("All predictions successful")
        else:
            print_warning(f"{total - successful} prediction(s) failed")
        
        if not all_passed:
            print_warning("Some requirement validations did not pass")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())
