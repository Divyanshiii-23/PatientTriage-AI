#!/usr/bin/env python3
"""
Test script to verify frontend fix for 422 validation errors.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_valid_request():
    """Test that a properly formatted request works."""
    print("🧪 Testing valid request...")
    
    payload = {
        "age": 45,
        "sex": "M",
        "hr": 105,
        "bp_systolic": 145,
        "bp_diastolic": 90,
        "spo2": 97,
        "rr": 18,
        "temperature": 37.2,
        "chief_complaint": "chest_pain_cardiac",
        "chief_complaint_category": "chest_pain_cardiac",
        "arrival_mode": "ambulance",
        "mental_status": "alert",
        "pain_score": 6,
        "symptoms": [],
        "medical_history": {}
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/predict", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - ESI: {data['esi_prediction']}, Confidence: {data['confidence_breakdown']['level']}, Safety: {data['safety_flag']['outcome']}")
        return True
    else:
        print(f"❌ FAILED - Status: {response.status_code}")
        print(f"Error: {response.text}")
        return False

def test_invalid_mental_status():
    """Test that invalid mental_status is rejected."""
    print("\n🧪 Testing invalid mental_status (should fail)...")
    
    payload = {
        "age": 45,
        "sex": "M",
        "hr": 105,
        "bp_systolic": 145,
        "bp_diastolic": 90,
        "spo2": 97,
        "rr": 18,
        "temperature": 37.2,
        "chief_complaint": "chest_pain_cardiac",
        "chief_complaint_category": "chest_pain_cardiac",
        "arrival_mode": "ambulance",
        "mental_status": "drowsy",  # Invalid - should be alert/verbal/pain/unresponsive/confused
        "pain_score": 6,
        "symptoms": [],
        "medical_history": {}
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/predict", json=payload)
    
    if response.status_code == 422:
        print(f"✅ Correctly rejected invalid mental_status")
        error_data = response.json()
        print(f"   Error details: {error_data['detail']}")
        return True
    else:
        print(f"❌ UNEXPECTED - Status: {response.status_code} (expected 422)")
        return False

def test_get_patients():
    """Test that GET /api/v1/patients works."""
    print("\n🧪 Testing GET /api/v1/patients...")
    
    response = requests.get(f"{BASE_URL}/api/v1/patients")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - Loaded {data['count']} patients")
        return True
    else:
        print(f"❌ FAILED - Status: {response.status_code}")
        return False

def main():
    print("=" * 60)
    print("Frontend Fix Verification Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Valid request", test_valid_request()))
    results.append(("Invalid mental_status", test_invalid_mental_status()))
    results.append(("GET patients", test_get_patients()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Frontend should now work correctly.")
        print("\n📋 Next steps:")
        print("   1. Close and reopen your browser tab")
        print("   2. Open frontend/index.html")
        print("   3. Select a test patient from dropdown")
        print("   4. Click 'Get AI Triage Recommendation'")
        print("   5. Results should display successfully!")
    else:
        print("\n⚠️ Some tests failed. Please check the backend logs.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
