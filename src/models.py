"""
Pydantic data models for PatientTriage.ai ML Core Engine API contracts.

This module defines all request/response models for the triage prediction system,
including patient data, processed features, confidence scoring, safety validation,
and prediction responses.

Requirements: 1.3, 13.1, 13.2, 20.1, 20.3, 20.4
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator, model_serializer


# ============================================================================
# Enums for categorical fields
# ============================================================================

class AgeGroup(str, Enum):
    """Age group classification for age-stratified vital assessment."""
    PEDIATRIC_INFANT = "pediatric_infant"  # 0-2 years
    PEDIATRIC_CHILD = "pediatric_child"    # 3-12 years
    PEDIATRIC_ADOLESCENT = "pediatric_adolescent"  # 13-17 years
    ADULT = "adult"                        # 18-64 years
    GERIATRIC = "geriatric"                # 65+ years


class ESILevel(int, Enum):
    """Emergency Severity Index levels (1=most critical, 5=least urgent)."""
    RESUSCITATION = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    NON_URGENT = 5


class ConfidenceLevel(str, Enum):
    """Overall confidence classification."""
    HIGH = "HIGH"      # Above 80%
    MEDIUM = "MEDIUM"  # 60-80%
    LOW = "LOW"        # Below 60%


class SafetyOutcome(str, Enum):
    """Safety validation outcomes."""
    RED = "RED"        # Critical safety concern, force escalation
    YELLOW = "YELLOW"  # Warning, recommend escalation/validation
    GREEN = "GREEN"    # No safety concerns, approve ML prediction


class DeteriorationStatus(str, Enum):
    """Patient deterioration classification."""
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"
    UNCERTAIN = "UNCERTAIN"


class ArrivalMode(str, Enum):
    """Patient arrival mode."""
    AMBULANCE = "ambulance"
    WALK_IN = "walk_in"
    POLICE = "police"
    TRANSFER = "transfer"


class MentalStatus(str, Enum):
    """Patient mental status assessment."""
    ALERT = "alert"
    VERBAL = "verbal"
    PAIN = "pain"
    UNRESPONSIVE = "unresponsive"
    CONFUSED = "confused"
    DROWSY = "drowsy"  # Added to match HTML forms


# ============================================================================
# Input Models - Patient Data
# ============================================================================

class Demographics(BaseModel):
    """Patient demographic information."""
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: str = Field(..., pattern="^(male|female|other)$", description="Patient biological sex")
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        """Validate age is within physiologically valid range."""
        if not (0 <= v <= 120):
            raise ValueError("Age must be between 0 and 120 years")
        return v


class VitalSigns(BaseModel):
    """Patient vital signs with physiological validation."""
    hr: Optional[int] = Field(None, ge=20, le=300, description="Heart rate in bpm")
    bp_systolic: Optional[int] = Field(None, ge=50, le=250, description="Systolic blood pressure in mmHg")
    bp_diastolic: Optional[int] = Field(None, ge=30, le=150, description="Diastolic blood pressure in mmHg")
    spo2: Optional[int] = Field(None, ge=0, le=100, description="Oxygen saturation percentage")
    rr: Optional[int] = Field(None, ge=5, le=60, description="Respiratory rate per minute")
    temperature: Optional[float] = Field(None, ge=32.0, le=45.0, description="Body temperature in Celsius")
    
    @field_validator('hr')
    @classmethod
    def validate_hr(cls, v: Optional[int]) -> Optional[int]:
        """Validate heart rate is physiologically valid."""
        if v is not None and not (20 <= v <= 300):
            raise ValueError("Heart rate must be between 20 and 300 bpm")
        return v
    
    @field_validator('spo2')
    @classmethod
    def validate_spo2(cls, v: Optional[int]) -> Optional[int]:
        """Validate SpO2 is within valid percentage range."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError("SpO2 must be between 0 and 100 percent")
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is physiologically valid."""
        if v is not None and not (32.0 <= v <= 45.0):
            raise ValueError("Temperature must be between 32.0 and 45.0 degrees Celsius")
        return v
    
    @field_validator('bp_systolic', 'bp_diastolic')
    @classmethod
    def validate_bp(cls, v: Optional[int]) -> Optional[int]:
        """Validate blood pressure values are physiologically valid."""
        if v is not None:
            if 'systolic' in cls.model_fields and not (50 <= v <= 250):
                raise ValueError("Systolic BP must be between 50 and 250 mmHg")
            elif 'diastolic' in cls.model_fields and not (30 <= v <= 150):
                raise ValueError("Diastolic BP must be between 30 and 150 mmHg")
        return v


class ClinicalData(BaseModel):
    """Clinical assessment data."""
    chief_complaint: str = Field(..., min_length=1, description="Primary reason for ED visit")
    chief_complaint_category: str = Field(..., description="Standardized complaint category")
    pain_score: Optional[int] = Field(None, ge=0, le=10, description="Pain score 0-10")
    arrival_mode: ArrivalMode = Field(..., description="Mode of arrival to ED")
    mental_status: MentalStatus = Field(..., description="Patient mental status")


class Symptoms(BaseModel):
    """Patient symptoms and observations."""
    symptom_list: List[str] = Field(default_factory=list, description="List of reported symptoms")
    symptom_count: int = Field(0, ge=0, description="Total number of symptoms")
    symptom_duration_hours: Optional[float] = Field(None, ge=0, description="Duration of symptoms in hours")


class MedicalHistory(BaseModel):
    """Patient medical history."""
    conditions: List[str] = Field(default_factory=list, description="Pre-existing medical conditions")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")
    previous_ed_visits: Optional[int] = Field(None, ge=0, description="Number of ED visits in last 12 months")


class ClinicalObservations(BaseModel):
    """Clinical observations and notes."""
    observations: List[str] = Field(default_factory=list, description="Clinical observations")
    triage_nurse_notes: Optional[str] = Field(None, description="Free-text nurse notes")


class PatientData(BaseModel):
    """
    Complete patient data for ESI triage prediction.
    
    Requirements: 1.3, 20.1, 20.3
    """
    demographics: Demographics = Field(..., description="Patient demographic information")
    vitals: VitalSigns = Field(..., description="Vital signs")
    clinical: ClinicalData = Field(..., description="Clinical assessment")
    symptoms: Symptoms = Field(default_factory=Symptoms, description="Symptoms and observations")
    medical_history: MedicalHistory = Field(default_factory=MedicalHistory, description="Medical history")
    observations: ClinicalObservations = Field(default_factory=ClinicalObservations, description="Clinical observations")
    request_id: Optional[str] = Field(None, description="Optional request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")
    
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serialization for consistent JSON formatting."""
        return {
            "demographics": self.demographics.model_dump(),
            "vitals": self.vitals.model_dump(),
            "clinical": self.clinical.model_dump(),
            "symptoms": self.symptoms.model_dump(),
            "medical_history": self.medical_history.model_dump(),
            "observations": self.observations.model_dump(),
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# Intermediate Models - Processed Features
# ============================================================================

class VitalDeviations(BaseModel):
    """Age-normalized vital sign deviations from expected ranges."""
    hr_deviation: Optional[float] = Field(None, description="Heart rate deviation (normalized)")
    bp_systolic_deviation: Optional[float] = Field(None, description="Systolic BP deviation (normalized)")
    bp_diastolic_deviation: Optional[float] = Field(None, description="Diastolic BP deviation (normalized)")
    rr_deviation: Optional[float] = Field(None, description="Respiratory rate deviation (normalized)")
    spo2_deviation: Optional[float] = Field(None, description="SpO2 deviation (normalized)")
    temperature_deviation: Optional[float] = Field(None, description="Temperature deviation (normalized)")


class DiscordanceFlags(BaseModel):
    """Symptom-vital discordance indicators for under-reporting detection."""
    pain_underreported: bool = Field(False, description="Pain score < 4 but HR > 110")
    severity_underreported: bool = Field(False, description="Minor complaint but 3+ abnormal vitals")
    respiratory_underreported: bool = Field(False, description="SpO2 < 93 but no respiratory symptoms")


class MissingIndicators(BaseModel):
    """Binary indicators for missing optional features."""
    is_missing_temperature: bool = Field(False, description="Temperature not provided")
    is_missing_pain_score: bool = Field(False, description="Pain score not provided")
    is_missing_medical_history: bool = Field(False, description="Medical history not provided")
    is_missing_medications: bool = Field(False, description="Medications not provided")
    is_missing_symptom_duration: bool = Field(False, description="Symptom duration not provided")


class ProcessedFeatures(BaseModel):
    """
    Engineered features after preprocessing pipeline.
    
    Requirements: 1.1, 1.2, 10.2, 10.3
    """
    age_group: AgeGroup = Field(..., description="Classified age group")
    vital_deviations: VitalDeviations = Field(..., description="Age-normalized vital deviations")
    discordance_flags: DiscordanceFlags = Field(..., description="Symptom-vital discordance indicators")
    missing_indicators: MissingIndicators = Field(..., description="Missing data indicators")
    data_completeness_score: float = Field(..., ge=0.0, le=1.0, description="Percentage of features present (0-1)")
    
    # Original features passed through
    raw_features: Dict[str, Any] = Field(default_factory=dict, description="Original patient features")


# ============================================================================
# Output Models - Confidence and Safety
# ============================================================================

class ConfidenceBreakdown(BaseModel):
    """
    Multi-dimensional confidence scoring breakdown.
    
    Requirements: 13.1, 13.2
    """
    model_certainty: float = Field(..., ge=0.0, le=100.0, description="Model certainty from probability entropy (0-100)")
    data_completeness: float = Field(..., ge=0.0, le=100.0, description="Data completeness score (0-100)")
    clinical_consistency: float = Field(..., ge=0.0, le=100.0, description="Clinical consistency score (0-100)")
    pattern_recognition: float = Field(..., ge=0.0, le=100.0, description="Pattern recognition score from OOD detection (0-100)")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted overall confidence score (0-100)")
    confidence_level: ConfidenceLevel = Field(..., description="Classification: HIGH/MEDIUM/LOW")
    
    @field_validator('confidence_level', mode='before')
    @classmethod
    def determine_confidence_level(cls, v, info) -> ConfidenceLevel:
        """Determine confidence level from overall score if not provided."""
        if isinstance(v, ConfidenceLevel):
            return v
        
        # Calculate from overall_score if available in values
        overall_score = info.data.get('overall_score')
        if overall_score is not None:
            if overall_score >= 80:
                return ConfidenceLevel.HIGH
            elif overall_score >= 60:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
        return v


class SafetyValidation(BaseModel):
    """
    Safety validation layer results.
    
    Requirements: 20.4
    """
    outcome: SafetyOutcome = Field(..., description="Safety outcome: RED/YELLOW/GREEN")
    triggered_criteria: List[str] = Field(default_factory=list, description="List of triggered safety criteria")
    recommended_action: str = Field(..., description="Recommended action based on safety assessment")
    forced_esi_override: Optional[ESILevel] = Field(None, description="Forced ESI level if safety override triggered")


class SHAPExplanation(BaseModel):
    """SHAP-based feature importance explanation."""
    feature_name: str = Field(..., description="Feature name")
    feature_value: Any = Field(..., description="Feature value")
    shap_value: float = Field(..., description="SHAP contribution value")
    direction: str = Field(..., pattern="^(increases|decreases)$", description="Direction of influence")
    severity: str = Field(..., pattern="^(critical|concerning|normal)$", description="Severity classification")


class PredictionResponse(BaseModel):
    """
    Complete ESI triage prediction response.
    
    Requirements: 20.1, 20.3, 20.4
    """
    request_id: str = Field(..., description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Prediction timestamp")
    
    # Core prediction
    esi_level: ESILevel = Field(..., description="Predicted ESI level (1-5)")
    probability_distribution: Dict[int, float] = Field(
        ..., 
        description="Probability distribution across all ESI levels"
    )
    
    # Confidence and safety
    confidence_breakdown: ConfidenceBreakdown = Field(..., description="Multi-dimensional confidence scores")
    safety_validation: SafetyValidation = Field(..., description="Safety validation results")
    
    # Explainability
    shap_explanation: List[SHAPExplanation] = Field(
        ..., 
        min_length=3,
        max_length=5,
        description="Top 3-5 contributing factors with SHAP values"
    )
    explanation_text: str = Field(..., description="Human-readable explanation")
    
    # Additional metadata
    sub_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Surge mode sub-prioritization score (0-100)")
    model_version: str = Field(..., description="Model version identifier")
    inference_time_ms: float = Field(..., ge=0, description="Total inference time in milliseconds")
    
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serialization for consistent JSON formatting."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "esi_level": self.esi_level.value,
            "probability_distribution": self.probability_distribution,
            "confidence_breakdown": self.confidence_breakdown.model_dump(),
            "safety_validation": self.safety_validation.model_dump(),
            "shap_explanation": [exp.model_dump() for exp in self.shap_explanation],
            "explanation_text": self.explanation_text,
            "sub_score": self.sub_score,
            "model_version": self.model_version,
            "inference_time_ms": round(self.inference_time_ms, 2)
        }


# ============================================================================
# Deterioration Detection Models
# ============================================================================

class VitalChange(BaseModel):
    """Temporal vital sign change metrics."""
    vital_name: str = Field(..., description="Vital sign name")
    initial_value: float = Field(..., description="Initial value at triage")
    current_value: float = Field(..., description="Current value")
    delta: float = Field(..., description="Absolute change")
    percent_change: float = Field(..., description="Percentage change")
    rate_of_change: float = Field(..., description="Rate of change per minute")
    trend: str = Field(..., pattern="^(improving|stable|worsening)$", description="Trend direction")


class DeteriorationRequest(BaseModel):
    """
    Request for deterioration assessment.
    
    Requirements: Requirements 4.*
    """
    patient_id: str = Field(..., description="Patient identifier")
    initial_esi_level: ESILevel = Field(..., description="Initial ESI level from triage")
    time_since_triage_minutes: int = Field(..., ge=0, description="Minutes since initial triage")
    
    # Vital sign changes
    vital_changes: List[VitalChange] = Field(..., min_length=1, description="Temporal vital sign changes")
    
    # Current state
    current_vitals: VitalSigns = Field(..., description="Current vital signs")
    current_symptoms: Optional[List[str]] = Field(None, description="Current symptoms")
    
    request_id: Optional[str] = Field(None, description="Optional request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")


class DeteriorationResponse(BaseModel):
    """
    Deterioration assessment response.
    
    Requirements: Requirements 4.*
    """
    request_id: str = Field(..., description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Assessment timestamp")
    patient_id: str = Field(..., description="Patient identifier")
    
    # Deterioration assessment
    deterioration_status: DeteriorationStatus = Field(..., description="STABLE/DETERIORATING/UNCERTAIN")
    deterioration_score: float = Field(..., ge=0.0, le=100.0, description="Deterioration score (0-100)")
    
    # Contributing factors
    shap_explanation: List[SHAPExplanation] = Field(
        ...,
        description="Top contributing vital changes"
    )
    explanation_text: str = Field(..., description="Human-readable explanation")
    
    # Recommendations
    recommend_immediate_reassessment: bool = Field(..., description="Flag for immediate clinical reassessment")
    recommended_esi_escalation: Optional[ESILevel] = Field(None, description="Recommended new ESI level if deteriorating")
    
    # Metadata
    model_version: str = Field(..., description="Deterioration model version")
    inference_time_ms: float = Field(..., ge=0, description="Inference time in milliseconds")
    
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """Custom serialization for consistent JSON formatting."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "patient_id": self.patient_id,
            "deterioration_status": self.deterioration_status.value,
            "deterioration_score": round(self.deterioration_score, 2),
            "shap_explanation": [exp.model_dump() for exp in self.shap_explanation],
            "explanation_text": self.explanation_text,
            "recommend_immediate_reassessment": self.recommend_immediate_reassessment,
            "recommended_esi_escalation": self.recommended_esi_escalation.value if self.recommended_esi_escalation else None,
            "model_version": self.model_version,
            "inference_time_ms": round(self.inference_time_ms, 2)
        }
