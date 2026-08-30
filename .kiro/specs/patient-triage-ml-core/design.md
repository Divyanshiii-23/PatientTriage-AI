# Technical Design: PatientTriage.ai ML Core Engine

## Overview

### System Purpose

The PatientTriage.ai ML Core Engine is a machine learning-powered clinical decision support system for Emergency Department (ED) triage. It provides real-time triage recommendations (ESI level 1-5), continuous deterioration monitoring during wait times, and surge mode sub-prioritization to address critical challenges in Indian EDs:

- **Specialist Shortage**: Only ~158 trained EM specialists annually for 119.1 million ED visits
- **High Mistriage Rates**: 32.2% overall including 3.3% dangerous under-triage
- **Overcrowding Mortality**: 5.4% mortality increase during peak times

The system processes patient demographics, vital signs, symptoms, and medical history to generate predictions with multi-dimensional confidence scores, safety validation, and SHAP-based explanations. It handles age-specific calibration, missing data, ambiguous symptoms, and explicitly surfaces uncertainty while biasing toward escalation under doubt.

### Key Design Principles

1. **Safety First**: Under-triage penalties 10× over-triage, safety validation layer overrides ML when needed
2. **Transparency**: Every prediction includes SHAP explanations and multi-dimensional confidence breakdown
3. **Clinical Accountability**: System provides recommendations, clinicians make final decisions
4. **Age-Appropriate Assessment**: Separate calibration for pediatric (0-2, 3-12, 13-17), adult (18-64), geriatric (65+)
5. **Graceful Degradation**: Works with missing data, flags low confidence, handles out-of-distribution cases
6. **Continuous Learning**: Override tracking feeds retraining pipeline, shadow mode enables safe deployment

### Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                       │
│  POST /predict    POST /deterioration    GET /health             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    Preprocessing Pipeline                        │
│  Schema Validation → Feature Engineering → Missing Data Handling │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼───────┐  ┌────────▼───────┐  ┌───────▼────────┐
│ Age-Stratified │  │  Deterioration │  │ Surge Engine   │
│ ESI Classifier │  │    Detector    │  │ (Formula-based)│
│   (CatBoost)   │  │   (XGBoost)    │  │                │
└────────┬───────┘  └────────┬───────┘  └───────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    Post-Processing Layer                         │
│  SHAP Explainer → Confidence Scorer → Safety Validator           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                      Response Formation                          │
│  JSON Serialization → Audit Logging → API Response               │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **ESI Classifier** | CatBoost 1.2+ | Superior categorical handling (50+ chief complaints), auto-categorical encoding, robust missing value support, strong baseline performance |
| **Deterioration Detector** | XGBoost 2.0+ | Optimized for temporal features, faster inference (<10ms), proven for time-series medical data |
| **Explainability** | SHAP TreeExplainer | Model-agnostic, additive feature attribution, fast for tree models (<100ms) |
| **API Framework** | FastAPI 0.100+ | Async support, auto OpenAPI docs, Pydantic validation, high throughput (1000+ req/s) |
| **Feature Store** | Redis 7.0+ | Sub-millisecond lookup for age ranges, condition urgency tables, recent predictions cache |
| **Model Registry** | MLflow 2.8+ | Version control, A/B testing, shadow mode, metric tracking |
| **Audit Storage** | PostgreSQL 15+ | ACID compliance, 7-year retention, complex queries for override analysis |
| **Monitoring** | Prometheus + Grafana | Real-time metrics, bias dashboards, alerting on under-triage spikes |



## Architecture

### System Components

The ML Core Engine consists of 8 major components organized in a pipeline architecture:

```
Input → Preprocessing → ML Models → Post-Processing → Output
                ↓
        Feature Store (Redis)
                ↓
        Model Registry (MLflow)
                ↓
        Audit Log (PostgreSQL)
```

#### 1. API Layer

**Responsibilities**:
- Receive patient data via REST endpoints
- Validate request schemas using Pydantic
- Route to appropriate pipeline (ESI prediction vs deterioration detection)
- Handle errors gracefully with appropriate HTTP status codes
- Enforce rate limiting (500 req/hour baseline, configurable)
- Support batch predictions for deterioration monitoring

**Implementation**:
```python
# FastAPI application structure
app = FastAPI(title="PatientTriage ML Core", version="2.0.0")

@app.post("/api/v1/predict", response_model=PredictionResponse)
async def predict_esi(patient: PatientData, background_tasks: BackgroundTasks):
    """
    Generate ESI triage recommendation with confidence and explanation.
    
    Target latency: <100ms p95
    Throughput: 500+ requests/hour
    """
    pass

@app.post("/api/v1/deterioration", response_model=DeteriorationResponse)
async def assess_deterioration(assessment: DeteriorationRequest):
    """
    Assess patient deterioration based on vital sign changes.
    
    Target latency: <100ms p95
    Triggered automatically by monitoring intervals
    """
    pass

@app.get("/api/v1/health")
async def health_check():
    """Service health including model availability"""
    return {"status": "healthy", "models_loaded": True}
```

**Endpoints**:

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/v1/predict` | POST | ESI prediction | API Key |
| `/api/v1/deterioration` | POST | Deterioration assessment | API Key |
| `/api/v1/health` | GET | Service health check | None |
| `/api/v1/models` | GET | List available model versions | Admin Token |
| `/api/v1/models/{version}/activate` | POST | Switch production model | Admin Token |

#### 2. Preprocessing Pipeline

**Responsibilities**:
- Validate patient data completeness
- Classify patient into age group (pediatric 0-2, 3-12, 13-17, adult 18-64, geriatric 65+)
- Compute vital deviations using age-specific lookup tables
- Detect symptom-vital discordance (under-reporting indicators)
- Handle missing data with CatBoost-compatible encoding
- Create `is_missing_*` indicator features
- Compute data completeness score

**Feature Engineering Pipeline**:

```python
def preprocess_patient_data(raw_data: PatientData) -> ProcessedFeatures:
    """
    Transform raw patient data into ML-ready features.
    
    Steps:
    1. Age group classification
    2. Vital deviation computation
    3. Discordance flag creation
    4. Missing indicator generation
    5. Data completeness calculation
    
    Returns: ProcessedFeatures with 40+ engineered features
    """
    features = {}
    
    # Step 1: Age group classification
    age = raw_data.demographics.age
    if age <= 2:
        features['age_group'] = 'pediatric_infant'
    elif age <= 12:
        features['age_group'] = 'pediatric_child'
    elif age <= 17:
        features['age_group'] = 'pediatric_adolescent'
    elif age <= 64:
        features['age_group'] = 'adult'
    else:
        features['age_group'] = 'geriatric'
    
    # Step 2: Vital deviations (age-specific normalization)
    vital_ranges = AGE_SPECIFIC_VITAL_RANGES[features['age_group']]
    
    if raw_data.vitals.hr is not None:
        hr_normal_mid = (vital_ranges['hr_min'] + vital_ranges['hr_max']) / 2
        hr_normal_width = vital_ranges['hr_max'] - vital_ranges['hr_min']
        features['hr_deviation'] = (raw_data.vitals.hr - hr_normal_mid) / hr_normal_width
    else:
        features['hr_deviation'] = None
        features['is_missing_hr'] = True
    
    # Similar for other vitals: bp_sys, bp_dia, rr, spo2, temp
    
    # Step 3: Symptom-vital discordance flags
    features['pain_underreported'] = (
        raw_data.clinical.pain_score is not None and 
        raw_data.clinical.pain_score < 4 and 
        raw_data.vitals.hr is not None and 
        raw_data.vitals.hr > 110
    )
    
    features['severity_underreported'] = (
        raw_data.clinical.chief_complaint_category in MINOR_COMPLAINTS and
        count_abnormal_vitals(raw_data.vitals, features['age_group']) >= 3
    )
    
    features['respiratory_underreported'] = (
        raw_data.vitals.spo2 is not None and
        raw_data.vitals.spo2 < 93 and
        not has_respiratory_symptoms(raw_data.symptoms)
    )
    
    # Step 4: Data completeness
    total_features = 40  # Expected feature count
    present_features = sum(1 for v in features.values() if v is not None)
    features['data_completeness_score'] = present_features / total_features
    
    return ProcessedFeatures(**features)
```

**Age-Specific Vital Ranges** (stored in Redis):

```python
AGE_SPECIFIC_VITAL_RANGES = {
    'pediatric_infant': {  # 0-2 years
        'hr_min': 100, 'hr_max': 160,
        'rr_min': 30, 'rr_max': 60,
        'bp_sys_min': 80, 'bp_sys_max': 110,
        'spo2_min': 95, 'temp_min': 36.5, 'temp_max': 37.5
    },
    'pediatric_child': {  # 3-12 years
        'hr_min': 70, 'hr_max': 120,
        'rr_min': 20, 'rr_max': 30,
        'bp_sys_min': 90, 'bp_sys_max': 120,
        'spo2_min': 95, 'temp_min': 36.5, 'temp_max': 37.5
    },
    'pediatric_adolescent': {  # 13-17 years
        'hr_min': 60, 'hr_max': 100,
        'rr_min': 12, 'rr_max': 20,
        'bp_sys_min': 100, 'bp_sys_max': 130,
        'spo2_min': 95, 'temp_min': 36.5, 'temp_max': 37.5
    },
    'adult': {  # 18-64 years
        'hr_min': 60, 'hr_max': 100,
        'rr_min': 12, 'rr_max': 20,
        'bp_sys_min': 110, 'bp_sys_max': 140,
        'bp_dia_min': 70, 'bp_dia_max': 90,
        'spo2_min': 95, 'temp_min': 36.5, 'temp_max': 37.5
    },
    'geriatric': {  # 65+ years
        'hr_min': 60, 'hr_max': 100,
        'rr_min': 12, 'rr_max': 20,
        'bp_sys_min': 120, 'bp_sys_max': 150,
        'bp_dia_min': 70, 'bp_dia_max': 90,
        'spo2_min': 92, 'temp_min': 36.0, 'temp_max': 37.5
    }
}
```

#### 3. Age-Stratified ESI Classifier

**Model Architecture**: CatBoost Multi-Class Classifier

**Why CatBoost**:
1. **Superior Categorical Handling**: 50+ chief complaint categories handled natively without one-hot explosion
2. **Built-in Missing Value Support**: No need for imputation, model learns optimal missing value splits
3. **Ordered Boosting**: Reduces overfitting on small subgroups (e.g., rare pediatric conditions)
4. **Strong Baseline**: Often outperforms XGBoost/LightGBM without extensive tuning
5. **Fast Inference**: ~5-10ms per prediction on CPU

**Hyperparameters**:

```python
catboost_params = {
    'iterations': 1000,
    'learning_rate': 0.05,
    'depth': 6,
    'loss_function': 'MultiClass',
    'custom_loss': ['Accuracy', 'TotalF1'],
    'eval_metric': 'TotalF1',
    'early_stopping_rounds': 50,
    'random_seed': 42,
    'task_type': 'CPU',  # Use GPU for training: 'GPU'
    'cat_features': [  # Categorical columns
        'chief_complaint_category',
        'arrival_mode',
        'mental_status',
        'age_group'
    ],
    'class_weights': {  # 10× penalty for under-triage
        0: 10,  # ESI 1 (most critical)
        1: 5,   # ESI 2
        2: 2,   # ESI 3
        3: 1,   # ESI 4
        4: 1    # ESI 5 (least urgent)
    },
    'bootstrap_type': 'Bayesian',
    'bagging_temperature': 1.0,
    'use_best_model': True
}
```

**Input Features** (40+ features):

| Category | Features | Type | Notes |
|----------|----------|------|-------|
| **Demographics** | age, sex, age_group | num, cat, cat | Age group drives vital calibration |
| **Vital Deviations** | hr_deviation, bp_sys_deviation, bp_dia_deviation, rr_deviation, spo2_deviation, temp_deviation | num | Age-normalized (-2 to +2 typically) |
| **Raw Vitals** | hr, bp_systolic, bp_diastolic, spo2, rr, temperature | num | Included alongside deviations |
| **Clinical** | chief_complaint_category, pain_score, arrival_mode, mental_status | cat, num, cat, cat | Chief complaint: 50+ categories |
| **Symptoms** | symptom_count, has_chest_pain, has_sob, has_altered_consciousness, has_bleeding | num, bool × N | Binary flags for key symptoms |
| **History** | cardiac_history, respiratory_history, diabetes, on_medications, recent_hospitalization | bool × 5 | Comorbidity indicators |
| **Observations** | visible_distress, altered_consciousness, active_bleeding, hemodynamic_instability | bool × 4 | Nurse observations |
| **Discordance Flags** | pain_underreported, severity_underreported, respiratory_underreported | bool × 3 | Under-reporting detection |
| **Missing Indicators** | is_missing_temp, is_missing_pain_score, is_missing_history | bool × N | CatBoost optional but helps confidence |
| **Data Quality** | data_completeness_score | num | 0-1, % of features present |

**Output**:
- **ESI Prediction**: Integer 1-5
- **Probability Distribution**: `[p_esi1, p_esi2, p_esi3, p_esi4, p_esi5]`
- **Raw SHAP Values**: Per-feature contributions (40+ values)

**Training Algorithm**:

```python
def train_esi_classifier(training_data: pd.DataFrame) -> CatBoostClassifier:
    """
    Train age-stratified ESI classifier with custom under-triage penalty.
    
    Data Requirements:
    - Minimum 50,000 ED records
    - Balanced age groups (15%+ each: pediatric, adult, geriatric)
    - Ground truth: clinician-assigned ESI with outcomes
    
    Returns: Trained CatBoost model
    """
    # Preprocess features
    X = preprocess_features(training_data)
    y = training_data['clinician_esi'] - 1  # Convert ESI 1-5 to 0-4 for CatBoost
    
    # Stratified split by age_group + ESI
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, 
        test_size=0.15, 
        stratify=pd.concat([X['age_group'], y], axis=1),
        random_state=42
    )
    
    # Define categorical features
    cat_features = ['chief_complaint_category', 'arrival_mode', 
                    'mental_status', 'age_group']
    
    # Custom loss: 10× penalty for under-triage
    # Under-triage: predicted > actual (e.g., predict ESI 4 when actually ESI 2)
    def custom_loss(preds, targets):
        pred_esi = np.argmax(preds, axis=1)
        under_triage_mask = pred_esi > targets
        over_triage_mask = pred_esi < targets
        correct_mask = pred_esi == targets
        
        loss = np.zeros_like(targets, dtype=float)
        loss[under_triage_mask] = 10.0 * (pred_esi[under_triage_mask] - targets[under_triage_mask])
        loss[over_triage_mask] = 1.0 * (targets[over_triage_mask] - pred_esi[over_triage_mask])
        
        return np.mean(loss)
    
    # Train model
    model = CatBoostClassifier(**catboost_params)
    model.fit(
        X_train, y_train,
        cat_features=cat_features,
        eval_set=(X_val, y_val),
        verbose=100,
        plot=True
    )
    
    # Validate age-stratified performance
    validate_age_stratified_performance(model, X_val, y_val)
    
    return model
```

**Custom Under-Triage Loss** (Mathematical Formulation):

Standard multi-class cross-entropy prioritizes overall accuracy. We need to heavily penalize under-triage errors. Define custom loss:

$$
L(\hat{y}, y) = \begin{cases}
10 \times |\hat{y} - y| & \text{if } \hat{y} > y \text{ (under-triage)} \\
1 \times |y - \hat{y}| & \text{if } \hat{y} < y \text{ (over-triage)} \\
0 & \text{if } \hat{y} = y \text{ (correct)}
\end{cases}
$$

Where:
- $\hat{y}$ = predicted ESI class (0-4)
- $y$ = true ESI class (0-4)
- Higher class number = lower urgency (ESI 5 = least urgent)

Implemented via `class_weights` in CatBoost:

```python
# Interpretation: ESI 1 (class 0) errors weighted 10×, ESI 2 weighted 5×, etc.
class_weights = {0: 10, 1: 5, 2: 2, 3: 1, 4: 1}
```



#### 4. Multi-Dimensional Confidence System

**Purpose**: Single confidence scores are insufficient for clinical decisions. We need transparency across multiple certainty dimensions so clinicians understand WHY confidence is high/low.

**Four Confidence Dimensions**:

1. **Model Certainty** (0-100): How confident is the ML model in its prediction?
2. **Data Completeness** (0-100): How much of the ideal data do we have?
3. **Clinical Consistency** (0-100): Do symptoms and vitals align logically?
4. **Pattern Recognition** (0-100): Is this patient similar to training data?

**Aggregation**: Weighted average → Overall confidence → HIGH/MEDIUM/LOW threshold

**Algorithm**:

```python
class ConfidenceSystem:
    """
    Multi-dimensional confidence scoring for clinical transparency.
    
    Outputs:
    - Four dimension scores (0-100 each)
    - Overall confidence (0-100)
    - Confidence level (HIGH/MEDIUM/LOW)
    - Recommendations (escalate, validate, accept)
    """
    
    def __init__(self):
        # Dimension weights (sum to 1.0)
        self.weights = {
            'model_certainty': 0.40,
            'data_completeness': 0.25,
            'clinical_consistency': 0.20,
            'pattern_recognition': 0.15
        }
        
        # Thresholds for HIGH/MEDIUM/LOW
        self.high_threshold = 80.0
        self.medium_threshold = 60.0
        
        # Load isolation forest for OOD detection (trained once)
        self.ood_detector = load_isolation_forest()
    
    def compute_confidence(
        self, 
        probability_distribution: np.ndarray,
        features: ProcessedFeatures,
        discordance_flags: Dict[str, bool]
    ) -> ConfidenceBreakdown:
        """
        Compute multi-dimensional confidence for a prediction.
        
        Args:
            probability_distribution: [p1, p2, p3, p4, p5] from ESI model
            features: Processed patient features
            discordance_flags: Symptom-vital discordance indicators
        
        Returns:
            ConfidenceBreakdown with all dimensions and overall score
        """
        
        # Dimension 1: Model Certainty (inverse of entropy)
        model_certainty = self._compute_model_certainty(probability_distribution)
        
        # Dimension 2: Data Completeness
        data_completeness = features.data_completeness_score * 100
        
        # Dimension 3: Clinical Consistency (inverse of discordance)
        clinical_consistency = self._compute_clinical_consistency(discordance_flags)
        
        # Dimension 4: Pattern Recognition (inverse of OOD score)
        pattern_recognition = self._compute_pattern_recognition(features)
        
        # Weighted aggregation
        overall = (
            self.weights['model_certainty'] * model_certainty +
            self.weights['data_completeness'] * data_completeness +
            self.weights['clinical_consistency'] * clinical_consistency +
            self.weights['pattern_recognition'] * pattern_recognition
        )
        
        # Classify into HIGH/MEDIUM/LOW
        if overall >= self.high_threshold:
            level = "HIGH"
        elif overall >= self.medium_threshold:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return ConfidenceBreakdown(
            model_certainty=model_certainty,
            data_completeness=data_completeness,
            clinical_consistency=clinical_consistency,
            pattern_recognition=pattern_recognition,
            overall=overall,
            level=level
        )
    
    def _compute_model_certainty(self, probs: np.ndarray) -> float:
        """
        Model certainty from probability distribution entropy.
        
        Low entropy (peaked distribution) → high certainty
        High entropy (uniform distribution) → low certainty
        
        Example:
        - [0.95, 0.02, 0.01, 0.01, 0.01] → entropy 0.3 → certainty 95
        - [0.4, 0.3, 0.15, 0.1, 0.05] → entropy 1.4 → certainty 40
        """
        # Compute Shannon entropy
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        
        # Max entropy for 5 classes: log(5) ≈ 1.61
        max_entropy = np.log(5)
        
        # Normalize to 0-100 (inverse: low entropy → high certainty)
        certainty = 100 * (1 - entropy / max_entropy)
        
        return float(certainty)
    
    def _compute_clinical_consistency(self, discordance_flags: Dict[str, bool]) -> float:
        """
        Clinical consistency from symptom-vital discordance flags.
        
        No discordance → 100% consistency
        Each discordance flag reduces consistency
        """
        total_flags = len(discordance_flags)
        triggered_flags = sum(discordance_flags.values())
        
        if total_flags == 0:
            return 100.0
        
        # Each triggered flag reduces consistency
        consistency = 100 * (1 - triggered_flags / total_flags)
        
        # Apply penalty curve (exponential)
        # 1 flag → ~70%, 2 flags → ~40%, 3 flags → ~20%
        if triggered_flags > 0:
            consistency *= (0.7 ** triggered_flags)
        
        return float(consistency)
    
    def _compute_pattern_recognition(self, features: ProcessedFeatures) -> float:
        """
        Pattern recognition from out-of-distribution (OOD) detection.
        
        Uses Isolation Forest trained on feature distributions.
        Low anomaly score → in-distribution → high confidence
        High anomaly score → OOD → low confidence
        """
        # Convert features to numpy array
        feature_vector = features.to_numpy()
        
        # Compute anomaly score (-1 to 1, where -1 = outlier)
        anomaly_score = self.ood_detector.score_samples([feature_vector])[0]
        
        # Convert to 0-100 (normalize from -1..1 to 0..100)
        pattern_score = 50 * (anomaly_score + 1)
        
        return float(pattern_score)
```

**Confidence-Driven Recommendations**:

```python
def generate_confidence_recommendations(
    confidence: ConfidenceBreakdown,
    predicted_esi: int
) -> List[str]:
    """
    Generate actionable recommendations based on confidence analysis.
    
    Rules:
    1. LOW confidence + ESI ≥3 → escalate by one level
    2. LOW confidence + data_completeness <70% → request more data
    3. MEDIUM confidence + clinical_consistency <50% → clinical validation
    4. Any pattern_recognition <30% → flag as OOD, recommend caution
    """
    recommendations = []
    
    if confidence.level == "LOW":
        if predicted_esi >= 3:
            recommendations.append(
                f"LOW confidence detected. Consider escalating from ESI {predicted_esi} "
                f"to ESI {predicted_esi - 1} for safety."
            )
        
        if confidence.data_completeness < 70:
            recommendations.append(
                f"Data completeness is {confidence.data_completeness:.0f}%. "
                "Obtain additional patient information if possible."
            )
    
    if confidence.clinical_consistency < 50:
        recommendations.append(
            "Clinical inconsistency detected (symptoms don't match vitals). "
            "Probe patient for under-reporting or hidden symptoms."
        )
    
    if confidence.pattern_recognition < 30:
        recommendations.append(
            "Patient presentation is unusual (out-of-distribution). "
            "Exercise clinical caution and consider specialist consultation."
        )
    
    return recommendations
```

**Example Confidence Breakdown**:

```json
{
  "model_certainty": 92.3,
  "data_completeness": 85.0,
  "clinical_consistency": 65.0,
  "pattern_recognition": 78.5,
  "overall": 81.7,
  "level": "HIGH",
  "recommendations": []
}
```



#### 5. Safety Validation Layer

**Purpose**: Rule-based safety net that runs AFTER ML prediction to catch life-threatening conditions that model might miss. Overrides ML when critical criteria are met.

**Design Philosophy**: 
- ML is good at patterns, rules are good at absolutes
- Under-triage kills, over-triage delays
- When in doubt, escalate

**Five Safety Validators**:

1. **Critical Clinical Criteria**: Hard-coded life threats (chest pain + age >50, SpO2 <85%, altered consciousness, active bleeding + hypotension)
2. **Vital Thresholds**: Age-specific critical ranges (HR >160 adult = RED, HR >160 infant = maybe normal)
3. **Confidence Check**: LOW confidence + high ESI triggers validation
4. **Data Quality**: Missing critical fields flags for review
5. **OOD Detection**: Out-of-distribution patients need human review

**Safety Outcomes**:
- **RED**: Critical concern, force ESI 1-2, mandatory clinician review
- **YELLOW**: Caution needed, recommend escalation or validation
- **GREEN**: No safety concerns, accept ML prediction

**Algorithm**:

```python
class SafetyValidator:
    """
    Rule-based safety validation layer for critical condition detection.
    
    Runs after ML prediction to enforce safety criteria.
    Overrides ML prediction when life-threatening conditions detected.
    """
    
    def __init__(self):
        self.critical_criteria = self._load_critical_criteria()
        self.vital_thresholds = AGE_SPECIFIC_VITAL_RANGES  # From Redis
    
    def validate(
        self,
        patient_data: PatientData,
        features: ProcessedFeatures,
        ml_prediction: int,
        confidence: ConfidenceBreakdown
    ) -> SafetyValidation:
        """
        Perform comprehensive safety validation.
        
        Returns:
            SafetyValidation with outcome (RED/YELLOW/GREEN),
            triggered criteria, and recommended action
        """
        triggered = []
        
        # Validator 1: Critical Clinical Criteria
        critical_flags = self._check_critical_criteria(patient_data, features)
        if critical_flags:
            triggered.extend(critical_flags)
        
        # Validator 2: Vital Thresholds (age-specific)
        vital_flags = self._check_vital_thresholds(patient_data, features)
        if vital_flags:
            triggered.extend(vital_flags)
        
        # Validator 3: Confidence Check
        confidence_flags = self._check_confidence(confidence, ml_prediction)
        if confidence_flags:
            triggered.extend(confidence_flags)
        
        # Validator 4: Data Quality
        data_quality_flags = self._check_data_quality(features)
        if data_quality_flags:
            triggered.extend(data_quality_flags)
        
        # Validator 5: OOD Detection
        ood_flags = self._check_ood(confidence.pattern_recognition)
        if ood_flags:
            triggered.extend(ood_flags)
        
        # Determine outcome and action
        return self._determine_outcome(triggered, ml_prediction)
    
    def _check_critical_criteria(
        self, 
        patient_data: PatientData, 
        features: ProcessedFeatures
    ) -> List[str]:
        """
        Check hard-coded critical clinical criteria.
        
        Critical Criteria:
        1. Chest pain + age >50 (cardiac risk)
        2. SpO2 <85% (severe hypoxia)
        3. Altered consciousness (GCS <13 or mental_status != 'alert')
        4. Active bleeding + SBP <90 (hemorrhagic shock)
        5. Severe respiratory distress (RR >30 adult or SpO2 <90%)
        6. Status epilepticus or active seizure
        """
        flags = []
        
        # Criterion 1: Chest pain + age >50
        if (patient_data.symptoms and 
            'chest_pain' in patient_data.symptoms and 
            patient_data.demographics.age > 50):
            flags.append("CRITICAL: Chest pain in patient >50 years (cardiac risk)")
        
        # Criterion 2: Severe hypoxia
        if patient_data.vitals.spo2 is not None and patient_data.vitals.spo2 < 85:
            flags.append(f"CRITICAL: SpO2 {patient_data.vitals.spo2}% (severe hypoxia)")
        
        # Criterion 3: Altered consciousness
        if (patient_data.clinical.mental_status != 'alert' or 
            'altered_consciousness' in (patient_data.observations or [])):
            flags.append("CRITICAL: Altered level of consciousness")
        
        # Criterion 4: Active bleeding + hypotension
        if ('active_bleeding' in (patient_data.observations or []) and
            patient_data.vitals.bp_systolic is not None and
            patient_data.vitals.bp_systolic < 90):
            flags.append(f"CRITICAL: Active bleeding with hypotension (SBP {patient_data.vitals.bp_systolic})")
        
        # Criterion 5: Severe respiratory distress
        age_group = features.age_group
        if age_group in ['adult', 'geriatric']:
            if (patient_data.vitals.rr is not None and patient_data.vitals.rr > 30):
                flags.append(f"CRITICAL: Severe tachypnea (RR {patient_data.vitals.rr})")
        
        if patient_data.vitals.spo2 is not None and patient_data.vitals.spo2 < 90:
            flags.append(f"CRITICAL: Severe hypoxia (SpO2 {patient_data.vitals.spo2}%)")
        
        # Criterion 6: Active seizure
        if 'seizure' in patient_data.clinical.chief_complaint.lower():
            flags.append("CRITICAL: Active or recent seizure")
        
        return flags
    
    def _check_vital_thresholds(
        self, 
        patient_data: PatientData, 
        features: ProcessedFeatures
    ) -> List[str]:
        """
        Check age-specific critical vital thresholds.
        
        Uses age group to determine what's critically abnormal.
        Example: HR 160 is normal for infant, critical for adult.
        """
        flags = []
        age_group = features.age_group
        thresholds = self.vital_thresholds[age_group]
        
        # Heart rate extremes
        if patient_data.vitals.hr is not None:
            hr = patient_data.vitals.hr
            if hr < 40:  # Universal bradycardia threshold
                flags.append(f"VITAL: Severe bradycardia (HR {hr})")
            elif age_group in ['adult', 'geriatric'] and hr > 140:
                flags.append(f"VITAL: Severe tachycardia (HR {hr})")
            elif age_group == 'pediatric_adolescent' and hr > 140:
                flags.append(f"VITAL: Severe tachycardia for adolescent (HR {hr})")
        
        # Blood pressure extremes
        if patient_data.vitals.bp_systolic is not None:
            sbp = patient_data.vitals.bp_systolic
            if sbp < 80:
                flags.append(f"VITAL: Severe hypotension (SBP {sbp})")
            elif sbp > 180:
                flags.append(f"VITAL: Severe hypertension (SBP {sbp})")
        
        # Temperature extremes
        if patient_data.vitals.temperature is not None:
            temp = patient_data.vitals.temperature
            if temp < 35.0:
                flags.append(f"VITAL: Hypothermia (Temp {temp}°C)")
            elif temp > 39.5:
                flags.append(f"VITAL: High fever (Temp {temp}°C)")
        
        return flags
    
    def _check_confidence(
        self, 
        confidence: ConfidenceBreakdown, 
        ml_prediction: int
    ) -> List[str]:
        """
        Check if low confidence should trigger safety escalation.
        
        Rule: LOW confidence + ESI ≥3 → flag for validation
        """
        flags = []
        
        if confidence.level == "LOW" and ml_prediction >= 3:
            flags.append(
                f"CONFIDENCE: LOW confidence ({confidence.overall:.0f}%) "
                f"with ESI {ml_prediction} - consider escalation"
            )
        
        return flags
    
    def _check_data_quality(self, features: ProcessedFeatures) -> List[str]:
        """
        Check for missing critical data fields.
        
        Critical fields: age, HR, BP, SpO2, RR, chief_complaint
        """
        flags = []
        
        if features.data_completeness_score < 0.7:
            missing = []
            if features.get('is_missing_hr', False):
                missing.append('HR')
            if features.get('is_missing_bp', False):
                missing.append('BP')
            if features.get('is_missing_spo2', False):
                missing.append('SpO2')
            if features.get('is_missing_rr', False):
                missing.append('RR')
            
            if missing:
                flags.append(
                    f"DATA_QUALITY: Missing critical vitals: {', '.join(missing)} "
                    f"(completeness {features.data_completeness_score*100:.0f}%)"
                )
        
        return flags
    
    def _check_ood(self, pattern_recognition_score: float) -> List[str]:
        """
        Check if patient is out-of-distribution (unusual presentation).
        
        Threshold: pattern_recognition <30% triggers OOD flag
        """
        flags = []
        
        if pattern_recognition_score < 30:
            flags.append(
                f"OOD: Unusual patient presentation (pattern score {pattern_recognition_score:.0f}%) "
                "- exercise clinical caution"
            )
        
        return flags
    
    def _determine_outcome(
        self, 
        triggered: List[str], 
        ml_prediction: int
    ) -> SafetyValidation:
        """
        Determine overall safety outcome and recommended action.
        
        Logic:
        - Any CRITICAL flag → RED, force ESI 1-2
        - Any VITAL flag + ESI ≥3 → YELLOW, recommend escalation
        - CONFIDENCE/DATA_QUALITY/OOD flags → YELLOW, recommend validation
        - No flags → GREEN, accept ML prediction
        """
        critical_flags = [f for f in triggered if f.startswith('CRITICAL:')]
        vital_flags = [f for f in triggered if f.startswith('VITAL:')]
        other_flags = [f for f in triggered if not f.startswith('CRITICAL:') and not f.startswith('VITAL:')]
        
        if critical_flags:
            # Force ESI 1 or 2
            override_esi = 1 if len(critical_flags) > 1 or 'severe hypoxia' in str(critical_flags) else 2
            return SafetyValidation(
                outcome="RED",
                triggered_criteria=triggered,
                recommended_action=f"OVERRIDE: Force ESI {override_esi} due to critical criteria",
                override_esi=override_esi
            )
        
        if vital_flags and ml_prediction >= 3:
            # Recommend escalation
            recommended_esi = max(1, ml_prediction - 1)
            return SafetyValidation(
                outcome="YELLOW",
                triggered_criteria=triggered,
                recommended_action=f"ESCALATE: Consider ESI {recommended_esi} instead of ESI {ml_prediction}",
                override_esi=None  # Recommendation, not forced override
            )
        
        if other_flags:
            # Flag for clinical validation
            return SafetyValidation(
                outcome="YELLOW",
                triggered_criteria=triggered,
                recommended_action="VALIDATE: Clinical review recommended",
                override_esi=None
            )
        
        # No safety concerns
        return SafetyValidation(
            outcome="GREEN",
            triggered_criteria=[],
            recommended_action="ACCEPT: No safety concerns, ML prediction approved",
            override_esi=None
        )
```

**Safety Validation Output Example**:

```json
{
  "outcome": "RED",
  "triggered_criteria": [
    "CRITICAL: Chest pain in patient >50 years (cardiac risk)",
    "VITAL: Severe tachycardia (HR 142)"
  ],
  "recommended_action": "OVERRIDE: Force ESI 1 due to critical criteria",
  "override_esi": 1
}
```



#### 6. Deterioration Detector

**Purpose**: Monitor waiting patients for clinical decline. Generate alerts when vital signs worsen or wait times exceed safety thresholds.

**Model Architecture**: XGBoost Binary Classifier

**Why XGBoost (not CatBoost)**:
1. **Temporal Feature Optimization**: XGBoost faster for continuous numerical features (deltas, rates, trajectories)
2. **Inference Speed**: ~5-8ms vs ~10-12ms for CatBoost on this feature set
3. **Tree Structure**: Depth-first growing better for time-series patterns
4. **Proven Track Record**: Extensive use in medical deterioration prediction (MIMIC-III studies)

**Hyperparameters**:

```python
xgboost_params = {
    'objective': 'binary:logistic',
    'max_depth': 5,
    'learning_rate': 0.1,
    'n_estimators': 500,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'gamma': 0.1,
    'reg_alpha': 0.1,  # L1 regularization
    'reg_lambda': 1.0,  # L2 regularization
    'scale_pos_weight': 3,  # Class imbalance: deteriorations are rare (~10%)
    'early_stopping_rounds': 30,
    'eval_metric': ['logloss', 'auc', 'aucpr'],
    'random_state': 42
}
```

**Input Features** (30+ temporal features):

| Category | Features | Computation | Example |
|----------|----------|-------------|---------|
| **Vital Deltas** | delta_hr, delta_bp_sys, delta_spo2, delta_rr, delta_temp | current - initial | delta_hr = 110 - 88 = +22 |
| **Percent Changes** | pct_change_hr, pct_change_bp_sys, pct_change_spo2, pct_change_rr | (current - initial) / initial × 100 | pct_change_hr = 22/88 × 100 = 25% |
| **Rates of Change** | rate_hr, rate_spo2, rate_bp | delta / time_elapsed_minutes | rate_hr = +22 / 30min = +0.73 bpm/min |
| **Trajectories** | hr_trend, spo2_trend, bp_trend | +1 (improving), 0 (stable), -1 (worsening) | spo2_trend = -1 (dropping) |
| **Volatility** | hr_volatility, spo2_volatility | Standard deviation if multiple measurements | hr_volatility = std([88, 95, 102, 110]) |
| **Acceleration** | hr_acceleration, spo2_acceleration | rate_current - rate_previous | Worsening is accelerating? |
| **Multi-Parameter** | num_vitals_worsening, num_vitals_critical | Count of vitals with negative trends | 3 vitals worsening |
| **Contextual** | initial_esi, time_since_triage, wait_time_penalty | ESI level, minutes elapsed | initial_esi = 3, wait = 45min |
| **Clinical** | age_group, pain_score_change, mental_status_change | From initial triage | pain increased from 4→7 |

**Output**:
- **Status**: STABLE, DETERIORATING, UNCERTAIN
- **Score**: 0-100 (probability of deterioration × 100)
- **Raw SHAP Values**: Per-feature contributions

**Training Algorithm**:

```python
def train_deterioration_detector(training_data: pd.DataFrame) -> xgb.XGBClassifier:
    """
    Train deterioration detection model using temporal vital changes.
    
    Data Requirements:
    - Minimum 15,000 patients with multiple vital measurements
    - Positive class: deterioration leading to ICU, crash cart, or mortality
    - Negative class: stable or improving patients
    - Class imbalance: ~10% positive (use scale_pos_weight)
    
    Returns: Trained XGBoost model
    """
    # Engineer temporal features
    X = engineer_temporal_features(training_data)
    
    # Label: 1 if deteriorated (ICU/crash cart/mortality), 0 if stable
    y = training_data['deteriorated'].astype(int)
    
    # Train/val split (temporal split, not random)
    # Use last 20% of time period for validation to avoid data leakage
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    # Train model
    model = xgb.XGBClassifier(**xgboost_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=100
    )
    
    # Validate on held-out test set
    validate_deterioration_performance(model, X_val, y_val)
    
    return model

def engineer_temporal_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Create temporal features from initial and current vitals.
    
    Input: DataFrame with columns initial_hr, current_hr, initial_spo2, 
           current_spo2, time_elapsed_minutes, etc.
    
    Output: DataFrame with 30+ engineered features
    """
    features = pd.DataFrame()
    
    # Deltas
    features['delta_hr'] = data['current_hr'] - data['initial_hr']
    features['delta_spo2'] = data['current_spo2'] - data['initial_spo2']
    features['delta_bp_sys'] = data['current_bp_sys'] - data['initial_bp_sys']
    features['delta_rr'] = data['current_rr'] - data['initial_rr']
    
    # Percent changes (handle division by zero)
    features['pct_change_hr'] = 100 * features['delta_hr'] / (data['initial_hr'] + 1e-5)
    features['pct_change_spo2'] = 100 * features['delta_spo2'] / (data['initial_spo2'] + 1e-5)
    features['pct_change_bp_sys'] = 100 * features['delta_bp_sys'] / (data['initial_bp_sys'] + 1e-5)
    
    # Rates of change (per minute)
    time_elapsed = data['time_elapsed_minutes']
    features['rate_hr'] = features['delta_hr'] / (time_elapsed + 1e-5)
    features['rate_spo2'] = features['delta_spo2'] / (time_elapsed + 1e-5)
    features['rate_bp_sys'] = features['delta_bp_sys'] / (time_elapsed + 1e-5)
    
    # Trajectories (-1 worsening, 0 stable, +1 improving)
    features['hr_trend'] = np.sign(features['delta_hr'])  # Increasing HR = worsening (-1)
    features['spo2_trend'] = np.sign(features['delta_spo2'])  # Decreasing SpO2 = worsening (-1)
    features['bp_trend'] = np.sign(features['delta_bp_sys'])  # Decreasing BP = worsening (-1)
    
    # Multi-parameter aggregates
    features['num_vitals_worsening'] = (
        (features['hr_trend'] == -1).astype(int) +
        (features['spo2_trend'] == -1).astype(int) +
        (features['bp_trend'] == -1).astype(int)
    )
    
    features['num_vitals_critical'] = (
        (data['current_hr'] > 130).astype(int) +
        (data['current_spo2'] < 90).astype(int) +
        (data['current_bp_sys'] < 90).astype(int)
    )
    
    # Contextual features
    features['initial_esi'] = data['initial_esi']
    features['time_since_triage'] = time_elapsed
    features['age_group_encoded'] = data['age_group'].astype('category').cat.codes
    
    return features
```

**Deterioration Classification Logic**:

```python
def classify_deterioration(
    deterioration_score: float,  # 0-100
    num_vitals_worsening: int,
    confidence: float  # From model
) -> str:
    """
    Classify patient status from deterioration score.
    
    Thresholds:
    - DETERIORATING: score ≥60 OR multiple vitals worsening
    - STABLE: score <40 AND confidence >70%
    - UNCERTAIN: everything else
    """
    if deterioration_score >= 60 or num_vitals_worsening >= 3:
        return "DETERIORATING"
    elif deterioration_score < 40 and confidence > 0.7:
        return "STABLE"
    else:
        return "UNCERTAIN"
```

**Monitoring Intervals** (ESI-specific):

```python
MONITORING_INTERVALS = {
    1: None,  # ESI 1 already in resuscitation, not waiting
    2: 15,    # Every 15 minutes
    3: 30,    # Every 30 minutes
    4: 60,    # Every 60 minutes
    5: 60     # Every 60 minutes
}

WAIT_TIME_SAFETY_NETS = {
    2: 30,  # Auto-alert if ESI 2 waits >30 min
    3: 60,  # Auto-alert if ESI 3 waits >60 min
    4: None,
    5: None
}
```

**Deterioration Assessment Output**:

```json
{
  "status": "DETERIORATING",
  "score": 73.5,
  "vital_changes": [
    {
      "vital": "HR",
      "initial": 88,
      "current": 118,
      "delta": 30,
      "rate": 1.0,
      "trend": "worsening"
    },
    {
      "vital": "SpO2",
      "initial": 96,
      "current": 91,
      "delta": -5,
      "rate": -0.17,
      "trend": "worsening"
    }
  ],
  "explanation": "Patient deteriorating: HR increased 30 bpm (34%), SpO2 decreased to 91%. 2 vitals worsening.",
  "recommendation": "URGENT: Re-assess patient immediately and consider ESI escalation",
  "confidence": 0.87,
  "next_check_in_minutes": 15
}
```



#### 7. Surge Mode Sub-Prioritization Engine

**Purpose**: When multiple patients have same ESI level during overcrowding, rank them by urgency to determine treatment order.

**Design Decision**: Formula-based, NOT machine learning.

**Why Formula Instead of ML**:
1. **Explainability**: Clinicians must understand ranking logic instantly
2. **No Training Data**: No ground truth for "which ESI 3 is more urgent than another ESI 3"
3. **Clinical Interpretability**: Transparent weights for vital severity, condition urgency, deterioration, wait time
4. **Simplicity**: No model training, versioning, or retraining overhead
5. **Auditability**: Easy to debug why Patient A ranked above Patient B

**Sub-Score Formula**:

$$
\text{SubScore} = 0.4 \times V_{severity} + 0.3 \times C_{urgency} + 0.2 \times D_{rate} + 0.1 \times W_{penalty}
$$

Where:
- $V_{severity}$ = Vital Severity Score (0-100): How abnormal are vitals?
- $C_{urgency}$ = Condition Urgency Score (0-100): Time-sensitivity of chief complaint
- $D_{rate}$ = Deterioration Rate Score (0-100): How fast is patient declining?
- $W_{penalty}$ = Wait Time Penalty (0-100): How long has patient been waiting?

**Weight Rationale**:
- **40% Vital Severity**: Objective physiological instability is highest priority
- **30% Condition Urgency**: Some conditions are inherently time-sensitive (STEMI, stroke)
- **20% Deterioration**: Worsening patients need intervention before crisis
- **10% Wait Time**: Fairness penalty prevents indefinite waiting, but lower weight than clinical factors

**Component Algorithms**:

```python
class SurgeEngine:
    """
    Formula-based sub-prioritization for patients with same ESI level.
    
    Used during surge mode to rank treatment order within ESI categories.
    """
    
    def __init__(self):
        # Load condition urgency lookup table from Redis
        self.condition_urgency_table = load_condition_urgency_table()
        
        # Component weights
        self.weights = {
            'vital_severity': 0.4,
            'condition_urgency': 0.3,
            'deterioration_rate': 0.2,
            'wait_time_penalty': 0.1
        }
    
    def compute_sub_score(
        self,
        patient_data: PatientData,
        features: ProcessedFeatures,
        deterioration_score: float,
        time_since_triage_minutes: int
    ) -> float:
        """
        Compute 0-100 sub-prioritization score for surge mode ranking.
        
        Higher score = higher priority within same ESI level
        
        Args:
            patient_data: Raw patient data
            features: Processed features with vital deviations
            deterioration_score: 0-100 from Deterioration Detector
            time_since_triage_minutes: Wait time
        
        Returns:
            Sub-score 0-100
        """
        # Component 1: Vital Severity (0-100)
        vital_severity = self._compute_vital_severity(features)
        
        # Component 2: Condition Urgency (0-100)
        condition_urgency = self._compute_condition_urgency(
            patient_data.clinical.chief_complaint_category,
            patient_data.symptoms
        )
        
        # Component 3: Deterioration Rate (0-100)
        deterioration_rate = deterioration_score  # Already 0-100
        
        # Component 4: Wait Time Penalty (0-100)
        wait_penalty = self._compute_wait_penalty(time_since_triage_minutes)
        
        # Weighted sum
        sub_score = (
            self.weights['vital_severity'] * vital_severity +
            self.weights['condition_urgency'] * condition_urgency +
            self.weights['deterioration_rate'] * deterioration_rate +
            self.weights['wait_time_penalty'] * wait_penalty
        )
        
        return float(sub_score)
    
    def _compute_vital_severity(self, features: ProcessedFeatures) -> float:
        """
        Vital severity from age-normalized deviations.
        
        Logic:
        - Each vital deviation contributes to severity
        - Deviation >2 = severe (contributes 100)
        - Deviation 1-2 = moderate (contributes 50)
        - Deviation <1 = mild (contributes 25)
        - Average across all vitals
        
        Example:
        - HR deviation = 2.3 (severe) → 100
        - SpO2 deviation = -1.5 (moderate) → 50
        - BP deviation = 0.8 (mild) → 25
        - Average = (100 + 50 + 25) / 3 = 58.3
        """
        vital_deviations = [
            features.hr_deviation,
            features.spo2_deviation,
            features.bp_sys_deviation,
            features.rr_deviation,
            features.temp_deviation
        ]
        
        severity_scores = []
        for deviation in vital_deviations:
            if deviation is None:
                continue
            
            abs_deviation = abs(deviation)
            if abs_deviation >= 2.0:
                severity_scores.append(100)
            elif abs_deviation >= 1.0:
                severity_scores.append(50)
            else:
                severity_scores.append(25 * abs_deviation)
        
        if not severity_scores:
            return 50.0  # Default if no vitals available
        
        return float(np.mean(severity_scores))
    
    def _compute_condition_urgency(
        self, 
        chief_complaint: str, 
        symptoms: List[str]
    ) -> float:
        """
        Condition urgency from chief complaint and symptoms.
        
        Uses lookup table of time-sensitive conditions:
        - STEMI / MI: 95 (door-to-balloon time critical)
        - Stroke: 90 (golden hour for thrombolysis)
        - Severe trauma: 90 (golden hour)
        - Anaphylaxis: 85 (rapid deterioration)
        - Sepsis: 80 (time to antibiotics)
        - Respiratory distress: 70
        - Abdominal pain: 50 (varies widely)
        - Minor injuries: 20
        
        Also boosts score if high-risk symptoms present (chest pain, SOB, bleeding)
        """
        # Base score from chief complaint
        base_score = self.condition_urgency_table.get(chief_complaint, 50.0)
        
        # Symptom modifiers
        symptom_boost = 0
        if 'chest_pain' in symptoms:
            symptom_boost += 15
        if 'shortness_of_breath' in symptoms:
            symptom_boost += 10
        if 'active_bleeding' in symptoms:
            symptom_boost += 10
        if 'altered_consciousness' in symptoms:
            symptom_boost += 20
        
        # Combine (cap at 100)
        urgency = min(100, base_score + symptom_boost)
        
        return float(urgency)
    
    def _compute_wait_penalty(self, wait_minutes: int) -> float:
        """
        Wait time penalty (0-100).
        
        Linear scaling with cap:
        - 0 min → 0
        - 60 min → 50
        - 120 min → 100
        - >120 min → 100 (capped)
        
        Rationale: Waiting shouldn't override clinical severity, but 
        prolonged waits increase risk and are unfair.
        """
        penalty = (wait_minutes / 120.0) * 100
        return float(min(100, penalty))


# Condition Urgency Lookup Table (stored in Redis)
CONDITION_URGENCY_TABLE = {
    'chest_pain_cardiac': 95,
    'stemi': 95,
    'stroke_cva': 90,
    'trauma_severe': 90,
    'anaphylaxis': 85,
    'sepsis': 80,
    'respiratory_distress': 75,
    'altered_mental_status': 70,
    'gi_bleed': 70,
    'severe_pain': 60,
    'abdominal_pain': 50,
    'fever': 40,
    'laceration': 30,
    'minor_trauma': 25,
    'rash': 20,
    'cold_flu_symptoms': 15
}
```

**Ranking Algorithm**:

```python
def rank_patients_in_surge(patients: List[PatientRecord]) -> List[PatientRecord]:
    """
    Rank patients for treatment order during surge conditions.
    
    Sorting priority:
    1. ESI level (1 highest priority)
    2. Sub-score (100 highest priority)
    3. Arrival time (earliest first, tiebreaker)
    
    Args:
        patients: List of waiting patients with ESI, sub_score, arrival_time
    
    Returns:
        Sorted list with highest priority first
    """
    return sorted(
        patients,
        key=lambda p: (
            p.esi_level,              # Primary: ESI 1 before ESI 2, etc.
            -p.sub_score,             # Secondary: Higher sub-score first (negate for descending)
            p.arrival_time            # Tertiary: Earlier arrival first
        )
    )
```

**Example Sub-Score Calculation**:

```
Patient A (ESI 3):
- Vital Severity: 75 (HR deviation 2.1, SpO2 deviation 1.8)
- Condition Urgency: 60 (abdominal pain)
- Deterioration Rate: 40 (stable but slightly elevated HR)
- Wait Penalty: 25 (30 minutes)
- Sub-Score = 0.4×75 + 0.3×60 + 0.2×40 + 0.1×25 = 30 + 18 + 8 + 2.5 = 58.5

Patient B (ESI 3):
- Vital Severity: 50 (mild tachycardia only)
- Condition Urgency: 75 (respiratory distress)
- Deterioration Rate: 65 (SpO2 dropping)
- Wait Penalty: 50 (60 minutes)
- Sub-Score = 0.4×50 + 0.3×75 + 0.2×65 + 0.1×50 = 20 + 22.5 + 13 + 5 = 60.5

Result: Patient B ranked higher (60.5 > 58.5) despite similar ESI
```



#### 8. SHAP-Based Explainability System

**Purpose**: Generate human-readable explanations showing which factors drove each prediction. Critical for clinical trust and override decisions.

**Why SHAP**:
1. **Model-Agnostic**: Works with any ML model (CatBoost, XGBoost, future models)
2. **Additive Attribution**: Sum of SHAP values = prediction - baseline (interpretable math)
3. **TreeExplainer Speed**: Optimized for tree-based models, <100ms computation
4. **Individual Predictions**: Explains specific patient, not just global feature importance
5. **Directional**: Shows if feature increased or decreased risk

**Algorithm**:

```python
import shap

class ExplainabilitySystem:
    """
    SHAP-based explanation generation for ML predictions.
    
    Generates top 3-5 contributing factors with human-readable descriptions.
    Target latency: <500ms total (SHAP + formatting)
    """
    
    def __init__(self, esi_model, deterioration_model):
        # Initialize SHAP explainers (one-time cost)
        self.esi_explainer = shap.TreeExplainer(esi_model)
        self.deterioration_explainer = shap.TreeExplainer(deterioration_model)
        
        # Human-readable feature names
        self.feature_names = load_feature_name_mapping()
        
        # Severity thresholds for color coding
        self.severity_thresholds = {
            'critical': 0.5,   # SHAP value >0.5 ESI levels
            'concerning': 0.2,  # SHAP value 0.2-0.5
            'normal': 0.0      # SHAP value <0.2
        }
    
    def explain_esi_prediction(
        self,
        features: ProcessedFeatures,
        predicted_esi: int,
        probability_distribution: np.ndarray
    ) -> Explanation:
        """
        Generate explanation for ESI prediction.
        
        Args:
            features: Processed patient features
            predicted_esi: Predicted ESI level (1-5)
            probability_distribution: Model probabilities [p1, p2, p3, p4, p5]
        
        Returns:
            Explanation with top contributing factors and formatted text
        """
        # Compute SHAP values
        feature_vector = features.to_numpy()
        shap_values = self.esi_explainer.shap_values(feature_vector)
        
        # Extract SHAP values for predicted class
        predicted_class_idx = predicted_esi - 1  # ESI 1→index 0, etc.
        shap_for_prediction = shap_values[predicted_class_idx][0]  # Single patient
        
        # Get top N features by absolute SHAP value
        top_n = 5
        feature_names = list(features.keys())
        feature_importance = [
            (name, shap_val, features[name]) 
            for name, shap_val in zip(feature_names, shap_for_prediction)
        ]
        
        # Sort by absolute SHAP value
        feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
        top_features = feature_importance[:top_n]
        
        # Format into human-readable explanation
        explanation_text, top_factors = self._format_explanation(
            top_features, 
            predicted_esi
        )
        
        return Explanation(
            text=explanation_text,
            top_factors=top_factors,
            shap_values=shap_for_prediction.tolist()
        )
    
    def explain_deterioration(
        self,
        temporal_features: Dict,
        deterioration_score: float
    ) -> Explanation:
        """
        Generate explanation for deterioration assessment.
        
        Focus on vital sign changes that contributed most to deterioration score.
        """
        # Compute SHAP values for deterioration model
        feature_vector = np.array([temporal_features[k] for k in sorted(temporal_features.keys())])
        shap_values = self.deterioration_explainer.shap_values(feature_vector)[0]
        
        # Get top contributing changes
        top_n = 3
        feature_names = sorted(temporal_features.keys())
        feature_importance = [
            (name, shap_val, temporal_features[name])
            for name, shap_val in zip(feature_names, shap_values)
        ]
        
        feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
        top_changes = feature_importance[:top_n]
        
        # Format explanation focusing on vital changes
        explanation_text = self._format_deterioration_explanation(
            top_changes,
            deterioration_score
        )
        
        top_factors = [
            {
                'feature': self._humanize_feature_name(name),
                'value': value,
                'contribution': float(shap_val),
                'direction': 'worsening' if shap_val > 0 else 'stable'
            }
            for name, shap_val, value in top_changes
        ]
        
        return Explanation(
            text=explanation_text,
            top_factors=top_factors,
            shap_values=shap_values.tolist()
        )
    
    def _format_explanation(
        self, 
        top_features: List[Tuple[str, float, Any]], 
        predicted_esi: int
    ) -> Tuple[str, List[Dict]]:
        """
        Format top features into human-readable explanation.
        
        Example output:
        "ESI 2 recommended based on: (1) Heart rate 118 bpm - elevated for age 
        (CRITICAL), (2) SpO2 92% - below normal (CONCERNING), (3) Age 68 years 
        - geriatric patient (NORMAL)"
        """
        explanation_parts = [f"ESI {predicted_esi} recommended based on:"]
        top_factors = []
        
        for idx, (feature_name, shap_value, feature_value) in enumerate(top_features, 1):
            # Humanize feature name
            human_name = self._humanize_feature_name(feature_name)
            
            # Determine severity
            severity = self._classify_severity(abs(shap_value))
            
            # Determine direction
            direction = "increases urgency" if shap_value > 0 else "decreases urgency"
            
            # Format value
            formatted_value = self._format_value(feature_name, feature_value)
            
            # Add to explanation
            explanation_parts.append(
                f"({idx}) {human_name} {formatted_value} - {direction} ({severity.upper()})"
            )
            
            # Add to structured factors
            top_factors.append({
                'feature': human_name,
                'value': formatted_value,
                'contribution': float(shap_value),
                'direction': direction,
                'severity': severity
            })
        
        explanation_text = ", ".join(explanation_parts)
        
        return explanation_text, top_factors
    
    def _format_deterioration_explanation(
        self,
        top_changes: List[Tuple[str, float, Any]],
        deterioration_score: float
    ) -> str:
        """
        Format deterioration explanation focusing on vital changes.
        
        Example:
        "Deterioration score 73/100. Key changes: HR increased 30 bpm (34%), 
        SpO2 decreased to 91% (-5%), BP stable."
        """
        status = "Deteriorating" if deterioration_score >= 60 else "Stable"
        explanation = f"{status} (score {deterioration_score:.0f}/100). Key changes: "
        
        change_descriptions = []
        for feature_name, shap_value, feature_value in top_changes:
            human_name = self._humanize_feature_name(feature_name)
            
            if 'delta' in feature_name:
                # Delta features
                direction = "increased" if feature_value > 0 else "decreased"
                change_descriptions.append(
                    f"{human_name} {direction} {abs(feature_value):.0f}"
                )
            elif 'rate' in feature_name:
                # Rate features
                change_descriptions.append(
                    f"{human_name} changing at {feature_value:.1f} per minute"
                )
            else:
                change_descriptions.append(
                    f"{human_name}: {feature_value}"
                )
        
        explanation += ", ".join(change_descriptions)
        
        return explanation
    
    def _humanize_feature_name(self, feature_name: str) -> str:
        """
        Convert technical feature names to human-readable labels.
        
        Examples:
        - 'hr_deviation' → 'Heart rate'
        - 'chief_complaint_category' → 'Chief complaint'
        - 'delta_hr' → 'HR change'
        - 'spo2_deviation' → 'Oxygen saturation'
        """
        return self.feature_names.get(feature_name, feature_name.replace('_', ' ').title())
    
    def _format_value(self, feature_name: str, value: Any) -> str:
        """
        Format feature value with appropriate units and precision.
        
        Examples:
        - hr_deviation: 2.3 → "elevated 2.3 SD"
        - age: 68 → "68 years"
        - chief_complaint_category: "chest_pain" → "chest pain"
        """
        if value is None:
            return "not recorded"
        
        # Vital deviations
        if 'deviation' in feature_name:
            if abs(value) >= 2.0:
                severity = "severely"
            elif abs(value) >= 1.0:
                severity = "moderately"
            else:
                severity = "slightly"
            
            direction = "elevated" if value > 0 else "low"
            return f"{severity} {direction} ({value:.1f} SD)"
        
        # Age
        if feature_name == 'age':
            return f"{value} years"
        
        # Vitals with units
        if 'hr' in feature_name.lower():
            return f"{value} bpm"
        if 'spo2' in feature_name.lower():
            return f"{value}%"
        if 'bp' in feature_name.lower():
            return f"{value} mmHg"
        if 'rr' in feature_name.lower():
            return f"{value} breaths/min"
        if 'temp' in feature_name.lower():
            return f"{value}°C"
        
        # Categorical
        if isinstance(value, str):
            return value.replace('_', ' ')
        
        # Numeric default
        return f"{value:.1f}"
    
    def _classify_severity(self, abs_shap_value: float) -> str:
        """
        Classify contribution severity for color coding.
        
        SHAP value interpretation:
        - >0.5 ESI levels of contribution → CRITICAL (red)
        - 0.2-0.5 → CONCERNING (yellow)
        - <0.2 → NORMAL (green)
        """
        if abs_shap_value >= self.severity_thresholds['critical']:
            return 'critical'
        elif abs_shap_value >= self.severity_thresholds['concerning']:
            return 'concerning'
        else:
            return 'normal'


# Feature name mapping (stored in config)
FEATURE_NAME_MAPPING = {
    'hr': 'Heart rate',
    'hr_deviation': 'Heart rate',
    'bp_systolic': 'Blood pressure (systolic)',
    'bp_sys_deviation': 'Blood pressure',
    'spo2': 'Oxygen saturation',
    'spo2_deviation': 'Oxygen saturation',
    'rr': 'Respiratory rate',
    'rr_deviation': 'Respiratory rate',
    'temperature': 'Temperature',
    'temp_deviation': 'Temperature',
    'age': 'Patient age',
    'age_group': 'Age group',
    'chief_complaint_category': 'Chief complaint',
    'pain_score': 'Pain level',
    'mental_status': 'Mental status',
    'arrival_mode': 'Arrival mode',
    'symptom_count': 'Number of symptoms',
    'data_completeness_score': 'Data completeness',
    'pain_underreported': 'Pain under-reporting indicator',
    'severity_underreported': 'Severity under-reporting indicator',
    'delta_hr': 'HR change',
    'delta_spo2': 'SpO2 change',
    'rate_hr': 'HR rate of change',
    'num_vitals_worsening': 'Number of worsening vitals',
    'time_since_triage': 'Wait time'
}
```

**Example Explanation Output**:

```json
{
  "text": "ESI 2 recommended based on: (1) Heart rate 118 bpm - moderately elevated (2.1 SD) - increases urgency (CRITICAL), (2) Oxygen saturation 92% - moderately low (-1.8 SD) - increases urgency (CONCERNING), (3) Patient age 68 years - geriatric patient - increases urgency (NORMAL), (4) Chief complaint chest pain - cardiac concern - increases urgency (CRITICAL), (5) Blood pressure 145/90 mmHg - slightly elevated (0.8 SD) - increases urgency (NORMAL)",
  "top_factors": [
    {
      "feature": "Heart rate",
      "value": "118 bpm (moderately elevated, 2.1 SD)",
      "contribution": 0.73,
      "direction": "increases urgency",
      "severity": "critical"
    },
    {
      "feature": "Oxygen saturation",
      "value": "92% (moderately low, -1.8 SD)",
      "contribution": 0.45,
      "direction": "increases urgency",
      "severity": "concerning"
    },
    {
      "feature": "Patient age",
      "value": "68 years",
      "contribution": 0.31,
      "direction": "increases urgency",
      "severity": "normal"
    },
    {
      "feature": "Chief complaint",
      "value": "chest pain",
      "contribution": 0.82,
      "direction": "increases urgency",
      "severity": "critical"
    },
    {
      "feature": "Blood pressure",
      "value": "145/90 mmHg (slightly elevated, 0.8 SD)",
      "contribution": 0.12,
      "direction": "increases urgency",
      "severity": "normal"
    }
  ],
  "shap_values": [0.73, 0.45, 0.31, 0.82, 0.12, ...]
}
```



#### 9. Override Tracking and Learning System

**Purpose**: Log clinician overrides, analyze patterns, feed retraining pipeline to improve model over time.

**Key Insight**: Overrides are not failures—they're learning opportunities. Systematic override patterns reveal model blind spots.

**Algorithm**:

```python
class OverrideTracker:
    """
    Track, analyze, and learn from clinician overrides of ML predictions.
    
    Goals:
    1. Log all overrides with context
    2. Detect systematic error patterns (e.g., "under-triages women 45-55 with chest pain")
    3. Generate retraining recommendations
    4. Provide dashboard metrics
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.pattern_detector = OverridePatternDetector()
    
    def log_override(
        self,
        prediction_id: str,
        ml_predicted_esi: int,
        ml_confidence_breakdown: Dict,
        clinician_final_esi: int,
        override_reason_category: str,
        override_reason_text: str,
        clinician_id: str,
        patient_features: Dict,
        timestamp: datetime
    ) -> None:
        """
        Log a clinician override to database.
        
        Override reason categories:
        - 'clinical_judgment': Subjective assessment overrides ML
        - 'additional_information': Clinician has info ML didn't
        - 'safety_concern': Clinician escalates due to risk aversion
        - 'ml_error': Clinician believes ML is clearly wrong
        - 'patient_preference': Patient requests specific care level
        - 'resource_constraint': Downgrade due to capacity
        """
        override_entry = {
            'prediction_id': prediction_id,
            'timestamp': timestamp,
            'ml_predicted_esi': ml_predicted_esi,
            'ml_confidence': ml_confidence_breakdown,
            'clinician_final_esi': clinician_final_esi,
            'override_direction': 'escalation' if clinician_final_esi < ml_predicted_esi else 'de-escalation',
            'override_magnitude': abs(clinician_final_esi - ml_predicted_esi),
            'override_reason_category': override_reason_category,
            'override_reason_text': override_reason_text,
            'clinician_id': clinician_id,
            'patient_features': patient_features,
            'outcome': None  # Populated later when available
        }
        
        # Write to PostgreSQL audit log
        self.db.insert('override_log', override_entry)
    
    def log_outcome(
        self,
        prediction_id: str,
        disposition: str,  # 'discharge', 'admit', 'icu', 'transfer'
        adverse_event: bool,
        time_to_treatment_minutes: int
    ) -> None:
        """
        Log eventual patient outcome to validate override decision.
        
        Allows retrospective analysis: Did override improve patient outcome?
        """
        outcome_entry = {
            'prediction_id': prediction_id,
            'disposition': disposition,
            'adverse_event': adverse_event,
            'time_to_treatment_minutes': time_to_treatment_minutes,
            'updated_at': datetime.now()
        }
        
        self.db.update('override_log', {'prediction_id': prediction_id}, outcome_entry)
    
    def analyze_patterns(self, time_window_days: int = 30) -> PatternAnalysis:
        """
        Analyze override patterns over rolling time window.
        
        Detects:
        1. High override rate for specific demographics
        2. Systematic under-triage (e.g., always escalates ESI 4→3 for chest pain)
        3. Low-confidence regions (e.g., pediatric asthma consistently overridden)
        4. Clinician-specific patterns (some clinicians override 40%, others 5%)
        
        Returns:
            PatternAnalysis with detected patterns and recommendations
        """
        # Query overrides from last N days
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        overrides = self.db.query(
            'override_log',
            filters={'timestamp': {'>=': cutoff_date}}
        )
        
        total_predictions = self.db.count(
            'predictions',
            filters={'timestamp': {'>=': cutoff_date}}
        )
        
        # Compute overall metrics
        total_overrides = len(overrides)
        override_rate = total_overrides / total_predictions if total_predictions > 0 else 0
        
        # Analyze by demographics
        demographic_patterns = self._analyze_by_demographics(overrides)
        
        # Analyze by chief complaint
        complaint_patterns = self._analyze_by_complaint(overrides)
        
        # Analyze by ESI level
        esi_patterns = self._analyze_by_esi(overrides)
        
        # Detect systematic errors
        systematic_errors = self._detect_systematic_errors(
            demographic_patterns,
            complaint_patterns,
            esi_patterns
        )
        
        # Generate retraining recommendations
        retraining_recommendations = self._generate_retraining_recommendations(
            systematic_errors
        )
        
        return PatternAnalysis(
            time_window_days=time_window_days,
            total_predictions=total_predictions,
            total_overrides=total_overrides,
            override_rate=override_rate,
            demographic_patterns=demographic_patterns,
            complaint_patterns=complaint_patterns,
            esi_patterns=esi_patterns,
            systematic_errors=systematic_errors,
            retraining_recommendations=retraining_recommendations
        )
    
    def _analyze_by_demographics(self, overrides: List[Dict]) -> Dict:
        """
        Analyze override patterns by age group and sex.
        
        Example finding:
        - Female patients 45-55: 23% override rate (escalations)
        - Male patients 45-55: 12% override rate
        → Potential under-triage of women with cardiac symptoms
        """
        patterns = {}
        
        for age_group in ['pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 'adult', 'geriatric']:
            for sex in ['male', 'female']:
                # Filter overrides for this demographic
                demo_overrides = [
                    o for o in overrides
                    if o['patient_features'].get('age_group') == age_group
                    and o['patient_features'].get('sex') == sex
                ]
                
                if len(demo_overrides) >= 10:  # Minimum sample size
                    override_rate = len(demo_overrides) / self._count_predictions_for_demo(age_group, sex)
                    
                    patterns[f"{age_group}_{sex}"] = {
                        'override_count': len(demo_overrides),
                        'override_rate': override_rate,
                        'avg_escalation': np.mean([
                            o['override_magnitude'] 
                            for o in demo_overrides 
                            if o['override_direction'] == 'escalation'
                        ]),
                        'primary_reasons': self._top_override_reasons(demo_overrides)
                    }
        
        return patterns
    
    def _detect_systematic_errors(
        self,
        demographic_patterns: Dict,
        complaint_patterns: Dict,
        esi_patterns: Dict
    ) -> List[SystematicError]:
        """
        Detect systematic model errors from override patterns.
        
        Threshold: Override rate >15% for any specific pattern triggers detection.
        """
        errors = []
        
        # Check demographic patterns
        for demo, stats in demographic_patterns.items():
            if stats['override_rate'] > 0.15:
                errors.append(SystematicError(
                    pattern_type='demographic',
                    pattern=demo,
                    override_rate=stats['override_rate'],
                    description=f"High override rate ({stats['override_rate']:.1%}) for {demo}",
                    sample_size=stats['override_count'],
                    primary_reasons=stats['primary_reasons']
                ))
        
        # Check complaint patterns
        for complaint, stats in complaint_patterns.items():
            if stats['override_rate'] > 0.15:
                errors.append(SystematicError(
                    pattern_type='chief_complaint',
                    pattern=complaint,
                    override_rate=stats['override_rate'],
                    description=f"High override rate ({stats['override_rate']:.1%}) for {complaint}",
                    sample_size=stats['override_count'],
                    primary_reasons=stats['primary_reasons']
                ))
        
        return errors
    
    def _generate_retraining_recommendations(
        self,
        systematic_errors: List[SystematicError]
    ) -> List[RetrainingRecommendation]:
        """
        Generate actionable retraining recommendations from detected errors.
        """
        recommendations = []
        
        for error in systematic_errors:
            if error.override_rate > 0.20:
                priority = 'HIGH'
            elif error.override_rate > 0.15:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            recommendations.append(RetrainingRecommendation(
                priority=priority,
                error_pattern=error,
                recommended_action=self._determine_action(error),
                data_needed=self._determine_data_needs(error),
                expected_impact=f"Reduce override rate from {error.override_rate:.1%} to <10%"
            ))
        
        return recommendations
    
    def _determine_action(self, error: SystematicError) -> str:
        """
        Determine recommended action based on error pattern.
        """
        if error.pattern_type == 'demographic':
            return f"Collect additional training data for {error.pattern}, retrain with class weights"
        elif error.pattern_type == 'chief_complaint':
            return f"Add feature engineering for {error.pattern}, retrain with augmented features"
        else:
            return "Retrain model with override data as ground truth"
    
    def generate_dashboard_metrics(self, time_window_days: int = 30) -> Dict:
        """
        Generate metrics for monitoring dashboard.
        
        Returns:
            Dictionary with agreement rate, override breakdown, trends
        """
        analysis = self.analyze_patterns(time_window_days)
        
        return {
            'agreement_rate': 1 - analysis.override_rate,
            'override_rate': analysis.override_rate,
            'override_breakdown': {
                'escalations': self._count_by_direction(analysis, 'escalation'),
                'de_escalations': self._count_by_direction(analysis, 'de-escalation')
            },
            'override_reasons': self._aggregate_override_reasons(analysis),
            'systematic_errors': len(analysis.systematic_errors),
            'retraining_recommended': len(analysis.retraining_recommendations) > 0,
            'trends': self._compute_trends(time_window_days)
        }


class OverridePatternDetector:
    """
    Statistical pattern detection for systematic model errors.
    
    Uses chi-square tests and confidence intervals to identify
    statistically significant override patterns.
    """
    
    def detect_significant_patterns(
        self,
        overrides: List[Dict],
        baseline_override_rate: float,
        significance_level: float = 0.05
    ) -> List[Dict]:
        """
        Detect statistically significant override patterns.
        
        Uses chi-square test: Is override rate for this group significantly
        different from baseline?
        """
        # Implementation would use scipy.stats.chi2_contingency
        pass
```

**Dashboard Metrics Example**:

```json
{
  "time_window_days": 30,
  "agreement_rate": 0.87,
  "override_rate": 0.13,
  "override_breakdown": {
    "escalations": 78,
    "de_escalations": 22
  },
  "override_reasons": {
    "clinical_judgment": 45,
    "additional_information": 30,
    "safety_concern": 15,
    "ml_error": 8,
    "patient_preference": 2
  },
  "systematic_errors": 2,
  "retraining_recommended": true,
  "detected_patterns": [
    {
      "pattern": "adult_female + chest_pain",
      "override_rate": 0.23,
      "sample_size": 43,
      "description": "High override rate for adult women with chest pain",
      "recommendation": "Retrain with additional weight on this demographic"
    },
    {
      "pattern": "pediatric_child + fever",
      "override_rate": 0.18,
      "sample_size": 31,
      "description": "High override rate for pediatric fever cases",
      "recommendation": "Add fever-specific features for pediatric model"
    }
  ],
  "trends": {
    "week_1": 0.11,
    "week_2": 0.13,
    "week_3": 0.14,
    "week_4": 0.13
  }
}
```



## Data Models

### Input Data Model

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ArrivalMode(str, Enum):
    WALK_IN = "walk_in"
    AMBULANCE = "ambulance"
    POLICE = "police"
    TRANSFER = "transfer"

class MentalStatus(str, Enum):
    ALERT = "alert"
    CONFUSED = "confused"
    DROWSY = "drowsy"
    UNRESPONSIVE = "unresponsive"

class Demographics(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: str = Field(..., regex="^(male|female|other)$")
    
    @validator('age')
    def compute_age_group(cls, age):
        if age <= 2:
            return 'pediatric_infant'
        elif age <= 12:
            return 'pediatric_child'
        elif age <= 17:
            return 'pediatric_adolescent'
        elif age <= 64:
            return 'adult'
        else:
            return 'geriatric'

class Vitals(BaseModel):
    hr: Optional[int] = Field(None, ge=20, le=250, description="Heart rate in bpm")
    bp_systolic: Optional[int] = Field(None, ge=50, le=250, description="Systolic BP in mmHg")
    bp_diastolic: Optional[int] = Field(None, ge=30, le=150, description="Diastolic BP in mmHg")
    spo2: Optional[int] = Field(None, ge=50, le=100, description="Oxygen saturation in %")
    rr: Optional[int] = Field(None, ge=5, le=60, description="Respiratory rate in breaths/min")
    temperature: Optional[float] = Field(None, ge=32.0, le=42.0, description="Temperature in Celsius")
    
    @validator('bp_systolic', 'bp_diastolic')
    def validate_bp(cls, v, values):
        if 'bp_systolic' in values and 'bp_diastolic' in values:
            if values['bp_systolic'] is not None and v is not None:
                if values['bp_systolic'] <= v:
                    raise ValueError("Systolic BP must be greater than diastolic BP")
        return v

class Clinical(BaseModel):
    chief_complaint: str = Field(..., min_length=1, max_length=500)
    chief_complaint_category: str = Field(..., description="Categorized complaint from lookup table")
    pain_score: Optional[int] = Field(None, ge=0, le=10, description="Pain scale 0-10")
    arrival_mode: ArrivalMode
    mental_status: MentalStatus

class MedicalHistory(BaseModel):
    cardiac_history: bool = False
    respiratory_history: bool = False
    diabetes: bool = False
    hypertension: bool = False
    on_medications: bool = False
    recent_hospitalization: bool = False

class PatientData(BaseModel):
    """
    Complete patient data for ESI prediction.
    
    Required fields: demographics, vitals (partial), clinical
    Optional fields: symptoms, history, observations
    """
    request_id: str = Field(..., description="Unique request identifier for tracing")
    demographics: Demographics
    vitals: Vitals
    clinical: Clinical
    symptoms: Optional[List[str]] = Field(default=[], description="List of reported symptoms")
    history: Optional[MedicalHistory] = Field(default=MedicalHistory())
    observations: Optional[List[str]] = Field(default=[], description="Clinical observations")
    metadata: Optional[Dict] = Field(default={}, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('vitals')
    def validate_required_vitals(cls, v):
        """Ensure at least critical vitals are present"""
        required = ['hr', 'bp_systolic', 'spo2', 'rr']
        missing = [field for field in required if getattr(v, field) is None]
        
        if len(missing) > 2:  # Allow max 2 missing critical vitals
            raise ValueError(f"Too many missing critical vitals: {missing}")
        
        return v
```

### Output Data Model

```python
class ConfidenceBreakdown(BaseModel):
    model_certainty: float = Field(..., ge=0, le=100)
    data_completeness: float = Field(..., ge=0, le=100)
    clinical_consistency: float = Field(..., ge=0, le=100)
    pattern_recognition: float = Field(..., ge=0, le=100)
    overall: float = Field(..., ge=0, le=100)
    level: str = Field(..., regex="^(HIGH|MEDIUM|LOW)$")

class SafetyValidation(BaseModel):
    outcome: str = Field(..., regex="^(RED|YELLOW|GREEN)$")
    triggered_criteria: List[str]
    recommended_action: str
    override_esi: Optional[int] = Field(None, ge=1, le=5)

class ExplanationFactor(BaseModel):
    feature: str
    value: str
    contribution: float
    direction: str
    severity: str = Field(..., regex="^(critical|concerning|normal)$")

class Explanation(BaseModel):
    text: str
    top_factors: List[ExplanationFactor]
    shap_values: Optional[List[float]] = None

class PredictionResponse(BaseModel):
    """
    Complete response for ESI prediction request.
    
    Includes prediction, confidence, safety validation, explanation, and metadata.
    """
    request_id: str
    esi_prediction: int = Field(..., ge=1, le=5, description="Predicted ESI level")
    probability_distribution: List[float] = Field(..., min_items=5, max_items=5)
    confidence_breakdown: ConfidenceBreakdown
    safety_flag: SafetyValidation
    explanation: Explanation
    sub_score: Optional[float] = Field(None, ge=0, le=100, description="Surge mode sub-score")
    recommendations: List[str] = Field(default=[])
    model_version: str
    inference_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_123abc",
                "esi_prediction": 2,
                "probability_distribution": [0.05, 0.72, 0.18, 0.04, 0.01],
                "confidence_breakdown": {
                    "model_certainty": 92.3,
                    "data_completeness": 85.0,
                    "clinical_consistency": 65.0,
                    "pattern_recognition": 78.5,
                    "overall": 81.7,
                    "level": "HIGH"
                },
                "safety_flag": {
                    "outcome": "YELLOW",
                    "triggered_criteria": ["VITAL: Severe tachycardia (HR 142)"],
                    "recommended_action": "ESCALATE: Consider ESI 1 for safety",
                    "override_esi": None
                },
                "explanation": {
                    "text": "ESI 2 recommended based on: (1) Heart rate 142 bpm...",
                    "top_factors": [
                        {
                            "feature": "Heart rate",
                            "value": "142 bpm",
                            "contribution": 0.73,
                            "direction": "increases urgency",
                            "severity": "critical"
                        }
                    ]
                },
                "sub_score": 68.5,
                "recommendations": ["Monitor patient closely due to tachycardia"],
                "model_version": "v2.1.0_20241201",
                "inference_time_ms": 87.3,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
```

### Deterioration Data Model

```python
class VitalChange(BaseModel):
    vital: str
    initial: float
    current: float
    delta: float
    rate: float
    trend: str = Field(..., regex="^(worsening|stable|improving)$")

class DeteriorationRequest(BaseModel):
    patient_id: str
    initial_vitals: Vitals
    current_vitals: Vitals
    initial_esi: int = Field(..., ge=1, le=5)
    time_since_triage_minutes: int = Field(..., ge=0)
    age_group: str

class DeteriorationResponse(BaseModel):
    patient_id: str
    status: str = Field(..., regex="^(STABLE|DETERIORATING|UNCERTAIN)$")
    score: float = Field(..., ge=0, le=100)
    vital_changes: List[VitalChange]
    explanation: str
    recommendation: str
    confidence: float = Field(..., ge=0, le=1)
    next_check_in_minutes: Optional[int]
    alert_triggered: bool
    model_version: str
    timestamp: datetime = Field(default_factory=datetime.now)
```

### Audit Log Schema

```sql
-- PostgreSQL schema for audit logging

CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    
    -- Input features (JSONB for flexibility)
    patient_features JSONB NOT NULL,
    
    -- Prediction outputs
    esi_prediction INTEGER NOT NULL CHECK (esi_prediction BETWEEN 1 AND 5),
    probability_distribution FLOAT[] NOT NULL,
    confidence_breakdown JSONB NOT NULL,
    safety_flag VARCHAR(10) NOT NULL CHECK (safety_flag IN ('RED', 'YELLOW', 'GREEN')),
    sub_score FLOAT,
    
    -- Explainability
    explanation JSONB NOT NULL,
    shap_values FLOAT[],
    
    -- Performance
    inference_time_ms FLOAT NOT NULL,
    
    -- Indexes for common queries
    INDEX idx_timestamp (timestamp),
    INDEX idx_model_version (model_version),
    INDEX idx_esi_prediction (esi_prediction),
    INDEX idx_safety_flag (safety_flag)
);

CREATE TABLE overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID REFERENCES predictions(id),
    timestamp TIMESTAMP NOT NULL,
    
    -- Override details
    ml_predicted_esi INTEGER NOT NULL,
    clinician_final_esi INTEGER NOT NULL,
    override_direction VARCHAR(20) NOT NULL,
    override_magnitude INTEGER NOT NULL,
    
    -- Reasoning
    override_reason_category VARCHAR(50) NOT NULL,
    override_reason_text TEXT,
    
    -- Clinician
    clinician_id VARCHAR(255) NOT NULL,
    
    -- Outcome (populated later)
    disposition VARCHAR(50),
    adverse_event BOOLEAN,
    time_to_treatment_minutes INTEGER,
    outcome_updated_at TIMESTAMP,
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_prediction_id (prediction_id),
    INDEX idx_clinician_id (clinician_id)
);

CREATE TABLE deterioration_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Deterioration details
    deterioration_status VARCHAR(20) NOT NULL,
    deterioration_score FLOAT NOT NULL,
    vital_changes JSONB NOT NULL,
    
    -- Context
    initial_esi INTEGER NOT NULL,
    time_since_triage_minutes INTEGER NOT NULL,
    alert_reason VARCHAR(100) NOT NULL,
    
    -- Model
    model_version VARCHAR(50) NOT NULL,
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_patient_id (patient_id),
    INDEX idx_deterioration_status (deterioration_status)
);

-- Data retention: 7 years for HIPAA compliance
-- Encrypted at rest with AES-256
-- Access restricted via RBAC
```



## API Specifications

### REST API Endpoints

#### 1. POST /api/v1/predict

**Purpose**: Generate ESI triage recommendation with confidence and explanation

**Authentication**: API Key in header (`X-API-Key`)

**Rate Limit**: 500 requests/hour (configurable per client)

**Request**:
```http
POST /api/v1/predict HTTP/1.1
Host: api.patienttriage.ai
Content-Type: application/json
X-API-Key: pk_live_abc123...

{
  "request_id": "req_20240115_103000_abc",
  "demographics": {
    "age": 68,
    "sex": "female"
  },
  "vitals": {
    "hr": 118,
    "bp_systolic": 145,
    "bp_diastolic": 92,
    "spo2": 92,
    "rr": 22,
    "temperature": 37.2
  },
  "clinical": {
    "chief_complaint": "chest pain radiating to left arm",
    "chief_complaint_category": "chest_pain_cardiac",
    "pain_score": 7,
    "arrival_mode": "ambulance",
    "mental_status": "alert"
  },
  "symptoms": ["chest_pain", "shortness_of_breath", "diaphoresis"],
  "history": {
    "cardiac_history": true,
    "hypertension": true,
    "on_medications": true
  },
  "observations": ["visible_distress"],
  "metadata": {
    "facility_id": "hosp_001",
    "nurse_id": "nurse_456"
  }
}
```

**Response** (200 OK):
```json
{
  "request_id": "req_20240115_103000_abc",
  "esi_prediction": 2,
  "probability_distribution": [0.12, 0.68, 0.15, 0.04, 0.01],
  "confidence_breakdown": {
    "model_certainty": 85.2,
    "data_completeness": 95.0,
    "clinical_consistency": 72.0,
    "pattern_recognition": 81.3,
    "overall": 82.1,
    "level": "HIGH"
  },
  "safety_flag": {
    "outcome": "RED",
    "triggered_criteria": [
      "CRITICAL: Chest pain in patient >50 years (cardiac risk)",
      "VITAL: Severe tachycardia (HR 118)"
    ],
    "recommended_action": "OVERRIDE: Force ESI 1 due to critical criteria",
    "override_esi": 1
  },
  "explanation": {
    "text": "ESI 2 recommended (SAFETY OVERRIDE to ESI 1) based on: (1) Chest pain in 68-year-old female with cardiac history - increases urgency (CRITICAL), (2) Heart rate 118 bpm - moderately elevated - increases urgency (CRITICAL), (3) Oxygen saturation 92% - borderline low - increases urgency (CONCERNING)",
    "top_factors": [
      {
        "feature": "Chief complaint + Age + History",
        "value": "Chest pain, 68 years, cardiac history",
        "contribution": 1.85,
        "direction": "increases urgency",
        "severity": "critical"
      },
      {
        "feature": "Heart rate",
        "value": "118 bpm (moderately elevated)",
        "contribution": 0.73,
        "direction": "increases urgency",
        "severity": "critical"
      },
      {
        "feature": "Oxygen saturation",
        "value": "92% (borderline low)",
        "contribution": 0.42,
        "direction": "increases urgency",
        "severity": "concerning"
      }
    ]
  },
  "sub_score": 87.5,
  "recommendations": [
    "URGENT: Immediate ECG and cardiac workup indicated",
    "Consider STEMI protocol activation",
    "Monitor O2 saturation closely"
  ],
  "model_version": "v2.1.0_20241201",
  "inference_time_ms": 92.7,
  "timestamp": "2024-01-15T10:30:00.123Z"
}
```

**Error Responses**:

```json
// 400 Bad Request - Invalid input
{
  "error": "ValidationError",
  "message": "Heart rate must be between 20 and 250 bpm",
  "field": "vitals.hr",
  "request_id": "req_20240115_103000_abc"
}

// 401 Unauthorized - Invalid API key
{
  "error": "AuthenticationError",
  "message": "Invalid or missing API key"
}

// 429 Too Many Requests - Rate limit exceeded
{
  "error": "RateLimitExceeded",
  "message": "Rate limit of 500 requests/hour exceeded",
  "retry_after_seconds": 1800
}

// 500 Internal Server Error - Model failure
{
  "error": "ModelInferenceError",
  "message": "Model inference failed, returning safety default",
  "esi_prediction": 2,
  "confidence_level": "LOW",
  "request_id": "req_20240115_103000_abc"
}

// 503 Service Unavailable - Model not loaded
{
  "error": "ServiceUnavailable",
  "message": "ML model is currently unavailable",
  "retry_after_seconds": 60
}
```

#### 2. POST /api/v1/deterioration

**Purpose**: Assess patient deterioration from vital sign changes

**Request**:
```json
{
  "patient_id": "pat_12345",
  "initial_vitals": {
    "hr": 88,
    "bp_systolic": 125,
    "bp_diastolic": 80,
    "spo2": 96,
    "rr": 16,
    "temperature": 37.0
  },
  "current_vitals": {
    "hr": 118,
    "bp_systolic": 118,
    "bp_diastolic": 78,
    "spo2": 91,
    "rr": 24,
    "temperature": 37.4
  },
  "initial_esi": 3,
  "time_since_triage_minutes": 35,
  "age_group": "adult"
}
```

**Response** (200 OK):
```json
{
  "patient_id": "pat_12345",
  "status": "DETERIORATING",
  "score": 73.5,
  "vital_changes": [
    {
      "vital": "HR",
      "initial": 88,
      "current": 118,
      "delta": 30,
      "rate": 0.86,
      "trend": "worsening"
    },
    {
      "vital": "SpO2",
      "initial": 96,
      "current": 91,
      "delta": -5,
      "rate": -0.14,
      "trend": "worsening"
    },
    {
      "vital": "RR",
      "initial": 16,
      "current": 24,
      "delta": 8,
      "rate": 0.23,
      "trend": "worsening"
    }
  ],
  "explanation": "Patient deteriorating: HR increased 30 bpm (34%), SpO2 decreased to 91%, RR increased 50%. 3 vitals worsening.",
  "recommendation": "URGENT: Re-assess patient immediately and consider ESI escalation from 3 to 2",
  "confidence": 0.89,
  "next_check_in_minutes": 15,
  "alert_triggered": true,
  "model_version": "v2.1.0_20241201",
  "timestamp": "2024-01-15T11:05:00.456Z"
}
```

#### 3. GET /api/v1/health

**Purpose**: Service health check

**Response** (200 OK):
```json
{
  "status": "healthy",
  "models_loaded": true,
  "esi_model_version": "v2.1.0_20241201",
  "deterioration_model_version": "v2.1.0_20241201",
  "uptime_seconds": 86400,
  "predictions_last_hour": 437,
  "avg_inference_time_ms": 89.2
}
```

#### 4. GET /api/v1/models (Admin Only)

**Purpose**: List available model versions

**Authentication**: Admin Token

**Response** (200 OK):
```json
{
  "models": [
    {
      "version": "v2.1.0_20241201",
      "status": "production",
      "deployed_at": "2024-12-01T00:00:00Z",
      "metrics": {
        "accuracy": 0.923,
        "under_triage_rate": 0.021,
        "f1_score": 0.91
      }
    },
    {
      "version": "v2.0.5_20241115",
      "status": "shadow",
      "deployed_at": "2024-11-15T00:00:00Z",
      "metrics": {
        "accuracy": 0.918,
        "under_triage_rate": 0.024,
        "f1_score": 0.89
      }
    }
  ]
}
```

#### 5. POST /api/v1/models/{version}/activate (Admin Only)

**Purpose**: Switch production model version

**Request**:
```json
{
  "version": "v2.1.0_20241201",
  "shadow_mode": false
}
```

**Response** (200 OK):
```json
{
  "message": "Model v2.1.0_20241201 activated as production",
  "previous_version": "v2.0.5_20241115",
  "activated_at": "2024-01-15T12:00:00Z"
}
```

### API Performance Requirements

| Metric | Target | Rationale |
|--------|--------|-----------|
| **p50 Latency** | <60ms | Real-time triage needs fast response |
| **p95 Latency** | <100ms | Acceptable for 95% of requests |
| **p99 Latency** | <150ms | Worst-case still usable |
| **Throughput** | 500+ req/hour | Baseline ED volume, scalable to 2000+ |
| **Availability** | 99.9% uptime | ~8 hours downtime/year acceptable |
| **Error Rate** | <0.5% | High reliability for clinical use |

### API Security

1. **Authentication**:
   - API Keys for client authentication
   - Admin Tokens (JWT) for administrative endpoints
   - Keys rotated every 90 days

2. **Authorization**:
   - RBAC: `client`, `clinician`, `admin` roles
   - Clients can only access prediction endpoints
   - Admins can access model management

3. **Encryption**:
   - TLS 1.3 for all API traffic
   - Certificate pinning for mobile clients
   - HSTS headers enforced

4. **Rate Limiting**:
   - Token bucket algorithm
   - 500 req/hour default, configurable per client
   - Burst allowance: 10 requests in 10 seconds

5. **Input Validation**:
   - Pydantic schemas enforce types and ranges
   - SQL injection prevention (parameterized queries)
   - XSS prevention (no HTML in responses)

6. **Audit Logging**:
   - All API requests logged with client ID, timestamp, endpoint
   - PHI access logged separately for HIPAA compliance



## Training Pipeline

### Overview

The training pipeline transforms raw ED records into production-ready models with safety guarantees and fairness validation.

```
Raw ED Data → Preprocessing → Feature Engineering → Model Training → 
Validation → Bias Audit → Test Scenarios → Model Registry → Deployment
```

### Data Requirements

| Requirement | Specification | Rationale |
|-------------|---------------|-----------|
| **Minimum Records** | 50,000 ED encounters | Statistical power for rare conditions |
| **Age Distribution** | ≥15% each: pediatric, adult, geriatric | Prevent age group bias |
| **ESI Distribution** | Representation across all ESI 1-5 | Balanced class learning |
| **Temporal Data** | ≥30% with multiple vital measurements | Train deterioration detector |
| **Outcomes** | Disposition, adverse events, time-to-treatment | Validate predictions |
| **Chief Complaints** | ≥50 complaint categories | Comprehensive symptom coverage |
| **Data Freshness** | Last 2 years | Reflect current practices |

### Training Steps

#### Step 1: Data Ingestion

```python
def ingest_training_data(data_sources: List[str]) -> pd.DataFrame:
    """
    Ingest ED records from multiple sources (EHR exports, CSV, databases).
    
    Sources:
    - Hospital EHR systems (HL7 FHIR format)
    - Research databases (MIMIC-IV, eICU)
    - Partnered ED facilities
    
    Returns:
        Raw DataFrame with 50k+ records
    """
    records = []
    
    for source in data_sources:
        if source.endswith('.csv'):
            df = pd.read_csv(source)
        elif source.startswith('postgresql://'):
            df = pd.read_sql(query, source)
        elif source.endswith('.fhir'):
            df = parse_fhir_bundle(source)
        
        records.append(df)
    
    combined = pd.concat(records, ignore_index=True)
    
    # Validate minimum requirements
    assert len(combined) >= 50000, f"Insufficient data: {len(combined)} < 50000"
    
    return combined
```

#### Step 2: Data Preprocessing

```python
def preprocess_training_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize raw training data.
    
    Steps:
    1. Handle missing values (median imputation for vitals)
    2. Remove physiologically impossible values (HR >250, SpO2 >100)
    3. Encode categorical variables
    4. Remove duplicates
    5. De-identify PHI (remove names, MRNs, DOB)
    """
    df = raw_data.copy()
    
    # Step 1: Missing value handling
    vital_cols = ['hr', 'bp_systolic', 'bp_diastolic', 'spo2', 'rr', 'temperature']
    for col in vital_cols:
        if col in df.columns:
            # Impute with age-stratified median
            for age_group in ['pediatric_infant', 'pediatric_child', 'adult', 'geriatric']:
                mask = df['age_group'] == age_group
                median_val = df.loc[mask, col].median()
                df.loc[mask, col] = df.loc[mask, col].fillna(median_val)
    
    # Step 2: Remove physiologically impossible values
    df = df[
        (df['hr'] >= 20) & (df['hr'] <= 250) &
        (df['spo2'] >= 50) & (df['spo2'] <= 100) &
        (df['rr'] >= 5) & (df['rr'] <= 60) &
        (df['temperature'] >= 32.0) & (df['temperature'] <= 42.0)
    ]
    
    # Step 3: Encode categorical variables
    df['chief_complaint_category'] = df['chief_complaint_category'].astype('category')
    df['arrival_mode'] = df['arrival_mode'].astype('category')
    df['mental_status'] = df['mental_status'].astype('category')
    
    # Step 4: Remove duplicates
    df = df.drop_duplicates(subset=['patient_id', 'encounter_date'], keep='first')
    
    # Step 5: De-identify PHI
    df = df.drop(columns=['patient_name', 'mrn', 'dob', 'address'], errors='ignore')
    df['patient_id'] = df['patient_id'].apply(lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    
    return df
```

#### Step 3: Feature Engineering

```python
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create derived features for training.
    
    Features:
    - Age group classification
    - Vital deviations (age-normalized)
    - Symptom-vital discordance flags
    - Data completeness score
    - Temporal features (for deterioration model)
    """
    # Age group
    df['age_group'] = pd.cut(
        df['age'],
        bins=[0, 2, 12, 17, 64, 120],
        labels=['pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 'adult', 'geriatric']
    )
    
    # Vital deviations
    for age_group, ranges in AGE_SPECIFIC_VITAL_RANGES.items():
        mask = df['age_group'] == age_group
        
        for vital in ['hr', 'rr', 'bp_systolic', 'spo2', 'temperature']:
            if vital in df.columns:
                normal_mid = (ranges[f'{vital}_min'] + ranges[f'{vital}_max']) / 2
                normal_width = ranges[f'{vital}_max'] - ranges[f'{vital}_min']
                df.loc[mask, f'{vital}_deviation'] = (df.loc[mask, vital] - normal_mid) / normal_width
    
    # Symptom-vital discordance
    df['pain_underreported'] = (df['pain_score'] < 4) & (df['hr'] > 110)
    df['severity_underreported'] = (
        df['chief_complaint_category'].isin(MINOR_COMPLAINTS) &
        (df[['hr_deviation', 'spo2_deviation', 'bp_sys_deviation']].abs() > 1.0).sum(axis=1) >= 3
    )
    
    # Data completeness
    total_features = 40
    df['data_completeness_score'] = df.notna().sum(axis=1) / total_features
    
    return df
```

#### Step 4: Train/Val/Test Split

```python
def split_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Stratified train/val/test split maintaining age and ESI distribution.
    
    Split: 70% train, 15% val, 15% test
    Stratify by: age_group + ESI level
    """
    from sklearn.model_selection import train_test_split
    
    # Create stratification column
    df['stratify_key'] = df['age_group'].astype(str) + '_' + df['clinician_esi'].astype(str)
    
    # First split: 70% train, 30% temp
    train, temp = train_test_split(
        df,
        test_size=0.3,
        stratify=df['stratify_key'],
        random_state=42
    )
    
    # Second split: 50% of temp = 15% val, 15% test
    val, test = train_test_split(
        temp,
        test_size=0.5,
        stratify=temp['stratify_key'],
        random_state=42
    )
    
    # Verify stratification
    print("Train distribution:")
    print(train['age_group'].value_counts(normalize=True))
    print(train['clinician_esi'].value_counts(normalize=True))
    
    return train.drop('stratify_key', axis=1), val.drop('stratify_key', axis=1), test.drop('stratify_key', axis=1)
```

#### Step 5: Model Training

```python
def train_esi_classifier(train_df: pd.DataFrame, val_df: pd.DataFrame) -> CatBoostClassifier:
    """
    Train CatBoost ESI classifier with custom under-triage penalty.
    """
    # Prepare features
    X_train = train_df.drop(['clinician_esi', 'outcome', 'disposition'], axis=1)
    y_train = train_df['clinician_esi'] - 1  # Convert to 0-4
    
    X_val = val_df.drop(['clinician_esi', 'outcome', 'disposition'], axis=1)
    y_val = val_df['clinician_esi'] - 1
    
    # Categorical features
    cat_features = ['chief_complaint_category', 'arrival_mode', 'mental_status', 'age_group']
    
    # Model
    model = CatBoostClassifier(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function='MultiClass',
        class_weights={0: 10, 1: 5, 2: 2, 3: 1, 4: 1},  # Under-triage penalty
        early_stopping_rounds=50,
        random_seed=42,
        cat_features=cat_features,
        verbose=100
    )
    
    # Train
    model.fit(
        X_train, y_train,
        eval_set=(X_val, y_val),
        plot=True
    )
    
    return model

def train_deterioration_detector(train_df: pd.DataFrame, val_df: pd.DataFrame) -> xgb.XGBClassifier:
    """
    Train XGBoost deterioration detector on temporal features.
    """
    # Filter to patients with temporal measurements
    train_df = train_df[train_df['has_temporal_data'] == True]
    val_df = val_df[val_df['has_temporal_data'] == True]
    
    # Engineer temporal features
    X_train = engineer_temporal_features(train_df)
    y_train = train_df['deteriorated'].astype(int)
    
    X_val = engineer_temporal_features(val_df)
    y_val = val_df['deteriorated'].astype(int)
    
    # Model
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        max_depth=5,
        learning_rate=0.1,
        n_estimators=500,
        scale_pos_weight=3,  # Handle class imbalance
        early_stopping_rounds=30,
        random_state=42
    )
    
    # Train
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=100
    )
    
    return model
```

#### Step 6: Hyperparameter Tuning

```python
import optuna

def tune_hyperparameters(train_df: pd.DataFrame, val_df: pd.DataFrame) -> Dict:
    """
    Hyperparameter tuning using Optuna.
    
    Optimizes for: weighted combination of accuracy and under-triage rate
    """
    def objective(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 500, 2000),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'depth': trial.suggest_int('depth', 4, 10),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-3, 10.0, log=True),
            'bagging_temperature': trial.suggest_float('bagging_temperature', 0.0, 1.0)
        }
        
        model = CatBoostClassifier(
            **params,
            loss_function='MultiClass',
            class_weights={0: 10, 1: 5, 2: 2, 3: 1, 4: 1},
            early_stopping_rounds=50,
            random_seed=42,
            verbose=False
        )
        
        X_train = train_df.drop(['clinician_esi'], axis=1)
        y_train = train_df['clinician_esi'] - 1
        X_val = val_df.drop(['clinician_esi'], axis=1)
        y_val = val_df['clinician_esi'] - 1
        
        model.fit(X_train, y_train, eval_set=(X_val, y_val))
        
        # Evaluate
        y_pred = model.predict(X_val)
        accuracy = (y_pred == y_val).mean()
        under_triage_rate = ((y_pred > y_val).sum() / len(y_val))
        
        # Objective: maximize accuracy, minimize under-triage (weighted)
        score = accuracy - 10 * under_triage_rate
        
        return score
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=100)
    
    return study.best_params
```

#### Step 7: Validation

```python
def validate_model(model, test_df: pd.DataFrame) -> Dict:
    """
    Comprehensive model validation on held-out test set.
    
    Metrics:
    - Overall accuracy
    - Per-class precision/recall/F1
    - Under-triage rate (predicted > actual)
    - Over-triage rate (predicted < actual)
    - Age-stratified performance
    - Calibration (predicted probabilities vs observed frequencies)
    """
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    
    X_test = test_df.drop(['clinician_esi', 'outcome'], axis=1)
    y_test = test_df['clinician_esi'] - 1
    
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    
    # Overall metrics
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred)
    
    # Under/over-triage rates
    under_triage_rate = (y_pred > y_test).mean()
    over_triage_rate = (y_pred < y_test).mean()
    
    # Age-stratified performance
    age_performance = {}
    for age_group in test_df['age_group'].unique():
        mask = test_df['age_group'] == age_group
        age_acc = accuracy_score(y_test[mask], y_pred[mask])
        age_under_triage = (y_pred[mask] > y_test[mask]).mean()
        age_performance[age_group] = {
            'accuracy': age_acc,
            'under_triage_rate': age_under_triage
        }
    
    # Calibration
    calibration_error = compute_calibration_error(y_proba, y_test)
    
    results = {
        'accuracy': accuracy,
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'under_triage_rate': under_triage_rate,
        'over_triage_rate': over_triage_rate,
        'age_stratified': age_performance,
        'calibration_error': calibration_error
    }
    
    # Validate against requirements
    assert accuracy >= 0.90, f"Accuracy {accuracy:.3f} < 0.90"
    assert under_triage_rate <= 0.025, f"Under-triage rate {under_triage_rate:.3f} > 0.025"
    for age_group, perf in age_performance.items():
        assert perf['accuracy'] >= 0.85, f"{age_group} accuracy {perf['accuracy']:.3f} < 0.85"
        assert perf['under_triage_rate'] <= 0.025, f"{age_group} under-triage {perf['under_triage_rate']:.3f} > 0.025"
    
    return results
```

#### Step 8: Bias Audit

```python
def bias_audit(model, test_df: pd.DataFrame) -> BiasReport:
    """
    Audit model for demographic biases.
    
    Checks:
    - Performance parity across sex (male vs female)
    - Performance parity across age groups
    - Under-triage rate disparities
    - Statistical significance of differences
    """
    from scipy.stats import chi2_contingency
    
    X_test = test_df.drop(['clinician_esi', 'outcome'], axis=1)
    y_test = test_df['clinician_esi'] - 1
    y_pred = model.predict(X_test)
    
    # Sex-based analysis
    male_mask = test_df['sex'] == 'male'
    female_mask = test_df['sex'] == 'female'
    
    male_acc = accuracy_score(y_test[male_mask], y_pred[male_mask])
    female_acc = accuracy_score(y_test[female_mask], y_pred[female_mask])
    
    male_under_triage = (y_pred[male_mask] > y_test[male_mask]).mean()
    female_under_triage = (y_pred[female_mask] > y_test[female_mask]).mean()
    
    sex_disparity = abs(male_under_triage - female_under_triage)
    
    # Age group analysis
    age_disparities = {}
    for age_group in test_df['age_group'].unique():
        mask = test_df['age_group'] == age_group
        age_under_triage = (y_pred[mask] > y_test[mask]).mean()
        age_disparities[age_group] = age_under_triage
    
    max_age_disparity = max(age_disparities.values()) - min(age_disparities.values())
    
    # Statistical significance
    contingency_table = pd.crosstab(
        test_df['sex'],
        (y_pred > y_test)
    )
    chi2, p_value, _, _ = chi2_contingency(contingency_table)
    
    # Generate report
    report = BiasReport(
        sex_disparity=sex_disparity,
        age_disparity=max_age_disparity,
        male_accuracy=male_acc,
        female_accuracy=female_acc,
        male_under_triage=male_under_triage,
        female_under_triage=female_under_triage,
        age_performance=age_disparities,
        statistical_significance=p_value,
        passes_fairness=sex_disparity < 0.05 and max_age_disparity < 0.05
    )
    
    # Alert if bias detected
    if not report.passes_fairness:
        print(f"⚠️  BIAS DETECTED: Sex disparity {sex_disparity:.3f}, Age disparity {max_age_disparity:.3f}")
        print("Model requires retraining with bias mitigation")
    
    return report
```

#### Step 9: Test Scenarios

```python
def run_test_scenarios(model) -> TestResults:
    """
    Test model on 15-20 clinical test scenarios.
    
    Scenarios:
    1. Ambiguous chest pain (could be cardiac or musculoskeletal)
    2. Pediatric fever without source
    3. Geriatric fall with normal vitals
    4. Asymptomatic hypertension
    5. Severe trauma with compensated vitals
    6. Subtle stroke presentation
    7. Sepsis with early signs
    8. Patient with incomplete data (missing vitals)
    9. Patient under-reporting pain
    10. Out-of-distribution presentation
    ... (15-20 total)
    """
    scenarios = load_test_scenarios()  # Hand-crafted clinical vignettes
    results = []
    
    for scenario in scenarios:
        prediction = model.predict([scenario.features])
        expected_esi = scenario.ground_truth_esi
        
        result = {
            'scenario_name': scenario.name,
            'predicted_esi': prediction[0] + 1,
            'expected_esi': expected_esi,
            'correct': prediction[0] + 1 == expected_esi,
            'clinically_acceptable': abs((prediction[0] + 1) - expected_esi) <= 1,
            'explanation': scenario.rationale
        }
        
        results.append(result)
    
    pass_rate = sum(r['clinically_acceptable'] for r in results) / len(results)
    
    assert pass_rate >= 0.85, f"Test scenario pass rate {pass_rate:.2%} < 85%"
    
    return TestResults(scenarios=results, pass_rate=pass_rate)
```

#### Step 10: Model Serialization and Registration

```python
def register_model(model, validation_results: Dict, bias_report: BiasReport) -> str:
    """
    Save model to MLflow registry with metadata.
    
    Metadata:
    - Training date
    - Performance metrics
    - Bias audit results
    - Feature importance
    - Model size
    - Inference latency
    """
    import mlflow
    import mlflow.catboost
    
    # Generate version identifier
    version = f"v2.1.0_{datetime.now().strftime('%Y%m%d')}"
    
    with mlflow.start_run(run_name=version):
        # Log model
        mlflow.catboost.log_model(model, "esi_classifier")
        
        # Log metrics
        mlflow.log_metrics({
            'accuracy': validation_results['accuracy'],
            'under_triage_rate': validation_results['under_triage_rate'],
            'over_triage_rate': validation_results['over_triage_rate'],
            'calibration_error': validation_results['calibration_error']
        })
        
        # Log bias metrics
        mlflow.log_metrics({
            'sex_disparity': bias_report.sex_disparity,
            'age_disparity': bias_report.age_disparity,
            'passes_fairness': 1.0 if bias_report.passes_fairness else 0.0
        })
        
        # Log artifacts
        mlflow.log_dict(validation_results, "validation_results.json")
        mlflow.log_dict(bias_report.to_dict(), "bias_audit.json")
        
        # Save feature importance
        feature_importance = model.get_feature_importance()
        mlflow.log_dict(
            dict(zip(model.feature_names_, feature_importance.tolist())),
            "feature_importance.json"
        )
        
        # Register model
        model_uri = f"runs:/{mlflow.active_run().info.run_id}/esi_classifier"
        mlflow.register_model(model_uri, "ESI_Classifier")
    
    print(f"✅ Model {version} registered successfully")
    return version
```



## Inference Pipeline

### End-to-End Flow

```
API Request → Schema Validation → Preprocessing → Feature Engineering →
ML Prediction → SHAP Explanation → Confidence Scoring → Safety Validation →
Sub-Score Computation → Response Formation → Audit Logging → API Response
```

**Target Latency Breakdown**:

| Step | Target (ms) | Notes |
|------|-------------|-------|
| Schema Validation | <5 | Pydantic fast validation |
| Preprocessing | <10 | Lightweight transformations |
| Feature Engineering | <15 | Age group lookup, vital deviations |
| ML Prediction (CatBoost) | <10 | Optimized tree traversal |
| SHAP Explanation | <30 | TreeExplainer batch computation |
| Confidence Scoring | <10 | Entropy + OOD check |
| Safety Validation | <5 | Rule evaluation |
| Sub-Score Computation | <5 | Simple formula |
| Response Formation | <5 | JSON serialization |
| **Total** | **<95ms** | p95 target <100ms |

### Inference Pseudocode

```python
@app.post("/api/v1/predict")
async def predict_esi(patient: PatientData, background_tasks: BackgroundTasks):
    """
    Main inference endpoint.
    
    Steps:
    1. Validate input
    2. Preprocess and engineer features
    3. ML prediction
    4. Explainability
    5. Confidence scoring
    6. Safety validation
    7. Sub-score (if surge mode)
    8. Format response
    9. Async audit logging
    10. Return
    """
    start_time = time.time()
    
    try:
        # Step 1: Input already validated by Pydantic
        
        # Step 2: Preprocessing
        features = preprocess_patient_data(patient)
        
        # Step 3: ML Prediction
        feature_vector = features.to_numpy()
        probabilities = esi_model.predict_proba([feature_vector])[0]
        predicted_esi = int(np.argmax(probabilities)) + 1  # Convert 0-4 to 1-5
        
        # Step 4: SHAP Explanation
        shap_values = shap_explainer.shap_values(feature_vector)
        explanation = explainability_system.explain_esi_prediction(
            features, predicted_esi, probabilities
        )
        
        # Step 5: Confidence Scoring
        discordance_flags = {
            'pain_underreported': features.pain_underreported,
            'severity_underreported': features.severity_underreported,
            'respiratory_underreported': features.respiratory_underreported
        }
        confidence = confidence_system.compute_confidence(
            probabilities, features, discordance_flags
        )
        
        # Step 6: Safety Validation
        safety = safety_validator.validate(
            patient, features, predicted_esi, confidence
        )
        
        # Apply safety override if needed
        final_esi = safety.override_esi if safety.override_esi else predicted_esi
        
        # Step 7: Sub-Score (if surge mode active)
        sub_score = None
        if is_surge_mode_active():
            deterioration_score = 50.0  # Placeholder (would query if available)
            sub_score = surge_engine.compute_sub_score(
                patient, features, deterioration_score, 
                time_since_triage_minutes=0
            )
        
        # Step 8: Generate recommendations
        recommendations = generate_confidence_recommendations(confidence, final_esi)
        if safety.outcome == "RED":
            recommendations.insert(0, "⚠️ CRITICAL ALERT: " + safety.recommended_action)
        
        # Step 9: Format Response
        inference_time_ms = (time.time() - start_time) * 1000
        
        response = PredictionResponse(
            request_id=patient.request_id,
            esi_prediction=final_esi,
            probability_distribution=probabilities.tolist(),
            confidence_breakdown=confidence,
            safety_flag=safety,
            explanation=explanation,
            sub_score=sub_score,
            recommendations=recommendations,
            model_version=esi_model.version,
            inference_time_ms=inference_time_ms
        )
        
        # Step 10: Async Audit Logging (doesn't block response)
        background_tasks.add_task(
            log_prediction,
            prediction=response,
            patient_features=features.to_dict()
        )
        
        return response
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ModelInferenceError as e:
        # Fallback: Return safe default (ESI 2, LOW confidence)
        return generate_safe_fallback_response(patient.request_id, error=str(e))
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Caching Strategy

```python
class PredictionCache:
    """
    Redis-based caching for expensive computations.
    
    Cached items:
    - Age-specific vital ranges (TTL: permanent, updated on model retrain)
    - Condition urgency table (TTL: permanent)
    - SHAP base values (TTL: permanent per model version)
    - OOD detector model (TTL: permanent per model version)
    - Recent predictions (TTL: 5 minutes for duplicate detection)
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_vital_ranges(self, age_group: str) -> Dict:
        """Get age-specific vital ranges (cached)."""
        key = f"vital_ranges:{age_group}"
        cached = self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        
        # Load from config
        ranges = AGE_SPECIFIC_VITAL_RANGES[age_group]
        self.redis.set(key, json.dumps(ranges))
        return ranges
    
    def get_condition_urgency(self, chief_complaint: str) -> float:
        """Get condition urgency score (cached)."""
        key = f"condition_urgency:{chief_complaint}"
        cached = self.redis.get(key)
        
        if cached:
            return float(cached)
        
        # Load from table
        urgency = CONDITION_URGENCY_TABLE.get(chief_complaint, 50.0)
        self.redis.set(key, urgency)
        return urgency
    
    def check_duplicate_request(self, request_id: str) -> Optional[PredictionResponse]:
        """Check if identical request was made recently (5 min window)."""
        key = f"prediction:{request_id}"
        cached = self.redis.get(key)
        
        if cached:
            return PredictionResponse.parse_raw(cached)
        
        return None
    
    def cache_prediction(self, response: PredictionResponse):
        """Cache prediction for 5 minutes."""
        key = f"prediction:{response.request_id}"
        self.redis.setex(key, 300, response.json())  # TTL 5 minutes
```

### Batch Inference (for Deterioration Monitoring)

```python
async def monitor_waiting_patients():
    """
    Background task: Monitor all waiting patients for deterioration.
    
    Runs every 5 minutes, checks patients due for re-assessment.
    """
    while True:
        # Query patients due for check
        patients = db.query("""
            SELECT patient_id, initial_esi, initial_vitals, current_vitals, 
                   time_since_triage_minutes, age_group
            FROM waiting_patients
            WHERE next_check_due <= NOW()
        """)
        
        if len(patients) == 0:
            await asyncio.sleep(300)  # 5 minutes
            continue
        
        # Batch inference (process 100 patients at once)
        batch_size = 100
        for i in range(0, len(patients), batch_size):
            batch = patients[i:i+batch_size]
            
            # Engineer temporal features for batch
            temporal_features = [engineer_temporal_features(p) for p in batch]
            X_batch = np.array(temporal_features)
            
            # Batch prediction
            deterioration_scores = deterioration_model.predict_proba(X_batch)[:, 1] * 100
            
            # Process results
            for patient, score in zip(batch, deterioration_scores):
                status = classify_deterioration(
                    score, 
                    patient['num_vitals_worsening'],
                    confidence=0.85
                )
                
                if status == "DETERIORATING" or score >= 60:
                    # Generate alert
                    await send_deterioration_alert(patient, score, status)
                
                # Update next check time
                next_check = compute_next_check_time(patient['initial_esi'])
                db.update('waiting_patients', 
                    {'patient_id': patient['patient_id']},
                    {'next_check_due': datetime.now() + timedelta(minutes=next_check)}
                )
        
        await asyncio.sleep(300)  # Check every 5 minutes
```



## Performance Optimization

### Model Optimization

#### 1. Model Quantization

```python
def quantize_model(model: CatBoostClassifier) -> CatBoostClassifier:
    """
    Quantize model to reduce size and improve inference speed.
    
    Techniques:
    - Float32 → Float16 for weights (2× size reduction)
    - Prune low-importance features (retain top 95% importance)
    - Tree depth reduction (if accuracy remains >90%)
    
    Trade-off: ~10% size reduction, ~15% speed improvement, <0.5% accuracy loss
    """
    # CatBoost supports quantization natively
    quantized_model = model.copy()
    quantized_model.save_model(
        "model_quantized.cbm",
        format="cbm",
        pool=None
    )
    
    return quantized_model
```

#### 2. Feature Selection

```python
def select_top_features(model: CatBoostClassifier, threshold: float = 0.95) -> List[str]:
    """
    Select features contributing to top 95% of importance.
    
    Reduces feature dimensionality from 40+ to ~25 features.
    Speeds up preprocessing and inference by ~20%.
    """
    feature_importance = model.get_feature_importance()
    feature_names = model.feature_names_
    
    # Sort by importance
    sorted_features = sorted(
        zip(feature_names, feature_importance),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Select top features contributing to 95% cumulative importance
    cumulative_importance = 0
    total_importance = sum(feature_importance)
    selected_features = []
    
    for feature_name, importance in sorted_features:
        selected_features.append(feature_name)
        cumulative_importance += importance
        
        if cumulative_importance / total_importance >= threshold:
            break
    
    print(f"Selected {len(selected_features)} of {len(feature_names)} features (95% importance)")
    
    return selected_features
```

### Database Optimization

#### 1. Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# PostgreSQL connection pool
engine = create_engine(
    "postgresql://user:pass@localhost/triage_db",
    poolclass=QueuePool,
    pool_size=20,  # Maintain 20 connections
    max_overflow=30,  # Allow 30 additional connections under load
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600  # Recycle connections every hour
)
```

#### 2. Async Audit Logging

```python
from fastapi import BackgroundTasks

async def log_prediction(prediction: PredictionResponse, patient_features: Dict):
    """
    Async audit logging (doesn't block API response).
    
    Writes to PostgreSQL in background after response sent.
    """
    await asyncio.sleep(0)  # Yield to event loop
    
    try:
        audit_entry = {
            'request_id': prediction.request_id,
            'timestamp': prediction.timestamp,
            'model_version': prediction.model_version,
            'patient_features': json.dumps(patient_features),
            'esi_prediction': prediction.esi_prediction,
            'probability_distribution': prediction.probability_distribution,
            'confidence_breakdown': prediction.confidence_breakdown.dict(),
            'safety_flag': prediction.safety_flag.outcome,
            'inference_time_ms': prediction.inference_time_ms
        }
        
        # Async database insert
        await db.execute(
            "INSERT INTO predictions (...) VALUES (...)",
            audit_entry
        )
    except Exception as e:
        logger.error(f"Audit logging failed: {e}")
        # Don't fail the request if logging fails
```

### Caching & Precomputation

#### 1. Age Range Lookup Table (Redis)

```python
# Preload all age-specific vital ranges into Redis on startup
async def preload_cache():
    """Preload reference data into Redis cache."""
    for age_group, ranges in AGE_SPECIFIC_VITAL_RANGES.items():
        redis_client.set(f"vital_ranges:{age_group}", json.dumps(ranges))
    
    for condition, urgency in CONDITION_URGENCY_TABLE.items():
        redis_client.set(f"condition_urgency:{condition}", urgency)
    
    print("✅ Cache preloaded")
```

#### 2. SHAP Base Values (Cached per Model Version)

```python
# Compute SHAP explainer once per model version, cache in memory
shap_explainer = shap.TreeExplainer(esi_model)
SHAP_EXPLAINER_CACHE[esi_model.version] = shap_explainer
```

### API Performance

#### 1. Response Compression

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses >1KB
```

#### 2. Async API Handlers

```python
# All endpoints use async/await for non-blocking I/O
@app.post("/api/v1/predict")
async def predict_esi(patient: PatientData):
    # Async processing allows handling 1000+ concurrent requests
    pass
```

#### 3. Rate Limiting (Token Bucket)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/predict")
@limiter.limit("500/hour")  # 500 requests per hour per client
async def predict_esi(patient: PatientData):
    pass
```

### Monitoring & Alerting

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
prediction_counter = Counter('predictions_total', 'Total predictions made')
inference_latency = Histogram('inference_latency_seconds', 'Inference latency')
under_triage_counter = Counter('under_triage_total', 'Under-triage count', ['age_group', 'sex'])
confidence_gauge = Gauge('average_confidence', 'Average confidence score')

# Instrument endpoints
@app.post("/api/v1/predict")
async def predict_esi(patient: PatientData):
    with inference_latency.time():
        response = await perform_inference(patient)
    
    # Update metrics
    prediction_counter.inc()
    confidence_gauge.set(response.confidence_breakdown.overall)
    
    # Track under-triage in real-time (if override logged later)
    return response

# Expose metrics endpoint for Prometheus scraping
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Alerting Rules (Prometheus)

```yaml
# prometheus_alerts.yml
groups:
  - name: ml_core_alerts
    rules:
      # Alert if under-triage rate exceeds 3.5% (7-day window)
      - alert: HighUnderTriageRate
        expr: rate(under_triage_total[7d]) / rate(predictions_total[7d]) > 0.035
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Under-triage rate exceeds 3.5%"
          description: "Under-triage rate is {{ $value | humanizePercentage }} (threshold: 3.5%)"
      
      # Alert if inference latency p95 exceeds 100ms
      - alert: HighInferenceLatency
        expr: histogram_quantile(0.95, inference_latency_seconds) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Inference latency p95 exceeds 100ms"
          description: "p95 latency is {{ $value }}s (threshold: 0.1s)"
      
      # Alert if error rate exceeds 0.5%
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.005
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate exceeds 0.5%"
      
      # Alert if sex-based under-triage disparity detected
      - alert: BiasDetected
        expr: |
          abs(
            rate(under_triage_total{sex="female"}[7d]) / rate(predictions_total{sex="female"}[7d]) -
            rate(under_triage_total{sex="male"}[7d]) / rate(predictions_total{sex="male"}[7d])
          ) > 0.05
        for: 24h
        labels:
          severity: warning
        annotations:
          summary: "Bias detected in under-triage rates between sexes"
```



## Deployment Strategy

### Deployment Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (AWS ALB)     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼──────────┐ ┌▼─────────────┐
     │  API Instance 1 │ │ API Instance 2│ │ API Instance │
     │  (FastAPI)      │ │  (FastAPI)   │ │  N (autoscale)│
     └────────┬────────┘ └───┬──────────┘ └┬─────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼──────────┐ ┌▼─────────────┐
     │ Redis Cache    │ │ PostgreSQL   │ │ MLflow       │
     │ (Vital Ranges, │ │ (Audit Logs) │ │ (Models)     │
     │  OOD Detector) │ └──────────────┘ └──────────────┘
     └────────────────┘
              
     ┌───────────────────────────────────────────────┐
     │         Monitoring & Alerting Stack           │
     │  Prometheus → Grafana → PagerDuty/Slack       │
     └───────────────────────────────────────────────┘
```

### Deployment Modes

#### 1. Blue-Green Deployment

```python
"""
Blue-Green deployment for zero-downtime model updates.

Process:
1. Deploy new model version (green) alongside production (blue)
2. Run shadow mode: green makes predictions, blue responds
3. Compare metrics (agreement rate, latency, accuracy on validation set)
4. If green passes: switch traffic to green, blue becomes backup
5. If green fails: rollback to blue
"""

class DeploymentManager:
    def __init__(self):
        self.blue_model = None  # Current production
        self.green_model = None  # New candidate
        self.current_color = "blue"
    
    def deploy_green(self, model_version: str):
        """Deploy new model as green (shadow mode)."""
        self.green_model = mlflow.pyfunc.load_model(f"models:/ESI_Classifier/{model_version}")
        print(f"✅ Green model {model_version} deployed in shadow mode")
    
    async def shadow_mode_prediction(self, patient_data: PatientData):
        """Run both models, return blue, log green for comparison."""
        # Production prediction (blue)
        blue_prediction = await self.predict_with_model(self.blue_model, patient_data)
        
        # Shadow prediction (green) - async, doesn't block
        asyncio.create_task(
            self.log_shadow_prediction(self.green_model, patient_data, blue_prediction)
        )
        
        return blue_prediction
    
    async def log_shadow_prediction(self, model, patient_data, blue_prediction):
        """Log shadow model prediction for comparison."""
        try:
            green_prediction = await self.predict_with_model(model, patient_data)
            
            # Log comparison
            await db.insert('shadow_comparisons', {
                'request_id': patient_data.request_id,
                'blue_esi': blue_prediction.esi_prediction,
                'green_esi': green_prediction.esi_prediction,
                'agreement': blue_prediction.esi_prediction == green_prediction.esi_prediction,
                'blue_confidence': blue_prediction.confidence_breakdown.overall,
                'green_confidence': green_prediction.confidence_breakdown.overall,
                'timestamp': datetime.now()
            })
        except Exception as e:
            logger.error(f"Shadow prediction failed: {e}")
    
    def analyze_shadow_performance(self, days: int = 7) -> Dict:
        """Analyze green model performance in shadow mode."""
        comparisons = db.query(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN agreement THEN 1 ELSE 0 END) as agreements,
                AVG(green_confidence) as avg_confidence
            FROM shadow_comparisons
            WHERE timestamp >= NOW() - INTERVAL '{days} days'
        """)[0]
        
        agreement_rate = comparisons['agreements'] / comparisons['total']
        
        return {
            'total_predictions': comparisons['total'],
            'agreement_rate': agreement_rate,
            'avg_confidence': comparisons['avg_confidence'],
            'ready_for_production': agreement_rate >= 0.95  # 95% agreement threshold
        }
    
    def switch_to_green(self):
        """Switch production traffic to green model."""
        if self.analyze_shadow_performance()['ready_for_production']:
            # Swap models
            self.blue_model, self.green_model = self.green_model, self.blue_model
            self.current_color = "green"
            
            print(f"✅ Switched to GREEN model (production)")
            print(f"   BLUE model retained as backup")
        else:
            raise ValueError("Green model not ready for production (agreement rate <95%)")
    
    def rollback_to_blue(self):
        """Emergency rollback to previous model."""
        if self.current_color == "green":
            self.current_color = "blue"
            print("⚠️  ROLLBACK: Switched back to BLUE model")
```

#### 2. A/B Testing

```python
class ABTestManager:
    """
    A/B testing for gradual rollout of new models.
    
    Strategy:
    - Split traffic: 90% model A (current), 10% model B (new)
    - Gradually increase B traffic: 10% → 25% → 50% → 75% → 100%
    - Monitor metrics at each stage
    - Rollback if B performs worse
    """
    
    def __init__(self):
        self.model_a = load_production_model()
        self.model_b = load_candidate_model()
        self.traffic_split = 0.10  # 10% to model B
    
    async def route_prediction(self, patient_data: PatientData) -> PredictionResponse:
        """Route request to A or B based on traffic split."""
        # Deterministic routing based on request_id hash
        if hash(patient_data.request_id) % 100 < self.traffic_split * 100:
            # Route to model B
            response = await self.predict_with_model_b(patient_data)
            response.model_version += "_ab_test_b"
        else:
            # Route to model A
            response = await self.predict_with_model_a(patient_data)
            response.model_version += "_ab_test_a"
        
        return response
    
    def compare_ab_metrics(self) -> Dict:
        """Compare performance between models A and B."""
        metrics_a = db.query("""
            SELECT 
                COUNT(*) as predictions,
                AVG(CASE WHEN safety_flag = 'GREEN' THEN 1 ELSE 0 END) as green_rate,
                AVG(inference_time_ms) as avg_latency
            FROM predictions
            WHERE model_version LIKE '%_ab_test_a'
              AND timestamp >= NOW() - INTERVAL '24 hours'
        """)[0]
        
        metrics_b = db.query("""
            SELECT 
                COUNT(*) as predictions,
                AVG(CASE WHEN safety_flag = 'GREEN' THEN 1 ELSE 0 END) as green_rate,
                AVG(inference_time_ms) as avg_latency
            FROM predictions
            WHERE model_version LIKE '%_ab_test_b'
              AND timestamp >= NOW() - INTERVAL '24 hours'
        """)[0]
        
        return {
            'model_a': metrics_a,
            'model_b': metrics_b,
            'b_is_better': (
                metrics_b['green_rate'] >= metrics_a['green_rate'] and
                metrics_b['avg_latency'] <= metrics_a['avg_latency'] * 1.1
            )
        }
    
    def increase_b_traffic(self):
        """Gradually increase traffic to model B."""
        if self.compare_ab_metrics()['b_is_better']:
            self.traffic_split = min(1.0, self.traffic_split + 0.15)
            print(f"✅ Increased model B traffic to {self.traffic_split:.0%}")
        else:
            print(f"⚠️  Model B not performing better, keeping split at {self.traffic_split:.0%}")
```

#### 3. Rollback Procedures

```python
class RollbackManager:
    """
    Emergency rollback procedures.
    
    Triggers:
    - Under-triage rate >3.5%
    - Error rate >1%
    - Inference latency p95 >150ms
    - Bias detected (sex/age disparity >5%)
    """
    
    def __init__(self):
        self.rollback_history = []
        self.model_versions = self.load_model_history()
    
    def check_rollback_triggers(self) -> Optional[str]:
        """Check if any rollback trigger is met."""
        # Query recent metrics (last 1 hour)
        metrics = db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN safety_flag = 'RED' THEN 1 ELSE 0 END) as red_flags,
                AVG(inference_time_ms) as avg_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms) as p95_latency
            FROM predictions
            WHERE timestamp >= NOW() - INTERVAL '1 hour'
        """)[0]
        
        # Trigger 1: High under-triage rate (approximated by RED flags)
        red_flag_rate = metrics['red_flags'] / metrics['total'] if metrics['total'] > 0 else 0
        if red_flag_rate > 0.10:  # >10% RED flags suggests issues
            return "HIGH_RED_FLAG_RATE"
        
        # Trigger 2: High latency
        if metrics['p95_latency'] > 150:
            return "HIGH_LATENCY"
        
        # Trigger 3: Error rate
        error_rate = self.get_error_rate_last_hour()
        if error_rate > 0.01:
            return "HIGH_ERROR_RATE"
        
        # Trigger 4: Bias detected
        if self.detect_bias():
            return "BIAS_DETECTED"
        
        return None
    
    def execute_rollback(self, reason: str):
        """Execute emergency rollback to previous model version."""
        current_version = get_current_model_version()
        previous_version = self.get_previous_stable_version()
        
        print(f"🚨 EMERGENCY ROLLBACK initiated")
        print(f"   Reason: {reason}")
        print(f"   Current: {current_version}")
        print(f"   Rolling back to: {previous_version}")
        
        # Load previous model
        previous_model = mlflow.pyfunc.load_model(f"models:/ESI_Classifier/{previous_version}")
        
        # Hot-swap global model
        global esi_model
        esi_model = previous_model
        
        # Log rollback
        self.rollback_history.append({
            'timestamp': datetime.now(),
            'reason': reason,
            'from_version': current_version,
            'to_version': previous_version
        })
        
        # Alert team
        send_slack_alert(f"🚨 ML Core rollback: {reason}")
        send_pagerduty_alert(f"ML Core rollback: {current_version} → {previous_version}")
        
        print(f"✅ Rollback complete. Now running {previous_version}")
    
    def get_previous_stable_version(self) -> str:
        """Get last known stable model version."""
        # Query model versions with >95% agreement rate and <2.5% under-triage
        stable_versions = db.query("""
            SELECT model_version
            FROM model_performance_history
            WHERE agreement_rate >= 0.95
              AND under_triage_rate <= 0.025
              AND deployed_days >= 7
            ORDER BY deployed_at DESC
            LIMIT 1
        """)
        
        if stable_versions:
            return stable_versions[0]['model_version']
        else:
            raise ValueError("No stable previous version found")
```

### Infrastructure Requirements

#### Compute Resources

| Component | Specification | Rationale |
|-----------|---------------|-----------|
| **API Instances** | 4 vCPU, 16GB RAM | Handle 500 req/hr with headroom |
| **Autoscaling** | 2-10 instances | Scale with load (2 baseline, 10 peak) |
| **Redis Cache** | 2GB memory, HA cluster | Vital ranges, OOD detector, predictions |
| **PostgreSQL** | 8 vCPU, 32GB RAM, 500GB SSD | 7 years audit logs, millions of records |
| **MLflow Server** | 2 vCPU, 8GB RAM | Model registry, metadata storage |

#### Network

- **Load Balancer**: AWS Application Load Balancer (ALB) with health checks
- **Availability Zones**: Multi-AZ deployment (us-east-1a, us-east-1b) for 99.9% uptime
- **CDN**: CloudFront for API docs and static assets
- **DNS**: Route53 with failover to backup region

#### Security

- **WAF**: AWS WAF rules blocking SQL injection, XSS attempts
- **DDoS Protection**: AWS Shield Standard
- **TLS Certificates**: AWS Certificate Manager, auto-renewal
- **Secrets Management**: AWS Secrets Manager for API keys, DB credentials
- **IAM Roles**: Least-privilege access for EC2, RDS, S3

#### Backup & Disaster Recovery

- **Database Backups**: Automated daily backups, 30-day retention
- **Point-in-Time Recovery**: 5-minute RPO for PostgreSQL
- **Model Versioning**: All models in S3 + MLflow (immutable)
- **Cross-Region Replication**: Audit logs replicated to us-west-2
- **RTO Target**: <15 minutes for critical failures
- **RPO Target**: <5 minutes for data loss

### Deployment Checklist

```markdown
## Pre-Deployment

- [ ] Model trained and validated (accuracy ≥90%, under-triage ≤2.5%)
- [ ] Bias audit passed (sex/age disparity <5%)
- [ ] Test scenarios passed (≥85% clinically acceptable)
- [ ] Model registered in MLflow with metadata
- [ ] Infrastructure provisioned (API, Redis, PostgreSQL)
- [ ] Monitoring dashboards configured (Grafana)
- [ ] Alerting rules deployed (Prometheus)
- [ ] Load testing completed (1000 req/hr sustained)
- [ ] Security scan passed (OWASP Top 10)
- [ ] HIPAA compliance validated

## Deployment

- [ ] Deploy model to shadow mode (blue-green)
- [ ] Run shadow mode for 7 days, collect metrics
- [ ] Analyze shadow performance (agreement rate ≥95%)
- [ ] Switch traffic to new model (green)
- [ ] Monitor for 24 hours (no rollback triggers)
- [ ] Gradually increase traffic (A/B testing if needed)
- [ ] Decommission old model after 14 days stable

## Post-Deployment

- [ ] Override tracking dashboard live
- [ ] Weekly bias audits scheduled
- [ ] Monthly retraining pipeline review
- [ ] Quarterly performance report to stakeholders
- [ ] Continuous monitoring of under-triage rate
```



## Error Handling

### Error Classification

| Error Type | HTTP Status | Handling Strategy | Example |
|------------|-------------|-------------------|---------|
| **Validation Error** | 400 | Return specific field error | `"vitals.hr must be between 20-250"` |
| **Authentication Error** | 401 | Reject with auth message | `"Invalid API key"` |
| **Authorization Error** | 403 | Reject with permission message | `"Admin access required"` |
| **Rate Limit Exceeded** | 429 | Return retry-after header | `"Rate limit: retry in 1800s"` |
| **Model Inference Error** | 500 | Return safe default (ESI 2, LOW confidence) | `"Model error, returning safety default"` |
| **Database Error** | 500 | Log error, proceed without audit logging | `"Audit log failed, prediction succeeded"` |
| **Service Unavailable** | 503 | Return unavailable message | `"ML model not loaded"` |

### Safe Fallback Strategy

```python
def generate_safe_fallback_response(request_id: str, error: str) -> PredictionResponse:
    """
    Generate safe fallback response when model inference fails.
    
    Fallback Strategy:
    - Predict ESI 2 (mid-high urgency, safe escalation)
    - Confidence: LOW (0%)
    - Safety flag: YELLOW (flag for clinical validation)
    - Explanation: Indicate model error, recommend manual assessment
    
    Rationale:
    - ESI 2 is safer than ESI 3+ (escalation bias)
    - LOW confidence signals clinician to rely on judgment
    - System gracefully degrades rather than failing completely
    """
    return PredictionResponse(
        request_id=request_id,
        esi_prediction=2,
        probability_distribution=[0.0, 1.0, 0.0, 0.0, 0.0],  # 100% ESI 2
        confidence_breakdown=ConfidenceBreakdown(
            model_certainty=0.0,
            data_completeness=0.0,
            clinical_consistency=0.0,
            pattern_recognition=0.0,
            overall=0.0,
            level="LOW"
        ),
        safety_flag=SafetyValidation(
            outcome="YELLOW",
            triggered_criteria=[f"MODEL_ERROR: {error}"],
            recommended_action="Manual clinical assessment required (model unavailable)",
            override_esi=None
        ),
        explanation=Explanation(
            text="Model inference failed. Defaulting to ESI 2 for safety. Manual assessment required.",
            top_factors=[]
        ),
        sub_score=None,
        recommendations=[
            "⚠️ ML model unavailable - perform manual triage",
            "System issue logged, technical team notified"
        ],
        model_version="FALLBACK",
        inference_time_ms=0.0
    )
```

### Error Monitoring

```python
# Log all errors to Sentry for debugging
import sentry_sdk

sentry_sdk.init(
    dsn="https://...@sentry.io/...",
    traces_sample_rate=0.1,  # Sample 10% of transactions
    environment="production"
)

# Track error patterns
error_counter = Counter('ml_errors_total', 'ML errors', ['error_type'])

@app.exception_handler(ModelInferenceError)
async def handle_model_error(request: Request, exc: ModelInferenceError):
    error_counter.labels(error_type='model_inference').inc()
    sentry_sdk.capture_exception(exc)
    
    return generate_safe_fallback_response(
        request_id=request.state.request_id,
        error=str(exc)
    )
```

## Testing Strategy

### Unit Tests

**Purpose**: Test individual components in isolation

**Coverage Target**: ≥85% code coverage

**Test Categories**:

1. **Preprocessing Tests**
   - Age group classification edge cases (age 0, 2, 12, 17, 64, 65, 120)
   - Vital deviation computation (boundary values, missing data)
   - Symptom-vital discordance detection (various combinations)
   - Data completeness scoring (0%, 50%, 100%)

2. **Model Inference Tests**
   - CatBoost prediction output format (5-element probability array)
   - XGBoost deterioration scoring (0-100 range)
   - SHAP explanation generation (top 5 factors returned)
   - Feature engineering consistency (same input → same features)

3. **Confidence System Tests**
   - Entropy calculation (uniform vs peaked distributions)
   - Data completeness scoring (missing vs complete)
   - Clinical consistency scoring (discordance flags)
   - OOD detection (in-distribution vs outliers)

4. **Safety Validator Tests**
   - Critical criteria detection (chest pain + age >50 → RED)
   - Vital threshold evaluation (HR 160 adult → flag, HR 160 infant → normal)
   - Confidence-based escalation (LOW + ESI 3 → recommend ESI 2)
   - Override logic (RED → force ESI 1-2)

5. **Surge Engine Tests**
   - Sub-score formula (component weights sum to 1.0)
   - Vital severity scoring (deviation →severity mapping)
   - Condition urgency lookup (STEMI → 95, fever → 40)
   - Patient ranking (ESI, sub-score, arrival time order)

6. **API Tests**
   - Input validation (Pydantic schemas enforce types/ranges)
   - Error responses (400, 401, 429, 500, 503 status codes)
   - Response format (JSON schema compliance)
   - Rate limiting (token bucket behavior)

**Example Unit Test**:

```python
def test_vital_deviation_computation():
    """Test age-specific vital deviation calculation."""
    # Adult with HR 140 (abnormal)
    adult_features = compute_vital_deviations(
        age=35, age_group='adult', hr=140, rr=18, spo2=95
    )
    assert adult_features['hr_deviation'] > 2.0  # Severely elevated
    
    # Infant with HR 140 (normal)
    infant_features = compute_vital_deviations(
        age=1, age_group='pediatric_infant', hr=140, rr=40, spo2=96
    )
    assert abs(infant_features['hr_deviation']) < 0.5  # Within normal range
    
def test_safety_validator_critical_criteria():
    """Test safety validator detects critical conditions."""
    patient = PatientData(
        demographics={'age': 68, 'sex': 'female'},
        vitals={'hr': 118, 'spo2': 92},
        clinical={'chief_complaint': 'chest pain'},
        symptoms=['chest_pain']
    )
    
    safety = safety_validator.validate(patient, features, ml_prediction=3, confidence=high_confidence)
    
    assert safety.outcome == "RED"
    assert "chest pain" in safety.triggered_criteria[0].lower()
    assert safety.override_esi in [1, 2]
```

### Integration Tests

**Purpose**: Test component interactions end-to-end

**Test Scenarios**:

1. **End-to-End Prediction**
   - Send patient data → receive prediction response
   - Verify all response fields present (ESI, confidence, safety, explanation)
   - Confirm audit log written to database
   - Check inference latency <100ms

2. **Deterioration Monitoring**
   - Submit initial and current vitals → receive deterioration assessment
   - Verify vital changes computed correctly
   - Confirm alert triggered if deteriorating
   - Check next monitoring interval set

3. **Override Tracking**
   - Log clinician override → verify database entry
   - Submit outcome data → verify override record updated
   - Query override patterns → verify aggregation correct

4. **Model Switching**
   - Deploy model to shadow mode → verify both models run
   - Switch to new production model → verify traffic routed correctly
   - Rollback to previous model → verify instant switch

5. **Error Handling**
   - Submit invalid input → receive 400 with field error
   - Exceed rate limit → receive 429 with retry-after
   - Simulate model failure → receive safe fallback (ESI 2, LOW confidence)

**Example Integration Test**:

```python
@pytest.mark.asyncio
async def test_end_to_end_prediction():
    """Test complete prediction pipeline."""
    # Prepare patient data
    patient = PatientData(
        request_id="test_123",
        demographics=Demographics(age=68, sex="female"),
        vitals=Vitals(hr=118, bp_systolic=145, spo2=92, rr=22),
        clinical=Clinical(
            chief_complaint="chest pain",
            chief_complaint_category="chest_pain_cardiac",
            pain_score=7,
            arrival_mode="ambulance",
            mental_status="alert"
        ),
        symptoms=["chest_pain", "shortness_of_breath"],
        history=MedicalHistory(cardiac_history=True, hypertension=True)
    )
    
    # Make API request
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/predict", json=patient.dict())
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    
    assert data['request_id'] == "test_123"
    assert data['esi_prediction'] in [1, 2]  # Safety should force ESI 1-2
    assert len(data['probability_distribution']) == 5
    assert data['confidence_breakdown']['level'] in ['HIGH', 'MEDIUM', 'LOW']
    assert data['safety_flag']['outcome'] in ['RED', 'YELLOW', 'GREEN']
    assert len(data['explanation']['top_factors']) >= 3
    assert data['inference_time_ms'] < 100
    
    # Verify audit log written
    audit_entry = await db.query(
        "SELECT * FROM predictions WHERE request_id = 'test_123'"
    )
    assert len(audit_entry) == 1
```

### Property-Based Tests

**Purpose**: This feature is NOT suitable for extensive property-based testing because:

1. **External Service Behavior**: The ML models (CatBoost, XGBoost) are third-party libraries whose behavior we don't control. We test OUR integration logic, not sklearn/catboost internals.

2. **Configuration Validation**: Safety rules, age ranges, and condition urgency scores are configuration, not complex logic requiring 100 iterations.

3. **One-Shot Operations**: Model inference is deterministic for given input; running 100 times with same input doesn't reveal new issues.

**Limited Property Testing** (where applicable):

We will use property-based testing ONLY for:

1. **Preprocessing Invariants**
   - Property: For any age, `age_group` classification is consistent
   - Property: Vital deviations are bounded (|-3| to |+3| typical range)

2. **Formula Correctness**
   - Property: Sub-score weights sum to 1.0 regardless of inputs
   - Property: Sub-score output is always 0-100

3. **Data Model Round-trips**
   - Property: PatientData JSON serialization then deserialization preserves all fields
   - Property: PredictionResponse JSON round-trip maintains data integrity

**Example Property Test**:

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=120))
def test_age_group_classification_property(age):
    """Property: Age group classification is deterministic and consistent."""
    age_group = classify_age_group(age)
    
    # Verify age_group is one of valid values
    assert age_group in [
        'pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 
        'adult', 'geriatric'
    ]
    
    # Verify consistency: same age → same group
    assert classify_age_group(age) == age_group
    
    # Verify boundaries
    if age <= 2:
        assert age_group == 'pediatric_infant'
    elif age <= 12:
        assert age_group == 'pediatric_child'
    elif age <= 17:
        assert age_group == 'pediatric_adolescent'
    elif age <= 64:
        assert age_group == 'adult'
    else:
        assert age_group == 'geriatric'

@given(
    vital_severity=st.floats(min_value=0, max_value=100),
    condition_urgency=st.floats(min_value=0, max_value=100),
    deterioration_rate=st.floats(min_value=0, max_value=100),
    wait_penalty=st.floats(min_value=0, max_value=100)
)
def test_surge_subscore_formula_property(vital_severity, condition_urgency, deterioration_rate, wait_penalty):
    """Property: Sub-score formula produces valid output for any input."""
    sub_score = (
        0.4 * vital_severity +
        0.3 * condition_urgency +
        0.2 * deterioration_rate +
        0.1 * wait_penalty
    )
    
    # Property 1: Output is bounded 0-100
    assert 0 <= sub_score <= 100
    
    # Property 2: Weights sum to 1.0 (formula is normalized)
    weights_sum = 0.4 + 0.3 + 0.2 + 0.1
    assert abs(weights_sum - 1.0) < 1e-10
```

### Load Testing

**Purpose**: Validate system performance under realistic and peak loads

**Tool**: Locust (Python load testing framework)

**Scenarios**:

1. **Baseline Load**: 500 requests/hour (8-10 req/min)
2. **Peak Load**: 2000 requests/hour (33 req/min)
3. **Surge Load**: 5000 requests/hour (83 req/min, temporary spike)

**Acceptance Criteria**:
- p50 latency <60ms at baseline load
- p95 latency <100ms at peak load
- p99 latency <150ms at surge load
- Error rate <0.5% at all loads
- System remains stable for 24+ hours continuous load

**Example Load Test**:

```python
from locust import HttpUser, task, between

class TriageUser(HttpUser):
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    @task
    def predict_esi(self):
        patient_data = generate_random_patient()  # Helper function
        
        self.client.post(
            "/api/v1/predict",
            json=patient_data,
            headers={"X-API-Key": "test_key"}
        )

# Run: locust -f load_test.py --host https://api.patienttriage.ai --users 100 --spawn-rate 10
```



## Correctness Properties

### Property-Based Testing Applicability Assessment

After analyzing the requirements for the PatientTriage.ai ML Core Engine, **property-based testing (PBT) is NOT the primary testing strategy** for this feature. Here's why:

**Reasons PBT is Limited**:

1. **ML Model Behavior**: The core functionality (CatBoost ESI classification, XGBoost deterioration detection) uses third-party ML libraries. We test our integration and preprocessing logic, not the internal behavior of sklearn/catboost/xgboost. These libraries have their own test suites.

2. **Configuration and Rules**: Most requirements specify configuration (age ranges, safety thresholds, condition urgency scores) and rule-based logic (safety validator criteria). These are deterministic checks, not complex algorithms requiring 100 iterations to find edge cases.

3. **External Service Integration**: API endpoints, database operations, and model registry interactions are integration points. Property-based testing doesn't add value over targeted integration tests with mocks.

4. **Performance Requirements**: Many requirements specify performance metrics (accuracy >90%, under-triage <2.5%, latency <100ms). These are validated through benchmark tests and load testing, not property-based tests.

5. **One-Shot Deterministic Operations**: For a given patient input, the model produces a deterministic prediction. Running the same input 100 times doesn't reveal new bugs—it returns the same result.

**Where PBT IS Applicable** (Limited Scope):

We will use property-based testing for a small subset of requirements where universal properties exist:

1. **Data Model Round-trips** (Requirement 20): JSON parsing and pretty-printing should preserve data
2. **Preprocessing Invariants** (Requirement 1): Age group classification should be deterministic
3. **Formula Correctness** (Requirement 5): Surge engine sub-score weights must sum to 1.0
4. **Bounded Outputs**: All scores (confidence, sub-score, deterioration) must be in valid ranges

**Testing Strategy**:

- **Unit Tests** (primary): Test individual components with concrete examples and edge cases
- **Integration Tests** (secondary): Test end-to-end workflows with realistic scenarios
- **Property-Based Tests** (limited): Test invariants in preprocessing and data models
- **Load Tests**: Validate performance requirements under realistic load
- **Clinical Test Scenarios**: Validate on 15-20 hand-crafted vignettes

### Limited Correctness Properties

Despite not being a PBT-heavy feature, we document a few universal properties that DO hold:

#### Property 1: Age Group Classification Consistency

**For any** patient age from 0 to 120, the age group classification SHALL be deterministic and consistent with defined boundaries.

**Validates: Requirement 1.1**

**Test Implementation**:
```python
@given(st.integers(min_value=0, max_value=120))
def test_age_group_deterministic(age):
    group = classify_age_group(age)
    assert group in ['pediatric_infant', 'pediatric_child', 'pediatric_adolescent', 'adult', 'geriatric']
    assert classify_age_group(age) == group  # Deterministic
```

#### Property 2: JSON Round-Trip Preservation

**For any** valid PatientData object, serializing to JSON then deserializing SHALL produce an equivalent object with all field values preserved.

**Validates: Requirement 20.5**

**Test Implementation**:
```python
@given(patient_data_strategy())
def test_patient_data_roundtrip(patient_data):
    json_str = patient_data.json()
    deserialized = PatientData.parse_raw(json_str)
    assert deserialized == patient_data
```

#### Property 3: Sub-Score Bounded Output

**For any** combination of vital severity, condition urgency, deterioration rate, and wait penalty (each 0-100), the computed sub-score SHALL be bounded between 0 and 100.

**Validates: Requirement 5.5**

**Test Implementation**:
```python
@given(
    st.floats(min_value=0, max_value=100),
    st.floats(min_value=0, max_value=100),
    st.floats(min_value=0, max_value=100),
    st.floats(min_value=0, max_value=100)
)
def test_subscore_bounded(vital_severity, condition_urgency, deterioration_rate, wait_penalty):
    sub_score = compute_sub_score(vital_severity, condition_urgency, deterioration_rate, wait_penalty)
    assert 0 <= sub_score <= 100
```

#### Property 4: Confidence Scores Bounded

**For any** prediction, all confidence dimension scores (model certainty, data completeness, clinical consistency, pattern recognition, overall) SHALL be bounded between 0 and 100.

**Validates: Requirement 2.8**

**Test Implementation**:
```python
@given(probability_distribution_strategy(), features_strategy())
def test_confidence_scores_bounded(prob_dist, features):
    confidence = confidence_system.compute_confidence(prob_dist, features, {})
    assert 0 <= confidence.model_certainty <= 100
    assert 0 <= confidence.data_completeness <= 100
    assert 0 <= confidence.clinical_consistency <= 100
    assert 0 <= confidence.pattern_recognition <= 100
    assert 0 <= confidence.overall <= 100
```

#### Property 5: Vital Deviation Age-Specific Normalization

**For any** patient with valid vital signs, the computed vital deviation SHALL be age-group-specific, and patients with identical vitals but different age groups SHALL produce different deviations.

**Validates: Requirement 1.2, Requirement 10.4**

**Test Implementation**:
```python
@given(st.integers(min_value=0, max_value=120), st.integers(min_value=60, max_value=180))
def test_vital_deviation_age_specific(age, hr):
    age_group = classify_age_group(age)
    deviation = compute_hr_deviation(hr, age_group)
    
    # Adult HR 140 should have high deviation
    if age_group == 'adult' and hr == 140:
        assert deviation > 1.5
    
    # Infant HR 140 should have low deviation
    if age_group == 'pediatric_infant' and hr == 140:
        assert abs(deviation) < 1.0
```

### Why We Don't Have More Properties

The majority of requirements fall into these categories, which are not suitable for PBT:

1. **ML Model Behavior** (Req 1.3-1.6, 4.1-4.5, 6.1-6.7, 11, 12): Testing third-party ML library behavior. Use validation datasets and test scenarios instead.

2. **Configuration Rules** (Req 3.1-3.8, 9.1-9.6, 10.1-10.5): Rule-based checks like "if SpO2 <85% then RED". Use unit tests with concrete examples (SpO2 84 → RED, SpO2 86 → check other criteria).

3. **API Integration** (Req 13.1-13.7, 14.1-14.7, 15.1-15.7): HTTP endpoints, database writes, model versioning. Use integration tests and mocks.

4. **System Properties** (Req 16, 17, 18, 19): Security, failure modes, bias monitoring, liability. Use security scans, chaos testing, fairness audits, and compliance validation.

5. **Monitoring and Learning** (Req 7.1-7.7): Override tracking and pattern detection. Use time-series data analysis and statistical tests.

**Conclusion**: This is primarily an **integration-heavy, configuration-driven ML system**. The majority of testing effort goes into:
- Unit tests for preprocessing and business logic
- Integration tests for API and database interactions
- Model validation on held-out datasets
- Clinical test scenarios for real-world validation
- Load tests for performance requirements

Property-based testing plays a minimal role, limited to the 5 properties documented above.

