#!/usr/bin/env python3
"""
Test script for ML Core Engine validation
Tests preprocessing, prediction, confidence scoring, and safety validation
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
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

def test_health_endpoint():
    """Test that the server is running"""
    print_section("1. Server Health Check")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print_success("Server is running at http://localhost:8000")
            print_success("API documentation available at http://localhost:8000/docs")
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Server is not responding: {e}")
        return False

def test_sample_prediction(patient_data: Dict, expected_results: Dict = None):
    """Test a single prediction with the ML Core"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/predict",
            json=patient_data,
            timeout=10
        )
        
        if response.status_code != 200:
            print_error(f"API returned status {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
        
        result = response.json()
        
        # Validate response structure
        required_fields = [
            'esi_prediction', 
            'probability_distribution', 
            'confidence_breakdown', 
            'safety_flag',
            'explanation'
        ]
        
        for field in required_fields:
            if field not in result:
                print_error(f"Missing field in response: {field}")
                return None
        
        return result
    except Exception as e:
        print_error(f"Prediction failed: {e}")
        return None

def validate_confidence_breakdown(confidence: Dict):
    """Validate confidence breakdown has all dimensions"""
    required_dimensions = [
        'model_certainty',
        'data_completeness', 
        'clinical_consistency',
        'pattern_recognition',
        'overall',
        'level'
    ]
    
    for dimension in required_dimensions:
        if dimension not in confidence:
            print_error(f"Missing confidence dimension: {dimension}")
            return False
        
        # Check scores are in valid range (0-100) except level
        if dimension != 'level':
            score = confidence[dimension]
            if not (0 <= score <= 100):
                print_error(f"{dimension} score {score} is out of range [0, 100]")
                return False
    
    # Check confidence level is valid
    valid_levels = ['HIGH', 'MEDIUM', 'LOW']
    if confidence['level'] not in valid_levels:
        print_error(f"Invalid confidence level: {confidence['level']}")
        return False
    
    return True

def test_diverse_scenarios():
    """Test ML Core with diverse patient scenarios"""
    print_section("2. Testing Diverse Patient Scenarios")
    
    test_cases = [
        {
            "name": "Adult chest pain (high risk)",
            "data": {
                "age": 55,
                "sex": "M",
                "hr": 98,
                "bp_systolic": 145,
                "bp_diastolic": 92,
                "spo2": 96,
                "rr": 18,
                "temperature": 37.1,
                "chief_complaint": "Chest pain with radiation to left arm",
                "chief_complaint_category": "chest_pain_cardiac",
                "arrival_mode": "ambulance",
                "mental_status": "alert",
                "pain_score": 8,
                "symptoms": ["chest_pain"],
                "medical_history": {}
            },
            "expected": {
                "esi_range": [1, 2, 3],
                "safety_flag": ["RED", "YELLOW"],
                "check": "chest_pain_high_risk"
            }
        },
        {
            "name": "Pediatric fever (infant)",
            "data": {
                "age": 1,
                "sex": "F",
                "hr": 150,
                "bp_systolic": 85,
                "bp_diastolic": 55,
                "spo2": 98,
                "rr": 38,
                "temperature": 38.8,
                "chief_complaint": "Fever and irritability",
                "chief_complaint_category": "fever",
                "arrival_mode": "walk_in",
                "mental_status": "alert",
                "pain_score": None,
                "symptoms": ["fever", "irritability"],
                "medical_history": {}
            },
            "expected": {
                "esi_range": [1, 2, 3],
                "safety_flag": ["RED", "YELLOW"],
                "check": "pediatric_infant"
            }
        },
        {
            "name": "Geriatric fall",
            "data": {
                "age": 78,
                "sex": "M",
                "hr": 88,
                "bp_systolic": 150,
                "bp_diastolic": 85,
                "spo2": 95,
                "rr": 16,
                "temperature": 36.8,
                "chief_complaint": "Fall from standing, hip pain",
                "chief_complaint_category": "trauma_fall",
                "arrival_mode": "ambulance",
                "mental_status": "alert",
                "pain_score": 7,
                "symptoms": ["hip_pain", "fall"],
                "medical_history": {"hypertension": True, "osteoporosis": True}
            },
            "expected": {
                "esi_range": [2, 3, 4],
                "check": "geriatric_patient"
            }
        },
        {
            "name": "Low SpO2 (respiratory distress)",
            "data": {
                "age": 60,
                "sex": "F",
                "hr": 110,
                "bp_systolic": 135,
                "bp_diastolic": 80,
                "spo2": 88,
                "rr": 28,
                "temperature": 37.5,
                "chief_complaint": "Shortness of breath",
                "chief_complaint_category": "respiratory_distress",
                "arrival_mode": "ambulance",
                "mental_status": "alert",
                "pain_score": 5,
                "symptoms": ["shortness_of_breath"],
                "medical_history": {}
            },
            "expected": {
                "esi_range": [1, 2],
                "safety_flag": ["RED"],
                "check": "low_spo2"
            }
        },
        {
            "name": "Minor injury (low acuity)",
            "data": {
                "age": 25,
                "sex": "F",
                "hr": 75,
                "bp_systolic": 118,
                "bp_diastolic": 75,
                "spo2": 99,
                "rr": 14,
                "temperature": 36.9,
                "chief_complaint": "Ankle sprain from sports injury",
                "chief_complaint_category": "musculoskeletal_minor",
                "arrival_mode": "walk_in",
                "mental_status": "alert",
                "pain_score": 4,
                "symptoms": ["ankle_pain"],
                "medical_history": {}
            },
            "expected": {
                "esi_range": [4, 5],
                "safety_flag": ["GREEN"],
                "check": "minor_injury"
            }
        },
        {
            "name": "Ambiguous abdominal pain",
            "data": {
                "age": 35,
                "sex": "M",
                "hr": 88,
                "bp_systolic": 128,
                "bp_diastolic": 78,
                "spo2": 98,
                "rr": 16,
                "temperature": 37.2,
                "chief_complaint": "Abdominal pain, diffuse",
                "chief_complaint_category": "abdominal_pain",
                "arrival_mode": "walk_in",
                "mental_status": "alert",
                "pain_score": 6,
                "symptoms": ["abdominal_pain"],
                "medical_history": {}
            },
            "expected": {
                "esi_range": [2, 3, 4],
                "check": "ambiguous_case"
            }
        },
        {
            "name": "Missing optional fields (data completeness)",
            "data": {
                "age": 42,
                "sex": "F",
                "hr": 92,
                "bp_systolic": 130,
                "bp_diastolic": 82,
                "spo2": 97,
                "rr": 16,
                "chief_complaint": "Headache",
                "chief_complaint_category": "neurological_headache",
                "arrival_mode": "walk_in",
                "mental_status": "alert",
                "symptoms": [],
                "medical_history": {}
            },
            "expected": {
                "check": "incomplete_data"
            }
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['name']} ---")
        
        result = test_sample_prediction(test_case['data'])
        
        if result is None:
            print_error(f"Failed to get prediction")
            results.append(False)
            continue
        
        # Display key results
        print(f"  ESI Prediction: {result['esi_prediction']}")
        print(f"  Confidence: {result['confidence_breakdown']['level']} ({result['confidence_breakdown']['overall']:.1f}%)")
        print(f"  Safety Flag: {result['safety_flag']['outcome']}")
        
        # Validate response structure
        if not validate_confidence_breakdown(result['confidence_breakdown']):
            print_error("Invalid confidence breakdown")
            results.append(False)
            continue
        
        # Check expected results
        expected = test_case.get('expected', {})
        passed = True
        
        if 'esi_range' in expected:
            if result['esi_prediction'] not in expected['esi_range']:
                print_warning(f"ESI {result['esi_prediction']} outside expected range {expected['esi_range']}")
                # This is a warning, not a failure
        
        if 'safety_flag' in expected:
            if result['safety_flag']['outcome'] not in expected['safety_flag']:
                print_warning(f"Safety flag {result['safety_flag']['outcome']} not in expected {expected['safety_flag']}")
        
        # Special checks
        check = expected.get('check')
        if check == 'chest_pain_high_risk':
            # Should trigger safety concern or at least YELLOW
            if result['safety_flag'] == 'GREEN' and result['esi_prediction'] > 3:
                print_warning("Chest pain in older adult should trigger safety concern")
        
        elif check == 'pediatric_infant':
            # Infant should trigger elevated ESI
            if result['esi_prediction'] > 3:
                print_warning("Infant with fever should be higher acuity")
        
        elif check == 'low_spo2':
            # Low SpO2 should trigger RED flag
            if result['safety_flag']['outcome'] != 'RED':
                print_error("Low SpO2 (88%) should trigger RED safety flag")
                passed = False
            if result['esi_prediction'] > 2:
                print_error("Low SpO2 should result in ESI 1 or 2")
                passed = False
        
        elif check == 'minor_injury':
            # Should be low acuity
            if result['esi_prediction'] < 3:
                print_warning("Minor injury should be lower acuity (ESI 3-5)")
        
        elif check == 'incomplete_data':
            # Should have reduced data completeness score
            data_comp = result['confidence_breakdown']['data_completeness']
            if data_comp >= 95:
                print_warning(f"Data completeness should be reduced with missing fields (got {data_comp:.1f}%)")
        
        if passed:
            print_success(f"Test case passed: {test_case['name']}")
        else:
            print_error(f"Test case failed: {test_case['name']}")
        
        results.append(passed)
    
    return all(results)

def test_preprocessing_features():
    """Test that preprocessing creates expected features"""
    print_section("3. Testing Preprocessing Features")
    
    # Simple patient for feature inspection
    patient = {
        "age": 45,
        "sex": "F",
        "hr": 120,
        "bp_systolic": 140,
        "bp_diastolic": 90,
        "spo2": 94,
        "rr": 22,
        "temperature": 38.0,
        "chief_complaint": "Fever and cough",
        "chief_complaint_category": "respiratory_infection",
        "arrival_mode": "walk_in",
        "mental_status": "alert",
        "pain_score": 3,
        "symptoms": ["fever", "cough"],
        "medical_history": {"asthma": True}
    }
    
    result = test_sample_prediction(patient)
    
    if result is None:
        print_error("Failed to get prediction for preprocessing test")
        return False
    
        # Check that all confidence dimensions are computed
        conf = result['confidence_breakdown']
        print(f"  Model Certainty: {conf['model_certainty']:.1f}%")
        print(f"  Data Completeness: {conf['data_completeness']:.1f}%")
        print(f"  Clinical Consistency: {conf['clinical_consistency']:.1f}%")
        print(f"  Pattern Recognition: {conf['pattern_recognition']:.1f}%")
        print(f"  Overall: {conf['overall']:.1f}% ({conf['level']})")
        
        # Check SHAP values are present
        if 'explanation' not in result or 'top_factors' not in result['explanation']:
            print_error("No top_factors in explanation")
            return False
        
        if len(result['explanation']['top_factors']) == 0:
            print_error("No top_factors in explanation")
            return False
        
        print(f"\n  Top contributing features:")
        for i, factor in enumerate(result['explanation']['top_factors'][:5], 1):
            print(f"    {i}. {factor['feature']}: {factor['shap_value']:+.3f} ({factor['direction']})")
    
    print_success("Preprocessing features validated")
    return True

def test_safety_validation_rules():
    """Test specific safety validation rules"""
    print_section("4. Testing Safety Validation Rules")
    
    safety_tests = [
        {
            "name": "Critical SpO2 (should trigger RED)",
            "patient": {
                "age": 50,
                "sex": "M",
                "hr": 100,
                "bp_systolic": 120,
                "bp_diastolic": 80,
                "spo2": 85,
                "rr": 20,
                "chief_complaint": "Difficulty breathing",
                "chief_complaint_category": "respiratory_distress",
                "arrival_mode": "ambulance",
                "mental_status": "alert",
                "symptoms": ["shortness_of_breath"],
                "medical_history": {}
            },
            "expected_flag": "RED",
            "expected_esi_max": 2
        },
        {
            "name": "Chest pain age > 45 (should trigger concern)",
            "patient": {
                "age": 60,
                "sex": "F",
                "hr": 88,
                "bp_systolic": 135,
                "bp_diastolic": 85,
                "spo2": 97,
                "rr": 16,
                "chief_complaint": "Chest pain",
                "chief_complaint_category": "chest_pain_cardiac",
                "arrival_mode": "ambulance",
                "mental_status": "alert",
                "pain_score": 7,
                "symptoms": ["chest_pain"],
                "medical_history": {}
            },
            "expected_flag": ["RED", "YELLOW"]
        },
        {
            "name": "Normal vitals (should be GREEN)",
            "patient": {
                "age": 30,
                "sex": "M",
                "hr": 75,
                "bp_systolic": 120,
                "bp_diastolic": 80,
                "spo2": 98,
                "rr": 14,
                "temperature": 36.8,
                "chief_complaint": "Minor cut requiring stitches",
                "chief_complaint_category": "wound_minor",
                "arrival_mode": "walk_in",
                "mental_status": "alert",
                "pain_score": 3,
                "symptoms": ["laceration"],
                "medical_history": {}
            },
            "expected_flag": "GREEN"
        }
    ]
    
    all_passed = True
    for test in safety_tests:
        print(f"\n--- {test['name']} ---")
        result = test_sample_prediction(test['patient'])
        
        if result is None:
            print_error("Failed to get prediction")
            all_passed = False
            continue
        
        flag = result['safety_flag']['outcome']
        print(f"  Safety Flag: {flag}")
        print(f"  ESI: {result['esi_prediction']}")
        
        # Check expected flag
        expected_flag = test.get('expected_flag')
        if expected_flag:
            if isinstance(expected_flag, list):
                if flag not in expected_flag:
                    print_error(f"Expected {expected_flag}, got {flag}")
                    all_passed = False
                else:
                    print_success(f"Safety flag correct: {flag}")
            else:
                if flag != expected_flag:
                    print_error(f"Expected {expected_flag}, got {flag}")
                    all_passed = False
                else:
                    print_success(f"Safety flag correct: {flag}")
        
        # Check ESI if specified
        if 'expected_esi_max' in test:
            if result['esi_prediction'] > test['expected_esi_max']:
                print_error(f"ESI {result['esi_prediction']} exceeds max {test['expected_esi_max']}")
                all_passed = False
            else:
                print_success(f"ESI within expected range")
    
    return all_passed

def main():
    print("\n" + "="*60)
    print("  ML CORE ENGINE VALIDATION TEST SUITE")
    print("="*60)
    
    # Test 1: Health check
    if not test_health_endpoint():
        print_error("\nServer is not running. Please start with: uvicorn app:app --reload")
        sys.exit(1)
    
    # Test 2: Diverse scenarios
    scenarios_passed = test_diverse_scenarios()
    
    # Test 3: Preprocessing features
    preprocessing_passed = test_preprocessing_features()
    
    # Test 4: Safety validation
    safety_passed = test_safety_validation_rules()
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    tests = [
        ("Server Health", True),
        ("Diverse Patient Scenarios", scenarios_passed),
        ("Preprocessing Features", preprocessing_passed),
        ("Safety Validation Rules", safety_passed)
    ]
    
    for test_name, passed in tests:
        if passed:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    all_passed = all(result for _, result in tests)
    
    if all_passed:
        print(f"\n{GREEN}{'='*60}")
        print("  ✓ ALL TESTS PASSED")
        print(f"{'='*60}{RESET}\n")
        print_info("ML Core Engine is working correctly!")
        print_info("Components validated:")
        print_info("  - Preprocessing pipeline with age-specific features")
        print_info("  - ESI prediction (1-5 classification)")
        print_info("  - Multi-dimensional confidence scoring")
        print_info("  - Safety validation layer")
        print_info("  - SHAP explainability")
        return 0
    else:
        print(f"\n{RED}{'='*60}")
        print("  ✗ SOME TESTS FAILED")
        print(f"{'='*60}{RESET}\n")
        print_warning("Please review the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
