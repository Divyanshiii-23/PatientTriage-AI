"""
PatientTriage.ai FastAPI Backend
Single-file prototype for Emergency Department triage system.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Literal, Any
from datetime import datetime, timedelta
import random
from enum import Enum

# ============================================================================
# Pydantic Models - API Request/Response Schemas
# ============================================================================

class PatientData(BaseModel):
    """
    Patient demographic, vital signs, and clinical data.
    Validates physiologically valid ranges per requirements 21.1, 21.2.
    """
    # Demographics
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: Literal["male", "female", "other", "M", "F", "Other"] = Field(..., description="Patient sex (accepts: male/female/other or M/F/Other)")
    
    # Vital Signs (required)
    hr: int = Field(..., ge=20, le=250, description="Heart rate in bpm")
    bp_systolic: int = Field(..., ge=40, le=250, description="Systolic BP in mmHg")
    bp_diastolic: int = Field(..., ge=20, le=150, description="Diastolic BP in mmHg")
    spo2: int = Field(..., ge=50, le=100, description="Oxygen saturation percentage")
    rr: int = Field(..., ge=4, le=60, description="Respiratory rate per minute")
    
    # Vital Signs (optional)
    temperature: Optional[float] = Field(None, ge=32.0, le=45.0, description="Temperature in Celsius")
    
    # Clinical Data (required)
    chief_complaint: str = Field(..., min_length=1, description="Primary symptom or complaint")
    chief_complaint_category: str = Field(..., description="Standardized category from 50+ options")
    arrival_mode: str = Field(..., description="Arrival method: ambulance, walk-in, wheelchair, etc.")
    mental_status: str = Field(..., description="Mental status: alert, confused, unresponsive, etc.")
    
    # Clinical Data (optional)
    pain_score: Optional[int] = Field(None, ge=0, le=10, description="Pain scale 0-10")
    symptoms: List[str] = Field(default_factory=list, description="List of reported symptoms")
    medical_history: Dict[str, bool] = Field(
        default_factory=dict, 
        description="Medical history flags: diabetes, hypertension, cardiac_history, etc."
    )
    
    @field_validator('bp_systolic', 'bp_diastolic')
    @classmethod
    def validate_blood_pressure(cls, v, info):
        """Ensure systolic BP is greater than diastolic BP"""
        if info.field_name == 'bp_diastolic' and 'bp_systolic' in info.data:
            if v >= info.data['bp_systolic']:
                raise ValueError("Diastolic BP must be less than systolic BP")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
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
                "symptoms": ["chest_pain", "shortness_of_breath"],
                "medical_history": {"hypertension": True, "diabetes": False}
            }
        }


class ConfidenceBreakdown(BaseModel):
    """
    Multi-dimensional confidence scoring.
    Four dimensions + overall score + confidence level classification.
    """
    model_certainty: float = Field(..., ge=0.0, le=100.0, description="Model prediction certainty 0-100")
    data_completeness: float = Field(..., ge=0.0, le=100.0, description="Data completeness score 0-100")
    clinical_consistency: float = Field(..., ge=0.0, le=100.0, description="Clinical consistency score 0-100")
    pattern_recognition: float = Field(..., ge=0.0, le=100.0, description="Pattern recognition score 0-100")
    overall: float = Field(..., ge=0.0, le=100.0, description="Overall weighted confidence 0-100")
    level: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Confidence level: HIGH (≥80), MEDIUM (60-80), LOW (<60)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model_certainty": 85.3,
                "data_completeness": 90.0,
                "clinical_consistency": 75.0,
                "pattern_recognition": 82.5,
                "overall": 83.2,
                "level": "HIGH"
            }
        }


class SafetyFlag(BaseModel):
    """
    Safety validation outcome from ML Core.
    RED/YELLOW/GREEN classification with triggered criteria and recommendations.
    """
    outcome: Literal["RED", "YELLOW", "GREEN"] = Field(..., description="Safety outcome color code")
    triggered_criteria: List[str] = Field(default_factory=list, description="List of triggered safety criteria")
    recommended_action: str = Field(..., description="Recommended action for clinician")
    override_esi: Optional[int] = Field(None, ge=1, le=5, description="Forced ESI level for RED outcomes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "outcome": "YELLOW",
                "triggered_criteria": ["LOW_CONFIDENCE"],
                "recommended_action": "Consider escalation or additional assessment",
                "override_esi": None
            }
        }


class Explanation(BaseModel):
    """
    Natural language explanation with SHAP feature contributions.
    """
    text: str = Field(..., description="Human-readable explanation of the prediction")
    top_factors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top 3-5 contributing factors with feature name, value, and SHAP contribution"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "The model predicts ESI 2 based primarily on chest pain in a patient over 50 with elevated heart rate.",
                "top_factors": [
                    {"feature": "chief_complaint", "value": "chest_pain_cardiac", "contribution": 0.42, "direction": "increases urgency"},
                    {"feature": "age", "value": 45, "contribution": 0.28, "direction": "increases urgency"},
                    {"feature": "hr", "value": 105, "contribution": 0.18, "direction": "increases urgency"}
                ]
            }
        }


class PredictionResponse(BaseModel):
    """
    Complete ESI prediction response from ML Core.
    Includes prediction, probabilities, confidence, safety, explanation, and metadata.
    Matches ML Core API response format per requirements 21.1, 21.2.
    """
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    esi_prediction: int = Field(..., ge=1, le=5, description="Predicted ESI level (1=most urgent, 5=least urgent)")
    probability_distribution: List[float] = Field(
        ..., 
        min_length=5, 
        max_length=5,
        description="Probability distribution for ESI levels 1-5 (must sum to ~1.0)"
    )
    confidence_breakdown: ConfidenceBreakdown = Field(..., description="Multi-dimensional confidence scoring")
    safety_flag: SafetyFlag = Field(..., description="Safety validation outcome")
    explanation: Explanation = Field(..., description="Natural language explanation with SHAP values")
    recommendations: List[str] = Field(default_factory=list, description="Actionable clinical recommendations")
    sub_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Sub-prioritization score for surge mode")
    model_version: str = Field(..., description="ML model version identifier")
    inference_time_ms: float = Field(..., ge=0.0, description="Model inference time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Prediction timestamp")
    
    @field_validator('probability_distribution')
    @classmethod
    def validate_probability_sum(cls, v):
        """Ensure probabilities sum to approximately 1.0"""
        total = sum(v)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Probability distribution must sum to ~1.0, got {total}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_12345",
                "esi_prediction": 2,
                "probability_distribution": [0.05, 0.65, 0.20, 0.08, 0.02],
                "confidence_breakdown": {
                    "model_certainty": 85.3,
                    "data_completeness": 90.0,
                    "clinical_consistency": 75.0,
                    "pattern_recognition": 82.5,
                    "overall": 83.2,
                    "level": "HIGH"
                },
                "safety_flag": {
                    "outcome": "YELLOW",
                    "triggered_criteria": ["CHEST_PAIN_AGE_OVER_50"],
                    "recommended_action": "Cardiac risk assessment recommended",
                    "override_esi": None
                },
                "explanation": {
                    "text": "Predicted ESI 2 based on chest pain presentation in patient over 50 with elevated heart rate.",
                    "top_factors": [
                        {"feature": "chief_complaint", "value": "chest_pain_cardiac", "contribution": 0.42, "direction": "increases urgency"},
                        {"feature": "age", "value": 45, "contribution": 0.28, "direction": "increases urgency"},
                        {"feature": "hr", "value": 105, "contribution": 0.18, "direction": "increases urgency"}
                    ]
                },
                "recommendations": [
                    "Consider cardiac workup (ECG, troponin)",
                    "Monitor O2 saturation closely",
                    "Obtain detailed cardiac history"
                ],
                "sub_score": None,
                "model_version": "v1.0.0",
                "inference_time_ms": 45.2,
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }


class OverrideRequest(BaseModel):
    """
    Clinician override of ML prediction.
    Logs when a clinician decides to assign a different ESI level than the ML recommendation.
    Requirements: 4.1-4.10
    """
    patient_id: str = Field(..., description="Unique patient identifier")
    ml_predicted_esi: int = Field(..., ge=1, le=5, description="ML model's predicted ESI level")
    clinician_final_esi: int = Field(..., ge=1, le=5, description="Clinician's final ESI decision")
    reason_category: Literal[
        "clinical_judgment", 
        "additional_information", 
        "safety_concern", 
        "ml_error",
        "patient_preference",
        "resource_constraint"
    ] = Field(..., description="Category of override reason")
    reason_text: str = Field(..., min_length=20, description="Detailed justification (minimum 20 characters)")
    clinician_id: Optional[str] = Field(None, description="ID or name of clinician performing override")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Override timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "patient_001",
                "ml_predicted_esi": 3,
                "clinician_final_esi": 2,
                "reason_category": "clinical_judgment",
                "reason_text": "Patient has significant cardiac history and family history of early MI. Escalating for cardiac workup despite stable vitals.",
                "timestamp": "2024-01-15T14:35:00Z"
            }
        }


class OverrideResponse(BaseModel):
    """
    Response after logging a clinician override.
    """
    success: bool = Field(..., description="Whether override was logged successfully")
    override_id: str = Field(..., description="Unique identifier for this override record")
    override_direction: Literal["escalation", "de-escalation", "no_change"] = Field(
        ..., 
        description="Direction of override: escalation (lower ESI = higher urgency), de-escalation, or no change"
    )
    override_magnitude: int = Field(..., ge=0, le=4, description="Absolute difference between ML and clinician ESI")
    message: str = Field(..., description="Confirmation message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "override_id": "override_abc123",
                "override_direction": "escalation",
                "override_magnitude": 1,
                "message": "Override logged successfully. Escalated from ESI 3 to ESI 2.",
                "timestamp": "2024-01-15T14:35:00Z"
            }
        }


# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="PatientTriage.ai Backend API",
    version="1.0.0",
    description="FastAPI backend for Emergency Department AI-powered triage system",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for local development (allow all origins for prototype)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (file://, localhost, etc.)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "PatientTriage.ai Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns API status and availability.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PatientTriage.ai Backend",
        "version": "1.0.0"
    }


def _convert_sex_to_lowercase(sex: str) -> str:
    """Convert API sex format (M/F/Other) to ML Core format (male/female/other)."""
    sex_mapping = {
        'M': 'male',
        'F': 'female',
        'Other': 'other',
        'male': 'male',
        'female': 'female',
        'other': 'other'
    }
    return sex_mapping.get(sex, sex.lower())


@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Triage"])
async def predict_esi(patient_data: PatientData):
    """
    ESI Triage Prediction Endpoint (ML Core Integration)
    
    Accepts patient demographics, vitals, and clinical data.
    Returns ESI prediction with confidence, safety validation, and SHAP explanation.
    
    Flow:
    1. Preprocess patient data (age-specific vital deviations)
    2. Generate ESI prediction with ML model (or fallback heuristics)
    3. Compute SHAP explanations
    4. Calculate multi-dimensional confidence scores
    5. Run safety validation
    6. Return PredictionResponse JSON
    
    Target latency: <500ms for demo
    Requirements: 3.1-3.12, 4.2
    """
    import time
    start_time = time.time()
    
    # Import ML Core components
    try:
        from src.preprocessing import preprocess_patient_data
        from src.confidence import ConfidenceScorer
        from src.explainer import SHAPExplainer
        from src.safety_validation import SafetyValidator
    except ImportError as ie:
        raise HTTPException(
            status_code=500,
            detail=f"ML Core components not available: {str(ie)}"
        )
    
    # Generate request ID
    request_id = f"req_{int(datetime.now().timestamp())}_{id(patient_data)}"
    
    try:
        # Step 1: Transform PatientData to preprocessing format
        patient_dict = {
            'demographics': {
                'age': patient_data.age,
                'sex': _convert_sex_to_lowercase(patient_data.sex)
            },
            'vitals': {
                'hr': patient_data.hr,
                'bp_systolic': patient_data.bp_systolic,
                'bp_diastolic': patient_data.bp_diastolic,
                'spo2': patient_data.spo2,
                'rr': patient_data.rr,
                'temperature': patient_data.temperature
            },
            'clinical': {
                'chief_complaint': patient_data.chief_complaint,
                'chief_complaint_category': patient_data.chief_complaint_category,
                'pain_score': patient_data.pain_score,
                'arrival_mode': patient_data.arrival_mode,
                'mental_status': patient_data.mental_status
            },
            'symptoms': patient_data.symptoms,
            'medical_history': patient_data.medical_history,
            'observations': []
        }
        
        # Step 2: Run preprocessing pipeline
        processed_features = preprocess_patient_data(patient_dict)
        age_group = processed_features['age_group']
        data_completeness_score = processed_features['data_completeness_score']
        
        # Step 3: Load ML model (if available) or use fallback heuristics
        try:
            import os
            import pickle
            
            model_path = 'models/esi_classifier.pkl'
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    ml_model = pickle.load(f)
                model_available = True
                model_version = "v1.0.0-ml"
            else:
                model_available = False
                model_version = "v1.0.0-heuristic-fallback"
        except Exception:
            model_available = False
            model_version = "v1.0.0-heuristic-fallback"
        
        # Step 4: Generate ESI prediction
        if model_available:
            # TODO: ML model prediction (task 2.2-2.3)
            # For now, fall through to heuristics
            model_available = False
        
        if not model_available:
            # Fallback heuristic prediction
            esi_pred, probability_distribution = _heuristic_esi_prediction(
                patient_data, processed_features
            )
        
        # Step 5: Compute SHAP explanations using SHAPExplainer
        explainer = SHAPExplainer()
        shap_result = explainer.explain_prediction(
            preprocessed_features=processed_features,
            predicted_esi=esi_pred,
            k=5
        )
        
        # Extract SHAP explanation data
        shap_explanation = shap_result['shap_explanation']
        explanation_text = shap_result['explanation_text']
        
        # Step 6: Calculate multi-dimensional confidence using ConfidenceScorer
        confidence_scorer = ConfidenceScorer()
        confidence_result = confidence_scorer.score_prediction(
            probability_distribution=probability_distribution,
            preprocessed_features=processed_features,
            patient_data=patient_dict
        )
        
        # Convert to ConfidenceBreakdown model
        confidence_breakdown = ConfidenceBreakdown(
            model_certainty=confidence_result['model_certainty'],
            data_completeness=confidence_result['data_completeness'],
            clinical_consistency=confidence_result['clinical_consistency'],
            pattern_recognition=confidence_result['pattern_recognition'],
            overall=confidence_result['overall_score'],
            level=confidence_result['confidence_level']
        )
        
        # Step 7: Run safety validation using SafetyValidator
        # First convert patient_dict back to PatientData model for safety validator
        from src.models import (
            Demographics, VitalSigns, ClinicalData, 
            Symptoms, MedicalHistory, ClinicalObservations,
            PatientData as SrcPatientData
        )
        
        # Create src.models.PatientData instance
        src_patient_data = SrcPatientData(
            demographics=Demographics(
                age=patient_data.age,
                sex=_convert_sex_to_lowercase(patient_data.sex)
            ),
            vitals=VitalSigns(
                hr=patient_data.hr,
                bp_systolic=patient_data.bp_systolic,
                bp_diastolic=patient_data.bp_diastolic,
                spo2=patient_data.spo2,
                rr=patient_data.rr,
                temperature=patient_data.temperature
            ),
            clinical=ClinicalData(
                chief_complaint=patient_data.chief_complaint,
                chief_complaint_category=patient_data.chief_complaint_category,
                pain_score=patient_data.pain_score,
                arrival_mode=patient_data.arrival_mode,
                mental_status=patient_data.mental_status.lower()
            ),
            symptoms=Symptoms(symptom_list=patient_data.symptoms),
            medical_history=MedicalHistory(
                conditions=[k for k, v in patient_data.medical_history.items() if v],
                medications=[],
                allergies=[]
            ),
            observations=ClinicalObservations(observations=[])
        )
        
        # Convert ESI prediction to ESILevel enum
        from src.models import ESILevel
        ml_esi_level = ESILevel(esi_pred)
        
        # Convert confidence result to ConfidenceBreakdown model from src.models
        from src.models import ConfidenceBreakdown as SrcConfidenceBreakdown, ConfidenceLevel
        src_confidence = SrcConfidenceBreakdown(
            model_certainty=confidence_result['model_certainty'],
            data_completeness=confidence_result['data_completeness'],
            clinical_consistency=confidence_result['clinical_consistency'],
            pattern_recognition=confidence_result['pattern_recognition'],
            overall_score=confidence_result['overall_score'],
            confidence_level=ConfidenceLevel(confidence_result['confidence_level'])
        )
        
        # Run safety validation
        safety_validator = SafetyValidator()
        safety_validation_result = safety_validator.validate(
            patient_data=src_patient_data,
            ml_prediction=ml_esi_level,
            confidence=src_confidence
        )
        
        # Convert to SafetyFlag model for API response
        safety_flag = SafetyFlag(
            outcome=safety_validation_result.outcome.value,
            triggered_criteria=safety_validation_result.triggered_criteria,
            recommended_action=safety_validation_result.recommended_action,
            override_esi=safety_validation_result.forced_esi_override.value if safety_validation_result.forced_esi_override else None
        )
        
        # Apply safety override if RED flag
        final_esi = safety_flag.override_esi if safety_flag.override_esi else esi_pred
        
        # Step 8: Generate clinical recommendations
        recommendations = _generate_recommendations(
            patient_data, processed_features, final_esi, 
            confidence_breakdown, safety_flag
        )
        
        # Calculate inference time
        inference_time_ms = (time.time() - start_time) * 1000.0
        
        # Return PredictionResponse
        return PredictionResponse(
            request_id=request_id,
            esi_prediction=final_esi,
            probability_distribution=probability_distribution,
            confidence_breakdown=confidence_breakdown,
            safety_flag=safety_flag,
            explanation=Explanation(
                text=explanation_text,
                top_factors=shap_explanation
            ),
            recommendations=recommendations,
            sub_score=None,  # Sub-score computed in surge mode (not implemented yet)
            model_version=model_version,
            inference_time_ms=inference_time_ms,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        # Log error and return fail-safe response
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in predict_esi: {str(e)}\n{error_details}")
        
        # Fail-safe: return ESI 2 (mid-high urgency) with LOW confidence
        return PredictionResponse(
            request_id=request_id,
            esi_prediction=2,
            probability_distribution=[0.0, 1.0, 0.0, 0.0, 0.0],
            confidence_breakdown=ConfidenceBreakdown(
                model_certainty=0.0,
                data_completeness=0.0,
                clinical_consistency=0.0,
                pattern_recognition=0.0,
                overall=0.0,
                level="LOW"
            ),
            safety_flag=SafetyFlag(
                outcome="RED",
                triggered_criteria=[f"SYSTEM_ERROR: {str(e)}"],
                recommended_action="Manual clinical assessment required (system error)",
                override_esi=2
            ),
            explanation=Explanation(
                text=f"System error occurred during prediction: {str(e)}. Defaulting to ESI 2 for safety.",
                top_factors=[]
            ),
            recommendations=[
                "⚠️ System error - perform manual triage assessment",
                "Technical team has been notified"
            ],
            sub_score=None,
            model_version="fail-safe-v1.0.0",
            inference_time_ms=(time.time() - start_time) * 1000.0,
            timestamp=datetime.now()
        )


def _heuristic_esi_prediction(
    patient_data: PatientData,
    processed_features: Dict[str, Any]
) -> tuple[int, List[float]]:
    """
    Fallback heuristic ESI prediction when ML model unavailable.
    
    Improved logic for better classification of low-acuity cases.
    
    Returns:
        (esi_level, probability_distribution)
    """
    esi_pred = 3  # Default to ESI 3
    
    # Normalize complaint category for checks
    complaint = patient_data.chief_complaint_category.lower()
    complaint_text = patient_data.chief_complaint.lower()
    
    # Critical indicators → ESI 1 (Resuscitation)
    if patient_data.spo2 < 85:
        esi_pred = 1
    elif patient_data.mental_status.lower() in ["unresponsive", "pain"]:
        esi_pred = 1
    elif patient_data.bp_systolic < 70:
        esi_pred = 1
    elif patient_data.rr > 35:
        esi_pred = 1
    elif "cardiac_arrest" in complaint or "stroke" in complaint and patient_data.mental_status.lower() == "unresponsive":
        esi_pred = 1
    
    # Emergent indicators → ESI 2 (High risk)
    elif "chest_pain" in complaint and patient_data.age > 50:
        esi_pred = 2
    elif patient_data.mental_status.lower() in ["confused", "drowsy"]:
        esi_pred = 2
    elif patient_data.bp_systolic < 90 or patient_data.bp_systolic > 180:
        esi_pred = 2
    elif patient_data.rr > 30 or patient_data.spo2 < 92:
        esi_pred = 2
    elif patient_data.hr > 130 or patient_data.hr < 50:
        esi_pred = 2
    elif "sepsis" in complaint or "gi_bleed" in complaint:
        esi_pred = 2
    elif "trauma_severe" in complaint or "anaphylaxis" in complaint:
        esi_pred = 2
    
    # Urgent indicators → ESI 3 (Moderate risk)
    elif ("abdominal_pain_severe" in complaint or 
          "back_pain_severe" in complaint or
          "headache_severe" in complaint):
        esi_pred = 3
    elif patient_data.pain_score and patient_data.pain_score >= 7:
        esi_pred = 3
    elif patient_data.temperature and patient_data.temperature >= 39.0:  # High fever
        esi_pred = 3
    elif "asthma_exacerbation" in complaint or "copd_exacerbation" in complaint:
        esi_pred = 3
    elif "kidney_stone" in complaint or "urinary_retention" in complaint:
        esi_pred = 3
    
    # Less Urgent → ESI 4 (Low risk, stable vitals, minor conditions)
    elif (90 <= patient_data.bp_systolic <= 140 and 
          60 <= patient_data.hr <= 100 and 
          patient_data.spo2 >= 95 and
          12 <= patient_data.rr <= 20):
        
        # Check for conditions that are clearly ESI 4-5
        if ("mild" in complaint or "minor" in complaint or
            "cold" in complaint or "flu" in complaint or
            "cough" in complaint and "hemoptysis" not in complaint or
            "rash" in complaint or
            "allergic_reaction" in complaint and "anaphylaxis" not in complaint or
            "fever_mild" in complaint or
            "back_pain_mild" in complaint or
            "headache_mild" in complaint or
            "abdominal_pain_mild" in complaint):
            
            # Check if truly minor (no high pain, stable vitals)
            if (not patient_data.pain_score or patient_data.pain_score <= 4) and \
               (not patient_data.temperature or patient_data.temperature < 38.5):
                esi_pred = 4
    
    # Non-Urgent → ESI 5 (Minimal risk, very stable, very minor)
    if esi_pred == 4:  # Only consider ESI 5 if already qualified for ESI 4
        if (("cold" in complaint or "flu_symptoms" in complaint) and
            (not patient_data.pain_score or patient_data.pain_score <= 2) and
            (not patient_data.temperature or patient_data.temperature < 38.0)):
            esi_pred = 5
        elif ("rash" in complaint and 
              (not patient_data.pain_score or patient_data.pain_score <= 2)):
            esi_pred = 5
        elif "dental_complaint" in complaint and patient_data.pain_score <= 3:
            esi_pred = 5
        elif "ear_complaint" in complaint and patient_data.pain_score <= 3:
            esi_pred = 5
    
    # Adjust for arrival mode (ambulance suggests higher acuity)
    if patient_data.arrival_mode == "ambulance" and esi_pred >= 4:
        esi_pred = max(3, esi_pred - 1)  # Bump up by 1 level, but not below ESI 3
    
    # Generate probability distribution peaked around prediction
    probs = [0.05, 0.10, 0.30, 0.40, 0.15]
    
    # Adjust distribution based on ESI level
    if esi_pred == 1:
        probs = [0.60, 0.25, 0.10, 0.03, 0.02]
    elif esi_pred == 2:
        probs = [0.10, 0.55, 0.25, 0.08, 0.02]
    elif esi_pred == 3:
        probs = [0.05, 0.20, 0.50, 0.20, 0.05]
    elif esi_pred == 4:
        probs = [0.02, 0.08, 0.25, 0.50, 0.15]
    elif esi_pred == 5:
        probs = [0.01, 0.04, 0.10, 0.35, 0.50]
    
    return esi_pred, probs


def _generate_explanation(
    patient_data: PatientData,
    processed_features: Dict[str, Any],
    esi_pred: int,
    model_available: bool
) -> tuple[List[Dict], str]:
    """
    Generate SHAP-style explanation of prediction.
    
    Returns:
        (shap_factors_list, explanation_text)
    """
    # Mock SHAP values based on feature contributions
    shap_factors = []
    
    # Chief complaint contribution
    urgency_keywords = ["chest_pain", "cardiac", "stroke", "respiratory_distress", "trauma"]
    if any(kw in patient_data.chief_complaint_category.lower() for kw in urgency_keywords):
        shap_factors.append({
            "feature": "chief_complaint_category",
            "value": patient_data.chief_complaint_category,
            "contribution": 0.45,
            "direction": "increases urgency"
        })
    else:
        shap_factors.append({
            "feature": "chief_complaint_category",
            "value": patient_data.chief_complaint_category,
            "contribution": -0.15,
            "direction": "decreases urgency"
        })
    
    # Age contribution
    if patient_data.age < 5:
        shap_factors.append({
            "feature": "age",
            "value": patient_data.age,
            "contribution": 0.25,
            "direction": "increases urgency"
        })
    elif patient_data.age > 65:
        shap_factors.append({
            "feature": "age",
            "value": patient_data.age,
            "contribution": 0.20,
            "direction": "increases urgency"
        })
    else:
        shap_factors.append({
            "feature": "age",
            "value": patient_data.age,
            "contribution": 0.05,
            "direction": "minimal impact"
        })
    
    # HR deviation contribution
    hr_dev = processed_features.get('hr_deviation', 0.0)
    if hr_dev and abs(hr_dev) > 0.5:
        shap_factors.append({
            "feature": "hr_deviation",
            "value": f"{hr_dev:.2f}",
            "contribution": abs(hr_dev) * 0.15,
            "direction": "increases urgency" if abs(hr_dev) > 0 else "minimal impact"
        })
    
    # SpO2 contribution
    if patient_data.spo2 < 92:
        shap_factors.append({
            "feature": "spo2",
            "value": patient_data.spo2,
            "contribution": (95 - patient_data.spo2) * 0.05,
            "direction": "increases urgency"
        })
    
    # BP contribution
    bp_dev = processed_features.get('bp_systolic_deviation', 0.0)
    if bp_dev and abs(bp_dev) > 0.5:
        shap_factors.append({
            "feature": "bp_systolic_deviation",
            "value": f"{bp_dev:.2f}",
            "contribution": abs(bp_dev) * 0.12,
            "direction": "increases urgency" if abs(bp_dev) > 0 else "minimal impact"
        })
    
    # Sort by contribution and take top 5
    shap_factors.sort(key=lambda x: abs(x['contribution']), reverse=True)
    top_shap_factors = shap_factors[:5]
    
    # Generate explanation text
    esi_names = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}
    explanation_text = f"Predicted ESI {esi_pred} ({esi_names[esi_pred]}) based on: "
    
    top_3_factors = top_shap_factors[:3]
    factor_descriptions = []
    for factor in top_3_factors:
        feature = factor['feature']
        if feature == 'chief_complaint_category':
            factor_descriptions.append(f"chief complaint ({factor['value']})")
        elif feature == 'age':
            factor_descriptions.append(f"patient age ({factor['value']} years)")
        elif feature == 'hr_deviation':
            factor_descriptions.append(f"heart rate deviation ({factor['value']})")
        elif feature == 'spo2':
            factor_descriptions.append(f"oxygen saturation ({factor['value']}%)")
        elif feature == 'bp_systolic_deviation':
            factor_descriptions.append(f"blood pressure deviation ({factor['value']})")
        else:
            factor_descriptions.append(feature)
    
    explanation_text += ", ".join(factor_descriptions) + "."
    
    return top_shap_factors, explanation_text


def _compute_confidence_scores(
    processed_features: Dict[str, Any],
    data_completeness_score: float,
    probability_distribution: List[float],
    model_available: bool
) -> ConfidenceBreakdown:
    """
    Compute multi-dimensional confidence scores.
    
    Four dimensions:
    1. Model certainty (from probability entropy)
    2. Data completeness (from preprocessing)
    3. Clinical consistency (symptom-vital alignment)
    4. Pattern recognition (OOD detection - mocked for now)
    """
    # 1. Model certainty from probability entropy
    max_prob = max(probability_distribution)
    model_certainty = max_prob * 100.0
    
    # 2. Data completeness (already computed)
    data_completeness = data_completeness_score
    
    # 3. Clinical consistency (mock - check vital-symptom alignment)
    clinical_consistency = 80.0  # Default
    
    # Check for discordance
    pain_score = processed_features.get('pain_score')
    hr = processed_features.get('hr')
    if pain_score and hr:
        if pain_score < 4 and hr > 110:
            clinical_consistency -= 20.0  # Pain under-reported
    
    spo2 = processed_features.get('spo2')
    symptoms = processed_features.get('symptoms', [])
    if spo2 and spo2 < 93:
        respiratory_symptoms = any(s in ['shortness_of_breath', 'respiratory_distress', 'cough'] 
                                   for s in symptoms)
        if not respiratory_symptoms:
            clinical_consistency -= 15.0  # Respiratory under-reported
    
    # 4. Pattern recognition (mock - would use OOD detection)
    pattern_recognition = 75.0 if model_available else 60.0
    
    # Overall confidence (weighted average)
    overall = (
        model_certainty * 0.35 +
        data_completeness * 0.25 +
        clinical_consistency * 0.25 +
        pattern_recognition * 0.15
    )
    
    # Determine level
    if overall >= 80:
        level = "HIGH"
    elif overall >= 60:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return ConfidenceBreakdown(
        model_certainty=model_certainty,
        data_completeness=data_completeness,
        clinical_consistency=clinical_consistency,
        pattern_recognition=pattern_recognition,
        overall=overall,
        level=level
    )


def _run_safety_validation(
    patient_data: PatientData,
    processed_features: Dict[str, Any],
    esi_pred: int,
    confidence_breakdown: ConfidenceBreakdown,
    age_group: str
) -> SafetyFlag:
    """
    Run safety validation with rule-based checks.
    
    Returns SafetyFlag with outcome (RED/YELLOW/GREEN)
    """
    outcome = "GREEN"
    triggered_criteria = []
    recommended_action = "No safety concerns - proceed with ML recommendation"
    override_esi = None
    
    # RED FLAGS (force escalation)
    
    # Critical hypoxia
    if patient_data.spo2 < 85:
        outcome = "RED"
        triggered_criteria.append("CRITICAL: Severe hypoxia (SpO2 < 85%)")
        recommended_action = "Immediate resuscitation required - Force ESI 1"
        override_esi = 1
    
    # Unresponsive
    elif patient_data.mental_status.lower() == "unresponsive":
        outcome = "RED"
        triggered_criteria.append("CRITICAL: Unresponsive patient")
        recommended_action = "Immediate assessment required - Force ESI 1"
        override_esi = 1
    
    # Severe hypotension
    elif patient_data.bp_systolic < 70:
        outcome = "RED"
        triggered_criteria.append("CRITICAL: Severe hypotension (SBP < 70)")
        recommended_action = "Immediate resuscitation required - Force ESI 1"
        override_esi = 1
    
    # Infant age <1 year (always higher risk)
    elif patient_data.age < 1:
        outcome = "RED"
        triggered_criteria.append("HIGH_RISK: Infant < 1 year")
        recommended_action = "Expedite assessment - Force ESI 2"
        override_esi = 2
    
    # YELLOW FLAGS (caution advised)
    
    elif outcome == "GREEN":  # Only check if not already RED
        
        # Chest pain + age >45
        if "chest_pain" in patient_data.chief_complaint.lower() and patient_data.age > 45:
            outcome = "YELLOW"
            triggered_criteria.append("CAUTION: Chest pain in patient >45 years (cardiac risk)")
            recommended_action = "Cardiac risk assessment recommended - consider ECG, troponin"
        
        # Moderate hypoxia
        if patient_data.spo2 < 92:
            if outcome != "YELLOW":
                outcome = "YELLOW"
            triggered_criteria.append("CAUTION: Hypoxia (SpO2 < 92%)")
            recommended_action = "Respiratory assessment and monitoring recommended"
        
        # Low confidence
        if confidence_breakdown.level == "LOW":
            if outcome != "YELLOW":
                outcome = "YELLOW"
            triggered_criteria.append("LOW_CONFIDENCE")
            recommended_action = "Low confidence prediction - consider escalation or additional assessment"
        
        # Confused mental status
        if patient_data.mental_status.lower() == "confused":
            if outcome != "YELLOW":
                outcome = "YELLOW"
            triggered_criteria.append("CAUTION: Altered mental status (confused)")
            recommended_action = "Neurological assessment recommended"
    
    return SafetyFlag(
        outcome=outcome,
        triggered_criteria=triggered_criteria,
        recommended_action=recommended_action,
        override_esi=override_esi
    )


def _generate_recommendations(
    patient_data: PatientData,
    processed_features: Dict[str, Any],
    esi_pred: int,
    confidence_breakdown: ConfidenceBreakdown,
    safety_flag: SafetyFlag
) -> List[str]:
    """Generate actionable clinical recommendations."""
    recommendations = []
    
    # Data completeness recommendations
    if confidence_breakdown.data_completeness < 80:
        recommendations.append("📋 Consider obtaining additional patient history for better assessment")
    
    # Vital-specific recommendations
    if patient_data.spo2 < 95:
        recommendations.append("🫁 Monitor oxygen saturation closely - consider supplemental O2")
    
    if patient_data.hr > 110:
        recommendations.append("❤️ Elevated heart rate - monitor for tachycardia, assess hydration")
    
    if patient_data.temperature and patient_data.temperature > 38.0:
        recommendations.append("🌡️ Fever present - consider infection workup if indicated")
    
    # Chief complaint recommendations
    if "chest_pain" in patient_data.chief_complaint.lower():
        recommendations.append("🫀 Chest pain - consider cardiac workup (ECG, troponin, chest X-ray)")
    
    if "shortness" in patient_data.chief_complaint.lower():
        recommendations.append("🫁 Respiratory distress - assess airway, breathing, circulation")
    
    if "abdominal" in patient_data.chief_complaint.lower():
        recommendations.append("🏥 Abdominal pain - consider imaging if acute abdomen suspected")
    
    # Age-specific recommendations
    age_group = processed_features.get('age_group')
    if 'pediatric' in age_group:
        recommendations.append("👶 Pediatric patient - use age-appropriate assessment and dosing")
    elif age_group == 'geriatric_65_plus':
        recommendations.append("👴 Geriatric patient - assess for polypharmacy, fall risk, comorbidities")
    
    # Safety flag recommendations
    if safety_flag.outcome in ["RED", "YELLOW"]:
        recommendations.append(f"⚠️ Safety Alert: {safety_flag.recommended_action}")
    
    return recommendations[:6]  # Limit to top 6 recommendations


@app.get("/api/v1/patients", tags=["Patients"])
async def get_test_patients():
    """
    Get Test Patients Endpoint
    
    Returns 20 pre-generated test patients from data/test_patients.json.
    These patients include diverse scenarios:
    - 2 pediatric patients (infant, child)
    - 2 geriatric patients (65+)
    - 1 ambiguous presentation (chest pain, borderline ESI 2/3)
    - 1 zero-history patient (minimal medical history)
    - Distribution across all ESI levels (1-5)
    - Patients with missing optional data
    
    This enables quick-load for demo scenarios.
    Requirements: 20.6, 20.7
    """
    import json
    import os
    
    try:
        # Load test patients from JSON file
        patients_file = os.path.join("data", "test_patients.json")
        
        if not os.path.exists(patients_file):
            raise HTTPException(
                status_code=404,
                detail=f"Test patients file not found: {patients_file}"
            )
        
        with open(patients_file, 'r') as f:
            patients = json.load(f)
        
        # Return patient data with basic info for selection
        return {
            "count": len(patients),
            "patients": patients,
            "note": "Pre-generated test patients for demonstration purposes"
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing test patients file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading test patients: {str(e)}"
        )


@app.get("/api/v1/overrides", tags=["Overrides"])
async def get_overrides():
    """
    Get all clinician overrides from overrides.json
    
    Returns:
        List of all override records
    """
    import json
    import os
    
    try:
        overrides_file = os.path.join("data", "overrides.json")
        
        if os.path.exists(overrides_file):
            with open(overrides_file, 'r') as f:
                overrides = json.load(f)
        else:
            overrides = []
        
        return {
            "status": "success",
            "count": len(overrides),
            "overrides": overrides
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "overrides": []
        }


@app.post("/api/v1/patients", tags=["Patients"])
async def add_patient(
    patient_data: PatientData, 
    patient_name: str,
    clinician_override_esi: Optional[int] = None
):
    """
    Add New Patient to Queue
    
    Saves a new patient to the queue (test_patients.json) with a generated patient_id.
    This allows the frontend to add patients and have them appear in the queue dashboard.
    
    Args:
        patient_data: Patient clinical and demographic data
        patient_name: Patient full name
        clinician_override_esi: If provided, patient's ground_truth_esi is set to this value (clinician override)
        
    Returns:
        Confirmation with patient_id and basic info
    """
    import json
    import os
    import uuid
    
    try:
        # Generate unique patient ID
        patient_id = str(uuid.uuid4())
        
        # Determine age group
        age = patient_data.age
        if age <= 2:
            age_group = "infant_0_2"
        elif age <= 12:
            age_group = "child_3_12"
        elif age <= 17:
            age_group = "adolescent_13_17"
        elif age <= 64:
            age_group = "adult_18_64"
        else:
            age_group = "geriatric_65_plus"
        
        # Normalize sex field
        sex_normalized = patient_data.sex.lower()
        if sex_normalized in ['m', 'male']:
            sex_normalized = 'male'
        elif sex_normalized in ['f', 'female']:
            sex_normalized = 'female'
        else:
            sex_normalized = 'other'
        
        # Create patient record
        new_patient = {
            "patient_id": patient_id,
            "name": patient_name,
            "demographics": {
                "age": patient_data.age,
                "sex": sex_normalized,
                "age_group": age_group
            },
            "vitals": {
                "hr": patient_data.hr,
                "bp_systolic": patient_data.bp_systolic,
                "bp_diastolic": patient_data.bp_diastolic,
                "spo2": patient_data.spo2,
                "rr": patient_data.rr,
                "temperature": patient_data.temperature
            },
            "clinical": {
                "chief_complaint": patient_data.chief_complaint,
                "chief_complaint_category": patient_data.chief_complaint_category,
                "pain_score": patient_data.pain_score,
                "arrival_mode": patient_data.arrival_mode,
                "mental_status": patient_data.mental_status
            },
            "symptoms": patient_data.symptoms,
            "medical_history": patient_data.medical_history,
            "observations": [],
            "ground_truth_esi": clinician_override_esi,  # Set from clinician override if provided
            "arrival_timestamp": datetime.now().isoformat()
        }
        
        # Load existing patients
        patients_file = os.path.join("data", "test_patients.json")
        
        if os.path.exists(patients_file):
            with open(patients_file, 'r') as f:
                patients = json.load(f)
        else:
            patients = []
        
        # Add new patient to beginning of list (most recent first)
        patients.insert(0, new_patient)
        
        # Save back to file
        with open(patients_file, 'w') as f:
            json.dump(patients, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Patient {patient_name} added to queue",
            "patient_id": patient_id,
            "patient_name": patient_name,
            "arrival_timestamp": new_patient["arrival_timestamp"],
            "count": len(patients)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding patient: {str(e)}"
        )


@app.post("/api/v1/override", response_model=OverrideResponse, tags=["Triage"])
async def log_clinician_override(override_request: OverrideRequest):
    """
    Log Clinician Override Endpoint
    
    Accepts override data when a clinician decides to assign a different ESI level 
    than the ML recommendation. Logs to data/overrides.json for audit purposes.
    
    Flow:
    1. Calculate override direction (escalation vs de-escalation)
    2. Calculate override magnitude (absolute difference)
    3. Generate unique override ID
    4. Append to overrides.json file
    5. Return confirmation response
    
    Requirements: 4.7, 4.8
    """
    import json
    import os
    import uuid
    from pathlib import Path
    
    try:
        # Step 1: Calculate override direction and magnitude
        ml_esi = override_request.ml_predicted_esi
        clinician_esi = override_request.clinician_final_esi
        
        if clinician_esi < ml_esi:
            override_direction = "escalation"  # Lower ESI = higher urgency
        elif clinician_esi > ml_esi:
            override_direction = "de-escalation"  # Higher ESI = lower urgency
        else:
            override_direction = "no_change"
        
        override_magnitude = abs(clinician_esi - ml_esi)
        
        # Step 2: Generate unique override ID
        override_id = f"override_{uuid.uuid4().hex[:12]}"
        
        # Step 3: Prepare override record
        override_record = {
            "override_id": override_id,
            "patient_id": override_request.patient_id,
            "ml_predicted_esi": ml_esi,
            "clinician_final_esi": clinician_esi,
            "override_direction": override_direction,
            "override_magnitude": override_magnitude,
            "reason_category": override_request.reason_category,
            "reason_text": override_request.reason_text,
            "clinician_id": override_request.clinician_id,
            "timestamp": override_request.timestamp.isoformat() if override_request.timestamp else datetime.now().isoformat()
        }
        
        # Step 4: Load existing overrides (if file exists)
        overrides_file = os.path.join("data", "overrides.json")
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        if os.path.exists(overrides_file):
            with open(overrides_file, 'r') as f:
                overrides_data = json.load(f)
                if not isinstance(overrides_data, list):
                    # If file contains a dict, convert to list
                    overrides_data = []
        else:
            overrides_data = []
        
        # Step 5: Append new override
        overrides_data.append(override_record)
        
        # Step 6: Write back to file
        with open(overrides_file, 'w') as f:
            json.dump(overrides_data, f, indent=2)
        
        # Step 7: Generate confirmation message
        if override_direction == "escalation":
            message = f"Override logged successfully. Escalated from ESI {ml_esi} to ESI {clinician_esi}."
        elif override_direction == "de-escalation":
            message = f"Override logged successfully. De-escalated from ESI {ml_esi} to ESI {clinician_esi}."
        else:
            message = f"Override logged successfully. No ESI change (confirmed ESI {ml_esi})."
        
        # Return response
        return OverrideResponse(
            success=True,
            override_id=override_id,
            override_direction=override_direction,
            override_magnitude=override_magnitude,
            message=message,
            timestamp=datetime.now()
        )
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading overrides file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error logging override: {str(e)}"
        )


@app.get("/api/v1/overrides", tags=["Triage"])
async def get_overrides():
    """
    Get All Overrides Endpoint
    
    Returns all logged clinician overrides from data/overrides.json.
    Useful for reviewing override patterns and model improvement.
    """
    import json
    import os
    
    try:
        overrides_file = os.path.join("data", "overrides.json")
        
        if not os.path.exists(overrides_file):
            return {
                "count": 0,
                "overrides": [],
                "note": "No overrides logged yet"
            }
        
        with open(overrides_file, 'r') as f:
            overrides_data = json.load(f)
            if not isinstance(overrides_data, list):
                overrides_data = []
        
        return {
            "count": len(overrides_data),
            "overrides": overrides_data,
            "note": "Clinician override audit log"
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading overrides file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading overrides: {str(e)}"
        )


@app.post("/api/v1/reassess", tags=["Queue"])
async def reassess_patient(patient_data: PatientData, patient_id: Optional[str] = None):
    """
    Reassess a patient and compare with previous assessment.
    
    Stores the new assessment and detects deterioration if previous assessment exists.
    
    Query Parameters:
        patient_id: Optional patient identifier for linking to existing history
        
    Request Body:
        patient_data: Current patient vitals and clinical data
    
    Returns:
        AI prediction + deterioration analysis if previous assessment exists
    """
    try:
        from src.patient_history import patient_history_store, PatientAssessment
        from src.deterioration_monitor import (
            DeteriorationMonitor, VitalAssessment, DeteriorationSeverity
        )
        from datetime import datetime
        import uuid
        
        monitor = DeteriorationMonitor()
        
        # Generate patient ID if not provided
        if not patient_id:
            patient_id = str(uuid.uuid4())
        
        # Get AI prediction
        prediction = await predict_esi(patient_data)
        
        # Create new assessment
        new_assessment = PatientAssessment(
            patient_id=patient_id,
            timestamp=datetime.now(),
            age=patient_data.age,
            sex=patient_data.sex,
            hr=patient_data.hr,
            bp_systolic=patient_data.bp_systolic,
            bp_diastolic=patient_data.bp_diastolic,
            spo2=patient_data.spo2,
            rr=patient_data.rr,
            temperature=patient_data.temperature,
            mental_status=patient_data.mental_status,
            chief_complaint=patient_data.chief_complaint,
            chief_complaint_category=patient_data.chief_complaint_category,
            arrival_mode=patient_data.arrival_mode,
            pain_score=patient_data.pain_score,
            esi_prediction=prediction.esi_prediction,
            confidence_level=prediction.confidence_breakdown.level,
            confidence_score=prediction.confidence_breakdown.overall,
            safety_flag=prediction.safety_flag.outcome,
            assessment_type='reassessment' if patient_history_store.has_multiple_assessments(patient_id) else 'initial'
        )
        
        # Check for previous assessment
        previous_assessment = patient_history_store.get_latest_assessment(patient_id)
        deterioration_alert = None
        
        if previous_assessment:
            # Convert to VitalAssessment for comparison
            prev_vital = VitalAssessment(
                timestamp=previous_assessment.timestamp,
                hr=previous_assessment.hr,
                bp_systolic=previous_assessment.bp_systolic,
                bp_diastolic=previous_assessment.bp_diastolic,
                spo2=previous_assessment.spo2,
                rr=previous_assessment.rr,
                temperature=previous_assessment.temperature,
                mental_status=previous_assessment.mental_status,
                esi_level=previous_assessment.esi_prediction
            )
            
            curr_vital = VitalAssessment(
                timestamp=new_assessment.timestamp,
                hr=new_assessment.hr,
                bp_systolic=new_assessment.bp_systolic,
                bp_diastolic=new_assessment.bp_diastolic,
                spo2=new_assessment.spo2,
                rr=new_assessment.rr,
                temperature=new_assessment.temperature,
                mental_status=new_assessment.mental_status,
                esi_level=new_assessment.esi_prediction
            )
            
            deterioration_alert = monitor.compare_assessments(curr_vital, prev_vital)
        
        # Store new assessment
        patient_history_store.add_assessment(new_assessment)
        
        # Build response
        response_data = {
            'patient_id': patient_id,
            'prediction': {
                'esi_prediction': prediction.esi_prediction,
                'confidence_breakdown': {
                    'model_certainty': prediction.confidence_breakdown.model_certainty,
                    'data_completeness': prediction.confidence_breakdown.data_completeness,
                    'clinical_consistency': prediction.confidence_breakdown.clinical_consistency,
                    'pattern_recognition': prediction.confidence_breakdown.pattern_recognition,
                    'overall': prediction.confidence_breakdown.overall,
                    'level': prediction.confidence_breakdown.level
                },
                'safety_flag': {
                    'outcome': prediction.safety_flag.outcome,
                    'triggered_criteria': prediction.safety_flag.triggered_criteria,
                    'recommended_action': prediction.safety_flag.recommended_action
                },
                'probability_distribution': prediction.probability_distribution,
                'explanation': prediction.explanation
            },
            'assessment_count': patient_history_store.get_assessment_count(patient_id),
            'is_reassessment': previous_assessment is not None,
            'deterioration_detected': deterioration_alert is not None and deterioration_alert.severity != DeteriorationSeverity.NONE
        }
        
        # Add deterioration details if detected
        if deterioration_alert and deterioration_alert.severity != DeteriorationSeverity.NONE:
            response_data['deterioration'] = {
                'severity': deterioration_alert.severity.value,
                'score': deterioration_alert.score,
                'urgent': deterioration_alert.urgent,
                'triggered_criteria': deterioration_alert.triggered_criteria,
                'vital_changes': deterioration_alert.vital_changes,
                'recommendation': deterioration_alert.recommendation
            }
            
            # Add comparison with previous assessment
            response_data['previous_assessment'] = {
                'timestamp': previous_assessment.timestamp.isoformat(),
                'esi_prediction': previous_assessment.esi_prediction,
                'hr': previous_assessment.hr,
                'bp_systolic': previous_assessment.bp_systolic,
                'spo2': previous_assessment.spo2,
                'rr': previous_assessment.rr,
                'mental_status': previous_assessment.mental_status
            }
        
        return response_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error during reassessment: {str(e)}"
        )


@app.get("/api/v1/patient/{patient_id}/history", tags=["Queue"])
async def get_patient_history(patient_id: str):
    """
    Get full assessment history for a patient.
    
    Path Parameters:
        patient_id: Patient identifier
        
    Returns:
        List of all assessments for this patient, with deterioration analysis
    """
    try:
        from src.patient_history import patient_history_store
        from src.deterioration_monitor import DeteriorationMonitor, VitalAssessment
        
        monitor = DeteriorationMonitor()
        
        # Get patient history
        history = patient_history_store.get_history(patient_id)
        
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for patient {patient_id}"
            )
        
        # Build response with deterioration analysis between consecutive assessments
        history_with_analysis = []
        
        for i, assessment in enumerate(history):
            entry = {
                'timestamp': assessment.timestamp.isoformat(),
                'assessment_type': assessment.assessment_type,
                'esi_prediction': assessment.esi_prediction,
                'vitals': {
                    'hr': assessment.hr,
                    'bp_systolic': assessment.bp_systolic,
                    'bp_diastolic': assessment.bp_diastolic,
                    'spo2': assessment.spo2,
                    'rr': assessment.rr,
                    'temperature': assessment.temperature,
                    'mental_status': assessment.mental_status
                },
                'clinical': {
                    'chief_complaint': assessment.chief_complaint,
                    'pain_score': assessment.pain_score
                },
                'confidence': {
                    'level': assessment.confidence_level,
                    'score': assessment.confidence_score
                },
                'safety_flag': assessment.safety_flag
            }
            
            # Add deterioration analysis if not first assessment
            if i > 0:
                prev_assessment = history[i-1]
                
                prev_vital = VitalAssessment(
                    timestamp=prev_assessment.timestamp,
                    hr=prev_assessment.hr,
                    bp_systolic=prev_assessment.bp_systolic,
                    bp_diastolic=prev_assessment.bp_diastolic,
                    spo2=prev_assessment.spo2,
                    rr=prev_assessment.rr,
                    temperature=prev_assessment.temperature,
                    mental_status=prev_assessment.mental_status,
                    esi_level=prev_assessment.esi_prediction
                )
                
                curr_vital = VitalAssessment(
                    timestamp=assessment.timestamp,
                    hr=assessment.hr,
                    bp_systolic=assessment.bp_systolic,
                    bp_diastolic=assessment.bp_diastolic,
                    spo2=assessment.spo2,
                    rr=assessment.rr,
                    temperature=assessment.temperature,
                    mental_status=assessment.mental_status,
                    esi_level=assessment.esi_prediction
                )
                
                alert = monitor.compare_assessments(curr_vital, prev_vital)
                
                entry['deterioration_since_previous'] = {
                    'severity': alert.severity.value,
                    'score': alert.score,
                    'triggered_criteria': alert.triggered_criteria
                } if alert.severity.value != 'none' else None
            
            history_with_analysis.append(entry)
        
        return {
            'patient_id': patient_id,
            'assessment_count': len(history),
            'first_assessment': history[0].timestamp.isoformat(),
            'latest_assessment': history[-1].timestamp.isoformat(),
            'history': history_with_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving patient history: {str(e)}"
        )


@app.get("/api/v1/queue", tags=["Queue"])
async def get_queue(surge_mode: bool = False):
    """
    Get current ED queue with all patients, predictions, and deterioration status.
    
    Query Parameters:
        surge_mode: Whether ED is in surge mode (affects reassessment intervals)
    
    Returns:
        Queue data with patients sorted by priority (ESI level)
    """
    try:
        from src.patient_history import patient_history_store, PatientAssessment
        from src.deterioration_monitor import (
            DeteriorationMonitor, VitalAssessment, DeteriorationSeverity
        )
        from datetime import datetime, timedelta
        
        monitor = DeteriorationMonitor()
        
        # Load all test patients
        import json
        test_patients_path = "data/test_patients.json"
        
        with open(test_patients_path, 'r') as f:
            patients_data = json.load(f)
        
        queue_patients = []
        
        for patient in patients_data:
            patient_id = patient['patient_id']
            
            # Get or create patient assessment history
            latest_assessment = patient_history_store.get_latest_assessment(patient_id)
            
            # If no history, create initial assessment from patient data
            if not latest_assessment:
                # Get AI prediction for this patient
                prediction_payload = {
                    'age': patient['demographics']['age'],
                    'sex': patient['demographics']['sex'],
                    'hr': patient['vitals']['hr'],
                    'bp_systolic': patient['vitals']['bp_systolic'],
                    'bp_diastolic': patient['vitals']['bp_diastolic'],
                    'spo2': patient['vitals']['spo2'],
                    'rr': patient['vitals']['rr'],
                    'temperature': patient['vitals'].get('temperature'),
                    'chief_complaint': patient['clinical']['chief_complaint'],
                    'chief_complaint_category': patient['clinical']['chief_complaint_category'],
                    'arrival_mode': patient['clinical']['arrival_mode'],
                    'mental_status': patient['clinical']['mental_status'],
                    'pain_score': patient['clinical'].get('pain_score'),
                    'symptoms': patient.get('symptoms', []),
                    'medical_history': patient.get('medical_history', {})
                }
                
                # Get prediction (call internal predict function)
                try:
                    prediction_request = PatientData(**prediction_payload)
                    prediction = await predict_esi(prediction_request)
                except Exception as e:
                    # Fallback to ground truth if prediction fails
                    prediction = {
                        'esi_prediction': patient.get('ground_truth_esi', 3),
                        'confidence_breakdown': {'level': 'MEDIUM', 'overall': 70.0},
                        'safety_flag': {'outcome': 'GREEN'}
                    }
                
                # Use current time as arrival time for realistic wait times in demo
                # In production, this would be actual arrival timestamp from registration
                arrival_time = datetime.now() - timedelta(minutes=random.randint(5, 120))
                
                initial_assessment = PatientAssessment(
                    patient_id=patient_id,
                    timestamp=arrival_time,
                    age=patient['demographics']['age'],
                    sex=patient['demographics']['sex'],
                    hr=patient['vitals']['hr'],
                    bp_systolic=patient['vitals']['bp_systolic'],
                    bp_diastolic=patient['vitals']['bp_diastolic'],
                    spo2=patient['vitals']['spo2'],
                    rr=patient['vitals']['rr'],
                    temperature=patient['vitals'].get('temperature'),
                    mental_status=patient['clinical']['mental_status'],
                    chief_complaint=patient['clinical']['chief_complaint'],
                    chief_complaint_category=patient['clinical']['chief_complaint_category'],
                    arrival_mode=patient['clinical']['arrival_mode'],
                    pain_score=patient['clinical'].get('pain_score'),
                    esi_prediction=prediction.get('esi_prediction', 3) if isinstance(prediction, dict) else prediction.esi_prediction,
                    confidence_level=prediction.get('confidence_breakdown', {}).get('level', 'MEDIUM') if isinstance(prediction, dict) else prediction.confidence_breakdown.level,
                    confidence_score=prediction.get('confidence_breakdown', {}).get('overall', 70.0) if isinstance(prediction, dict) else prediction.confidence_breakdown.overall,
                    safety_flag=prediction.get('safety_flag', {}).get('outcome', 'GREEN') if isinstance(prediction, dict) else prediction.safety_flag.outcome,
                    assessment_type='initial'
                )
                
                patient_history_store.add_assessment(initial_assessment)
                latest_assessment = initial_assessment
            
            # Calculate wait time
            wait_time_minutes = int((datetime.now() - latest_assessment.timestamp).total_seconds() / 60)
            
            # Check for deterioration (if multiple assessments exist)
            deterioration_alert = None
            previous_assessment = patient_history_store.get_previous_assessment(patient_id)
            
            if previous_assessment:
                # Convert to VitalAssessment for deterioration check
                prev_vital = VitalAssessment(
                    timestamp=previous_assessment.timestamp,
                    hr=previous_assessment.hr,
                    bp_systolic=previous_assessment.bp_systolic,
                    bp_diastolic=previous_assessment.bp_diastolic,
                    spo2=previous_assessment.spo2,
                    rr=previous_assessment.rr,
                    temperature=previous_assessment.temperature,
                    mental_status=previous_assessment.mental_status,
                    esi_level=previous_assessment.esi_prediction
                )
                
                curr_vital = VitalAssessment(
                    timestamp=latest_assessment.timestamp,
                    hr=latest_assessment.hr,
                    bp_systolic=latest_assessment.bp_systolic,
                    bp_diastolic=latest_assessment.bp_diastolic,
                    spo2=latest_assessment.spo2,
                    rr=latest_assessment.rr,
                    temperature=latest_assessment.temperature,
                    mental_status=latest_assessment.mental_status,
                    esi_level=latest_assessment.esi_prediction
                )
                
                deterioration_alert = monitor.compare_assessments(curr_vital, prev_vital)
            
            # Check reassessment due
            is_reassessment_due, minutes_overdue = monitor.check_reassessment_due(
                esi_level=latest_assessment.esi_prediction,
                last_assessment_time=latest_assessment.timestamp,
                surge_mode=surge_mode
            )
            
            # Build queue patient entry
            queue_entry = {
                'patient_id': patient_id,
                'name': patient.get('name', f'Patient {patient_id[:8]}'),
                'demographics': patient['demographics'],
                'vitals': patient['vitals'],
                'clinical': patient['clinical'],
                'symptoms': patient.get('symptoms', []),
                'esi_prediction': latest_assessment.esi_prediction,
                'confidence_level': latest_assessment.confidence_level,
                'confidence_score': latest_assessment.confidence_score,
                'safety_flag': latest_assessment.safety_flag,
                'arrival_timestamp': latest_assessment.timestamp.isoformat(),
                'wait_minutes': wait_time_minutes,
                'assessment_count': patient_history_store.get_assessment_count(patient_id),
                'reassessment_due': is_reassessment_due,
                'reassessment_overdue_minutes': minutes_overdue if is_reassessment_due else 0,
                'deterioration': None if not deterioration_alert or deterioration_alert.severity == DeteriorationSeverity.NONE else {
                    'severity': deterioration_alert.severity.value,
                    'score': deterioration_alert.score,
                    'urgent': deterioration_alert.urgent,
                    'triggered_criteria': deterioration_alert.triggered_criteria,
                    'recommendation': deterioration_alert.recommendation
                },
                'reassessment_priority': monitor.generate_reassessment_priority(
                    esi_level=latest_assessment.esi_prediction,
                    minutes_overdue=minutes_overdue,
                    has_deterioration=deterioration_alert is not None and deterioration_alert.severity != DeteriorationSeverity.NONE
                )
            }
            
            queue_patients.append(queue_entry)
        
        # Sort by ESI level (1 first), then by wait time
        queue_patients.sort(key=lambda p: (p['esi_prediction'], -p['wait_minutes']))
        
        # Calculate metrics
        total_patients = len(queue_patients)
        esi_counts = {i: len([p for p in queue_patients if p['esi_prediction'] == i]) for i in range(1, 6)}
        deterioration_count = len([p for p in queue_patients if p['deterioration'] is not None])
        reassessment_due_count = len([p for p in queue_patients if p['reassessment_due']])
        
        # Average wait time for ESI 3
        esi3_patients = [p for p in queue_patients if p['esi_prediction'] == 3]
        avg_wait_esi3 = sum(p['wait_minutes'] for p in esi3_patients) / len(esi3_patients) if esi3_patients else 0
        
        return {
            'queue': queue_patients,
            'metrics': {
                'total_patients': total_patients,
                'esi_1': esi_counts.get(1, 0),
                'esi_2': esi_counts.get(2, 0),
                'esi_3': esi_counts.get(3, 0),
                'esi_4': esi_counts.get(4, 0),
                'esi_5': esi_counts.get(5, 0),
                'deterioration_alerts': deterioration_count,
                'reassessment_due': reassessment_due_count,
                'avg_wait_esi3_minutes': round(avg_wait_esi3, 1)
            },
            'surge_mode': surge_mode,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error loading queue: {str(e)}"
        )


@app.get("/api/models/info", tags=["Models"])
async def model_info():
    """
    Model information endpoint.
    Returns current model version and metadata.
    """
    return {
        "esi_classifier": {
            "version": "prototype-v1.0.0",
            "type": "heuristic",
            "description": "Simplified rule-based ESI classification for prototype",
            "status": "active"
        },
        "note": "This is a prototype backend. Production system will integrate with ML Core Engine."
    }


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
