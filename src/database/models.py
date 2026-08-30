"""
SQLAlchemy ORM models for audit logging and override tracking.

Models:
- Prediction: ESI predictions with full audit trail
- Override: Clinician overrides with reasoning and outcomes
- DeteriorationAlert: Patient deterioration alerts during wait time

Requirements: 7.1, 15.1, 15.2, 15.3, 15.4, 16.2
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey,
    Index, CheckConstraint, ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB as PostgresJSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.compiler import compiles
import uuid

Base = declarative_base()

# Create a universal JSON type that works with both SQLite and PostgreSQL
class UniversalJSON(JSON):
    """JSON type that uses JSONB on PostgreSQL and JSON on other databases."""
    pass

@compiles(UniversalJSON, 'postgresql')
def compile_jsonb_postgresql(element, compiler, **kw):
    """Use JSONB for PostgreSQL."""
    return 'JSONB'

@compiles(UniversalJSON)
def compile_json_default(element, compiler, **kw):
    """Use JSON for other databases."""
    return compiler.visit_JSON(element, **kw)


class Prediction(Base):
    """
    Audit log for all ESI predictions.
    
    Stores complete prediction context including input features, model outputs,
    confidence scores, safety validation, and explanations.
    
    Retention: 7 years for HIPAA compliance
    Encryption: Row-level encryption enabled for PHI
    """
    __tablename__ = 'predictions'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request tracking
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Model information
    model_version = Column(String(50), nullable=False, index=True)
    
    # Input features (UniversalJSON for flexibility, becomes JSONB on PostgreSQL)
    patient_features = Column(UniversalJSON, nullable=False, comment='Complete patient data as JSON')
    
    # Prediction outputs
    esi_prediction = Column(
        Integer, 
        nullable=False, 
        index=True,
        comment='Predicted ESI level (1-5)'
    )
    probability_distribution = Column(
        ARRAY(Float), 
        nullable=False,
        comment='Probability distribution [p1, p2, p3, p4, p5]'
    )
    confidence_breakdown = Column(
        UniversalJSON, 
        nullable=False,
        comment='Multi-dimensional confidence scores'
    )
    safety_outcome = Column(
        String(10), 
        nullable=False, 
        index=True,
        comment='Safety validation outcome: RED, YELLOW, or GREEN'
    )
    
    # Explainability
    explanation = Column(
        UniversalJSON, 
        nullable=False,
        comment='SHAP-based explanation with top contributing factors'
    )
    
    # Sub-prioritization (surge mode)
    sub_score = Column(
        Float,
        nullable=True,
        comment='Sub-prioritization score for surge mode (0-100)'
    )
    
    # Performance metrics
    inference_time_ms = Column(
        Float, 
        nullable=False,
        comment='Total inference time in milliseconds'
    )
    
    # Relationships
    overrides = relationship('Override', back_populates='prediction', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('esi_prediction >= 1 AND esi_prediction <= 5', name='esi_range_check'),
        CheckConstraint('safety_outcome IN (\'RED\', \'YELLOW\', \'GREEN\')', name='safety_outcome_check'),
        CheckConstraint('inference_time_ms >= 0', name='inference_time_positive'),
        CheckConstraint('sub_score IS NULL OR (sub_score >= 0 AND sub_score <= 100)', name='sub_score_range'),
        Index('idx_predictions_timestamp', 'timestamp'),
        Index('idx_predictions_model_version', 'model_version'),
        Index('idx_predictions_esi', 'esi_prediction'),
        Index('idx_predictions_safety', 'safety_outcome'),
        Index('idx_predictions_timestamp_esi', 'timestamp', 'esi_prediction'),  # Composite for common queries
    )
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, request_id={self.request_id}, esi={self.esi_prediction})>"


class Override(Base):
    """
    Clinician overrides of ML predictions with reasoning and outcomes.
    
    Captures when clinicians disagree with ML recommendations, enabling
    pattern analysis and continuous learning.
    
    Requirements: 7.1, 7.2
    """
    __tablename__ = 'overrides'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to prediction
    prediction_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('predictions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Override details
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    ml_predicted_esi = Column(
        Integer, 
        nullable=False,
        comment='ESI level predicted by ML model'
    )
    ml_confidence = Column(
        UniversalJSON,
        nullable=False,
        comment='ML confidence breakdown at time of override'
    )
    
    clinician_final_esi = Column(
        Integer, 
        nullable=False,
        comment='Final ESI level assigned by clinician'
    )
    
    override_direction = Column(
        String(20),
        nullable=False,
        comment='escalation or de-escalation'
    )
    override_magnitude = Column(
        Integer,
        nullable=False,
        comment='Absolute difference between ML and clinician ESI'
    )
    
    # Reasoning
    override_reason_category = Column(
        String(50), 
        nullable=False,
        index=True,
        comment='Predefined category: clinical_judgment, additional_information, safety_concern, ml_error, patient_preference, resource_constraint'
    )
    override_reason_text = Column(
        Text,
        nullable=True,
        comment='Free-text explanation from clinician'
    )
    
    # Clinician tracking
    clinician_id = Column(
        String(255), 
        nullable=False,
        index=True,
        comment='Identifier for clinician who made override'
    )
    
    # Patient outcome (populated later)
    patient_outcome = Column(
        UniversalJSON,
        nullable=True,
        comment='Eventual patient outcome: disposition, adverse_events, time_to_treatment'
    )
    outcome_updated_at = Column(
        DateTime,
        nullable=True,
        comment='Timestamp when outcome data was added'
    )
    
    # Relationships
    prediction = relationship('Prediction', back_populates='overrides')
    
    # Constraints
    __table_args__ = (
        CheckConstraint('ml_predicted_esi >= 1 AND ml_predicted_esi <= 5', name='ml_esi_range'),
        CheckConstraint('clinician_final_esi >= 1 AND clinician_final_esi <= 5', name='clinician_esi_range'),
        CheckConstraint('override_direction IN (\'escalation\', \'de-escalation\')', name='override_direction_check'),
        CheckConstraint('override_magnitude >= 0', name='override_magnitude_positive'),
        Index('idx_overrides_timestamp', 'timestamp'),
        Index('idx_overrides_prediction', 'prediction_id'),
        Index('idx_overrides_clinician', 'clinician_id'),
        Index('idx_overrides_category', 'override_reason_category'),
        Index('idx_overrides_timestamp_category', 'timestamp', 'override_reason_category'),  # For pattern analysis
    )
    
    def __repr__(self):
        return f"<Override(id={self.id}, ml_esi={self.ml_predicted_esi}, clinician_esi={self.clinician_final_esi})>"


class DeteriorationAlert(Base):
    """
    Alerts for patient deterioration during ED wait time.
    
    Tracks vital sign changes and triggers re-assessment when patients
    show signs of clinical decline.
    
    Requirements: 4.6, 4.7, 4.8, 4.9, 4.10, 15.3
    """
    __tablename__ = 'deterioration_alerts'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Patient tracking
    patient_id = Column(
        String(255), 
        nullable=False,
        index=True,
        comment='Hashed patient identifier'
    )
    
    # Alert details
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    deterioration_status = Column(
        String(20),
        nullable=False,
        index=True,
        comment='STABLE, DETERIORATING, or UNCERTAIN'
    )
    deterioration_score = Column(
        Float,
        nullable=False,
        comment='Deterioration probability score (0-100)'
    )
    
    # Vital changes
    vital_changes = Column(
        UniversalJSON,
        nullable=False,
        comment='Temporal vital sign changes with deltas, rates, trends'
    )
    
    # Context
    initial_esi = Column(
        Integer,
        nullable=False,
        comment='ESI level at initial triage'
    )
    time_since_triage_minutes = Column(
        Integer,
        nullable=False,
        comment='Minutes elapsed since initial triage'
    )
    
    alert_reason = Column(
        String(100),
        nullable=False,
        comment='Reason for alert: vital_deterioration, wait_time_exceeded, or multiple_vitals_worsening'
    )
    
    # Model information
    model_version = Column(
        String(50),
        nullable=False,
        comment='Deterioration detector model version'
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint('deterioration_status IN (\'STABLE\', \'DETERIORATING\', \'UNCERTAIN\')', name='deterioration_status_check'),
        CheckConstraint('deterioration_score >= 0 AND deterioration_score <= 100', name='deterioration_score_range'),
        CheckConstraint('initial_esi >= 1 AND initial_esi <= 5', name='initial_esi_range'),
        CheckConstraint('time_since_triage_minutes >= 0', name='time_since_triage_positive'),
        Index('idx_deterioration_timestamp', 'timestamp'),
        Index('idx_deterioration_patient', 'patient_id'),
        Index('idx_deterioration_status', 'deterioration_status'),
        Index('idx_deterioration_patient_timestamp', 'patient_id', 'timestamp'),  # For patient history
    )
    
    def __repr__(self):
        return f"<DeteriorationAlert(id={self.id}, patient={self.patient_id}, status={self.deterioration_status})>"
