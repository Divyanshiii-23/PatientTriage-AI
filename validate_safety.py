#!/usr/bin/env python3
"""
Quick validation script for safety validation layer.
Tests key safety rules to ensure implementation is correct.
"""

from src.models import (
    PatientData,
    Demographics,
    VitalSigns,
    ClinicalData,
    ArrivalMode,
    MentalStatus,
    ConfidenceBreakdown,
    ConfidenceLevel,
    ESILevel,
    SafetyOutcome
)
from src.safety_validation import SafetyValidator


def test_infant_red_flag():
    """Test: Infant age triggers RED flag."""
    print("\n=== Test 1: Infant Age (<1 year) → RED Flag ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=0, sex="male"),
        vitals=VitalSigns(hr=140, bp_systolic=85, bp_diastolic=55, spo2=98, rr=35),
        clinical=ClinicalData(
            chief_complaint="Fever",
            chief_complaint_category="fever",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = validator.validate(patient, ESILevel.URGENT, confidence)
    
    print(f"✓ Outcome: {result.outcome.value}")
    print(f"✓ Override: {result.forced_esi_override.value if result.forced_esi_override else 'None'}")
    print(f"✓ Criteria: {result.triggered_criteria}")
    
    assert result.outcome == SafetyOutcome.RED, "Should be RED"
    assert result.forced_esi_override == ESILevel.EMERGENT, "Should force ESI 2"
    print("✅ PASSED")


def test_hypoxia_red_flag():
    """Test: SpO2 <90% triggers RED flag."""
    print("\n=== Test 2: SpO2 <90% → RED Flag (ESI 1) ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=55, sex="female"),
        vitals=VitalSigns(hr=105, bp_systolic=135, bp_diastolic=85, spo2=85, rr=26),
        clinical=ClinicalData(
            chief_complaint="Shortness of breath",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = validator.validate(patient, ESILevel.URGENT, confidence)
    
    print(f"✓ Outcome: {result.outcome.value}")
    print(f"✓ Override: {result.forced_esi_override.value if result.forced_esi_override else 'None'}")
    print(f"✓ Criteria: {result.triggered_criteria}")
    
    assert result.outcome == SafetyOutcome.RED, "Should be RED"
    assert result.forced_esi_override == ESILevel.RESUSCITATION, "Should force ESI 1"
    print("✅ PASSED")


def test_chest_pain_age_over_45_yellow():
    """Test: Chest pain + age >45 triggers YELLOW flag."""
    print("\n=== Test 3: Chest Pain + Age >45 → YELLOW Flag ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=52, sex="male"),
        vitals=VitalSigns(hr=95, bp_systolic=140, bp_diastolic=88, spo2=97, rr=16),
        clinical=ClinicalData(
            chief_complaint="Chest pain radiating to left arm",
            chief_complaint_category="chest_pain_cardiac",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = validator.validate(patient, ESILevel.URGENT, confidence)
    
    print(f"✓ Outcome: {result.outcome.value}")
    print(f"✓ Override: {result.forced_esi_override.value if result.forced_esi_override else 'None'}")
    print(f"✓ Criteria: {result.triggered_criteria}")
    
    assert result.outcome == SafetyOutcome.YELLOW, "Should be YELLOW"
    assert result.forced_esi_override is None, "YELLOW doesn't force override"
    print("✅ PASSED")


def test_severe_trauma_red_flag():
    """Test: Severe trauma triggers RED flag."""
    print("\n=== Test 4: Severe Trauma → RED Flag (ESI 1) ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=28, sex="male"),
        vitals=VitalSigns(hr=115, bp_systolic=105, bp_diastolic=70, spo2=94, rr=24),
        clinical=ClinicalData(
            chief_complaint="Major motor vehicle collision",
            chief_complaint_category="trauma_severe",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = validator.validate(patient, ESILevel.EMERGENT, confidence)
    
    print(f"✓ Outcome: {result.outcome.value}")
    print(f"✓ Override: {result.forced_esi_override.value if result.forced_esi_override else 'None'}")
    print(f"✓ Criteria: {result.triggered_criteria}")
    
    assert result.outcome == SafetyOutcome.RED, "Should be RED"
    assert result.forced_esi_override == ESILevel.RESUSCITATION, "Should force ESI 1"
    print("✅ PASSED")


def test_stable_patient_green():
    """Test: Stable patient gets GREEN flag."""
    print("\n=== Test 5: Stable Patient → GREEN Flag ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=28, sex="male"),
        vitals=VitalSigns(hr=75, bp_systolic=120, bp_diastolic=78, spo2=99, rr=14),
        clinical=ClinicalData(
            chief_complaint="Minor laceration",
            chief_complaint_category="laceration",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = validator.validate(patient, ESILevel.LESS_URGENT, confidence)
    
    print(f"✓ Outcome: {result.outcome.value}")
    print(f"✓ Override: {result.forced_esi_override.value if result.forced_esi_override else 'None'}")
    print(f"✓ Criteria: {result.triggered_criteria}")
    
    assert result.outcome == SafetyOutcome.GREEN, "Should be GREEN"
    assert result.forced_esi_override is None, "No override for GREEN"
    print("✅ PASSED")


def test_apply_safety_override():
    """Test: apply_safety_override correctly overrides ML prediction."""
    print("\n=== Test 6: Apply Safety Override ===")
    
    validator = SafetyValidator()
    confidence = ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )
    
    patient = PatientData(
        demographics=Demographics(age=65, sex="female"),
        vitals=VitalSigns(hr=105, bp_systolic=120, bp_diastolic=80, spo2=88, rr=26),
        clinical=ClinicalData(
            chief_complaint="Shortness of breath",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    ml_prediction = ESILevel.URGENT  # ML predicts ESI 3
    
    # Get safety validation
    safety_result = validator.validate(patient, ml_prediction, confidence)
    
    # Apply override
    final_esi, override_applied = validator.apply_safety_override(
        ml_prediction,
        safety_result
    )
    
    print(f"✓ ML Prediction: ESI {ml_prediction.value}")
    print(f"✓ Final ESI: ESI {final_esi.value}")
    print(f"✓ Override Applied: {override_applied}")
    
    assert override_applied is True, "Override should be applied"
    assert final_esi == ESILevel.RESUSCITATION, "Should be forced to ESI 1"
    assert final_esi != ml_prediction, "Should differ from ML"
    print("✅ PASSED")


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("SAFETY VALIDATION LAYER - VALIDATION TESTS")
    print("=" * 70)
    
    try:
        test_infant_red_flag()
        test_hypoxia_red_flag()
        test_chest_pain_age_over_45_yellow()
        test_severe_trauma_red_flag()
        test_stable_patient_green()
        test_apply_safety_override()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Safety Validation Layer Working Correctly!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
