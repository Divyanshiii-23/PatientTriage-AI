"""
Unit tests for Pydantic data models.

Tests cover:
- Model instantiation with valid data
- Field validation for physiologically valid ranges
- JSON serialization/deserialization
- Edge cases and boundary conditions
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import (
    Demographics,
    VitalSigns,
    ClinicalData,
    Symptoms,
    MedicalHistory,
    ClinicalObservations,
    PatientData,
    ProcessedFeatures,
    VitalDeviations,
    DiscordanceFlags,
    MissingIndicators,
    ConfidenceBreakdown,
    SafetyValidation,
    SHAPExplanation,
    PredictionResponse,
    VitalChange,
    DeteriorationRequest,
    DeteriorationResponse,
    AgeGroup,
    ESILevel,
    ConfidenceLevel,
    SafetyOutcome,
    DeteriorationStatus,
    ArrivalMode,
    MentalStatus,
)


class TestDemographics:
    """Test Demographics model validation."""
    
    def test_valid_demographics(self):
        """Test creating demographics with valid data."""
        demo = Demographics(age=45, sex="male")
        assert demo.age == 45
        assert demo.sex == "male"
    
    def test_age_boundary_values(self):
        """Test age boundaries (0-120)."""
        Demographics(age=0, sex="female")  # Should pass
        Demographics(age=120, sex="male")  # Should pass
        
        with pytest.raises(ValidationError):
            Demographics(age=-1, sex="female")
        
        with pytest.raises(ValidationError):
            Demographics(age=121, sex="male")
    
    def test_invalid_sex(self):
        """Test invalid sex value."""
        with pytest.raises(ValidationError):
            Demographics(age=30, sex="invalid")


class TestVitalSigns:
    """Test VitalSigns model validation."""
    
    def test_valid_vitals(self):
        """Test creating vital signs with valid data."""
        vitals = VitalSigns(
            hr=80,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98,
            rr=16,
            temperature=37.0
        )
        assert vitals.hr == 80
        assert vitals.spo2 == 98
        assert vitals.temperature == 37.0
    
    def test_optional_fields(self):
        """Test that vital fields are optional."""
        vitals = VitalSigns()
        assert vitals.hr is None
        assert vitals.temperature is None
    
    def test_hr_validation(self):
        """Test heart rate validation (20-300 bpm)."""
        VitalSigns(hr=20)  # Should pass
        VitalSigns(hr=300)  # Should pass
        
        with pytest.raises(ValidationError):
            VitalSigns(hr=19)
        
        with pytest.raises(ValidationError):
            VitalSigns(hr=301)
    
    def test_spo2_validation(self):
        """Test SpO2 validation (0-100%)."""
        VitalSigns(spo2=0)  # Should pass
        VitalSigns(spo2=100)  # Should pass
        
        with pytest.raises(ValidationError):
            VitalSigns(spo2=-1)
        
        with pytest.raises(ValidationError):
            VitalSigns(spo2=101)
    
    def test_temperature_validation(self):
        """Test temperature validation (32-45°C)."""
        VitalSigns(temperature=32.0)  # Should pass
        VitalSigns(temperature=45.0)  # Should pass
        
        with pytest.raises(ValidationError):
            VitalSigns(temperature=31.9)
        
        with pytest.raises(ValidationError):
            VitalSigns(temperature=45.1)


class TestPatientData:
    """Test PatientData model with all components."""
    
    def test_minimal_patient_data(self):
        """Test creating patient data with required fields only."""
        patient = PatientData(
            demographics=Demographics(age=35, sex="female"),
            vitals=VitalSigns(hr=75, bp_systolic=120, bp_diastolic=80, spo2=98, rr=14),
            clinical=ClinicalData(
                chief_complaint="Chest pain",
                chief_complaint_category="cardiac",
                arrival_mode=ArrivalMode.AMBULANCE,
                mental_status=MentalStatus.ALERT
            )
        )
        assert patient.demographics.age == 35
        assert patient.vitals.hr == 75
        assert patient.clinical.chief_complaint == "Chest pain"
    
    def test_complete_patient_data(self):
        """Test creating patient data with all optional fields."""
        patient = PatientData(
            demographics=Demographics(age=67, sex="male"),
            vitals=VitalSigns(
                hr=95,
                bp_systolic=145,
                bp_diastolic=90,
                spo2=94,
                rr=18,
                temperature=38.2
            ),
            clinical=ClinicalData(
                chief_complaint="Shortness of breath",
                chief_complaint_category="respiratory",
                pain_score=6,
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            ),
            symptoms=Symptoms(
                symptom_list=["dyspnea", "cough", "fever"],
                symptom_count=3,
                symptom_duration_hours=24.0
            ),
            medical_history=MedicalHistory(
                conditions=["hypertension", "diabetes"],
                medications=["metformin", "lisinopril"],
                allergies=["penicillin"],
                previous_ed_visits=2
            ),
            observations=ClinicalObservations(
                observations=["appears distressed", "using accessory muscles"],
                triage_nurse_notes="Patient appears in moderate respiratory distress"
            ),
            request_id="test-123"
        )
        assert patient.symptoms.symptom_count == 3
        assert len(patient.medical_history.conditions) == 2
        assert patient.request_id == "test-123"
    
    def test_patient_data_serialization(self):
        """Test custom JSON serialization."""
        patient = PatientData(
            demographics=Demographics(age=40, sex="female"),
            vitals=VitalSigns(hr=80),
            clinical=ClinicalData(
                chief_complaint="Headache",
                chief_complaint_category="neurological",
                arrival_mode=ArrivalMode.WALK_IN,
                mental_status=MentalStatus.ALERT
            )
        )
        serialized = patient.model_dump()
        assert "demographics" in serialized
        assert "vitals" in serialized
        assert "timestamp" in serialized


class TestProcessedFeatures:
    """Test ProcessedFeatures model."""
    
    def test_valid_processed_features(self):
        """Test creating processed features."""
        features = ProcessedFeatures(
            age_group=AgeGroup.ADULT,
            vital_deviations=VitalDeviations(
                hr_deviation=0.5,
                bp_systolic_deviation=0.2
            ),
            discordance_flags=DiscordanceFlags(
                pain_underreported=True,
                severity_underreported=False
            ),
            missing_indicators=MissingIndicators(
                is_missing_temperature=True
            ),
            data_completeness_score=0.85
        )
        assert features.age_group == AgeGroup.ADULT
        assert features.data_completeness_score == 0.85
        assert features.discordance_flags.pain_underreported is True
    
    def test_completeness_score_validation(self):
        """Test data completeness score is between 0 and 1."""
        with pytest.raises(ValidationError):
            ProcessedFeatures(
                age_group=AgeGroup.ADULT,
                vital_deviations=VitalDeviations(),
                discordance_flags=DiscordanceFlags(),
                missing_indicators=MissingIndicators(),
                data_completeness_score=1.5  # Invalid
            )


class TestConfidenceBreakdown:
    """Test ConfidenceBreakdown model."""
    
    def test_valid_confidence_breakdown(self):
        """Test creating confidence breakdown with valid scores."""
        confidence = ConfidenceBreakdown(
            model_certainty=85.0,
            data_completeness=90.0,
            clinical_consistency=80.0,
            pattern_recognition=88.0,
            overall_score=85.75,
            confidence_level=ConfidenceLevel.HIGH
        )
        assert confidence.overall_score == 85.75
        assert confidence.confidence_level == ConfidenceLevel.HIGH
    
    def test_confidence_level_boundaries(self):
        """Test confidence level classification boundaries."""
        # HIGH: >= 80%
        high_conf = ConfidenceBreakdown(
            model_certainty=85.0,
            data_completeness=85.0,
            clinical_consistency=85.0,
            pattern_recognition=85.0,
            overall_score=85.0,
            confidence_level=ConfidenceLevel.HIGH
        )
        assert high_conf.confidence_level == ConfidenceLevel.HIGH
        
        # MEDIUM: 60-80%
        medium_conf = ConfidenceBreakdown(
            model_certainty=70.0,
            data_completeness=70.0,
            clinical_consistency=70.0,
            pattern_recognition=70.0,
            overall_score=70.0,
            confidence_level=ConfidenceLevel.MEDIUM
        )
        assert medium_conf.confidence_level == ConfidenceLevel.MEDIUM
        
        # LOW: < 60%
        low_conf = ConfidenceBreakdown(
            model_certainty=50.0,
            data_completeness=50.0,
            clinical_consistency=50.0,
            pattern_recognition=50.0,
            overall_score=50.0,
            confidence_level=ConfidenceLevel.LOW
        )
        assert low_conf.confidence_level == ConfidenceLevel.LOW


class TestSafetyValidation:
    """Test SafetyValidation model."""
    
    def test_red_safety_outcome(self):
        """Test RED safety outcome with forced escalation."""
        safety = SafetyValidation(
            outcome=SafetyOutcome.RED,
            triggered_criteria=["chest_pain_age_50", "spo2_below_85"],
            recommended_action="Force ESI 1 - Critical condition detected",
            forced_esi_override=ESILevel.RESUSCITATION
        )
        assert safety.outcome == SafetyOutcome.RED
        assert safety.forced_esi_override == ESILevel.RESUSCITATION
        assert len(safety.triggered_criteria) == 2
    
    def test_green_safety_outcome(self):
        """Test GREEN safety outcome with no concerns."""
        safety = SafetyValidation(
            outcome=SafetyOutcome.GREEN,
            triggered_criteria=[],
            recommended_action="No safety concerns - approve ML prediction"
        )
        assert safety.outcome == SafetyOutcome.GREEN
        assert len(safety.triggered_criteria) == 0
        assert safety.forced_esi_override is None


class TestPredictionResponse:
    """Test complete PredictionResponse model."""
    
    def test_valid_prediction_response(self):
        """Test creating a complete prediction response."""
        response = PredictionResponse(
            request_id="test-456",
            esi_level=ESILevel.URGENT,
            probability_distribution={
                1: 0.05,
                2: 0.15,
                3: 0.60,
                4: 0.15,
                5: 0.05
            },
            confidence_breakdown=ConfidenceBreakdown(
                model_certainty=85.0,
                data_completeness=90.0,
                clinical_consistency=80.0,
                pattern_recognition=88.0,
                overall_score=85.75,
                confidence_level=ConfidenceLevel.HIGH
            ),
            safety_validation=SafetyValidation(
                outcome=SafetyOutcome.GREEN,
                triggered_criteria=[],
                recommended_action="Approve ML prediction"
            ),
            shap_explanation=[
                SHAPExplanation(
                    feature_name="hr_deviation",
                    feature_value=1.2,
                    shap_value=0.45,
                    direction="increases",
                    severity="concerning"
                ),
                SHAPExplanation(
                    feature_name="pain_score",
                    feature_value=7,
                    shap_value=0.38,
                    direction="increases",
                    severity="concerning"
                ),
                SHAPExplanation(
                    feature_name="age",
                    feature_value=45,
                    shap_value=0.12,
                    direction="increases",
                    severity="normal"
                )
            ],
            explanation_text="Patient triaged as ESI 3 (Urgent) based on moderate vital abnormalities and pain score",
            model_version="v2.0.0",
            inference_time_ms=85.3
        )
        assert response.esi_level == ESILevel.URGENT
        assert len(response.shap_explanation) == 3
        assert response.confidence_breakdown.confidence_level == ConfidenceLevel.HIGH
    
    def test_shap_explanation_count_validation(self):
        """Test that SHAP explanation must have 3-5 features."""
        # Too few
        with pytest.raises(ValidationError):
            PredictionResponse(
                request_id="test",
                esi_level=ESILevel.URGENT,
                probability_distribution={1: 0.2, 2: 0.3, 3: 0.3, 4: 0.1, 5: 0.1},
                confidence_breakdown=ConfidenceBreakdown(
                    model_certainty=80.0,
                    data_completeness=80.0,
                    clinical_consistency=80.0,
                    pattern_recognition=80.0,
                    overall_score=80.0,
                    confidence_level=ConfidenceLevel.HIGH
                ),
                safety_validation=SafetyValidation(
                    outcome=SafetyOutcome.GREEN,
                    triggered_criteria=[],
                    recommended_action="Approve"
                ),
                shap_explanation=[  # Only 2 items
                    SHAPExplanation(
                        feature_name="hr",
                        feature_value=100,
                        shap_value=0.5,
                        direction="increases",
                        severity="normal"
                    ),
                    SHAPExplanation(
                        feature_name="age",
                        feature_value=40,
                        shap_value=0.3,
                        direction="increases",
                        severity="normal"
                    )
                ],
                explanation_text="Test",
                model_version="v1",
                inference_time_ms=50.0
            )


class TestDeteriorationModels:
    """Test deterioration detection models."""
    
    def test_vital_change(self):
        """Test VitalChange model."""
        change = VitalChange(
            vital_name="heart_rate",
            initial_value=80,
            current_value=110,
            delta=30,
            percent_change=37.5,
            rate_of_change=1.5,
            trend="worsening"
        )
        assert change.vital_name == "heart_rate"
        assert change.delta == 30
        assert change.trend == "worsening"
    
    def test_deterioration_request(self):
        """Test DeteriorationRequest model."""
        request = DeteriorationRequest(
            patient_id="patient-789",
            initial_esi_level=ESILevel.URGENT,
            time_since_triage_minutes=45,
            vital_changes=[
                VitalChange(
                    vital_name="hr",
                    initial_value=80,
                    current_value=110,
                    delta=30,
                    percent_change=37.5,
                    rate_of_change=0.67,
                    trend="worsening"
                )
            ],
            current_vitals=VitalSigns(hr=110, spo2=92)
        )
        assert request.patient_id == "patient-789"
        assert request.time_since_triage_minutes == 45
        assert len(request.vital_changes) == 1
    
    def test_deterioration_response(self):
        """Test DeteriorationResponse model."""
        response = DeteriorationResponse(
            request_id="det-123",
            patient_id="patient-789",
            deterioration_status=DeteriorationStatus.DETERIORATING,
            deterioration_score=75.5,
            shap_explanation=[
                SHAPExplanation(
                    feature_name="hr_rate_of_change",
                    feature_value=0.67,
                    shap_value=0.6,
                    direction="increases",
                    severity="critical"
                ),
                SHAPExplanation(
                    feature_name="spo2_delta",
                    feature_value=-6,
                    shap_value=0.4,
                    direction="increases",
                    severity="concerning"
                )
            ],
            explanation_text="Patient showing signs of deterioration",
            recommend_immediate_reassessment=True,
            recommended_esi_escalation=ESILevel.EMERGENT,
            model_version="v1.0.0",
            inference_time_ms=42.1
        )
        assert response.deterioration_status == DeteriorationStatus.DETERIORATING
        assert response.recommend_immediate_reassessment is True
        assert response.recommended_esi_escalation == ESILevel.EMERGENT


class TestJSONRoundTrip:
    """Test JSON serialization/deserialization round-trip."""
    
    def test_patient_data_round_trip(self):
        """Test PatientData JSON round-trip preservation."""
        original = PatientData(
            demographics=Demographics(age=55, sex="male"),
            vitals=VitalSigns(
                hr=88,
                bp_systolic=135,
                bp_diastolic=85,
                spo2=96,
                rr=16,
                temperature=37.2
            ),
            clinical=ClinicalData(
                chief_complaint="Chest discomfort",
                chief_complaint_category="cardiac",
                pain_score=5,
                arrival_mode=ArrivalMode.AMBULANCE,
                mental_status=MentalStatus.ALERT
            ),
            symptoms=Symptoms(
                symptom_list=["chest pain", "shortness of breath"],
                symptom_count=2,
                symptom_duration_hours=2.5
            ),
            request_id="round-trip-test"
        )
        
        # Serialize to JSON
        json_str = json.dumps(original.model_dump(), default=str)
        
        # Deserialize back
        json_data = json.loads(json_str)
        reconstructed = PatientData(**json_data)
        
        # Verify all fields preserved
        assert reconstructed.demographics.age == original.demographics.age
        assert reconstructed.vitals.hr == original.vitals.hr
        assert reconstructed.clinical.pain_score == original.clinical.pain_score
        assert reconstructed.symptoms.symptom_count == original.symptoms.symptom_count
        assert reconstructed.request_id == original.request_id
    
    def test_prediction_response_round_trip(self):
        """Test PredictionResponse JSON round-trip preservation."""
        original = PredictionResponse(
            request_id="response-test",
            esi_level=ESILevel.EMERGENT,
            probability_distribution={1: 0.1, 2: 0.7, 3: 0.15, 4: 0.04, 5: 0.01},
            confidence_breakdown=ConfidenceBreakdown(
                model_certainty=82.0,
                data_completeness=95.0,
                clinical_consistency=85.0,
                pattern_recognition=90.0,
                overall_score=88.0,
                confidence_level=ConfidenceLevel.HIGH
            ),
            safety_validation=SafetyValidation(
                outcome=SafetyOutcome.GREEN,
                triggered_criteria=[],
                recommended_action="Approve"
            ),
            shap_explanation=[
                SHAPExplanation(
                    feature_name="test",
                    feature_value=1,
                    shap_value=0.5,
                    direction="increases",
                    severity="normal"
                ) for _ in range(3)
            ],
            explanation_text="Test explanation",
            model_version="v2.0.0",
            inference_time_ms=95.7
        )
        
        # Serialize to JSON using custom serializer
        serialized = original.model_dump()
        json_str = json.dumps(serialized, default=str)
        
        # Deserialize back
        json_data = json.loads(json_str)
        
        # Verify key fields preserved
        assert json_data["request_id"] == "response-test"
        assert json_data["esi_level"] == ESILevel.EMERGENT.value
        assert json_data["model_version"] == "v2.0.0"
