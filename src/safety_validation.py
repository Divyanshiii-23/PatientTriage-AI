"""
Safety Validation Layer - Rule-based checks for critical conditions.

This module implements the safety validation layer that runs after ML prediction
to catch life-threatening conditions. It enforces safety criteria and can override
ML predictions when critical conditions are detected.

Task: 2.5 - Implement safety validation layer with rule-based checks
Requirements: 3.5, 3.6, 3.7, 13.1-13.3
"""

from typing import Dict, List, Optional, Tuple
from src.models import (
    PatientData,
    SafetyValidation,
    SafetyOutcome,
    ESILevel,
    ConfidenceBreakdown,
    AgeGroup
)
from src.preprocessing import classify_age_group


class SafetyValidator:
    """
    Rule-based safety validation layer for critical condition detection.
    
    Runs after ML prediction to enforce safety criteria that can override
    the ML recommendation when life-threatening conditions are detected.
    
    Safety Rules Implemented:
    1. Age <1 year (infant) → RED flag, force ESI 2
    2. SpO2 <90% → RED flag, force ESI 1
    3. Chest pain + age >45 → YELLOW flag (cardiac risk)
    4. Severe trauma → RED flag, force ESI 1
    
    Additional safety checks:
    5. Severe hypotension (SBP <90) → RED flag, force ESI 1
    6. Altered mental status → RED flag, force ESI 2
    7. Severe tachycardia (HR >140 adult) → YELLOW flag
    8. LOW confidence + ESI ≥3 → YELLOW flag, recommend escalation
    """
    
    def __init__(self):
        """Initialize safety validator with critical thresholds."""
        # Critical thresholds
        self.CRITICAL_SPO2_THRESHOLD = 90  # SpO2 < 90% = RED
        self.CRITICAL_SBP_THRESHOLD = 90   # SBP < 90 = RED (hypotension)
        self.CARDIAC_RISK_AGE = 45         # Age > 45 with chest pain = YELLOW
        self.INFANT_AGE_THRESHOLD = 1      # Age < 1 year = RED
        self.SEVERE_TACHYCARDIA_ADULT = 140  # HR > 140 in adults = YELLOW
        
        # Chest pain related keywords
        self.CHEST_PAIN_KEYWORDS = [
            'chest pain', 'chest_pain', 'cardiac', 'chest discomfort',
            'chest pressure', 'angina', 'myocardial', 'heart attack'
        ]
        
        # Trauma related keywords
        self.TRAUMA_KEYWORDS = [
            'trauma', 'severe trauma', 'trauma_severe', 'major trauma',
            'polytrauma', 'gsw', 'gunshot', 'stabbing', 'blunt trauma'
        ]
        
        # Altered mental status indicators
        self.ALTERED_MENTAL_STATUS = [
            'unresponsive', 'confused', 'drowsy', 'unconscious',
            'obtunded', 'lethargic', 'somnolent'
        ]
    
    def validate(
        self,
        patient_data: PatientData,
        ml_prediction: ESILevel,
        confidence: ConfidenceBreakdown
    ) -> SafetyValidation:
        """
        Perform comprehensive safety validation.
        
        Args:
            patient_data: Complete patient data
            ml_prediction: ML predicted ESI level
            confidence: Multi-dimensional confidence breakdown
            
        Returns:
            SafetyValidation with outcome, triggered criteria, and recommendations
        """
        triggered_criteria: List[str] = []
        safety_outcome = SafetyOutcome.GREEN
        forced_esi: Optional[ESILevel] = None
        recommended_action = "No immediate safety concerns detected - proceed with ML recommendation"
        
        # Extract patient information
        age = patient_data.demographics.age
        age_group = classify_age_group(age)
        vitals = patient_data.vitals
        clinical = patient_data.clinical
        
        # Rule 1: Infant age check (age < 1 year)
        if age < self.INFANT_AGE_THRESHOLD:
            triggered_criteria.append(
                f"CRITICAL: Infant patient (age {age} months) - heightened risk"
            )
            safety_outcome = SafetyOutcome.RED
            forced_esi = ESILevel.EMERGENT  # Force ESI 2
            recommended_action = "Infant patient requires immediate assessment - Force ESI 2"
        
        # Rule 2: Critical hypoxia (SpO2 < 90%)
        if vitals.spo2 is not None and vitals.spo2 < self.CRITICAL_SPO2_THRESHOLD:
            triggered_criteria.append(
                f"CRITICAL: Severe hypoxia detected (SpO2 {vitals.spo2}% < 90%)"
            )
            safety_outcome = SafetyOutcome.RED
            forced_esi = ESILevel.RESUSCITATION  # Force ESI 1
            recommended_action = "Immediate resuscitation required - Force ESI 1"
        
        # Rule 3: Severe hypotension (SBP < 90 mmHg)
        if vitals.bp_systolic is not None and vitals.bp_systolic < self.CRITICAL_SBP_THRESHOLD:
            triggered_criteria.append(
                f"CRITICAL: Severe hypotension (SBP {vitals.bp_systolic} mmHg < 90)"
            )
            safety_outcome = SafetyOutcome.RED
            forced_esi = ESILevel.RESUSCITATION  # Force ESI 1
            recommended_action = "Hemodynamic instability detected - Force ESI 1"
        
        # Rule 4: Severe trauma
        if self._check_severe_trauma(clinical.chief_complaint, clinical.chief_complaint_category):
            triggered_criteria.append(
                "CRITICAL: Severe trauma presentation - time-critical intervention required"
            )
            safety_outcome = SafetyOutcome.RED
            forced_esi = ESILevel.RESUSCITATION  # Force ESI 1
            recommended_action = "Severe trauma requires immediate intervention - Force ESI 1"
        
        # Rule 5: Altered mental status
        if self._check_altered_mental_status(clinical.mental_status.value):
            triggered_criteria.append(
                f"CRITICAL: Altered mental status ({clinical.mental_status.value}) - neurological concern"
            )
            # Only set RED if not already RED
            if safety_outcome != SafetyOutcome.RED:
                safety_outcome = SafetyOutcome.RED
                forced_esi = ESILevel.EMERGENT  # Force ESI 2
                recommended_action = "Altered consciousness requires immediate assessment - Force ESI 2"
        
        # Rule 6: Chest pain in patient > 45 years (cardiac risk)
        if self._check_chest_pain(clinical.chief_complaint, clinical.chief_complaint_category):
            if age > self.CARDIAC_RISK_AGE:
                triggered_criteria.append(
                    f"CAUTION: Chest pain in patient age {age} > 45 years - high cardiac risk"
                )
                # Only set YELLOW if not already RED
                if safety_outcome == SafetyOutcome.GREEN:
                    safety_outcome = SafetyOutcome.YELLOW
                    recommended_action = "Cardiac risk assessment recommended - consider ECG, troponin, and cardiology consult"
        
        # Rule 7: Severe tachycardia (age-specific)
        if vitals.hr is not None:
            tachycardia_threshold = self._get_tachycardia_threshold(age_group)
            if vitals.hr > tachycardia_threshold:
                age_group_str = age_group.value if hasattr(age_group, 'value') else str(age_group)
                triggered_criteria.append(
                    f"CAUTION: Severe tachycardia (HR {vitals.hr} > {tachycardia_threshold} bpm for {age_group_str})"
                )
                # Only set YELLOW if not already RED
                if safety_outcome == SafetyOutcome.GREEN:
                    safety_outcome = SafetyOutcome.YELLOW
                    recommended_action = "Monitor hemodynamic status closely - investigate cause of tachycardia"
        
        # Rule 8: LOW confidence with non-urgent ESI prediction
        if confidence.confidence_level.value == "LOW" and ml_prediction.value >= 3:
            triggered_criteria.append(
                f"CAUTION: LOW confidence ({confidence.overall_score:.0f}%) with ESI {ml_prediction.value} prediction"
            )
            # Only set YELLOW if not already RED
            if safety_outcome == SafetyOutcome.GREEN:
                safety_outcome = SafetyOutcome.YELLOW
                recommended_action = f"LOW confidence - consider escalating to ESI {ml_prediction.value - 1} for safety"
        
        # If no criteria triggered, keep GREEN
        if not triggered_criteria:
            triggered_criteria.append("All safety checks passed")
            recommended_action = "No safety concerns - ML prediction approved"
        
        return SafetyValidation(
            outcome=safety_outcome,
            triggered_criteria=triggered_criteria,
            recommended_action=recommended_action,
            forced_esi_override=forced_esi
        )
    
    def _check_chest_pain(self, chief_complaint: str, chief_complaint_category: str) -> bool:
        """
        Check if patient presents with chest pain.
        
        Args:
            chief_complaint: Free-text chief complaint
            chief_complaint_category: Standardized category
            
        Returns:
            True if chest pain detected
        """
        complaint_lower = chief_complaint.lower()
        category_lower = chief_complaint_category.lower()
        
        # Check both free text and category
        for keyword in self.CHEST_PAIN_KEYWORDS:
            if keyword.lower() in complaint_lower or keyword.lower() in category_lower:
                return True
        
        return False
    
    def _check_severe_trauma(self, chief_complaint: str, chief_complaint_category: str) -> bool:
        """
        Check if patient presents with severe trauma.
        
        Args:
            chief_complaint: Free-text chief complaint
            chief_complaint_category: Standardized category
            
        Returns:
            True if severe trauma detected
        """
        complaint_lower = chief_complaint.lower()
        category_lower = chief_complaint_category.lower()
        
        # Check both free text and category
        for keyword in self.TRAUMA_KEYWORDS:
            if keyword.lower() in complaint_lower or keyword.lower() in category_lower:
                return True
        
        return False
    
    def _check_altered_mental_status(self, mental_status: str) -> bool:
        """
        Check if patient has altered mental status.
        
        Args:
            mental_status: Mental status assessment
            
        Returns:
            True if altered mental status detected
        """
        status_lower = mental_status.lower()
        
        for keyword in self.ALTERED_MENTAL_STATUS:
            if keyword.lower() in status_lower:
                return True
        
        return False
    
    def _get_tachycardia_threshold(self, age_group: AgeGroup) -> int:
        """
        Get age-specific tachycardia threshold.
        
        Args:
            age_group: Patient age group classification
            
        Returns:
            Heart rate threshold for severe tachycardia
        """
        thresholds = {
            AgeGroup.PEDIATRIC_INFANT: 180,     # Infants: HR > 180 concerning
            AgeGroup.PEDIATRIC_CHILD: 160,      # Children: HR > 160 concerning
            AgeGroup.PEDIATRIC_ADOLESCENT: 150, # Adolescents: HR > 150 concerning
            AgeGroup.ADULT: 140,                # Adults: HR > 140 concerning
            AgeGroup.GERIATRIC: 120             # Geriatric: HR > 120 concerning
        }
        return thresholds.get(age_group, 140)  # Default to adult threshold
    
    def apply_safety_override(
        self,
        ml_prediction: ESILevel,
        safety_validation: SafetyValidation
    ) -> Tuple[ESILevel, bool]:
        """
        Apply safety validation override to ML prediction if necessary.
        
        Args:
            ml_prediction: Original ML predicted ESI level
            safety_validation: Safety validation results
            
        Returns:
            Tuple of (final_esi_level, override_applied)
        """
        if safety_validation.forced_esi_override is not None:
            # RED flag with forced override
            return (safety_validation.forced_esi_override, True)
        
        # No override needed
        return (ml_prediction, False)
    
    def get_safety_recommendations(
        self,
        safety_validation: SafetyValidation,
        patient_data: PatientData
    ) -> List[str]:
        """
        Generate actionable safety recommendations based on validation results.
        
        Args:
            safety_validation: Safety validation results
            patient_data: Patient data
            
        Returns:
            List of actionable clinical recommendations
        """
        recommendations = []
        
        # Add outcome-specific recommendations
        if safety_validation.outcome == SafetyOutcome.RED:
            recommendations.append("🚨 CRITICAL: Immediate physician evaluation required")
            recommendations.append("⚠️ Prepare for potential resuscitation")
            recommendations.append("📊 Continuous vital sign monitoring")
        
        elif safety_validation.outcome == SafetyOutcome.YELLOW:
            recommendations.append("⚠️ Enhanced monitoring recommended")
            recommendations.append("🔍 Consider additional diagnostic workup")
        
        else:  # GREEN
            recommendations.append("✅ Standard triage workflow approved")
        
        # Add specific recommendations based on triggered criteria
        for criterion in safety_validation.triggered_criteria:
            if "hypoxia" in criterion.lower():
                recommendations.append("🫁 Supplemental oxygen - target SpO2 ≥94%")
                recommendations.append("🔬 Consider arterial blood gas analysis")
            
            elif "hypotension" in criterion.lower():
                recommendations.append("💉 IV access and fluid resuscitation")
                recommendations.append("📈 Assess for shock etiology")
            
            elif "cardiac" in criterion.lower() or "chest pain" in criterion.lower():
                recommendations.append("🫀 12-lead ECG within 10 minutes")
                recommendations.append("🩸 Cardiac biomarkers (troponin)")
                recommendations.append("💊 Consider aspirin if no contraindications")
            
            elif "trauma" in criterion.lower():
                recommendations.append("🩻 FAST exam and trauma protocol activation")
                recommendations.append("🏥 Notify trauma surgery team")
            
            elif "infant" in criterion.lower():
                recommendations.append("👶 Pediatric assessment protocol")
                recommendations.append("🌡️ Monitor temperature and hydration status")
            
            elif "mental status" in criterion.lower():
                recommendations.append("🧠 Neurological assessment (GCS, pupils)")
                recommendations.append("🩻 Consider head CT if trauma or acute change")
        
        return list(dict.fromkeys(recommendations))  # Remove duplicates while preserving order


# Singleton instance for module-level access
safety_validator = SafetyValidator()
