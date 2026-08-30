# Task 5.5 Visual Test Checklist

## Pre-Test Setup
- [x] Backend server running: `uvicorn app:app --reload` at http://localhost:8000
- [x] Frontend HTML file opened in browser: `/Users/divyanshiii/Win/frontend/index.html`
- [x] Browser console open (F12 or Cmd+Option+I on Mac)

## Visual Verification Checklist

### 1. Page Load (Automatic)
Expected Behavior:
- [ ] Dropdown automatically populates on page load
- [ ] Console shows: "🔄 Loading test patients..."
- [ ] Console shows: "✅ Loaded 20 test patients"
- [ ] Console shows: "✅ Populated dropdown with 20 patients"
- [ ] Dropdown shows "-- Load Test Patient --" as first option
- [ ] 20 patient options visible below

### 2. Dropdown Content Verification
Check that the following patients are visible with correct labels:

**Special Case Patients:**
- [ ] Patient #1: Contains "AMBIGUOUS" label
  - Example: "1. John Smith (45yo, female) [AMBIGUOUS, ZERO-HISTORY] - Chest Pain Cardiac"

- [ ] At least 2 patients with "PEDIATRIC" label
  - Example: "2. Maria Garcia (1yo, female) [PEDIATRIC] - Sepsis Suspected"
  - Example: "3. Wei Chen (8yo, male) [PEDIATRIC, ZERO-HISTORY] - Back Pain Mild"

- [ ] At least 2 patients with "GERIATRIC" label
  - Example: "4. Priya Sharma (78yo, male) [GERIATRIC] - Trauma Head"
  - Example: "5. David Johnson (72yo, male) [GERIATRIC] - Chest Pain Pleuritic"

- [ ] At least 1 patient with "ZERO-HISTORY" label
  - Multiple patients should have this label

**Format Verification:**
- [ ] Each option shows: "[Number]. [Name] ([Age]yo, [Sex]) [Labels] - [Chief Complaint]"
- [ ] All 20 patients numbered 1-20
- [ ] Chief complaints are readable (underscores replaced with spaces, capitalized)

### 3. Patient Selection - Ambiguous Case (Patient #1)
Actions:
1. Select "1. John Smith..." from dropdown

Expected Results:
- [ ] Console shows: "📋 Auto-populating form for patient: John Smith"
- [ ] Console shows: "ℹ️ Special case: AMBIGUOUS, ZERO-HISTORY"
- [ ] Console shows: "✅ Form auto-populated successfully"

**Form Fields Populated:**
- [ ] Age: 45
- [ ] Sex: female
- [ ] Heart Rate: 124 bpm
- [ ] BP Systolic: 105 mmHg
- [ ] BP Diastolic: 69 mmHg
- [ ] SpO2: 91%
- [ ] Respiratory Rate: 22 breaths/min
- [ ] Temperature: 37.0°C
- [ ] Chief Complaint: "chest_pain_cardiac" selected
- [ ] Pain Score: 8
- [ ] Medical History: (empty or minimal)

**Visual Indicators:**
- [ ] Age group badge does NOT show (adult patient)
- [ ] Vital ranges show adult ranges (HR: 60-100 bpm, etc.)
- [ ] Data completeness bar shows high percentage (85-95%)
- [ ] Form scrolls to top automatically

### 4. Patient Selection - Pediatric Infant (Patient #2)
Actions:
1. Select "2. Maria Garcia..." from dropdown

Expected Results:
- [ ] Console shows: "📋 Auto-populating form for patient: Maria Garcia"
- [ ] Console shows: "ℹ️ Special case: PEDIATRIC"

**Pediatric-Specific Features:**
- [ ] Age group badge visible: "👶 PEDIATRIC PATIENT (Infant 0-2)"
- [ ] Badge has blue background (#e3f2fd)
- [ ] Badge has blue text (#1976d2)
- [ ] Vital ranges update to infant ranges:
  - [ ] HR: "Normal infant_0_2: 100-160 bpm"
  - [ ] RR: "Normal: 30-60 breaths/min"
  - [ ] BP Sys: "Normal: 70-100 mmHg"
  - [ ] BP Dia: "Normal: 40-60 mmHg"

**Form Values:**
- [ ] Age: 1
- [ ] HR: 170 (outside infant normal range - should show warning)
- [ ] BP Systolic: 69 (slightly below range)
- [ ] SpO2: 92%
- [ ] Chief Complaint: "sepsis_suspected"

### 5. Patient Selection - Geriatric (Patient #4)
Actions:
1. Select "4. Priya Sharma..." from dropdown

Expected Results:
**Geriatric-Specific Features:**
- [ ] Age group badge visible: "👴 GERIATRIC PATIENT (65+)"
- [ ] Badge has purple background (#f3e5f5)
- [ ] Badge has purple text (#7b1fa2)
- [ ] Vital ranges update to geriatric ranges:
  - [ ] HR: "Normal geriatric_65_plus: 60-100 bpm"
  - [ ] BP Sys: "Normal: 90-140 mmHg"

**Form Values:**
- [ ] Age: 78
- [ ] Chief Complaint: "trauma_head"

### 6. Patient Selection - Zero-History (Patient #6)
Actions:
1. Select a patient with [ZERO-HISTORY] label

Expected Results:
- [ ] Console shows: "ℹ️ Special case: ZERO-HISTORY"
- [ ] Medical History field is empty or minimal
- [ ] Data completeness percentage is lower (70-85%)
- [ ] All other fields populated correctly

### 7. Clear Form
Actions:
1. Select "-- Load Test Patient --" from dropdown

Expected Results:
- [ ] Console shows: "Clearing form"
- [ ] All form fields reset to empty
- [ ] Age group badge disappears
- [ ] Data completeness shows 0%
- [ ] Vital ranges return to default (adult ranges)

### 8. Rapid Switching
Actions:
1. Select Patient #1
2. Select Patient #2
3. Select Patient #10
4. Select Patient #20

Expected Results:
- [ ] Form updates instantly with each selection
- [ ] No lag or freezing
- [ ] Console logs each patient change
- [ ] Age group badges update correctly
- [ ] Vital ranges update correctly

### 9. Error Handling (Optional - If Backend Down)
Actions:
1. Stop backend server
2. Refresh page

Expected Results:
- [ ] Console shows error message
- [ ] Dropdown shows: "Error loading patients"
- [ ] Page does not crash
- [ ] User can still manually enter data

### 10. Browser Compatibility (Test in Multiple Browsers)
Test the same functionality in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (Mac only)

All features should work identically across browsers.

## Final Verification

### Console Output
Expected console messages in order:
```
1. Chart.js version: [version]
2. 🔄 Loading test patients...
3. ✅ Loaded 20 test patients
4. ✅ Populated dropdown with 20 patients
5. (When patient selected) 📋 Auto-populating form for patient: [Name]
6. (For special cases) ℹ️ Special case: [Labels]
7. ✅ Form auto-populated successfully
```

### No Errors
- [ ] No red errors in console
- [ ] No JavaScript exceptions
- [ ] No failed network requests (except if testing error handling)

### User Experience
- [ ] Dropdown is easy to read and navigate
- [ ] Labels help identify special cases at a glance
- [ ] Form population is instant and smooth
- [ ] Data completeness updates in real-time
- [ ] Visual feedback is clear (badges, colors, etc.)

## Pass Criteria

**PASS**: All checkboxes can be checked (or at least 95%)
**FAIL**: Critical functionality missing (no patients load, form doesn't populate, etc.)

## Notes

Record any issues or observations:
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________

## Test Date: [Date]
## Tester: [Name]
## Browser: [Browser Name and Version]
## Result: [ ] PASS  [ ] FAIL

---

## Automated Test Results (from test_task_5_5.py)

```
✅ Status Code: 200
✅ Patient Count: 20
✅ Patients Loaded: 20
✅ PASS: Total patients = 20
✅ PASS: At least 2 pediatric patients
✅ PASS: At least 2 geriatric patients
✅ PASS: At least 1 ambiguous presentation
✅ PASS: At least 1 zero-history patient
✅ ALL REQUIREMENTS MET
✅ ALL FRONTEND CHECKS PASSED
✅ TASK 5.5 COMPLETE - All tests passed!
```
