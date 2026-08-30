"""
Example: Complete confidence scoring integration with preprocessing pipeline.

This example demonstrates how to:
1. Load patient data
2. Preprocess features
3. Generate mock prediction probabilities
4. Compute 4-dimensional confidence scores
5. Display results

Requirements: 2.4, 3.3, 3.4, 8.1-8.9
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing import preprocess_patient_data
from src.confidence import ConfidenceScorer


def mock_ml_prediction(preprocessed_features):
    """
    Mock ML model prediction for demonstration.
    
    In production, this would be replaced with actual CatBoost model inference.
    """
    # Simple heuristic for ESI prediction
    esi_pred = 3  # Default
    
    # Critical indicators → ESI 1-2
    hr_dev = preprocessed_features.get('hr_deviation', 0.0) or 0.0
    spo2_dev = preprocessed_features.get('spo2_deviation', 0.0) or 0.0
    bp_sys_dev = preprocessed_features.get('bp_systolic_deviation', 0.0) or 0.0
    
    if spo2_dev < -3.0:  # Very low SpO2
        esi_pred = 1
    elif abs(hr_dev) > 2.0 or abs(spo2_dev) > 2.0:
        esi_pred = 2
    elif abs(hr_dev) < 0.5 and abs(spo2_dev) < 0.5 and abs(bp_sys_dev) < 0.5:
        esi_pred = 4  # Very stable vitals
    
    # Generate probability distribution (peaked around prediction)
    probs = [0.05, 0.10, 0.15, 0.40, 0.30]
    probs[esi_pred - 1] = 0.60  # Peak at prediction
    
    # Normalize
    prob_sum = sum(probs)
    probability_distribution = [p / prob_sum for p in probs]
    
    return esi_pred, probability_distribution


def demonstrate_confidence_scoring(patient_data, patient_name="Patient"):
    """
    Complete demonstration of confidence scoring pipeline.
    
    Args:
        patient_data: Raw patient data dictionary
        patient_name: Name for display purposes
    """
    print(f"\n{'=' * 70}")
    print(f"Confidence Scoring Demo: {patient_name}")
    print(f"{'=' * 70}\n")
    
    # Step 1: Preprocess patient data
    print("Step 1: Preprocessing patient data...")
    preprocessed_features = preprocess_patient_data(patient_data)
    print(f"  ✓ Age group: {preprocessed_features['age_group']}")
    print(f"  ✓ Data completeness: {preprocessed_features['data_completeness_score']:.1f}%")
    print()
    
    # Step 2: Generate ML prediction (mock)
    print("Step 2: Generating ESI prediction...")
    esi_pred, probability_distribution = mock_ml_prediction(preprocessed_features)
    print(f"  ✓ Predicted ESI: {esi_pred}")
    print(f"  ✓ Probability distribution:")
    for i, prob in enumerate(probability_distribution, 1):
        print(f"      ESI {i}: {prob:.2%}")
    print()
    
    # Step 3: Compute confidence scores
    print("Step 3: Computing multi-dimensional confidence...")
    scorer = ConfidenceScorer()
    confidence = scorer.score_prediction(
        probability_distribution=probability_distribution,
        preprocessed_features=preprocessed_features,
        patient_data=patient_data
    )
    
    print(f"  📊 Confidence Breakdown:")
    print(f"      Model Certainty:        {confidence['model_certainty']:.1f}/100")
    print(f"      Data Completeness:      {confidence['data_completeness']:.1f}/100")
    print(f"      Clinical Consistency:   {confidence['clinical_consistency']:.1f}/100")
    print(f"      Pattern Recognition:    {confidence['pattern_recognition']:.1f}/100")
    print()
    print(f"  🎯 Overall Confidence:      {confidence['overall_score']:.1f}/100")
    print(f"  📌 Confidence Level:        {confidence['confidence_level']}")
    print()
    
    # Step 4: Interpretation
    print("Step 4: Confidence interpretation...")
    level = confidence['confidence_level']
    
    if level == 'HIGH':
        print("  ✅ HIGH confidence: Prediction is reliable, proceed with ML recommendation")
    elif level == 'MEDIUM':
        print("  ⚠️  MEDIUM confidence: Consider clinician review, prediction may be ambiguous")
    else:
        print("  🚨 LOW confidence: Manual assessment strongly recommended")
    
    # Identify low-scoring dimensions
    low_dimensions = []
    for dim in ['model_certainty', 'data_completeness', 'clinical_consistency', 'pattern_recognition']:
        if confidence[dim] < 60.0:
            low_dimensions.append((dim, confidence[dim]))
    
    if low_dimensions:
        print("\n  ⚠️  Low-scoring dimensions:")
        for dim_name, score in low_dimensions:
            print(f"      - {dim_name.replace('_', ' ').title()}: {score:.1f}/100")
            
            # Provide recommendations
            if dim_name == 'data_completeness':
                print("        → Recommendation: Gather additional patient information")
            elif dim_name == 'clinical_consistency':
                print("        → Recommendation: Verify symptom-vital alignment, patient may be under-reporting")
            elif dim_name == 'pattern_recognition':
                print("        → Recommendation: Unusual presentation, exercise extra caution")
            elif dim_name == 'model_certainty':
                print("        → Recommendation: Ambiguous case, consider alternative ESI levels")
    
    print()
    return confidence


def main():
    """Run confidence scoring demonstrations."""
    
    print("\n" + "=" * 70)
    print("CONFIDENCE SCORING SYSTEM DEMONSTRATION")
    print("Multi-dimensional confidence for ED triage predictions")
    print("=" * 70)
    
    # ========================================================================
    # Example 1: High confidence case
    # Typical adult with clear presentation
    # ========================================================================
    
    patient1 = {
        'demographics': {'age': 52, 'sex': 'male'},
        'vitals': {
            'hr': 115,  # Elevated
            'bp_systolic': 145,  # Elevated
            'bp_diastolic': 92,  # Elevated
            'spo2': 96,  # Normal
            'rr': 20,  # Normal
            'temperature': 37.8,  # Slight fever
        },
        'clinical': {
            'chief_complaint': 'chest pain radiating to left arm',
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 8,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
        },
        'symptoms': ['chest_pain', 'shortness_of_breath', 'diaphoresis'],
        'medical_history': {'hypertension': True, 'diabetes': False},
        'observations': ['appears_distressed'],
    }
    
    confidence1 = demonstrate_confidence_scoring(patient1, "Adult with Chest Pain (High Confidence)")
    
    # ========================================================================
    # Example 2: Low confidence case
    # Unusual presentation with missing data and inconsistencies
    # ========================================================================
    
    patient2 = {
        'demographics': {'age': 105, 'sex': 'female'},
        'vitals': {
            'hr': 185,  # Extreme tachycardia
            'bp_systolic': 70,  # Very low
            'bp_diastolic': 45,  # Very low
            'spo2': 78,  # Critically low
            'rr': 8,  # Very low (unusual)
            # temperature missing
        },
        'clinical': {
            'chief_complaint': 'feeling fine, routine checkup',  # Inconsistent!
            'chief_complaint_category': 'routine_checkup',
            # pain_score missing
            'arrival_mode': 'walk_in',
            'mental_status': 'alert',
        },
        'symptoms': [],  # No symptoms despite critical vitals!
        'medical_history': {},  # No history
        'observations': [],
    }
    
    confidence2 = demonstrate_confidence_scoring(patient2, "Unusual Presentation (Low Confidence)")
    
    # ========================================================================
    # Example 3: Medium confidence case
    # Ambiguous presentation (could be ESI 2 or 3)
    # ========================================================================
    
    patient3 = {
        'demographics': {'age': 47, 'sex': 'male'},
        'vitals': {
            'hr': 102,  # Borderline elevated
            'bp_systolic': 138,  # Borderline elevated
            'bp_diastolic': 86,  # Borderline elevated
            'spo2': 96,  # Normal
            'rr': 18,  # Normal
            'temperature': 37.1,  # Normal
        },
        'clinical': {
            'chief_complaint': 'mild chest discomfort, started 4 hours ago',
            'chief_complaint_category': 'chest_pain_atypical',
            'pain_score': 4,  # Moderate
            'arrival_mode': 'walk_in',
            'mental_status': 'alert',
        },
        'symptoms': ['chest_pain_mild'],
        'medical_history': {'hypertension': True},
        'observations': [],
    }
    
    confidence3 = demonstrate_confidence_scoring(patient3, "Ambiguous Chest Pain (Medium Confidence)")
    
    # ========================================================================
    # Summary comparison
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("SUMMARY: Confidence Comparison")
    print("=" * 70)
    print()
    print("┌" + "─" * 28 + "┬" + "─" * 13 + "┬" + "─" * 13 + "┬" + "─" * 13 + "┐")
    print("│ Patient                    │   Overall   │    Level    │  ESI Pred   │")
    print("├" + "─" * 28 + "┼" + "─" * 13 + "┼" + "─" * 13 + "┼" + "─" * 13 + "┤")
    print(f"│ Adult with Chest Pain      │    {confidence1['overall_score']:5.1f}    │    {confidence1['confidence_level']:7s}  │      2      │")
    print(f"│ Unusual Presentation       │    {confidence2['overall_score']:5.1f}    │    {confidence2['confidence_level']:7s}  │      1      │")
    print(f"│ Ambiguous Chest Pain       │    {confidence3['overall_score']:5.1f}    │    {confidence3['confidence_level']:7s}  │      2      │")
    print("└" + "─" * 28 + "┴" + "─" * 13 + "┴" + "─" * 13 + "┴" + "─" * 13 + "┘")
    print()
    
    print("Key Insights:")
    print("  • HIGH confidence (>80%): Clear presentation, complete data, consistent symptoms")
    print("  • MEDIUM confidence (60-80%): Ambiguous cases, borderline vitals, incomplete data")
    print("  • LOW confidence (<60%): Extreme outliers, inconsistent data, unusual presentations")
    print()
    print("✅ Confidence scoring system demonstration complete!")
    print()


if __name__ == '__main__':
    main()
