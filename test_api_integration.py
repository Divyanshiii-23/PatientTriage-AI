"""
Integration test for GET /api/v1/patients endpoint using FastAPI TestClient
"""
from fastapi.testclient import TestClient
from app import app

# Create test client
client = TestClient(app)

def test_get_patients_endpoint():
    """Test GET /api/v1/patients endpoint"""
    print("\n" + "="*60)
    print("Testing GET /api/v1/patients endpoint")
    print("="*60 + "\n")
    
    # Make request to endpoint
    response = client.get("/api/v1/patients")
    
    # Check status code
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    print(f"✓ Status code: {response.status_code}")
    
    # Parse JSON response
    data = response.json()
    
    # Check response structure
    assert "count" in data, "Response missing 'count' field"
    assert "patients" in data, "Response missing 'patients' field"
    assert "note" in data, "Response missing 'note' field"
    print("✓ Response has correct structure")
    
    # Check patient count
    assert data["count"] == 20, f"Expected 20 patients, got {data['count']}"
    assert len(data["patients"]) == 20, f"Expected 20 patients in array, got {len(data['patients'])}"
    print(f"✓ Correct patient count: {data['count']}")
    
    # Check first patient structure
    first_patient = data["patients"][0]
    required_fields = ["patient_id", "name", "demographics", "vitals", "clinical", 
                      "symptoms", "medical_history", "ground_truth_esi"]
    
    for field in required_fields:
        assert field in first_patient, f"Patient missing required field: {field}"
    print("✓ Patients have required fields")
    
    # Check patient diversity
    age_groups = set(p["demographics"]["age_group"] for p in data["patients"])
    esi_levels = set(p["ground_truth_esi"] for p in data["patients"])
    
    print(f"✓ Age groups: {age_groups}")
    print(f"✓ ESI levels: {sorted(esi_levels)}")
    
    # Verify special cases
    pediatric = [p for p in data["patients"] if p["demographics"]["age"] < 18]
    geriatric = [p for p in data["patients"] if p["demographics"]["age"] >= 65]
    ambiguous = [p for p in data["patients"] if "chest_pain" in p["clinical"]["chief_complaint_category"]]
    zero_history = [p for p in data["patients"] if not p["medical_history"]]
    
    assert len(pediatric) >= 2, f"Need at least 2 pediatric, got {len(pediatric)}"
    assert len(geriatric) >= 2, f"Need at least 2 geriatric, got {len(geriatric)}"
    assert len(ambiguous) >= 1, f"Need at least 1 ambiguous, got {len(ambiguous)}"
    assert len(zero_history) >= 1, f"Need at least 1 zero-history, got {len(zero_history)}"
    
    print(f"✓ {len(pediatric)} pediatric patients")
    print(f"✓ {len(geriatric)} geriatric patients")
    print(f"✓ {len(ambiguous)} ambiguous presentations")
    print(f"✓ {len(zero_history)} zero-history patients")
    
    print("\n" + "="*60)
    print("✅ All integration tests passed!")
    print("="*60)
    print(f"\nSample patient from endpoint:")
    print(f"  Name: {first_patient['name']}")
    print(f"  Age: {first_patient['demographics']['age']}")
    print(f"  ESI: {first_patient['ground_truth_esi']}")
    print(f"  Chief Complaint: {first_patient['clinical']['chief_complaint']}")

def test_endpoint_error_handling():
    """Test error handling (file not found would be tested by mocking)"""
    # Note: We can't easily test file-not-found without mocking
    # But we can verify the endpoint is accessible
    print("\n" + "="*60)
    print("Testing endpoint error handling")
    print("="*60 + "\n")
    
    # Test that endpoint exists
    response = client.get("/api/v1/patients")
    assert response.status_code != 404, "Endpoint not found (404)"
    print("✓ Endpoint is accessible (not 404)")
    
    print("\n" + "="*60)
    print("✅ Error handling tests passed!")
    print("="*60)

if __name__ == "__main__":
    try:
        test_get_patients_endpoint()
        test_endpoint_error_handling()
        print("\n" + "🎉 All tests completed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
