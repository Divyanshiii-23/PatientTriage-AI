"""
Validation script for SHAP Explainer (Task 2.3).

Validates:
- SHAP value generation
- Top 5 feature extraction
- Natural language explanation formatting
- Integration with preprocessing pipeline

Requirements: 3.8, 3.9
"""

import sys
sys.path.insert(0, '/Users/divyanshiii/Win')

from src.explainer import SHAPExplainer
from src.preprocessing import preprocess_patient_data


def test_explainer_basic():
    """Test basic explainer functionality."""
    print("=" * 60)
    print("Test 1: Basic Explainer Functionality")
    print("=" * 60)
    
    explainer = SHAPExplainer()
    
    # Check initialization
    assert explainer is not None, "Explainer failed to initialize"
    assert len(explainer.feature_names) > 0, "No feature names defined"
    
    print(f"✓ Explainer initialized successfully")
    print(f"✓ Feature names defined: {len(explainer.feature_names)} features")
    print()


def test_top_features_extraction():
    """Test top feature extraction."""
    print("=" * 60)
    print("Test 2: Top Features Extraction")
    print("=" * 60)
    
    explainer = SHAPExplainer()
    
    # Create test features
    test_features = {
        'age': 55,
        'age_group': 'adult_18_64',
        'sex': 'male',
        'hr': 120,
        'hr_deviation': 1.5,
        'bp_systolic': 90,
        'bp_systolic_deviation': -1.0,
        'spo2': 98,
        'spo2_deviation': 0.1,
        'rr': 18,
        'rr_deviation': 0.0,
        'chief_complaint_category': 'chest_pain_cardiac',
        'pain_score': 8,
        'arrival_mode': 'ambulance',
        'mental_status': 'alert',
        'data_completeness_score': 90.0,
    }
    
    # Generate SHAP values
    shap_values, base_value = explainer.generate_shap_values(test_features)
    
    assert len(shap_values) == len(explainer.feature_names), \
        f"SHAP values length mismatch: {len(shap_values)} != {len(explainer.feature_names)}"
    
    print(f"✓ Generated SHAP values for {len(shap_values)} features")
    print(f"✓ Base value: {base_value:.3f}")
    
    # Get top 5 features
    top_features = explainer.get_top_features(shap_values, k=5)
    
    assert len(top_features) <= 5, f"Too many top features returned: {len(top_features)}"
    assert len(top_features) > 0, "No top features returned"
    
    print(f"✓ Extracted top {len(top_features)} contributing features")
    
    # Check feature structure
    for i, feature in enumerate(top_features[:3]):
        assert 'feature' in feature, "Missing 'feature' key"
        assert 'shap_value' in feature, "Missing 'shap_value' key"
        assert 'direction' in feature, "Missing 'direction' key"
        assert 'severity' in feature, "Missing 'severity' key"
        
        print(f"  {i+1}. {feature['feature']}: {feature['shap_value']:.3f} ({feature['direction']}, {feature['severity']})")
    
    print()


def test_natural_language_explanation():
    """Test natural language explanation generation."""
    print("=" * 60)
    print("Test 3: Natural Language Explanation")
    print("=" * 60)
    
    explainer = SHAPExplainer()
    
    # High-urgency case
    test_features = {
        'age': 55,
        'age_group': 'adult_18_64',
        'sex': 'male',
        'hr': 120,
        'hr_deviation': 1.5,
        'bp_systolic': 90,
        'bp_systolic_deviation': -1.0,
        'spo2': 98,
        'spo2_deviation': 0.1,
        'rr': 18,
        'rr_deviation': 0.0,
        'chief_complaint_category': 'chest_pain_cardiac',
        'pain_score': 8,
        'arrival_mode': 'ambulance',
        'mental_status': 'alert',
        'data_completeness_score': 90.0,
    }
    
    result = explainer.explain_prediction(test_features, predicted_esi=2, k=5)
    
    assert 'explanation_text' in result, "Missing 'explanation_text' in result"
    assert 'shap_explanation' in result, "Missing 'shap_explanation' in result"
    assert 'base_value' in result, "Missing 'base_value' in result"
    
    explanation_text = result['explanation_text']
    assert len(explanation_text) > 0, "Empty explanation text"
    assert "ESI 2" in explanation_text, "Explanation doesn't mention predicted ESI"
    
    print(f"✓ Generated natural language explanation")
    print(f"\nExplanation:\n{explanation_text}\n")
    
    # Check top features have values
    for feature in result['shap_explanation']:
        assert 'feature_value' in feature, f"Missing 'feature_value' for {feature['feature']}"
    
    print(f"✓ All top features include values")
    print()


def test_integration_with_preprocessing():
    """Test integration with preprocessing pipeline."""
    print("=" * 60)
    print("Test 4: Integration with Preprocessing Pipeline")
    print("=" * 60)
    
    # Create raw patient data
    raw_patient = {
        'demographics': {'age': 45, 'sex': 'male'},
        'vitals': {
            'hr': 120,
            'bp_systolic': 90,
            'bp_diastolic': 60,
            'spo2': 98,
            'rr': 18,
            'temperature': 38.5,
        },
        'clinical': {
            'chief_complaint': 'chest pain radiating to left arm',
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 8,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
        },
        'symptoms': ['chest_pain', 'shortness_of_breath'],
        'medical_history': {'hypertension': True},
    }
    
    # Preprocess
    preprocessed = preprocess_patient_data(raw_patient)
    
    print(f"✓ Preprocessed patient data")
    print(f"  Age group: {preprocessed['age_group']}")
    print(f"  HR: {preprocessed['hr']} bpm (deviation: {preprocessed['hr_deviation']:.2f})")
    print(f"  Data completeness: {preprocessed['data_completeness_score']:.1f}%")
    
    # Generate explanation
    explainer = SHAPExplainer()
    result = explainer.explain_prediction(preprocessed, predicted_esi=2, k=5)
    
    print(f"\n✓ Generated SHAP explanation from preprocessed data")
    print(f"\nTop 3 Contributing Factors:")
    for i, feature in enumerate(result['shap_explanation'][:3]):
        print(f"  {i+1}. {feature['feature']}: {feature['shap_value']:.3f} ({feature['direction']})")
    
    print()


def test_multiple_scenarios():
    """Test explainer on multiple clinical scenarios."""
    print("=" * 60)
    print("Test 5: Multiple Clinical Scenarios")
    print("=" * 60)
    
    explainer = SHAPExplainer()
    
    scenarios = [
        {
            'name': 'High Urgency - Chest Pain',
            'features': {
                'age': 55,
                'hr': 120,
                'hr_deviation': 1.5,
                'spo2': 96,
                'spo2_deviation': -0.3,
                'chief_complaint_category': 'chest_pain_cardiac',
                'pain_score': 8,
                'arrival_mode': 'ambulance',
                'data_completeness_score': 90.0,
            },
            'predicted_esi': 2,
        },
        {
            'name': 'Pediatric - Fever',
            'features': {
                'age': 1,
                'age_group': 'infant_0_2',
                'hr': 140,
                'hr_deviation': 0.0,
                'spo2': 98,
                'spo2_deviation': 0.0,
                'chief_complaint_category': 'fever_high',
                'data_completeness_score': 75.0,
            },
            'predicted_esi': 3,
        },
        {
            'name': 'Low Urgency - Cold/Flu',
            'features': {
                'age': 30,
                'hr': 75,
                'hr_deviation': 0.0,
                'spo2': 99,
                'spo2_deviation': 0.0,
                'chief_complaint_category': 'cold_flu_symptoms',
                'arrival_mode': 'walk_in',
                'data_completeness_score': 85.0,
            },
            'predicted_esi': 4,
        },
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 40)
        
        result = explainer.explain_prediction(
            scenario['features'], 
            predicted_esi=scenario['predicted_esi']
        )
        
        print(f"Predicted ESI: {scenario['predicted_esi']}")
        print(f"Top factors:")
        for i, feature in enumerate(result['shap_explanation'][:3]):
            print(f"  {i+1}. {feature['feature']}: {feature['shap_value']:.2f}")
        
        assert len(result['explanation_text']) > 0, f"Empty explanation for {scenario['name']}"
        print(f"✓ Explanation generated successfully")
    
    print(f"\n✓ All {len(scenarios)} scenarios processed successfully")
    print()


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("SHAP Explainer Validation (Task 2.3)")
    print("=" * 60)
    print()
    
    try:
        test_explainer_basic()
        test_top_features_extraction()
        test_natural_language_explanation()
        test_integration_with_preprocessing()
        test_multiple_scenarios()
        
        print("=" * 60)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✓ SHAP explainer initialization")
        print("  ✓ SHAP value generation")
        print("  ✓ Top 5 feature extraction")
        print("  ✓ Natural language formatting")
        print("  ✓ Integration with preprocessing pipeline")
        print("  ✓ Multiple clinical scenarios")
        print()
        print("Task 2.3 Complete: SHAP explainer implemented successfully")
        print("Requirements 3.8, 3.9 validated")
        print()
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ VALIDATION FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
