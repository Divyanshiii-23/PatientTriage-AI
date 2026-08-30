"""
Unit tests for Safety Validation Layer.

Tests all safety rules and edge cases for the safety validation system.
Task: 2.5 - Test safety validation layer
"""

import pytest
from src.models import (
    PatientData,
    Demographics,
    VitalSigns,
    ClinicalData,
    ArrivalMode,
    MentalStatus,
    Symptoms,
    MedicalHistory,
    ClinicalObservations,
    ConfidenceBreakdown,
    ConfidenceLevel,
    ESILevel,
    SafetyOutcome
)
from src.safety_validation import SafetyValidator


@pytest.fixture
def safety_validator():
    """Create safety validator instance for tests."""
    return SafetyValidator()


@pytest.fixture
def baseline_confidence():
    """Create baseline HIGH confidence for tests."""
    return ConfidenceBreakdown(
        model_certainty=85.0,
        data_completeness=90.0,
        clinical_consistency=80.0,
        pattern_recognition=85.0,
        overall_score=85.0,
        confidence_level=ConfidenceLevel.HIGH
    )


@pytest.fixture
def low_confidence():
    """Create LOW confidence for tests."""
    return ConfidenceBreakdown(
        model_certainty=45.0,
        data_completeness=50.0,
        clinical_consistency=55.0,
        pattern_recognition=48.0,
        overall_score=50.0,
        confidence_level=ConfidenceLevel.LOW
    )


def test_infant_age_triggers_red_flag(safety_validator, baseline_confidence):
    """Test Rule 1: Age <1 year triggers RED flag with ESI 2 override."""
    patient_data = PatientData(
        demographics=Demographics(age=0, sex="male"),  # 0 years = infant
        vitals=VitalSigns(
            hr=140,
            bp_systolic=85,
            bp_diastolic=55,
            spo2=98,
            rr=35
        ),
        clinical=ClinicalData(
            chief_complaint="Fever and fussiness",
            chief_complaint_category="fever",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,  # ML predicts ESI 3
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    assert result.forced_esi_override == ESILevel.EMERGENT  # Force ESI 2
    assert any("Infant" in criterion for criterion in result.triggered_criteria)
    assert "Force ESI 2" in result.recommended_action


def test_critical_hypoxia_triggers_red_flag(safety_validator, baseline_confidence):
    """Test Rule 2: SpO2 <90% triggers RED flag with ESI 1 override."""
    patient_data = PatientData(
        demographics=Demographics(age=55, sex="female"),
        vitals=VitalSigns(
            hr=105,
            bp_systolic=135,
            bp_diastolic=85,
            spo2=85,  # Critical hypoxia
            rr=26
        ),
        clinical=ClinicalData(
            chief_complaint="Shortness of breath",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    assert result.forced_esi_override == ESILevel.RESUSCITATION  # Force ESI 1
    assert any("hypoxia" in criterion.lower() for criterion in result.triggered_criteria)
    assert any("SpO2" in criterion for criterion in result.triggered_criteria)
    assert "Force ESI 1" in result.recommended_action


def test_severe_hypotension_triggers_red_flag(safety_validator, baseline_confidence):
    """Test Rule: SBP <90 mmHg triggers RED flag with ESI 1 override."""
    patient_data = PatientData(
        demographics=Demographics(age=45, sex="male"),
        vitals=VitalSigns(
            hr=125,
            bp_systolic=75,  # Severe hypotension
            bp_diastolic=50,
            spo2=96,
            rr=22
        ),
        clinical=ClinicalData(
            chief_complaint="Dizziness and weakness",
            chief_complaint_category="syncope",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    assert result.forced_esi_override == ESILevel.RESUSCITATION  # Force ESI 1
    assert any("hypotension" in criterion.lower() for criterion in result.triggered_criteria)
    assert "Force ESI 1" in result.recommended_action


def test_chest_pain_over_45_triggers_yellow_flag(safety_validator, baseline_confidence):
    """Test Rule 3: Chest pain + age >45 triggers YELLOW flag."""
    patient_data = PatientData(
        demographics=Demographics(age=52, sex="male"),  # > 45 years
        vitals=VitalSigns(
            hr=95,
            bp_systolic=140,
            bp_diastolic=88,
            spo2=97,
            rr=16
        ),
        clinical=ClinicalData(
            chief_complaint="Chest pain radiating to left arm",  # Chest pain
            chief_complaint_category="chest_pain_cardiac",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.YELLOW
    assert result.forced_esi_override is None  # YELLOW doesn't force override
    assert any("Chest pain" in criterion and "cardiac risk" in criterion for criterion in result.triggered_criteria)
    assert "Cardiac risk assessment" in result.recommended_action


def test_chest_pain_under_45_no_yellow_flag(safety_validator, baseline_confidence):
    """Test that chest pain in patient <45 doesn't trigger cardiac YELLOW (unless other criteria)."""
    patient_data = PatientData(
        demographics=Demographics(age=30, sex="male"),  # < 45 years
        vitals=VitalSigns(
            hr=85,
            bp_systolic=125,
            bp_diastolic=80,
            spo2=98,
            rr=14
        ),
        clinical=ClinicalData(
            chief_complaint="Chest pain",
            chief_complaint_category="chest_pain_musculoskeletal",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    # Should be GREEN (no cardiac risk flag for age <45 with normal vitals)
    assert result.outcome == SafetyOutcome.GREEN
    assert result.forced_esi_override is None


def test_severe_trauma_triggers_red_flag(safety_validator, baseline_confidence):
    """Test Rule 4: Severe trauma triggers RED flag with ESI 1 override."""
    patient_data = PatientData(
        demographics=Demographics(age=28, sex="male"),
        vitals=VitalSigns(
            hr=115,
            bp_systolic=105,
            bp_diastolic=70,
            spo2=94,
            rr=24
        ),
        clinical=ClinicalData(
            chief_complaint="Major motor vehicle collision with chest trauma",
            chief_complaint_category="trauma_severe",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.EMERGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    assert result.forced_esi_override == ESILevel.RESUSCITATION  # Force ESI 1
    assert any("trauma" in criterion.lower() for criterion in result.triggered_criteria)
    assert "Force ESI 1" in result.recommended_action


def test_altered_mental_status_triggers_red_flag(safety_validator, baseline_confidence):
    """Test Rule: Altered mental status triggers RED flag with ESI 2 override."""
    patient_data = PatientData(
        demographics=Demographics(age=70, sex="female"),
        vitals=VitalSigns(
            hr=92,
            bp_systolic=135,
            bp_diastolic=82,
            spo2=96,
            rr=18
        ),
        clinical=ClinicalData(
            chief_complaint="Confusion and disorientation",
            chief_complaint_category="altered_mental_status",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.CONFUSED  # Altered
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    assert result.forced_esi_override == ESILevel.EMERGENT  # Force ESI 2
    assert any("mental status" in criterion.lower() for criterion in result.triggered_criteria)
    assert "Force ESI 2" in result.recommended_action


def test_severe_tachycardia_triggers_yellow_flag(safety_validator, baseline_confidence):
    """Test Rule: Severe tachycardia triggers YELLOW flag (age-specific)."""
    patient_data = PatientData(
        demographics=Demographics(age=45, sex="male"),  # Adult
        vitals=VitalSigns(
            hr=155,  # Severe tachycardia for adult (>140)
            bp_systolic=125,
            bp_diastolic=82,
            spo2=97,
            rr=20
        ),
        clinical=ClinicalData(
            chief_complaint="Palpitations and dizziness",
            chief_complaint_category="palpitations",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.YELLOW
    assert result.forced_esi_override is None  # YELLOW doesn't force override
    assert any("tachycardia" in criterion.lower() for criterion in result.triggered_criteria)
    assert "hemodynamic" in result.recommended_action.lower()


def test_low_confidence_with_esi3_triggers_yellow_flag(safety_validator, low_confidence):
    """Test Rule 8: LOW confidence with ESI ≥3 triggers YELLOW flag."""
    patient_data = PatientData(
        demographics=Demographics(age=35, sex="female"),
        vitals=VitalSigns(
            hr=85,
            bp_systolic=120,
            bp_diastolic=78,
            spo2=98,
            rr=16
        ),
        clinical=ClinicalData(
            chief_complaint="Vague abdominal discomfort",
            chief_complaint_category="abdominal_pain",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,  # ESI 3
        confidence=low_confidence  # LOW confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.YELLOW
    assert result.forced_esi_override is None
    assert any("LOW confidence" in criterion for criterion in result.triggered_criteria)
    assert "escalating to ESI" in result.recommended_action


def test_no_safety_concerns_green_flag(safety_validator, baseline_confidence):
    """Test that stable patient with no red flags gets GREEN outcome."""
    patient_data = PatientData(
        demographics=Demographics(age=28, sex="male"),
        vitals=VitalSigns(
            hr=75,
            bp_systolic=120,
            bp_diastolic=78,
            spo2=99,
            rr=14
        ),
        clinical=ClinicalData(
            chief_complaint="Minor laceration to hand",
            chief_complaint_category="laceration",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.LESS_URGENT,  # ESI 4
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.GREEN
    assert result.forced_esi_override is None
    assert "All safety checks passed" in result.triggered_criteria
    assert "No safety concerns" in result.recommended_action


def test_multiple_red_criteria_highest_priority(safety_validator, baseline_confidence):
    """Test that multiple RED criteria result in most critical override."""
    patient_data = PatientData(
        demographics=Demographics(age=0, sex="male"),  # Infant (RED - ESI 2)
        vitals=VitalSigns(
            hr=180,
            bp_systolic=70,  # Hypotension (RED - ESI 1)
            bp_diastolic=45,
            spo2=86,  # Hypoxia (RED - ESI 1)
            rr=55
        ),
        clinical=ClinicalData(
            chief_complaint="Respiratory distress and poor feeding",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.CONFUSED  # Altered (RED - ESI 2)
        )
    )
    
    result = safety_validator.validate(
        patient_data,
        ml_prediction=ESILevel.URGENT,
        confidence=baseline_confidence
    )
    
    # Assertions
    assert result.outcome == SafetyOutcome.RED
    # Should force ESI 1 (most critical from hypoxia/hypotension, evaluated before infant check)
    assert result.forced_esi_override == ESILevel.RESUSCITATION
    # Multiple criteria should be listed
    assert len(result.triggered_criteria) >= 3
    assert any("hypoxia" in c.lower() for c in result.triggered_criteria)
    assert any("hypotension" in c.lower() for c in result.triggered_criteria)


def test_apply_safety_override_with_red_flag(safety_validator, baseline_confidence):
    """Test that apply_safety_override correctly overrides ML prediction."""
    patient_data = PatientData(
        demographics=Demographics(age=65, sex="female"),
        vitals=VitalSigns(
            hr=105,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=88,  # RED - hypoxia
            rr=26
        ),
        clinical=ClinicalData(
            chief_complaint="Shortness of breath",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    ml_prediction = ESILevel.URGENT  # ML predicts ESI 3
    
    # Get safety validation
    safety_result = safety_validator.validate(
        patient_data,
        ml_prediction,
        baseline_confidence
    )
    
    # Apply override
    final_esi, override_applied = safety_validator.apply_safety_override(
        ml_prediction,
        safety_result
    )
    
    # Assertions
    assert override_applied is True
    assert final_esi == ESILevel.RESUSCITATION  # Should be forced to ESI 1
    assert final_esi != ml_prediction  # Should differ from ML


def test_apply_safety_override_no_override(safety_validator, baseline_confidence):
    """Test that apply_safety_override doesn't override when GREEN."""
    patient_data = PatientData(
        demographics=Demographics(age=30, sex="male"),
        vitals=VitalSigns(
            hr=72,
            bp_systolic=118,
            bp_diastolic=76,
            spo2=98,
            rr=14
        ),
        clinical=ClinicalData(
            chief_complaint="Minor sprain",
            chief_complaint_category="sprain",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    ml_prediction = ESILevel.LESS_URGENT  # ML predicts ESI 4
    
    # Get safety validation
    safety_result = safety_validator.validate(
        patient_data,
        ml_prediction,
        baseline_confidence
    )
    
    # Apply override
    final_esi, override_applied = safety_validator.apply_safety_override(
        ml_prediction,
        safety_result
    )
    
    # Assertions
    assert override_applied is False
    assert final_esi == ml_prediction  # Should remain ML prediction


def test_get_safety_recommendations_red_outcome(safety_validator, baseline_confidence):
    """Test that RED outcome generates appropriate recommendations."""
    patient_data = PatientData(
        demographics=Demographics(age=55, sex="male"),
        vitals=VitalSigns(
            hr=125,
            bp_systolic=135,
            bp_diastolic=85,
            spo2=86,  # Hypoxia
            rr=28
        ),
        clinical=ClinicalData(
            chief_complaint="Severe shortness of breath",
            chief_complaint_category="respiratory_distress",
            arrival_mode=ArrivalMode.AMBULANCE,
            mental_status=MentalStatus.ALERT
        )
    )
    
    safety_result = safety_validator.validate(
        patient_data,
        ESILevel.EMERGENT,
        baseline_confidence
    )
    
    recommendations = safety_validator.get_safety_recommendations(
        safety_result,
        patient_data
    )
    
    # Assertions
    assert len(recommendations) > 0
    assert any("CRITICAL" in rec for rec in recommendations)
    assert any("oxygen" in rec.lower() or "o2" in rec.lower() for rec in recommendations)
    assert any("monitoring" in rec.lower() for rec in recommendations)


def test_get_safety_recommendations_yellow_outcome(safety_validator, baseline_confidence):
    """Test that YELLOW outcome generates appropriate recommendations."""
    patient_data = PatientData(
        demographics=Demographics(age=50, sex="male"),
        vitals=VitalSigns(
            hr=105,
            bp_systolic=135,
            bp_diastolic=88,
            spo2=97,
            rr=18
        ),
        clinical=ClinicalData(
            chief_complaint="Chest discomfort",
            chief_complaint_category="chest_pain_cardiac",
            arrival_mode=ArrivalMode.WALK_IN,
            mental_status=MentalStatus.ALERT
        )
    )
    
    safety_result = safety_validator.validate(
        patient_data,
        ESILevel.URGENT,
        baseline_confidence
    )
    
    recommendations = safety_validator.get_safety_recommendations(
        safety_result,
        patient_data
    )
    
    # Assertions
    assert len(recommendations) > 0
    assert any("ECG" in rec or "cardiac" in rec.lower() for rec in recommendations)
    assert any("Enhanced monitoring" in rec or "monitoring" in rec.lower() for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
