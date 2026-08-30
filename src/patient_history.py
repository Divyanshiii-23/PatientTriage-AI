"""
Patient History Storage and Management

In-memory storage for patient assessments and history tracking.
In production, this would use a proper database (PostgreSQL, MongoDB, etc.)

Features:
- Store patient assessments with timestamps
- Retrieve patient history
- Track reassessment intervals
- Support for multiple assessments per patient
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class PatientAssessment:
    """Single patient assessment record"""
    patient_id: str
    timestamp: datetime
    
    # Demographics
    age: int
    sex: str
    
    # Vitals
    hr: int
    bp_systolic: int
    bp_diastolic: int
    spo2: int
    rr: int
    temperature: Optional[float]
    mental_status: str
    
    # Clinical
    chief_complaint: str
    chief_complaint_category: str
    arrival_mode: str
    pain_score: Optional[int]
    
    # AI Prediction
    esi_prediction: int
    confidence_level: str
    confidence_score: float
    safety_flag: str
    
    # Assessment metadata
    assessed_by: Optional[str] = None
    assessment_type: str = "initial"  # initial, reassessment, deterioration_check
    
    def to_dict(self) -> dict:
        """Convert to dictionary with datetime serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class PatientHistoryStore:
    """
    In-memory storage for patient assessment history.
    Thread-safe for prototype; would use Redis/DB in production.
    """
    
    def __init__(self):
        """Initialize empty history store"""
        # patient_id -> list of assessments
        self._history: Dict[str, List[PatientAssessment]] = {}
        
        # patient_id -> current queue position info
        self._queue_info: Dict[str, dict] = {}
    
    def add_assessment(self, assessment: PatientAssessment) -> None:
        """
        Add a new assessment for a patient.
        
        Args:
            assessment: PatientAssessment to store
        """
        patient_id = assessment.patient_id
        
        if patient_id not in self._history:
            self._history[patient_id] = []
        
        self._history[patient_id].append(assessment)
        
        # Keep only last 10 assessments per patient (memory management)
        if len(self._history[patient_id]) > 10:
            self._history[patient_id] = self._history[patient_id][-10:]
    
    def get_history(self, patient_id: str) -> List[PatientAssessment]:
        """
        Get all assessments for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            List of assessments, oldest first
        """
        return self._history.get(patient_id, [])
    
    def get_latest_assessment(self, patient_id: str) -> Optional[PatientAssessment]:
        """
        Get most recent assessment for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest assessment or None if no history
        """
        history = self.get_history(patient_id)
        return history[-1] if history else None
    
    def get_previous_assessment(self, patient_id: str) -> Optional[PatientAssessment]:
        """
        Get second-most recent assessment (for comparison).
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Previous assessment or None if less than 2 assessments
        """
        history = self.get_history(patient_id)
        return history[-2] if len(history) >= 2 else None
    
    def has_multiple_assessments(self, patient_id: str) -> bool:
        """Check if patient has been assessed multiple times"""
        return len(self.get_history(patient_id)) >= 2
    
    def get_assessment_count(self, patient_id: str) -> int:
        """Get total number of assessments for a patient"""
        return len(self.get_history(patient_id))
    
    def get_time_since_last_assessment(self, patient_id: str) -> Optional[float]:
        """
        Get minutes since last assessment.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Minutes since last assessment, or None if no history
        """
        latest = self.get_latest_assessment(patient_id)
        if not latest:
            return None
        
        time_diff = datetime.now() - latest.timestamp
        return time_diff.total_seconds() / 60
    
    def update_queue_info(self, patient_id: str, info: dict) -> None:
        """
        Update queue position information for a patient.
        
        Args:
            patient_id: Patient identifier
            info: Dictionary with queue info (arrival_time, wait_minutes, etc.)
        """
        self._queue_info[patient_id] = info
    
    def get_queue_info(self, patient_id: str) -> Optional[dict]:
        """Get queue information for a patient"""
        return self._queue_info.get(patient_id)
    
    def remove_from_queue(self, patient_id: str) -> None:
        """Remove patient from queue (discharged, admitted, etc.)"""
        if patient_id in self._queue_info:
            del self._queue_info[patient_id]
    
    def get_all_in_queue(self) -> List[str]:
        """Get list of all patient IDs currently in queue"""
        return list(self._queue_info.keys())
    
    def clear_old_history(self, days: int = 7) -> int:
        """
        Clear assessment history older than specified days.
        
        Args:
            days: Number of days to retain
            
        Returns:
            Number of patient records cleared
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleared = 0
        
        for patient_id in list(self._history.keys()):
            # Remove old assessments
            self._history[patient_id] = [
                a for a in self._history[patient_id]
                if a.timestamp > cutoff
            ]
            
            # If no assessments left, remove patient
            if not self._history[patient_id]:
                del self._history[patient_id]
                cleared += 1
        
        return cleared
    
    def export_history(self, patient_id: str) -> str:
        """
        Export patient history as JSON string (for audit/compliance).
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            JSON string of patient history
        """
        history = self.get_history(patient_id)
        history_dicts = [a.to_dict() for a in history]
        return json.dumps(history_dicts, indent=2)
    
    def get_statistics(self) -> dict:
        """Get overall statistics about stored history"""
        total_patients = len(self._history)
        total_assessments = sum(len(h) for h in self._history.values())
        patients_in_queue = len(self._queue_info)
        
        return {
            'total_patients': total_patients,
            'total_assessments': total_assessments,
            'average_assessments_per_patient': total_assessments / total_patients if total_patients > 0 else 0,
            'patients_in_queue': patients_in_queue
        }


# Global instance for prototype (would be database connection in production)
patient_history_store = PatientHistoryStore()


# Example usage
if __name__ == "__main__":
    from datetime import timedelta
    
    store = PatientHistoryStore()
    
    # Add initial assessment
    assessment1 = PatientAssessment(
        patient_id="P001",
        timestamp=datetime.now() - timedelta(minutes=45),
        age=45,
        sex="M",
        hr=85,
        bp_systolic=120,
        bp_diastolic=80,
        spo2=98,
        rr=16,
        temperature=37.0,
        mental_status="alert",
        chief_complaint="Chest pain",
        chief_complaint_category="chest_pain_cardiac",
        arrival_mode="ambulance",
        pain_score=6,
        esi_prediction=3,
        confidence_level="HIGH",
        confidence_score=85.0,
        safety_flag="GREEN",
        assessment_type="initial"
    )
    
    store.add_assessment(assessment1)
    
    # Add reassessment
    assessment2 = PatientAssessment(
        patient_id="P001",
        timestamp=datetime.now(),
        age=45,
        sex="M",
        hr=105,  # Increased
        bp_systolic=110,  # Slightly decreased
        bp_diastolic=75,
        spo2=96,  # Slightly decreased
        rr=18,  # Increased
        temperature=37.2,
        mental_status="alert",
        chief_complaint="Chest pain",
        chief_complaint_category="chest_pain_cardiac",
        arrival_mode="ambulance",
        pain_score=7,  # Increased
        esi_prediction=2,  # Escalated
        confidence_level="HIGH",
        confidence_score=88.0,
        safety_flag="YELLOW",
        assessment_type="reassessment"
    )
    
    store.add_assessment(assessment2)
    
    # Test retrieval
    print("=== Patient History Store Test ===")
    print(f"Total assessments for P001: {store.get_assessment_count('P001')}")
    print(f"Has multiple assessments: {store.has_multiple_assessments('P001')}")
    print(f"Time since last assessment: {store.get_time_since_last_assessment('P001'):.1f} minutes")
    
    latest = store.get_latest_assessment('P001')
    print(f"\nLatest assessment:")
    print(f"  ESI: {latest.esi_prediction}")
    print(f"  HR: {latest.hr} bpm")
    print(f"  Confidence: {latest.confidence_level}")
    
    previous = store.get_previous_assessment('P001')
    print(f"\nPrevious assessment:")
    print(f"  ESI: {previous.esi_prediction}")
    print(f"  HR: {previous.hr} bpm")
    
    print(f"\nVital changes:")
    print(f"  HR: {previous.hr} → {latest.hr} ({latest.hr - previous.hr:+d})")
    print(f"  ESI: {previous.esi_prediction} → {latest.esi_prediction}")
    
    # Statistics
    stats = store.get_statistics()
    print(f"\nStore statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
