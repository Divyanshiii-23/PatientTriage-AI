"""
Unit tests for SHAP Explainer module.

Tests:
- SHAP value generation
- Top feature extraction
- Natural language explanation formatting
- Integration with preprocessing pipeline

Requirements: 3.8, 3.9
"""

import pytest
import numpy as np
from src.explainer import SHAPExplainer, load_model_and_create_explainer


class TestSHAPExplainer:
    """Test suite for SHAPExplainer class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.explainer = SHAPExplainer()
    
    def test_initialization(self):
        """Test explainer initializes correctly."""
        assert self.explainer is not None
        assert self.explainer.feature_names is not None
        assert len(self.explainer.feature_names) > 0
    
    def test_feature_names_include_expected_features(self):
        """Test that feature names include critical features."""
        expected_features = [
            'age', 'hr', 'spo2', 'hr_deviation', 'spo2_deviation',
            'chief_complaint_category', 'data_completeness_score'
        ]
        
        for feature in expected_features:
            assert feature in self.explainer.feature_names, f"Missing expected feature: {feature}"
    
    def test_generate_shap_values_returns_correct_shape(self):
        """Test SHAP value generation returns correct shape."""
        # Prepare test features
        test_features = {
            'age': 45,
            'age_group': 'adult_18_64',
            'sex': 'male',
            'hr': 120,
            'hr_deviation': 1.5,
            'bp_systolic': 90,
            'bp_systolic_deviation': -1.0,
            'spo2': 98,
            'spo2_deviation': 0.0,
            'rr': 18,
            'rr_deviation': 0.0,
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 8,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
            'data_completeness_score': 90.0,
        }
        
        shap_values, base_value = self.explainer.generate_shap_values(test_features)
        
        # Check shape
        assert isinstance(shap_values, np.ndarray)
        assert len(shap_values) == len(self.explainer.feature_names)
        
        # Check base value
        assert isinstance(base_value, (int, float))
    
    def test_get_top_features_returns_k_features(self):
        """Test get_top_features returns correct number of features."""
        # Create mock SHAP values
        shap_values = np.array([0.5, 0.3, -0.2, 0.8, 0.1, 0.0, -0.4, 0.6] + [0.0] * 20)
        
        # Get top 5 features
        top_features = self.explainer.get_top_features(shap_values, k=5)
        
        # Check count (should be <= 5, excluding zero contributions)
        assert len(top_features) <= 5
        
        # Check structure
        for feature in top_features:
            assert 'feature' in feature
            assert 'shap_value' in feature
            assert 'direction' in feature
            assert 'severity' in feature
    
    def test_get_top_features_sorted_by_importance(self):
        """Test top features are sorted by absolute importance."""
        # Create mock SHAP values with known ordering
        shap_values = np.array([0.1, -0.5, 0.3, 0.8, -0.2] + [0.0] * 23)
        
        top_features = self.explainer.get_top_features(shap_values, k=3)
        
        # Should be sorted: 0.8, -0.5, 0.3
        assert len(top_features) >= 3
        assert abs(top_features[0]['shap_value']) >= abs(top_features[1]['shap_value'])
        assert abs(top_features[1]['shap_value']) >= abs(top_features[2]['shap_value'])
    
    def test_get_top_features_direction_correct(self):
        """Test direction is correctly assigned based on sign."""
        shap_values = np.array([0.5, -0.3] + [0.0] * 26)
        
        top_features = self.explainer.get_top_features(shap_values, k=2)
        
        # Positive should increase urgency
        positive_feature = [f for f in top_features if f['shap_value'] > 0][0]
        assert positive_feature['direction'] == "increases urgency"
        
        # Negative should decrease urgency
        negative_feature = [f for f in top_features if f['shap_value'] < 0][0]
        assert negative_feature['direction'] == "decreases urgency"
    
    def test_get_top_features_severity_classification(self):
        """Test severity is correctly classified."""
        shap_values = np.array([0.5, 0.3, 0.1, 0.0] + [0.0] * 24)
        
        top_features = self.explainer.get_top_features(shap_values, k=3)
        
        # Check severity thresholds
        critical = [f for f in top_features if f['severity'] == 'critical']
        concerning = [f for f in top_features if f['severity'] == 'concerning']
        normal = [f for f in top_features if f['severity'] == 'normal']
        
        # Should have critical (>0.4), concerning (>0.2), normal (<0.2)
        assert len(critical) >= 1  # 0.5 is critical
        assert len(concerning) >= 1  # 0.3 is concerning
    
    def test_format_natural_language_explanation_structure(self):
        """Test natural language explanation is well-formed."""
        top_features = [
            {
                'feature': 'hr_deviation',
                'shap_value': 0.4,
                'direction': 'increases urgency',
                'severity': 'concerning'
            },
            {
                'feature': 'chief_complaint_category',
                'shap_value': 0.5,
                'direction': 'increases urgency',
                'severity': 'critical'
            },
        ]
        
        test_features = {
            'hr': 120,
            'hr_deviation': 1.5,
            'chief_complaint_category': 'chest_pain_cardiac',
        }
        
        explanation = self.explainer.format_natural_language_explanation(
            top_features, test_features, predicted_esi=2
        )
        
        # Check basic structure
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "ESI 2" in explanation
        assert "model predicts" in explanation.lower()
    
    def test_format_natural_language_includes_feature_values(self):
        """Test explanation includes actual feature values."""
        top_features = [
            {
                'feature': 'hr_deviation',
                'shap_value': 0.4,
                'direction': 'increases urgency',
                'severity': 'concerning'
            },
            {
                'feature': 'spo2_deviation',
                'shap_value': -0.5,
                'direction': 'increases urgency',
                'severity': 'critical'
            },
        ]
        
        test_features = {
            'hr': 120,
            'hr_deviation': 1.5,
            'spo2': 89,
            'spo2_deviation': -1.0,
        }
        
        explanation = self.explainer.format_natural_language_explanation(
            top_features, test_features, predicted_esi=2
        )
        
        # Should include actual values
        assert "120" in explanation or "heart rate" in explanation.lower()
        assert "89" in explanation or "oxygen" in explanation.lower()
    
    def test_explain_prediction_integration(self):
        """Test full explanation pipeline."""
        test_features = {
            'age': 55,
            'age_group': 'adult_18_64',
            'sex': 'male',
            'hr': 120,
            'hr_deviation': 1.0,
            'bp_systolic': 150,
            'bp_systolic_deviation': 1.0,
            'spo2': 96,
            'spo2_deviation': 0.1,
            'rr': 20,
            'rr_deviation': 0.5,
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 8,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
            'data_completeness_score': 90.0,
        }
        
        result = self.explainer.explain_prediction(test_features, predicted_esi=2)
        
        # Check structure
        assert 'shap_explanation' in result
        assert 'explanation_text' in result
        assert 'base_value' in result
        
        # Check SHAP explanation
        assert isinstance(result['shap_explanation'], list)
        assert len(result['shap_explanation']) > 0
        assert len(result['shap_explanation']) <= 5  # Top 5
        
        # Check explanation text
        assert isinstance(result['explanation_text'], str)
        assert len(result['explanation_text']) > 0
        
        # Check base value
        assert isinstance(result['base_value'], (int, float))
    
    def test_explain_prediction_top_features_have_values(self):
        """Test explanation includes feature values."""
        test_features = {
            'age': 45,
            'age_group': 'adult_18_64',
            'hr': 120,
            'hr_deviation': 1.5,
            'spo2': 98,
            'spo2_deviation': 0.0,
            'chief_complaint_category': 'chest_pain_cardiac',
            'data_completeness_score': 90.0,
        }
        
        result = self.explainer.explain_prediction(test_features, predicted_esi=2)
        
        # Each top feature should have a value
        for feature in result['shap_explanation']:
            assert 'feature_value' in feature
    
    def test_high_urgency_case(self):
        """Test explanation for high-urgency case (ESI 1-2)."""
        high_urgency_features = {
            'age': 65,
            'age_group': 'geriatric_65_plus',
            'hr': 150,
            'hr_deviation': 2.5,
            'spo2': 85,
            'spo2_deviation': -2.0,
            'bp_systolic': 80,
            'bp_systolic_deviation': -2.0,
            'rr': 35,
            'rr_deviation': 2.0,
            'chief_complaint_category': 'respiratory_distress',
            'mental_status': 'confused',
            'arrival_mode': 'ambulance',
            'data_completeness_score': 85.0,
        }
        
        result = self.explainer.explain_prediction(high_urgency_features, predicted_esi=1)
        
        # Should have strong positive contributions
        total_positive_contribution = sum(
            f['shap_value'] for f in result['shap_explanation'] if f['shap_value'] > 0
        )
        assert total_positive_contribution > 0.5  # Significant positive contribution
    
    def test_low_urgency_case(self):
        """Test explanation for low-urgency case (ESI 4-5)."""
        low_urgency_features = {
            'age': 30,
            'age_group': 'adult_18_64',
            'hr': 75,
            'hr_deviation': 0.0,
            'spo2': 99,
            'spo2_deviation': 0.0,
            'bp_systolic': 120,
            'bp_systolic_deviation': 0.0,
            'rr': 14,
            'rr_deviation': 0.0,
            'chief_complaint_category': 'cold_flu_symptoms',
            'mental_status': 'alert',
            'arrival_mode': 'walk_in',
            'data_completeness_score': 85.0,
        }
        
        result = self.explainer.explain_prediction(low_urgency_features, predicted_esi=4)
        
        # Should have features with negative or low contributions
        assert len(result['shap_explanation']) > 0
        # At least one feature should decrease urgency or have low contribution
        has_decreasing = any(f['shap_value'] < 0 or abs(f['shap_value']) < 0.2 
                            for f in result['shap_explanation'])
        assert has_decreasing
    
    def test_pediatric_case_includes_age_factor(self):
        """Test pediatric case highlights age as a factor."""
        pediatric_features = {
            'age': 1,
            'age_group': 'infant_0_2',
            'hr': 140,
            'hr_deviation': 0.0,  # Normal for infant
            'spo2': 98,
            'spo2_deviation': 0.0,
            'chief_complaint_category': 'fever_high',
            'data_completeness_score': 75.0,
        }
        
        result = self.explainer.explain_prediction(pediatric_features, predicted_esi=3)
        
        # Age should be in top features
        feature_names = [f['feature'] for f in result['shap_explanation']]
        assert 'age' in feature_names or 'age_group' in feature_names


class TestLoadModelAndCreateExplainer:
    """Test model loading utility."""
    
    def test_load_explainer_without_model(self):
        """Test creating explainer without trained model."""
        explainer = load_model_and_create_explainer(model_path=None)
        
        assert explainer is not None
        assert isinstance(explainer, SHAPExplainer)
    
    def test_load_explainer_with_nonexistent_model(self):
        """Test creating explainer with non-existent model path."""
        explainer = load_model_and_create_explainer(model_path="/path/to/nonexistent/model.cbm")
        
        # Should still create explainer with mock values
        assert explainer is not None
        assert isinstance(explainer, SHAPExplainer)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
