"""
Deterioration Detection and Monitoring Module

Tracks patient vitals over time and detects clinical deterioration.
Compares current assessment with previous assessments to identify worsening trends.

Key Features:
- Vital sign comparison (HR, BP, SpO2, RR, mental status)
- Deterioration scoring based on clinical significance
- Reassessment interval tracking based on ESI level
- Alert generation for critical changes
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class DeteriorationSeverity(Enum):
    """Severity levels for detected deterioration"""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass
class VitalAssessment:
    """Single vital signs assessment snapshot"""
    timestamp: datetime
    hr: int
    bp_systolic: int
    bp_diastolic: int
    spo2: int
    rr: int
    temperature: Optional[float]
    mental_status: str
    esi_level: int


@dataclass
class DeteriorationAlert:
    """Alert generated when deterioration is detected"""
    severity: DeteriorationSeverity
    score: float  # 0-100, higher = more concerning
    triggered_criteria: List[str]
    vital_changes: Dict[str, Dict[str, float]]  # vital -> {previous, current, change}
    recommendation: str
    urgent: bool  # Requires immediate intervention


class DeteriorationMonitor:
    """
    Monitors patient vitals over time and detects deterioration.
    
    Uses Modified Early Warning Score (MEWS) principles adapted for ED triage.
    """
    
    # Critical change thresholds (absolute changes that trigger alerts)
    CRITICAL_THRESHOLDS = {
        'hr_increase': 40,  # HR increase > 40 bpm
        'hr_decrease': 30,  # HR decrease > 30 bpm (bradycardia)
        'bp_systolic_drop': 30,  # Systolic BP drop > 30 mmHg
        'bp_systolic_increase': 60,  # Systolic BP increase > 60 mmHg
        'spo2_drop': 5,  # SpO2 drop > 5%
        'rr_increase': 10,  # RR increase > 10 /min
        'rr_decrease': 8,  # RR decrease > 8 /min (hypoventilation)
        'temp_increase': 1.5,  # Temperature increase > 1.5°C
    }
    
    # Reassessment intervals by ESI level (minutes)
    REASSESSMENT_INTERVALS = {
        1: 0,    # Continuous monitoring
        2: 15,   # Every 15 minutes
        3: 30,   # Every 30 minutes
        4: 60,   # Every 60 minutes
        5: 120,  # Every 2 hours
    }
    
    def __init__(self):
        """Initialize deterioration monitor"""
        pass
    
    def compare_assessments(
        self,
        current: VitalAssessment,
        previous: VitalAssessment
    ) -> DeteriorationAlert:
        """
        Compare two vital assessments and detect deterioration.
        
        Args:
            current: Most recent vital signs assessment
            previous: Previous vital signs assessment for comparison
            
        Returns:
            DeteriorationAlert with severity, score, and triggered criteria
        """
        score = 0.0
        triggered_criteria = []
        vital_changes = {}
        
        # 1. Heart Rate Analysis
        hr_change = current.hr - previous.hr
        vital_changes['hr'] = {
            'previous': previous.hr,
            'current': current.hr,
            'change': hr_change
        }
        
        if hr_change > self.CRITICAL_THRESHOLDS['hr_increase']:
            score += 30
            triggered_criteria.append(
                f"Severe tachycardia: HR increased from {previous.hr} to {current.hr} bpm (+{hr_change})"
            )
        elif hr_change > 20:
            score += 15
            triggered_criteria.append(
                f"Moderate tachycardia: HR increased from {previous.hr} to {current.hr} bpm (+{hr_change})"
            )
        elif hr_change < -self.CRITICAL_THRESHOLDS['hr_decrease']:
            score += 25
            triggered_criteria.append(
                f"Severe bradycardia: HR decreased from {previous.hr} to {current.hr} bpm ({hr_change})"
            )
        
        # 2. Blood Pressure Analysis
        bp_sys_change = current.bp_systolic - previous.bp_systolic
        vital_changes['bp_systolic'] = {
            'previous': previous.bp_systolic,
            'current': current.bp_systolic,
            'change': bp_sys_change
        }
        
        if bp_sys_change < -self.CRITICAL_THRESHOLDS['bp_systolic_drop']:
            score += 35
            triggered_criteria.append(
                f"Critical BP drop: Systolic BP decreased from {previous.bp_systolic} to {current.bp_systolic} mmHg ({bp_sys_change})"
            )
        elif bp_sys_change < -20:
            score += 20
            triggered_criteria.append(
                f"Moderate BP drop: Systolic BP decreased from {previous.bp_systolic} to {current.bp_systolic} mmHg ({bp_sys_change})"
            )
        elif bp_sys_change > self.CRITICAL_THRESHOLDS['bp_systolic_increase']:
            score += 20
            triggered_criteria.append(
                f"Severe hypertension: Systolic BP increased from {previous.bp_systolic} to {current.bp_systolic} mmHg (+{bp_sys_change})"
            )
        
        # 3. Oxygen Saturation Analysis
        spo2_change = current.spo2 - previous.spo2
        vital_changes['spo2'] = {
            'previous': previous.spo2,
            'current': current.spo2,
            'change': spo2_change
        }
        
        if spo2_change < -self.CRITICAL_THRESHOLDS['spo2_drop']:
            score += 40
            triggered_criteria.append(
                f"Critical hypoxia: SpO2 dropped from {previous.spo2}% to {current.spo2}% ({spo2_change}%)"
            )
        elif spo2_change < -3:
            score += 20
            triggered_criteria.append(
                f"Moderate hypoxia: SpO2 dropped from {previous.spo2}% to {current.spo2}% ({spo2_change}%)"
            )
        
        # 4. Respiratory Rate Analysis
        rr_change = current.rr - previous.rr
        vital_changes['rr'] = {
            'previous': previous.rr,
            'current': current.rr,
            'change': rr_change
        }
        
        if rr_change > self.CRITICAL_THRESHOLDS['rr_increase']:
            score += 25
            triggered_criteria.append(
                f"Severe tachypnea: RR increased from {previous.rr} to {current.rr} /min (+{rr_change})"
            )
        elif rr_change > 6:
            score += 15
            triggered_criteria.append(
                f"Moderate tachypnea: RR increased from {previous.rr} to {current.rr} /min (+{rr_change})"
            )
        elif rr_change < -self.CRITICAL_THRESHOLDS['rr_decrease']:
            score += 30
            triggered_criteria.append(
                f"Severe hypoventilation: RR decreased from {previous.rr} to {current.rr} /min ({rr_change})"
            )
        
        # 5. Mental Status Analysis
        mental_status_scores = {
            'alert': 0,
            'confused': 1,
            'verbal': 2,
            'pain': 3,
            'unresponsive': 4
        }
        
        prev_mental_score = mental_status_scores.get(previous.mental_status.lower(), 0)
        curr_mental_score = mental_status_scores.get(current.mental_status.lower(), 0)
        
        vital_changes['mental_status'] = {
            'previous': previous.mental_status,
            'current': current.mental_status,
            'change': curr_mental_score - prev_mental_score
        }
        
        if curr_mental_score > prev_mental_score:
            mental_decline = curr_mental_score - prev_mental_score
            if mental_decline >= 2:
                score += 50
                triggered_criteria.append(
                    f"Critical mental status decline: Changed from {previous.mental_status} to {current.mental_status}"
                )
            else:
                score += 25
                triggered_criteria.append(
                    f"Mental status decline: Changed from {previous.mental_status} to {current.mental_status}"
                )
        
        # 6. Temperature Analysis (if available)
        if current.temperature is not None and previous.temperature is not None:
            temp_change = current.temperature - previous.temperature
            vital_changes['temperature'] = {
                'previous': previous.temperature,
                'current': current.temperature,
                'change': temp_change
            }
            
            if temp_change > self.CRITICAL_THRESHOLDS['temp_increase']:
                score += 15
                triggered_criteria.append(
                    f"Rapid temperature increase: {previous.temperature}°C to {current.temperature}°C (+{temp_change:.1f}°C)"
                )
        
        # 7. ESI Level Change
        if current.esi_level < previous.esi_level:
            esi_change = previous.esi_level - current.esi_level
            score += esi_change * 10
            triggered_criteria.append(
                f"Acuity escalation: ESI changed from {previous.esi_level} to {current.esi_level}"
            )
        
        # Determine severity
        severity = self._calculate_severity(score)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(severity, triggered_criteria)
        
        # Determine if urgent
        urgent = severity in [DeteriorationSeverity.SEVERE, DeteriorationSeverity.CRITICAL]
        
        return DeteriorationAlert(
            severity=severity,
            score=score,
            triggered_criteria=triggered_criteria,
            vital_changes=vital_changes,
            recommendation=recommendation,
            urgent=urgent
        )
    
    def _calculate_severity(self, score: float) -> DeteriorationSeverity:
        """Calculate deterioration severity based on score"""
        if score >= 80:
            return DeteriorationSeverity.CRITICAL
        elif score >= 50:
            return DeteriorationSeverity.SEVERE
        elif score >= 30:
            return DeteriorationSeverity.MODERATE
        elif score >= 10:
            return DeteriorationSeverity.MILD
        else:
            return DeteriorationSeverity.NONE
    
    def _generate_recommendation(
        self,
        severity: DeteriorationSeverity,
        criteria: List[str]
    ) -> str:
        """Generate clinical recommendation based on severity"""
        if severity == DeteriorationSeverity.CRITICAL:
            return "IMMEDIATE PHYSICIAN EVALUATION REQUIRED. Consider ICU consultation and escalate ESI level."
        elif severity == DeteriorationSeverity.SEVERE:
            return "URGENT reassessment required within 15 minutes. Notify physician immediately."
        elif severity == DeteriorationSeverity.MODERATE:
            return "Reassess within 30 minutes. Monitor closely and consider physician notification."
        elif severity == DeteriorationSeverity.MILD:
            return "Continue monitoring. Reassess per standard ESI interval."
        else:
            return "No significant deterioration detected. Continue routine monitoring."
    
    def check_reassessment_due(
        self,
        esi_level: int,
        last_assessment_time: datetime,
        surge_mode: bool = False
    ) -> Tuple[bool, int]:
        """
        Check if patient reassessment is overdue.
        
        Args:
            esi_level: Current ESI level (1-5)
            last_assessment_time: Timestamp of last assessment
            surge_mode: Whether ED is in surge mode (reduces intervals)
            
        Returns:
            Tuple of (is_due: bool, minutes_overdue: int)
        """
        interval_minutes = self.REASSESSMENT_INTERVALS.get(esi_level, 30)
        
        # In surge mode, reduce intervals by 33%
        if surge_mode:
            interval_minutes = max(int(interval_minutes * 0.67), 5)
        
        time_since_assessment = datetime.now() - last_assessment_time
        minutes_since = time_since_assessment.total_seconds() / 60
        
        is_due = minutes_since >= interval_minutes
        minutes_overdue = max(0, int(minutes_since - interval_minutes))
        
        return is_due, minutes_overdue
    
    def generate_reassessment_priority(
        self,
        esi_level: int,
        minutes_overdue: int,
        has_deterioration: bool
    ) -> int:
        """
        Generate priority score for reassessment queue.
        Higher score = higher priority.
        
        Args:
            esi_level: Current ESI level (1-5)
            minutes_overdue: How many minutes past due interval
            has_deterioration: Whether deterioration has been detected
            
        Returns:
            Priority score (0-100)
        """
        # Base priority from ESI (lower ESI = higher priority)
        base_priority = (6 - esi_level) * 15  # ESI 1 = 75, ESI 5 = 15
        
        # Add priority for being overdue (max +20)
        overdue_priority = min(minutes_overdue / 3, 20)
        
        # Critical boost for deterioration
        deterioration_boost = 50 if has_deterioration else 0
        
        total_priority = min(100, base_priority + overdue_priority + deterioration_boost)
        
        return int(total_priority)


# Example usage and testing
if __name__ == "__main__":
    # Create monitor
    monitor = DeteriorationMonitor()
    
    # Simulate two assessments
    previous = VitalAssessment(
        timestamp=datetime.now() - timedelta(minutes=30),
        hr=85,
        bp_systolic=120,
        bp_diastolic=80,
        spo2=98,
        rr=16,
        temperature=37.0,
        mental_status='alert',
        esi_level=3
    )
    
    current = VitalAssessment(
        timestamp=datetime.now(),
        hr=125,  # Significant increase
        bp_systolic=95,  # Significant drop
        bp_diastolic=60,
        spo2=92,  # Drop
        rr=24,  # Increase
        temperature=37.5,
        mental_status='confused',  # Decline
        esi_level=2  # Escalated
    )
    
    # Detect deterioration
    alert = monitor.compare_assessments(current, previous)
    
    print("=== Deterioration Detection Example ===")
    print(f"Severity: {alert.severity.value.upper()}")
    print(f"Score: {alert.score:.1f}/100")
    print(f"Urgent: {alert.urgent}")
    print(f"\nTriggered Criteria ({len(alert.triggered_criteria)}):")
    for criterion in alert.triggered_criteria:
        print(f"  • {criterion}")
    print(f"\nRecommendation: {alert.recommendation}")
    
    # Check reassessment
    is_due, overdue = monitor.check_reassessment_due(
        esi_level=3,
        last_assessment_time=datetime.now() - timedelta(minutes=35),
        surge_mode=False
    )
    
    print(f"\n=== Reassessment Check ===")
    print(f"Reassessment due: {is_due}")
    print(f"Minutes overdue: {overdue}")
    
    # Priority score
    priority = monitor.generate_reassessment_priority(
        esi_level=2,
        minutes_overdue=10,
        has_deterioration=True
    )
    print(f"Reassessment priority: {priority}/100")
