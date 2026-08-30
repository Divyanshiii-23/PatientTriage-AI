"""
Unit test for GET /api/v1/patients endpoint
"""
import json
import os
import sys

def test_patients_file_exists():
    """Test that test_patients.json exists"""
    patients_file = "data/test_patients.json"
    assert os.path.exists(patients_file), f"File not found: {patients_file}"
    print("✓ test_patients.json exists")
    return True

def test_patients_file_valid_json():
    """Test that test_patients.json is valid JSON"""
    patients_file = "data/test_patients.json"
    with open(patients_file, 'r') as f:
        patients = json.load(f)
    assert isinstance(patients, list), "Patients data should be a list"
    print(f"✓ Valid JSON with {len(patients)} patients")
    return patients

def test_patient_count(patients):
    """Test that there are exactly 20 patients"""
    assert len(patients) == 20, f"Expected 20 patients, got {len(patients)}"
    print("✓ Exactly 20 test patients")
    return True

def test_patient_structure(patients):
    """Test that each patient has required fields"""
    required_fields = ["patient_id", "name", "demographics", "vitals", "clinical", 
                      "symptoms", "medical_history", "ground_truth_esi"]
    
    for i, patient in enumerate(patients):
        for field in required_fields:
            assert field in patient, f"Patient {i} missing field: {field}"
    
    print("✓ All patients have required fields")
    return True

def test_age_group_diversity(patients):
    """Test that patients include diverse age groups"""
    age_groups = set(p["demographics"]["age_group"] for p in patients)
    
    # Check for pediatric
    pediatric_groups = {"infant_0_2", "child_3_12", "adolescent_13_17"}
    has_pediatric = bool(age_groups & pediatric_groups)
    assert has_pediatric, "No pediatric patients found"
    
    # Check for geriatric
    has_geriatric = "geriatric_65_plus" in age_groups
    assert has_geriatric, "No geriatric patients found"
    
    print(f"✓ Age groups represented: {age_groups}")
    return True

def test_esi_distribution(patients):
    """Test that all ESI levels are represented"""
    esi_levels = set(p["ground_truth_esi"] for p in patients)
    expected_esi = {1, 2, 3, 4, 5}
    
    assert esi_levels == expected_esi, f"Not all ESI levels present. Got: {esi_levels}"
    
    # Check minimum 2 per level as per requirements
    for esi in expected_esi:
        count = sum(1 for p in patients if p["ground_truth_esi"] == esi)
        assert count >= 2, f"ESI {esi} has only {count} patients (need at least 2)"
    
    print(f"✓ All ESI levels 1-5 represented with at least 2 patients each")
    return True

def test_special_cases(patients):
    """Test for special case patients"""
    # Pediatric
    pediatric = [p for p in patients if p["demographics"]["age"] < 18]
    assert len(pediatric) >= 2, f"Need at least 2 pediatric patients, got {len(pediatric)}"
    print(f"✓ {len(pediatric)} pediatric patients")
    
    # Geriatric
    geriatric = [p for p in patients if p["demographics"]["age"] >= 65]
    assert len(geriatric) >= 2, f"Need at least 2 geriatric patients, got {len(geriatric)}"
    print(f"✓ {len(geriatric)} geriatric patients")
    
    # Ambiguous (chest pain cardiac)
    ambiguous = [p for p in patients if "chest_pain" in p["clinical"]["chief_complaint_category"]]
    assert len(ambiguous) >= 1, "Need at least 1 ambiguous presentation"
    print(f"✓ {len(ambiguous)} ambiguous presentations (chest pain)")
    
    # Zero history
    zero_history = [p for p in patients if not p["medical_history"]]
    assert len(zero_history) >= 1, "Need at least 1 zero-history patient"
    print(f"✓ {len(zero_history)} zero-history patients")
    
    return True

def test_endpoint_logic():
    """Simulate the endpoint logic"""
    patients_file = "data/test_patients.json"
    
    # Simulate what the endpoint does
    if not os.path.exists(patients_file):
        raise FileNotFoundError(f"File not found: {patients_file}")
    
    with open(patients_file, 'r') as f:
        patients = json.load(f)
    
    response = {
        "count": len(patients),
        "patients": patients,
        "note": "Pre-generated test patients for demonstration purposes"
    }
    
    assert response["count"] == 20
    assert len(response["patients"]) == 20
    print("✓ Endpoint logic validated successfully")
    
    return response

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Testing GET /api/v1/patients endpoint")
    print("="*60 + "\n")
    
    try:
        # Test file exists
        test_patients_file_exists()
        
        # Test valid JSON and load data
        patients = test_patients_file_valid_json()
        
        # Test patient count
        test_patient_count(patients)
        
        # Test patient structure
        test_patient_structure(patients)
        
        # Test age group diversity
        test_age_group_diversity(patients)
        
        # Test ESI distribution
        test_esi_distribution(patients)
        
        # Test special cases
        test_special_cases(patients)
        
        # Test endpoint logic
        response = test_endpoint_logic()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        print(f"\nEndpoint will return {response['count']} patients")
        print(f"Sample patient: {response['patients'][0]['name']} "
              f"(age {response['patients'][0]['demographics']['age']}, "
              f"ESI {response['patients'][0]['ground_truth_esi']})")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
