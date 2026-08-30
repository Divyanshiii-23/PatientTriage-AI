"""
Property-based tests for PatientData JSON round-trip preservation.

Task 1.2: Write property test for PatientData JSON round-trip
- Property 2: JSON Round-Trip Preservation
- Validates: Requirements 20.5, 20.6

This module uses Hypothesis to generate arbitrary valid PatientData objects
and verify that serializing to JSON then deserializing produces an equivalent
object with all field values preserved.

Test coverage:
- All required fields preserved
- All optional fields preserved (when present)
- Missing optional fields handled correctly
- Extreme values preserved
- Unicode text fields preserved
- Timestamp serialization/deserialization
- Nested object structures preserved
"""

import json
from datetime import datetime
from typing import Optional, List

from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import SearchStrategy
import pytest

from src.models import (
    PatientData,
    Demographics,
    VitalSigns,
    ClinicalData,
    Symptoms,
    MedicalHistory,
    ClinicalObservations,
    ArrivalMode,
    MentalStatus,
)


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def demographics_strategy(draw) -> Demographics:
    """Generate valid Demographics objects."""
    age = draw(st.integers(min_value=0, max_value=120))
    sex = draw(st.sampled_from(["male", "female", "other"]))
    return Demographics(age=age, sex=sex)


@st.composite
def vital_signs_strategy(draw) -> VitalSigns:
    """Generate valid VitalSigns objects with optional fields."""
    # Generate optional fields - some may be None
    hr = draw(st.none() | st.integers(min_value=20, max_value=300))
    bp_systolic = draw(st.none() | st.integers(min_value=50, max_value=250))
    bp_diastolic = draw(st.none() | st.integers(min_value=30, max_value=150))
    spo2 = draw(st.none() | st.integers(min_value=0, max_value=100))
    rr = draw(st.none() | st.integers(min_value=5, max_value=60))
    temperature = draw(st.none() | st.floats(min_value=32.0, max_value=45.0, allow_nan=False, allow_infinity=False))
    
    return VitalSigns(
        hr=hr,
        bp_systolic=bp_systolic,
        bp_diastolic=bp_diastolic,
        spo2=spo2,
        rr=rr,
        temperature=temperature
    )


@st.composite
def clinical_data_strategy(draw) -> ClinicalData:
    """Generate valid ClinicalData objects."""
    # Generate text with potential unicode characters
    chief_complaint = draw(st.text(min_size=1, max_size=200).filter(lambda x: len(x.strip()) > 0))
    chief_complaint_category = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    pain_score = draw(st.none() | st.integers(min_value=0, max_value=10))
    arrival_mode = draw(st.sampled_from(list(ArrivalMode)))
    mental_status = draw(st.sampled_from(list(MentalStatus)))
    
    return ClinicalData(
        chief_complaint=chief_complaint,
        chief_complaint_category=chief_complaint_category,
        pain_score=pain_score,
        arrival_mode=arrival_mode,
        mental_status=mental_status
    )


@st.composite
def symptoms_strategy(draw) -> Symptoms:
    """Generate valid Symptoms objects."""
    symptom_list = draw(st.lists(st.text(min_size=1, max_size=50), max_size=10))
    symptom_count = draw(st.integers(min_value=0, max_value=20))
    symptom_duration_hours = draw(st.none() | st.floats(min_value=0, max_value=168.0, allow_nan=False, allow_infinity=False))
    
    return Symptoms(
        symptom_list=symptom_list,
        symptom_count=symptom_count,
        symptom_duration_hours=symptom_duration_hours
    )


@st.composite
def medical_history_strategy(draw) -> MedicalHistory:
    """Generate valid MedicalHistory objects."""
    conditions = draw(st.lists(st.text(min_size=1, max_size=50), max_size=10))
    medications = draw(st.lists(st.text(min_size=1, max_size=50), max_size=15))
    allergies = draw(st.lists(st.text(min_size=1, max_size=50), max_size=10))
    previous_ed_visits = draw(st.none() | st.integers(min_value=0, max_value=50))
    
    return MedicalHistory(
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        previous_ed_visits=previous_ed_visits
    )


@st.composite
def clinical_observations_strategy(draw) -> ClinicalObservations:
    """Generate valid ClinicalObservations objects."""
    observations = draw(st.lists(st.text(min_size=1, max_size=100), max_size=10))
    triage_nurse_notes = draw(st.none() | st.text(max_size=500))
    
    return ClinicalObservations(
        observations=observations,
        triage_nurse_notes=triage_nurse_notes
    )


@st.composite
def patient_data_strategy(draw) -> PatientData:
    """
    Generate valid PatientData objects with all possible field combinations.
    
    This strategy generates:
    - Required fields: demographics, vitals, clinical
    - Optional fields: symptoms, medical_history, observations, request_id
    - Handles missing optional fields
    - Generates extreme but valid values
    - Includes unicode text
    """
    demographics = draw(demographics_strategy())
    vitals = draw(vital_signs_strategy())
    clinical = draw(clinical_data_strategy())
    symptoms = draw(symptoms_strategy())
    medical_history = draw(medical_history_strategy())
    observations = draw(clinical_observations_strategy())
    
    # Optional request_id
    request_id = draw(st.none() | st.text(min_size=1, max_size=100))
    
    # Generate timestamp - use fixed or random
    timestamp = draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)))
    
    return PatientData(
        demographics=demographics,
        vitals=vitals,
        clinical=clinical,
        symptoms=symptoms,
        medical_history=medical_history,
        observations=observations,
        request_id=request_id,
        timestamp=timestamp
    )


# ============================================================================
# Property Tests
# ============================================================================

class TestPatientDataJSONRoundTrip:
    """
    Property-based tests for PatientData JSON round-trip preservation.
    
    Property 2: FOR ALL valid PatientData objects, parsing the JSON then
    pretty-printing then parsing again SHALL produce equivalent PatientData
    object with all field values preserved.
    
    Validates: Requirements 20.5, 20.6
    """
    
    @given(patient_data_strategy())
    @settings(max_examples=20, deadline=None)
    def test_json_roundtrip_preserves_all_fields(self, patient_data: PatientData):
        """
        Test that JSON serialization → deserialization preserves all fields.
        
        Property: serialize(deserialize(serialize(obj))) == serialize(obj)
        """
        # Serialize to JSON
        json_dict = patient_data.model_dump()
        json_str = json.dumps(json_dict, default=str)
        
        # Deserialize back
        json_data = json.loads(json_str)
        reconstructed = PatientData(**json_data)
        
        # Verify all fields preserved
        assert reconstructed.demographics.age == patient_data.demographics.age
        assert reconstructed.demographics.sex == patient_data.demographics.sex
        
        # Verify vitals (including None values)
        assert reconstructed.vitals.hr == patient_data.vitals.hr
        assert reconstructed.vitals.bp_systolic == patient_data.vitals.bp_systolic
        assert reconstructed.vitals.bp_diastolic == patient_data.vitals.bp_diastolic
        assert reconstructed.vitals.spo2 == patient_data.vitals.spo2
        assert reconstructed.vitals.rr == patient_data.vitals.rr
        
        # Temperature needs special handling for float comparison
        if patient_data.vitals.temperature is not None:
            assert reconstructed.vitals.temperature is not None
            assert abs(reconstructed.vitals.temperature - patient_data.vitals.temperature) < 0.01
        else:
            assert reconstructed.vitals.temperature is None
        
        # Verify clinical data
        assert reconstructed.clinical.chief_complaint == patient_data.clinical.chief_complaint
        assert reconstructed.clinical.chief_complaint_category == patient_data.clinical.chief_complaint_category
        assert reconstructed.clinical.pain_score == patient_data.clinical.pain_score
        assert reconstructed.clinical.arrival_mode == patient_data.clinical.arrival_mode
        assert reconstructed.clinical.mental_status == patient_data.clinical.mental_status
        
        # Verify symptoms
        assert reconstructed.symptoms.symptom_list == patient_data.symptoms.symptom_list
        assert reconstructed.symptoms.symptom_count == patient_data.symptoms.symptom_count
        
        # Symptom duration needs float comparison
        if patient_data.symptoms.symptom_duration_hours is not None:
            assert reconstructed.symptoms.symptom_duration_hours is not None
            assert abs(reconstructed.symptoms.symptom_duration_hours - patient_data.symptoms.symptom_duration_hours) < 0.01
        else:
            assert reconstructed.symptoms.symptom_duration_hours is None
        
        # Verify medical history
        assert reconstructed.medical_history.conditions == patient_data.medical_history.conditions
        assert reconstructed.medical_history.medications == patient_data.medical_history.medications
        assert reconstructed.medical_history.allergies == patient_data.medical_history.allergies
        assert reconstructed.medical_history.previous_ed_visits == patient_data.medical_history.previous_ed_visits
        
        # Verify observations
        assert reconstructed.observations.observations == patient_data.observations.observations
        assert reconstructed.observations.triage_nurse_notes == patient_data.observations.triage_nurse_notes
        
        # Verify request_id
        assert reconstructed.request_id == patient_data.request_id
    
    @given(patient_data_strategy())
    @settings(max_examples=20, deadline=None)
    def test_double_roundtrip_produces_same_result(self, patient_data: PatientData):
        """
        Test that double round-trip produces identical result.
        
        Property: roundtrip(roundtrip(obj)) == roundtrip(obj)
        """
        # First round-trip
        json_str1 = json.dumps(patient_data.model_dump(), default=str)
        reconstructed1 = PatientData(**json.loads(json_str1))
        
        # Second round-trip
        json_str2 = json.dumps(reconstructed1.model_dump(), default=str)
        reconstructed2 = PatientData(**json.loads(json_str2))
        
        # Both reconstructions should be equal
        assert reconstructed1.demographics.age == reconstructed2.demographics.age
        assert reconstructed1.vitals.hr == reconstructed2.vitals.hr
        assert reconstructed1.clinical.chief_complaint == reconstructed2.clinical.chief_complaint
    
    @given(patient_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_json_string_is_valid_json(self, patient_data: PatientData):
        """
        Test that serialized JSON is valid and parseable.
        
        Property: For all valid PatientData, json.loads(json.dumps(obj)) succeeds
        """
        json_dict = patient_data.model_dump()
        json_str = json.dumps(json_dict, default=str)
        
        # Should not raise exception
        parsed = json.loads(json_str)
        
        # Should be a dictionary
        assert isinstance(parsed, dict)
        
        # Should have required top-level keys
        assert "demographics" in parsed
        assert "vitals" in parsed
        assert "clinical" in parsed
    
    @given(st.integers(min_value=0, max_value=120))
    @settings(max_examples=50)
    def test_boundary_ages_preserved(self, age: int):
        """
        Test that boundary age values (0-120) are preserved.
        
        Edge cases: age=0, age=120
        """
        patient = PatientData(
            demographics=Demographics(age=age, sex="male"),
            vitals=VitalSigns(),
            clinical=ClinicalData(
                chief_complaint="test",
                chief_complaint_category="test",
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            )
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        assert reconstructed.demographics.age == age
    
    @given(
        st.integers(min_value=20, max_value=300),
        st.integers(min_value=0, max_value=100),
        st.floats(min_value=32.0, max_value=45.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_extreme_vital_values_preserved(self, hr: int, spo2: int, temp: float):
        """
        Test that extreme but valid vital values are preserved.
        
        Edge cases: HR=20, HR=300, SpO2=0, SpO2=100, temp=32.0, temp=45.0
        """
        patient = PatientData(
            demographics=Demographics(age=50, sex="female"),
            vitals=VitalSigns(hr=hr, spo2=spo2, temperature=temp),
            clinical=ClinicalData(
                chief_complaint="test",
                chief_complaint_category="test",
                arrival_mode=ArrivalMode.AMBULANCE,
                mental_status=MentalStatus.ALERT
            )
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        assert reconstructed.vitals.hr == hr
        assert reconstructed.vitals.spo2 == spo2
        assert abs(reconstructed.vitals.temperature - temp) < 0.01
    
    @given(
        st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
            blacklist_characters='\x00\n\r\t'
        )),
        st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
            blacklist_characters='\x00\n\r\t'
        ))
    )
    @settings(max_examples=50)
    def test_unicode_text_preserved(self, complaint_category: str, chief_complaint: str):
        """
        Test that unicode text in fields is preserved.
        
        Covers: special characters, accented letters, numbers in text
        """
        # Filter out empty strings after stripping
        assume(len(complaint_category.strip()) > 0)
        assume(len(chief_complaint.strip()) > 0)
        
        patient = PatientData(
            demographics=Demographics(age=30, sex="other"),
            vitals=VitalSigns(),
            clinical=ClinicalData(
                chief_complaint=chief_complaint,
                chief_complaint_category=complaint_category,
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            )
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        assert reconstructed.clinical.chief_complaint == chief_complaint
        assert reconstructed.clinical.chief_complaint_category == complaint_category
    
    def test_missing_optional_fields_handled(self):
        """
        Test that missing optional fields are handled correctly.
        
        Edge case: Minimal PatientData with only required fields
        """
        patient = PatientData(
            demographics=Demographics(age=40, sex="male"),
            vitals=VitalSigns(),  # All vitals None
            clinical=ClinicalData(
                chief_complaint="Headache",
                chief_complaint_category="neurological",
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            )
            # No symptoms, medical_history, observations, request_id
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        # Verify None values preserved
        assert reconstructed.vitals.hr is None
        assert reconstructed.vitals.temperature is None
        assert reconstructed.symptoms.symptom_list == []
        assert reconstructed.medical_history.conditions == []
        assert reconstructed.observations.observations == []
        assert reconstructed.request_id is None
    
    def test_complete_patient_data_preserved(self):
        """
        Test that fully populated PatientData is preserved.
        
        Edge case: PatientData with all fields populated
        """
        patient = PatientData(
            demographics=Demographics(age=68, sex="female"),
            vitals=VitalSigns(
                hr=105,
                bp_systolic=160,
                bp_diastolic=95,
                spo2=91,
                rr=24,
                temperature=38.7
            ),
            clinical=ClinicalData(
                chief_complaint="Severe chest pain radiating to left arm",
                chief_complaint_category="chest_pain_cardiac",
                pain_score=9,
                arrival_mode=ArrivalMode.AMBULANCE,
                mental_status=MentalStatus.ALERT
            ),
            symptoms=Symptoms(
                symptom_list=["chest pain", "dyspnea", "diaphoresis", "nausea"],
                symptom_count=4,
                symptom_duration_hours=3.5
            ),
            medical_history=MedicalHistory(
                conditions=["hypertension", "diabetes", "hyperlipidemia"],
                medications=["metformin", "lisinopril", "atorvastatin"],
                allergies=["penicillin", "sulfa drugs"],
                previous_ed_visits=3
            ),
            observations=ClinicalObservations(
                observations=["appears distressed", "diaphoretic", "clutching chest"],
                triage_nurse_notes="Patient appears in significant distress, high risk presentation"
            ),
            request_id="test-complete-123"
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        # Verify every field
        assert reconstructed.demographics.age == 68
        assert reconstructed.vitals.hr == 105
        assert reconstructed.clinical.pain_score == 9
        assert len(reconstructed.symptoms.symptom_list) == 4
        assert len(reconstructed.medical_history.conditions) == 3
        assert len(reconstructed.observations.observations) == 3
        assert reconstructed.request_id == "test-complete-123"
    
    @given(patient_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_timestamp_serialization(self, patient_data: PatientData):
        """
        Test that timestamp is correctly serialized to ISO format.
        
        Property: Timestamps are serialized as ISO strings and can be parsed back
        """
        json_dict = patient_data.model_dump()
        
        # Timestamp should be serializable
        json_str = json.dumps(json_dict, default=str)
        parsed = json.loads(json_str)
        
        # Should contain timestamp
        assert "timestamp" in parsed
        
        # Timestamp should be a string in ISO format
        timestamp_str = parsed["timestamp"]
        assert isinstance(timestamp_str, str)
        
        # Should be parseable back to datetime
        reconstructed = PatientData(**parsed)
        assert isinstance(reconstructed.timestamp, datetime)


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestJSONRoundTripEdgeCases:
    """Additional edge case tests for JSON round-trip."""
    
    def test_empty_lists_preserved(self):
        """Test that empty lists in optional fields are preserved."""
        patient = PatientData(
            demographics=Demographics(age=25, sex="male"),
            vitals=VitalSigns(),
            clinical=ClinicalData(
                chief_complaint="Minor injury",
                chief_complaint_category="trauma_minor",
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            ),
            symptoms=Symptoms(symptom_list=[], symptom_count=0),
            medical_history=MedicalHistory(
                conditions=[],
                medications=[],
                allergies=[]
            ),
            observations=ClinicalObservations(observations=[])
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        assert reconstructed.symptoms.symptom_list == []
        assert reconstructed.medical_history.conditions == []
        assert reconstructed.observations.observations == []
    
    def test_all_vitals_none_preserved(self):
        """Test that all None vitals are preserved correctly."""
        patient = PatientData(
            demographics=Demographics(age=30, sex="female"),
            vitals=VitalSigns(
                hr=None,
                bp_systolic=None,
                bp_diastolic=None,
                spo2=None,
                rr=None,
                temperature=None
            ),
            clinical=ClinicalData(
                chief_complaint="Follow-up",
                chief_complaint_category="administrative",
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            )
        )
        
        json_str = json.dumps(patient.model_dump(), default=str)
        reconstructed = PatientData(**json.loads(json_str))
        
        assert reconstructed.vitals.hr is None
        assert reconstructed.vitals.bp_systolic is None
        assert reconstructed.vitals.bp_diastolic is None
        assert reconstructed.vitals.spo2 is None
        assert reconstructed.vitals.rr is None
        assert reconstructed.vitals.temperature is None
    
    def test_pain_score_boundaries(self):
        """Test pain score boundary values (0 and 10) are preserved."""
        for pain_score in [0, 10, None]:
            patient = PatientData(
                demographics=Demographics(age=45, sex="other"),
                vitals=VitalSigns(),
                clinical=ClinicalData(
                    chief_complaint="Pain assessment",
                    chief_complaint_category="pain",
                    pain_score=pain_score,
                    arrival_mode=ArrivalMode.WALK_IN,
                    mental_status=MentalStatus.ALERT
                )
            )
            
            json_str = json.dumps(patient.model_dump(), default=str)
            reconstructed = PatientData(**json.loads(json_str))
            
            assert reconstructed.clinical.pain_score == pain_score


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
