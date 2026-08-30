# Requirements Document

## Introduction

The PatientTriage.ai Clinical Interface & Workflow is a web-based prototype application that demonstrates the ML Core Engine in realistic Emergency Department triage scenarios. This interface serves as an Accenture Innovation Challenge 2026 Round 2 submission, showcasing how AI-powered triage assistance integrates into clinical workflows while maintaining clinician authority, safety, and accountability.

The interface addresses critical ED challenges including specialist shortage (158 EM specialists for 119.1M visits annually), high mistriage rates (32.2% including 3.3% dangerous under-triage), and overcrowding mortality (5.4% increase at peak). It provides nurses and clinicians with real-time ESI recommendations, continuous deterioration monitoring, and surge mode prioritization while surfacing uncertainty explicitly and capturing override patterns for continuous improvement.

This specification covers ONLY the clinical interface and workflow prototype. The underlying ML Core Engine (ESI classification, deterioration detection, explainability, safety validation) is defined in a separate specification.

## Glossary

- **Clinical_Interface**: The web-based application used by nurses and clinicians for patient triage and monitoring
- **Triage_Workflow**: The sequence of steps from patient arrival through ESI assignment and queue placement
- **Patient_Intake_Form**: The digital form capturing demographics, vitals, symptoms, and history
- **Recommendation_Panel**: The UI component displaying ML Core predictions, confidence, explanation, and safety alerts
- **Override_Dialog**: The modal interface for clinicians to override AI recommendations with justification
- **Waiting_Queue_Dashboard**: The real-time display of all waiting patients with deterioration indicators and re-assessment timers
- **Simulated_Patient_Generator**: The system that creates 15-20 diverse test cases for prototype demonstration
- **Session**: A clinician's authenticated login period with all actions audited
- **Surge_Mode**: System state activated when waiting patients exceed threshold, triggering sub-prioritization
- **Deterioration_Alert**: Visual and audible notification when waiting patient's vitals worsen
- **Re_Assessment_Trigger**: Automated prompt for nurses to re-check patient vitals based on ESI and wait time
- **Confidence_Indicator**: Visual representation of multi-dimensional confidence (model certainty, data completeness, clinical consistency, pattern recognition)
- **Safety_Flag**: Color-coded alert (RED/YELLOW/GREEN) from ML Core safety validation
- **SHAP_Visualization**: Graphical display of feature contributions to ESI prediction
- **Audit_Trail**: Immutable log of all triage decisions, overrides, and system actions
- **Zero_History_Patient**: Patient with no prior ED visits in system database
- **Ambiguous_Presentation**: Clinical scenario where ESI could reasonably be 2 or 3 (e.g., chest pain in 40-year-old)
- **Age_Appropriate_Validation**: Input validation rules that adjust vital sign ranges based on patient age group
- **Fail_Safe_Default**: System behavior when ML Core unavailable (escalate to ESI 2, flag for manual assessment)
- **Chief_Complaint_Selector**: Structured input for primary symptom with 50+ standardized categories
- **Vital_Signs_Panel**: Form section capturing HR, BP, SpO2, RR, temperature with real-time validation
- **Patient_Card**: Summary tile in queue dashboard showing photo placeholder, name, ESI, wait time, and status
- **ED_Nurse**: Primary user role responsible for initial patient intake and triage
- **Attending_Physician**: Secondary user role with override authority and dashboard monitoring access
- **Prototype_Session**: Demonstration mode with 15-20 pre-loaded simulated patients
- **Real_Time_Update**: WebSocket-driven UI refresh showing deterioration alerts and queue changes
- **HIPAA_Mode**: Compliance setting that redacts identifiable information in audit logs and screenshots

## Requirements

### Requirement 1: Simulated Patient Data Generation

**User Story:** As a demonstration evaluator, I want the prototype to include 15-20 diverse, realistic patient scenarios, so that I can assess system behavior across edge cases and typical ED presentations.

#### Acceptance Criteria

1. THE Simulated_Patient_Generator SHALL create exactly 20 patient records with demographics, vitals, symptoms, chief complaints, and medical history

2. THE Simulated_Patient_Generator SHALL include at least 1 ambiguous presentation where ESI could reasonably be level 2 or level 3

3. THE Simulated_Patient_Generator SHALL include at least 2 pediatric patients (age less than 18) spanning different age groups (infant 0-2, child 3-12, adolescent 13-17)

4. THE Simulated_Patient_Generator SHALL include at least 2 geriatric patients (age 65 or greater) with comorbidities

5. THE Simulated_Patient_Generator SHALL include at least 1 zero-history patient with no prior ED visits and minimal medical history

6. THE Simulated_Patient_Generator SHALL distribute patients across all ESI levels (minimum 2 patients each for ESI 1, 2, 3, 4, 5)

7. THE Simulated_Patient_Generator SHALL include at least 3 patients with missing optional data (temperature, pain score, or medical history) to test confidence penalization

8. THE Simulated_Patient_Generator SHALL assign realistic chief complaints from 50+ standardized categories (chest pain cardiac, abdominal pain, fever, trauma, respiratory distress, etc.)

9. THE Simulated_Patient_Generator SHALL generate age-appropriate vital signs using ML Core age-specific normal ranges

10. FOR ALL generated patients, THE Simulated_Patient_Generator SHALL create unique patient identifiers, arrival timestamps, and photo placeholders

### Requirement 2: Patient Intake Workflow

**User Story:** As an ED nurse, I want a streamlined digital intake form that guides me through capturing patient information, so that I can efficiently triage patients while ensuring data completeness.

#### Acceptance Criteria

1. WHEN a new patient arrives, THE Clinical_Interface SHALL display Patient_Intake_Form with sections for demographics, vitals, chief complaint, symptoms, history, and observations

2. THE Patient_Intake_Form SHALL validate age input (0-120 years) and automatically classify patient into age group (pediatric infant, pediatric child, pediatric adolescent, adult, geriatric)

3. THE Patient_Intake_Form SHALL apply age-appropriate vital sign validation ranges based on classified age group (infant HR 100-160 valid, adult HR 100-160 flagged)

4. THE Patient_Intake_Form SHALL mark vital signs (HR, BP systolic, BP diastolic, SpO2, RR) as required and chief complaint as required

5. THE Patient_Intake_Form SHALL mark temperature, pain score, medical history, and detailed symptoms as optional

6. THE Patient_Intake_Form SHALL provide Chief_Complaint_Selector with autocomplete search across 50+ standardized categories

7. THE Patient_Intake_Form SHALL display data completeness percentage updating in real-time as fields are filled (0-100%)

8. THE Patient_Intake_Form SHALL prevent form submission if required fields are missing

9. WHEN Patient_Intake_Form is submitted, THE Clinical_Interface SHALL call ML Core ESI prediction API with collected data

10. WHEN Patient_Intake_Form is submitted, THE Clinical_Interface SHALL transition to Recommendation_Panel showing ML prediction results

### Requirement 3: Real-Time Triage Recommendation Display

**User Story:** As an ED nurse, I want to see the AI triage recommendation with confidence levels and contributing factors, so that I can make an informed ESI decision incorporating both ML insights and my clinical judgment.

#### Acceptance Criteria

1. WHEN ML Core returns prediction, THE Recommendation_Panel SHALL display predicted ESI level (1-5) prominently with color coding (ESI 1 red, ESI 2 orange, ESI 3 yellow, ESI 4 green, ESI 5 blue)

2. THE Recommendation_Panel SHALL display probability distribution as horizontal bar chart showing likelihood for each ESI level (5 bars summing to 100%)

3. THE Recommendation_Panel SHALL display overall confidence level (HIGH/MEDIUM/LOW) with icon (checkmark HIGH, warning MEDIUM, alert LOW)

4. THE Recommendation_Panel SHALL display confidence breakdown showing 4 dimension scores (model certainty, data completeness, clinical consistency, pattern recognition) as 0-100 values with progress bars

5. THE Recommendation_Panel SHALL display Safety_Flag outcome (RED/YELLOW/GREEN) with prominent visual indicator (red banner RED, yellow border YELLOW, green checkmark GREEN)

6. WHEN Safety_Flag is RED, THE Recommendation_Panel SHALL display triggered safety criteria list and override recommendation (force ESI 1 or 2)

7. WHEN Safety_Flag is YELLOW, THE Recommendation_Panel SHALL display caution message and escalation recommendation

8. THE Recommendation_Panel SHALL display SHAP explanation text in natural language showing top 3-5 contributing factors

9. THE Recommendation_Panel SHALL display SHAP_Visualization as horizontal bar chart showing feature contributions (positive contributions push toward higher urgency, negative toward lower urgency)

10. THE Recommendation_Panel SHALL display recommendations list from ML Core (e.g., "Obtain additional patient history", "Monitor O2 saturation closely", "Consider cardiac workup")

11. THE Recommendation_Panel SHALL provide Accept button to confirm ML recommendation and proceed to queue

12. THE Recommendation_Panel SHALL provide Override button to open Override_Dialog for clinician to assign different ESI

### Requirement 4: Clinician Override Mechanism

**User Story:** As a clinician, I want to override AI recommendations when my clinical judgment differs, while documenting my reasoning, so that the system learns from my expertise and maintains accountability.

#### Acceptance Criteria

1. WHEN clinician clicks Override button, THE Clinical_Interface SHALL open Override_Dialog modal displaying ML predicted ESI and confidence breakdown

2. THE Override_Dialog SHALL provide ESI level selector (radio buttons 1-5) for clinician final decision

3. THE Override_Dialog SHALL provide override reason category dropdown with options (clinical judgment, additional information, safety concern, ML error, patient preference, resource constraint)

4. THE Override_Dialog SHALL provide free-text field for detailed override justification (minimum 20 characters required)

5. THE Override_Dialog SHALL display side-by-side comparison of ML predicted ESI vs clinician selected ESI with difference highlighted

6. THE Override_Dialog SHALL calculate and display override direction (escalation if clinician ESI less than ML ESI, de-escalation if greater)

7. WHEN Override_Dialog is submitted, THE Clinical_Interface SHALL call ML Core override logging API with ML prediction, clinician decision, reason category, reason text, and timestamp

8. WHEN Override_Dialog is submitted, THE Clinical_Interface SHALL write audit entry to database with all override details

9. THE Clinical_Interface SHALL accept clinician ESI as final decision regardless of ML recommendation (100% override capability)

10. WHEN override is escalation (clinician ESI less than ML ESI), THE Clinical_Interface SHALL show confirmation dialog highlighting increased resource allocation

### Requirement 5: Waiting Queue Dashboard

**User Story:** As an ED nurse, I want a real-time dashboard showing all waiting patients with deterioration indicators and priority order, so that I can monitor patient status and intervene when conditions worsen.

#### Acceptance Criteria

1. THE Waiting_Queue_Dashboard SHALL display all triaged patients not yet assigned to treatment rooms as Patient_Card tiles

2. EACH Patient_Card SHALL display patient photo placeholder, patient name, patient age, assigned ESI level, current wait time in minutes, and status indicator (stable, deteriorating, re-assessment due)

3. THE Waiting_Queue_Dashboard SHALL sort Patient_Cards by priority: primary sort by ESI level (1 highest), secondary sort by sub-score if surge mode active (100 highest), tertiary sort by arrival time (earliest first)

4. WHEN surge mode is active (waiting patients greater than threshold 15), THE Waiting_Queue_Dashboard SHALL display "SURGE MODE ACTIVE" banner and show sub-scores on Patient_Cards

5. THE Waiting_Queue_Dashboard SHALL update in real-time using WebSocket connection receiving deterioration alerts and status changes

6. WHEN patient deterioration detected, THE Waiting_Queue_Dashboard SHALL change Patient_Card border to red, display "DETERIORATING" badge, and play audible alert tone

7. WHEN patient due for re-assessment (ESI 2 after 15 min, ESI 3 after 30 min, ESI 4/5 after 60 min), THE Waiting_Queue_Dashboard SHALL change Patient_Card border to orange and display "RE-ASSESSMENT DUE" badge

8. THE Waiting_Queue_Dashboard SHALL display summary statistics: total waiting patients, average wait time, patients by ESI level, surge mode status

9. WHEN clinician clicks Patient_Card, THE Clinical_Interface SHALL open patient detail modal showing full history, vitals timeline, and option to trigger manual re-assessment

10. THE Waiting_Queue_Dashboard SHALL provide Refresh All button to manually trigger deterioration checks for all waiting patients

### Requirement 6: Automatic Deterioration Monitoring

**User Story:** As an ED nurse, I want the system to automatically monitor waiting patients and alert me when vitals worsen, so that I can intervene before patients decompensate.

#### Acceptance Criteria

1. WHILE patient has ESI level 2 and remains in waiting queue, THE Clinical_Interface SHALL trigger re-assessment prompt every 15 minutes

2. WHILE patient has ESI level 3 and remains in waiting queue, THE Clinical_Interface SHALL trigger re-assessment prompt every 30 minutes

3. WHILE patient has ESI level 4 or 5 and remains in waiting queue, THE Clinical_Interface SHALL trigger re-assessment prompt every 60 minutes

4. WHEN re-assessment prompt triggered, THE Clinical_Interface SHALL display modal with patient name, last vitals, and form to enter current vitals

5. WHEN nurse submits updated vitals, THE Clinical_Interface SHALL call ML Core deterioration detection API with initial vitals, current vitals, time elapsed, and patient age group

6. WHEN ML Core returns deterioration assessment, THE Clinical_Interface SHALL display deterioration status (STABLE/DETERIORATING/UNCERTAIN), score (0-100), vital changes list, and explanation

7. IF deterioration status is DETERIORATING or score greater than or equal to 60, THEN THE Clinical_Interface SHALL display Deterioration_Alert with recommendation to escalate ESI or expedite treatment

8. IF deterioration status is DETERIORATING, THEN THE Clinical_Interface SHALL update Patient_Card status indicator to deteriorating and trigger audible alert

9. IF ESI 2 patient wait time exceeds 30 minutes, THEN THE Clinical_Interface SHALL generate automatic alert regardless of vitals (safety time threshold)

10. IF ESI 3 patient wait time exceeds 60 minutes, THEN THE Clinical_Interface SHALL generate automatic alert regardless of vitals (safety time threshold)

11. THE Clinical_Interface SHALL log all re-assessment events and deterioration assessments to audit trail

### Requirement 7: Surge Mode Demonstration

**User Story:** As a demonstration evaluator, I want to simulate surge conditions with 3× normal patient volume, so that I can observe sub-prioritization and queue management under overcrowding.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL provide Simulate Surge button in prototype mode to load additional 15 simulated patients instantly

2. WHEN Simulate Surge activated, THE Clinical_Interface SHALL detect waiting queue size greater than threshold 15 and activate surge mode

3. WHEN surge mode activated, THE Clinical_Interface SHALL call ML Core surge engine for each waiting patient to compute sub-scores (0-100)

4. WHEN surge mode activated, THE Clinical_Interface SHALL display sub-score on each Patient_Card below ESI level

5. WHEN surge mode activated, THE Clinical_Interface SHALL re-sort Waiting_Queue_Dashboard by ESI level (primary), then sub-score descending (secondary), then arrival time (tertiary)

6. THE Clinical_Interface SHALL highlight patients with sub-score greater than 80 as high priority within their ESI category (orange highlight)

7. WHEN surge mode active, THE Recommendation_Panel SHALL display sub-score for newly triaged patients

8. THE Clinical_Interface SHALL provide Exit Surge Mode button to clear additional patients and return to normal operations

9. THE Clinical_Interface SHALL log surge mode activation timestamp, patient count, and deactivation timestamp to audit trail

### Requirement 8: Confidence and Uncertainty Surfacing

**User Story:** As a clinician, I want uncertainty and confidence issues explicitly highlighted, so that I know when to apply extra scrutiny or gather additional information.

#### Acceptance Criteria

1. WHEN overall confidence is LOW (less than 60%), THE Recommendation_Panel SHALL display prominent warning banner "LOW CONFIDENCE - Exercise Clinical Caution"

2. WHEN data completeness dimension is less than 70%, THE Recommendation_Panel SHALL display recommendation "Incomplete Data: Consider obtaining [missing fields list]"

3. WHEN clinical consistency dimension is less than 50%, THE Recommendation_Panel SHALL display recommendation "Symptom-Vital Discordance: Patient may be under-reporting symptoms"

4. WHEN pattern recognition dimension is less than 30%, THE Recommendation_Panel SHALL display recommendation "Unusual Presentation: Out-of-distribution case, exercise caution"

5. WHEN confidence is LOW and predicted ESI is 3 or higher, THE Recommendation_Panel SHALL display auto-escalation suggestion "Consider escalating to ESI [predicted-1] for safety"

6. THE Confidence_Indicator SHALL use color coding: HIGH green, MEDIUM yellow, LOW red

7. THE Recommendation_Panel SHALL display tooltip on each confidence dimension explaining what it measures and why score is high or low

8. WHEN Safety_Flag is YELLOW or RED, THE Recommendation_Panel SHALL display safety concerns above ML prediction with higher visual priority

9. THE Clinical_Interface SHALL log all LOW confidence predictions to audit trail for quality review

### Requirement 9: Fail-Safe and Error Handling

**User Story:** As an ED nurse, I want the system to handle errors gracefully and default to safe escalation when ML is unavailable, so that patient safety is never compromised by technical failures.

#### Acceptance Criteria

1. IF ML Core API call fails or times out (greater than 5 seconds), THEN THE Clinical_Interface SHALL display error message "ML prediction unavailable, defaulting to manual triage"

2. IF ML Core API returns error, THEN THE Clinical_Interface SHALL display Fail_Safe_Default recommendation: ESI 2, LOW confidence, with message "System error - manual clinical assessment required"

3. IF ML Core API unavailable, THEN THE Clinical_Interface SHALL allow nurse to manually assign ESI level without override dialog (direct entry)

4. THE Clinical_Interface SHALL validate all user inputs client-side before API calls (age 0-120, HR 20-250, BP systolic greater than diastolic, SpO2 50-100)

5. THE Clinical_Interface SHALL display user-friendly error messages for validation failures (e.g., "Heart rate must be between 20 and 250 bpm")

6. THE Clinical_Interface SHALL retry failed API calls up to 2 times with exponential backoff (1 second, 2 seconds)

7. THE Clinical_Interface SHALL log all errors and fail-safe activations to audit trail with error details

8. IF deterioration monitoring API fails, THEN THE Clinical_Interface SHALL display warning on Patient_Card "Deterioration check failed - manual assessment required"

9. THE Clinical_Interface SHALL prevent data loss by auto-saving Patient_Intake_Form to browser local storage every 10 seconds

10. THE Clinical_Interface SHALL restore unsaved intake form from local storage if browser crashes or navigates away

### Requirement 10: Ambiguous Presentation Handling

**User Story:** As a clinician, I want to see how the system handles ambiguous presentations where ESI could reasonably be 2 or 3, so that I can evaluate whether confidence scoring and explanations guide appropriate decisions.

#### Acceptance Criteria

1. THE Simulated_Patient_Generator SHALL create at least 1 ambiguous patient: 45-year-old with atypical chest pain, mild tachycardia (HR 105), normal SpO2 (97%), no cardiac history

2. WHEN ambiguous patient triaged, THE ML Core SHALL predict ESI 2 or ESI 3 with probability distribution showing both levels have significant likelihood (e.g., ESI 2 at 45%, ESI 3 at 40%)

3. WHEN ambiguous patient triaged, THE Recommendation_Panel SHALL display confidence level MEDIUM or LOW (overall confidence 60-80%)

4. THE Recommendation_Panel SHALL display SHAP explanation showing mixed contributing factors (age increases urgency, normal vitals decrease urgency, chest pain increases urgency)

5. THE Recommendation_Panel SHALL display recommendation acknowledging ambiguity: "Borderline case: ESI 2 vs 3. Consider cardiac risk factors and clinical presentation."

6. THE Clinical_Interface SHALL enable clinician to easily override ambiguous prediction without excessive justification (dropdown only, free text optional)

7. THE Clinical_Interface SHALL log ambiguous cases (confidence 60-80% with probability distribution entropy greater than threshold) separately for model improvement analysis

8. WHEN ambiguous patient accepted without override, THE Clinical_Interface SHALL add note to patient record "Ambiguous presentation - monitor closely"

### Requirement 11: Pediatric and Geriatric Patient Handling

**User Story:** As an ED nurse, I want age-appropriate validation and visual cues for pediatric and geriatric patients, so that I apply correct vital sign interpretation and recognize high-risk demographics.

#### Acceptance Criteria

1. WHEN patient age is less than 18, THE Patient_Intake_Form SHALL display "PEDIATRIC PATIENT" badge and apply pediatric vital sign ranges

2. WHEN patient age is 65 or greater, THE Patient_Intake_Form SHALL display "GERIATRIC PATIENT" badge and apply geriatric vital sign ranges

3. THE Patient_Intake_Form SHALL display age-specific normal ranges as helper text below vital input fields (e.g., "Normal pediatric HR: 70-120 bpm")

4. WHEN pediatric vital entered outside age-appropriate range, THE Patient_Intake_Form SHALL show yellow warning "Outside normal pediatric range" without blocking submission

5. WHEN geriatric patient triaged, THE Recommendation_Panel SHALL highlight if age is a contributing factor in SHAP explanation

6. THE Simulated_Patient_Generator SHALL create pediatric infant (age 1) with fever (38.5°C), HR 140 (normal for infant), and fussiness to demonstrate age-appropriate vital interpretation

7. THE Simulated_Patient_Generator SHALL create geriatric patient (age 78) with fall, normal vitals, but history of anticoagulation to demonstrate high-risk despite stable presentation

8. THE Clinical_Interface SHALL log patient age group with every triage decision for age-stratified performance analysis

### Requirement 12: Zero-History Patient Handling

**User Story:** As an ED nurse, I want to see how the system handles patients with no prior ED visits and minimal medical history, so that I can evaluate confidence penalization for incomplete data.

#### Acceptance Criteria

1. THE Simulated_Patient_Generator SHALL create at least 1 zero-history patient with patient identifier, demographics, current vitals, and chief complaint only (no medical history, no prior visits)

2. WHEN zero-history patient triaged, THE Patient_Intake_Form SHALL show data completeness score less than 70%

3. WHEN zero-history patient triaged, THE Recommendation_Panel SHALL show data completeness confidence dimension less than 70%

4. THE Recommendation_Panel SHALL display recommendation "Limited Patient History: Consider additional screening questions"

5. WHEN zero-history patient has LOW confidence (overall less than 60%), THE Recommendation_Panel SHALL suggest escalation if predicted ESI is 3 or higher

6. THE Clinical_Interface SHALL allow nurse to mark patient as "No Known History" with checkbox, which acknowledges limited data without penalizing confidence further

7. THE Clinical_Interface SHALL log zero-history patient triage events separately for analysis of performance on data-sparse cases

### Requirement 13: Visual Alert System

**User Story:** As an ED nurse, I want clear visual and audible alerts for high-risk patients and deteriorating conditions, so that critical issues are immediately noticeable in a busy ED environment.

#### Acceptance Criteria

1. WHEN ML Core returns Safety_Flag RED, THE Recommendation_Panel SHALL display red banner at top with icon, bold text "CRITICAL SAFETY ALERT", and triggered criteria list

2. WHEN ML Core returns Safety_Flag YELLOW, THE Recommendation_Panel SHALL display yellow border and warning icon with caution message

3. WHEN ML Core returns Safety_Flag GREEN, THE Recommendation_Panel SHALL display green checkmark icon with "No Safety Concerns" message

4. WHEN predicted ESI is 1, THE Recommendation_Panel SHALL display pulsing red background animation and play alert sound (dismissible)

5. WHEN deterioration detected (status DETERIORATING or score greater than or equal to 60), THE Clinical_Interface SHALL display red alert modal with patient name, vital changes, and action buttons (Escalate ESI, Expedite Treatment, Dismiss)

6. WHEN deterioration detected, THE Waiting_Queue_Dashboard SHALL update Patient_Card with red border, "DETERIORATING" badge, and audible alert tone

7. WHEN re-assessment due, THE Waiting_Queue_Dashboard SHALL update Patient_Card with orange border and "RE-ASSESSMENT DUE" badge (no sound)

8. WHEN wait time exceeds safety threshold (ESI 2 greater than 30 min, ESI 3 greater than 60 min), THE Waiting_Queue_Dashboard SHALL display yellow warning icon on Patient_Card

9. THE Clinical_Interface SHALL provide audio settings to enable or disable alert sounds per user preference

10. THE Clinical_Interface SHALL use WCAG 2.1 AA compliant color contrast for all alert states (red on white, yellow on black, green on white)

### Requirement 14: Session Management and Authentication

**User Story:** As an ED nurse, I want to log in with my credentials to start a triage session, so that all my actions are audited and attributed to me for accountability.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL display login screen requiring username and password before accessing patient data

2. THE Clinical_Interface SHALL validate credentials against user database with roles (ED_Nurse, Attending_Physician, Administrator)

3. WHEN login successful, THE Clinical_Interface SHALL create Session with user identifier, role, login timestamp, and session token

4. THE Clinical_Interface SHALL display user name and role in header throughout session

5. THE Clinical_Interface SHALL log all triage decisions, overrides, and patient interactions with session user identifier for audit attribution

6. THE Clinical_Interface SHALL provide Logout button to end session and clear session token

7. THE Clinical_Interface SHALL auto-logout after 60 minutes of inactivity for security

8. THE Clinical_Interface SHALL display session timeout warning 5 minutes before auto-logout with option to extend session

9. THE Clinical_Interface SHALL restrict Administrator role features (user management, audit log viewing) from ED_Nurse and Attending_Physician roles

10. THE Clinical_Interface SHALL encrypt session tokens and store in httpOnly secure cookies

### Requirement 15: Audit Trail and Logging

**User Story:** As a hospital administrator, I want comprehensive audit logs of all triage decisions and system actions, so that I can investigate incidents, demonstrate compliance, and analyze override patterns.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL write audit entry for each patient triage containing timestamp, session user identifier, patient identifier, patient demographics, input vitals, ML predicted ESI, ML confidence breakdown, Safety_Flag, final ESI decision, and override flag

2. WHEN clinician override occurs, THE Clinical_Interface SHALL write audit entry containing ML predicted ESI, clinician final ESI, override reason category, override reason text, and override timestamp

3. WHEN deterioration detected, THE Clinical_Interface SHALL write audit entry containing patient identifier, deterioration status, deterioration score, vital changes, and alert timestamp

4. THE Clinical_Interface SHALL write audit entry for surge mode activation and deactivation with timestamp and patient count

5. THE Clinical_Interface SHALL write audit entry for all ML Core API failures with error message and timestamp

6. THE Clinical_Interface SHALL store audit logs in PostgreSQL database with immutable insert-only schema (no updates or deletes allowed)

7. THE Clinical_Interface SHALL provide Audit Log Viewer (Administrator role only) showing filterable table of all audit entries

8. THE Audit Log Viewer SHALL support filtering by date range, user identifier, patient identifier, ESI level, override flag, and Safety_Flag

9. THE Clinical_Interface SHALL export audit logs to CSV format for external analysis (Administrator role only)

10. THE Clinical_Interface SHALL retain audit logs for minimum 7 years in compliance with medical record retention requirements

### Requirement 16: HIPAA Compliance and Data Protection

**User Story:** As a privacy officer, I want patient data protected according to HIPAA requirements, so that we avoid breaches and maintain patient trust.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL encrypt all patient data in transit using HTTPS with TLS 1.3 or higher

2. THE Clinical_Interface SHALL not store patient identifiable information in browser local storage (only session token stored)

3. THE Clinical_Interface SHALL redact patient names from audit logs in HIPAA_Mode for demonstration screenshots and recordings

4. THE Clinical_Interface SHALL implement role-based access control restricting patient data access to authenticated ED_Nurse and Attending_Physician roles only

5. THE Clinical_Interface SHALL log all patient data access events (view patient record, view waiting queue) with user identifier and timestamp

6. THE Clinical_Interface SHALL display HIPAA compliance notice on login screen: "This system contains protected health information. Unauthorized access is prohibited."

7. THE Clinical_Interface SHALL auto-lock screen after 5 minutes of inactivity requiring re-authentication

8. THE Clinical_Interface SHALL not display patient data in browser page title or URL for screenshot privacy

9. THE Clinical_Interface SHALL provide data anonymization toggle for prototype demonstrations (replace real names with "Patient A", "Patient B", etc.)

10. THE Clinical_Interface SHALL hash patient identifiers in database using SHA-256 before storage for pseudonymization

### Requirement 17: Performance and Responsiveness

**User Story:** As an ED nurse, I want the interface to respond instantly to my actions, so that I can triage patients quickly without waiting for loading screens.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL load Patient_Intake_Form within 500 milliseconds of clicking New Patient button

2. THE Clinical_Interface SHALL display Recommendation_Panel within 2 seconds of submitting Patient_Intake_Form (including ML Core API call latency)

3. THE Clinical_Interface SHALL update Waiting_Queue_Dashboard in real-time (less than 1 second latency) when deterioration detected via WebSocket

4. THE Clinical_Interface SHALL validate Patient_Intake_Form inputs with zero perceptible delay (less than 100 milliseconds)

5. THE Clinical_Interface SHALL render Waiting_Queue_Dashboard with 50 Patient_Cards within 1 second

6. THE Clinical_Interface SHALL handle concurrent user sessions supporting minimum 10 simultaneous ED nurses without performance degradation

7. THE Clinical_Interface SHALL paginate Audit Log Viewer results displaying 50 entries per page with lazy loading

8. THE Clinical_Interface SHALL cache simulated patient data in memory after initial load to eliminate database query latency during prototype demonstrations

9. THE Clinical_Interface SHALL display loading spinner during ML Core API calls with timeout message if exceeds 5 seconds

10. THE Clinical_Interface SHALL optimize SHAP_Visualization rendering to display within 500 milliseconds (lazy load chart library if needed)

### Requirement 18: Responsive Design and Accessibility

**User Story:** As an ED nurse, I want the interface to work on tablets and large monitors with touch or mouse input, so that I can use it at triage desk or bedside.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL support responsive layouts for screen widths 1024 pixels (tablet landscape) to 1920 pixels (desktop monitor)

2. THE Patient_Intake_Form SHALL use single-column layout on tablet (1024px) and two-column layout on desktop (greater than 1440px)

3. THE Waiting_Queue_Dashboard SHALL display Patient_Cards in grid layout: 2 columns on tablet, 3 columns on desktop (1440px), 4 columns on large desktop (1920px)

4. THE Clinical_Interface SHALL support touch gestures: tap to select, swipe to scroll, pinch to zoom charts

5. THE Clinical_Interface SHALL use minimum 16px font size for body text and 44px minimum touch target size for buttons (WCAG 2.1 AA)

6. THE Clinical_Interface SHALL provide keyboard navigation: Tab to move between fields, Enter to submit forms, Escape to close modals

7. THE Clinical_Interface SHALL provide ARIA labels for screen reader accessibility on all interactive elements

8. THE Clinical_Interface SHALL maintain 4.5:1 color contrast ratio for normal text and 3:1 for large text (WCAG 2.1 AA)

9. THE Clinical_Interface SHALL provide focus indicators (blue outline) for keyboard navigation

10. THE Clinical_Interface SHALL display descriptive alt text for all icons and images for screen reader users

### Requirement 19: Technology Stack and Architecture

**User Story:** As a developer, I want clear technical specifications for frontend, backend, and integration, so that I can build a maintainable, scalable prototype.

#### Acceptance Criteria

1. THE Clinical_Interface frontend SHALL use React 18 or higher with TypeScript for type safety

2. THE Clinical_Interface SHALL use Material-UI (MUI) or Ant Design component library for consistent UI design

3. THE Clinical_Interface SHALL use React Router for client-side routing between intake, recommendation, queue dashboard, and audit log views

4. THE Clinical_Interface SHALL use Redux Toolkit or Zustand for global state management (current patient, waiting queue, session)

5. THE Clinical_Interface backend SHALL use FastAPI (Python 3.10 or higher) as API server integrating with ML Core

6. THE Clinical_Interface SHALL use PostgreSQL 15 or higher for relational database storing patient records, audit logs, and user accounts

7. THE Clinical_Interface SHALL use Socket.io or native WebSockets for real-time deterioration alerts and queue updates

8. THE Clinical_Interface SHALL use JSON Web Tokens (JWT) for stateless session authentication

9. THE Clinical_Interface SHALL containerize frontend (Nginx serving React build) and backend (FastAPI with Gunicorn) using Docker for deployment

10. THE Clinical_Interface SHALL provide Docker Compose configuration for single-command local development environment setup

### Requirement 20: Prototype Demonstration Workflow

**User Story:** As a demonstration evaluator, I want a guided workflow that showcases all key features in 10-15 minutes, so that I can efficiently assess the system's capabilities.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL provide Prototype Mode toggle loading 20 pre-generated simulated patients and enabling demonstration features

2. WHEN Prototype Mode activated, THE Clinical_Interface SHALL display Guided Tour overlay with 8 steps: (1) Login, (2) Triage patient, (3) View recommendation, (4) Override decision, (5) Monitor queue, (6) Detect deterioration, (7) Activate surge mode, (8) Review audit log

3. THE Guided Tour SHALL highlight relevant UI elements with pulsing border and tooltip text explaining feature

4. THE Clinical_Interface SHALL provide Next and Previous buttons in Guided Tour to navigate between steps

5. THE Clinical_Interface SHALL provide Skip Tour button to dismiss Guided Tour and explore freely

6. THE Clinical_Interface SHALL provide Demo Scenarios dropdown pre-selecting interesting patients: "Ambiguous Chest Pain (Patient 5)", "Pediatric Fever (Patient 12)", "Geriatric Fall (Patient 18)", "Zero History (Patient 20)"

7. WHEN demo scenario selected, THE Clinical_Interface SHALL auto-populate Patient_Intake_Form with selected patient data

8. THE Clinical_Interface SHALL provide Reset Demo button to clear all triage decisions and restore initial 20-patient state

9. THE Clinical_Interface SHALL display demonstration statistics: patients triaged, overrides captured, deterioration alerts triggered, surge mode activations

10. THE Clinical_Interface SHALL provide Export Demo Report button generating PDF summary with screenshots, statistics, and audit log excerpt

### Requirement 21: Integration with ML Core API

**User Story:** As a developer, I want clear API contracts for calling ML Core endpoints, so that frontend and backend integration is reliable and type-safe.

#### Acceptance Criteria

1. THE Clinical_Interface backend SHALL call ML Core POST /api/v1/predict endpoint for ESI classification with PatientData JSON request body

2. THE Clinical_Interface SHALL parse ML Core PredictionResponse JSON containing esi_prediction, probability_distribution, confidence_breakdown, safety_flag, explanation, sub_score, recommendations, and model_version

3. THE Clinical_Interface backend SHALL call ML Core POST /api/v1/deterioration endpoint for deterioration assessment with DeteriorationRequest JSON containing patient_id, initial_vitals, current_vitals, initial_esi, time_since_triage_minutes, and age_group

4. THE Clinical_Interface SHALL parse ML Core DeteriorationResponse JSON containing status, score, vital_changes, explanation, recommendation, confidence, next_check_in_minutes, and alert_triggered

5. THE Clinical_Interface SHALL handle ML Core API errors (400, 401, 500, 503) and display user-friendly error messages

6. THE Clinical_Interface SHALL retry transient errors (500, 503) up to 2 times with exponential backoff before displaying fail-safe default

7. THE Clinical_Interface SHALL validate ML Core response schemas using TypeScript interfaces or Zod validators before rendering UI

8. THE Clinical_Interface SHALL log all ML Core API requests and responses to audit trail including request_id, timestamp, endpoint, status_code, and latency_ms

9. THE Clinical_Interface SHALL pass session user identifier to ML Core API in request metadata for audit attribution

10. THE Clinical_Interface SHALL display ML Core model_version in Recommendation_Panel footer for traceability

### Requirement 22: Data Anonymization for Demonstrations

**User Story:** As a demonstration presenter, I want to anonymize patient data for public presentations, so that I can showcase the system without HIPAA concerns.

#### Acceptance Criteria

1. THE Clinical_Interface SHALL provide Anonymization Toggle in settings switching between real names and anonymous identifiers

2. WHEN Anonymization Toggle enabled, THE Clinical_Interface SHALL display patient names as "Patient A", "Patient B", etc. in sequential order

3. WHEN Anonymization Toggle enabled, THE Clinical_Interface SHALL replace photo placeholders with generic avatar icons

4. WHEN Anonymization Toggle enabled, THE Clinical_Interface SHALL redact patient identifiers from audit logs in Audit Log Viewer

5. THE Clinical_Interface SHALL maintain anonymization toggle state across browser refresh using local storage

6. THE Clinical_Interface SHALL apply anonymization to all UI components: Patient_Cards, Recommendation_Panel, Override_Dialog, Audit Log Viewer

7. THE Clinical_Interface SHALL provide disclaimer when anonymization enabled: "Demo Mode: Patient data anonymized for presentation"

8. THE Simulated_Patient_Generator SHALL use fictional but realistic names (John Smith, Maria Garcia, etc.) that can be anonymized

9. THE Clinical_Interface SHALL not anonymize clinical data (vitals, chief complaints, ESI levels) as these are necessary for demonstration

10. THE Clinical_Interface SHALL include anonymization state in exported demo report for clarity

### Requirement 23: Parser for Patient Data JSON and Pretty Printer

**User Story:** As a developer, I want to parse patient data from ML Core JSON responses and format it back for validation, so that I ensure data integrity throughout the workflow.

#### Acceptance Criteria

1. WHEN ML Core API returns PredictionResponse JSON, THE Clinical_Interface SHALL parse it into typed PredictionResponse object with all fields validated

2. WHEN ML Core API returns DeteriorationResponse JSON, THE Clinical_Interface SHALL parse it into typed DeteriorationResponse object with all fields validated

3. WHEN parsing fails due to invalid JSON syntax, THE Clinical_Interface SHALL display error message "Invalid API response format" and log error details

4. WHEN parsing fails due to missing required fields, THE Clinical_Interface SHALL display error message identifying missing field name

5. THE Clinical_Interface SHALL provide Pretty_Printer function that formats patient data objects back into valid JSON with 2-space indentation and sorted keys

6. FOR ALL valid patient data objects, parsing the JSON then pretty-printing then parsing again SHALL produce equivalent object with all field values preserved (round-trip property)

7. THE Clinical_Interface SHALL validate round-trip integrity for PatientData, PredictionResponse, and DeteriorationResponse in unit tests

8. THE Clinical_Interface SHALL display formatted JSON in Audit Log Viewer detail view for debugging

9. THE Pretty_Printer SHALL escape special characters and handle nested objects correctly for complex SHAP explanation structures

10. THE Clinical_Interface SHALL provide JSON schema validation for all API requests and responses using JSON Schema Draft 7 or higher
