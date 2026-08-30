"""
SHAP Explainer for Feature Contributions.

Implements SHAP-based explainability for ESI triage predictions:
- Loads trained CatBoost model and creates TreeExplainer
- Generates SHAP values for top 5 contributing features
- Formats explanations as natural language

Requirements: 3.8, 3.9
"""

import shap
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path


class SHAPExplainer:
    """
    SHAP-based explainability for triage predictions.
    
    Uses TreeExplainer for CatBoost models to compute feature importance
    with Shapley values. Provides natural language explanations of predictions.
    """
    
    def __init__(self, model=None, feature_names: Optional[List[str]] = None):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained CatBoost model (if None, uses mock model)
            feature_names: List of feature names for explanation
        """
        self.model = model
        self.feature_names = feature_names or self._get_default_feature_names()
        
        # Create TreeExplainer if model is provided
        if model is not None:
            try:
                self.explainer = shap.TreeExplainer(model)
            except Exception as e:
                print(f"Warning: Could not create TreeExplainer: {e}")
                self.explainer = None
        else:
            self.explainer = None
    
    def _get_default_feature_names(self) -> List[str]:
        """
        Get default feature names from preprocessing pipeline.
        
        Returns:
            List of feature names
        """
        return [
            # Demographics
            'age',
            'age_group',
            'sex',
            
            # Raw vitals
            'hr',
            'bp_systolic',
            'bp_diastolic',
            'spo2',
            'rr',
            'temperature',
            
            # Vital deviations (most important for SHAP)
            'hr_deviation',
            'bp_systolic_deviation',
            'bp_diastolic_deviation',
            'spo2_deviation',
            'rr_deviation',
            'temperature_deviation',
            
            # Missing indicators
            'is_missing_hr',
            'is_missing_bp_systolic',
            'is_missing_bp_diastolic',
            'is_missing_spo2',
            'is_missing_rr',
            'is_missing_temperature',
            'is_missing_pain_score',
            'is_missing_medical_history',
            
            # Data quality
            'data_completeness_score',
            
            # Clinical
            'chief_complaint_category',
            'pain_score',
            'arrival_mode',
            'mental_status',
        ]
    
    def _prepare_features_for_shap(
        self, 
        preprocessed_features: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Convert preprocessed features dict to DataFrame for SHAP.
        
        Handles:
        - Categorical encoding (age_group, chief_complaint_category, etc.)
        - Boolean to int conversion
        - Missing value handling
        
        Args:
            preprocessed_features: Dictionary from preprocessing pipeline
            
        Returns:
            DataFrame with one row, columns matching feature_names
        """
        # Extract numeric and encoded categorical features
        feature_dict = {}
        
        for feature_name in self.feature_names:
            value = preprocessed_features.get(feature_name)
            
            # Handle categorical features (encode as needed)
            if feature_name == 'age_group':
                # Encode age group as ordinal
                age_group_map = {
                    'infant_0_2': 0,
                    'child_3_12': 1,
                    'adolescent_13_17': 2,
                    'adult_18_64': 3,
                    'geriatric_65_plus': 4,
                }
                feature_dict[feature_name] = age_group_map.get(value, 3)  # Default to adult
            
            elif feature_name == 'sex':
                # Encode sex as binary
                sex_map = {'male': 0, 'female': 1, 'other': 2}
                feature_dict[feature_name] = sex_map.get(value, 0)
            
            elif feature_name == 'chief_complaint_category':
                # For now, use hash encoding (in production, use trained encoder)
                feature_dict[feature_name] = hash(value) % 100 if value else 0
            
            elif feature_name in ['arrival_mode', 'mental_status']:
                # Simple encoding for categorical features
                feature_dict[feature_name] = hash(value) % 10 if value else 0
            
            elif feature_name.startswith('is_missing_'):
                # Convert boolean to int
                feature_dict[feature_name] = int(value) if value is not None else 0
            
            else:
                # Numeric features
                feature_dict[feature_name] = value if value is not None else 0.0
        
        # Create DataFrame
        df = pd.DataFrame([feature_dict])
        
        return df
    
    def generate_shap_values(
        self, 
        preprocessed_features: Dict[str, Any]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate SHAP values for a single prediction.
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
            
        Returns:
            Tuple of (shap_values, base_value)
            - shap_values: Array of SHAP values for each feature
            - base_value: Model's base prediction
        """
        if self.explainer is None:
            # Mock SHAP values for prototype (based on heuristics)
            return self._generate_mock_shap_values(preprocessed_features)
        
        # Prepare features
        X = self._prepare_features_for_shap(preprocessed_features)
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(X)
        
        # For multi-class (ESI 1-5), shap_values is a list of arrays
        # Return the SHAP values for the predicted class
        if isinstance(shap_values, list):
            # Get predicted class
            prediction = self.model.predict(X)[0]
            shap_values_for_class = shap_values[prediction - 1]  # ESI 1-5 -> index 0-4
        else:
            shap_values_for_class = shap_values
        
        # Get base value (expected value)
        base_value = self.explainer.expected_value
        if isinstance(base_value, list):
            base_value = base_value[0]
        
        return shap_values_for_class[0], base_value
    
    def _generate_mock_shap_values(
        self, 
        preprocessed_features: Dict[str, Any]
    ) -> Tuple[np.ndarray, float]:
        """
        Generate mock SHAP values based on heuristics (for prototype).
        
        This is a fallback when no trained model is available.
        Uses clinical heuristics to estimate feature importance.
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
            
        Returns:
            Tuple of (shap_values, base_value)
        """
        # Base value (expected log-odds for ESI 3)
        base_value = 0.0
        
        # Initialize SHAP values to zero
        shap_values = np.zeros(len(self.feature_names))
        
        # Create feature index mapping
        feature_idx = {name: i for i, name in enumerate(self.feature_names)}
        
        # Age contribution
        age = preprocessed_features.get('age', 40)
        if age > 65:
            shap_values[feature_idx['age']] = 0.3  # Increases urgency
        elif age < 3:
            shap_values[feature_idx['age']] = 0.4  # High urgency for infants
        else:
            shap_values[feature_idx['age']] = 0.0  # Neutral
        
        # Vital deviations (most important features)
        hr_deviation = preprocessed_features.get('hr_deviation', 0.0)
        if hr_deviation is not None and abs(hr_deviation) > 1.0:
            shap_values[feature_idx['hr_deviation']] = hr_deviation * 0.4  # Strong signal
        
        spo2_deviation = preprocessed_features.get('spo2_deviation', 0.0)
        if spo2_deviation is not None and spo2_deviation < -0.5:
            shap_values[feature_idx['spo2_deviation']] = spo2_deviation * 0.5  # Critical signal
        
        bp_systolic_deviation = preprocessed_features.get('bp_systolic_deviation', 0.0)
        if bp_systolic_deviation is not None and abs(bp_systolic_deviation) > 1.0:
            shap_values[feature_idx['bp_systolic_deviation']] = bp_systolic_deviation * 0.3
        
        rr_deviation = preprocessed_features.get('rr_deviation', 0.0)
        if rr_deviation is not None and abs(rr_deviation) > 1.0:
            shap_values[feature_idx['rr_deviation']] = rr_deviation * 0.35
        
        # Chief complaint category
        chief_complaint = preprocessed_features.get('chief_complaint_category', '')
        if 'chest_pain_cardiac' in chief_complaint:
            shap_values[feature_idx['chief_complaint_category']] = 0.5
        elif 'respiratory_distress' in chief_complaint:
            shap_values[feature_idx['chief_complaint_category']] = 0.45
        elif 'stroke' in chief_complaint:
            shap_values[feature_idx['chief_complaint_category']] = 0.6
        elif 'trauma_severe' in chief_complaint:
            shap_values[feature_idx['chief_complaint_category']] = 0.55
        elif 'fever' in chief_complaint or 'cold_flu' in chief_complaint:
            shap_values[feature_idx['chief_complaint_category']] = -0.3
        
        # Pain score
        pain_score = preprocessed_features.get('pain_score')
        if pain_score is not None and pain_score > 7:
            shap_values[feature_idx['pain_score']] = 0.2
        
        # Data completeness
        data_completeness = preprocessed_features.get('data_completeness_score', 75.0)
        if data_completeness < 60:
            shap_values[feature_idx['data_completeness_score']] = -0.15  # Reduces confidence
        
        # Arrival mode
        arrival_mode = preprocessed_features.get('arrival_mode', '')
        if arrival_mode == 'ambulance':
            shap_values[feature_idx['arrival_mode']] = 0.25
        
        # Mental status
        mental_status = preprocessed_features.get('mental_status', 'alert')
        if mental_status != 'alert':
            shap_values[feature_idx['mental_status']] = 0.35
        
        return shap_values, base_value
    
    def get_top_features(
        self, 
        shap_values: np.ndarray, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top k contributing features by absolute SHAP value.
        
        Args:
            shap_values: Array of SHAP values for each feature
            k: Number of top features to return
            
        Returns:
            List of dicts with feature info:
            [
                {
                    'feature': 'hr_deviation',
                    'value': 1.5,
                    'shap_value': 0.42,
                    'direction': 'increases urgency',
                    'severity': 'critical'
                },
                ...
            ]
        """
        # Get absolute values for ranking
        abs_shap_values = np.abs(shap_values)
        
        # Get top k indices
        top_indices = np.argsort(abs_shap_values)[-k:][::-1]  # Descending order
        
        top_features = []
        for idx in top_indices:
            feature_name = self.feature_names[idx]
            shap_val = float(shap_values[idx])
            
            # Skip features with zero contribution
            if abs(shap_val) < 0.01:
                continue
            
            # Determine direction
            direction = "increases urgency" if shap_val > 0 else "decreases urgency"
            
            # Determine severity
            abs_val = abs(shap_val)
            if abs_val > 0.4:
                severity = "critical"
            elif abs_val > 0.2:
                severity = "concerning"
            else:
                severity = "normal"
            
            top_features.append({
                'feature': feature_name,
                'shap_value': shap_val,
                'direction': direction,
                'severity': severity,
            })
        
        return top_features
    
    def format_natural_language_explanation(
        self,
        top_features: List[Dict[str, Any]],
        preprocessed_features: Dict[str, Any],
        predicted_esi: int
    ) -> str:
        """
        Format SHAP explanation as natural language.
        
        Args:
            top_features: List of top contributing features from get_top_features()
            preprocessed_features: Original features for value lookup
            predicted_esi: Predicted ESI level
            
        Returns:
            Human-readable explanation string
            
        Example:
            "The model predicts ESI 2 based primarily on elevated heart rate (120 bpm, +50% above normal), 
            chest pain presentation, and patient age over 50. These factors strongly suggest cardiac evaluation."
        """
        if not top_features:
            return f"The model predicts ESI {predicted_esi} based on overall patient presentation."
        
        # Build explanation parts
        explanation_parts = []
        
        for i, feature in enumerate(top_features[:5]):  # Top 5
            feature_name = feature['feature']
            direction = feature['direction']
            shap_val = feature['shap_value']
            severity = feature['severity']
            
            # Get feature value
            feature_value = preprocessed_features.get(feature_name)
            
            # Format feature-specific explanation
            if feature_name == 'hr_deviation':
                hr = preprocessed_features.get('hr')
                if hr:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"heart rate of {hr} bpm ({direction.replace('increases urgency', 'elevated').replace('decreases urgency', 'normal')}, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'spo2_deviation':
                spo2 = preprocessed_features.get('spo2')
                if spo2:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"oxygen saturation of {spo2}% ({direction.replace('increases urgency', 'low').replace('decreases urgency', 'normal')}, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'bp_systolic_deviation':
                bp = preprocessed_features.get('bp_systolic')
                if bp:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"systolic blood pressure of {bp} mmHg ({direction.replace('increases urgency', 'abnormal').replace('decreases urgency', 'normal')}, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'rr_deviation':
                rr = preprocessed_features.get('rr')
                if rr:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"respiratory rate of {rr}/min ({direction.replace('increases urgency', 'elevated').replace('decreases urgency', 'normal')}, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'age':
                age = preprocessed_features.get('age')
                if age:
                    percent_change = abs(shap_val) * 100
                    if age > 65:
                        explanation_parts.append(
                            f"patient age {age} years (geriatric population at higher risk, contributing {percent_change:.0f}% to urgency)"
                        )
                    elif age < 3:
                        explanation_parts.append(
                            f"patient age {age} years (pediatric infant requiring closer monitoring, contributing {percent_change:.0f}% to urgency)"
                        )
            
            elif feature_name == 'chief_complaint_category':
                complaint = preprocessed_features.get('chief_complaint_category', '')
                if complaint:
                    percent_change = abs(shap_val) * 100
                    complaint_display = complaint.replace('_', ' ').title()
                    explanation_parts.append(
                        f"chief complaint of '{complaint_display}' (contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'pain_score':
                pain = preprocessed_features.get('pain_score')
                if pain:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"pain score of {pain}/10 (severe pain, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'mental_status':
                mental = preprocessed_features.get('mental_status', '')
                if mental and mental != 'alert':
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"altered mental status ({mental}, contributing {percent_change:.0f}% to urgency)"
                    )
            
            elif feature_name == 'arrival_mode':
                arrival = preprocessed_features.get('arrival_mode', '')
                if arrival == 'ambulance':
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"arrival by ambulance (indicating pre-hospital assessment of urgency, contributing {percent_change:.0f}%)"
                    )
            
            elif feature_name == 'data_completeness_score':
                completeness = preprocessed_features.get('data_completeness_score', 100)
                if completeness < 70:
                    percent_change = abs(shap_val) * 100
                    explanation_parts.append(
                        f"incomplete data ({completeness:.0f}% complete, reducing confidence by {percent_change:.0f}%)"
                    )
        
        # Construct final explanation
        if explanation_parts:
            main_factors = ", ".join(explanation_parts[:3])  # Top 3
            additional = ""
            if len(explanation_parts) > 3:
                additional = f" Additional contributing factors include {', '.join(explanation_parts[3:])}."
            
            explanation = f"The model predicts ESI {predicted_esi} based primarily on {main_factors}.{additional}"
        else:
            explanation = f"The model predicts ESI {predicted_esi} based on overall patient presentation."
        
        return explanation
    
    def explain_prediction(
        self,
        preprocessed_features: Dict[str, Any],
        predicted_esi: int,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate complete SHAP explanation for a prediction.
        
        This is the main method to use for generating explanations.
        
        Args:
            preprocessed_features: Features from preprocessing pipeline
            predicted_esi: Predicted ESI level (1-5)
            k: Number of top features to include
            
        Returns:
            Dictionary with:
            {
                'shap_explanation': [
                    {
                        'feature_name': str,
                        'feature_value': Any,
                        'shap_value': float,
                        'direction': str,
                        'severity': str
                    },
                    ...
                ],
                'explanation_text': str,
                'base_value': float
            }
        """
        # Generate SHAP values
        shap_values, base_value = self.generate_shap_values(preprocessed_features)
        
        # Get top features
        top_features = self.get_top_features(shap_values, k=k)
        
        # Add feature values to top features
        for feature in top_features:
            feature_name = feature['feature']
            feature['feature_value'] = preprocessed_features.get(feature_name)
        
        # Generate natural language explanation
        explanation_text = self.format_natural_language_explanation(
            top_features, 
            preprocessed_features, 
            predicted_esi
        )
        
        return {
            'shap_explanation': top_features,
            'explanation_text': explanation_text,
            'base_value': float(base_value)
        }


# ============================================================================
# Utility Functions
# ============================================================================

def load_model_and_create_explainer(model_path: Optional[str] = None) -> SHAPExplainer:
    """
    Load trained model and create SHAP explainer.
    
    Args:
        model_path: Path to trained CatBoost model (.cbm file)
        
    Returns:
        Initialized SHAPExplainer
    """
    model = None
    
    if model_path and Path(model_path).exists():
        try:
            from catboost import CatBoostClassifier
            model = CatBoostClassifier()
            model.load_model(model_path)
            print(f"✓ Loaded model from {model_path}")
        except Exception as e:
            print(f"Warning: Could not load model from {model_path}: {e}")
            print("Using mock SHAP values for prototype")
    else:
        print("No model path provided or model not found. Using mock SHAP values for prototype.")
    
    explainer = SHAPExplainer(model=model)
    
    return explainer


if __name__ == '__main__':
    # Example usage and testing
    print("SHAP Explainer Test\n")
    
    # Create explainer (without trained model, uses mock)
    explainer = SHAPExplainer()
    
    # Test case 1: Adult with chest pain
    print("Test 1: Adult with chest pain (high-risk presentation)")
    test_features_1 = {
        'age': 55,
        'age_group': 'adult_18_64',
        'sex': 'male',
        'hr': 120,
        'hr_deviation': 1.0,  # Significantly elevated
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
        'is_missing_temperature': False,
        'is_missing_pain_score': False,
        'is_missing_medical_history': False,
    }
    
    explanation_1 = explainer.explain_prediction(test_features_1, predicted_esi=2)
    print(f"Explanation: {explanation_1['explanation_text']}")
    print("\nTop features:")
    for feat in explanation_1['shap_explanation'][:3]:
        print(f"  - {feat['feature']}: {feat['shap_value']:.3f} ({feat['direction']})")
    print()
    
    # Test case 2: Pediatric with fever
    print("Test 2: Pediatric infant with fever (normal vitals for age)")
    test_features_2 = {
        'age': 1,
        'age_group': 'infant_0_2',
        'sex': 'female',
        'hr': 140,
        'hr_deviation': 0.0,  # Normal for infant
        'bp_systolic': 85,
        'bp_systolic_deviation': 0.0,
        'spo2': 98,
        'spo2_deviation': 0.0,
        'rr': 35,
        'rr_deviation': 0.0,
        'temperature': 38.5,
        'temperature_deviation': 1.0,
        'chief_complaint_category': 'fever_high',
        'pain_score': None,
        'arrival_mode': 'walk_in',
        'mental_status': 'alert',
        'data_completeness_score': 75.0,
        'is_missing_temperature': False,
        'is_missing_pain_score': True,
        'is_missing_medical_history': True,
    }
    
    explanation_2 = explainer.explain_prediction(test_features_2, predicted_esi=3)
    print(f"Explanation: {explanation_2['explanation_text']}")
    print("\nTop features:")
    for feat in explanation_2['shap_explanation'][:3]:
        print(f"  - {feat['feature']}: {feat['shap_value']:.3f} ({feat['direction']})")
    print()
    
    # Test case 3: Low urgency presentation
    print("Test 3: Adult with minor complaint (low urgency)")
    test_features_3 = {
        'age': 30,
        'age_group': 'adult_18_64',
        'sex': 'female',
        'hr': 75,
        'hr_deviation': -0.1,
        'bp_systolic': 120,
        'bp_systolic_deviation': 0.0,
        'spo2': 99,
        'spo2_deviation': 0.0,
        'rr': 14,
        'rr_deviation': 0.0,
        'chief_complaint_category': 'cold_flu_symptoms',
        'pain_score': 2,
        'arrival_mode': 'walk_in',
        'mental_status': 'alert',
        'data_completeness_score': 85.0,
        'is_missing_temperature': False,
        'is_missing_pain_score': False,
        'is_missing_medical_history': False,
    }
    
    explanation_3 = explainer.explain_prediction(test_features_3, predicted_esi=4)
    print(f"Explanation: {explanation_3['explanation_text']}")
    print("\nTop features:")
    for feat in explanation_3['shap_explanation'][:3]:
        print(f"  - {feat['feature']}: {feat['shap_value']:.3f} ({feat['direction']})")
    print()
    
    print("✅ SHAP Explainer test complete!")
