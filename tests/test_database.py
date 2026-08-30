"""
Tests for database schema and models.

Task 1.3: Set up PostgreSQL schema for audit logging and override tracking
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Prediction, Override, DeteriorationAlert


# Use in-memory SQLite for testing (not PostgreSQL)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


class TestDatabaseSchema:
    """Test database schema creation and structure."""
    
    def test_predictions_table_exists(self, db_engine):
        """Test that predictions table is created."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'predictions' in tables
    
    def test_overrides_table_exists(self, db_engine):
        """Test that overrides table is created."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'overrides' in tables
    
    def test_deterioration_alerts_table_exists(self, db_engine):
        """Test that deterioration_alerts table is created."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        assert 'deterioration_alerts' in tables
    
    def test_predictions_columns(self, db_engine):
        """Test that predictions table has all required columns."""
        inspector = inspect(db_engine)
        columns = inspector.get_columns('predictions')
        column_names = [col['name'] for col in columns]
        
        required_columns = [
            'id', 'request_id', 'timestamp', 'model_version',
            'patient_features', 'esi_prediction', 'probability_distribution',
            'confidence_breakdown', 'safety_outcome', 'explanation',
            'sub_score', 'inference_time_ms'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Column '{col}' missing from predictions table"
    
    def test_overrides_columns(self, db_engine):
        """Test that overrides table has all required columns."""
        inspector = inspect(db_engine)
        columns = inspector.get_columns('overrides')
        column_names = [col['name'] for col in columns]
        
        required_columns = [
            'id', 'prediction_id', 'timestamp', 'ml_predicted_esi',
            'ml_confidence', 'clinician_final_esi', 'override_direction',
            'override_magnitude', 'override_reason_category',
            'override_reason_text', 'clinician_id', 'patient_outcome',
            'outcome_updated_at'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Column '{col}' missing from overrides table"
    
    def test_deterioration_alerts_columns(self, db_engine):
        """Test that deterioration_alerts table has all required columns."""
        inspector = inspect(db_engine)
        columns = inspector.get_columns('deterioration_alerts')
        column_names = [col['name'] for col in columns]
        
        required_columns = [
            'id', 'patient_id', 'timestamp', 'deterioration_status',
            'deterioration_score', 'vital_changes', 'initial_esi',
            'time_since_triage_minutes', 'alert_reason', 'model_version'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Column '{col}' missing from deterioration_alerts table"


class TestPredictionModel:
    """Test Prediction model CRUD operations."""
    
    def test_create_prediction(self, db_session):
        """Test creating a prediction record."""
        prediction = Prediction(
            request_id="req_test_123",
            timestamp=datetime.utcnow(),
            model_version="v2.1.0_test",
            patient_features={"age": 68, "hr": 118, "spo2": 92},
            esi_prediction=2,
            probability_distribution=[0.05, 0.72, 0.18, 0.04, 0.01],
            confidence_breakdown={"overall": 81.7, "level": "HIGH"},
            safety_outcome="YELLOW",
            explanation={"text": "ESI 2 based on chest pain", "top_factors": []},
            sub_score=68.5,
            inference_time_ms=92.7
        )
        
        db_session.add(prediction)
        db_session.commit()
        
        # Query back
        retrieved = db_session.query(Prediction).filter_by(request_id="req_test_123").first()
        assert retrieved is not None
        assert retrieved.esi_prediction == 2
        assert retrieved.safety_outcome == "YELLOW"
        assert retrieved.model_version == "v2.1.0_test"
    
    def test_prediction_unique_request_id(self, db_session):
        """Test that request_id must be unique."""
        prediction1 = Prediction(
            request_id="req_duplicate",
            model_version="v2.1.0",
            patient_features={},
            esi_prediction=2,
            probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
            confidence_breakdown={},
            safety_outcome="GREEN",
            explanation={},
            inference_time_ms=50.0
        )
        
        db_session.add(prediction1)
        db_session.commit()
        
        # Try to add another with same request_id
        prediction2 = Prediction(
            request_id="req_duplicate",  # Same ID
            model_version="v2.1.0",
            patient_features={},
            esi_prediction=3,
            probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
            confidence_breakdown={},
            safety_outcome="GREEN",
            explanation={},
            inference_time_ms=50.0
        )
        
        db_session.add(prediction2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()
    
    def test_prediction_jsonb_fields(self, db_session):
        """Test that JSONB fields store complex data."""
        complex_features = {
            "demographics": {"age": 68, "sex": "female"},
            "vitals": {"hr": 118, "bp_systolic": 145, "spo2": 92},
            "symptoms": ["chest_pain", "shortness_of_breath"]
        }
        
        prediction = Prediction(
            request_id="req_jsonb_test",
            model_version="v2.1.0",
            patient_features=complex_features,
            esi_prediction=2,
            probability_distribution=[0.05, 0.72, 0.18, 0.04, 0.01],
            confidence_breakdown={"model_certainty": 92.3, "overall": 81.7},
            safety_outcome="YELLOW",
            explanation={"text": "Test", "top_factors": [{"feature": "HR", "contribution": 0.73}]},
            inference_time_ms=92.7
        )
        
        db_session.add(prediction)
        db_session.commit()
        
        # Query and verify complex data
        retrieved = db_session.query(Prediction).filter_by(request_id="req_jsonb_test").first()
        assert retrieved.patient_features["demographics"]["age"] == 68
        assert retrieved.confidence_breakdown["model_certainty"] == 92.3
        assert len(retrieved.explanation["top_factors"]) == 1


class TestOverrideModel:
    """Test Override model CRUD operations."""
    
    def test_create_override(self, db_session):
        """Test creating an override record linked to a prediction."""
        # First create a prediction
        prediction = Prediction(
            request_id="req_override_test",
            model_version="v2.1.0",
            patient_features={"age": 68},
            esi_prediction=3,
            probability_distribution=[0.1, 0.2, 0.4, 0.2, 0.1],
            confidence_breakdown={"overall": 65.0},
            safety_outcome="GREEN",
            explanation={"text": "ESI 3"},
            inference_time_ms=85.0
        )
        
        db_session.add(prediction)
        db_session.commit()
        
        # Create override
        override = Override(
            prediction_id=prediction.id,
            timestamp=datetime.utcnow(),
            ml_predicted_esi=3,
            ml_confidence={"overall": 65.0},
            clinician_final_esi=2,
            override_direction="escalation",
            override_magnitude=1,
            override_reason_category="clinical_judgment",
            override_reason_text="Patient appears more distressed than vitals suggest",
            clinician_id="clinician_001"
        )
        
        db_session.add(override)
        db_session.commit()
        
        # Query back
        retrieved = db_session.query(Override).filter_by(prediction_id=prediction.id).first()
        assert retrieved is not None
        assert retrieved.ml_predicted_esi == 3
        assert retrieved.clinician_final_esi == 2
        assert retrieved.override_direction == "escalation"
        assert retrieved.override_magnitude == 1
    
    def test_override_relationship(self, db_session):
        """Test relationship between Override and Prediction."""
        # Create prediction
        prediction = Prediction(
            request_id="req_relationship_test",
            model_version="v2.1.0",
            patient_features={},
            esi_prediction=3,
            probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
            confidence_breakdown={},
            safety_outcome="GREEN",
            explanation={},
            inference_time_ms=50.0
        )
        
        db_session.add(prediction)
        db_session.commit()
        
        # Create multiple overrides for same prediction
        for i in range(2):
            override = Override(
                prediction_id=prediction.id,
                ml_predicted_esi=3,
                ml_confidence={},
                clinician_final_esi=2,
                override_direction="escalation",
                override_magnitude=1,
                override_reason_category="clinical_judgment",
                clinician_id=f"clinician_{i}"
            )
            db_session.add(override)
        
        db_session.commit()
        
        # Query prediction and access overrides through relationship
        retrieved_prediction = db_session.query(Prediction).filter_by(request_id="req_relationship_test").first()
        assert len(retrieved_prediction.overrides) == 2


class TestDeteriorationAlertModel:
    """Test DeteriorationAlert model CRUD operations."""
    
    def test_create_deterioration_alert(self, db_session):
        """Test creating a deterioration alert."""
        alert = DeteriorationAlert(
            patient_id="patient_hashed_123",
            timestamp=datetime.utcnow(),
            deterioration_status="DETERIORATING",
            deterioration_score=73.5,
            vital_changes={
                "hr": {"initial": 88, "current": 118, "delta": 30},
                "spo2": {"initial": 96, "current": 91, "delta": -5}
            },
            initial_esi=3,
            time_since_triage_minutes=35,
            alert_reason="vital_deterioration",
            model_version="v2.1.0_deterioration"
        )
        
        db_session.add(alert)
        db_session.commit()
        
        # Query back
        retrieved = db_session.query(DeteriorationAlert).filter_by(patient_id="patient_hashed_123").first()
        assert retrieved is not None
        assert retrieved.deterioration_status == "DETERIORATING"
        assert retrieved.deterioration_score == 73.5
        assert retrieved.vital_changes["hr"]["delta"] == 30
    
    def test_deterioration_alert_patient_history(self, db_session):
        """Test querying deterioration history for a patient."""
        patient_id = "patient_history_test"
        
        # Create multiple alerts over time
        for i in range(3):
            alert = DeteriorationAlert(
                patient_id=patient_id,
                timestamp=datetime.utcnow() - timedelta(minutes=i*15),
                deterioration_status="DETERIORATING" if i == 2 else "STABLE",
                deterioration_score=50.0 + (i * 10),
                vital_changes={},
                initial_esi=3,
                time_since_triage_minutes=15 * i,
                alert_reason="routine_check",
                model_version="v2.1.0"
            )
            db_session.add(alert)
        
        db_session.commit()
        
        # Query patient history
        history = db_session.query(DeteriorationAlert).filter_by(
            patient_id=patient_id
        ).order_by(DeteriorationAlert.timestamp.desc()).all()
        
        assert len(history) == 3
        assert history[0].time_since_triage_minutes == 0  # Most recent
        assert history[-1].time_since_triage_minutes == 30  # Oldest


class TestQueryPerformance:
    """Test common query patterns for performance validation."""
    
    def test_query_predictions_by_timestamp(self, db_session):
        """Test querying predictions by timestamp range."""
        # Create predictions over different times
        for i in range(5):
            prediction = Prediction(
                request_id=f"req_time_test_{i}",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                model_version="v2.1.0",
                patient_features={},
                esi_prediction=2,
                probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
                confidence_breakdown={},
                safety_outcome="GREEN",
                explanation={},
                inference_time_ms=50.0
            )
            db_session.add(prediction)
        
        db_session.commit()
        
        # Query last 2 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        recent = db_session.query(Prediction).filter(
            Prediction.timestamp >= cutoff_time
        ).all()
        
        assert len(recent) == 3  # 0, 1, 2 hours ago
    
    def test_query_predictions_by_esi(self, db_session):
        """Test querying predictions by ESI level."""
        # Create predictions with different ESI levels
        for esi in range(1, 6):
            prediction = Prediction(
                request_id=f"req_esi_test_{esi}",
                model_version="v2.1.0",
                patient_features={},
                esi_prediction=esi,
                probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
                confidence_breakdown={},
                safety_outcome="GREEN",
                explanation={},
                inference_time_ms=50.0
            )
            db_session.add(prediction)
        
        db_session.commit()
        
        # Query ESI 1 and 2 (critical cases)
        critical = db_session.query(Prediction).filter(
            Prediction.esi_prediction <= 2
        ).all()
        
        assert len(critical) == 2
    
    def test_query_overrides_by_category(self, db_session):
        """Test querying overrides by reason category."""
        # Create prediction
        prediction = Prediction(
            request_id="req_category_test",
            model_version="v2.1.0",
            patient_features={},
            esi_prediction=3,
            probability_distribution=[0.2, 0.2, 0.2, 0.2, 0.2],
            confidence_breakdown={},
            safety_outcome="GREEN",
            explanation={},
            inference_time_ms=50.0
        )
        db_session.add(prediction)
        db_session.commit()
        
        # Create overrides with different categories
        categories = ["clinical_judgment", "additional_information", "safety_concern"]
        for cat in categories:
            override = Override(
                prediction_id=prediction.id,
                ml_predicted_esi=3,
                ml_confidence={},
                clinician_final_esi=2,
                override_direction="escalation",
                override_magnitude=1,
                override_reason_category=cat,
                clinician_id="clinician_001"
            )
            db_session.add(override)
        
        db_session.commit()
        
        # Query by category
        safety_overrides = db_session.query(Override).filter_by(
            override_reason_category="safety_concern"
        ).all()
        
        assert len(safety_overrides) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
