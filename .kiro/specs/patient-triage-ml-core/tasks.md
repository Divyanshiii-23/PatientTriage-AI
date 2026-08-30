# Implementation Plan: PatientTriage.ai ML Core Engine

## Overview

This implementation plan breaks down the PatientTriage.ai ML Core Engine into discrete, manageable tasks covering all components from data models to deployment. The system provides real-time ESI triage recommendations, continuous deterioration monitoring, surge mode sub-prioritization, multi-dimensional confidence scoring, safety validation, and SHAP-based explainability for Emergency Department triage.

**Technology Stack**: Python 3.10+, FastAPI, CatBoost, XGBoost, SHAP, PostgreSQL, Redis, MLflow, Prometheus, Grafana

**Implementation Approach**: Foundation-first (data models, infrastructure) → Core ML (preprocessing, models, confidence) → Safety & Explainability → API & Integration → Testing & Deployment

## Tasks

### 1. Foundation: Data Models and Infrastructure

- [ ] 1.1 Create Pydantic data models for API contracts
  - Implement `PatientData` with demographics, vitals, symptoms, clinical data, observations, medical history
  - Implement `ProcessedFeatures` with age group, vital deviations, discordance flags, missing indicators, data completeness score
  - Implement `ConfidenceBreakdown` with model certainty, data completeness, clinical consistency, pattern recognition, overall score, confidence level
  - Implement `SafetyValidation` with outcome (RED/YELLOW/GREEN), triggered criteria, recommended action
  - Implement `PredictionResponse` with ESI prediction, probability distribution, confidence breakdown, safety validation, SHAP explanation, sub-score, model version
  - Implement `DeteriorationRequest` and `DeteriorationResponse` with temporal vital changes, deterioration status, score, explanation
  - Add field validators for physiologically valid ranges (age 0-120, HR 20-300, SpO2 0-100, temperature 32-45°C)
  - Add custom serialization for consistent JSON formatting
  - _Requirements: 1.3, 13.1, 13.2, 20.1, 20.3, 20.4_

- [ ] 1.2 Write property test for PatientData JSON round-trip
  - **Property 2: JSON Round-Trip Preservation**
  - **Validates: Requirements 20.5, 20.6**
  - Use Hypothesis to generate arbitrary valid PatientData objects
  - Test: serialize to JSON → deserialize → verify all fields preserved
  - Test edge cases: missing optional fields, extreme values, unicode in text fields

- [x] 1.3 Set up PostgreSQL schema for audit logging and override tracking
  - Create `predictions` table with columns: id, timestamp, request_id, model_version, patient_features (JSONB), esi_prediction, probability_distribution, confidence_breakdown, safety_outcome, explanation, inference_time_ms
  - Create `overrides` table with columns: id, prediction_id, timestamp, ml_predicted_esi, ml_confidence, clinician_final_esi, override_reason_category, override_reason_text, clinician_id, patient_outcome
  - Create `deterioration_alerts` table with columns: id, timestamp, patient_id, esi_level, deterioration_score, deterioration_status, vital_changes (JSONB), time_since_last_assessment, alert_reason
  - Add indexes on timestamp, model_version, esi_prediction, safety_outcome for query performance
  - Enable row-level encryption for PHI compliance
  - Set up 7-year retention policy with automated archival
  - _Requirements: 7.1, 15.1, 15.2, 15.3, 15.4, 16.2_

- [ ] 1.4 Set up Redis cache for age-specific lookup tables
  - Load `AGE_SPECIFIC_VITAL_RANGES` into Redis hash: pediatric_infant, pediatric_child, pediatric_adolescent, adult, geriatric with HR, RR, BP, SpO2, temperature ranges
  - Load `CONDITION_URGENCY_LOOKUP` into Redis hash: 50+ chief complaint categories with urgency scores 0-30
  - Implement cache preloading on application startup
  - Add cache hit/miss metrics for monitoring
  - Set up connection pooling (min 5, max 50 connections)
  - _Requirements: 5.2, 10.1, 10.2_

- [ ] 1.5 Set up MLflow model registry
  - Configure MLflow tracking server with PostgreSQL backend
  - Define model schema with metadata: training_date, performance_metrics (accuracy, under_triage_rate, F1_scores), age_group_metrics, bias_audit_results
  - Implement model registration function with version tagging
  - Implement model loading with version specification (production vs shadow)
  - Set up model staging transitions: None → Staging → Production → Archived
  - _Requirements: 14.1, 14.2, 14.6_

### 2. Preprocessing Pipeline

- [ ] 2.1 Implement age group classification and vital deviation computation
  - Implement `classify_age_group()` function: 0-2 → pediatric_infant, 3-12 → pediatric_child, 13-17 → pediatric_adolescent, 18-64 → adult, 65+ → geriatric
  - Implement `compute_vital_deviation()` for each vital: (actual - age_midpoint) / age_range_width
  - Fetch age-specific ranges from Redis cache with fallback to hardcoded defaults
  - Handle missing vitals gracefully (return None for deviation)
  - Return normalized deviations typically in range -2 to +2
  - _Requirements: 1.1, 1.2, 10.2, 10.3_

- [ ]* 2.2 Write property test for age group classification determinism
  - **Property 1: Age Group Classification Consistency**
  - **Validates: Requirements 1.1, 10.1**
  - Use Hypothesis to generate ages 0-120
  - Test: same age always produces same age group
  - Test: boundary conditions (age 2, 12, 17, 64, 65)

- [ ]* 2.3 Write property test for vital deviation age-specific normalization
  - **Property 5: Vital Deviation Age-Specific Normalization**
  - **Validates: Requirements 10.3, 10.4**
  - Use Hypothesis to generate patient pairs with same vitals, different ages
  - Test: adult HR=140 produces high deviation, infant HR=140 produces low deviation
  - Test: all vitals (HR, RR, BP, SpO2, temp) are age-normalized

- [ ] 2.4 Implement symptom-vital discordance detection
  - Implement `detect_pain_underreporting()`: pain_score < 4 AND HR > 110 → flag True
  - Implement `detect_severity_underreporting()`: chief_complaint in MINOR_COMPLAINTS AND count_abnormal_vitals() >= 3 → flag True
  - Implement `detect_respiratory_underreporting()`: SpO2 < 93 AND no respiratory symptoms → flag True
  - Implement `count_abnormal_vitals()` helper using age-specific thresholds
  - Return dictionary of discordance flags for confidence system
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 2.5 Implement missing data handling and completeness scoring
  - Create `is_missing_*` indicator features for all optional fields (temperature, pain_score, medical_history, medications)
  - Implement `compute_data_completeness_score()`: present_features / total_expected_features
  - Define expected feature count: 40 features (demographics, vitals, deviations, clinical, symptoms, history, observations, discordance flags)
  - Handle None values gracefully in all preprocessing functions
  - Return ProcessedFeatures object with all engineered features
  - _Requirements: 8.2, 8.4, 8.5, 8.6_

- [ ] 2.6 Implement complete preprocessing pipeline orchestration
  - Implement `preprocess_patient_data(raw_data: PatientData) -> ProcessedFeatures` 
  - Pipeline steps: 1) Age group classification, 2) Vital deviation computation, 3) Discordance detection, 4) Missing indicator generation, 5) Data completeness calculation
  - Add preprocessing duration metrics (target <5ms)
  - Add validation for physiologically impossible values (reject if critical vitals invalid)
  - Log preprocessing errors with patient request ID for debugging
  - _Requirements: 1.3, 8.1, 17.7_

### 3. Age-Stratified ESI Classifier (CatBoost)

- [ ] 3.1 Implement training data ingestion and validation
  - Load training data from CSV/Parquet files (minimum 50,000 ED records)
  - Validate required columns: demographics, vitals, chief_complaint, symptoms, medical_history, clinician_assigned_esi, final_diagnosis, outcome_data
  - Validate age group balance: minimum 15% representation in pediatric, adult, geriatric groups
  - Validate ESI distribution: check for class imbalance
  - Filter invalid records: missing critical fields, physiologically impossible values, ESI outside 1-5 range
  - Generate data quality report: record count, missingness by feature, class distribution
  - _Requirements: 11.1, 11.2, 11.4, 11.5_

- [ ] 3.2 Implement feature engineering for training data
  - Apply preprocessing pipeline to all training records
  - Create age_group categorical feature
  - Compute vital deviations for all vitals
  - Create symptom count and binary symptom flags (chest_pain, sob, altered_consciousness, bleeding)
  - Create comorbidity flags from medical history
  - Create clinical observation flags (visible_distress, hemodynamic_instability)
  - Create discordance flags
  - Handle missing data with CatBoost-compatible encoding (None preserved)
  - Generate feature importance baseline from input distribution
  - _Requirements: 1.3, 8.2, 8.3, 10.2_

- [ ] 3.3 Implement stratified train/validation/test split
  - Split data: 70% train, 15% validation, 15% test
  - Stratify by age_group AND esi_level to maintain proportional representation
  - Use random seed 42 for reproducibility
  - Validate splits: check age group distribution, ESI distribution match source data
  - Save split indices for experiment reproducibility
  - _Requirements: 11.6_

- [ ] 3.4 Train CatBoost ESI classifier with custom under-triage penalty
  - Configure CatBoost hyperparameters: iterations=1000, learning_rate=0.05, depth=6, loss_function='MultiClass', bootstrap_type='Bayesian'
  - Set categorical features: chief_complaint_category, arrival_mode, mental_status, age_group
  - Set class weights: {0: 10, 1: 5, 2: 2, 3: 1, 4: 1} for 10× under-triage penalty
  - Train with early stopping (50 rounds) on validation set
  - Monitor training: log loss curve, validation accuracy, per-class F1 scores
  - Use best model from validation performance
  - Save training metrics to MLflow
  - _Requirements: 1.4, 1.5, 14.1_

- [ ]* 3.5 Write unit tests for CatBoost training pipeline
  - Test: training data validation rejects invalid records
  - Test: feature engineering produces expected feature count (40+)
  - Test: stratified split maintains age group proportions
  - Test: trained model produces valid output shape (5 probabilities)
  - Test: class weights are applied correctly

- [ ] 3.6 Validate age-stratified performance metrics
  - Compute overall metrics: accuracy, macro F1, under-triage rate, over-triage rate, confusion matrix
  - Compute per-age-group metrics: pediatric, adult, geriatric accuracy and under-triage rates
  - Compute per-ESI metrics: precision, recall, F1 for each ESI level 1-5
  - Validate: overall accuracy > 90%, under-triage rate < 2.5%, all age groups accuracy > 85%
  - Generate calibration plots: predicted probabilities vs observed frequencies
  - Save validation report to MLflow
  - _Requirements: 1.6, 12.1, 12.2, 12.5, 12.6_

- [ ] 3.7 Implement bias audit across demographics
  - Compute performance metrics separately for male vs female patients
  - Compute performance metrics separately for each age group
  - Compute performance metrics for each chief complaint category
  - Check for disparities: under-triage rate difference > 5 percentage points triggers fairness alert
  - Generate bias audit report with statistical significance tests
  - Log bias metrics to MLflow and flag affected demographic groups
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7_

- [ ] 3.8 Run clinical test scenarios and edge cases
  - Test 15-20 clinical vignettes: ambiguous presentations, pediatric critical cases, geriatric falls, chest pain variants, sepsis presentations
  - Test missing data scenarios: only required fields present, 70% completeness, 90% completeness
  - Test boundary cases: age 0, 2, 12, 17, 64, 65, 120
  - Test out-of-distribution cases: extremely rare chief complaints, unusual vital combinations
  - Validate predictions align with clinical expectations (expert review)
  - Document test results and any concerning predictions
  - _Requirements: 11.7_

- [ ] 3.9 Serialize and register model to MLflow
  - Save CatBoost model with metadata: training_date, hyperparameters, feature list, categorical features
  - Log validation metrics: accuracy, F1 scores, under-triage rate, age group performance
  - Log bias audit report as artifact
  - Log test scenario results as artifact
  - Register model to MLflow registry with version tag (e.g., v2.1.0)
  - Transition model to "Staging" stage for shadow mode testing
  - _Requirements: 14.1, 14.2_

### 4. Multi-Dimensional Confidence System

- [ ] 4.1 Implement model certainty computation from entropy
  - Implement `compute_model_certainty(probability_distribution: np.ndarray) -> float`
  - Calculate Shannon entropy: -sum(p * log(p))
  - Normalize: certainty = 100 * (1 - entropy / log(5))
  - Handle edge cases: uniform distribution → 0 certainty, peaked distribution (0.95) → 95 certainty
  - Return float 0-100
  - _Requirements: 2.1_

- [ ] 4.2 Implement clinical consistency scoring from discordance
  - Implement `compute_clinical_consistency(discordance_flags: Dict[str, bool]) -> float`
  - Calculate: 100 * (1 - triggered_flags / total_flags)
  - Apply exponential penalty: consistency *= (0.7 ** triggered_flags)
  - 0 flags → 100%, 1 flag → 70%, 2 flags → 49%, 3 flags → 34%
  - Return float 0-100
  - _Requirements: 2.3, 9.5_

- [ ] 4.3 Train Isolation Forest for out-of-distribution detection
  - Train Isolation Forest on training feature distributions (40+ features)
  - Configure: contamination=0.05 (assume 5% outliers), n_estimators=200, random_state=42
  - Fit on preprocessed training features only (exclude target ESI)
  - Validate: compute anomaly scores on validation set, check score distribution
  - Save trained Isolation Forest to MLflow with ESI classifier
  - Load on inference for pattern recognition scoring
  - _Requirements: 2.4, 17.5, 17.6_

- [ ] 4.4 Implement pattern recognition scoring from OOD detection
  - Implement `compute_pattern_recognition(features: ProcessedFeatures) -> float`
  - Convert features to numpy array for Isolation Forest input
  - Compute anomaly score: isolation_forest.score_samples([feature_vector])[0]
  - Normalize: pattern_score = 50 * (anomaly_score + 1) to convert from [-1, 1] to [0, 100]
  - Low anomaly score (in-distribution) → high confidence ~75-100
  - High anomaly score (OOD) → low confidence ~0-25
  - Return float 0-100
  - _Requirements: 2.4_

- [ ] 4.5 Implement multi-dimensional confidence aggregation
  - Implement `ConfidenceSystem.compute_confidence()` with weighted average
  - Weights: model_certainty=0.40, data_completeness=0.25, clinical_consistency=0.20, pattern_recognition=0.15
  - Compute overall = weighted sum of four dimensions
  - Classify: HIGH (≥80), MEDIUM (60-80), LOW (<60)
  - Return ConfidenceBreakdown with all dimension scores, overall score, confidence level
  - _Requirements: 2.5, 2.8_

- [ ]* 4.6 Write property test for confidence scores bounded
  - **Property 4: Confidence Scores Bounded**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
  - Use Hypothesis to generate arbitrary probability distributions and features
  - Test: all confidence dimensions (model certainty, data completeness, clinical consistency, pattern recognition, overall) are in range [0, 100]
  - Test: overall confidence is weighted average of dimensions
  - Test: confidence level classification (HIGH/MEDIUM/LOW) matches thresholds

- [ ] 4.7 Implement confidence-driven recommendations
  - Implement `generate_confidence_recommendations(confidence: ConfidenceBreakdown, predicted_esi: int) -> List[str]`
  - Rule 1: LOW confidence + ESI ≥3 → recommend escalation by one level
  - Rule 2: data_completeness < 70% → recommend obtaining more data
  - Rule 3: clinical_consistency < 50% → recommend probing for under-reporting
  - Rule 4: pattern_recognition < 30% → flag OOD, recommend specialist consultation
  - Return list of actionable recommendation strings
  - _Requirements: 2.6, 2.7, 8.7, 9.6_

### 5. Safety Validation Layer

- [ ] 5.1 Implement critical clinical criteria checker
  - Implement `check_critical_criteria(patient_data: PatientData, features: ProcessedFeatures) -> List[str]`
  - Criterion 1: chest pain + age > 50 → "CRITICAL: Chest pain in patient >50 years (cardiac risk)"
  - Criterion 2: SpO2 < 85% → "CRITICAL: SpO2 X% (severe hypoxia)"
  - Criterion 3: mental_status != 'alert' OR altered_consciousness observation → "CRITICAL: Altered level of consciousness"
  - Criterion 4: active_bleeding + BP_systolic < 90 → "CRITICAL: Active bleeding with hypotension"
  - Criterion 5: RR > 30 (adult/geriatric) OR SpO2 < 90% → "CRITICAL: Severe respiratory distress"
  - Criterion 6: 'seizure' in chief_complaint → "CRITICAL: Active or recent seizure"
  - Return list of triggered critical criteria descriptions
  - _Requirements: 3.1_

- [ ] 5.2 Implement age-specific vital threshold checker
  - Implement `check_vital_thresholds(patient_data: PatientData, features: ProcessedFeatures) -> List[str]`
  - Fetch age-specific critical thresholds from Redis
  - Check HR: adult >140 or <40 → flag, pediatric infant >180 or <100 → flag
  - Check BP: adult systolic <90 or >180 → flag, geriatric <90 → flag (hemorrhage risk)
  - Check SpO2: <92% (any age) → flag
  - Check RR: adult >30 or <8 → flag, pediatric >60 → flag
  - Check temperature: >39.5°C (high fever) or <35°C (hypothermia) → flag
  - Return list of triggered vital threshold flags
  - _Requirements: 3.2, 10.5_

- [ ] 5.3 Implement confidence and data quality validators
  - Implement `check_confidence(confidence: ConfidenceBreakdown, ml_prediction: int) -> List[str]`
  - If confidence.level == "LOW" → flag for validation
  - If confidence.data_completeness < 70% → flag missing critical data
  - Implement `check_data_quality(features: ProcessedFeatures) -> List[str]`
  - Check for missing critical fields: age, HR, BP, SpO2, RR, chief_complaint
  - Return lists of confidence and data quality flags
  - _Requirements: 3.3, 3.4_

- [ ] 5.4 Implement OOD detection flag
  - Implement `check_ood(pattern_recognition_score: float) -> List[str]`
  - If pattern_recognition < 30 → flag "Patient presentation is out-of-distribution"
  - Return list with OOD flag if triggered
  - _Requirements: 3.5_

- [ ] 5.5 Implement safety outcome determination
  - Implement `SafetyValidator.determine_outcome(triggered_criteria: List[str], ml_prediction: int) -> SafetyValidation`
  - RED outcome: any critical clinical criteria OR severe vital threshold violations → force ESI to 1 or 2, mandatory clinician review
  - YELLOW outcome: LOW confidence OR data quality issues OR OOD flag → recommend escalation or validation
  - GREEN outcome: no safety concerns → approve ML prediction as-is
  - Return SafetyValidation with outcome, triggered criteria, recommended action
  - _Requirements: 3.6, 3.7, 3.8, 3.9_

- [ ]* 5.6 Write unit tests for safety validation rules
  - Test: chest pain + age 55 triggers RED outcome with forced ESI 1-2
  - Test: SpO2 84% triggers RED outcome
  - Test: LOW confidence + ESI 4 triggers YELLOW outcome with escalation recommendation
  - Test: normal vitals + HIGH confidence triggers GREEN outcome
  - Test: OOD patient triggers YELLOW outcome
  - Test: missing critical fields triggers YELLOW outcome

### 6. Deterioration Detection (XGBoost)

- [ ] 6.1 Implement temporal feature engineering for vital changes
  - Implement `compute_temporal_features(initial_vitals: dict, current_vitals: dict, time_delta_minutes: int) -> dict`
  - Compute delta features: delta_hr, delta_spo2, delta_bp_sys, delta_bp_dia, delta_rr, delta_temp
  - Compute percentage change: pct_change_hr = (current - initial) / initial * 100
  - Compute rate of change: rate_hr = delta_hr / time_delta_minutes (change per minute)
  - Compute trajectory: vital_trend = 'worsening' if delta crosses threshold, 'stable' otherwise
  - Compute volatility: standard deviation of vital readings if multiple measurements
  - Compute multi-parameter features: num_vitals_worsening, num_vitals_critical
  - Return dictionary with 20+ temporal features
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 6.2 Prepare deterioration training data
  - Extract records with temporal vital measurements (minimum 30% of training data)
  - Label DETERIORATING if: patient eventually required higher ESI, ICU admission, or adverse event
  - Label STABLE if: patient ESI remained same or improved, no adverse events
  - Create temporal features for all record pairs (initial triage vs later assessment)
  - Validate: minimum 5,000 deteriorating cases, balanced class distribution
  - Split: 70% train, 15% validation, 15% test with stratification
  - _Requirements: 11.3_

- [ ] 6.3 Train XGBoost deterioration detector
  - Configure XGBoost hyperparameters: objective='binary:logistic', max_depth=5, learning_rate=0.05, n_estimators=500, scale_pos_weight=2.0
  - Train on temporal features with early stopping (50 rounds) on validation set
  - Monitor: log loss, AUROC, AUPRC, sensitivity, specificity
  - Use best model from validation AUROC
  - Save training metrics to MLflow
  - _Requirements: 4.4_

- [ ] 6.4 Validate deterioration detector performance
  - Compute metrics: sensitivity, specificity, AUROC, AUPRC, false-alert rate
  - Validate: sensitivity > 85%, false-alert rate < 10%
  - Compute time-to-detection: average minutes from deterioration start to detection
  - Generate calibration plot for deterioration probabilities
  - Test on clinical scenarios: sepsis progression, respiratory failure, cardiac decompensation
  - Save validation report to MLflow
  - _Requirements: 4.4, 12.3, 12.8_

- [ ] 6.5 Implement deterioration classification logic
  - Implement `classify_deterioration(deterioration_score: float, confidence: float) -> str`
  - DETERIORATING: score ≥ 60 and confidence ≥ 50 → "Patient shows signs of clinical deterioration"
  - STABLE: score < 40 → "Patient condition appears stable"
  - UNCERTAIN: score 40-60 OR confidence < 50 → "Uncertain, recommend clinical assessment"
  - Return deterioration status with score 0-100
  - _Requirements: 4.4_

- [ ] 6.6 Implement monitoring interval scheduler
  - Implement `compute_monitoring_interval(esi_level: int) -> int` (returns minutes)
  - ESI 1: None (already in resuscitation, not waiting)
  - ESI 2: 15 minutes
  - ESI 3: 30 minutes
  - ESI 4: 60 minutes
  - ESI 5: 60 minutes
  - Implement wait time safety net: ESI 2 > 30 min wait OR ESI 3 > 60 min wait → auto alert regardless of vitals
  - _Requirements: 4.6, 4.7, 4.8, 4.9, 4.10_

- [ ]* 6.7 Write unit tests for deterioration detection
  - Test: temporal feature engineering produces correct delta, rate, trajectory features
  - Test: deterioration classification logic (DETERIORATING, STABLE, UNCERTAIN) follows score thresholds
  - Test: monitoring interval matches ESI-specific schedules
  - Test: wait time safety net triggers at correct thresholds (ESI 2 > 30 min, ESI 3 > 60 min)

- [ ] 6.8 Serialize and register deterioration detector to MLflow
  - Save XGBoost model with metadata: training_date, hyperparameters, feature list
  - Log validation metrics: sensitivity, specificity, AUROC, false-alert rate
  - Register model to MLflow registry with version tag
  - Link to ESI classifier version for compatibility tracking
  - _Requirements: 14.1, 14.2_

### 7. Surge Mode Sub-Prioritization Engine

- [ ] 7.1 Implement vital severity score computation
  - Implement `compute_vital_severity_score(vitals: dict, age_group: str) -> float` (returns 0-40)
  - For each vital, compute deviation from age-specific normal range
  - Score each vital: 0 points (normal), 4 points (mildly abnormal), 8 points (severely abnormal)
  - Sum across 5 vitals: HR, BP, SpO2, RR, temperature (max 40 points)
  - Use age-specific thresholds from Redis
  - _Requirements: 5.1_

- [ ] 7.2 Load condition urgency lookup table into Redis
  - Create urgency mapping for 50+ chief complaint categories
  - High urgency (25-30 points): chest pain, stroke symptoms, major trauma, severe bleeding, sepsis, anaphylaxis
  - Medium urgency (15-24 points): abdominal pain, fractures, moderate trauma, respiratory distress, altered mental status
  - Low urgency (5-14 points): minor injuries, rashes, chronic complaints, medication refills
  - Very low urgency (0-4 points): administrative, preventive care
  - Preload into Redis on startup with cache metrics
  - _Requirements: 5.2_

- [ ] 7.3 Implement deterioration rate score computation
  - Implement `compute_deterioration_rate_score(deterioration_score: float, time_delta: int) -> float` (returns 0-20)
  - If deterioration_score ≥ 60 (DETERIORATING): base 15 points + 5 points if rapid (< 30 min)
  - If deterioration_score 40-60 (UNCERTAIN): 8 points
  - If deterioration_score < 40 (STABLE): 0 points
  - Adjust for rate: faster deterioration → higher score
  - _Requirements: 5.3_

- [ ] 7.4 Implement wait time penalty computation
  - Implement `compute_wait_time_penalty(esi_level: int, wait_minutes: int) -> float` (returns 0-10)
  - ESI 2: 1 point per 10 minutes (max 10 points at 100 min)
  - ESI 3: 1 point per 20 minutes (max 10 points at 200 min)
  - ESI 4: 1 point per 40 minutes (max 10 points at 400 min)
  - ESI 5: 1 point per 60 minutes (max 10 points at 600 min)
  - Ensure wait time doesn't override clinical acuity (capped at 10%)
  - _Requirements: 5.4_

- [ ] 7.5 Implement total sub-score computation and patient ranking
  - Implement `compute_sub_score(vital_severity: float, condition_urgency: float, deterioration_rate: float, wait_penalty: float) -> float`
  - Sum all components: sub_score = vital_severity + condition_urgency + deterioration_rate + wait_penalty (max 100)
  - Implement `rank_patients_in_surge(patients: List[PatientRecord]) -> List[PatientRecord]`
  - Sort by: 1) ESI level (ascending, 1 = highest priority), 2) sub_score (descending), 3) arrival_time (ascending)
  - Return ranked patient list
  - _Requirements: 5.5, 5.6, 5.7_

- [ ]* 7.6 Write property test for sub-score bounded output
  - **Property 3: Sub-Score Bounded Output**
  - **Validates: Requirements 5.5**
  - Use Hypothesis to generate arbitrary vital severity (0-40), condition urgency (0-30), deterioration rate (0-20), wait penalty (0-10)
  - Test: computed sub_score is always in range [0, 100]
  - Test: sub_score is sum of components
  - Test: sub_score never exceeds 100 even with max inputs

- [ ]* 7.7 Write unit tests for surge engine ranking
  - Test: patients sorted first by ESI (1 before 2 before 3)
  - Test: within same ESI, sorted by sub_score descending
  - Test: within same ESI and sub_score, sorted by arrival time ascending
  - Test: sub_score components computed correctly (vital severity, condition urgency, deterioration rate, wait penalty)

### 8. SHAP Explainability System

- [ ] 8.1 Implement SHAP TreeExplainer integration for ESI classifier
  - Load trained CatBoost ESI classifier
  - Initialize SHAP TreeExplainer: `explainer = shap.TreeExplainer(esi_model)`
  - Cache explainer in memory per model version (compute once, reuse)
  - Implement `compute_shap_values(features: ProcessedFeatures) -> np.ndarray`
  - Return SHAP values for predicted class (shape: 40+ features)
  - Add SHAP computation time metrics (target <100ms)
  - _Requirements: 6.1_

- [ ] 8.2 Implement SHAP TreeExplainer integration for deterioration detector
  - Load trained XGBoost deterioration detector
  - Initialize SHAP TreeExplainer: `explainer = shap.TreeExplainer(deterioration_model)`
  - Cache explainer in memory
  - Implement `compute_deterioration_shap_values(temporal_features: dict) -> np.ndarray`
  - Return SHAP values for positive class (deteriorating)
  - _Requirements: 6.2_

- [ ] 8.3 Implement top feature selection and explanation formatting
  - Implement `select_top_features(shap_values: np.ndarray, feature_names: List[str], n: int = 5) -> List[Tuple[str, float]]`
  - Sort features by absolute SHAP value descending
  - Select top 3-5 features
  - Return list of (feature_name, shap_value) tuples
  - _Requirements: 6.3_

- [ ] 8.4 Implement human-readable explanation generation
  - Implement `generate_explanation_text(top_features: List[Tuple[str, float]], patient_data: PatientData) -> List[str]`
  - Map feature names to human-readable descriptions: 'hr_deviation' → 'Heart rate', 'spo2' → 'Oxygen saturation'
  - Classify severity: critical (red), concerning (yellow), normal (green) based on threshold
  - Format: "[Severity] [Feature Name]: [Value] ([Direction] ESI level by [SHAP value])"
  - Example: "🔴 CRITICAL - Oxygen saturation: 88% (increases ESI urgency by 0.42)"
  - Example: "🟡 CONCERNING - Heart rate: 125 bpm (increases ESI urgency by 0.18)"
  - Example: "🟢 NORMAL - Temperature: 37.1°C (minimal impact)"
  - _Requirements: 6.4, 6.5, 6.7_

- [ ] 8.5 Implement complete explainability pipeline
  - Implement `ExplainabilitySystem.generate_explanation(prediction: int, shap_values: np.ndarray, patient_data: PatientData) -> List[str]`
  - Combine: SHAP computation → top feature selection → human-readable formatting
  - Validate total time < 500ms (SHAP < 100ms, formatting < 50ms, rest for safety/confidence)
  - Return structured explanation list for API response
  - _Requirements: 6.6_

- [ ]* 8.6 Write unit tests for SHAP explainability
  - Test: SHAP values computed for all features (length = 40+)
  - Test: top features selected correctly (sorted by absolute SHAP value)
  - Test: explanation text formatted correctly with severity classification
  - Test: feature name humanization works (hr_deviation → "Heart rate")
  - Test: explanation generation completes within 500ms

### 9. Override Tracking and Learning System

- [ ] 9.1 Implement override logging to database
  - Implement `log_override(prediction_id: str, ml_prediction: int, ml_confidence: ConfidenceBreakdown, clinician_final_esi: int, override_reason_category: str, override_reason_text: str, clinician_id: str) -> None`
  - Write to `overrides` table with all fields
  - Record timestamp, link to original prediction via prediction_id
  - Validate override reason category from predefined list: "clinical_judgment", "vital_concern", "symptom_concern", "history_concern", "patient_request", "other"
  - _Requirements: 7.1_

- [ ] 9.2 Implement outcome data recording
  - Implement `record_outcome(prediction_id: str, disposition: str, adverse_events: List[str], time_to_treatment_minutes: int) -> None`
  - Update `overrides` table with outcome data when available
  - Disposition: "discharged", "admitted_ward", "admitted_icu", "transferred", "left_ama", "deceased"
  - Adverse events: "cardiac_arrest", "respiratory_failure", "septic_shock", "stroke", "mi", "none"
  - _Requirements: 7.2_

- [ ] 9.3 Implement pattern analysis for systematic errors
  - Implement `analyze_override_patterns() -> Dict[str, float]`
  - Query overrides table grouped by: age_group, chief_complaint_category, sex
  - Compute override rate for each pattern: (overrides / total predictions) * 100
  - Identify patterns with override rate > 15% → systematic error
  - Return dictionary: {pattern_description: override_rate_percentage}
  - _Requirements: 7.3, 7.4_

- [ ] 9.4 Implement retraining recommendation generation
  - Implement `generate_retraining_recommendations() -> List[str]`
  - For each systematic error pattern (override rate > 15%):
    - Generate recommendation: "Model under-triages [age_group] patients with [chief_complaint] (X% override rate). Recommend retraining with additional focus on this subgroup."
  - Prioritize by: 1) Under-triage rate, 2) Patient volume, 3) Adverse event frequency
  - Return list of actionable recommendations with data collection targets
  - _Requirements: 7.4_

- [ ] 9.5 Implement agreement rate and override breakdown metrics
  - Implement `compute_agreement_metrics(time_window_days: int = 30) -> Dict`
  - Query predictions and overrides in rolling window
  - Compute agreement_rate = (predictions - overrides) / predictions * 100
  - Compute override breakdown: frequency of each override reason category
  - Compute under-triage override rate: overrides where clinician_esi < ml_esi
  - Compute over-triage override rate: overrides where clinician_esi > ml_esi
  - Return metrics dictionary
  - _Requirements: 7.5, 7.6_

- [ ] 9.6 Implement performance trend tracking
  - Implement `compute_performance_trends() -> Dict`
  - Query data in rolling 30-day windows for past 6 months
  - Compute trends: agreement_rate_over_time, override_rate_over_time, under_triage_rate_over_time
  - Detect degradation: agreement rate decreasing > 5 percentage points → alert
  - Generate dashboard data for Grafana visualization
  - Return time series data
  - _Requirements: 7.7_

- [ ]* 9.7 Write unit tests for override tracking
  - Test: override logging writes all fields correctly to database
  - Test: outcome recording updates existing override records
  - Test: pattern analysis identifies groups with high override rates
  - Test: retraining recommendations generated for patterns > 15% override rate
  - Test: agreement rate computed correctly (predictions - overrides) / predictions

### 10. FastAPI Application and Endpoints

- [ ] 10.1 Set up FastAPI application with middleware
  - Initialize FastAPI app with title, version, description, OpenAPI docs
  - Add GZip compression middleware for response size reduction
  - Add CORS middleware with allowed origins (configurable)
  - Add request ID middleware for tracing (generate UUID per request)
  - Add timing middleware for latency metrics
  - Add rate limiting middleware (500 req/hour default, configurable per client)
  - _Requirements: 13.4, 13.5_

- [ ] 10.2 Implement POST /api/v1/predict endpoint
  - Define endpoint: `@app.post("/api/v1/predict", response_model=PredictionResponse)`
  - Accept `PatientData` JSON body
  - Validate request schema (Pydantic auto-validation)
  - Pipeline: 1) Preprocess, 2) ESI prediction, 3) Confidence scoring, 4) Safety validation, 5) SHAP explanation, 6) Sub-score computation
  - Async audit logging in background task (non-blocking)
  - Return PredictionResponse with all fields
  - Target latency: <100ms p95
  - _Requirements: 13.1, 13.2, 13.3_

- [ ] 10.3 Implement POST /api/v1/deterioration endpoint
  - Define endpoint: `@app.post("/api/v1/deterioration", response_model=DeteriorationResponse)`
  - Accept `DeteriorationRequest` with patient_id, initial_vitals, current_vitals, time_delta
  - Compute temporal features
  - Run deterioration detector
  - Compute SHAP explanation for deterioration
  - Classify: DETERIORATING, STABLE, UNCERTAIN
  - Log deterioration alert if DETERIORATING
  - Return DeteriorationResponse
  - _Requirements: 4.4, 4.5, 13.1_

- [ ] 10.4 Implement GET /api/v1/health endpoint
  - Define endpoint: `@app.get("/api/v1/health")`
  - Check model availability: ESI classifier loaded, deterioration detector loaded, Isolation Forest loaded
  - Check database connection: PostgreSQL ping
  - Check cache connection: Redis ping
  - Check model version: return production model version
  - Return health status: "healthy" if all checks pass, "degraded" if issues, "unhealthy" if critical failure
  - _Requirements: 13.1_

- [ ] 10.5 Implement admin endpoints for model management
  - `GET /api/v1/models`: List available model versions from MLflow registry
  - `POST /api/v1/models/{version}/activate`: Switch production model to specified version
  - `GET /api/v1/models/shadow`: Get shadow mode status
  - `POST /api/v1/models/shadow/enable`: Enable shadow mode with specified model version
  - `POST /api/v1/models/shadow/disable`: Disable shadow mode
  - Require admin token authentication (Bearer token from environment variable)
  - _Requirements: 14.3, 14.6_

- [ ] 10.6 Implement error handling and safe fallback
  - Add global exception handler for unhandled exceptions
  - Return HTTP 400 for invalid input (missing fields, invalid types, out-of-range values)
  - Return HTTP 500 for internal errors (model failure, database error)
  - Return HTTP 503 for service unavailable (model not loaded)
  - Implement safe fallback: if model inference fails, return ESI 2 with LOW confidence and safety flag RED
  - Log all errors to application logs and Sentry for debugging
  - _Requirements: 17.1, 17.2, 13.5, 13.6_

- [ ]* 10.7 Write integration tests for API endpoints
  - Test: POST /predict with valid patient data returns 200 with PredictionResponse
  - Test: POST /predict with missing required fields returns 400 with error message
  - Test: POST /predict with invalid field types returns 400
  - Test: POST /deterioration with valid data returns DeteriorationResponse
  - Test: GET /health returns health status with model availability
  - Test: admin endpoints require authentication (401 without token)
  - Test: end-to-end prediction includes all components (preprocessing, ML, confidence, safety, explanation)

### 11. Model Loading and Inference Pipeline

- [ ] 11.1 Implement model loading from MLflow registry
  - Implement `load_production_model() -> Tuple[CatBoostClassifier, xgb.XGBClassifier, IsolationForest, str]`
  - Query MLflow registry for models in "Production" stage
  - Load ESI classifier, deterioration detector, Isolation Forest
  - Load SHAP explainers and cache in memory
  - Return models and model version identifier
  - Add model loading time metrics
  - _Requirements: 14.2, 14.6_

- [ ] 11.2 Implement shadow mode dual prediction
  - Implement `predict_with_shadow(patient_data: PatientData, production_model, shadow_model) -> Tuple[PredictionResponse, PredictionResponse]`
  - Run both production and shadow models on same input
  - Compute predictions, confidence, safety validation for both
  - Log both predictions with shadow flag to audit log
  - Return production prediction to client (shadow prediction hidden)
  - Add shadow mode metrics: agreement rate, prediction differences
  - _Requirements: 14.3, 14.4, 14.5_

- [ ] 11.3 Implement comparative metrics for shadow mode
  - Implement `compute_shadow_comparison(production_predictions: List, shadow_predictions: List) -> Dict`
  - Compute agreement rate: % of predictions where production_esi == shadow_esi
  - Compute under-triage differential: shadow under-triage rate - production under-triage rate
  - Compute confidence differential: average confidence difference
  - Compute performance differential: accuracy, F1 comparison (requires ground truth from overrides)
  - Generate comparison report for shadow model evaluation
  - _Requirements: 14.7_

- [ ] 11.4 Implement complete inference pipeline
  - Implement `inference_pipeline(patient_data: PatientData) -> PredictionResponse`
  - Steps: 1) Preprocessing (5ms), 2) ESI prediction (10ms), 3) Confidence scoring (5ms), 4) Safety validation (5ms), 5) SHAP explanation (50ms), 6) Sub-score (5ms), 7) Response formation (5ms)
  - Total target: <100ms p95
  - Add per-step latency metrics
  - Handle failures gracefully with safe fallback
  - _Requirements: 13.3_

- [ ]* 11.5 Write unit tests for model loading and inference
  - Test: production model loads successfully from MLflow
  - Test: shadow mode runs both models and returns production prediction
  - Test: inference pipeline completes all steps in correct order
  - Test: inference pipeline meets latency target (<100ms typical)
  - Test: safe fallback returns ESI 2 with LOW confidence on model failure

### 12. Caching and Performance Optimization

- [ ] 12.1 Implement Redis connection pooling
  - Configure Redis connection pool: min 5 connections, max 50 connections, socket timeout 5s
  - Implement `get_redis_client() -> redis.Redis` with connection reuse
  - Add connection health check on startup
  - Add cache hit/miss metrics (Prometheus counters)
  - Handle Redis failures gracefully: fallback to hardcoded defaults if cache unavailable
  - _Requirements: 1.4_

- [ ] 12.2 Implement age range and condition urgency caching
  - Preload `AGE_SPECIFIC_VITAL_RANGES` into Redis hash on startup
  - Preload `CONDITION_URGENCY_LOOKUP` into Redis hash on startup
  - Implement `get_age_specific_ranges(age_group: str) -> Dict` with Redis fetch
  - Implement `get_condition_urgency(chief_complaint: str) -> float` with Redis fetch
  - Add cache warming on application startup
  - _Requirements: 10.1_

- [ ] 12.3 Implement SHAP explainer caching
  - Cache SHAP TreeExplainer in-memory per model version
  - Implement `get_cached_shap_explainer(model_version: str) -> shap.TreeExplainer`
  - Recompute explainer only when model version changes
  - Add explainer cache metrics (cache hits, misses)
  - _Requirements: 6.1, 6.2_

- [ ] 12.4 Implement duplicate request detection
  - Cache recent predictions in Redis with 5-minute TTL
  - Key: hash of patient demographics + vitals + timestamp (rounded to minute)
  - On new request, check cache for duplicate
  - If duplicate found within 5 minutes, return cached prediction (avoid redundant inference)
  - Add duplicate detection metrics
  - _Requirements: 13.4_

- [ ] 12.5 Implement model quantization for faster inference
  - Apply CatBoost quantization: convert float features to 8-bit integers
  - Test quantized model: validate accuracy loss < 0.5 percentage points
  - Measure inference speedup: expect 20-30% latency reduction
  - Deploy quantized model if accuracy acceptable
  - _Requirements: 13.3_

- [ ]* 12.6 Write unit tests for caching
  - Test: Redis connection pool works with concurrent requests
  - Test: age range caching returns correct values from Redis
  - Test: SHAP explainer cached correctly per model version
  - Test: duplicate request detection returns cached prediction
  - Test: cache failures fallback to hardcoded defaults gracefully

### 13. Checkpoint - Core System Integration

- [ ] 13. Checkpoint - Verify core ML pipeline integration
  - Verify end-to-end prediction works: patient data → preprocessing → ESI prediction → confidence → safety → explanation → response
  - Verify deterioration detection works: initial + current vitals → temporal features → deterioration score → classification
  - Verify surge engine works: patient list → ranking by ESI + sub-score
  - Verify all models loaded: ESI classifier, deterioration detector, Isolation Forest, SHAP explainers
  - Run 10 test predictions with clinical vignettes, validate outputs
  - Run load test: 100 concurrent requests, verify latency <100ms p95
  - Ensure all tests pass, ask the user if questions arise

### 14. Monitoring and Alerting

- [ ] 14.1 Implement Prometheus metrics instrumentation
  - Counter: `predictions_total` labeled by esi_level, confidence_level, safety_outcome
  - Counter: `overrides_total` labeled by override_reason_category
  - Counter: `deterioration_alerts_total` labeled by esi_level, deterioration_status
  - Histogram: `prediction_latency_seconds` with buckets [0.01, 0.05, 0.1, 0.2, 0.5]
  - Histogram: `shap_computation_seconds` with buckets [0.01, 0.05, 0.1, 0.2]
  - Gauge: `model_version` (current production model version as gauge value)
  - Gauge: `cache_hit_rate` (Redis cache hit rate 0-1)
  - Counter: `errors_total` labeled by error_type, endpoint
  - _Requirements: 12.3, 12.4_

- [ ] 14.2 Set up Grafana dashboard for real-time metrics
  - Create dashboard: "PatientTriage ML Core - Real-Time Performance"
  - Panel 1: Prediction volume over time (predictions per hour)
  - Panel 2: ESI distribution (bar chart of ESI 1-5 percentages)
  - Panel 3: Confidence level distribution (HIGH/MEDIUM/LOW percentages)
  - Panel 4: Safety outcome distribution (RED/YELLOW/GREEN percentages)
  - Panel 5: Latency percentiles (p50, p95, p99 line chart)
  - Panel 6: Under-triage rate (rolling 24-hour window)
  - Panel 7: Override rate (rolling 24-hour window)
  - Panel 8: Cache hit rate (Redis)
  - _Requirements: 12.4_

- [ ] 14.3 Configure Prometheus alert rules
  - Alert: `HighUnderTriageRate` if under_triage_rate > 3.5% for 1 hour → CRITICAL
  - Alert: `HighErrorRate` if errors_total rate > 5% for 15 minutes → WARNING
  - Alert: `HighLatency` if prediction_latency p95 > 150ms for 10 minutes → WARNING
  - Alert: `ModelUnavailable` if model_version gauge == 0 → CRITICAL
  - Alert: `DatabaseDown` if database connection fails → CRITICAL
  - Alert: `CacheDown` if Redis connection fails → WARNING
  - Alert: `BiasDetected` if demographic group under-triage disparity > 5 percentage points → WARNING
  - _Requirements: 17.4, 18.4_

- [ ] 14.4 Set up bias monitoring dashboard
  - Create dashboard: "PatientTriage ML Core - Bias Monitoring"
  - Panel 1: Under-triage rate by sex (male vs female)
  - Panel 2: Under-triage rate by age group (pediatric, adult, geriatric)
  - Panel 3: Accuracy by demographic subgroup (heatmap)
  - Panel 4: Override rate by demographic subgroup
  - Panel 5: Statistical significance tests (chi-square p-values for performance disparities)
  - Panel 6: Fairness alerts (list of demographic groups flagged for bias)
  - _Requirements: 18.1, 18.2, 18.3, 18.5_

- [ ] 14.5 Set up override tracking dashboard
  - Create dashboard: "PatientTriage ML Core - Override Analysis"
  - Panel 1: Agreement rate over time (rolling 30-day window)
  - Panel 2: Override rate over time
  - Panel 3: Override reason breakdown (pie chart)
  - Panel 4: Systematic error patterns (table: pattern, override rate, recommendation)
  - Panel 5: Outcome analysis (disposition by override vs non-override)
  - Panel 6: Time-to-treatment comparison (override vs non-override)
  - _Requirements: 7.5, 7.6, 7.7_

### 15. Deployment and Infrastructure

- [ ] 15.1 Create Dockerfile for ML Core service
  - Base image: python:3.10-slim
  - Install system dependencies: libgomp1 (for CatBoost), build-essential
  - Install Python dependencies: fastapi, uvicorn, catboost, xgboost, shap, redis, psycopg2, mlflow, prometheus-client
  - Copy application code
  - Expose port 8000
  - Set environment variables: MODEL_REGISTRY_URI, DATABASE_URI, REDIS_URI
  - Health check: curl http://localhost:8000/api/v1/health
  - Run command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

- [ ] 15.2 Set up blue-green deployment configuration
  - Create Kubernetes deployment: `ml-core-blue` and `ml-core-green`
  - Configure service: `ml-core-service` pointing to active deployment (blue or green)
  - Implement deployment script: 1) Deploy new version to inactive environment, 2) Run smoke tests, 3) Switch service to new environment, 4) Keep old environment for 1 hour (quick rollback)
  - Add deployment metrics: deployment_count, rollback_count
  - _Requirements: 14.6_

- [ ] 15.3 Configure AWS infrastructure provisioning (Terraform)
  - ECS cluster for ML Core service (4 tasks, 2 vCPU, 4 GB RAM each)
  - RDS PostgreSQL instance (db.t3.medium, 100 GB SSD, multi-AZ)
  - ElastiCache Redis cluster (cache.t3.medium, 2 nodes)
  - Application Load Balancer with health checks
  - S3 bucket for MLflow artifacts
  - CloudWatch logs for application logs
  - IAM roles for ECS task execution and MLflow access

- [ ] 15.4 Set up load balancer and auto-scaling
  - Configure ALB: health check path `/api/v1/health`, target port 8000, timeout 5s, interval 30s
  - Set up target group with sticky sessions (session affinity for cache efficiency)
  - Configure auto-scaling: CPU > 70% for 5 minutes → scale up, CPU < 30% for 10 minutes → scale down
  - Min instances: 2, Max instances: 10
  - Add auto-scaling metrics to Grafana
  - _Requirements: 13.4_

- [ ] 15.5 Implement rollback procedures
  - Create rollback script: switch service back to previous deployment (blue ↔ green)
  - Rollback triggers: under-triage rate spike (>5%), error rate spike (>10%), latency spike (p95 >200ms)
  - Automatic rollback: if health checks fail for 5 minutes post-deployment
  - Manual rollback: admin command via API or kubectl
  - Add rollback alerts to Slack/PagerDuty
  - _Requirements: 14.6_

### 16. Testing and Validation

- [ ]* 16.1 Write unit tests for preprocessing functions
  - Test: `classify_age_group()` with boundary cases (0, 2, 12, 17, 64, 65, 120)
  - Test: `compute_vital_deviation()` for each vital with age-specific ranges
  - Test: `detect_pain_underreporting()` with various pain scores and HR combinations
  - Test: `detect_severity_underreporting()` with minor complaints + abnormal vitals
  - Test: `detect_respiratory_underreporting()` with low SpO2 + no respiratory symptoms
  - Test: `compute_data_completeness_score()` with varying missing fields

- [ ]* 16.2 Write unit tests for confidence system
  - Test: `compute_model_certainty()` with uniform distribution (low certainty) vs peaked distribution (high certainty)
  - Test: `compute_clinical_consistency()` with 0, 1, 2, 3 discordance flags
  - Test: `compute_pattern_recognition()` with in-distribution vs OOD features
  - Test: `compute_confidence()` weighted aggregation produces correct overall score
  - Test: confidence level classification (HIGH ≥80, MEDIUM 60-80, LOW <60)

- [ ]* 16.3 Write unit tests for safety validator
  - Test: chest pain + age 60 triggers RED outcome
  - Test: SpO2 84% triggers RED outcome with forced ESI 1-2
  - Test: altered consciousness triggers RED outcome
  - Test: active bleeding + BP 85 triggers RED outcome
  - Test: LOW confidence + ESI 4 triggers YELLOW outcome
  - Test: normal vitals + HIGH confidence triggers GREEN outcome

- [ ]* 16.4 Write unit tests for surge engine
  - Test: `compute_vital_severity_score()` with normal vitals (0 points) vs abnormal vitals (max 40)
  - Test: `compute_condition_urgency_score()` for high urgency (chest pain) vs low urgency (rash)
  - Test: `compute_deterioration_rate_score()` for DETERIORATING vs STABLE
  - Test: `compute_wait_time_penalty()` for ESI 2 at 60 minutes vs ESI 5 at 300 minutes
  - Test: `rank_patients_in_surge()` sorts by ESI first, then sub-score, then arrival time

- [ ]* 16.5 Write integration test for end-to-end prediction
  - Test: create PatientData with realistic values
  - Test: call POST /api/v1/predict endpoint
  - Test: verify response contains esi_prediction (1-5), probability_distribution (5 values sum to 1.0), confidence_breakdown (4 dimensions + overall), safety_validation (outcome + criteria), explanation (3-5 factors), sub_score (0-100), model_version
  - Test: verify latency <100ms p95
  - Test: verify audit log entry created in database

- [ ]* 16.6 Write property-based tests for correctness properties
  - Test: Property 1 (Age Group Classification Consistency) - already in task 2.2
  - Test: Property 2 (JSON Round-Trip Preservation) - already in task 1.2
  - Test: Property 3 (Sub-Score Bounded Output) - already in task 7.6
  - Test: Property 4 (Confidence Scores Bounded) - already in task 4.6
  - Test: Property 5 (Vital Deviation Age-Specific Normalization) - already in task 2.3

- [ ]* 16.7 Run load testing with Locust
  - Configure Locust: 100 users, spawn rate 10 users/second, duration 10 minutes
  - Test POST /api/v1/predict with realistic patient data (vary demographics, vitals, symptoms)
  - Measure: requests per second (target >500/hour = 0.14/s baseline), latency percentiles (p50, p95, p99), error rate
  - Validate: p95 latency <100ms, error rate <1%, no memory leaks
  - Generate load test report with graphs
  - _Requirements: 13.3, 13.4_

### 17. Clinical Test Scenarios

- [ ] 17.1 Create 15-20 clinical test vignettes
  - Vignette 1: Pediatric febrile seizure (2 years old, fever 39.5°C, recent seizure, altered mental status)
  - Vignette 2: Adult chest pain (55 years old, substernal chest pain, HR 98, BP 140/90, no prior cardiac history)
  - Vignette 3: Geriatric fall (78 years old, fall from standing, hip pain, HR 88, BP 150/85)
  - Vignette 4: Sepsis presentation (45 years old, fever 38.8°C, HR 115, RR 24, BP 95/60, altered mental status)
  - Vignette 5: Minor injury (25 years old, ankle sprain, pain score 4, normal vitals)
  - Vignette 6: Respiratory distress (60 years old, SOB, SpO2 88%, RR 28, history of COPD)
  - Vignette 7: Abdominal pain ambiguous (30 years old, abdominal pain, pain score 6, normal vitals)
  - Vignette 8: Pediatric respiratory (8 months old, cough, RR 55, SpO2 94%, fever 38.2°C)
  - Vignette 9: Stroke symptoms (70 years old, sudden weakness, slurred speech, BP 180/100)
  - Vignette 10: Anaphylaxis (35 years old, hives, throat swelling, BP 85/55, HR 120)
  - Vignettes 11-20: Additional scenarios covering trauma, overdose, psychiatric crisis, diabetic emergencies, etc.
  - _Requirements: 11.7_

- [ ] 17.2 Run model predictions on clinical vignettes
  - For each vignette, create PatientData object
  - Run inference pipeline: preprocessing → prediction → confidence → safety → explanation
  - Record: predicted ESI, confidence breakdown, safety outcome, explanation factors
  - Compare to expected clinical ESI (expert clinician ground truth)
  - Document any discrepancies or concerning predictions
  - _Requirements: 11.7_

- [ ] 17.3 Expert clinical review of vignette predictions
  - Present vignette predictions to clinical experts (EM physicians)
  - Review: ESI prediction, confidence scores, safety flags, explanation factors
  - Collect feedback: appropriate/inappropriate, concerning patterns, suggested improvements
  - Validate explanations are clinically sensible
  - Document expert consensus on model performance
  - _Requirements: 11.7_

### 18. Security and Compliance

- [ ] 18.1 Implement TLS encryption for API
  - Configure Uvicorn with TLS certificate: uvicorn --ssl-keyfile key.pem --ssl-certfile cert.pem
  - Enforce HTTPS only (redirect HTTP → HTTPS)
  - Use TLS 1.3 minimum version
  - Configure strong cipher suites (AES-256-GCM preferred)
  - Add HSTS header: max-age=31536000; includeSubDomains
  - _Requirements: 16.1_

- [ ] 18.2 Implement AES-256 encryption for data at rest
  - Enable PostgreSQL transparent data encryption (TDE) for audit logs
  - Enable Redis encryption at rest
  - Encrypt MLflow artifacts in S3 with SSE-S3 or SSE-KMS
  - Configure key rotation policy: rotate encryption keys every 90 days
  - _Requirements: 15.5, 16.2_

- [ ] 18.3 Implement role-based access control (RBAC)
  - Define roles: `api_user` (POST /predict, POST /deterioration), `admin` (model management), `auditor` (read-only audit logs)
  - Implement API key authentication for api_user role
  - Implement admin token authentication for admin endpoints
  - Implement read-only database role for auditor access
  - Add access logs: timestamp, user_id, action, resource accessed
  - _Requirements: 16.5, 16.6_

- [ ] 18.4 Implement data retention and purge policies
  - Configure audit log retention: 7 years (medical record requirement)
  - Implement automated archival: move records >1 year old to cold storage (S3 Glacier)
  - Implement purge function: delete records after retention period with admin approval
  - Add data purge logs: timestamp, records purged, admin_id
  - _Requirements: 15.4, 16.7_

- [ ] 18.5 Implement PHI de-identification for model training
  - Remove direct identifiers: name, MRN, DOB, address, phone, email
  - Tokenize quasi-identifiers: patient_id → hashed_id
  - Preserve: demographics (age, sex), vitals, symptoms, clinical data, outcomes
  - Validate: no PHI in training datasets (automated scan + manual review)
  - Document de-identification methodology for compliance audits
  - _Requirements: 16.4_

- [ ] 18.6 Document HIPAA compliance controls
  - Document encryption controls: TLS 1.3 in transit, AES-256 at rest
  - Document access controls: RBAC, API key authentication, admin token
  - Document audit logging: comprehensive logs for all PHI access
  - Document data retention and purge policies
  - Document breach notification procedure
  - Document business associate agreements (BAA) requirements
  - _Requirements: 16.1, 16.2, 16.5, 16.6_

### 19. Documentation and Knowledge Transfer

- [ ] 19.1 Write API documentation (OpenAPI/Swagger)
  - Document POST /api/v1/predict: request schema, response schema, examples, error codes
  - Document POST /api/v1/deterioration: request schema, response schema, examples
  - Document GET /api/v1/health: response schema
  - Document admin endpoints: authentication requirements, request/response schemas
  - Add example requests and responses for each endpoint
  - Add error code reference: 400 (invalid input), 401 (unauthorized), 500 (internal error), 503 (unavailable)
  - _Requirements: 13.1, 13.5, 13.6_

- [ ] 19.2 Write deployment guide
  - Document infrastructure requirements: ECS cluster, RDS, ElastiCache, ALB, S3
  - Document environment variables: MODEL_REGISTRY_URI, DATABASE_URI, REDIS_URI, ADMIN_TOKEN, SENTRY_DSN
  - Document deployment steps: 1) Build Docker image, 2) Push to ECR, 3) Deploy to ECS, 4) Run smoke tests, 5) Switch traffic
  - Document rollback procedure
  - Document scaling configuration
  - Document monitoring and alerting setup
  - _Requirements: 14.6_

- [ ] 19.3 Write model training guide
  - Document training data requirements: minimum 50,000 records, balanced age groups, required fields
  - Document preprocessing steps: feature engineering, stratified split
  - Document CatBoost hyperparameters and training configuration
  - Document XGBoost hyperparameters for deterioration detector
  - Document validation metrics and acceptance criteria
  - Document bias audit procedure
  - Document model registration to MLflow
  - _Requirements: 11.1, 11.5, 11.6_

- [ ] 19.4 Write clinical user guide
  - Explain AI as clinical decision support (not replacement for judgment)
  - Explain confidence levels: HIGH (trust), MEDIUM (caution), LOW (validate)
  - Explain safety outcomes: RED (critical, review required), YELLOW (validate), GREEN (accept)
  - Explain SHAP explanations: how to interpret contributing factors
  - Provide examples: high confidence prediction, low confidence with escalation, safety override
  - Document override process and importance of feedback
  - _Requirements: 19.1, 19.2, 19.3_

- [ ] 19.5 Write compliance and legal documentation
  - Document that ML Core provides recommendations, clinicians make decisions
  - Document compliance with 21st Century Cures Act CDS exemption criteria
  - Document that system does not require FDA device regulation
  - Document liability: clinician retains decision authority and accountability
  - Document informed consent requirements (hospital policy dependent)
  - Document incident reporting procedure for adverse events
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7_

### 20. Final Checkpoint and Production Readiness

- [ ] 20. Final checkpoint - Production readiness validation
  - Verify all unit tests pass (preprocessing, confidence, safety, surge, explainability)
  - Verify all integration tests pass (end-to-end prediction, deterioration detection)
  - Verify all property-based tests pass (5 correctness properties)
  - Verify load testing meets targets (p95 latency <100ms, >500 req/hour)
  - Verify clinical vignettes produce acceptable predictions (expert review)
  - Verify monitoring dashboards operational (Grafana + Prometheus)
  - Verify security controls implemented (TLS, encryption, RBAC)
  - Verify documentation complete (API, deployment, training, clinical user guide)
  - Run smoke test on staging environment (10 predictions, validate correctness)
  - Get sign-off from clinical stakeholders, engineering lead, compliance officer
  - Ensure all tests pass, ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.3", "1.4", "1.5"]
    },
    {
      "id": 1,
      "tasks": ["1.2", "2.1", "3.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "2.4", "2.5", "3.2"]
    },
    {
      "id": 3,
      "tasks": ["2.6", "3.3"]
    },
    {
      "id": 4,
      "tasks": ["3.4"]
    },
    {
      "id": 5,
      "tasks": ["3.5", "3.6", "3.7", "3.8", "4.3"]
    },
    {
      "id": 6,
      "tasks": ["3.9", "4.1", "4.2", "4.4", "6.2"]
    },
    {
      "id": 7,
      "tasks": ["4.5", "6.1"]
    },
    {
      "id": 8,
      "tasks": ["4.6", "4.7", "5.1", "5.2", "5.3", "5.4", "6.3"]
    },
    {
      "id": 9,
      "tasks": ["5.5", "6.4"]
    },
    {
      "id": 10,
      "tasks": ["5.6", "6.5", "6.6", "7.2"]
    },
    {
      "id": 11,
      "tasks": ["6.7", "6.8", "7.1", "7.3", "7.4"]
    },
    {
      "id": 12,
      "tasks": ["7.5", "8.1", "8.2"]
    },
    {
      "id": 13,
      "tasks": ["7.6", "7.7", "8.3", "8.4"]
    },
    {
      "id": 14,
      "tasks": ["8.5", "9.1", "9.2", "10.1"]
    },
    {
      "id": 15,
      "tasks": ["8.6", "9.3", "9.4", "10.2", "10.3", "10.4"]
    },
    {
      "id": 16,
      "tasks": ["9.5", "9.6", "10.5", "10.6", "11.1"]
    },
    {
      "id": 17,
      "tasks": ["9.7", "10.7", "11.2", "11.3", "12.1", "12.2"]
    },
    {
      "id": 18,
      "tasks": ["11.4", "12.3", "12.4", "12.5"]
    },
    {
      "id": 19,
      "tasks": ["11.5", "12.6"]
    },
    {
      "id": 20,
      "tasks": ["14.1", "14.2", "15.1", "17.1"]
    },
    {
      "id": 21,
      "tasks": ["14.3", "14.4", "14.5", "15.2", "15.3", "17.2"]
    },
    {
      "id": 22,
      "tasks": ["15.4", "15.5", "17.3", "18.1", "18.2", "18.3"]
    },
    {
      "id": 23,
      "tasks": ["16.1", "16.2", "16.3", "16.4", "16.5", "18.4", "18.5"]
    },
    {
      "id": 24,
      "tasks": ["16.6", "16.7", "18.6", "19.1", "19.2"]
    },
    {
      "id": 25,
      "tasks": ["19.3", "19.4", "19.5"]
    }
  ]
}
```

## Notes

- **Tasks marked with `*` are optional** and can be skipped for faster MVP delivery. These are primarily test-related sub-tasks that validate correctness but are not required for core functionality.
- **Checkpoint tasks (13, 20)** ensure incremental validation at major milestones. Stop and verify system integration before proceeding.
- **Property-based tests** validate the 5 universal correctness properties documented in the design. These test fundamental invariants that must always hold.
- **Each task references specific requirements** for traceability. Use requirement IDs (e.g., 1.1, 2.3) to map tasks back to acceptance criteria.
- **Implementation language**: Python 3.10+ with FastAPI, CatBoost, XGBoost, SHAP, PostgreSQL, Redis, MLflow
- **Critical path**: Foundation (Wave 0-1) → Preprocessing (Wave 2-3) → ML Models (Wave 4-6) → Confidence & Safety (Wave 7-10) → API (Wave 14-19) → Testing & Deployment (Wave 20-25)
- **Parallel execution**: Tasks within the same wave are independent and can be executed in parallel for faster development
- **Testing strategy**: Unit tests for components, integration tests for end-to-end flows, property tests for correctness invariants, load tests for performance, clinical vignettes for validation
- **Security first**: TLS encryption, AES-256 at rest, RBAC, audit logging, PHI de-identification for compliance
- **Monitoring early**: Instrument metrics from the start, set up dashboards and alerts before production deployment
- **Clinical accountability**: AI provides recommendations, clinicians make decisions. Override tracking feeds continuous improvement loop.
