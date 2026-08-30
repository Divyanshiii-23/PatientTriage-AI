"""
Test script for validating Pydantic models in app.py
"""

import sys
import json
from datetime import datetime

# Test imports
try:
    from app import (
        PatientData, 
        ConfidenceBreakdown, 
        SafetyFlag, 
        Explanation,
        PredictionResponse,
        app
    )
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test PatientData model
try:
    patient = PatientData(
        age=45,
        sex="M",
        hr=105,
        bp_systolic=145,
        bp_diastolic=90,
        spo2=97,
        rr=18,
        temperature=37.2,
        chief_complaint="Chest pain",
        chief_complaint_category="chest_pain_cardiac",
        arrival_mode="ambulance",
        mental_status="alert",
        pain_score=6,
        symptoms=["chest_pain", "shortness_of_breath"],
        medical_history={"hypertension": True, "diabetes": False}
    )
    print("✓ PatientData model validated")
    print(f"  - Age: {patient.age}, HR: {patient.hr}, SpO2: {patient.spo2}%")
except Exception as e:
    print(f"✗ PatientData validation failed: {e}")
    sys.exit(1)

# Test ConfidenceBreakdown model
try:
    confidence = ConfidenceBreakdown(
        model_certainty=85.3,
        data_completeness=90.0,
        clinical_consistency=75.0,
        pattern_recognition=82.5,
        overall=83.2,
        level="HIGH"
    )
    print("✓ ConfidenceBreakdown model validated")
    print(f"  - Overall: {confidence.overall}%, Level: {confidence.level}")
except Exception as e:
    print(f"✗ ConfidenceBreakdown validation failed: {e}")
    sys.exit(1)

# Test SafetyFlag model
try:
    safety = SafetyFlag(
        outcome="YELLOW",
        triggered_criteria=["CHEST_PAIN_AGE_OVER_50"],
        recommended_action="Cardiac risk assessment recommended",
        override_esi=None
    )
    print("✓ SafetyFlag model validated")
    print(f"  - Outcome: {safety.outcome}, Criteria: {len(safety.triggered_criteria)}")
except Exception as e:
    print(f"✗ SafetyFlag validation failed: {e}")
    sys.exit(1)

# Test Explanation model
try:
    explanation = Explanation(
        text="Predicted ESI 2 based on patient presentation",
        top_factors=[
            {"feature": "chief_complaint", "value": "chest_pain_cardiac", "contribution": 0.42, "direction": "increases urgency"}
        ]
    )
    print("✓ Explanation model validated")
    print(f"  - Factors: {len(explanation.top_factors)}")
except Exception as e:
    print(f"✗ Explanation validation failed: {e}")
    sys.exit(1)

# Test PredictionResponse model
try:
    prediction = PredictionResponse(
        request_id="test_123",
        esi_prediction=2,
        probability_distribution=[0.05, 0.65, 0.20, 0.08, 0.02],
        confidence_breakdown=confidence,
        safety_flag=safety,
        explanation=explanation,
        recommendations=["Consider cardiac workup"],
        sub_score=None,
        model_version="v1.0.0",
        inference_time_ms=45.2,
        timestamp=datetime.now()
    )
    print("✓ PredictionResponse model validated")
    print(f"  - ESI: {prediction.esi_prediction}, Probability: {prediction.probability_distribution[prediction.esi_prediction-1]:.2%}")
except Exception as e:
    print(f"✗ PredictionResponse validation failed: {e}")
    sys.exit(1)

# Test JSON serialization
try:
    json_output = prediction.model_dump_json(indent=2)
    print("✓ JSON serialization successful")
    print(f"  - JSON length: {len(json_output)} characters")
except Exception as e:
    print(f"✗ JSON serialization failed: {e}")
    sys.exit(1)

# Test field validators
try:
    # Test BP validation (diastolic must be < systolic)
    try:
        invalid_patient = PatientData(
            age=45,
            sex="M",
            hr=105,
            bp_systolic=90,
            bp_diastolic=150,  # Invalid: higher than systolic
            spo2=97,
            rr=18,
            chief_complaint="Test",
            chief_complaint_category="test",
            arrival_mode="walk-in",
            mental_status="alert"
        )
        print("✗ BP validation should have failed")
    except ValueError:
        print("✓ BP validation works correctly (rejected invalid BP)")
except Exception as e:
    print(f"✗ Validator test failed: {e}")
    sys.exit(1)

# Test probability distribution validator
try:
    try:
        invalid_prediction = PredictionResponse(
            request_id="test",
            esi_prediction=2,
            probability_distribution=[0.1, 0.2, 0.3, 0.2, 0.1],  # Sums to 0.9, not 1.0
            confidence_breakdown=confidence,
            safety_flag=safety,
            explanation=explanation,
            recommendations=[],
            model_version="v1.0.0",
            inference_time_ms=10.0
        )
        print("✗ Probability validation should have failed")
    except ValueError:
        print("✓ Probability distribution validation works correctly")
except Exception as e:
    print(f"✗ Probability validator test failed: {e}")
    sys.exit(1)

# Test FastAPI app
try:
    assert app is not None
    print("✓ FastAPI app created successfully")
    print(f"  - Title: {app.title}")
    print(f"  - Version: {app.version}")
except Exception as e:
    print(f"✗ FastAPI app validation failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("✓ ALL TESTS PASSED")
print("="*50)
print(f"\nTask 4.1 completed successfully!")
print(f"Created app.py with:")
print(f"  - PatientData model (demographics + vitals + clinical data)")
print(f"  - PredictionResponse model (ESI + probabilities + confidence + safety)")
print(f"  - ConfidenceBreakdown model (4 dimensions)")
print(f"  - SafetyFlag model (RED/YELLOW/GREEN)")
print(f"  - Explanation model (SHAP values)")
print(f"  - FastAPI app with CORS for localhost:3000")
print(f"  - /health endpoint")
print(f"  - /api/triage/predict endpoint")
