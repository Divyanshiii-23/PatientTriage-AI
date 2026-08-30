"""
Synthetic Patient Data Generator for ED Triage ML Model Training.

Generates:
- 500 training patients with stratified age groups and ESI distribution
- 20 diverse test patients with edge cases (ambiguous, pediatric, geriatric, zero-history)

Requirements: 1.1-1.10
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple


# Age-specific vital sign normal ranges
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


# Chief complaint categories (50+ categories)
CHIEF_COMPLAINT_CATEGORIES = [
    # Cardiovascular (ESI 1-2)
    'chest_pain_cardiac', 'chest_pain_pleuritic', 'palpitations', 'syncope',
    
    # Respiratory (ESI 1-3)
    'respiratory_distress', 'shortness_of_breath', 'wheezing', 'cough', 'hemoptysis',
    
    # Neurological (ESI 1-3)
    'stroke_symptoms', 'altered_mental_status', 'seizure', 'headache_severe', 
    'headache_mild', 'dizziness', 'weakness_unilateral', 'numbness_tingling',
    
    # Gastrointestinal (ESI 2-4)
    'abdominal_pain_severe', 'abdominal_pain_mild', 'nausea_vomiting', 
    'diarrhea', 'gi_bleed', 'constipation',
    
    # Trauma (ESI 1-4)
    'trauma_severe_multisystem', 'trauma_head', 'trauma_chest', 'trauma_abdominal',
    'fracture_suspected', 'laceration_major', 'laceration_minor', 'burn',
    'fall_ground_level', 'fall_from_height', 'motor_vehicle_collision',
    
    # Infectious (ESI 2-4)
    'fever_high', 'fever_mild', 'sepsis_suspected', 'cellulitis', 'abscess',
    'urinary_symptoms', 'pneumonia_suspected',
    
    # Musculoskeletal (ESI 3-5)
    'back_pain_severe', 'back_pain_mild', 'joint_pain', 'muscle_strain',
    'neck_pain',
    
    # General (ESI 3-5)
    'weakness_generalized', 'fatigue', 'malaise', 'dehydration',
    'cold_flu_symptoms', 'allergic_reaction_mild', 'rash', 'insect_bite',
    
    # Psychiatric (ESI 2-4)
    'suicidal_ideation', 'psychosis', 'anxiety', 'substance_intoxication',
]


# Symptom lists by category
SYMPTOMS_BY_CATEGORY = {
    'chest_pain_cardiac': ['chest_pain', 'shortness_of_breath', 'diaphoresis', 'nausea'],
    'respiratory_distress': ['shortness_of_breath', 'wheezing', 'cough', 'chest_tightness'],
    'stroke_symptoms': ['weakness_unilateral', 'speech_difficulty', 'facial_drooping', 'confusion'],
    'abdominal_pain_severe': ['abdominal_pain', 'nausea_vomiting', 'fever'],
    'fever_high': ['fever', 'chills', 'malaise', 'body_aches'],
    'trauma_severe_multisystem': ['pain', 'bleeding', 'altered_consciousness'],
    # Add more as needed
}


# Medical history conditions
MEDICAL_CONDITIONS = [
    'hypertension', 'diabetes', 'cardiac_history', 'respiratory_history',
    'kidney_disease', 'liver_disease', 'cancer', 'immunocompromised',
    'stroke_history', 'seizure_disorder', 'copd', 'asthma'
]


# Names for test patients (diverse, realistic)
TEST_PATIENT_NAMES = [
    ('John', 'Smith'), ('Maria', 'Garcia'), ('Wei', 'Chen'),
    ('Priya', 'Sharma'), ('David', 'Johnson'), ('Aisha', 'Mohamed'),
    ('Carlos', 'Rodriguez'), ('Emily', 'Wilson'), ('Raj', 'Patel'),
    ('Sarah', 'Brown'), ('Ahmed', 'Ali'), ('Linda', 'Davis'),
    ('Michael', 'Martinez'), ('Anna', 'Kim'), ('James', 'Lee'),
    ('Sofia', 'Lopez'), ('Robert', 'Anderson'), ('Lisa', 'Thomas'),
    ('Daniel', 'White'), ('Jessica', 'Taylor'),
]


class SyntheticPatientGenerator:
    """Generate realistic synthetic ED patient data."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed for reproducibility."""
        random.seed(seed)
        self.patient_counter = 0
    
    def classify_age_group(self, age: int) -> str:
        """Classify patient into age group."""
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
    
    def generate_vitals(
        self, 
        age_group: str, 
        target_esi: int, 
        is_missing_data: bool = False
    ) -> Dict[str, Any]:
        """Generate age-appropriate vital signs targeting specific ESI level."""
        ranges = AGE_SPECIFIC_VITAL_RANGES[age_group]
        vitals = {}
        
        # Heart Rate
        if target_esi == 1:
            vitals['hr'] = random.randint(ranges['hr_max'] + 30, 200)  # Severe tachycardia
        elif target_esi == 2:
            vitals['hr'] = random.randint(ranges['hr_max'] + 10, ranges['hr_max'] + 30)
        elif target_esi == 3:
            vitals['hr'] = random.randint(ranges['hr_max'] - 10, ranges['hr_max'] + 15)
        else:
            vitals['hr'] = random.randint(ranges['hr_min'], ranges['hr_max'])
        
        # Blood Pressure
        if target_esi <= 2:
            vitals['bp_systolic'] = random.randint(ranges['bp_sys_min'] - 20, ranges['bp_sys_min'])
            vitals['bp_diastolic'] = random.randint(ranges['bp_dia_min'] - 15, ranges['bp_dia_min'])
        else:
            vitals['bp_systolic'] = random.randint(ranges['bp_sys_min'], ranges['bp_sys_max'])
            vitals['bp_diastolic'] = random.randint(ranges['bp_dia_min'], ranges['bp_dia_max'])
        
        # SpO2
        if target_esi == 1:
            vitals['spo2'] = random.randint(85, 90)  # Severe hypoxia
        elif target_esi == 2:
            vitals['spo2'] = random.randint(91, 94)  # Moderate hypoxia
        else:
            vitals['spo2'] = random.randint(ranges['spo2_min'], 100)
        
        # Respiratory Rate
        if target_esi <= 2:
            vitals['rr'] = random.randint(ranges['rr_max'], ranges['rr_max'] + 15)
        else:
            vitals['rr'] = random.randint(ranges['rr_min'], ranges['rr_max'])
        
        # Temperature (optional - may be missing)
        if not is_missing_data or random.random() > 0.3:
            if 'fever' in str(target_esi):
                vitals['temperature'] = round(random.uniform(38.0, 40.0), 1)
            else:
                vitals['temperature'] = round(random.uniform(ranges['temp_min'], ranges['temp_max']), 1)
        
        return vitals
    
    def generate_chief_complaint(self, target_esi: int, is_ambiguous: bool = False) -> Tuple[str, str]:
        """Generate chief complaint text and category."""
        if is_ambiguous:
            # Ambiguous: chest pain that could be cardiac (ESI 2) or musculoskeletal (ESI 3)
            return (
                "chest discomfort radiating to left arm, started 2 hours ago, improved with rest",
                "chest_pain_cardiac"
            )
        
        # Select category based on ESI
        if target_esi == 1:
            categories = [c for c in CHIEF_COMPLAINT_CATEGORIES if 'severe' in c or 'stroke' in c or 'cardiac' in c]
        elif target_esi == 2:
            categories = [c for c in CHIEF_COMPLAINT_CATEGORIES if any(x in c for x in ['severe', 'distress', 'bleed', 'sepsis'])]
        elif target_esi == 3:
            categories = [c for c in CHIEF_COMPLAINT_CATEGORIES if any(x in c for x in ['pain', 'fever', 'headache', 'weakness'])]
        elif target_esi == 4:
            categories = [c for c in CHIEF_COMPLAINT_CATEGORIES if any(x in c for x in ['mild', 'minor', 'strain'])]
        else:  # ESI 5
            categories = [c for c in CHIEF_COMPLAINT_CATEGORIES if any(x in c for x in ['mild', 'cold', 'flu', 'rash'])]
        
        category = random.choice(categories) if categories else random.choice(CHIEF_COMPLAINT_CATEGORIES)
        
        # Generate text based on category
        complaint_texts = {
            'chest_pain_cardiac': "crushing chest pain with radiation to left arm and jaw",
            'respiratory_distress': "severe difficulty breathing, unable to speak full sentences",
            'stroke_symptoms': "sudden onset right-sided weakness and slurred speech",
            'abdominal_pain_severe': "severe sharp abdominal pain, started 4 hours ago",
            'fever_high': "high fever for 2 days with chills and body aches",
            'trauma_severe_multisystem': "motor vehicle collision, chest and abdominal pain",
            'cold_flu_symptoms': "runny nose, mild cough, low-grade fever for 3 days",
            'back_pain_mild': "lower back pain, started after lifting heavy object",
        }
        
        text = complaint_texts.get(category, f"patient presenting with {category.replace('_', ' ')}")
        return (text, category)
    
    def generate_symptoms(self, chief_complaint_category: str) -> List[str]:
        """Generate symptoms based on chief complaint."""
        if chief_complaint_category in SYMPTOMS_BY_CATEGORY:
            return SYMPTOMS_BY_CATEGORY[chief_complaint_category].copy()
        
        # Default symptoms based on category keywords
        symptoms = []
        if 'pain' in chief_complaint_category:
            symptoms.append('pain')
        if 'fever' in chief_complaint_category:
            symptoms.extend(['fever', 'chills'])
        if 'respiratory' in chief_complaint_category or 'breathing' in chief_complaint_category:
            symptoms.extend(['shortness_of_breath', 'cough'])
        
        return symptoms if symptoms else ['general_malaise']
    
    def generate_medical_history(self, age: int, is_zero_history: bool = False) -> Dict[str, Any]:
        """Generate medical history."""
        if is_zero_history:
            return {}
        
        history = {}
        
        # Age-based probability of conditions
        if age >= 65:
            for condition in ['hypertension', 'diabetes', 'cardiac_history']:
                if random.random() < 0.4:
                    history[condition] = True
        elif age >= 45:
            for condition in ['hypertension', 'diabetes']:
                if random.random() < 0.2:
                    history[condition] = True
        
        # Random additional conditions
        for condition in random.sample(MEDICAL_CONDITIONS, k=random.randint(0, 2)):
            history[condition] = True
        
        # Medications flag
        if history:
            history['on_medications'] = random.random() < 0.7
        
        return history
    
    def generate_patient(
        self,
        target_esi: int = None,
        age: int = None,
        is_ambiguous: bool = False,
        is_zero_history: bool = False,
        is_missing_data: bool = False,
        name: Tuple[str, str] = None,
    ) -> Dict[str, Any]:
        """Generate a single synthetic patient."""
        self.patient_counter += 1
        
        # Determine age if not specified
        if age is None:
            if target_esi and target_esi <= 2:
                age = random.randint(35, 75)
            else:
                age = random.randint(18, 70)
        
        age_group = self.classify_age_group(age)
        
        # Determine ESI if not specified
        if target_esi is None:
            # Weighted distribution: ESI 3 most common, ESI 1 rare
            target_esi = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 40, 25, 15])[0]
        
        # Generate components
        vitals = self.generate_vitals(age_group, target_esi, is_missing_data)
        chief_complaint, chief_complaint_category = self.generate_chief_complaint(target_esi, is_ambiguous)
        symptoms = self.generate_symptoms(chief_complaint_category)
        medical_history = self.generate_medical_history(age, is_zero_history)
        
        # Generate name
        if name is None:
            first = random.choice(['John', 'Mary', 'Michael', 'Sarah', 'David', 'Lisa', 'James', 'Emily'])
            last = random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis'])
            name = (first, last)
        
        # Pain score (optional)
        pain_score = None
        if not is_missing_data or random.random() > 0.3:
            if 'pain' in chief_complaint_category:
                pain_score = random.randint(5, 10) if target_esi <= 2 else random.randint(3, 7)
            else:
                pain_score = random.randint(0, 4)
        
        patient = {
            'patient_id': str(uuid.uuid4()),
            'name': f"{name[0]} {name[1]}",
            'demographics': {
                'age': age,
                'sex': random.choice(['male', 'female']),
                'age_group': age_group,
            },
            'vitals': vitals,
            'clinical': {
                'chief_complaint': chief_complaint,
                'chief_complaint_category': chief_complaint_category,
                'pain_score': pain_score,
                'arrival_mode': 'ambulance' if target_esi <= 2 else random.choice(['walk_in', 'ambulance', 'private_vehicle']),
                'mental_status': 'alert' if target_esi >= 3 else random.choice(['alert', 'confused', 'drowsy']),
            },
            'symptoms': symptoms,
            'medical_history': medical_history,
            'observations': [],
            'ground_truth_esi': target_esi,
            'arrival_timestamp': (datetime.now() - timedelta(minutes=random.randint(0, 180))).isoformat(),
        }
        
        return patient
    
    def generate_training_set(self, n: int = 500) -> List[Dict[str, Any]]:
        """Generate training dataset with stratified age groups and ESI distribution."""
        patients = []
        
        # Age group distribution: 10% infant, 15% child, 10% adolescent, 50% adult, 15% geriatric
        age_group_counts = {
            'infant_0_2': int(n * 0.10),
            'child_3_12': int(n * 0.15),
            'adolescent_13_17': int(n * 0.10),
            'adult_18_64': int(n * 0.50),
            'geriatric_65_plus': int(n * 0.15),
        }
        
        # ESI distribution: 5% ESI 1, 15% ESI 2, 40% ESI 3, 25% ESI 4, 15% ESI 5
        esi_distribution = [1, 2, 3, 4, 5]
        esi_weights = [5, 15, 40, 25, 15]
        
        for age_group, count in age_group_counts.items():
            for _ in range(count):
                # Determine age within group
                if age_group == 'infant_0_2':
                    age = random.randint(0, 2)
                elif age_group == 'child_3_12':
                    age = random.randint(3, 12)
                elif age_group == 'adolescent_13_17':
                    age = random.randint(13, 17)
                elif age_group == 'adult_18_64':
                    age = random.randint(18, 64)
                else:  # geriatric
                    age = random.randint(65, 90)
                
                # Sample ESI with weights
                target_esi = random.choices(esi_distribution, weights=esi_weights)[0]
                
                patient = self.generate_patient(target_esi=target_esi, age=age)
                patients.append(patient)
        
        return patients
    
    def generate_test_set(self) -> List[Dict[str, Any]]:
        """Generate 20 diverse test patients with edge cases."""
        patients = []
        
        # Patient 1: Ambiguous chest pain (ESI 2 vs 3 borderline) - 45yo male
        patients.append(self.generate_patient(
            target_esi=2,
            age=45,
            is_ambiguous=True,
            name=TEST_PATIENT_NAMES[0]
        ))
        
        # Patient 2: Pediatric infant with fever (ESI 2)
        patients.append(self.generate_patient(
            target_esi=2,
            age=1,
            name=TEST_PATIENT_NAMES[1]
        ))
        
        # Patient 3: Pediatric child with minor trauma (ESI 4)
        patients.append(self.generate_patient(
            target_esi=4,
            age=8,
            name=TEST_PATIENT_NAMES[2]
        ))
        
        # Patient 4: Geriatric with fall and anticoagulation (ESI 2)
        patient4 = self.generate_patient(
            target_esi=2,
            age=78,
            name=TEST_PATIENT_NAMES[3]
        )
        patient4['medical_history']['cardiac_history'] = True
        patient4['medical_history']['on_anticoagulation'] = True
        patient4['clinical']['chief_complaint'] = "fall from standing height, hit head"
        patient4['clinical']['chief_complaint_category'] = 'trauma_head'
        patients.append(patient4)
        
        # Patient 5: Geriatric with normal vitals but cardiac history (ESI 3)
        patients.append(self.generate_patient(
            target_esi=3,
            age=72,
            name=TEST_PATIENT_NAMES[4]
        ))
        
        # Patient 6: Zero-history patient (ESI 3)
        patients.append(self.generate_patient(
            target_esi=3,
            age=25,
            is_zero_history=True,
            name=TEST_PATIENT_NAMES[5]
        ))
        
        # Patients 7-9: Missing optional data (ESI 3, 4, 5)
        for i, esi in enumerate([3, 4, 5]):
            patients.append(self.generate_patient(
                target_esi=esi,
                age=random.randint(25, 55),
                is_missing_data=True,
                name=TEST_PATIENT_NAMES[6 + i]
            ))
        
        # Patients 10-11: ESI 1 (critical)
        patients.append(self.generate_patient(target_esi=1, age=60, name=TEST_PATIENT_NAMES[9]))
        patients.append(self.generate_patient(target_esi=1, age=35, name=TEST_PATIENT_NAMES[10]))
        
        # Patients 12-13: ESI 2 (emergent)
        patients.append(self.generate_patient(target_esi=2, age=50, name=TEST_PATIENT_NAMES[11]))
        patients.append(self.generate_patient(target_esi=2, age=28, name=TEST_PATIENT_NAMES[12]))
        
        # Patients 14-16: ESI 3 (urgent)
        for i in range(3):
            patients.append(self.generate_patient(
                target_esi=3,
                age=random.randint(25, 60),
                name=TEST_PATIENT_NAMES[13 + i]
            ))
        
        # Patients 17-18: ESI 4 (less urgent)
        for i in range(2):
            patients.append(self.generate_patient(
                target_esi=4,
                age=random.randint(20, 50),
                name=TEST_PATIENT_NAMES[16 + i]
            ))
        
        # Patients 19-20: ESI 5 (non-urgent)
        for i in range(2):
            patients.append(self.generate_patient(
                target_esi=5,
                age=random.randint(18, 40),
                name=TEST_PATIENT_NAMES[18 + i]
            ))
        
        return patients


def main():
    """Generate and save training and test datasets."""
    print("Starting synthetic patient data generation...")
    
    # Create data directory
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Initialize generator
    generator = SyntheticPatientGenerator(seed=42)
    
    # Generate training set
    print("\nGenerating 500 training patients...")
    training_patients = generator.generate_training_set(n=500)
    print(f"✓ Generated {len(training_patients)} training patients")
    
    # Verify ESI distribution
    esi_counts = {}
    for patient in training_patients:
        esi = patient['ground_truth_esi']
        esi_counts[esi] = esi_counts.get(esi, 0) + 1
    print(f"  ESI distribution: {esi_counts}")
    
    # Save training set
    training_path = data_dir / 'training_patients.json'
    with open(training_path, 'w') as f:
        json.dump(training_patients, f, indent=2)
    print(f"✓ Saved to {training_path}")
    
    # Generate test set
    print("\nGenerating 20 test patients...")
    test_patients = generator.generate_test_set()
    print(f"✓ Generated {len(test_patients)} test patients")
    
    # Verify test set requirements
    pediatric_count = sum(1 for p in test_patients if p['demographics']['age'] < 18)
    geriatric_count = sum(1 for p in test_patients if p['demographics']['age'] >= 65)
    zero_history_count = sum(1 for p in test_patients if not p['medical_history'])
    missing_data_count = sum(1 for p in test_patients if p['vitals'].get('temperature') is None or p['clinical']['pain_score'] is None)
    
    print(f"  Pediatric patients: {pediatric_count}")
    print(f"  Geriatric patients: {geriatric_count}")
    print(f"  Zero-history patients: {zero_history_count}")
    print(f"  Patients with missing data: {missing_data_count}")
    
    # Verify ESI distribution in test set
    test_esi_counts = {}
    for patient in test_patients:
        esi = patient['ground_truth_esi']
        test_esi_counts[esi] = test_esi_counts.get(esi, 0) + 1
    print(f"  ESI distribution: {test_esi_counts}")
    
    # Save test set
    test_path = data_dir / 'test_patients.json'
    with open(test_path, 'w') as f:
        json.dump(test_patients, f, indent=2)
    print(f"✓ Saved to {test_path}")
    
    print("\n✅ Data generation complete!")
    print(f"   Training patients: {len(training_patients)}")
    print(f"   Test patients: {len(test_patients)}")
    print(f"   Total chief complaint categories: {len(CHIEF_COMPLAINT_CATEGORIES)}")


if __name__ == '__main__':
    main()
