"""
Test script for POST /api/v1/override endpoint
Task 4.4: Implement POST /api/v1/override endpoint to log clinician overrides
"""

import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


def test_override_escalation():
    """Test escalation override (clinician ESI < ML ESI)"""
    print("\n=== Test 1: Escalation Override ===")
    
    payload = {
        "patient_id": "test_patient_001",
        "ml_predicted_esi": 3,
        "clinician_final_esi": 2,
        "reason_category": "clinical_judgment",
        "reason_text": "Patient has significant cardiac history and requires closer monitoring."
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data["success"] == True, "Override should succeed"
    assert data["override_direction"] == "escalation", "Should be escalation"
    assert data["override_magnitude"] == 1, "Magnitude should be 1"
    assert "Escalated from ESI 3 to ESI 2" in data["message"], "Message should indicate escalation"
    
    print("✅ Escalation override test passed")
    print(f"   Override ID: {data['override_id']}")
    print(f"   Message: {data['message']}")


def test_override_deescalation():
    """Test de-escalation override (clinician ESI > ML ESI)"""
    print("\n=== Test 2: De-escalation Override ===")
    
    payload = {
        "patient_id": "test_patient_002",
        "ml_predicted_esi": 2,
        "clinician_final_esi": 4,
        "reason_category": "additional_information",
        "reason_text": "Patient states symptoms are chronic and manageable. No acute distress on examination."
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data["success"] == True, "Override should succeed"
    assert data["override_direction"] == "de-escalation", "Should be de-escalation"
    assert data["override_magnitude"] == 2, "Magnitude should be 2"
    assert "De-escalated from ESI 2 to ESI 4" in data["message"], "Message should indicate de-escalation"
    
    print("✅ De-escalation override test passed")
    print(f"   Override ID: {data['override_id']}")
    print(f"   Message: {data['message']}")


def test_override_no_change():
    """Test no change override (clinician ESI == ML ESI)"""
    print("\n=== Test 3: No Change Override ===")
    
    payload = {
        "patient_id": "test_patient_003",
        "ml_predicted_esi": 3,
        "clinician_final_esi": 3,
        "reason_category": "clinical_judgment",
        "reason_text": "ML recommendation is appropriate and consistent with clinical assessment."
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data["success"] == True, "Override should succeed"
    assert data["override_direction"] == "no_change", "Should be no change"
    assert data["override_magnitude"] == 0, "Magnitude should be 0"
    assert "No ESI change" in data["message"], "Message should indicate no change"
    
    print("✅ No change override test passed")
    print(f"   Override ID: {data['override_id']}")
    print(f"   Message: {data['message']}")


def test_all_reason_categories():
    """Test all six reason categories"""
    print("\n=== Test 4: All Reason Categories ===")
    
    categories = [
        "clinical_judgment",
        "additional_information",
        "safety_concern",
        "ml_error",
        "patient_preference",
        "resource_constraint"
    ]
    
    for i, category in enumerate(categories):
        payload = {
            "patient_id": f"test_patient_category_{i}",
            "ml_predicted_esi": 3,
            "clinician_final_esi": 2,
            "reason_category": category,
            "reason_text": f"Testing {category} category with sufficient detail for validation."
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
        assert response.status_code == 200, f"Failed for category {category}: {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, f"Override failed for category {category}"
    
    print(f"✅ All {len(categories)} reason categories test passed")


def test_validation_short_reason():
    """Test validation: reason text too short"""
    print("\n=== Test 5: Validation - Short Reason Text ===")
    
    payload = {
        "patient_id": "test_patient_validation",
        "ml_predicted_esi": 3,
        "clinician_final_esi": 2,
        "reason_category": "clinical_judgment",
        "reason_text": "Too short"  # Only 9 characters, needs 20
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
    
    assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
    
    data = response.json()
    assert "detail" in data, "Should have validation error details"
    
    print("✅ Validation test passed (correctly rejected short reason)")
    print(f"   Error: {data['detail']}")


def test_validation_invalid_esi():
    """Test validation: invalid ESI level"""
    print("\n=== Test 6: Validation - Invalid ESI Level ===")
    
    payload = {
        "patient_id": "test_patient_invalid_esi",
        "ml_predicted_esi": 3,
        "clinician_final_esi": 6,  # Invalid: must be 1-5
        "reason_category": "clinical_judgment",
        "reason_text": "Testing invalid ESI level validation with sufficient text."
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/override", json=payload)
    
    assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
    
    print("✅ Validation test passed (correctly rejected invalid ESI)")


def test_get_overrides():
    """Test GET /api/v1/overrides endpoint"""
    print("\n=== Test 7: Get Overrides ===")
    
    response = requests.get(f"{BASE_URL}/api/v1/overrides")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "count" in data, "Response should have count"
    assert "overrides" in data, "Response should have overrides list"
    assert isinstance(data["overrides"], list), "Overrides should be a list"
    
    print(f"✅ Get overrides test passed")
    print(f"   Total overrides: {data['count']}")


def verify_overrides_file():
    """Verify overrides.json file exists and is valid"""
    print("\n=== Test 8: Verify Overrides File ===")
    
    try:
        with open('data/overrides.json', 'r') as f:
            overrides = json.load(f)
        
        assert isinstance(overrides, list), "Overrides should be a list"
        
        # Verify structure of first override
        if len(overrides) > 0:
            override = overrides[0]
            required_fields = [
                "override_id", "patient_id", "ml_predicted_esi", 
                "clinician_final_esi", "override_direction", "override_magnitude",
                "reason_category", "reason_text", "timestamp"
            ]
            
            for field in required_fields:
                assert field in override, f"Missing required field: {field}"
        
        print(f"✅ Overrides file verification passed")
        print(f"   File contains {len(overrides)} overrides")
        
    except Exception as e:
        print(f"❌ File verification failed: {str(e)}")
        raise


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Testing POST /api/v1/override Endpoint")
    print("Task 4.4: Log Clinician Overrides")
    print("=" * 60)
    
    tests = [
        test_override_escalation,
        test_override_deescalation,
        test_override_no_change,
        test_all_reason_categories,
        test_validation_short_reason,
        test_validation_invalid_esi,
        test_get_overrides,
        verify_overrides_file
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {test.__name__}")
            print(f"   Error: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
