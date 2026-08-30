#!/usr/bin/env python3
"""
Simple end-to-end test: Manual form submission via curl
"""

import requests
import json

# Test data that matches form submission
test_patient = {
    "age": 45,
    "sex": "M",
    "hr": 105,
    "bp_systolic": 145,
    "bp_diastolic": 90,
    "spo2": 97,
    "rr": 18,
    "temperature": 37.2,
    "chief_complaint": "Chest pain",
    "chief_complaint_category": "chest_pain_cardiac",
    "arrival_mode": "ambulance",
    "mental_status": "alert",
    "pain_score": 6,
    "symptoms": [],
    "medical_history": {}
}

print("="*60)
print("  End-to-End Test: Form Submission")
print("="*60)
print()

print("📤 Submitting patient data...")
print(f"   Age: {test_patient['age']}, Sex: {test_patient['sex']}")
print(f"   Chief Complaint: {test_patient['chief_complaint']}")
print(f"   HR: {test_patient['hr']}, SpO2: {test_patient['spo2']}%")
print()

try:
    response = requests.post(
        'http://localhost:8000/api/v1/predict',
        json=test_patient,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("✅ Success! Received prediction:")
        print()
        print(f"   ESI Prediction: {result['esi_prediction']}")
        print(f"   Confidence: {result['confidence_breakdown']['level']} ({result['confidence_breakdown']['overall']:.1f}%)")
        print(f"   Safety Flag: {result['safety_flag']['outcome']}")
        print()
        print("   Top Contributing Factors:")
        for i, factor in enumerate(result['explanation']['top_factors'][:3], 1):
            print(f"      {i}. {factor['feature']}: {factor['direction']} (SHAP: {factor['shap_value']:+.3f})")
        print()
        print("✅ Frontend-backend integration is working!")
        print()
        print("Next step: Open frontend/index.html in a browser to test the UI")
        
    else:
        print(f"❌ Error: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Make sure the backend server is running:")
    print("   uvicorn app:app --reload")
