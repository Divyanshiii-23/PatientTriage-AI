#!/usr/bin/env python3
"""
Simple test script for preprocessing pipeline (no pytest required).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from preprocessing import (
    classify_age_group,
    compute_vital_deviation,
    compute_data_completeness,
    preprocess_patient_data,
    get_feature_names,
)


def test_age_classification():
    """Test age group classification."""
    print("Testing age group classification...")
    
    assert classify_age_group(0) == 'infant_0_2', "Failed: age 0"
    assert classify_age_group(2) == 'infant_0_2', "Failed: age 2"
    assert classify_age_group(5) == 'child_3_12', "Failed: age 5"
    assert classify_age_group(12) == 'child_3_12', "Failed: age 12"
    assert classify_age_group(15) == 'adolescent_13_17', "Failed: age 15"
    assert classify_age_group(17) == 'adolescent_13_17', "Failed: age 17"
    assert classify_age_group(25) == 'adult_18_64', "Failed: age 25"
    assert classify_age_group(64) == 'adult_18_64', "Failed: age 64"
    assert classify_age_group(70) == 'geriatric_65_plus', "Failed: age 70"
    
    print("  ✓ Age classification works correctly")


def test_vital_deviations():
    """Test vital deviation calculations."""
    print("\nTesting vital deviations...")
    
    # Adult HR at midpoint (80) should be 0
    dev = compute_vital_deviation(80, 'hr', 'adult_18_64')
    assert abs(dev) < 0.01, f"Expected ~0, got {dev}"
    
    # Adult HR 120 should be elevated (deviation ~1.0)
    dev = compute_vital_deviation(120, 'hr', 'adult_18_64')
    assert abs(dev - 1.0) < 0.01, f"Expected ~1.0, got {dev}"
    
    # Infant HR 140 should be slightly elevated but normal (deviation ~0.17)
    dev = compute_vital_deviation(140, 'hr', 'infant_0_2')
    assert abs(dev - 0.167) < 0.05, f"Expected ~0.17, got {dev}"
    
    # Compare adult vs infant for same HR value
    adult_dev = compute_vital_deviation(140, 'hr', 'adult_18_64')
    infant_dev = compute_vital_deviation(140, 'hr', 'infant_0_2')
    assert adult_dev > infant_dev, f"Adult deviation ({adult_dev}) should be > infant ({infant_dev})"
    
    # SpO2 normal should be 0
    dev = compute_vital_deviation(98, 'spo2', 'adult_18_64')
    assert dev == 0.0, f"SpO2 98 should have 0 deviation, got {dev}"
    
    # SpO2 low should be negative
    dev = compute_vital_deviation(90, 'spo2', 'adult_18_64')
    assert dev < 0, f"SpO2 90 should have negative deviation, got {dev}"
    
    # Missing vital should return None
    dev = compute_vital_deviation(None, 'hr', 'adult_18_64')
    assert dev is None, f"Missing vital should return None, got {dev}"
    
    print("  ✓ Vital deviations calculated correctly")


def test_data_completeness():
    """Test data completeness score."""
    print("\nTesting data completeness...")
    
    # Complete patient
    complete_patient = {
        'demographics': {'age': 45, 'sex': 'male'},
        'vitals': {
            'hr': 80, 'bp_systolic': 120, 'bp_diastolic': 80,
            'spo2': 98, 'rr': 16, 'temperature': 37.0,
        },
        'clinical': {
            'chief_complaint': 'chest pain',
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 7,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
        },
        'symptoms': ['chest_pain'],
        'medical_history': {'hypertension': True},
        'observations': ['distress'],
    }
    
    score = compute_data_completeness(complete_patient)
    assert score == 100.0, f"Complete data should score 100%, got {score}"
    
    # Minimal patient (only required fields)
    minimal_patient = {
        'demographics': {'age': 45, 'sex': 'male'},
        'vitals': {
            'hr': 80, 'bp_systolic': 120, 'bp_diastolic': 80,
            'spo2': 98, 'rr': 16,
        },
        'clinical': {
            'chief_complaint': 'chest pain',
            'chief_complaint_category': 'chest_pain_cardiac',
        },
    }
    
    score = compute_data_completeness(minimal_patient)
    assert 50.0 < score < 80.0, f"Minimal data should score 50-80%, got {score}"
    
    print(f"  ✓ Data completeness: complete={100.0}%, minimal={score:.1f}%")


def test_full_preprocessing():
    """Test full preprocessing pipeline."""
    print("\nTesting full preprocessing pipeline...")
    
    # Test Case 1: Adult with complete data
    adult_patient = {
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
            'chief_complaint': 'chest pain',
            'chief_complaint_category': 'chest_pain_cardiac',
            'pain_score': 8,
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
        },
        'symptoms': ['chest_pain', 'shortness_of_breath'],
        'medical_history': {'hypertension': True},
        'observations': ['visible_distress'],
    }
    
    features = preprocess_patient_data(adult_patient)
    
    # Verify age group
    assert features['age'] == 45, f"Age should be 45, got {features['age']}"
    assert features['age_group'] == 'adult_18_64', f"Age group should be adult_18_64, got {features['age_group']}"
    
    # Verify raw vitals preserved
    assert features['hr'] == 120, f"HR should be 120, got {features['hr']}"
    assert features['spo2'] == 98, f"SpO2 should be 98, got {features['spo2']}"
    
    # Verify deviations calculated
    assert features['hr_deviation'] is not None, "HR deviation should not be None"
    assert features['hr_deviation'] > 0, f"HR 120 should have positive deviation, got {features['hr_deviation']}"
    assert features['bp_systolic_deviation'] < 0, f"BP 90 should have negative deviation, got {features['bp_systolic_deviation']}"
    
    # Verify missing indicators
    assert features['is_missing_hr'] is False, "HR should not be missing"
    assert features['is_missing_temperature'] is False, "Temperature should not be missing"
    
    # Verify data completeness
    assert features['data_completeness_score'] > 90.0, f"Complete data should score >90%, got {features['data_completeness_score']}"
    
    # Verify pass-through fields
    assert features['sex'] == 'male', f"Sex should be male, got {features['sex']}"
    assert features['pain_score'] == 8, f"Pain score should be 8, got {features['pain_score']}"
    assert len(features['symptoms']) == 2, f"Should have 2 symptoms, got {len(features['symptoms'])}"
    
    print("  ✓ Adult patient preprocessing works")
    
    # Test Case 2: Infant with normal vitals
    infant_patient = {
        'demographics': {'age': 1, 'sex': 'female'},
        'vitals': {
            'hr': 140,  # Normal for infant
            'bp_systolic': 85,
            'bp_diastolic': 55,
            'spo2': 97,
            'rr': 40,
        },
        'clinical': {
            'chief_complaint': 'fever',
            'chief_complaint_category': 'fever_high',
        },
        'symptoms': ['fever'],
        'medical_history': {},
    }
    
    features = preprocess_patient_data(infant_patient)
    
    assert features['age_group'] == 'infant_0_2', f"Should be infant, got {features['age_group']}"
    assert abs(features['hr_deviation']) < 0.5, f"HR 140 should be normal for infant, deviation={features['hr_deviation']}"
    
    print("  ✓ Infant patient preprocessing works")
    
    # Test Case 3: Patient with missing data
    missing_data_patient = {
        'demographics': {'age': 60, 'sex': 'male'},
        'vitals': {
            'hr': 95,
            'bp_systolic': 140,
            'bp_diastolic': 85,
            'spo2': 94,
            'rr': 18,
            # temperature missing
        },
        'clinical': {
            'chief_complaint': 'chest discomfort',
            'chief_complaint_category': 'chest_pain_cardiac',
            # pain_score missing
        },
        'symptoms': ['chest_pain'],
        'medical_history': {},
    }
    
    features = preprocess_patient_data(missing_data_patient)
    
    assert features['is_missing_temperature'] is True, "Temperature should be flagged as missing"
    assert features['is_missing_pain_score'] is True, "Pain score should be flagged as missing"
    assert features['temperature_deviation'] is None, "Missing temperature should have None deviation"
    assert features['hr_deviation'] is not None, "Present HR should have deviation"
    
    print("  ✓ Missing data handling works")


def test_age_specific_ranges():
    """Test that different age groups use different vital ranges."""
    print("\nTesting age-specific vital ranges...")
    
    # Same BP value, different ages
    bp_value = 130
    
    # Adult: 110-130 (normal range) -> at upper limit
    adult_patient = {
        'demographics': {'age': 45, 'sex': 'male'},
        'vitals': {'hr': 80, 'bp_systolic': bp_value, 'bp_diastolic': 80, 'spo2': 98, 'rr': 16},
        'clinical': {'chief_complaint': 'test', 'chief_complaint_category': 'test'},
    }
    
    # Geriatric: 120-140 (normal range) -> at midpoint
    geriatric_patient = {
        'demographics': {'age': 75, 'sex': 'male'},
        'vitals': {'hr': 80, 'bp_systolic': bp_value, 'bp_diastolic': 80, 'spo2': 93, 'rr': 16},
        'clinical': {'chief_complaint': 'test', 'chief_complaint_category': 'test'},
    }
    
    adult_features = preprocess_patient_data(adult_patient)
    geriatric_features = preprocess_patient_data(geriatric_patient)
    
    # BP 130 should be more abnormal for adult than geriatric
    print(f"  Adult BP 130 deviation: {adult_features['bp_systolic_deviation']:.2f}")
    print(f"  Geriatric BP 130 deviation: {geriatric_features['bp_systolic_deviation']:.2f}")
    
    assert adult_features['bp_systolic_deviation'] > geriatric_features['bp_systolic_deviation'], \
        "Adult should have higher deviation than geriatric for BP 130"
    
    print("  ✓ Age-specific ranges work correctly")


def test_feature_names():
    """Test feature names utility."""
    print("\nTesting feature names utility...")
    
    names = get_feature_names()
    
    assert isinstance(names, list), "Feature names should be a list"
    assert len(names) > 20, f"Should have >20 features, got {len(names)}"
    
    # Check key features present
    key_features = ['age', 'age_group', 'hr', 'hr_deviation', 'is_missing_hr', 'data_completeness_score']
    for feature in key_features:
        assert feature in names, f"Feature '{feature}' should be in feature names"
    
    print(f"  ✓ Feature names: {len(names)} features defined")


def main():
    """Run all tests."""
    print("="*60)
    print("PREPROCESSING PIPELINE TEST SUITE")
    print("="*60)
    
    try:
        test_age_classification()
        test_vital_deviations()
        test_data_completeness()
        test_full_preprocessing()
        test_age_specific_ranges()
        test_feature_names()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
