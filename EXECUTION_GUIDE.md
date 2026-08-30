# PatientTriage.ai - Complete Execution Guide
## Step-by-Step Setup, Testing, and Demo Instructions

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Testing](#testing)
6. [Demo Scenarios](#demo-scenarios)
7. [Troubleshooting](#troubleshooting)
8. [Video Recording Guide](#video-recording-guide)

---

## 🔧 Prerequisites

### System Requirements

**Operating System:**
- macOS 10.15+ (Catalina or later)
- Linux (Ubuntu 20.04+ or equivalent)
- Windows 10/11 with WSL2

**Hardware:**
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Modern multi-core processor

**Software:**
- **Python 3.10 or higher** (check with `python3 --version`)
- **pip** package manager (check with `pip3 --version`)
- **Modern web browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

### Verify Python Installation

```bash
python3 --version
# Expected output: Python 3.10.x or higher

pip3 --version
# Expected output: pip 22.x or higher
```

If Python is not installed:
- **macOS**: `brew install python@3.10`
- **Linux**: `sudo apt install python3.10 python3-pip`
- **Windows**: Download from python.org

---

## 📦 Installation

### Step 1: Navigate to Project Directory

```bash
cd /Users/divyanshiii/Win
# Or wherever you cloned/downloaded the repository

# Verify you're in the correct directory
ls -la
# Should see: app.py, frontend/, data/, src/, requirements.txt
```

### Step 2: Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

**Expected packages installed:**
- fastapi
- uvicorn[standard]
- catboost
- shap
- numpy
- pandas
- pydantic
- scikit-learn
- python-multipart

**Verify installation:**
```bash
python3 -c "import fastapi, catboost, shap, sklearn; print('✅ All core dependencies installed')"
```

**Expected output:**
```
✅ All core dependencies installed
```

If you see import errors, reinstall specific packages:
```bash
pip3 install --upgrade fastapi catboost shap scikit-learn
```

---

## 🚀 Backend Setup

### Step 1: Verify Data Files Exist

```bash
ls -la data/
```

**Expected files:**
- `patients.json` - Queue state (can be empty initially: `[]`)
- `overrides.json` - Override audit log (can be empty initially: `[]`)
- `test_patients.json` - Demo patient scenarios

If missing, create them:
```bash
mkdir -p data
echo "[]" > data/patients.json
echo "[]" > data/overrides.json
```

### Step 2: Start the Backend Server

```bash
uvicorn app:app --reload --port 8000
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/Users/divyanshiii/Win']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Troubleshooting:**

**Error: `Address already in use`**
```bash
# Port 8000 is already taken
# Find and kill the process:
lsof -ti:8000 | xargs kill -9

# Or use a different port:
uvicorn app:app --reload --port 8001
```

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
# Dependencies not installed
pip3 install -r requirements.txt
```

### Step 3: Verify Backend is Running

**Option A: Browser**
- Open: http://localhost:8000/docs
- Should see interactive API documentation (Swagger UI)

**Option B: Command Line**
```bash
curl http://localhost:8000/docs
# Should return HTML content (Swagger UI page)
```

**Option C: Test Health Endpoint**
```bash
curl http://localhost:8000/api/v1/patients
# Should return: [] (empty queue) or JSON array of patients
```

✅ **Backend is ready when you see the Swagger UI at /docs**

---

## 🌐 Frontend Setup

### Patient Intake Form

**Step 1: Open index.html**

```bash
# macOS
open frontend/index.html

# Linux
xdg-open frontend/index.html

# Windows (WSL)
explorer.exe frontend/index.html

# Or manually:
# Navigate to: file:///Users/divyanshiii/Win/frontend/index.html
```

**Expected:**
- Page loads in browser
- Title: "PatientTriage.ai - Emergency Department Triage Assistant"
- Left panel: Patient intake form
- Right panel: "Enter patient data to see ML recommendation"

### Clinical Queue & Governance Views

**Step 2: Open queue.html**

```bash
# macOS
open frontend/queue.html

# Linux
xdg-open frontend/queue.html

# Windows (WSL)
explorer.exe frontend/queue.html
```

**Expected:**
- Page loads with two views: Clinical View (default) and Governance View
- Top bar shows: "Clinical Queue" and "Governance & Audit" tabs
- Queue initially empty or shows patients from patients.json

### Verify Frontend-Backend Connection

**Step 1: In queue.html**
- Click "🔄 Refresh Queue"
- Browser console should show: "Loaded X patients"

**Step 2: In index.html**
- Load a test patient from dropdown
- Click "Get AI Triage Recommendation"
- Should see prediction results (not "Failed to fetch" error)

✅ **Frontend is ready when test prediction returns results**

---

## 🧪 Testing

### Automated Test Suite

#### Test 1: ML Core Validation

**Purpose:** Verify ML pipeline end-to-end

```bash
python test_ml_core.py
```

**Expected output:**
```
🔬 PatientTriage.ai - ML Core Validation Tests
===============================================

📡 Test 1: Server Health Check
✅ Server is running at http://localhost:8000

🧪 Test 2: Diverse Patient Scenarios
✅ ESI 1 (Critical) - Cardiac Arrest: PASS
✅ ESI 2 (Emergent) - Stroke: PASS
✅ ESI 3 (Urgent) - Moderate Injury: PASS
✅ ESI 4 (Less Urgent) - Minor Injury: PASS
✅ ESI 5 (Non-Urgent) - Minor Complaint: PASS
✅ Ambiguous Case - Chest Pain: PASS
✅ Pediatric Case - Infant Fever: PASS

✅ All tests PASSED!
```

If tests fail, check:
1. Backend server is running
2. Port 8000 is accessible
3. Dependencies installed correctly

#### Test 2: Frontend Integration

**Purpose:** Verify HTML structure and JavaScript

```bash
python test_frontend_integration.py
```

**Expected output:**
```
🧪 Frontend Integration Tests
==============================

✅ Test 1: HTML Structure
✅ Test 2: Form Fields Present
✅ Test 3: JavaScript Functions Defined
✅ Test 4: API Endpoints Referenced
✅ Test 5: Chart.js Loaded
✅ Test 6: Result Display Elements
✅ Test 7: Event Listeners
✅ Test 8: Error Handling
✅ Test 9: Data Completeness Indicator

✅ 9/9 tests passed!
```

#### Test 3: Visual Alerts

**Purpose:** Verify high-risk case styling

```bash
python test_visual_alerts.py
```

**Expected output:**
```
🎨 Visual Alerts Tests
======================

✅ Test 1: ESI 1 Pulsing Red Border
✅ Test 2: RED Safety Flag Banner
✅ Test 3: LOW Confidence Warning
✅ Test 4: MEDIUM Confidence Warning
... (13 tests total)

✅ 13/13 tests passed!
```

### Manual Testing

#### Test Scenario 1: Normal Flow

1. **Open index.html**
2. **Load test patient**: "Moderate Injury - 35yo Male"
3. **Click**: "Get AI Triage Recommendation"
4. **Verify**:
   - ESI prediction displayed (likely ESI 3 or 4)
   - Confidence scores shown
   - Safety flag is GREEN or YELLOW
   - SHAP explanation present
   - Probability chart renders

#### Test Scenario 2: Critical Case with RED Flag

1. **Open index.html**
2. **Load test patient**: "Cardiac Arrest - 68yo Male"
3. **Click**: "Get AI Triage Recommendation"
4. **Verify**:
   - ESI 1 prediction
   - **Pulsing red border** around results panel
   - **RED safety flag** banner at top
   - Safety criteria shown (e.g., "Age > 65 + Chest Pain")
   - High confidence (>80%)

#### Test Scenario 3: Low Confidence Warning

1. **Open index.html**
2. **Load test patient**: "Ambiguous Chest Pain - 45yo Male"
3. **Click**: "Get AI Triage Recommendation"
4. **Verify**:
   - ESI 2 or 3 prediction
   - **YELLOW safety flag**
   - LOW or MEDIUM confidence
   - **Warning message** displayed
   - Confidence breakdown shows which dimension is low

#### Test Scenario 4: Clinician Override

1. **Complete Test Scenario 1** (get a prediction)
2. **Click**: "Override Recommendation" button
3. **In dialog**:
   - Select different ESI (e.g., if ML said 3, select 2)
   - Choose reason: "Clinical Judgment"
   - Enter text: "Patient appears more distressed than vitals indicate"
   - Enter clinician ID: "Dr. Test Clinician"
4. **Click**: "Submit Override"
5. **Verify**:
   - Success alert appears
   - Override ID shown
   - Patient added to queue

#### Test Scenario 5: Queue Management

1. **Open queue.html**
2. **Verify**:
   - Patients displayed in cards
   - **ESI badges** color-coded
   - **Time left** shown (e.g., "25 min left", not "25 min waited")
   - Sorted by ESI level first, then time left
3. **Test search**:
   - Type patient name in search box
   - Queue filters in real-time
4. **Test remove**:
   - Click on a patient card
   - Click "Remove from Queue"
   - Verify queue count decreases

#### Test Scenario 6: Governance Audit View

1. **In queue.html**, click "Governance & Audit" tab
2. **Verify**:
   - Accountability metrics displayed (8 cards)
   - Patients with overrides shown (orange background)
   - Override details visible
   - **Clinician ID displayed** (e.g., "👤 Overridden By: Dr. Test Clinician")
   - ML ESI vs Override ESI shown correctly
3. **Test governance search**:
   - Type in governance search box
   - Results filter independently from clinical view

---

## 🎬 Demo Scenarios

### Demo 1: Typical Patient Flow (2 minutes)

**Script:**

1. **"Let me show you a typical emergency department patient."**
   - Open index.html
   - Load: "Moderate Injury - 35yo Male"

2. **"The nurse enters demographics, vitals, and chief complaint."**
   - Highlight the auto-populated fields
   - Point out data completeness indicator (e.g., 87%)

3. **"Click 'Get AI Triage Recommendation' for instant ESI prediction."**
   - Click button
   - Wait for results (~100ms)

4. **"The system provides a comprehensive assessment."**
   - Point to ESI badge (e.g., ESI 3)
   - Show probability chart
   - Explain confidence scores:
     - "Model is 85% certain"
     - "Data is 87% complete"
     - "Vitals are clinically consistent"
   - Show SHAP explanation:
     - "Chief complaint 'Moderate Injury' suggests ESI 3"
     - "Vital signs are mostly normal"

5. **"Safety validation shows GREEN - no concerns."**
   - Point to safety flag

6. **"Nurse can accept or override this recommendation."**
   - Show both buttons

### Demo 2: High-Risk Patient with RED Flag (3 minutes)

**Script:**

1. **"Now let's see a critical case."**
   - Load: "Cardiac Arrest - 68yo Male" or "Severe Hypoxia - 72yo Female"

2. **"Notice the age and chief complaint."**
   - Age: 68, Chief Complaint: Cardiac Arrest

3. **"Click 'Get AI Triage Recommendation'."**

4. **"The system immediately flags this as ESI 1 - life-threatening."**
   - Point to **pulsing red border**
   - Show **ESI 1 badge** in red

5. **"A RED safety banner alerts the nurse."**
   - Read safety criteria: "Age > 65 + Chest Pain (Cardiac Risk)"
   - Show "CRITICAL ALERT" message

6. **"This patient needs immediate resuscitation."**
   - Explain ESI 1 = 0 minutes wait time

7. **"The explanation shows why."**
   - SHAP: "Chief complaint 'Cardiac Arrest' increases urgency by 95%"
   - "Age 68 increases urgency for cardiac presentations"

### Demo 3: Ambiguous Case with Low Confidence (3 minutes)

**Script:**

1. **"Not all cases are clear-cut. Let's try an ambiguous one."**
   - Load: "Ambiguous Chest Pain - 45yo Male"

2. **"This patient has borderline vitals."**
   - Show: HR 92 (slightly elevated), BP 135/85 (borderline high)

3. **"Click 'Get AI Triage Recommendation'."**

4. **"The model predicts ESI 3, but with MEDIUM confidence."**
   - Show confidence: ~65-70%
   - Point out which dimension is low (e.g., Model Certainty)

5. **"A YELLOW safety flag recommends validation."**
   - "Chest pain in patient >45 (cardiac risk)"
   - "Recommend clinical validation"

6. **"The system is transparent about uncertainty."**
   - Show probability chart: spread across ESI 2, 3, 4
   - "Model is less certain - probabilities are not peaked"

7. **"This helps nurses know when to seek senior input."**

### Demo 4: Clinician Override Workflow (3 minutes)

**Script:**

1. **"Clinicians can override any recommendation."**
   - Start from any prediction result

2. **"Suppose the nurse disagrees. Click 'Override Recommendation'."**
   - Click button
   - Dialog opens

3. **"She selects her clinical ESI assessment."**
   - Select ESI 2 (if ML said ESI 3)

4. **"Choose the reason category."**
   - Select: "Clinical Judgment"

5. **"Provide detailed justification - minimum 20 characters."**
   - Type: "Patient appears more distressed and anxious than vitals suggest. Sweating and pale."

6. **"Enter clinician ID for accountability."**
   - Type: "Dr. Sarah Johnson"

7. **"Submit the override."**
   - Click "Submit Override"
   - Show success alert with override ID

8. **"This is logged for quality improvement and model retraining."**
   - Open queue.html
   - Go to Governance View
   - Find the overridden patient (orange background)
   - Point to override details:
     - ML predicted ESI 3
     - Clinician escalated to ESI 2
     - Reason shown
     - **Clinician ID displayed: "👤 Overridden By: Dr. Sarah Johnson"**

### Demo 5: Queue Management (2 minutes)

**Script:**

1. **"After triage, patients enter the clinical queue."**
   - Open queue.html
   - Show Clinical View

2. **"Patients are sorted by urgency."**
   - Point to ESI order: ESI 1 → ESI 5
   - "Within each ESI, those with less time left appear first"

3. **"Each card shows key information."**
   - ESI badge (color-coded)
   - Time left until assessment deadline
   - Patient demographics
   - Chief complaint

4. **"Notice the time display."**
   - "This shows time LEFT, not time waited"
   - Example: "15 min left" (not "15 min")
   - Critical: RED with pulse (<5 min left)
   - Overdue: RED background

5. **"Nurses can search and filter."**
   - Type in search box
   - Queue filters in real-time
   - Use ESI filters (Critical, Urgent, All)

6. **"When a patient is seen, remove them."**
   - Click patient card
   - Click "Remove from Queue"
   - Queue count updates

### Demo 6: Governance & Accountability (3 minutes)

**Script:**

1. **"Switch to Governance View for full audit trail."**
   - Click "Governance & Audit" tab

2. **"This view is for quality assurance and compliance."**
   - Show accountability dashboard:
     - Total patients
     - Escalation rate
     - Override rate
     - Safety flags triggered

3. **"Every patient shows complete history."**
   - Click on an overridden patient (orange background)
   - Show timeline:
     - Arrival
     - ML assessment (with ESI)
     - Clinician override (with new ESI)
     - Current status

4. **"Override details are fully transparent."**
   - ML predicted: ESI 3
   - Override to: ESI 2
   - Direction: ESCALATION
   - Magnitude: 1 level
   - Reason category: Clinical Judgment
   - Detailed text: "..."
   - **Clinician accountability: "👤 Overridden By: Dr. Sarah Johnson"**

5. **"This supports DPDPA 2023 compliance."**
   - Show compliance checklist
   - Purpose limitation
   - Data minimization
   - Accountability

6. **"Governance search filters independently."**
   - Type in governance search
   - Results filter without affecting clinical view

---

## 🎥 Video Recording Guide

### Recommended Setup

**Screen Recording Software:**
- **macOS**: QuickTime Player or ScreenFlow
- **Windows**: OBS Studio or Camtasia
- **Linux**: SimpleScreenRecorder or OBS Studio

**Recording Settings:**
- Resolution: 1920x1080 (1080p HD)
- Frame rate: 30 fps
- Audio: Voiceover or captions
- Duration: 5-8 minutes max
- Format: MP4 (H.264)

### Video Script Outline (7 minutes)

#### Segment 1: Introduction (30 seconds)
- Title slide: "PatientTriage.ai - ML-Powered ED Triage"
- Brief overview: "Demonstrating ESI classification, confidence scoring, safety validation, and explainability"

#### Segment 2: Normal Patient Flow (1:30 minutes)
- Show patient intake form
- Load test patient
- Submit for prediction
- Explain results panel

#### Segment 3: Critical Case (1:30 minutes)
- Load cardiac arrest patient
- Show RED safety flag
- Explain pulsing border
- Show SHAP explanation

#### Segment 4: Override Workflow (1:30 minutes)
- Disagree with prediction
- Open override dialog
- Submit override
- Show governance audit

#### Segment 5: Queue Management (1 minute)
- Show clinical queue
- Explain sorting (ESI + time left)
- Demonstrate search
- Remove patient

#### Segment 6: Governance View (1:30 minutes)
- Switch to governance
- Show accountability dashboard
- Explain override history
- Show clinician ID display

#### Segment 7: Conclusion (30 seconds)
- Recap key features
- Mention real-world complexities addressed
- GitHub repository link

### Recording Tips

1. **Clean browser**: Close unnecessary tabs, hide bookmarks bar
2. **Zoom in**: Increase font size for readability
3. **Slow down**: Pause 2 seconds between actions
4. **Narrate**: Explain what you're doing as you do it
5. **Highlight**: Use cursor to point to important elements
6. **Test audio**: Check microphone levels before full recording
7. **One take per segment**: Record segments separately, then edit together

### Post-Production

1. **Edit**: Cut out mistakes, dead time
2. **Captions**: Add subtitles for accessibility
3. **Music**: Optional background music (keep volume low)
4. **Intro/Outro**: 5-second title cards
5. **Export**: MP4, H.264, 1080p, 30fps

---

## 🔧 Troubleshooting

### Backend Issues

#### "Address already in use" (Port 8000)

**Problem:** Another process is using port 8000

**Solution 1: Kill the process**
```bash
# macOS/Linux
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Solution 2: Use different port**
```bash
uvicorn app:app --reload --port 8001
# Update frontend API URLs to http://localhost:8001
```

#### "Module not found" errors

**Problem:** Dependencies not installed

**Solution:**
```bash
pip3 install --upgrade -r requirements.txt

# If specific package fails:
pip3 install --upgrade fastapi catboost shap scikit-learn
```

#### "File not found: data/patients.json"

**Problem:** Data directory or files missing

**Solution:**
```bash
mkdir -p data
echo "[]" > data/patients.json
echo "[]" > data/overrides.json
```

### Frontend Issues

#### "Failed to fetch" errors

**Problem:** Backend not running or wrong URL

**Solution:**
1. Verify backend: `curl http://localhost:8000/docs`
2. Check browser console for actual error
3. Ensure no CORS issues (shouldn't occur with file://)

#### Charts not displaying

**Problem:** Chart.js not loaded or JavaScript errors

**Solution:**
1. Check browser console for errors
2. Verify internet connection (Chart.js from CDN)
3. Try different browser (Chrome recommended)

#### Results not showing

**Problem:** JavaScript error or API response issue

**Solution:**
1. Open browser console (F12)
2. Look for error messages
3. Check Network tab for API responses
4. Verify backend returned valid JSON

### Data Issues

#### Queue not loading

**Problem:** patients.json corrupted or invalid JSON

**Solution:**
```bash
# Backup current file
cp data/patients.json data/patients.json.backup

# Reset to empty array
echo "[]" > data/patients.json

# Or restore from backup if valid
```

#### Overrides not saving

**Problem:** overrides.json write permission or format issue

**Solution:**
```bash
# Check permissions
ls -la data/overrides.json

# Fix permissions
chmod 644 data/overrides.json

# Reset file
echo "[]" > data/overrides.json
```

### Performance Issues

#### Slow predictions (>1 second)

**Problem:** Model loading or heavy computation

**Solution:**
1. Check backend logs for slowness
2. Restart backend to reload model
3. Ensure sufficient RAM (4GB+)

#### Browser freezing

**Problem:** Too many patients in queue or memory leak

**Solution:**
1. Clear queue (reset patients.json)
2. Restart browser
3. Use incognito mode for testing

---

## ✅ Verification Checklist

Before demo or submission, verify:

### Backend
- [ ] Server starts without errors
- [ ] /docs endpoint shows Swagger UI
- [ ] POST /api/v1/predict returns valid response
- [ ] GET /api/v1/patients returns array
- [ ] POST /api/v1/override saves to overrides.json
- [ ] All test scripts pass

### Frontend
- [ ] index.html loads in browser
- [ ] queue.html loads in browser
- [ ] Test patient dropdown works
- [ ] Form validation works
- [ ] Prediction results display
- [ ] Charts render correctly
- [ ] Override dialog opens and submits
- [ ] Queue displays patients
- [ ] Governance view shows overrides
- [ ] Search functionality works in both views
- [ ] Time left displays correctly (not time waited)
- [ ] Clinician ID shows in governance (not "SYSTEM")

### Features
- [ ] ESI 1 shows pulsing red border
- [ ] RED safety flags display prominently
- [ ] LOW confidence warnings appear
- [ ] SHAP explanations are readable
- [ ] Override workflow end-to-end functional
- [ ] Queue sorting works (ESI → time left)
- [ ] Remove from queue updates count
- [ ] All real-world complexities addressed

### Documentation
- [ ] README.md complete
- [ ] SOLUTION_ARCHITECTURE.md detailed
- [ ] EXECUTION_GUIDE.md (this file) comprehensive
- [ ] requirements.txt includes all dependencies
- [ ] Code comments explain complex logic

---

## 📝 Quick Command Reference

```bash
# Start backend
uvicorn app:app --reload --port 8000

# Run tests
python test_ml_core.py
python test_frontend_integration.py
python test_visual_alerts.py

# Open frontends
open frontend/index.html
open frontend/queue.html

# Check backend health
curl http://localhost:8000/docs

# View API docs in browser
http://localhost:8000/docs

# Reset data files
echo "[]" > data/patients.json
echo "[]" > data/overrides.json

# Install dependencies
pip3 install -r requirements.txt

# Check Python version
python3 --version
```

---

## 🎉 Ready for Submission!

Your prototype is complete when:
1. ✅ All tests pass
2. ✅ Backend runs without errors
3. ✅ Frontend displays results correctly
4. ✅ Override workflow functional end-to-end
5. ✅ Queue management working
6. ✅ Governance view shows overrides with clinician IDs
7. ✅ Time left displays correctly
8. ✅ Documentation complete
9. ✅ Demo video recorded
10. ✅ GitHub repository ready

**Good luck with your submission!** 🚀

---

**Last Updated:** August 29, 2026
**Status:** Production-Ready Prototype
