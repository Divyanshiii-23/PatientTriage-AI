#!/usr/bin/env python3
"""
Test script for Task 5.5: Demo Patient Quick-Load Functionality
Tests that the frontend can fetch and display test patients correctly
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_patients_endpoint():
    """Test that the GET /api/v1/patients endpoint works"""
    print("=" * 80)
    print("Testing GET /api/v1/patients endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/patients")
        
        print(f"\n✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Patient Count: {data['count']}")
            print(f"✅ Patients Loaded: {len(data['patients'])}")
            
            # Check for special case patients
            special_cases = {
                'pediatric': 0,
                'geriatric': 0,
                'ambiguous': 0,
                'zero_history': 0
            }
            
            print("\n" + "=" * 80)
            print("Analyzing Patient Demographics")
            print("=" * 80)
            
            for i, patient in enumerate(data['patients'], 1):
                age = patient['demographics']['age']
                labels = []
                
                # PEDIATRIC
                if age < 18:
                    special_cases['pediatric'] += 1
                    labels.append('PEDIATRIC')
                
                # GERIATRIC
                if age >= 65:
                    special_cases['geriatric'] += 1
                    labels.append('GERIATRIC')
                
                # AMBIGUOUS (chest pain, age 40-50)
                if (patient['patient_id'] == 'd91729c4-6761-4445-bd98-d385d690077b' or
                    (patient['clinical']['chief_complaint_category'] == 'chest_pain_cardiac' and 
                     40 <= age <= 50)):
                    special_cases['ambiguous'] += 1
                    labels.append('AMBIGUOUS')
                
                # ZERO-HISTORY
                history = patient.get('medical_history', {})
                if not history or len(history) == 0:
                    special_cases['zero_history'] += 1
                    labels.append('ZERO-HISTORY')
                
                # Print patient info
                label_str = f" [{', '.join(labels)}]" if labels else ""
                print(f"\n{i}. {patient['name']} ({age}yo, {patient['demographics']['sex']}){label_str}")
                print(f"   Chief Complaint: {patient['clinical']['chief_complaint_category']}")
                print(f"   Ground Truth ESI: {patient.get('ground_truth_esi', 'N/A')}")
            
            print("\n" + "=" * 80)
            print("Special Cases Summary")
            print("=" * 80)
            print(f"PEDIATRIC patients: {special_cases['pediatric']}")
            print(f"GERIATRIC patients: {special_cases['geriatric']}")
            print(f"AMBIGUOUS presentations: {special_cases['ambiguous']}")
            print(f"ZERO-HISTORY patients: {special_cases['zero_history']}")
            
            # Validate requirements
            print("\n" + "=" * 80)
            print("Requirements Validation")
            print("=" * 80)
            
            checks = []
            checks.append(("Total patients = 20", data['count'] == 20))
            checks.append(("At least 2 pediatric patients", special_cases['pediatric'] >= 2))
            checks.append(("At least 2 geriatric patients", special_cases['geriatric'] >= 2))
            checks.append(("At least 1 ambiguous presentation", special_cases['ambiguous'] >= 1))
            checks.append(("At least 1 zero-history patient", special_cases['zero_history'] >= 1))
            
            all_passed = True
            for check_name, result in checks:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status}: {check_name}")
                if not result:
                    all_passed = False
            
            print("\n" + "=" * 80)
            if all_passed:
                print("✅ ALL REQUIREMENTS MET")
            else:
                print("❌ SOME REQUIREMENTS NOT MET")
            print("=" * 80)
            
            return all_passed
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_frontend_structure():
    """Test that the frontend HTML includes the necessary JavaScript"""
    print("\n" + "=" * 80)
    print("Testing Frontend HTML Structure")
    print("=" * 80)
    
    try:
        with open('/Users/divyanshiii/Win/frontend/index.html', 'r') as f:
            html_content = f.read()
        
        checks = [
            ("Demo patient selector dropdown exists", 'id="demo-patient-selector"' in html_content),
            ("loadTestPatients function defined", 'async function loadTestPatients()' in html_content),
            ("populateDemoPatientDropdown function defined", 'function populateDemoPatientDropdown(patients)' in html_content),
            ("autoPopulateForm function defined", 'function autoPopulateForm(patientId)' in html_content),
            ("PEDIATRIC label logic", "'PEDIATRIC'" in html_content),
            ("GERIATRIC label logic", "'GERIATRIC'" in html_content),
            ("AMBIGUOUS label logic", "'AMBIGUOUS'" in html_content),
            ("ZERO-HISTORY label logic", "'ZERO-HISTORY'" in html_content),
            ("Fetch API call to /api/v1/patients", "fetch('http://localhost:8000/api/v1/patients')" in html_content),
            ("DOMContentLoaded event listener", "window.addEventListener('DOMContentLoaded'" in html_content),
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {check_name}")
            if not result:
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ ALL FRONTEND CHECKS PASSED")
        else:
            print("❌ SOME FRONTEND CHECKS FAILED")
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error reading frontend HTML: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("TASK 5.5: Demo Patient Quick-Load Functionality Tests")
    print("=" * 80)
    
    # Test backend endpoint
    backend_ok = test_patients_endpoint()
    
    # Test frontend structure
    frontend_ok = test_frontend_structure()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Backend endpoint: {'✅ PASS' if backend_ok else '❌ FAIL'}")
    print(f"Frontend structure: {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    
    if backend_ok and frontend_ok:
        print("\n✅ TASK 5.5 COMPLETE - All tests passed!")
        print("\nTo test in browser:")
        print("1. Ensure backend is running: uvicorn app:app --reload")
        print("2. Open frontend/index.html in a web browser")
        print("3. The dropdown should auto-populate with 20 test patients")
        print("4. Selecting a patient should auto-fill the form")
        print("5. Special labels should appear: PEDIATRIC, GERIATRIC, AMBIGUOUS, ZERO-HISTORY")
        return 0
    else:
        print("\n❌ TASK 5.5 INCOMPLETE - Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
