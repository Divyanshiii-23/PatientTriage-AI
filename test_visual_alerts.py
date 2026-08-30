#!/usr/bin/env python3
"""
Test script to verify visual alerts are properly implemented
"""

import re
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

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

def test_visual_alerts():
    """Test that visual alerts are properly implemented"""
    print_section("Visual Alerts Implementation Test")
    
    html_path = Path("/Users/divyanshiii/Win/frontend/index.html")
    html_content = html_path.read_text()
    
    tests = []
    
    # Test 1: ESI 1 pulsing animation
    print("Test 1: ESI 1 Pulsing Red Border")
    if re.search(r'high-risk-panel', html_content):
        print_success("high-risk-panel class found")
        tests.append(True)
    else:
        print_error("high-risk-panel class NOT found")
        tests.append(False)
    
    if re.search(r'esi_prediction === 1', html_content):
        print_success("ESI 1 detection logic found")
        tests.append(True)
    else:
        print_error("ESI 1 detection logic NOT found")
        tests.append(False)
    
    if re.search(r'@keyframes pulseBorder', html_content):
        print_success("pulseBorder animation defined")
        tests.append(True)
    else:
        print_error("pulseBorder animation NOT defined")
        tests.append(False)
    
    # Test 2: RED safety flag prominent banner
    print("\nTest 2: RED Safety Flag Prominent Banner")
    if re.search(r'safety-flag-red', html_content):
        print_success("safety-flag-red class found")
        tests.append(True)
    else:
        print_error("safety-flag-red class NOT found")
        tests.append(False)
    
    if re.search(r'CRITICAL SAFETY ALERT', html_content):
        print_success("Critical safety alert text found")
        tests.append(True)
    else:
        print_error("Critical safety alert text NOT found")
        tests.append(False)
    
    if re.search(r'@keyframes pulseAlert', html_content):
        print_success("pulseAlert animation defined")
        tests.append(True)
    else:
        print_error("pulseAlert animation NOT defined")
        tests.append(False)
    
    if re.search(r'animation:.*pulseAlert', html_content):
        print_success("pulseAlert animation applied to RED flag")
        tests.append(True)
    else:
        print_error("pulseAlert animation NOT applied")
        tests.append(False)
    
    # Test 3: LOW confidence warnings
    print("\nTest 3: LOW Confidence Warnings")
    if re.search(r"confidenceLevel === 'LOW'", html_content):
        print_success("LOW confidence detection logic found")
        tests.append(True)
    else:
        print_error("LOW confidence detection logic NOT found")
        tests.append(False)
    
    if re.search(r'LOW CONFIDENCE.*Exercise Clinical Caution', html_content):
        print_success("LOW confidence warning message found")
        tests.append(True)
    else:
        print_error("LOW confidence warning message NOT found")
        tests.append(False)
    
    # Test 4: MEDIUM confidence warning for non-urgent cases
    print("\nTest 4: MEDIUM Confidence Warning (ESI >= 3)")
    if re.search(r"confidenceLevel === 'MEDIUM'.*esi_prediction >= 3", html_content):
        print_success("MEDIUM confidence + ESI >= 3 detection logic found")
        tests.append(True)
    else:
        print_error("MEDIUM confidence + ESI >= 3 detection logic NOT found")
        tests.append(False)
    
    if re.search(r'MEDIUM CONFIDENCE.*Recommend Clinical Validation', html_content):
        print_success("MEDIUM confidence warning message found")
        tests.append(True)
    else:
        print_error("MEDIUM confidence warning message NOT found")
        tests.append(False)
    
    # Test 5: RED safety flag also triggers high-risk panel
    print("\nTest 5: RED Safety Flag Triggers High-Risk Styling")
    if re.search(r"safety_flag\.outcome === 'RED'.*high-risk-panel", html_content, re.DOTALL):
        print_success("RED safety flag triggers high-risk panel class")
        tests.append(True)
    else:
        print_error("RED safety flag does NOT trigger high-risk panel")
        tests.append(False)
    
    # Test 6: Visual styling enhancements
    print("\nTest 6: Enhanced Visual Styling")
    if re.search(r'box-shadow.*rgba\(211, 47, 47', html_content):
        print_success("Enhanced box-shadow for red alerts found")
        tests.append(True)
    else:
        print_error("Enhanced box-shadow NOT found")
        tests.append(False)
    
    # Summary
    print_section("SUMMARY")
    passed = sum(tests)
    total = len(tests)
    percentage = (passed / total) * 100
    
    print(f"Tests Passed: {passed}/{total} ({percentage:.0f}%)")
    print()
    
    if passed == total:
        print(f"{GREEN}{'='*60}")
        print("  ✓ ALL VISUAL ALERT TESTS PASSED")
        print(f"{'='*60}{RESET}\n")
        print_info("Visual alerts implemented correctly:")
        print_info("  ✓ ESI 1 pulsing red border animation")
        print_info("  ✓ RED safety flag prominent banner with animation")
        print_info("  ✓ LOW confidence warnings")
        print_info("  ✓ MEDIUM confidence warnings for ESI >= 3")
        print_info("  ✓ Enhanced visual styling with box-shadows")
        print()
        print_info("To test in browser:")
        print_info("  1. Start backend: uvicorn app:app --reload")
        print_info("  2. Open frontend/index.html")
        print_info("  3. Test with demo patients:")
        print_info("     - Infant with fever (should show RED flag + ESI 2)")
        print_info("     - Low SpO2 case (should show RED flag + ESI 1 + pulsing)")
        print_info("     - Minor injury (should show GREEN flag)")
        return 0
    else:
        print(f"{RED}{'='*60}")
        print("  ✗ SOME TESTS FAILED")
        print(f"{'='*60}{RESET}\n")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(test_visual_alerts())
