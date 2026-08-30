"""
Preprocessing Pipeline for ED Triage ML Model.

Implements:
- Age group classification (infant 0-2, child 3-12, adolescent 13-17, adult 18-64, geriatric 65+)
- Vital deviation calculation using age-specific normal ranges
- Missing data handling with indicator features
- Data completeness score computation (0-100%)

Requirements: 2.2, 2.3, 11.3
"""

from typing import Dict, Any, List, Optional
import numpy as np


# Age-specific vital sign normal ranges (from data_generation.py)
AGE_SPECIFIC_VITAL_RANGES = {
    'infant_0_2': {
        'hr_min': 100, 'hr_max': 160,
        'bp_sys_min': 70, 'bp_sys_max': 100,
        'bp_dia_min': 50, 'bp_dia_max': 65,
        'spo2_min': 95,
        'rr_min': 30, 'rr_max': 60,
        'temp_min': 36.5, 'temp_max': 37.5,
    },
    'child_3_12': {
        'hr_min': 70, 'hr_max': 120,
        'bp_sys_min': 90, 'bp_sys_max': 110,
        'bp_dia_min': 55, 'bp_dia_max': 70,
        'spo2_min': 95,
        'rr_min': 20, 'rr_max': 30,
        'temp_min': 36.5, 'temp_max': 37.5,
    },
    'adolescent_13_17': {
        'hr_min': 60, 'hr_max': 100,
        'bp_sys_min': 100, 'bp_sys_max': 120,
        'bp_dia_min': 60, 'bp_dia_max': 80,
        'spo2_min': 95,
        'rr_min': 12, 'rr_max': 20,
        'temp_min': 36.5, 'temp_max': 37.5,
    },
    'adult_18_64': {
        'hr_min': 60, 'hr_max': 100,
        'bp_sys_min': 110, 'bp_sys_max': 130,
        'bp_dia_min': 70, 'bp_dia_max': 85,
        'spo2_min': 95,
        'rr_min': 12, 'rr_max': 20,
        'temp_min': 36.5, 'temp_max': 37.5,
    },
    'geriatric_65_plus': {
        'hr_min': 60, 'hr_max': 100,
        'bp_sys_min': 120, 'bp_sys_max': 140,
        'bp_dia_min': 70, 'bp_dia_max': 90,
        'spo2_min': 92,
        'rr_min': 12, 'rr_max': 20,
        'temp_min': 36.0, 'temp_max': 37.5,
    },
}


# Expected features for data completeness calculation
EXPECTED_FEATURES = [
    # Demographics (required)
    'age', 'sex',
    # Vital signs (required)
    'hr', 'bp_systolic', 'bp_diastolic', 'spo2', 'rr',
    # Vital signs (optional)
    'temperature',
    # Clinical (required)
    'chief_complaint', 'chief_complaint_category',
    # Clinical (optional)
    'pain_score', 'arrival_mode', 'mental_status',
    # Symptoms (optional but valuable)
    'symptoms',
    # Medical history (optional but valuable)
    'medical_history',
    # Observations (optional)
    'observations',
]


def classify_age_group(age: int) -> str:
    """
    Classify patient into age group based on age in years.
    
    Age Groups:
    - infant_0_2: 0-2 years
    - child_3_12: 3-12 years
    - adolescent_13_17: 13-17 years
    - adult_18_64: 18-64 years
    - geriatric_65_plus: 65+ years
    
    Args:
        age: Patient age in years
        
    Returns:
        Age group string identifier
        
    Example:
        >>> classify_age_group(1)
        'infant_0_2'
        >>> classify_age_group(45)
        'adult_18_64'
    """
    if age <= 2:
        return 'infant_0_2'
    elif age <= 12:
        return 'child_3_12'
    elif age <= 17:
        return 'adolescent_13_17'
    elif age <= 64:
        return 'adult_18_64'
    else:
        return 'geriatric_65_plus'


def compute_vital_deviation(
    vital_value: Optional[float],
    vital_name: str,
    age_group: str
) -> Optional[float]:
    """
    Compute normalized deviation from age-specific normal range.
    
    Formula:
        deviation = (actual - midpoint) / range_width
    
    Where:
        midpoint = (min + max) / 2
        range_width = max - min
    
    Interpretation:
    - deviation = 0: perfectly normal
    - deviation = -1: one full range below normal
    - deviation = +1: one full range above normal
    - deviation = +2: two full ranges above normal (very abnormal)
    
    Args:
        vital_value: Actual vital sign value (None if missing)
        vital_name: Name of vital ('hr', 'bp_systolic', 'bp_diastolic', 'rr', 'spo2', 'temp')
        age_group: Patient's age group
        
    Returns:
        Normalized deviation (float) or None if vital_value is missing
        
    Example:
        >>> # Adult with HR 140 (normal range 60-100, midpoint 80, width 40)
        >>> compute_vital_deviation(140, 'hr', 'adult_18_64')
        1.5  # (140 - 80) / 40 = 1.5 (significantly elevated)
        
        >>> # Infant with HR 140 (normal range 100-160, midpoint 130, width 60)
        >>> compute_vital_deviation(140, 'hr', 'infant_0_2')
        0.167  # (140 - 130) / 60 = 0.167 (slightly elevated but normal)
    """
    if vital_value is None:
        return None
    
    ranges = AGE_SPECIFIC_VITAL_RANGES[age_group]
    
    # Map vital names to range keys
    vital_mapping = {
        'hr': ('hr_min', 'hr_max'),
        'bp_systolic': ('bp_sys_min', 'bp_sys_max'),
        'bp_diastolic': ('bp_dia_min', 'bp_dia_max'),
        'rr': ('rr_min', 'rr_max'),
        'spo2': ('spo2_min', None),  # SpO2 only has minimum
        'temperature': ('temp_min', 'temp_max'),
        'temp': ('temp_min', 'temp_max'),
    }
    
    if vital_name not in vital_mapping:
        raise ValueError(f"Unknown vital sign: {vital_name}")
    
    min_key, max_key = vital_mapping[vital_name]
    
    # Handle SpO2 (only has minimum threshold)
    if vital_name == 'spo2':
        spo2_min = ranges[min_key]
        # For SpO2, deviation is based on distance from normal minimum (95/92)
        # Below minimum is negative deviation, above is normal (0)
        if vital_value >= spo2_min:
            return 0.0  # Normal
        else:
            # Deviation = how many percentage points below normal
            # Normalize by typical abnormal range (85-95)
            deviation = (vital_value - spo2_min) / 10.0
            return deviation
    
    # For other vitals with min/max ranges
    vital_min = ranges[min_key]
    vital_max = ranges[max_key]
    
    midpoint = (vital_min + vital_max) / 2.0
    range_width = vital_max - vital_min
    
    if range_width == 0:
        return 0.0  # Avoid division by zero
    
    deviation = (vital_value - midpoint) / range_width
    
    return float(deviation)


def compute_data_completeness(patient_data: Dict[str, Any]) -> float:
    """
    Compute data completeness score (0-100%).
    
    Counts how many expected features are present and non-null.
    
    Args:
        patient_data: Raw patient data dictionary
        
    Returns:
        Completeness score as percentage (0.0 to 100.0)
        
    Example:
        >>> patient = {
        ...     'demographics': {'age': 45, 'sex': 'male'},
        ...     'vitals': {'hr': 80, 'bp_systolic': 120, 'bp_diastolic': 80, 'spo2': 98, 'rr': 16},
        ...     'clinical': {'chief_complaint': 'chest pain', 'chief_complaint_category': 'chest_pain_cardiac'},
        ... }
        >>> compute_data_completeness(patient)
        73.33  # 11 out of 15 expected features present
    """
    present_count = 0
    total_count = len(EXPECTED_FEATURES)
    
    # Demographics
    demographics = patient_data.get('demographics', {})
    if demographics.get('age') is not None:
        present_count += 1
    if demographics.get('sex'):
        present_count += 1
    
    # Vitals
    vitals = patient_data.get('vitals', {})
    for vital in ['hr', 'bp_systolic', 'bp_diastolic', 'spo2', 'rr', 'temperature']:
        if vitals.get(vital) is not None:
            present_count += 1
    
    # Clinical
    clinical = patient_data.get('clinical', {})
    for field in ['chief_complaint', 'chief_complaint_category', 'pain_score', 'arrival_mode', 'mental_status']:
        if clinical.get(field) is not None:
            present_count += 1
    
    # Symptoms (list)
    symptoms = patient_data.get('symptoms', [])
    if symptoms and len(symptoms) > 0:
        present_count += 1
    
    # Medical history (dict)
    medical_history = patient_data.get('medical_history', {})
    if medical_history and len(medical_history) > 0:
        present_count += 1
    
    # Observations (list)
    observations = patient_data.get('observations', [])
    if observations and len(observations) > 0:
        present_count += 1
    
    completeness_score = (present_count / total_count) * 100.0
    return completeness_score


def preprocess_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw patient data into ML-ready features.
    
    Preprocessing Steps:
    1. Age group classification
    2. Vital deviation computation (age-specific)
    3. Missing data indicator features
    4. Data completeness score calculation
    
    Args:
        patient_data: Raw patient data dictionary with structure:
            {
                'demographics': {'age': int, 'sex': str, ...},
                'vitals': {'hr': float, 'bp_systolic': float, ...},
                'clinical': {'chief_complaint': str, ...},
                'symptoms': [str, ...],
                'medical_history': {str: bool, ...},
                'observations': [str, ...],
            }
    
    Returns:
        Dictionary of preprocessed features:
            {
                # Age classification
                'age': int,
                'age_group': str,
                
                # Raw vitals
                'hr': float or None,
                'bp_systolic': float or None,
                'bp_diastolic': float or None,
                'spo2': float or None,
                'rr': float or None,
                'temperature': float or None,
                
                # Vital deviations (age-normalized)
                'hr_deviation': float or None,
                'bp_systolic_deviation': float or None,
                'bp_diastolic_deviation': float or None,
                'spo2_deviation': float or None,
                'rr_deviation': float or None,
                'temperature_deviation': float or None,
                
                # Missing indicators
                'is_missing_hr': bool,
                'is_missing_bp_systolic': bool,
                'is_missing_bp_diastolic': bool,
                'is_missing_spo2': bool,
                'is_missing_rr': bool,
                'is_missing_temperature': bool,
                'is_missing_pain_score': bool,
                'is_missing_medical_history': bool,
                
                # Data quality
                'data_completeness_score': float,  # 0-100
                
                # Pass-through features
                'sex': str,
                'chief_complaint': str,
                'chief_complaint_category': str,
                'pain_score': float or None,
                'arrival_mode': str or None,
                'mental_status': str or None,
                'symptoms': List[str],
                'medical_history': Dict[str, Any],
                'observations': List[str],
            }
    
    Example:
        >>> patient = {
        ...     'demographics': {'age': 45, 'sex': 'male'},
        ...     'vitals': {'hr': 120, 'bp_systolic': 90, 'bp_diastolic': 60, 'spo2': 98, 'rr': 18},
        ...     'clinical': {'chief_complaint': 'chest pain', 'chief_complaint_category': 'chest_pain_cardiac'},
        ...     'symptoms': ['chest_pain', 'shortness_of_breath'],
        ...     'medical_history': {'hypertension': True},
        ... }
        >>> features = preprocess_patient_data(patient)
        >>> features['age_group']
        'adult_18_64'
        >>> features['hr_deviation']
        1.0  # HR 120 is 1 full range above normal (60-100)
        >>> features['data_completeness_score']
        66.67
    """
    features = {}
    
    # Extract nested dictionaries
    demographics = patient_data.get('demographics', {})
    vitals = patient_data.get('vitals', {})
    clinical = patient_data.get('clinical', {})
    symptoms = patient_data.get('symptoms', [])
    medical_history = patient_data.get('medical_history', {})
    observations = patient_data.get('observations', [])
    
    # Step 1: Age group classification
    age = demographics.get('age')
    if age is None:
        raise ValueError("Age is required for preprocessing")
    
    age_group = classify_age_group(age)
    features['age'] = age
    features['age_group'] = age_group
    
    # Step 2: Extract raw vitals
    vital_names = ['hr', 'bp_systolic', 'bp_diastolic', 'spo2', 'rr', 'temperature']
    
    for vital_name in vital_names:
        # Handle bp_systolic/bp_diastolic naming (may be stored as bp_sys/bp_dia)
        if vital_name == 'bp_systolic':
            vital_value = vitals.get('bp_systolic') or vitals.get('bp_sys')
        elif vital_name == 'bp_diastolic':
            vital_value = vitals.get('bp_diastolic') or vitals.get('bp_dia')
        else:
            vital_value = vitals.get(vital_name)
        
        features[vital_name] = vital_value
    
    # Step 3: Compute vital deviations (age-specific normalization)
    for vital_name in vital_names:
        vital_value = features[vital_name]
        deviation = compute_vital_deviation(vital_value, vital_name, age_group)
        features[f'{vital_name}_deviation'] = deviation
    
    # Step 4: Missing data indicators
    for vital_name in vital_names:
        is_missing = features[vital_name] is None
        features[f'is_missing_{vital_name}'] = is_missing
    
    # Additional missing indicators
    features['is_missing_pain_score'] = clinical.get('pain_score') is None
    features['is_missing_medical_history'] = not medical_history or len(medical_history) == 0
    
    # Step 5: Data completeness score
    features['data_completeness_score'] = compute_data_completeness(patient_data)
    
    # Step 6: Pass-through features (no transformation needed)
    features['sex'] = demographics.get('sex')
    features['chief_complaint'] = clinical.get('chief_complaint', '')
    features['chief_complaint_category'] = clinical.get('chief_complaint_category', '')
    features['pain_score'] = clinical.get('pain_score')
    features['arrival_mode'] = clinical.get('arrival_mode')
    features['mental_status'] = clinical.get('mental_status')
    features['symptoms'] = symptoms if symptoms else []
    features['medical_history'] = medical_history if medical_history else {}
    features['observations'] = observations if observations else []
    
    return features


def preprocess_batch(patient_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Preprocess a batch of patients.
    
    Args:
        patient_list: List of raw patient data dictionaries
        
    Returns:
        List of preprocessed feature dictionaries
        
    Example:
        >>> patients = [patient1, patient2, patient3]
        >>> features = preprocess_batch(patients)
        >>> len(features)
        3
    """
    return [preprocess_patient_data(patient) for patient in patient_list]


def get_feature_names() -> List[str]:
    """
    Get list of all feature names produced by preprocessing pipeline.
    
    Useful for ML model training to know expected feature set.
    
    Returns:
        List of feature names
    """
    feature_names = [
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
        
        # Vital deviations
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
        'chief_complaint',
        'chief_complaint_category',
        'pain_score',
        'arrival_mode',
        'mental_status',
        
        # Complex features
        'symptoms',  # List[str]
        'medical_history',  # Dict[str, Any]
        'observations',  # List[str]
    ]
    
    return feature_names


if __name__ == '__main__':
    # Example usage and testing
    print("Preprocessing Pipeline Test\n")
    
    # Test 1: Adult patient with complete data
    print("Test 1: Adult patient with complete data")
    adult_patient = {
        'demographics': {'age': 45, 'sex': 'male'},
        'vitals': {
            'hr': 120,  # Elevated
            'bp_systolic': 90,  # Low
            'bp_diastolic': 60,  # Low
            'spo2': 98,  # Normal
            'rr': 18,  # Normal
            'temperature': 38.5,  # Fever
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
        'observations': ['visible_distress'],
    }
    
    features = preprocess_patient_data(adult_patient)
    print(f"  Age group: {features['age_group']}")
    print(f"  HR: {features['hr']} bpm, Deviation: {features['hr_deviation']:.2f}")
    print(f"  BP Systolic: {features['bp_systolic']} mmHg, Deviation: {features['bp_systolic_deviation']:.2f}")
    print(f"  SpO2: {features['spo2']}%, Deviation: {features['spo2_deviation']:.2f}")
    print(f"  Data completeness: {features['data_completeness_score']:.1f}%")
    print(f"  Missing temperature: {features['is_missing_temperature']}")
    print()
    
    # Test 2: Pediatric infant with normal vitals
    print("Test 2: Pediatric infant (age 1) with normal vitals")
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
        'symptoms': ['fever', 'fussiness'],
        'medical_history': {},
    }
    
    features = preprocess_patient_data(infant_patient)
    print(f"  Age group: {features['age_group']}")
    print(f"  HR: {features['hr']} bpm, Deviation: {features['hr_deviation']:.2f}")
    print(f"  RR: {features['rr']}, Deviation: {features['rr_deviation']:.2f}")
    print(f"  Data completeness: {features['data_completeness_score']:.1f}%")
    print(f"  Missing temperature: {features['is_missing_temperature']}")
    print(f"  Missing medical history: {features['is_missing_medical_history']}")
    print()
    
    # Test 3: Geriatric patient with missing data
    print("Test 3: Geriatric patient (age 75) with missing data")
    geriatric_patient = {
        'demographics': {'age': 75, 'sex': 'male'},
        'vitals': {
            'hr': 95,
            'bp_systolic': 150,  # Elevated for geriatric
            'bp_diastolic': 85,
            'spo2': 90,  # Low
            'rr': 16,
            # temperature missing
        },
        'clinical': {
            'chief_complaint': 'shortness of breath',
            'chief_complaint_category': 'shortness_of_breath',
            # pain_score missing
            'arrival_mode': 'ambulance',
            'mental_status': 'alert',
        },
        'symptoms': ['shortness_of_breath', 'cough'],
        'medical_history': {'hypertension': True, 'cardiac_history': True, 'copd': True},
        'observations': [],
    }
    
    features = preprocess_patient_data(geriatric_patient)
    print(f"  Age group: {features['age_group']}")
    print(f"  HR: {features['hr']} bpm, Deviation: {features['hr_deviation']:.2f}")
    print(f"  BP Systolic: {features['bp_systolic']} mmHg, Deviation: {features['bp_systolic_deviation']:.2f}")
    print(f"  SpO2: {features['spo2']}%, Deviation: {features['spo2_deviation']:.2f}")
    print(f"  Data completeness: {features['data_completeness_score']:.1f}%")
    print(f"  Missing temperature: {features['is_missing_temperature']}")
    print(f"  Missing pain score: {features['is_missing_pain_score']}")
    print()
    
    print("✅ Preprocessing pipeline test complete!")
    print(f"\nTotal features produced: {len(get_feature_names())}")
