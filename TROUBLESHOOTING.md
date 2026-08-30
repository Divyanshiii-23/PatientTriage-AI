# Troubleshooting Guide

## ✅ ISSUE FIXED: CORS Error

**Problem**: Frontend showing "Error loading patients" and "Error - go for manual triage"

**Root Cause**: CORS (Cross-Origin Resource Sharing) was blocking requests from file:// URLs

**Solution Applied**: Changed CORS configuration to allow all origins

**Status**: ✅ **FIXED** - Server auto-reloaded with new settings

---

## How to Verify It's Working

### Test 1: Check Backend Health
```bash
curl http://localhost:8000/api/v1/patients
```
**Expected**: JSON with 20 patients

### Test 2: Test Prediction API
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
**Expected**: JSON with esi_prediction, confidence_breakdown, safety_flag, etc.

---

## Frontend Testing Steps

### Step 1: Refresh the Frontend
**Important**: Close and reopen your browser tab, or hard refresh:
- **Chrome/Firefox**: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)
- **Safari**: Cmd+Option+R

### Step 2: Check Browser Console
1. Open Developer Tools (F12 or Cmd+Option+I)
2. Go to Console tab
3. Look for errors

**Good signs**:
- "✅ Loaded 20 test patients"
- "✅ Populated dropdown with 20 patients"
- No red error messages

**Bad signs**:
- CORS errors (should be fixed now)
- "Failed to fetch"
- 404 errors

### Step 3: Test Demo Patient Load
1. Click "Load Test Patient" dropdown
2. Select any patient (e.g., "John Smith")
3. Form should auto-fill

**Expected**: All fields populate with patient data

### Step 4: Test Prediction
1. With a patient loaded, click "Get AI Triage Recommendation"
2. Wait 1-2 seconds
3. Results should appear in right panel

**Expected**:
- ESI level badge (1-5)
- Confidence breakdown (4 bars)
- Safety flag (RED/YELLOW/GREEN)
- Explanation text
- Charts visible

---

## Common Issues & Solutions

### Issue 1: "Error loading patients"

**Check**:
```bash
# Is backend running?
curl http://localhost:8000/api/v1/patients
```

**Solution**:
- If not running: `uvicorn app:app --reload --port 8000`
- If running but not responding: Restart backend

### Issue 2: "Error - go for manual triage"

**Causes**:
1. CORS blocking (✅ fixed)
2. Backend not running
3. Wrong port
4. Invalid data format

**Check Backend Logs**:
Look at terminal where uvicorn is running for error messages

**Test API Directly**:
```bash
# Should return prediction
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "sex": "F",
    "hr": 80,
    "bp_systolic": 120,
    "bp_diastolic": 80,
    "spo2": 98,
    "rr": 16,
    "chief_complaint": "Headache",
    "chief_complaint_category": "neurological_headache",
    "arrival_mode": "walk_in",
    "mental_status": "alert",
    "symptoms": [],
    "medical_history": {}
  }'
```

### Issue 3: Charts Not Showing

**Cause**: Chart.js not loading

**Check**: Browser console should show Chart.js loaded
- Look for: `Chart is not defined` error

**Solution**: Check internet connection (Chart.js loads from CDN)

### Issue 4: Dropdown Shows "Error loading patients"

**Cause**: CORS or backend issue

**Solution**:
1. ✅ CORS is now fixed (allow_origins=["*"])
2. Refresh browser page (hard refresh)
3. Check backend is running

---

## Quick Restart Steps

If still having issues, do a full restart:

### 1. Stop Backend
```bash
# Press Ctrl+C in terminal where uvicorn is running
```

### 2. Restart Backend
```bash
cd /Users/divyanshiii/Win
uvicorn app:app --reload --port 8000
```

Wait for:
```
INFO:     Application startup complete.
```

### 3. Reopen Frontend
```bash
# Close browser tab completely
# Reopen:
open frontend/index.html
```

---

## Testing Checklist

After fix, verify:

- [ ] Backend running: `curl http://localhost:8000/api/v1/patients`
- [ ] Frontend opens in browser
- [ ] Browser console shows no CORS errors
- [ ] "Load Test Patient" dropdown populates with 20 patients
- [ ] Can select a patient and form auto-fills
- [ ] Can click "Get AI Triage Recommendation"
- [ ] Results display in right panel with charts
- [ ] No error messages

---

## Current Status

✅ **CORS Fixed**: Backend now allows all origins  
✅ **Backend Running**: http://localhost:8000  
✅ **API Working**: Predictions returning correctly  
⏳ **Action Required**: Refresh your browser page

---

## If Still Not Working

1. **Check backend logs** in terminal
2. **Check browser console** for JavaScript errors
3. **Try different browser** (Chrome recommended)
4. **Verify URL**: Should be file:///Users/divyanshiii/Win/frontend/index.html

---

## Success Indicators

When working correctly, you should see:

**In Browser Console**:
```
🔄 Loading test patients...
✅ Loaded 20 test patients
✅ Populated dropdown with 20 patients
```

**After Submitting Form**:
```
📤 Submitting patient data: {...}
✅ Received prediction: {...}
```

**In Right Panel**:
- Large ESI badge (colored 1-5)
- Probability distribution chart
- 4 confidence bars
- Safety flag banner (if RED/YELLOW)
- Explanation text with chart

---

## Need More Help?

Run these diagnostics:

```bash
# Test backend health
curl http://localhost:8000/api/v1/patients | head -20

# Test prediction
python test_e2e_simple.py

# Check backend logs
# Look at terminal where uvicorn is running
```

**Everything should be working now after the CORS fix and page refresh!** ✅
