# Time Display and Clinician ID Fixes
## PatientTriage.ai - August 29, 2026

---

## 🔧 Issues Fixed

### Issue 1: Time Display Not Showing Assessment Deadline
**Problem:** Queue showing "waited time" instead of "time left until assessment deadline"

**Before:**
```
⏱ 15 min    ← How long they've waited (not useful)
```

**After:**
```
⏱ 25 min left   ← Time remaining until assessment deadline ✓
⏱ 3 min left    ← Urgent! Only 3 minutes left ✓
⏱ ⚠️ OVERDUE   ← Past deadline! ✓
```

---

### Issue 2: Governance Showing "SYSTEM" Instead of Clinician Name
**Problem:** Override display showing "Overridden By: SYSTEM" instead of actual clinician ID

**Root Cause:** Backend not saving `clinician_id` field

**Before:**
```
👤 Overridden By: SYSTEM    ← Wrong!
```

**After:**
```
👤 Overridden By: Dr. Jane Smith    ← Correct! ✓
```

---

## ✅ Fix 1: Time Left Display

### Changes in `/Users/divyanshiii/Win/frontend/queue.html`

**Function:** `createPatientCard(patient)`

**New Logic:**
```javascript
// Calculate time LEFT until assessment deadline based on ESI
const maxWaitMinutes = {
    1: 0,    // Immediate
    2: 10,   // 10 minutes
    3: 30,   // 30 minutes
    4: 60,   // 60 minutes
    5: 120   // 120 minutes
};

const timeLeftMinutes = Math.max(0, maxWaitMinutes[esi] - patient.waitMinutes);
const timeLeftHours = Math.floor(timeLeftMinutes / 60);
const timeLeftMins = timeLeftMinutes % 60;

let timeLeftStr;
let timeLeftClass = '';

if (timeLeftMinutes <= 0) {
    timeLeftStr = '⚠️ OVERDUE';
    timeLeftClass = 'overdue';
} else if (timeLeftMinutes < 5) {
    timeLeftStr = `${timeLeftMins} min left`;
    timeLeftClass = 'critical-time';
} else if (timeLeftHours > 0) {
    timeLeftStr = `${timeLeftHours}h ${timeLeftMins}m left`;
} else {
    timeLeftStr = `${timeLeftMins} min left`;
}
```

**Display:**
```html
<div class="wait-time ${timeLeftClass}">⏱ ${timeLeftStr}</div>
```

---

### CSS Enhancements

**Added styles for urgency indicators:**

```css
.wait-time.critical-time {
    color: #d32f2f;
    font-weight: 700;
    animation: pulse 1.5s ease-in-out infinite;
}

.wait-time.overdue {
    color: #c62828;
    font-weight: 700;
    background: #ffebee;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
```

**Visual Effects:**
- **Normal time:** Regular display (e.g., "25 min left")
- **Critical time (< 5 min):** Red text with pulsing animation
- **Overdue:** Red text on pink background

---

## ✅ Fix 2: Clinician ID in Governance View

### Changes in `/Users/divyanshiii/Win/app.py`

#### 1. Updated `OverrideRequest` Model

**Added field:**
```python
class OverrideRequest(BaseModel):
    patient_id: str
    ml_predicted_esi: int
    clinician_final_esi: int
    reason_category: Literal[...]
    reason_text: str
    clinician_id: Optional[str] = Field(None, description="ID or name of clinician")  # ← NEW
    timestamp: Optional[datetime]
```

#### 2. Updated Override Logging

**Function:** `log_clinician_override()`

**Before:**
```python
override_record = {
    "override_id": override_id,
    "patient_id": override_request.patient_id,
    "ml_predicted_esi": ml_esi,
    "clinician_final_esi": clinician_esi,
    "override_direction": override_direction,
    "override_magnitude": override_magnitude,
    "reason_category": override_request.reason_category,
    "reason_text": override_request.reason_text,
    "timestamp": ...
    # Missing clinician_id! ← BUG
}
```

**After:**
```python
override_record = {
    "override_id": override_id,
    "patient_id": override_request.patient_id,
    "ml_predicted_esi": ml_esi,
    "clinician_final_esi": clinician_esi,
    "override_direction": override_direction,
    "override_magnitude": override_magnitude,
    "reason_category": override_request.reason_category,
    "reason_text": override_request.reason_text,
    "clinician_id": override_request.clinician_id,  # ← FIXED
    "timestamp": ...
}
```

---

## 📊 Examples

### Example 1: Time Display Scenarios

| Patient | ESI | Waited | Max Wait | Time Left | Display | Color |
|---------|-----|--------|----------|-----------|---------|-------|
| Patient A | 1 | 0 min | 0 min | 0 min | "⚠️ OVERDUE" | Red bg |
| Patient B | 2 | 3 min | 10 min | 7 min | "7 min left" | Normal |
| Patient C | 2 | 8 min | 10 min | 2 min | "2 min left" | Red pulse |
| Patient D | 2 | 12 min | 10 min | 0 min | "⚠️ OVERDUE" | Red bg |
| Patient E | 3 | 5 min | 30 min | 25 min | "25 min left" | Normal |
| Patient F | 4 | 45 min | 60 min | 15 min | "15 min left" | Normal |
| Patient G | 5 | 60 min | 120 min | 1h 0m | "1h 0m left" | Normal |

---

### Example 2: Cardiac Arrest Scenario (Your Example)

**Setup:**
- Patient A: ESI 2, Cardiac arrest, waited 1 min
- Patient B: ESI 2, Something else, waited 5 min

**Calculation:**
- Patient A: 10 - 1 = **9 min left**
- Patient B: 10 - 5 = **5 min left**

**Display:**
```
Queue:
┌────────────────────────────┐
│ Patient B - ESI 2          │ ← 5 min left (less time, higher priority)
│ ⏱ 5 min left              │
├────────────────────────────┤
│ Patient A - ESI 2          │ ← 9 min left
│ ⏱ 9 min left              │
└────────────────────────────┘
```

**Sorting:** Patient B comes first because 5 < 9 ✓

---

### Example 3: Clinician ID Display

**Override Flow:**
1. User enters clinician ID: "Dr. Jane Smith"
2. Frontend sends to backend with `clinician_id: "Dr. Jane Smith"`
3. Backend saves to `data/overrides.json`:
   ```json
   {
     "override_id": "override_abc123",
     "patient_id": "patient_xyz",
     "ml_predicted_esi": 3,
     "clinician_final_esi": 5,
     "override_direction": "de-escalation",
     "override_magnitude": 2,
     "reason_category": "clinical_judgment",
     "reason_text": "Just a fever, nothing serious",
     "clinician_id": "Dr. Jane Smith",  ← SAVED
     "timestamp": "2026-08-29T10:30:00"
   }
   ```
4. Governance view fetches overrides
5. Displays: **"👤 Overridden By: Dr. Jane Smith"** ✓

---

## 🧪 Testing

### Test 1: Time Display
1. Add patient with ESI 2
2. Check time display immediately
3. **Expected:** "10 min left" ✓

4. Wait 3 minutes (or simulate)
5. Refresh queue
6. **Expected:** "7 min left" ✓

7. Wait until 8 minutes total
8. Refresh queue
9. **Expected:** "2 min left" in RED with pulse animation ✓

10. Wait past 10 minutes
11. Refresh queue
12. **Expected:** "⚠️ OVERDUE" with red background ✓

---

### Test 2: Sorting by Time Left
1. Add 3 patients, all ESI 3:
   - Patient A: Just added (30 min left)
   - Patient B: Waited 10 min (20 min left)
   - Patient C: Waited 20 min (10 min left)

2. Check queue order
3. **Expected Order:**
   - Patient C (10 min left) ← Top
   - Patient B (20 min left)
   - Patient A (30 min left) ← Bottom

✓ Patients with less time left appear first

---

### Test 3: Clinician ID in Governance
1. Override a patient:
   - ML predicts ESI 3
   - Override to ESI 5
   - Enter clinician ID: "Dr. Sarah Johnson"
   - Submit

2. Go to Governance View
3. Find the overridden patient (orange background)
4. Look at override section

**Expected:**
```
Reason Category: CLINICAL JUDGMENT
"Patient seems fine, just minor symptoms"
─────────────────────────────────────────
👤 Overridden By: Dr. Sarah Johnson
```

✓ Shows actual clinician name, not "SYSTEM"

---

### Test 4: No Clinician ID Provided
1. Override a patient
2. Leave clinician ID field empty
3. Submit

**Expected in Governance:**
```
👤 Overridden By: SYSTEM
```

✓ Fallback to "SYSTEM" if no ID provided

---

## 🔄 Backend Restart Required

**IMPORTANT:** Backend must be restarted for clinician_id fix to take effect!

```bash
# Stop current backend (Ctrl+C)
# Restart:
python app.py
```

**Why?** The `OverrideRequest` model changed - added `clinician_id` field

---

## ✅ Summary

### Frontend Changes (`queue.html`)
- ✅ Calculate time LEFT until deadline (not time waited)
- ✅ Display urgency with colors and animations
- ✅ Sort by time left within same ESI

### Backend Changes (`app.py`)
- ✅ Added `clinician_id` to `OverrideRequest` model
- ✅ Save `clinician_id` in override records
- ✅ Return `clinician_id` in override API responses

### Visual Changes
- ✅ Normal time: Regular display
- ✅ Critical time (< 5 min): Red with pulse
- ✅ Overdue: Red with background
- ✅ Clinician ID: Displayed prominently in governance

---

## 🎯 Verification Checklist

- [ ] Hard refresh frontend (Cmd+Shift+R)
- [ ] Restart backend (`python app.py`)
- [ ] Add new patients - check time displays correctly
- [ ] Override with clinician ID - check governance shows name
- [ ] Wait/simulate time passing - check time updates and colors
- [ ] Check sorting - patients with less time appear first within ESI
- [ ] Check overdue display - red background appears

---

**Date:** August 29, 2026  
**Files Modified:**  
- `/Users/divyanshiii/Win/frontend/queue.html` (time display + CSS)  
- `/Users/divyanshiii/Win/app.py` (clinician_id field)  
**Status:** ✅ COMPLETE - RESTART BACKEND REQUIRED
