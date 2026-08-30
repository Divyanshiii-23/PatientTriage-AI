# Implementation Plan: Clinical Interface Workflow (1-Day Prototype)

## Overview

This is a **simplified 1-day prototype** focused on demonstrating the ML Core Engine with a minimal clinical interface. The goal is to showcase ESI classification with real ML models, SHAP explanations, confidence scoring, and safety validation through a simple but functional web interface.

**Key Simplifications:**
- Single Python file backend (FastAPI)
- Single HTML file frontend (vanilla JavaScript + Chart.js)
- JSON file storage (no database)
- Pre-generated patient data (20 diverse cases)
- Lightweight ML models (simplified training for demo)
- Focus on core demo flow: input → prediction → visualization

**Time Budget:** ~8 hours implementation, ~2 hours testing and polish

## Tasks

- [x] 1. Generate synthetic training dataset and test patients
  - Create Python script to generate 500 synthetic ED patient records with demographics, vitals, symptoms, ESI labels (stratified by age groups)
  - Generate 20 diverse test patients including: 2 pediatric, 2 geriatric, 1 ambiguous chest pain, 1 zero-history, distribution across all ESI levels
  - Include realistic chief complaints from 50+ categories (chest pain, abdominal pain, fever, trauma, respiratory distress, etc.)
  - Save as `data/training_patients.json` and `data/test_patients.json`
  - _Requirements: 1.1-1.10_

- [x] 2. Build simplified ML Core Engine
  - [x] 2.1 Implement preprocessing pipeline with age-specific vital deviation calculation
    - Create age group classifier (infant 0-2, child 3-12, adolescent 13-17, adult 18-64, geriatric 65+)
    - Implement vital deviation features using age-specific normal ranges
    - Handle missing data with indicator features
    - Compute data completeness score (0-100%)
    - _Requirements: 2.2, 2.3, 11.3_

  - [x] 2.2 Train CatBoost ESI classifier on synthetic data
    - Train 5-class CatBoost model (ESI 1-5) with class weights (10:5:2:1:1) to penalize under-triage
    - Use categorical encoding for chief complaints
    - Train on 80% data, validate on 20%
    - Target simple model: max 100 trees, depth 4 for fast inference
    - Save model as `models/esi_classifier.cbm`
    - _Requirements: Referenced from ML Core spec_

  - [x] 2.3 Implement SHAP explainer for feature contributions
    - Load trained model and create TreeExplainer
    - Generate SHAP values for top 5 contributing features
    - Format explanations as natural language (e.g., "High heart rate increases urgency by 15%")
    - _Requirements: 3.8, 3.9_

  - [x] 2.4 Build multi-dimensional confidence scoring system
    - Implement 4 confidence dimensions: model certainty (from probabilities), data completeness (% fields present), clinical consistency (symptom-vital alignment), pattern recognition (distance from training distribution)
    - Aggregate to overall confidence: HIGH (>80%), MEDIUM (60-80%), LOW (<60%)
    - Return confidence breakdown as 4 separate scores 0-100
    - _Requirements: 3.3, 3.4, 8.1-8.9_

  - [x] 2.5 Implement safety validation layer with rule-based checks
    - Create safety validator checking: age <1 year → RED flag ESI 2, SpO2 <90% → RED flag ESI 1, chest pain + age >45 → YELLOW flag, severe trauma → RED flag ESI 1
    - Return safety flag (RED/YELLOW/GREEN) with triggered criteria list
    - Override ML prediction if RED flag (force escalation to ESI 1 or 2)
    - _Requirements: 3.5, 3.6, 3.7, 13.1-13.3_

- [ ] 3. Checkpoint - Test ML Core with sample patients
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Build FastAPI backend with essential endpoints
  - [x] 4.1 Create single `app.py` with FastAPI application and Pydantic models
    - Define PatientData model with demographics, vitals, clinical data (chief complaint, pain score, medical history)
    - Define PredictionResponse model with esi_prediction, probability_distribution (dict of ESI 1-5 to probabilities), confidence_breakdown (4 dimensions), safety_flag, explanation (natural language), shap_values (top 5 features with contributions)
    - Initialize FastAPI app with CORS middleware for local development
    - _Requirements: 21.1, 21.2_

  - [x] 4.2 Implement POST /api/v1/predict endpoint
    - Load patient data from request, run preprocessing pipeline
    - Generate ESI prediction with ML model
    - Compute SHAP explanations
    - Calculate confidence scores
    - Run safety validation
    - Return PredictionResponse JSON
    - Target latency: <500ms for demo
    - _Requirements: 3.1-3.12_

  - [x] 4.3 Implement GET /api/v1/patients endpoint to serve test patients
    - Load 20 pre-generated test patients from `data/test_patients.json`
    - Return as JSON array with patient_id, name, age, demographics
    - Enable quick-load for demo scenarios
    - _Requirements: 20.6, 20.7_

  - [x] 4.4 Implement POST /api/v1/override endpoint to log clinician overrides
    - Accept override data: patient_id, ml_predicted_esi, clinician_final_esi, reason_category, reason_text, timestamp
    - Append to `data/overrides.json` file
    - Calculate override direction (escalation vs de-escalation)
    - _Requirements: 4.7, 4.8_

- [x] 5. Build single-page web interface
  - [x] 5.1 Create `frontend/index.html` with three main sections: patient intake form, ML recommendation panel, demo patient selector
    - Use modern CSS with flexbox layout: left sidebar (intake form), right panel (results), top bar (demo selector)
    - Include Chart.js library via CDN for probability distributions and SHAP visualizations
    - Add basic styling with ESI color coding (ESI 1 red, 2 orange, 3 yellow, 4 green, 5 blue)
    - _Requirements: 2.1, 3.1, 18.1-18.3_

  - [x] 5.2 Implement patient intake form with validation
    - Add input fields: age (0-120), sex, HR (20-250), BP systolic/diastolic, SpO2 (50-100%), RR, temperature (optional), pain score (0-10, optional)
    - Add chief complaint dropdown with 20+ common categories (chest pain, abdominal pain, fever, trauma, shortness of breath, etc.)
    - Add medical history textarea (optional)
    - Display real-time data completeness percentage
    - Validate required fields and age-appropriate vital ranges client-side
    - _Requirements: 2.1-2.10_

  - [x] 5.3 Implement ML recommendation panel with visualizations
    - Display predicted ESI level prominently with color-coded badge
    - Show probability distribution as horizontal bar chart (Chart.js) for all 5 ESI levels
    - Display overall confidence level (HIGH/MEDIUM/LOW) with icon and color
    - Show confidence breakdown as 4 progress bars: model certainty, data completeness, clinical consistency, pattern recognition
    - Display safety flag with prominent banner (RED/YELLOW/GREEN)
    - Show SHAP explanation in natural language with feature contribution chart
    - _Requirements: 3.1-3.12_

  - [x] 5.4 Add override dialog modal
    - Create modal overlay triggered by "Override Recommendation" button
    - Show side-by-side comparison: ML predicted ESI vs clinician selected ESI (radio buttons 1-5)
    - Add reason category dropdown (clinical judgment, additional information, safety concern, ML error)
    - Add free-text justification field (minimum 20 characters)
    - Display override direction (escalation/de-escalation) with color coding
    - On submit, POST to /api/v1/override endpoint and display confirmation
    - _Requirements: 4.1-4.10_

  - [x] 5.5 Implement demo patient quick-load functionality
    - Add dropdown at top of page listing 20 pre-generated patients by scenario (e.g., "Ambiguous Chest Pain - 45yo Male", "Pediatric Fever - 2yo")
    - On selection, fetch patient data from GET /api/v1/patients and auto-populate intake form
    - Highlight special cases with labels: AMBIGUOUS, PEDIATRIC, GERIATRIC, ZERO-HISTORY
    - _Requirements: 20.1-20.10_

- [ ] 6. Integrate frontend with backend API
  - [-] 6.1 Implement JavaScript fetch calls to backend
    - Create submitPatientData() function to POST to /api/v1/predict
    - Create loadTestPatients() function to GET from /api/v1/patients
    - Create submitOverride() function to POST to /api/v1/override
    - Add error handling with user-friendly messages
    - Show loading spinners during API calls
    - _Requirements: 21.1-21.5_

  - [-] 6.2 Wire up form submission to display prediction results
    - On form submit, call submitPatientData()
    - Parse PredictionResponse JSON
    - Update recommendation panel with all results: ESI, probabilities, confidence, safety flag, explanations
    - Render Chart.js visualizations for probability distribution and SHAP values
    - Enable override button after prediction displayed
    - _Requirements: 2.10, 3.1-3.12_

- [ ] 7. Add demonstration features and polish
  - [-] 7.1 Add visual alerts for high-risk cases
    - If predicted ESI is 1, show pulsing red border animation on recommendation panel
    - If safety flag is RED, display prominent alert banner with triggered criteria
    - If confidence is LOW and ESI ≥3, show warning suggesting clinician review
    - Add color-coded confidence indicators (green HIGH, yellow MEDIUM, red LOW)
    - _Requirements: 13.1-13.5, 8.1_

  - [x] 7.2 Add age-specific patient badges and helper text
    - Display "PEDIATRIC PATIENT" badge for age <18 with blue background
    - Display "GERIATRIC PATIENT" badge for age ≥65 with purple background
    - Show age-appropriate vital sign normal ranges as helper text below input fields
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 7.3 Create simple README with setup and demo instructions
    - Document setup: install requirements (fastapi, uvicorn, catboost, shap, numpy, pandas)
    - Document how to run: generate data, train model, start server, open browser
    - Include demo walkthrough: try ambiguous case, try override, observe confidence scores
    - List key features demonstrated: ML classification, SHAP explanations, safety validation, age-specific handling
    - _Requirements: Documentation for submission_

- [ ] 8. Final testing and demo preparation
  - [ ] 8.1 Test end-to-end flow with all 20 test patients
    - Load each test patient and verify prediction completes successfully
    - Check that ambiguous case shows MEDIUM confidence
    - Verify pediatric and geriatric patients trigger age-specific features
    - Confirm safety flags trigger appropriately (infant → RED, low SpO2 → RED)
    - _Requirements: 10.1-10.8, 11.6, 11.7_

  - [ ] 8.2 Verify override logging and test error handling
    - Submit override for at least 2 patients and verify saved to overrides.json
    - Test with missing optional fields (temperature, pain score) and verify data completeness penalty
    - Test with invalid inputs and verify validation messages
    - Simulate API error and verify fail-safe message displays
    - _Requirements: 4.7-4.9, 9.1-9.5_

- [ ] 9. Checkpoint - Final validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This is a **prototype for demonstration purposes**, not production-ready
- No database, authentication, or real-time monitoring (scope reduced for 1-day timeline)
- ML models are trained on synthetic data for proof-of-concept
- Focus is on showcasing ML Core capabilities: ESI classification, explainability, confidence scoring, safety validation
- Frontend is intentionally simple (single HTML file) to maximize time on ML Core
- All patient data is fictional and generated programmatically
- Override logging writes to JSON file for simplicity
- Tasks marked with `*` would be optional in normal workflow, but all tasks here are essential for minimum viable demo

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "5.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "4.2", "4.3", "5.2"] },
    { "id": 4, "tasks": ["4.4", "5.3", "5.4", "5.5"] },
    { "id": 5, "tasks": ["6.1", "6.2", "7.1", "7.2"] },
    { "id": 6, "tasks": ["7.3", "8.1", "8.2"] }
  ]
}
```
