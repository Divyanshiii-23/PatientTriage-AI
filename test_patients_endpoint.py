"""
Test script for GET /api/v1/patients endpoint
Task 4.3: Verify the endpoint returns 20 test patients correctly
"""

import requests
import json
import sys

def test_patients_endpoint():
    """Test the GET /api/v1/patients endpoint"""
    print("=" * 60)
    print("Testing GET /api/v1/patients endpoint")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/patients"
    
    try:
        # Make GET request
        print(f"\n📡 Sending GET request to {endpoint}...")
        response = requests.get(endpoint, timeout=5)
        
        # Check status code
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Request successful (200 OK)")
            
            # Parse response
            data = response.json()
            
            # Validate response structure
            print("\n📋 Response Structure:")
            print(f"   - Count: {data.get('count')}")
            print(f"   - Patients array length: {len(data.get('patients', []))}")
            print(f"   - Note: {data.get('note')}")
            
            # Validate patient count
            if data.get('count') == 20:
                print("\n✅ Correct number of patients (20)")
            else:
                print(f"\n❌ Expected 20 patients, got {data.get('count')}")
                return False
            
            # Validate first patient structure
            patients = data.get('patients', [])
            if len(patients) > 0:
                first_patient = patients[0]
                print("\n📝 First Patient Sample:")
                print(f"   - Patient ID: {first_patient.get('patient_id')}")
                print(f"   - Name: {first_patient.get('name')}")
                print(f"   - Age: {first_patient.get('demographics', {}).get('age')}")
                print(f"   - Sex: {first_patient.get('demographics', {}).get('sex')}")
                print(f"   - Chief Complaint: {first_patient.get('clinical', {}).get('chief_complaint')[:50]}...")
                
                # Check required fields
                required_fields = ['patient_id', 'name', 'demographics', 'vitals', 'clinical']
                missing = [f for f in required_fields if f not in first_patient]
                
                if missing:
                    print(f"\n❌ Missing required fields: {missing}")
                    return False
                else:
                    print("\n✅ All required fields present")
            
            # Check patient diversity
            print("\n🔍 Patient Diversity Analysis:")
            pediatric = sum(1 for p in patients if p['demographics']['age'] < 18)
            geriatric = sum(1 for p in patients if p['demographics']['age'] >= 65)
            
            print(f"   - Pediatric (<18): {pediatric} patients")
            print(f"   - Geriatric (≥65): {geriatric} patients")
            print(f"   - Adult (18-64): {20 - pediatric - geriatric} patients")
            
            if pediatric >= 2:
                print("   ✅ At least 2 pediatric patients")
            else:
                print(f"   ⚠️  Only {pediatric} pediatric patients (expected ≥2)")
            
            if geriatric >= 2:
                print("   ✅ At least 2 geriatric patients")
            else:
                print(f"   ⚠️  Only {geriatric} geriatric patients (expected ≥2)")
            
            # Check for ambiguous case (requirement 20.6)
            ambiguous_cases = [
                p for p in patients 
                if 'chest_pain' in p['clinical'].get('chief_complaint_category', '').lower()
                and 40 <= p['demographics']['age'] <= 50
            ]
            print(f"\n   - Ambiguous cases (chest pain, age 40-50): {len(ambiguous_cases)}")
            if ambiguous_cases:
                print(f"     Example: {ambiguous_cases[0]['name']}, Age {ambiguous_cases[0]['demographics']['age']}")
            
            # Check ESI distribution
            esi_dist = {}
            for p in patients:
                esi = p.get('ground_truth_esi')
                if esi:
                    esi_dist[esi] = esi_dist.get(esi, 0) + 1
            
            print(f"\n   📊 ESI Distribution:")
            for esi in sorted(esi_dist.keys()):
                print(f"      ESI {esi}: {esi_dist[esi]} patients")
            
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Endpoint working correctly")
            print("=" * 60)
            return True
        
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Cannot connect to server")
        print("   Make sure the FastAPI server is running on http://localhost:8000")
        print("   Run: python app.py")
        return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_patients_endpoint()
    sys.exit(0 if success else 1)
