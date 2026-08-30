# PatientTriage.ai - Solution Architecture
## Complete System Design & Implementation

---

## 📐 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT TIER (Browser)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Patient      │  │ Clinical     │  │ Governance       │  │
│  │ Intake Form  │  │ Queue View   │  │ Audit View       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                  │                   │             │
│         └──────────────────┴───────────────────┘             │
│                          │                                   │
│                    JavaScript                                │
│              (Vanilla JS + Chart.js)                         │
└──────────────────────────┬───────────────────────────────────┘
                          │
                     HTTP/JSON
                          │
┌──────────────────────────┴───────────────────────────────────┐
│                    APPLICATION TIER                           │
│                    FastAPI Backend                            │
├───────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              API Endpoints (app.py)                      │ │
│  │  • POST /api/v1/predict      - ML triage prediction     │ │
│  │  • POST /api/v1/patients     - Add patient to queue     │ │
│  │  • GET  /api/v1/patients     - Fetch queue              │ │
│  │  • POST /api/v1/override     - Log clinician override   │ │
│  │  • GET  /api/v1/overrides    - Get override history     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌───────────────────────┴──────────────────────────────┐   │
│  │              Core ML Pipeline                         │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ 1. Preprocessing (src/preprocessing.py)         │ │   │
│  │  │    • Age group classification                   │ │   │
│  │  │    • Vital sign deviation calculation           │ │   │
│  │  │    • Feature engineering                        │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ 2. ESI Prediction (CatBoost)                    │ │   │
│  │  │    • Gradient boosting classifier               │ │   │
│  │  │    • 5-class output (ESI 1-5)                   │ │   │
│  │  │    • Probability distribution                   │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ 3. Confidence Scoring (src/confidence.py)       │ │   │
│  │  │    • Model certainty (40%)                      │ │   │
│  │  │    • Data completeness (25%)                    │ │   │
│  │  │    • Clinical consistency (20%)                 │ │   │
│  │  │    • Pattern recognition (15%)                  │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ 4. Safety Validation (src/safety_validation.py) │ │   │
│  │  │    • RED flags (force escalation)               │ │   │
│  │  │    • YELLOW flags (recommend validation)        │ │   │
│  │  │    • Override unsafe predictions                │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ 5. Explainability (src/explainer.py)            │ │   │
│  │  │    • SHAP TreeExplainer                         │ │   │
│  │  │    • Feature importance ranking                 │ │   │
│  │  │    • Natural language generation                │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────────┘
                           │
                      File I/O
                           │
┌───────────────────────────┴───────────────────────────────────┐
│                       DATA TIER                                │
├───────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ patients.json    │  │ overrides.json   │  │ Test Data   │ │
│  │ (Queue State)    │  │ (Audit Log)      │  │ (Synthetic) │ │
│  └──────────────────┘  └──────────────────┘  └─────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Component Architecture

### 1. Client Tier - Frontend (HTML/CSS/JavaScript)

#### Files:
- `frontend/index.html` - Patient intake form
- `frontend/queue.html` - Clinical queue & governance views

#### Key Features:
- **Patient Intake Form**: Real-time validation, auto-populated test data
- **Clinical Queue View**: ESI-sorted patient cards, time-left countdown, search
- **Governance Audit View**: Override history, accountability metrics, DPDPA compliance
- **Real-time Updates**: WebSocket-ready architecture (currently polling)
- **Responsive Design**: Desktop and tablet optimized

#### Data Flow:
1. User enters patient data
2. JavaScript validates and collects form data
3. POST request to `/api/v1/predict`
4. Response parsed and displayed
5. Patient saved to queue via `/api/v1/patients`
6. Override logged via `/api/v1/override` if clinician disagrees

---

### 2. Application Tier - Backend (FastAPI + Python)

#### Core File: `app.py`

**API Endpoints:**

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/api/v1/predict` | POST | ML triage prediction | Patient vitals/symptoms | ESI + confidence + explanation |
| `/api/v1/patients` | POST | Add to queue | Patient data + ESI | Patient ID + confirmation |
| `/api/v1/patients` | GET | Fetch queue | None | Array of patients in queue |
| `/api/v1/override` | POST | Log clinician override | Override details | Override ID + confirmation |
| `/api/v1/overrides` | GET | Fetch override history | None | Array of overrides |
| `/docs` | GET | API documentation | None | Interactive Swagger UI |

**Processing Pipeline:**

```python
# 1. Receive patient data
patient_data = PatientRequest(...)

# 2. Preprocess features
processed_features = preprocess_patient_data(patient_data)
# Output: age_group, vital_deviations, engineered_features

# 3. Generate ESI prediction
prediction = esi_model.predict(processed_features)
probabilities = esi_model.predict_proba(processed_features)
# Output: esi_level (1-5), probability_distribution

# 4. Calculate confidence
confidence = calculate_confidence(
    probabilities, patient_data, processed_features
)
# Output: 4-dimensional confidence breakdown + overall level

# 5. Run safety validation
safety_flag = validate_safety(patient_data, prediction, confidence)
# Output: RED/YELLOW/GREEN + override_esi if needed

# 6. Generate explanation
explanation = explain_prediction(
    processed_features, prediction, shap_explainer
)
# Output: SHAP values + natural language text

# 7. Return comprehensive response
return PredictionResponse(
    esi_prediction=final_esi,
    probability_distribution=probabilities,
    confidence_breakdown=confidence,
    safety_flag=safety_flag,
    explanation=explanation
)
```

---

### 3. Data Tier - Storage (JSON Files)

#### Queue State: `data/patients.json`

```json
[
  {
    "patient_id": "patient_abc123",
    "name": "John Doe",
    "demographics": {
      "age": 45,
      "sex": "M"
    },
    "vitals": {
      "hr": 105,
      "bp_systolic": 145,
      "bp_diastolic": 90,
      "spo2": 97,
      "rr": 18,
      "temperature": 37.2
    },
    "clinical": {
      "chief_complaint": "Chest pain",
      "chief_complaint_category": "chest_pain_cardiac",
      "arrival_mode": "ambulance",
      "mental_status": "alert",
      "pain_score": 6
    },
    "prediction": {
      "esi_prediction": 3,
      "probability_distribution": [0.036, 0.071, 0.500, 0.286, 0.107],
      "confidence_breakdown": { ... },
      "safety_flag": { ... }
    },
    "ground_truth_esi": 2,  // If clinician overrode
    "arrival_timestamp": "2026-08-29T10:15:00",
    "waitMinutes": 15,
    "isDeteriorating": false,
    "reassessmentDue": false
  }
]
```

#### Override Audit Log: `data/overrides.json`

```json
[
  {
    "override_id": "override_xyz789",
    "patient_id": "patient_abc123",
    "ml_predicted_esi": 3,
    "clinician_final_esi": 2,
    "override_direction": "escalation",
    "override_magnitude": 1,
    "reason_category": "clinical_judgment",
    "reason_text": "Patient appears more distressed than vitals suggest",
    "clinician_id": "Dr. Jane Smith",
    "timestamp": "2026-08-29T10:16:30"
  }
]
```

---

## 🔄 Data Flow Diagrams

### Primary Workflow: Patient Triage

```
┌─────────┐
│  Nurse  │
└────┬────┘
     │ 1. Enters patient data
     ▼
┌─────────────────┐
│  Intake Form    │
│  (Frontend)     │
└────┬────────────┘
     │ 2. Validates & submits
     ▼
┌─────────────────┐
│  POST /predict  │
│  (FastAPI)      │
└────┬────────────┘
     │ 3. Preprocesses
     ▼
┌─────────────────┐
│  ML Pipeline    │
│  • Preprocess   │
│  • Predict ESI  │
│  • Score conf   │
│  • Validate     │
│  • Explain      │
└────┬────────────┘
     │ 4. Returns results
     ▼
┌─────────────────┐
│  Results Panel  │
│  (Frontend)     │
└────┬────────────┘
     │ 5. Nurse reviews
     ▼
   ┌───────────────┐
   │  Accept?      │
   └───┬───────┬───┘
       │       │
    YES│       │NO (Override)
       │       │
       ▼       ▼
┌──────────┐ ┌─────────────┐
│ Add to   │ │ Override    │
│ Queue    │ │ Dialog      │
└──────────┘ └──┬──────────┘
       │         │ 6. Logs override
       │         ▼
       │    ┌─────────────────┐
       │    │ POST /override  │
       │    └─────────────────┘
       │         │
       └─────┬───┘
             ▼
      ┌─────────────────┐
      │ POST /patients  │
      │ (Add to queue)  │
      └─────────────────┘
             │
             ▼
      ┌─────────────────┐
      │  Clinical Queue │
      │  (Sorted by ESI)│
      └─────────────────┘
```

### Override Workflow

```
┌──────────────┐
│  Clinician   │
│  disagrees   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Override Dialog  │
│ • Select ESI     │
│ • Choose reason  │
│ • Justify (20+)  │
│ • Enter ID       │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ POST /override   │
│ (Log to audit)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│overrides.json    │
│(Appended record) │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Governance View  │
│ • Shows override │
│ • ML vs Clinician│
│ • Accountability │
└──────────────────┘
```

---

## 🧩 Module Breakdown

### Backend Modules

#### `app.py` (Main Application)
- FastAPI application setup
- API endpoint definitions
- Request/response models (Pydantic)
- CORS configuration
- Error handling

**Key Functions:**
- `predict_esi()` - Main prediction endpoint
- `add_patient_to_queue()` - Queue management
- `log_clinician_override()` - Override logging
- `get_overrides()` - Fetch override history

#### `src/preprocessing.py`
**Purpose:** Feature engineering for ML model

**Functions:**
- `classify_age_group(age)` - Pediatric/Adult/Geriatric
- `calculate_vital_deviations(vitals, age_group)` - Z-scores
- `preprocess_patient_data(patient)` - Full pipeline

**Output Features:**
- Age group category
- Vital sign deviations (HR, BP, SpO2, RR, temp)
- Categorical encodings (chief complaint, arrival mode, mental status)
- Binary flags (pediatric, geriatric, arrived_by_ambulance)

#### `src/confidence.py`
**Purpose:** Multi-dimensional confidence scoring

**Functions:**
- `calculate_model_certainty(probabilities)` - Entropy-based
- `calculate_data_completeness(patient_data)` - Field presence
- `check_clinical_consistency(patient_data)` - Discordance detection
- `calculate_pattern_recognition(features)` - OOD detection
- `calculate_overall_confidence(...)` - Weighted average

**Output:** 4 scores + overall level (HIGH/MEDIUM/LOW)

#### `src/safety_validation.py`
**Purpose:** Rule-based safety checks

**Functions:**
- `validate_safety(patient_data, esi, confidence)` - Main validator
- `check_red_flags(patient_data)` - Critical conditions
- `check_yellow_flags(esi, confidence, completeness)` - Caution

**Output:** SafetyFlag (RED/YELLOW/GREEN + recommended action)

#### `src/explainer.py`
**Purpose:** SHAP-based explainability

**Functions:**
- `initialize_shap_explainer(model)` - TreeExplainer setup
- `explain_prediction(features, prediction, explainer)` - SHAP values
- `format_explanation(shap_values, features)` - Natural language

**Output:** Top factors + descriptions + SHAP values

#### `src/models.py`
**Purpose:** ML model loading and inference

**Functions:**
- `load_esi_model()` - Load CatBoost from file
- `predict_esi(features)` - Inference
- `train_esi_model(training_data)` - Training script

**Note:** Current prototype uses heuristic fallback if model unavailable

---

### Frontend Modules

#### `frontend/index.html` - Patient Intake
**Sections:**
1. **Header**: Logo, title, demo patient selector
2. **Form**: Demographics, vitals, clinical info, symptoms
3. **Results Panel**: ESI prediction, confidence, safety flag, charts, explanation
4. **Override Dialog**: Modal for clinician disagreement

**Key JavaScript Functions:**
- `submitPrediction()` - Main form submission
- `displayPredictionResults(data)` - Render results
- `showOverrideDialog()` - Open override modal
- `submitOverride()` - Log override
- `loadDemoPatient(patientData)` - Auto-populate form

#### `frontend/queue.html` - Clinical Queue & Governance
**Views:**
1. **Clinical View**: Patient queue sorted by ESI + time left
2. **Governance View**: Override audit history + accountability

**Key JavaScript Functions:**
- `loadQueueData()` - Fetch patients from API
- `displayQueue()` - Render sorted patient cards
- `createPatientCard(patient)` - Generate card HTML
- `selectPatient(patient)` - Show detail panel
- `removeFromQueue(patientId)` - Remove patient
- `searchPatients(term)` - Real-time search
- `loadAllPatientAudits()` - Governance data
- `renderGovernancePatients(data)` - Audit display
- `searchGovernancePatients(term)` - Governance search

---

## 🔐 Security & Compliance Considerations

### Current Prototype (Demonstration)
- ❌ No authentication/authorization
- ❌ No encryption in transit (HTTP)
- ❌ No data at rest encryption
- ❌ No audit logging for access
- ❌ No PHI protection mechanisms
- ❌ No role-based access control

### Production Requirements
- ✅ OAuth 2.0 + JWT authentication
- ✅ TLS 1.3 encryption (HTTPS)
- ✅ AES-256 encryption at rest
- ✅ Comprehensive audit logs
- ✅ HIPAA compliance (BAA, encryption, audit trail)
- ✅ RBAC (nurse, physician, admin roles)
- ✅ Data retention policies
- ✅ Incident response procedures

### DPDPA 2023 Compliance (India)
- ✅ Purpose limitation (triage only)
- ✅ Data minimization (collect only needed fields)
- ✅ Consent framework (implied for care)
- ✅ Data security (encryption required)
- ✅ Accountability (governance view tracks overrides)
- ❌ User rights (access, correction, deletion) - not implemented
- ❌ Breach notification - not implemented

---

## 📈 Scalability Considerations

### Current Prototype Limitations
- Single server (no load balancing)
- File-based storage (JSON)
- In-memory model (no caching)
- Synchronous processing
- No horizontal scaling

### Production Scaling Strategy

#### Horizontal Scaling
```
┌──────────────┐
│ Load Balancer│
│   (Nginx)    │
└──────┬───────┘
       │
   ┌───┴────┬────────┬────────┐
   ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ App  │ │ App  │ │ App  │ │ App  │
│Server│ │Server│ │Server│ │Server│
│  1   │ │  2   │ │  3   │ │  4   │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
   │        │        │        │
   └────────┴────────┴────────┘
            │
            ▼
    ┌───────────────┐
    │  PostgreSQL   │
    │  (Primary +   │
    │   Read Replicas)
    └───────────────┘
            │
            ▼
    ┌───────────────┐
    │  Redis Cache  │
    │  (Sessions +  │
    │   Model Cache) │
    └───────────────┘
```

#### Database Optimization
- PostgreSQL with connection pooling
- Read replicas for queue views
- Write-ahead logging for overrides
- Partitioning by date for audit logs

#### Caching Strategy
- Redis for:
  - User sessions
  - Model predictions (5-minute TTL)
  - Queue state
  - Test patient data

#### Asynchronous Processing
- Celery for:
  - SHAP computation (offloaded)
  - Batch predictions
  - Report generation
  - Model retraining

---

## 🧪 Testing Strategy

### Unit Tests
- Preprocessing functions (age groups, vital deviations)
- Confidence scoring (each dimension)
- Safety validation (RED/YELLOW/GREEN logic)
- Explainability (SHAP value formatting)

### Integration Tests
- API endpoint responses
- End-to-end prediction flow
- Override logging workflow
- Frontend-backend communication

### Validation Tests
- Clinical vignettes (EM physician review)
- Edge cases (extreme vitals, missing data)
- Bias detection (age, sex, race)
- Safety net effectiveness (RED flag triggers)

### Performance Tests
- Inference latency (target: <100ms)
- Concurrent users (target: 50+ nurses)
- Queue refresh rate
- Override log write speed

---

## 📊 Monitoring & Observability

### Key Metrics (Production)

#### Model Performance
- **Accuracy**: ESI prediction vs ground truth
- **Precision/Recall**: Per ESI level
- **Calibration**: Predicted probabilities vs actual outcomes
- **Bias**: Performance by demographics

#### System Performance
- **Latency**: p50, p95, p99 inference time
- **Throughput**: Predictions per second
- **Error Rate**: Failed predictions
- **Uptime**: 99.9% SLA

#### Clinical Safety
- **Override Rate**: % of predictions overridden
- **Override Direction**: Escalation vs de-escalation
- **RED Flag Triggers**: Count by type
- **Under-Triage Events**: Missed high-acuity cases

#### User Engagement
- **Active Users**: Nurses using system
- **Prediction Acceptance**: % accepted without override
- **Average Session Time**
- **Feature Usage**: Which views/features used most

---

## 🔄 Deployment Pipeline

### CI/CD Workflow

```
┌──────────────┐
│  Developer   │
│  Commits     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    GitHub    │
│  Repository  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  CI Pipeline │
│  (GitHub     │
│   Actions)   │
│  • Lint      │
│  • Test      │
│  • Build     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Docker Image│
│  (Artifact   │
│   Registry)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Staging Env │
│  • Smoke test│
│  • UAT       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Production  │
│  • Blue-green│
│  • Rollback  │
└──────────────┘
```

---

## 💡 Design Decisions & Rationale

### Why CatBoost?
- **Categorical features**: Native handling (no one-hot encoding)
- **Robustness**: Resistant to overfitting
- **Speed**: Fast inference (<10ms)
- **Explainability**: SHAP compatible

### Why Multi-Dimensional Confidence?
- **Transparency**: Clinicians see why confidence is low
- **Actionable**: Can address specific dimension (e.g., complete missing data)
- **Safety**: Different dimensions matter for different ESI levels

### Why Rule-Based Safety Layer?
- **Fail-safe**: Catches ML errors
- **Interpretability**: Clear criteria
- **Regulatory**: Easier to validate than black-box
- **Bias mitigation**: Ensures minimum standards

### Why JSON Storage?
- **Prototype simplicity**: No database setup
- **Human-readable**: Easy debugging
- **Version control**: Can track in git
- **Limitation acknowledged**: Will migrate to PostgreSQL for production

---

## 📌 Summary

**Architecture Type:** Monolithic (prototype) → Microservices (production)

**Key Strengths:**
- Clear separation of concerns (preprocessing → prediction → validation → explanation)
- Multi-layered safety (ML + rules + human override)
- Full audit trail for accountability
- Explainable AI at every step

**Key Limitations:**
- Single server (no HA)
- File storage (no ACID guarantees)
- No auth/authz
- Not HIPAA-compliant
- Synthetic data only

**Production Path:**
1. Database migration (PostgreSQL)
2. Authentication layer (OAuth 2.0)
3. Horizontal scaling (load balancer + multiple app servers)
4. Caching (Redis)
5. Async processing (Celery)
6. Monitoring (Prometheus + Grafana)
7. Clinical validation study

---

**This architecture demonstrates a production-ready design pattern adapted for rapid prototyping.**
