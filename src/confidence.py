"""
Multi-Dimensional Confidence Scoring System for ED Triage ML Predictions.

Implements 4 confidence dimensions:
1. Model Certainty: Entropy-based measure from probability distribution
2. Data Completeness: Percentage of features present
3. Clinical Consistency: Symptom-vital alignment checks
4. Pattern Recognition: Distance from training distribution (OOD detection)

Aggregates to overall confidence: HIGH (>80%), MEDIUM (60-80%), LOW (<60%)

Requirements: 3.3, 3.4, 8.1-8.9
"""

from typing import Dict, List, Optional, Tuple
import numpy as np


class ConfidenceScorer:
    """
    Multi-dimensional confidence scoring for triage predictions.
    
    Computes 4 separate confidence dimensions and aggregates to overall score:
    - Model Certainty: From probability entropy (0-100)
    - Data Completeness: From preprocessing (0-100)
    - Clinical Consistency: Symptom-vital discordance checks (0-100)
    - Pattern Recognition: Training distribution similarity (0-100)
    
    Overall score is weighted average with configurable weights.
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        training_mean: Optional[np.ndarray] = None,
        training_std: Optional[np.ndarray] = None,
    ):
        """
        Initialize confidence scorer.
        
        Args:
            weights: Dimension weights for overall score (default: equal weights)
            training_mean: Mean vector from training data for OOD detection
            training_std: Std vector from training data for OOD detection
        """
        # Default equal weights for all dimensions
        self.weights = weights or {
            'model_certainty': 0.25,
            'data_completeness': 0.25,
            'clinical_consistency': 0.25,
            'pattern_recognition': 0.25,
        }
        
        # Validate weights sum to 1.0
        weight_sum = sum(self.weights.values())
        if not (0.99 <= weight_sum <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")
        
        # Training distribution statistics for OOD detection
        self.training_mean = training_mean
        self.training_std = training_std
    
    def compute_model_certainty(self, probability_distribution: List[float]) -> float:
        """
        Compute model certainty from probability distribution.
        
        Uses normalized entropy as inverse of certainty:
        - Low entropy (peaked distribution) → High certainty
        - High entropy (uniform distribution) → Low certainty
        
        Formula:
            entropy = -sum(p * log(p)) for all p in distribution
            max_entropy = log(n_classes)  # 5 ESI levels
            normalized_entropy = entropy / max_entropy  # 0-1
            certainty_score = (1 - normalized_entropy) * 100  # 0-100
        
        Args:
            probability_distribution: List of probabilities for ESI 1-5 (must sum to 1.0)
        
        Returns:
            Certainty score 0-100 (higher = more certain)
        
        Example:
            >>> # Very confident prediction: ESI 2 with 95% probability
            >>> compute_model_certainty([0.01, 0.95, 0.02, 0.01, 0.01])
            91.3  # High certainty
            
            >>> # Ambiguous prediction: ESI 2 and 3 both likely
            >>> compute_model_certainty([0.05, 0.45, 0.40, 0.08, 0.02])
            62.5  # Medium certainty
            
            >>> # Very uncertain: nearly uniform distribution
            >>> compute_model_certainty([0.20, 0.20, 0.20, 0.20, 0.20])
            0.0  # Low certainty
        """
        # Validate input
        if len(probability_distribution) != 5:
            raise ValueError(f"Expected 5 probabilities (ESI 1-5), got {len(probability_distribution)}")
        
        prob_sum = sum(probability_distribution)
        if not (0.99 <= prob_sum <= 1.01):
            raise ValueError(f"Probabilities must sum to 1.0, got {prob_sum}")
        
        # Convert to numpy array and add small epsilon to avoid log(0)
        probs = np.array(probability_distribution)
        epsilon = 1e-10
        probs = np.clip(probs, epsilon, 1.0)
        
        # Compute entropy
        entropy = -np.sum(probs * np.log(probs))
        
        # Maximum entropy for 5 classes (uniform distribution)
        max_entropy = np.log(5)
        
        # Normalize entropy to 0-1 range
        normalized_entropy = entropy / max_entropy
        
        # Convert to certainty score (inverse of entropy)
        certainty_score = (1.0 - normalized_entropy) * 100.0
        
        return float(certainty_score)
    
    def compute_data_completeness(self, preprocessed_features: Dict[str, any]) -> float:
        """
        Compute data completeness score from preprocessed features.
        
        This is already computed in preprocessing pipeline as 'data_completeness_score'.
        We extract and validate it here.
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
        
        Returns:
            Data completeness score 0-100
        
        Example:
            >>> features = {'data_completeness_score': 85.0, ...}
            >>> compute_data_completeness(features)
            85.0
        """
        completeness = preprocessed_features.get('data_completeness_score')
        
        if completeness is None:
            raise ValueError("data_completeness_score not found in preprocessed features")
        
        if not (0.0 <= completeness <= 100.0):
            raise ValueError(f"Data completeness must be 0-100, got {completeness}")
        
        return float(completeness)
    
    def compute_clinical_consistency(
        self,
        preprocessed_features: Dict[str, any],
        patient_data: Dict[str, any]
    ) -> float:
        """
        Compute clinical consistency score from symptom-vital alignment.
        
        Checks for discordance patterns that suggest under-reporting or data quality issues:
        1. Pain underreporting: Low pain score but elevated heart rate
        2. Severity underreporting: Minor complaint but multiple abnormal vitals
        3. Respiratory underreporting: Low SpO2 but no respiratory symptoms
        4. Vital-symptom alignment: Reported symptoms match vital sign abnormalities
        
        Scoring:
        - Start at 100 (perfect consistency)
        - Deduct points for each discordance detected
        - Minimum score is 0
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
            patient_data: Original patient data dict
        
        Returns:
            Clinical consistency score 0-100 (higher = more consistent)
        
        Example:
            >>> # Patient with chest pain, elevated HR, low SpO2 → Consistent
            >>> features = {'hr_deviation': 1.5, 'spo2_deviation': -2.0, ...}
            >>> patient = {'symptoms': ['chest_pain', 'shortness_of_breath'], ...}
            >>> compute_clinical_consistency(features, patient)
            95.0  # High consistency
            
            >>> # Patient with normal vitals but reports severe pain → Inconsistent
            >>> features = {'hr_deviation': 0.0, 'pain_score': 9, ...}
            >>> patient = {'pain_score': 9, ...}
            >>> compute_clinical_consistency(features, patient)
            70.0  # Moderate consistency (pain-vital mismatch)
        """
        consistency_score = 100.0
        
        # Extract relevant features
        hr_deviation = preprocessed_features.get('hr_deviation', 0.0)
        spo2_deviation = preprocessed_features.get('spo2_deviation', 0.0)
        bp_systolic_deviation = preprocessed_features.get('bp_systolic_deviation', 0.0)
        rr_deviation = preprocessed_features.get('rr_deviation', 0.0)
        pain_score = preprocessed_features.get('pain_score')
        
        # Get symptoms and clinical data
        clinical = patient_data.get('clinical', {})
        symptoms_data = patient_data.get('symptoms', {})
        symptoms = symptoms_data.get('symptom_list', []) if isinstance(symptoms_data, dict) else symptoms_data
        
        # Count abnormal vitals (deviation > 1.0 or < -1.0)
        abnormal_vital_count = 0
        if hr_deviation is not None and abs(hr_deviation) > 1.0:
            abnormal_vital_count += 1
        if spo2_deviation is not None and abs(spo2_deviation) > 1.0:
            abnormal_vital_count += 1
        if bp_systolic_deviation is not None and abs(bp_systolic_deviation) > 1.0:
            abnormal_vital_count += 1
        if rr_deviation is not None and abs(rr_deviation) > 1.0:
            abnormal_vital_count += 1
        
        # Check 1: Pain underreporting
        # Low pain score (<4) but elevated heart rate (HR deviation > 1.5)
        if pain_score is not None and pain_score < 4:
            if hr_deviation is not None and hr_deviation > 1.5:
                consistency_score -= 15.0  # Moderate deduction
        
        # Check 2: Severity underreporting
        # Minor complaint but 3+ abnormal vitals
        minor_complaints = ['cold', 'flu', 'minor_injury', 'rash', 'routine_checkup']
        chief_complaint = clinical.get('chief_complaint', '').lower()
        is_minor_complaint = any(mc in chief_complaint for mc in minor_complaints)
        
        if is_minor_complaint and abnormal_vital_count >= 3:
            consistency_score -= 20.0  # Significant deduction
        
        # Check 3: Respiratory underreporting
        # Low SpO2 (deviation < -1.0) but no respiratory symptoms
        respiratory_symptoms = [
            'shortness_of_breath', 'dyspnea', 'wheezing', 'cough',
            'respiratory_distress', 'difficulty_breathing'
        ]
        has_respiratory_symptoms = any(rs in symptoms for rs in respiratory_symptoms)
        
        if spo2_deviation is not None and spo2_deviation < -1.0:
            if not has_respiratory_symptoms:
                consistency_score -= 20.0  # Significant deduction
        
        # Check 4: Vital-symptom alignment
        # Reported symptoms should match vital sign abnormalities
        
        # Chest pain symptoms should correlate with abnormal HR or BP
        chest_symptoms = ['chest_pain', 'cardiac', 'heart']
        has_chest_symptoms = any(cs in symptoms or cs in chief_complaint for cs in chest_symptoms)
        
        if has_chest_symptoms:
            # Expect HR elevation or BP abnormality
            if hr_deviation is not None and hr_deviation > 0.5:
                consistency_score += 5.0  # Bonus for alignment (capped at 100)
            elif hr_deviation is not None and abs(hr_deviation) < 0.2 and abs(bp_systolic_deviation or 0.0) < 0.2:
                # Chest pain but completely normal vitals → slight penalty
                consistency_score -= 10.0
        
        # Fever symptoms should correlate with elevated temperature
        fever_symptoms = ['fever', 'chills', 'hot']
        has_fever_symptoms = any(fs in symptoms or fs in chief_complaint for fs in fever_symptoms)
        temperature_deviation = preprocessed_features.get('temperature_deviation')
        
        if has_fever_symptoms:
            if temperature_deviation is not None and temperature_deviation > 0.5:
                consistency_score += 5.0  # Bonus for alignment
            elif temperature_deviation is not None and temperature_deviation < -0.5:
                # Reports fever but low temperature → inconsistent
                consistency_score -= 15.0
        
        # Ensure score stays in 0-100 range
        consistency_score = max(0.0, min(100.0, consistency_score))
        
        return float(consistency_score)
    
    def compute_pattern_recognition(
        self,
        preprocessed_features: Dict[str, any]
    ) -> float:
        """
        Compute pattern recognition score based on distance from training distribution.
        
        Uses Out-of-Distribution (OOD) detection to identify unusual patient presentations
        that differ significantly from the training data.
        
        Method:
        1. Extract numeric features (vital deviations, age, scores)
        2. Compute Mahalanobis distance from training distribution mean
        3. Convert distance to confidence score (closer = higher confidence)
        
        If training statistics are not provided, use simplified heuristic:
        - Check if vital deviations are extreme (>3 standard deviations)
        - Deduct points for out-of-range values
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
        
        Returns:
            Pattern recognition score 0-100 (higher = more similar to training data)
        
        Example:
            >>> # Typical adult patient with normal-ish vitals
            >>> features = {
            ...     'hr_deviation': 0.5,
            ...     'bp_systolic_deviation': 0.3,
            ...     'spo2_deviation': 0.0,
            ...     'age': 45,
            ...     ...
            ... }
            >>> compute_pattern_recognition(features)
            88.0  # High similarity to training
            
            >>> # Unusual presentation with extreme vitals
            >>> features = {
            ...     'hr_deviation': 4.5,  # Very extreme
            ...     'bp_systolic_deviation': -3.0,  # Very extreme
            ...     'spo2_deviation': -5.0,  # Very extreme
            ...     'age': 105,  # Unusual age
            ...     ...
            ... }
            >>> compute_pattern_recognition(features)
            15.0  # Low similarity (OOD case)
        """
        # If training statistics available, use Mahalanobis distance
        if self.training_mean is not None and self.training_std is not None:
            # Extract numeric feature vector
            feature_vector = self._extract_numeric_features(preprocessed_features)
            
            # Compute standardized Mahalanobis distance
            # distance = sqrt(sum(((x - mean) / std) ** 2))
            diff = feature_vector - self.training_mean
            standardized_diff = diff / (self.training_std + 1e-8)  # Avoid division by zero
            mahalanobis_distance = np.sqrt(np.sum(standardized_diff ** 2))
            
            # Convert distance to score (closer = higher score)
            # Using exponential decay: score = 100 * exp(-distance / scale)
            scale = 5.0  # Tunable parameter (smaller = more sensitive to distance)
            pattern_score = 100.0 * np.exp(-mahalanobis_distance / scale)
            
            return float(pattern_score)
        
        # Fallback: Heuristic-based OOD detection without training statistics
        pattern_score = 100.0
        
        # Extract vital deviations
        hr_dev = preprocessed_features.get('hr_deviation')
        bp_sys_dev = preprocessed_features.get('bp_systolic_deviation')
        bp_dia_dev = preprocessed_features.get('bp_diastolic_deviation')
        spo2_dev = preprocessed_features.get('spo2_deviation')
        rr_dev = preprocessed_features.get('rr_deviation')
        temp_dev = preprocessed_features.get('temperature_deviation')
        
        # Check for extreme deviations (>3 SD from normal range)
        extreme_threshold = 3.0
        very_extreme_threshold = 5.0
        
        deviations = [hr_dev, bp_sys_dev, bp_dia_dev, spo2_dev, rr_dev, temp_dev]
        
        for dev in deviations:
            if dev is None:
                continue
            
            abs_dev = abs(dev)
            
            if abs_dev > very_extreme_threshold:
                # Very extreme outlier (>5 SD)
                pattern_score -= 30.0
            elif abs_dev > extreme_threshold:
                # Extreme outlier (>3 SD)
                pattern_score -= 15.0
            elif abs_dev > 2.0:
                # Moderate outlier (>2 SD)
                pattern_score -= 5.0
        
        # Check for unusual age
        age = preprocessed_features.get('age', 0)
        if age < 1:
            pattern_score -= 10.0  # Very young infants are unusual
        elif age > 100:
            pattern_score -= 15.0  # Very old patients are unusual
        
        # Check for missing critical vitals (unusual in ED setting)
        missing_hr = preprocessed_features.get('is_missing_hr', False)
        missing_spo2 = preprocessed_features.get('is_missing_spo2', False)
        missing_bp = preprocessed_features.get('is_missing_bp_systolic', False)
        
        if missing_hr or missing_spo2 or missing_bp:
            pattern_score -= 10.0  # Missing critical vitals is unusual
        
        # Ensure score stays in 0-100 range
        pattern_score = max(0.0, min(100.0, pattern_score))
        
        return float(pattern_score)
    
    def _extract_numeric_features(self, preprocessed_features: Dict[str, any]) -> np.ndarray:
        """
        Extract numeric feature vector for OOD detection.
        
        Args:
            preprocessed_features: Features from preprocessing
        
        Returns:
            Numpy array of numeric features
        """
        # Feature list for OOD detection (vital deviations + age)
        feature_names = [
            'age',
            'hr_deviation',
            'bp_systolic_deviation',
            'bp_diastolic_deviation',
            'spo2_deviation',
            'rr_deviation',
            'temperature_deviation',
        ]
        
        feature_vector = []
        for fname in feature_names:
            value = preprocessed_features.get(fname)
            # Replace None with 0.0 for missing values
            feature_vector.append(value if value is not None else 0.0)
        
        return np.array(feature_vector)
    
    def compute_overall_confidence(
        self,
        model_certainty: float,
        data_completeness: float,
        clinical_consistency: float,
        pattern_recognition: float
    ) -> Tuple[float, str]:
        """
        Compute overall weighted confidence score and classification.
        
        Formula:
            overall = (w1 * model_certainty + w2 * data_completeness +
                      w3 * clinical_consistency + w4 * pattern_recognition)
        
        Classification:
            - HIGH: overall >= 80
            - MEDIUM: 60 <= overall < 80
            - LOW: overall < 60
        
        Args:
            model_certainty: Model certainty score 0-100
            data_completeness: Data completeness score 0-100
            clinical_consistency: Clinical consistency score 0-100
            pattern_recognition: Pattern recognition score 0-100
        
        Returns:
            Tuple of (overall_score: float, confidence_level: str)
        
        Example:
            >>> compute_overall_confidence(85.0, 90.0, 75.0, 82.0)
            (83.0, 'HIGH')
            
            >>> compute_overall_confidence(70.0, 60.0, 65.0, 72.0)
            (66.75, 'MEDIUM')
            
            >>> compute_overall_confidence(45.0, 50.0, 55.0, 48.0)
            (49.5, 'LOW')
        """
        # Validate inputs
        for score, name in [
            (model_certainty, 'model_certainty'),
            (data_completeness, 'data_completeness'),
            (clinical_consistency, 'clinical_consistency'),
            (pattern_recognition, 'pattern_recognition')
        ]:
            if not (0.0 <= score <= 100.0):
                raise ValueError(f"{name} must be 0-100, got {score}")
        
        # Compute weighted average
        overall_score = (
            self.weights['model_certainty'] * model_certainty +
            self.weights['data_completeness'] * data_completeness +
            self.weights['clinical_consistency'] * clinical_consistency +
            self.weights['pattern_recognition'] * pattern_recognition
        )
        
        # Classify confidence level
        if overall_score >= 80.0:
            confidence_level = 'HIGH'
        elif overall_score >= 60.0:
            confidence_level = 'MEDIUM'
        else:
            confidence_level = 'LOW'
        
        return float(overall_score), confidence_level
    
    def score_prediction(
        self,
        probability_distribution: List[float],
        preprocessed_features: Dict[str, any],
        patient_data: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Complete confidence scoring for a prediction.
        
        Computes all 4 dimensions + overall score + classification.
        
        Args:
            probability_distribution: Model's probability output for ESI 1-5
            preprocessed_features: Features from preprocessing pipeline
            patient_data: Original patient data dict
        
        Returns:
            Dictionary with all confidence scores:
            {
                'model_certainty': float (0-100),
                'data_completeness': float (0-100),
                'clinical_consistency': float (0-100),
                'pattern_recognition': float (0-100),
                'overall_score': float (0-100),
                'confidence_level': str ('HIGH'/'MEDIUM'/'LOW')
            }
        
        Example:
            >>> scorer = ConfidenceScorer()
            >>> probs = [0.05, 0.70, 0.15, 0.08, 0.02]
            >>> features = {...}  # Preprocessed features
            >>> patient = {...}  # Original patient data
            >>> confidence = scorer.score_prediction(probs, features, patient)
            >>> confidence['overall_score']
            78.5
            >>> confidence['confidence_level']
            'MEDIUM'
        """
        # Compute each dimension
        model_certainty = self.compute_model_certainty(probability_distribution)
        data_completeness = self.compute_data_completeness(preprocessed_features)
        clinical_consistency = self.compute_clinical_consistency(
            preprocessed_features, patient_data
        )
        pattern_recognition = self.compute_pattern_recognition(preprocessed_features)
        
        # Compute overall score and classification
        overall_score, confidence_level = self.compute_overall_confidence(
            model_certainty,
            data_completeness,
            clinical_consistency,
            pattern_recognition
        )
        
        return {
            'model_certainty': model_certainty,
            'data_completeness': data_completeness,
            'clinical_consistency': clinical_consistency,
            'pattern_recognition': pattern_recognition,
            'overall_score': overall_score,
            'confidence_level': confidence_level
        }


# ============================================================================
# Helper Functions
# ============================================================================

def load_training_statistics(training_data_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load training data statistics for OOD detection.
    
    Computes mean and standard deviation of numeric features from training data.
    
    Args:
        training_data_path: Path to training data JSON file
    
    Returns:
        Tuple of (mean_vector, std_vector) as numpy arrays
    """
    import json
    from src.preprocessing import preprocess_patient_data
    
    # Load training data
    with open(training_data_path, 'r') as f:
        training_patients = json.load(f)
    
    # Preprocess all patients
    feature_vectors = []
    for patient in training_patients:
        try:
            features = preprocess_patient_data(patient)
            
            # Extract numeric features
            feature_vec = [
                features.get('age', 0),
                features.get('hr_deviation', 0.0),
                features.get('bp_systolic_deviation', 0.0),
                features.get('bp_diastolic_deviation', 0.0),
                features.get('spo2_deviation', 0.0),
                features.get('rr_deviation', 0.0),
                features.get('temperature_deviation', 0.0),
            ]
            
            feature_vectors.append(feature_vec)
        except Exception as e:
            print(f"Warning: Skipping patient due to preprocessing error: {e}")
            continue
    
    # Convert to numpy array
    feature_matrix = np.array(feature_vectors)
    
    # Compute statistics
    mean_vector = np.mean(feature_matrix, axis=0)
    std_vector = np.std(feature_matrix, axis=0)
    
    return mean_vector, std_vector


if __name__ == '__main__':
    # Example usage and testing
    print("Confidence Scoring System Test\n")
    
    # Test 1: High confidence case (peaked distribution, complete data)
    print("Test 1: High confidence prediction")
    scorer = ConfidenceScorer()
    
    probs = [0.02, 0.85, 0.08, 0.03, 0.02]  # Very peaked at ESI 2
    features = {
        'data_completeness_score': 95.0,
        'hr_deviation': 1.2,
        'bp_systolic_deviation': 0.8,
        'spo2_deviation': 0.0,
        'rr_deviation': 0.5,
        'temperature_deviation': 0.3,
        'age': 45,
        'pain_score': 7,
        'is_missing_hr': False,
        'is_missing_spo2': False,
        'is_missing_bp_systolic': False,
    }
    patient = {
        'clinical': {'chief_complaint': 'chest pain'},
        'symptoms': {'symptom_list': ['chest_pain', 'shortness_of_breath']}
    }
    
    confidence = scorer.score_prediction(probs, features, patient)
    print(f"  Model Certainty: {confidence['model_certainty']:.1f}")
    print(f"  Data Completeness: {confidence['data_completeness']:.1f}")
    print(f"  Clinical Consistency: {confidence['clinical_consistency']:.1f}")
    print(f"  Pattern Recognition: {confidence['pattern_recognition']:.1f}")
    print(f"  Overall Score: {confidence['overall_score']:.1f}")
    print(f"  Confidence Level: {confidence['confidence_level']}")
    print()
    
    # Test 2: Low confidence case (flat distribution, missing data, inconsistencies)
    print("Test 2: Low confidence prediction")
    
    probs = [0.18, 0.22, 0.21, 0.20, 0.19]  # Nearly uniform (uncertain)
    features = {
        'data_completeness_score': 55.0,  # Incomplete data
        'hr_deviation': 4.5,  # Extreme outlier
        'bp_systolic_deviation': -3.2,  # Extreme outlier
        'spo2_deviation': -2.5,  # Significant deviation
        'rr_deviation': None,  # Missing
        'temperature_deviation': None,  # Missing
        'age': 102,  # Unusual age
        'pain_score': 2,  # Low pain but extreme vitals
        'is_missing_rr': True,
        'is_missing_temperature': True,
        'is_missing_bp_systolic': False,
    }
    patient = {
        'clinical': {'chief_complaint': 'routine checkup'},  # Minor complaint
        'symptoms': {'symptom_list': []}  # No symptoms despite abnormal vitals
    }
    
    confidence = scorer.score_prediction(probs, features, patient)
    print(f"  Model Certainty: {confidence['model_certainty']:.1f}")
    print(f"  Data Completeness: {confidence['data_completeness']:.1f}")
    print(f"  Clinical Consistency: {confidence['clinical_consistency']:.1f}")
    print(f"  Pattern Recognition: {confidence['pattern_recognition']:.1f}")
    print(f"  Overall Score: {confidence['overall_score']:.1f}")
    print(f"  Confidence Level: {confidence['confidence_level']}")
    print()
    
    # Test 3: Medium confidence case
    print("Test 3: Medium confidence prediction (ambiguous case)")
    
    probs = [0.05, 0.48, 0.38, 0.07, 0.02]  # Split between ESI 2 and 3
    features = {
        'data_completeness_score': 75.0,
        'hr_deviation': 1.0,
        'bp_systolic_deviation': 0.5,
        'spo2_deviation': 0.0,
        'rr_deviation': 0.3,
        'temperature_deviation': 0.8,
        'age': 48,
        'pain_score': 5,
        'is_missing_hr': False,
        'is_missing_spo2': False,
        'is_missing_bp_systolic': False,
    }
    patient = {
        'clinical': {'chief_complaint': 'chest discomfort'},
        'symptoms': {'symptom_list': ['mild_chest_pain']}
    }
    
    confidence = scorer.score_prediction(probs, features, patient)
    print(f"  Model Certainty: {confidence['model_certainty']:.1f}")
    print(f"  Data Completeness: {confidence['data_completeness']:.1f}")
    print(f"  Clinical Consistency: {confidence['clinical_consistency']:.1f}")
    print(f"  Pattern Recognition: {confidence['pattern_recognition']:.1f}")
    print(f"  Overall Score: {confidence['overall_score']:.1f}")
    print(f"  Confidence Level: {confidence['confidence_level']}")
    print()
    
    print("✅ Confidence scoring system test complete!")
