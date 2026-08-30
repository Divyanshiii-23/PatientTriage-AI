"""
Unit tests for confidence scoring system.

Tests all 4 dimensions plus overall scoring:
- Model Certainty (entropy-based)
- Data Completeness (from preprocessing)
- Clinical Consistency (symptom-vital alignment)
- Pattern Recognition (OOD detection)
"""

import pytest
import numpy as np
from src.confidence import ConfidenceScorer


class TestModelCertainty:
    """Test model certainty computation from probability distributions."""
    
    def test_very_confident_prediction(self):
        """Test high confidence when probability is peaked."""
        scorer = ConfidenceScorer()
        probs = [0.01, 0.95, 0.02, 0.01, 0.01]  # 95% at ESI 2
        certainty = scorer.compute_model_certainty(probs)
        
        assert 80.0 <= certainty <= 100.0  # High certainty
        assert certainty > 75.0  # Should be very high
    
    def test_uncertain_prediction(self):
        """Test low confidence when probability is flat."""
        scorer = ConfidenceScorer()
        probs = [0.20, 0.20, 0.20, 0.20, 0.20]  # Uniform distribution
        certainty = scorer.compute_model_certainty(probs)
        
        assert -1.0 <= certainty <= 5.0  # Very low certainty (near 0)
    
    def test_ambiguous_prediction(self):
        """Test medium confidence for ambiguous case."""
        scorer = ConfidenceScorer()
        probs = [0.05, 0.45, 0.40, 0.08, 0.02]  # Split between ESI 2 and 3
        certainty = scorer.compute_model_certainty(probs)
        
        assert 20.0 <= certainty <= 50.0  # Medium certainty
    
    def test_invalid_probability_count(self):
        """Test error handling for wrong number of probabilities."""
        scorer = ConfidenceScorer()
        probs = [0.5, 0.5]  # Only 2 classes
        
        with pytest.raises(ValueError, match="Expected 5 probabilities"):
            scorer.compute_model_certainty(probs)
    
    def test_invalid_probability_sum(self):
        """Test error handling for probabilities not summing to 1."""
        scorer = ConfidenceScorer()
        probs = [0.1, 0.2, 0.3, 0.4, 0.5]  # Sum = 1.5
        
        with pytest.raises(ValueError, match="must sum to 1.0"):
            scorer.compute_model_certainty(probs)


class TestDataCompleteness:
    """Test data completeness extraction and validation."""
    
    def test_complete_data(self):
        """Test high completeness score."""
        scorer = ConfidenceScorer()
        features = {'data_completeness_score': 95.0}
        
        completeness = scorer.compute_data_completeness(features)
        assert completeness == 95.0
    
    def test_incomplete_data(self):
        """Test low completeness score."""
        scorer = ConfidenceScorer()
        features = {'data_completeness_score': 45.0}
        
        completeness = scorer.compute_data_completeness(features)
        assert completeness == 45.0
    
    def test_missing_completeness_score(self):
        """Test error handling when completeness not in features."""
        scorer = ConfidenceScorer()
        features = {}  # Missing data_completeness_score
        
        with pytest.raises(ValueError, match="data_completeness_score not found"):
            scorer.compute_data_completeness(features)
    
    def test_invalid_completeness_range(self):
        """Test error handling for out-of-range completeness."""
        scorer = ConfidenceScorer()
        features = {'data_completeness_score': 150.0}  # Invalid
        
        with pytest.raises(ValueError, match="must be 0-100"):
            scorer.compute_data_completeness(features)


class TestClinicalConsistency:
    """Test clinical consistency scoring from symptom-vital alignment."""
    
    def test_consistent_presentation(self):
        """Test high consistency when symptoms match vitals."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 1.5,  # Elevated HR
            'spo2_deviation': -1.5,  # Low SpO2
            'bp_systolic_deviation': 0.5,
            'rr_deviation': 1.0,  # Elevated RR
            'temperature_deviation': 1.2,  # Fever
            'pain_score': 7,
        }
        patient = {
            'clinical': {'chief_complaint': 'chest pain'},
            'symptoms': {'symptom_list': ['chest_pain', 'shortness_of_breath']}
        }
        
        consistency = scorer.compute_clinical_consistency(features, patient)
        assert 85.0 <= consistency <= 100.0  # High consistency
    
    def test_pain_underreporting(self):
        """Test penalty for pain underreporting."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 2.0,  # Very elevated HR
            'spo2_deviation': 0.0,
            'bp_systolic_deviation': 0.0,
            'rr_deviation': 0.0,
            'pain_score': 2,  # Low pain score despite elevated HR
        }
        patient = {
            'clinical': {'chief_complaint': 'minor complaint'},
            'symptoms': {'symptom_list': []}
        }
        
        consistency = scorer.compute_clinical_consistency(features, patient)
        assert consistency < 90.0  # Should be penalized
    
    def test_severity_underreporting(self):
        """Test penalty for minor complaint with abnormal vitals."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 2.0,  # Abnormal
            'spo2_deviation': -2.0,  # Abnormal
            'bp_systolic_deviation': 2.0,  # Abnormal
            'rr_deviation': 1.5,  # Abnormal (4 abnormal vitals)
            'pain_score': None,
        }
        patient = {
            'clinical': {'chief_complaint': 'routine checkup'},
            'symptoms': {'symptom_list': []}
        }
        
        consistency = scorer.compute_clinical_consistency(features, patient)
        assert consistency < 85.0  # Should be significantly penalized
    
    def test_respiratory_underreporting(self):
        """Test penalty for low SpO2 without respiratory symptoms."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 0.0,
            'spo2_deviation': -2.5,  # Very low SpO2
            'bp_systolic_deviation': 0.0,
            'rr_deviation': 0.0,
            'pain_score': None,
        }
        patient = {
            'clinical': {'chief_complaint': 'headache'},
            'symptoms': {'symptom_list': ['headache']}  # No respiratory symptoms
        }
        
        consistency = scorer.compute_clinical_consistency(features, patient)
        assert consistency < 85.0  # Should be penalized


class TestPatternRecognition:
    """Test pattern recognition / OOD detection."""
    
    def test_typical_patient(self):
        """Test high score for typical patient."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 0.5,  # Slight elevation
            'bp_systolic_deviation': 0.3,
            'bp_diastolic_deviation': 0.2,
            'spo2_deviation': 0.0,
            'rr_deviation': 0.4,
            'temperature_deviation': 0.3,
            'age': 45,
            'is_missing_hr': False,
            'is_missing_spo2': False,
            'is_missing_bp_systolic': False,
        }
        
        pattern_score = scorer.compute_pattern_recognition(features)
        assert 80.0 <= pattern_score <= 100.0  # High similarity
    
    def test_extreme_outlier(self):
        """Test low score for extreme outliers."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': 6.0,  # Very extreme
            'bp_systolic_deviation': -5.0,  # Very extreme
            'bp_diastolic_deviation': 0.0,
            'spo2_deviation': -4.0,  # Very extreme
            'rr_deviation': 0.0,
            'temperature_deviation': 0.0,
            'age': 105,  # Unusual age
            'is_missing_hr': False,
            'is_missing_spo2': False,
            'is_missing_bp_systolic': False,
        }
        
        pattern_score = scorer.compute_pattern_recognition(features)
        assert 0.0 <= pattern_score <= 40.0  # Low similarity (OOD)
    
    def test_missing_critical_vitals(self):
        """Test penalty for missing critical vitals."""
        scorer = ConfidenceScorer()
        
        features = {
            'hr_deviation': None,  # Missing
            'bp_systolic_deviation': 0.0,
            'bp_diastolic_deviation': 0.0,
            'spo2_deviation': None,  # Missing
            'rr_deviation': 0.0,
            'temperature_deviation': 0.0,
            'age': 45,
            'is_missing_hr': True,
            'is_missing_spo2': True,
            'is_missing_bp_systolic': False,
        }
        
        pattern_score = scorer.compute_pattern_recognition(features)
        assert pattern_score < 95.0  # Should be penalized


class TestOverallConfidence:
    """Test overall confidence aggregation."""
    
    def test_high_confidence(self):
        """Test HIGH classification for scores >= 80."""
        scorer = ConfidenceScorer()
        
        overall, level = scorer.compute_overall_confidence(
            model_certainty=85.0,
            data_completeness=90.0,
            clinical_consistency=88.0,
            pattern_recognition=82.0
        )
        
        assert 80.0 <= overall <= 100.0
        assert level == 'HIGH'
    
    def test_medium_confidence(self):
        """Test MEDIUM classification for scores 60-79."""
        scorer = ConfidenceScorer()
        
        overall, level = scorer.compute_overall_confidence(
            model_certainty=70.0,
            data_completeness=65.0,
            clinical_consistency=72.0,
            pattern_recognition=68.0
        )
        
        assert 60.0 <= overall < 80.0
        assert level == 'MEDIUM'
    
    def test_low_confidence(self):
        """Test LOW classification for scores < 60."""
        scorer = ConfidenceScorer()
        
        overall, level = scorer.compute_overall_confidence(
            model_certainty=45.0,
            data_completeness=50.0,
            clinical_consistency=55.0,
            pattern_recognition=48.0
        )
        
        assert 0.0 <= overall < 60.0
        assert level == 'LOW'
    
    def test_custom_weights(self):
        """Test custom weight configuration."""
        # Weight model certainty more heavily
        scorer = ConfidenceScorer(weights={
            'model_certainty': 0.5,
            'data_completeness': 0.2,
            'clinical_consistency': 0.2,
            'pattern_recognition': 0.1,
        })
        
        overall, level = scorer.compute_overall_confidence(
            model_certainty=90.0,  # Weighted heavily
            data_completeness=50.0,
            clinical_consistency=50.0,
            pattern_recognition=50.0
        )
        
        # Should be high because model_certainty is weighted at 50%
        assert overall > 65.0


class TestCompleteScoring:
    """Test complete end-to-end confidence scoring."""
    
    def test_high_confidence_case(self):
        """Test complete scoring for high confidence prediction."""
        scorer = ConfidenceScorer()
        
        probs = [0.02, 0.85, 0.08, 0.03, 0.02]
        features = {
            'data_completeness_score': 92.0,
            'hr_deviation': 1.2,
            'bp_systolic_deviation': 0.8,
            'bp_diastolic_deviation': 0.5,
            'spo2_deviation': 0.0,
            'rr_deviation': 0.6,
            'temperature_deviation': 0.4,
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
        
        assert 'model_certainty' in confidence
        assert 'data_completeness' in confidence
        assert 'clinical_consistency' in confidence
        assert 'pattern_recognition' in confidence
        assert 'overall_score' in confidence
        assert 'confidence_level' in confidence
        
        # All dimensions should be reasonable
        assert 0.0 <= confidence['model_certainty'] <= 100.0
        assert 0.0 <= confidence['data_completeness'] <= 100.0
        assert 0.0 <= confidence['clinical_consistency'] <= 100.0
        assert 0.0 <= confidence['pattern_recognition'] <= 100.0
        assert 0.0 <= confidence['overall_score'] <= 100.0
        assert confidence['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']
        
        # This should be high confidence overall
        assert confidence['confidence_level'] in ['HIGH', 'MEDIUM']
    
    def test_low_confidence_case(self):
        """Test complete scoring for low confidence prediction."""
        scorer = ConfidenceScorer()
        
        probs = [0.19, 0.21, 0.20, 0.20, 0.20]  # Nearly uniform
        features = {
            'data_completeness_score': 50.0,
            'hr_deviation': 5.0,  # Extreme
            'bp_systolic_deviation': -4.0,  # Extreme
            'bp_diastolic_deviation': 0.0,
            'spo2_deviation': None,
            'rr_deviation': None,
            'temperature_deviation': None,
            'age': 105,
            'pain_score': 2,
            'is_missing_spo2': True,
            'is_missing_rr': True,
            'is_missing_temperature': True,
            'is_missing_hr': False,
            'is_missing_bp_systolic': False,
        }
        patient = {
            'clinical': {'chief_complaint': 'routine checkup'},
            'symptoms': {'symptom_list': []}
        }
        
        confidence = scorer.score_prediction(probs, features, patient)
        
        # This should be low confidence
        assert confidence['confidence_level'] in ['LOW', 'MEDIUM']
        assert confidence['overall_score'] < 70.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
