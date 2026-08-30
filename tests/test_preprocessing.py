"""
Unit tests for preprocessing pipeline.

Tests:
- Age group classification
- Vital deviation calculation (age-specific)
- Missing data handling
- Data completeness score
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from preprocessing import (
    classify_age_group,
    compute_vital_deviation,
    compute_data_completeness,
    preprocess_patient_data,
    get_feature_names,
)


class TestAgeGroupClassification:
    """Test age group classification function."""
    
    def test_infant_0_2(self):
        """Test infant classification (0-2 years)."""
        assert classify_age_group(0) == 'infant_0_2'
        assert classify_age_group(1) == 'infant_0_2'
        assert classify_age_group(2) == 'infant_0_2'
    
    def test_child_3_12(self):
        """Test child classification (3-12 years)."""
        assert classify_age_group(3) == 'child_3_12'
        assert classify_age_group(8) == 'child_3_12'
        assert classify_age_group(12) == 'child_3_12'
    
    def test_adolescent_13_17(self):
        """Test adolescent classification (13-17 years)."""
        assert classify_age_group(13) == 'adolescent_13_17'
        assert classify_age_group(15) == 'adolescent_13_17'
        assert classify_age_group(17) == 'adolescent_13_17'
    
    def test_adult_18_64(self):
        """Test adult classification (18-64 years)."""
        assert classify_age_group(18) == 'adult_18_64'
        assert classify_age_group(45) == 'adult_18_64'
        assert classify_age_group(64) == 'adult_18_64'
    
    def test_geriatric_65_plus(self):
        """Test geriatric classification (65+ years)."""
        assert classify_age_group(65) == 'geriatric_65_plus'
        assert classify_age_group(75) == 'geriatric_65_plus'
        assert classify_age_group(90) == 'geriatric_65_plus'


class TestVitalDeviation:
    """Test vital deviation calculation with age-specific ranges."""
    
    def test_adult_hr_normal(self):
        """Test adult HR in normal range (60-100)."""
        # HR 80 is exactly at midpoint (deviation = 0)
        deviation = compute_vital_deviation(80, 'hr', 'adult_18_64')
        assert deviation == 0.0
    
    def test_adult_hr_elevated(self):
        """Test adult HR elevated above normal."""
        # HR 120 is 1 full range above normal (60-100, width=40)
        # (120 - 80) / 40 = 1.0
        deviation = compute_vital_deviation(120, 'hr', 'adult_18_64')
        assert abs(deviation - 1.0) < 0.01
    
    def test_infant_hr_normal(self):
        """Test infant HR that's normal for age but would be high for adult."""
        # HR 140 is normal for infant (range 100-160, midpoint 130)
        # (140 - 130) / 60 = 0.167
        deviation = compute_vital_deviation(140, 'hr', 'infant_0_2')
        assert abs(deviation - 0.167) < 0.01
    
    def test_adult_hr_vs_infant_hr_same_value(self):
        """Test that same HR value has different deviations for different ages."""
        adult_deviation = compute_vital_deviation(140, 'hr', 'adult_18_64')
        infant_deviation = compute_vital_deviation(140, 'hr', 'infant_0_2')
        
        # Adult HR 140 is very abnormal (deviation ~1.5)
        # Infant HR 140 is slightly elevated but normal (deviation ~0.17)
        assert adult_deviation > 1.0
        assert infant_deviation < 0.5
        assert adult_deviation > infant_deviation
    
    def test_bp_systolic_deviation(self):
        """Test BP systolic deviation calculation."""
        # Adult normal: 110-130, midpoint 120, width 20
        # BP 150: (150 - 120) / 20 = 1.5
        deviation = compute_vital_deviation(150, 'bp_systolic', 'adult_18_64')
        assert abs(deviation - 1.5) < 0.01
    
    def test_spo2_normal(self):
        """Test SpO2 at normal levels."""
        # SpO2 >= 95 is normal for adults (deviation = 0)
        deviation = compute_vital_deviation(98, 'spo2', 'adult_18_64')
        assert deviation == 0.0
    
    def test_spo2_low(self):
        """Test SpO2 below normal threshold."""
        # SpO2 90 is 5 points below normal minimum (95)
        # Deviation = (90 - 95) / 10 = -0.5
        deviation = compute_vital_deviation(90, 'spo2', 'adult_18_64')
        assert deviation < 0.0
    
    def test_temperature_deviation(self):
        """Test temperature deviation calculation."""
        # Adult normal: 36.5-37.5, midpoint 37.0, width 1.0
        # Temp 39.0: (39.0 - 37.0) / 1.0 = 2.0 (fever)
        deviation = compute_vital_deviation(39.0, 'temperature', 'adult_18_64')
        assert abs(deviation - 2.0) < 0.01
    
    def test_missing_vital_returns_none(self):
        """Test that missing vital returns None."""
        deviation = compute_vital_deviation(None, 'hr', 'adult_18_64')
        assert deviation is None
    
    def test_geriatric_bp_ranges(self):
        """Test that geriatric patients have different BP normal ranges."""
        # Geriatric BP normal: 120-140 (higher than adult 110-130)
        # BP 130 is midpoint for geriatric (deviation = 0)
        deviation = compute_vital_deviation(130, 'bp_systolic', 'geriatric_65_plus')
        assert abs(deviation) < 0.01


class TestDataCompleteness:
    """Test data completeness score calculation."""
    
    def test_complete_data(self):
        """Test patient with all fields present."""
        patient = {
            'demographics': {'age': 45, 'sex': 'male'},
            'vitals': {
                'hr': 80,
                'bp_systolic': 120,
                'bp_diastolic': 80,
                'spo2': 98,
                'rr': 16,
                'temperature': 37.0,
            },
            'clinical': {
                'chief_complaint': 'chest pain',
                'chief_complaint_category': 'chest_pain_cardiac',
                'pain_score': 7,
                'arrival_mode': 'ambulance',
                'mental_status': 'alert',
            },
            'symptoms': ['chest_pain', 'shortness_of_breath'],
            'medical_history': {'hypertension': True},
            'observations': ['visible_distress'],
        }
        
        score = compute_data_completeness(patient)
        assert score == 100.0  # All 15 expected features present
    
    def test_missing_optional_fields(self):
        """Test patient with only required fields."""
        patient = {
            'demographics': {'age': 45, 'sex': 'male'},
            'vitals': {
                'hr': 80,
                'bp_systolic': 120,
                'bp_diastolic': 80,
                'spo2': 98,
                'rr': 16,
                # temperature missing
            },
            'clinical': {
                'chief_complaint': 'chest pain',
                'chief_complaint_category': 'chest_pain_cardiac',
                # pain_score missing
                # arrival_mode missing
                # mental_status missing
            },
            # symptoms missing
            # medical_history missing
            # observations missing
        }
        
        score = compute_data_completeness(patient)
        # Present: age, sex, hr, bp_sys, bp_dia, spo2, rr, chief_complaint, chief_complaint_category
        # Missing: temperature, pain_score, arrival_mode, mental_status, symptoms, medical_history, observations
        # 9 out of 16 = 56.25%
        assert 50.0 < score < 70.0
    
    def test_zero_history_patient(self):
        """Test patient with no medical history."""
        patient = {
            'demographics': {'age': 25, 'sex': 'female'},
            'vitals': {'hr': 85, 'bp_systolic': 115, 'bp_diastolic': 75, 'spo2': 99, 'rr': 14},
            'clinical': {
                'chief_complaint': 'minor cut',
                'chief_complaint_category': 'laceration_minor',
            },
            'medical_history': {},  # Empty history
        }
        
        score = compute_data_completeness(patient)
        assert score < 100.0  # Should penalize missing medical history


class TestPreprocessPatientData:
    """Test full preprocessing pipeline."""
    
    def test_adult_patient_complete_data(self):
        """Test preprocessing adult patient with complete data."""
        patient = {
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
        
        features = preprocess_patient_data(patient)
        
        # Check age group
        assert features['age'] == 45
        assert features['age_group'] == 'adult_18_64'
        
        # Check raw vitals preserved
        assert features['hr'] == 120
        assert features['bp_systolic'] == 90
        assert features['spo2'] == 98
        
        # Check deviations calculated
        assert features['hr_deviation'] is not None
        assert features['hr_deviation'] > 0  # Elevated
        assert features['bp_systolic_deviation'] is not None
        assert features['bp_systolic_deviation'] < 0  # Low
        
        # Check missing indicators
        assert features['is_missing_hr'] is False
        assert features['is_missing_temperature'] is False
        assert features['is_missing_pain_score'] is False
        
        # Check data completeness
        assert features['data_completeness_score'] > 90.0
        
        # Check pass-through fields
        assert features['sex'] == 'male'
        assert features['chief_complaint_category'] == 'chest_pain_cardiac'
        assert features['pain_score'] == 8
        assert len(features['symptoms']) == 2
    
    def test_infant_patient_normal_vitals(self):
        """Test that infant with 'high' HR is classified as normal."""
        patient = {
            'demographics': {'age': 1, 'sex': 'female'},
            'vitals': {
                'hr': 140,  # Normal for infant, high for adult
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
        
        features = preprocess_patient_data(patient)
        
        # Check age group
        assert features['age_group'] == 'infant_0_2'
        
        # Check HR deviation is small (normal for infant)
        assert features['hr_deviation'] is not None
        assert abs(features['hr_deviation']) < 0.5  # Close to normal
        
        # Compare to adult with same HR
        adult_patient = patient.copy()
        adult_patient['demographics'] = {'age': 45, 'sex': 'female'}
        adult_features = preprocess_patient_data(adult_patient)
        
        # Adult should have much higher deviation for HR 140
        assert adult_features['hr_deviation'] > features['hr_deviation']
    
    def test_missing_data_indicators(self):
        """Test that missing data creates proper indicator features."""
        patient = {
            'demographics': {'age': 60, 'sex': 'male'},
            'vitals': {
                'hr': 95,
                'bp_systolic': 140,
                'bp_diastolic': 85,
                'spo2': 94,
                'rr': 18,
                # temperature MISSING
            },
            'clinical': {
                'chief_complaint': 'chest discomfort',
                'chief_complaint_category': 'chest_pain_cardiac',
                # pain_score MISSING
            },
            'symptoms': ['chest_pain'],
            'medical_history': {},  # Empty history
        }
        
        features = preprocess_patient_data(patient)
        
        # Check missing indicators
        assert features['is_missing_temperature'] is True
        assert features['is_missing_pain_score'] is True
        assert features['is_missing_medical_history'] is True
        
        # Check non-missing indicators
        assert features['is_missing_hr'] is False
        assert features['is_missing_spo2'] is False
        
        # Check that deviations still calculated for present vitals
        assert features['hr_deviation'] is not None
        assert features['spo2_deviation'] is not None
        
        # Check that missing vital has None deviation
        assert features['temperature_deviation'] is None
    
    def test_geriatric_patient_different_ranges(self):
        """Test that geriatric patients use different vital ranges."""
        geriatric = {
            'demographics': {'age': 75, 'sex': 'male'},
            'vitals': {
                'hr': 85,
                'bp_systolic': 135,  # Normal for geriatric, high for adult
                'bp_diastolic': 80,
                'spo2': 93,  # Normal for geriatric (min 92), low for adult (min 95)
                'rr': 16,
            },
            'clinical': {
                'chief_complaint': 'weakness',
                'chief_complaint_category': 'weakness_generalized',
            },
            'symptoms': ['weakness'],
            'medical_history': {'hypertension': True, 'cardiac_history': True},
        }
        
        features = preprocess_patient_data(geriatric)
        
        assert features['age_group'] == 'geriatric_65_plus'
        
        # BP 135 should be close to normal for geriatric (range 120-140)
        assert abs(features['bp_systolic_deviation']) < 1.0
        
        # SpO2 93 should be normal for geriatric (min 92)
        assert features['spo2_deviation'] >= 0.0  # Not below threshold
    
    def test_bp_naming_variations(self):
        """Test that both bp_systolic and bp_sys naming work."""
        patient1 = {
            'demographics': {'age': 45, 'sex': 'male'},
            'vitals': {'hr': 80, 'bp_systolic': 120, 'bp_diastolic': 80, 'spo2': 98, 'rr': 16},
            'clinical': {'chief_complaint': 'test', 'chief_complaint_category': 'test'},
        }
        
        patient2 = {
            'demographics': {'age': 45, 'sex': 'male'},
            'vitals': {'hr': 80, 'bp_sys': 120, 'bp_dia': 80, 'spo2': 98, 'rr': 16},
            'clinical': {'chief_complaint': 'test', 'chief_complaint_category': 'test'},
        }
        
        features1 = preprocess_patient_data(patient1)
        features2 = preprocess_patient_data(patient2)
        
        # Both should extract BP correctly
        assert features1['bp_systolic'] == 120
        assert features2['bp_systolic'] == 120
        assert features1['bp_systolic_deviation'] == features2['bp_systolic_deviation']


class TestFeatureNames:
    """Test feature names utility function."""
    
    def test_get_feature_names_returns_list(self):
        """Test that get_feature_names returns a list."""
        names = get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0
    
    def test_feature_names_include_key_features(self):
        """Test that key features are included in feature names."""
        names = get_feature_names()
        
        # Check key features present
        assert 'age' in names
        assert 'age_group' in names
        assert 'hr' in names
        assert 'hr_deviation' in names
        assert 'is_missing_hr' in names
        assert 'data_completeness_score' in names
        assert 'chief_complaint_category' in names


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
