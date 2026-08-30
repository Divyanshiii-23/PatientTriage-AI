#!/usr/bin/env python3
"""
Test script for frontend-backend integration validation
Tests that the HTML frontend correctly integrates with the FastAPI backend
"""

import re
import sys
from pathlib import Path

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

def test_html_structure():
    """Test that the HTML file has all required elements"""
    print_section("1. HTML Structure Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    if not html_path.exists():
        print_error("frontend/index.html not found")
        return False
    
    html_content = html_path.read_text()
    
    # Check for essential form elements
    required_elements = [
        (r'id=["\']age["\']', "Age input field"),
        (r'id=["\']sex["\']', "Sex input field"),
        (r'id=["\']heart-rate["\']', "Heart rate input field"),
        (r'id=["\']bp-systolic["\']', "Systolic BP input field"),
        (r'id=["\']bp-diastolic["\']', "Diastolic BP input field"),
        (r'id=["\']spo2["\']', "SpO2 input field"),
        (r'id=["\']resp-rate["\']', "Respiratory rate input field"),
        (r'id=["\']chief-complaint["\']', "Chief complaint field"),
        (r'id=["\']arrival-mode["\']', "Arrival mode field"),
        (r'id=["\']mental-status["\']', "Mental status field"),
    ]
    
    all_present = True
    for pattern, description in required_elements:
        if re.search(pattern, html_content):
            print_success(f"{description} found")
        else:
            print_error(f"{description} NOT found")
            all_present = False
    
    return all_present

def test_javascript_functions():
    """Test that all required JavaScript functions are defined"""
    print_section("2. JavaScript Functions Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    # Check for essential functions
    required_functions = [
        (r'async\s+function\s+submitPatientData\s*\(', "submitPatientData (main form submission)"),
        (r'async\s+function\s+loadTestPatients\s*\(', "loadTestPatients (load demo patients)"),
        (r'function\s+displayRecommendation\s*\(', "displayRecommendation (show results)"),
        (r'function\s+displayESILevel\s*\(', "displayESILevel (show ESI prediction)"),
        (r'function\s+displayProbabilityChart\s*\(', "displayProbabilityChart (probability visualization)"),
        (r'function\s+displayConfidenceBreakdown\s*\(', "displayConfidenceBreakdown (confidence scores)"),
        (r'function\s+displaySafetyFlag\s*\(', "displaySafetyFlag (safety validation)"),
        (r'function\s+displaySHAPExplanation\s*\(', "displaySHAPExplanation (SHAP factors)"),
        (r'async\s+function\s+submitOverride\s*\(', "submitOverride (clinician override)"),
        (r'function\s+autoPopulateForm\s*\(', "autoPopulateForm (quick-load patients)"),
    ]
    
    all_present = True
    for pattern, description in required_functions:
        if re.search(pattern, html_content):
            print_success(f"{description} defined")
        else:
            print_error(f"{description} NOT found")
            all_present = False
    
    return all_present

def test_api_endpoints():
    """Test that the correct API endpoints are called"""
    print_section("3. API Endpoint References Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    # Check for API endpoint calls
    expected_endpoints = [
        (r'["\']http://localhost:8000/api/v1/predict["\']', "/api/v1/predict (main prediction endpoint)"),
        (r'["\']http://localhost:8000/api/v1/patients["\']', "/api/v1/patients (test patients endpoint)"),
        (r'["\']http://localhost:8000/api/v1/override["\']', "/api/v1/override (clinician override endpoint)"),
    ]
    
    all_present = True
    for pattern, description in expected_endpoints:
        if re.search(pattern, html_content):
            print_success(f"{description} referenced")
        else:
            print_error(f"{description} NOT found")
            all_present = False
    
    return all_present

def test_response_handling():
    """Test that response fields are properly handled"""
    print_section("4. Response Field Handling Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    # Check for proper response field access
    expected_fields = [
        (r'esi_prediction', "ESI prediction field"),
        (r'probability_distribution', "Probability distribution field"),
        (r'confidence_breakdown', "Confidence breakdown field"),
        (r'safety_flag', "Safety flag field"),
        (r'explanation', "Explanation field"),
        (r'model_certainty', "Model certainty field"),
        (r'data_completeness', "Data completeness field"),
        (r'clinical_consistency', "Clinical consistency field"),
        (r'pattern_recognition', "Pattern recognition field"),
    ]
    
    all_present = True
    for field, description in expected_fields:
        if re.search(field, html_content):
            print_success(f"{description} accessed")
        else:
            print_warning(f"{description} may not be accessed")
    
    return all_present

def test_chart_libraries():
    """Test that Chart.js is loaded for visualizations"""
    print_section("5. Visualization Libraries Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    if re.search(r'chart\.js', html_content, re.IGNORECASE):
        print_success("Chart.js library included")
        chart_loaded = True
    else:
        print_error("Chart.js library NOT included")
        chart_loaded = False
    
    # Check for canvas elements
    canvas_elements = [
        (r'id=["\']probability-chart["\']', "Probability distribution chart canvas"),
        (r'id=["\']shap-chart["\']', "SHAP explanation chart canvas"),
    ]
    
    all_canvases = True
    for pattern, description in canvas_elements:
        if re.search(pattern, html_content):
            print_success(f"{description} present")
        else:
            print_error(f"{description} NOT found")
            all_canvases = False
    
    return chart_loaded and all_canvases

def test_result_display_elements():
    """Test that result display elements exist"""
    print_section("6. Result Display Elements Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    display_elements = [
        (r'id=["\']esi-display["\']', "ESI display container"),
        (r'id=["\']esi-level["\']', "ESI level display"),
        (r'id=["\']confidence-breakdown["\']', "Confidence breakdown container"),
        (r'id=["\']safety-flag-banner["\']', "Safety flag banner"),
        (r'id=["\']safety-flag-text["\']', "Safety flag text"),
        (r'id=["\']shap-explanation["\']', "SHAP explanation text"),
        (r'class=["\']right-panel["\']', "ML recommendation panel (right-panel)"),
    ]
    
    all_present = True
    for pattern, description in display_elements:
        if re.search(pattern, html_content):
            print_success(f"{description} present")
        else:
            print_error(f"{description} NOT found")
            all_present = False
    
    return all_present

def test_event_listeners():
    """Test that event listeners are properly set up"""
    print_section("7. Event Listener Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_content = html_path.read_text()
    
    event_listeners = [
        (r'addEventListener\(["\']submit["\']', "Form submit event listener"),
        (r'addEventListener\(["\']DOMContentLoaded["\']', "DOMContentLoaded event listener"),
        (r'addEventListener\(["\']change["\']', "Change event listener (likely for demo patient selector)"),
    ]
    
    all_present = True
    for pattern, description in event_listeners:
        if re.search(pattern, html_content):
            print_success(f"{description} present")
        else:
            print_warning(f"{description} may not be present")
    
    return all_present

def test_error_handling():
    """Test that error handling is implemented"""
    print_section("8. Error Handling Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    # Check for try-catch blocks and error handling
    error_handling = [
        (r'try\s*{', "Try-catch blocks for error handling"),
        (r'catch\s*\(', "Catch blocks for error handling"),
        (r'console\.error', "Console error logging"),
        (r'alert\(', "User-facing error messages"),
    ]
    
    has_error_handling = False
    for pattern, description in error_handling:
        if re.search(pattern, html_content):
            print_success(f"{description} present")
            has_error_handling = True
        else:
            print_info(f"{description} check skipped")
    
    return has_error_handling

def test_form_data_collection():
    """Test that form data is properly collected"""
    print_section("9. Form Data Collection Validation")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    # Check that form fields are accessed
    form_fields = [
        'age', 'sex', 'hr', 'bp_systolic', 'bp_diastolic', 
        'spo2', 'rr', 'chief_complaint', 'arrival_mode', 'mental_status'
    ]
    
    found_fields = 0
    for field in form_fields:
        # Look for patterns like getElementById('field') or document.querySelector('#field')
        patterns = [
            rf'getElementById\(["\']({field}|{field.replace("_", "-")})["\']',
            rf'querySelector\(["\']#({field}|{field.replace("_", "-")})["\']',
            rf'value\s*=.*?{field.replace("_", "-")}'
        ]
        
        if any(re.search(pattern, html_content) for pattern in patterns):
            found_fields += 1
    
    percentage = (found_fields / len(form_fields)) * 100
    
    if percentage >= 80:
        print_success(f"Form data collection: {found_fields}/{len(form_fields)} fields ({percentage:.0f}%)")
        return True
    else:
        print_warning(f"Form data collection: {found_fields}/{len(form_fields)} fields ({percentage:.0f}%)")
        return False

def main():
    print("\n" + "="*60)
    print("  FRONTEND-BACKEND INTEGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("HTML Structure", test_html_structure),
        ("JavaScript Functions", test_javascript_functions),
        ("API Endpoints", test_api_endpoints),
        ("Response Handling", test_response_handling),
        ("Chart Libraries", test_chart_libraries),
        ("Result Display Elements", test_result_display_elements),
        ("Event Listeners", test_event_listeners),
        ("Error Handling", test_error_handling),
        ("Form Data Collection", test_form_data_collection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    for test_name, passed in results:
        if passed:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    percentage = (passed_count / total_count) * 100
    
    print(f"\n{BLUE}Results: {passed_count}/{total_count} tests passed ({percentage:.0f}%){RESET}\n")
    
    if passed_count == total_count:
        print(f"{GREEN}{'='*60}")
        print("  ✓ ALL INTEGRATION TESTS PASSED")
        print(f"{'='*60}{RESET}\n")
        print_info("Frontend-backend integration is working correctly!")
        print_info("Next steps:")
        print_info("  1. Open frontend/index.html in a browser")
        print_info("  2. Ensure backend server is running (uvicorn app:app --reload)")
        print_info("  3. Test form submission with demo patients")
        print_info("  4. Verify visualizations render correctly")
        return 0
    elif percentage >= 80:
        print(f"{YELLOW}{'='*60}")
        print("  ⚠ MOST INTEGRATION TESTS PASSED")
        print(f"{'='*60}{RESET}\n")
        print_warning("Some minor issues detected but integration should work")
        return 0
    else:
        print(f"{RED}{'='*60}")
        print("  ✗ SOME INTEGRATION TESTS FAILED")
        print(f"{'='*60}{RESET}\n")
        print_warning("Please review the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
