# PatientTriage.ai - Clinical Interface Workflow Prototype

A **1-day prototype** demonstrating an ML-powered Emergency Department triage system with real-time ESI (Emergency Severity Index) classification, explainable AI, confidence scoring, and safety validation.

![Status](https://img.shields.io/badge/status-prototype-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 🎯 Overview

PatientTriage.ai is a clinical decision support prototype that demonstrates how machine learning can assist emergency department triage nurses in assessing patient acuity. The system provides:

- **ESI Level Prediction** (1-5): Real-time classification based on patient demographics, vitals, and symptoms
- **Multi-Dimensional Confidence Scoring**: Transparent confidence metrics across 4 dimensions
- **Safety Validation Layer**: Rule-based checks to catch high-risk cases and override unsafe predictions
- **SHAP Explainability**: Natural language explanations showing which factors influenced the prediction
- **Interactive Web Interface**: Single-page application for rapid patient data entry and visualization
- **Clinician Override Tracking**: Log disagreements to improve model over time

**⚠️ Important**: This is a **demonstration prototype** trained on synthetic data. It is NOT intended for clinical use and should not be used for actual patient care decisions.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 2GB RAM minimum
- macOS, Linux, or Windows

### Installation

1. **Clone or download this repository**

```bash
cd /path/to/PatientTriage.ai
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

Required packages:
- `fastapi` - Web framework for API endpoints
- `uvicorn` - ASGI server
- `catboost` - ML model for ESI classification
- `xgboost` - ML model for deterioration detection (if implemented)
- `shap` - Explainability framework
- `numpy` - Numerical computations
- `pandas` - Data manipulation
- `pydantic` - Data validation
- `scikit-learn` - Isolation Forest for OOD detection

3. **Verify installation**

```bash
python -c "import fastapi, catboost, shap; print('✓ All dependencies installed')"
```

### Running the Application

1. **Start the FastAPI backend server**

```bash
uvicorn app:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

2. **Open the frontend in your browser**

```bash
# macOS
open frontend/index.html

# Linux
xdg-open frontend/index.html

# Windows
start frontend/index.html
```

Or manually navigate to: `file:///path/to/Win/frontend/index.html`

3. **Verify the connection**

The API documentation is available at: http://localhost:8000/docs

---

## 📖 Demo Walkthrough

### Step 1: Load a Test Patient

1. At the top of the page, find the **"Load Test Patient"** dropdown
2. Select a patient scenario (e.g., "Ambiguous Chest Pain - 45yo Male")
3. The form will auto-populate with realistic patient data

**Available Test Scenarios:**
- **Ambiguous Cases**: Borderline ESI 2/3 presentations
- **Pediatric Cases**: Infant fever, child respiratory distress
- **Geriatric Cases**: Falls, trauma in elderly patients
- **High-Risk Cases**: Low SpO2, chest pain in older adults
- **Low-Acuity Cases**: Minor injuries, simple complaints
- **Zero-History Cases**: Testing data completeness penalties

### Step 2: Review Auto-Populated Data

The form will show:
- **Demographics**: Age, sex, special badges (PEDIATRIC, GERIATRIC)
- **Vital Signs**: HR, RR, BP, SpO2, temperature
- **Clinical Info**: Chief complaint, arrival mode, mental status, pain score
- **Data Completeness**: Real-time percentage indicator

### Step 3: Submit for AI Prediction

1. Click **"Get AI Triage Recommendation"**
2. Wait for the API response (~100ms typical)
3. View the comprehensive results panel

### Step 4: Interpret the Results

The right panel displays:

#### ESI Level Prediction
- **Large color-coded badge** (ESI 1-5)
- **Description** of urgency level
- **Visual alerts** if ESI 1 (pulsing red border)

#### Safety Flag Banner
- **GREEN**: No safety concerns - approve prediction
- **YELLOW**: Caution advised - recommend validation
- **RED**: Critical safety alert - requires immediate review
  - Displays triggered criteria (e.g., "SpO2 < 90%")
  - May override ML prediction (force ESI 1 or 2)
  - **Pulsing animation** for visibility

#### Probability Distribution Chart
- Horizontal bar chart showing confidence for each ESI level
- Helps visualize prediction uncertainty

#### Confidence Breakdown
- **Model Certainty**: Based on probability distribution entropy
- **Data Completeness**: Percentage of fields present
- **Clinical Consistency**: No symptom-vital discordance
- **Pattern Recognition**: Similarity to training data
- **Overall Confidence**: Weighted average (HIGH/MEDIUM/LOW)
- **Warnings**: Displayed for LOW or MEDIUM confidence on ESI ≥ 3

#### SHAP Explanation
- Natural language description of prediction reasoning
- Bar chart showing top 3-5 contributing factors
- Feature values and their impact on urgency

### Step 5: Override (Optional)

If you disagree with the ML recommendation:

1. Click **"Override Recommendation"** button
2. Select your clinician ESI assessment (1-5)
3. Choose override reason category:
   - Clinical Judgment
   - Additional Information
   - Safety Concern
   - ML Error
4. Provide text justification (minimum 20 characters)
5. Submit override - logged for model improvement

---

## 🔧 Testing the System

### Run ML Core Validation Tests

```bash
python test_ml_core.py
```

This validates:
- ✓ Server health and API availability
- ✓ Diverse patient scenarios (7 test cases)
- ✓ Preprocessing pipeline with age-specific features
- ✓ Multi-dimensional confidence scoring
- ✓ Safety validation rules (RED/YELLOW/GREEN)

Expected: **All tests pass** with detailed output

### Run Frontend Integration Tests

```bash
python test_frontend_integration.py
```

This validates:
- ✓ HTML structure and form fields
- ✓ JavaScript functions present
- ✓ API endpoints referenced correctly
- ✓ Response field handling
- ✓ Chart.js visualization library
- ✓ Result display elements
- ✓ Event listeners
- ✓ Error handling
- ✓ Form data collection (100%)

Expected: **9/9 tests pass**

### Run Visual Alerts Tests

```bash
python test_visual_alerts.py
```

This validates:
- ✓ ESI 1 pulsing red border animation
- ✓ RED safety flag prominent banner
- ✓ LOW confidence warnings
- ✓ MEDIUM confidence warnings
- ✓ Enhanced visual styling

Expected: **13/13 tests pass**

### Run Simple End-to-End Test

```bash
python test_e2e_simple.py
```

This validates a complete prediction flow via API call.

---

## 🎨 Key Features

### 1. ML-Powered ESI Classification

- **CatBoost classifier** trained on synthetic ED data
- **5-class prediction**: ESI 1 (most urgent) to ESI 5 (least urgent)
- **Class weights**: 10:5:2:1:1 to penalize under-triage
- **Categorical encoding**: Handles chief complaint categories natively
- **Age-stratified**: Considers pediatric, adult, geriatric differences

### 2. Multi-Dimensional Confidence Scoring

Four independent confidence dimensions:

#### Model Certainty (40% weight)
- Computed from probability distribution entropy
- High certainty: peaked distribution (e.g., 90% ESI 3)
- Low certainty: uniform distribution (e.g., 20% each ESI)

#### Data Completeness (25% weight)
- Percentage of expected fields present
- Penalties for missing temperature, pain score, medical history
- Target: ≥90% completeness for high confidence

#### Clinical Consistency (20% weight)
- Detects symptom-vital discordance
- Pain underreporting: Low pain + high HR
- Severity underreporting: Minor complaint + multiple abnormal vitals
- Respiratory underreporting: Low SpO2 + no respiratory symptoms

#### Pattern Recognition (15% weight)
- Uses Isolation Forest for out-of-distribution detection
- Low score: unusual vital combinations or rare presentations
- High score: typical patterns seen in training data

**Overall Confidence**: Weighted average → HIGH (≥80%), MEDIUM (60-80%), LOW (<60%)

### 3. Safety Validation Layer

Rule-based checks override unsafe ML predictions:

#### RED Flags (Force Escalation)
- Age < 1 year (infants automatically escalated)
- SpO2 < 90% (severe hypoxia)
- Chest pain + age > 45 (cardiac risk)
- Severe trauma indicators
- Altered mental status
- Active bleeding with hypotension

#### YELLOW Flags (Recommend Validation)
- LOW confidence on any prediction
- MEDIUM confidence on non-urgent (ESI ≥ 3)
- Data completeness < 70%
- Out-of-distribution patient (OOD detection)

#### GREEN Flag
- No safety concerns
- HIGH confidence
- Good data quality
- Typical presentation

### 4. SHAP Explainability

- **TreeExplainer** for CatBoost model
- **Top 3-5 features** shown with SHAP values
- **Natural language** explanations:
  - "Chief complaint 'Chest Pain Cardiac' increases urgency by 50%"
  - "Systolic BP 145 mmHg (abnormal) increases urgency by 38%"
  - "Arrival by ambulance indicates pre-hospital urgency assessment"
- **Visual bar chart** of feature contributions

### 5. Age-Specific Vital Processing

Different normal ranges by age group:

- **Pediatric Infant (0-2 years)**: HR 100-180, RR 30-60
- **Pediatric Child (3-12 years)**: HR 70-120, RR 20-30
- **Pediatric Adolescent (13-17 years)**: HR 60-100, RR 12-20
- **Adult (18-64 years)**: HR 60-100, RR 12-20
- **Geriatric (65+ years)**: HR 60-100, RR 12-20 (with fall risk considerations)

### 6. Interactive Web Interface

- **Single-page application**: No page reloads
- **Responsive design**: Works on desktop and tablet
- **Real-time validation**: Client-side field checks
- **Data completeness indicator**: Live percentage updates
- **Chart.js visualizations**: Probability and SHAP charts
- **Demo patient quick-load**: 20 pre-generated scenarios
- **Override dialog modal**: Capture clinician disagreements

### 7. Visual Alerts for High-Risk Cases

- **ESI 1**: Pulsing red border animation on entire panel
- **RED safety flag**: Critical alert banner with animation
- **LOW confidence**: Red-bordered warning message
- **MEDIUM confidence (ESI ≥3)**: Yellow-bordered validation recommendation
- **Color coding**: Consistent ESI colors throughout UI

---

## 📊 Data & Models

### Training Data

- **500 synthetic ED patient records**
- **Age distribution**: Balanced across pediatric, adult, geriatric
- **ESI distribution**: Stratified by urgency level
- **Chief complaints**: 50+ categories (cardiac, respiratory, trauma, GI, neuro, etc.)
- **Vitals**: Realistic ranges with age-specific variations
- **Missing data**: Simulated incomplete records (10-30% missingness)

**Location**: `data/training_patients.json`

### Test Patients

- **20 diverse test cases** for demonstration
- **Special scenarios**: Ambiguous, pediatric, geriatric, zero-history
- **Edge cases**: Extreme vitals, unusual presentations
- **All ESI levels represented** (1-5)

**Location**: `data/test_patients.json`

### Models

- **ESI Classifier**: CatBoost (`models/esi_classifier.cbm` - if saved)
- **Isolation Forest**: Scikit-learn (for OOD detection)
- **SHAP Explainer**: Cached in-memory per model version

**Note**: Current prototype uses heuristic-based fallback if trained model is unavailable. Training script would be: `src/data_generation.py` → `src/models.py`

---

## 🏗️ Architecture

### Backend (FastAPI)

**File**: `app.py`

**Key Endpoints**:
- `POST /api/v1/predict`: Main ESI prediction endpoint
- `GET /api/v1/patients`: Fetch test patient data
- `POST /api/v1/override`: Log clinician overrides
- `GET /docs`: Interactive API documentation

**Components**:
- `src/preprocessing.py`: Feature engineering, age groups, vital deviations
- `src/confidence.py`: Multi-dimensional confidence scoring
- `src/safety_validation.py`: Rule-based safety checks
- `src/explainer.py`: SHAP value computation and formatting
- `src/models.py`: Model loading and inference

### Frontend (Vanilla JavaScript + HTML/CSS)

**File**: `frontend/index.html` (single file, ~2000 lines)

**Sections**:
- Patient intake form (left sidebar)
- ML recommendation display (right panel)
- Demo patient selector (top bar)
- Override dialog modal

**Dependencies**:
- Chart.js (via CDN) for visualizations

### Data Storage

- **Test patients**: `data/test_patients.json`
- **Override logs**: `data/overrides.json` (JSON file, appended)

**Note**: Prototype uses JSON files for simplicity. Production would use PostgreSQL.

---

## 📝 API Examples

### Predict ESI Level

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age": 45,
    "sex": "M",
    "hr": 105,
    "bp_systolic": 145,
    "bp_diastolic": 90,
    "spo2": 97,
    "rr": 18,
    "temperature": 37.2,
    "chief_complaint": "Chest pain",
    "chief_complaint_category": "chest_pain_cardiac",
    "arrival_mode": "ambulance",
    "mental_status": "alert",
    "pain_score": 6,
    "symptoms": [],
    "medical_history": {}
  }'
```

**Response**:
```json
{
  "esi_prediction": 3,
  "probability_distribution": [0.036, 0.071, 0.500, 0.286, 0.107],
  "confidence_breakdown": {
    "model_certainty": 22.25,
    "data_completeness": 87.5,
    "clinical_consistency": 100.0,
    "pattern_recognition": 100.0,
    "overall": 77.44,
    "level": "MEDIUM"
  },
  "safety_flag": {
    "outcome": "YELLOW",
    "triggered_criteria": ["Chest pain in patient >45 years (cardiac risk)"],
    "recommended_action": "Recommend clinical validation",
    "override_esi": null
  },
  "explanation": {
    "text": "The model predicts ESI 3 based primarily on...",
    "top_factors": [
      {
        "feature": "chief_complaint_category",
        "shap_value": 0.5,
        "direction": "increases urgency",
        "severity": "critical",
        "feature_value": "chest_pain_cardiac"
      }
    ]
  },
  "model_version": "v1.0.0-heuristic-fallback",
  "inference_time_ms": 7.28
}
```

### Get Test Patients

```bash
curl http://localhost:8000/api/v1/patients
```

### Submit Override

```bash
curl -X POST http://localhost:8000/api/v1/override \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "demo_001",
    "ml_predicted_esi": 3,
    "ml_confidence": 77.4,
    "clinician_final_esi": 2,
    "reason_category": "clinical_judgment",
    "reason_text": "Patient appears more distressed than vitals suggest"
  }'
```

---

## ⚠️ Limitations & Disclaimers

### This is a Prototype

- **Synthetic training data**: Not real patient data
- **Simplified models**: Not validated on real ED outcomes
- **No clinical validation**: Not tested with actual clinicians
- **No FDA clearance**: Not a medical device
- **No HIPAA compliance**: Not configured for PHI protection
- **No authentication**: Open API, no access controls

### For Demonstration Purposes Only

This prototype demonstrates:
✓ ML classification with explainability
✓ Confidence scoring and uncertainty quantification
✓ Safety validation and override mechanisms
✓ Interactive clinical interface design

It does NOT:
✗ Provide actual medical advice
✗ Replace clinical judgment
✗ Meet regulatory requirements
✗ Handle real patient data securely
✗ Scale to production workloads

### Clinical Decision Support Intent

If this were production:
- Clinician retains full decision authority
- AI provides supplementary information only
- System must comply with 21st Century Cures Act CDS exemption criteria
- Comprehensive incident reporting required
- Regular bias audits and performance monitoring needed

---

## 🛠️ Troubleshooting

### Backend won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Frontend shows "Failed to fetch"

**Error**: Network error when submitting form

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/docs`
2. Check console for CORS errors (should not occur with local file)
3. Ensure port 8000 is not blocked by firewall

### Charts not displaying

**Error**: Blank spaces where charts should be

**Solutions**:
1. Check browser console for JavaScript errors
2. Verify Chart.js loaded (look for `<script src="https://cdn.jsdelivr.net/npm/chart.js...">`)
3. Try a different browser (Chrome recommended)

### Demo patients not loading

**Error**: Dropdown shows "Error loading patients"

**Solutions**:
1. Verify `data/test_patients.json` exists
2. Check backend logs for file read errors
3. Ensure backend restarted after any data file changes

---

## 📚 Further Development

This prototype could be extended with:

### Technical Enhancements
- [ ] Train on real de-identified ED data
- [ ] Implement deterioration detection (XGBoost temporal model)
- [ ] Add surge mode sub-prioritization engine
- [ ] Set up PostgreSQL database with audit logging
- [ ] Implement Redis caching for lookup tables
- [ ] Add MLflow model registry and versioning
- [ ] Create shadow mode for A/B testing

### Safety & Validation
- [ ] Clinical vignette testing with EM physicians
- [ ] Bias audit across demographics
- [ ] Prospective validation study in ED
- [ ] Adverse event monitoring
- [ ] Performance drift detection
- [ ] Regular retraining pipeline

### Production Readiness
- [ ] Authentication and authorization (RBAC)
- [ ] HIPAA compliance (encryption, audit logs, BAAs)
- [ ] Blue-green deployment with rollback
- [ ] Monitoring and alerting (Prometheus + Grafana)
- [ ] Load testing and auto-scaling
- [ ] Comprehensive unit and integration tests
- [ ] Clinical user training and documentation

---

## 📄 License

MIT License - See LICENSE file for details.

This is educational/demonstration software. Not intended for clinical use.

---

## 🙏 Acknowledgments

- **Emergency Severity Index (ESI)**: AHRQ-funded triage algorithm
- **CatBoost**: Yandex open-source gradient boosting library
- **SHAP**: Lundberg & Lee's explainable AI framework
- **FastAPI**: Modern Python web framework
- **Chart.js**: Open-source charting library

---

## 📧 Contact

For questions about this prototype implementation:
- Review the code comments in `app.py` and `frontend/index.html`
- Check test scripts for usage examples
- Refer to API documentation at `/docs` endpoint

**Remember**: This is a technical demonstration, not clinical software.

---

## 🚦 Quick Reference

| Command | Purpose |
|---------|---------|
| `uvicorn app:app --reload` | Start backend server |
| `open frontend/index.html` | Open frontend |
| `python test_ml_core.py` | Test ML components |
| `python test_frontend_integration.py` | Test frontend |
| `python test_visual_alerts.py` | Test visual alerts |
| `curl http://localhost:8000/docs` | View API docs |

**Backend**: http://localhost:8000
**Frontend**: file:///path/to/Win/frontend/index.html
**API Docs**: http://localhost:8000/docs

---

**Built with ❤️ for demonstrating ML in healthcare**
