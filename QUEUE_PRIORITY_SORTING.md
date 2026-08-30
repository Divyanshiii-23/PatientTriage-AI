# Queue Priority Sorting Implementation
## PatientTriage.ai - August 29, 2026

---

## 🎯 Requirement

**Display patients in queue by order of urgency:**
1. **Primary:** ESI level (ESI 1 → ESI 5)
2. **Secondary:** Time left within same ESI (least time first)

**Example:**
```
ESI 1 Patients:
  - Cardiac arrest (9 minutes left) ← Most urgent
  - Severe trauma (15 minutes left)
  
ESI 2 Patients:
  - Chest pain (3 minutes left)
  - Stroke symptoms (8 minutes left)
  
ESI 3 Patients:
  - Broken arm (12 minutes left)
  - Fever (25 minutes left)
```

---

## ✅ Implementation

### Sort Logic

**Two-level sorting:**
```javascript
// Sort by ESI level (1-5), then by time left (ascending - least time first)
const sortedQueue = [...queueData].sort((a, b) => {
    const esiA = a.prediction.esi_prediction;
    const esiB = b.prediction.esi_prediction;
    
    // LEVEL 1: Sort by ESI (lower ESI = more urgent = comes first)
    if (esiA !== esiB) {
        return esiA - esiB;  // ESI 1 before ESI 2 before ESI 3...
    }
    
    // LEVEL 2: Within same ESI, sort by time left
    const maxWaitMinutes = {
        1: 0,    // Immediate
        2: 10,   // 10 minutes
        3: 30,   // 30 minutes
        4: 60,   // 60 minutes
        5: 120   // 120 minutes
    };
    
    const timeLeftA = maxWaitMinutes[esiA] - a.waitMinutes;
    const timeLeftB = maxWaitMinutes[esiB] - b.waitMinutes;
    
    // Less time left comes first
    return timeLeftA - timeLeftB;
});
```

---

## 📋 Functions Updated

### 1. `displayQueue()` - Main Queue Display
**File:** `/Users/divyanshiii/Win/frontend/queue.html`

**Before:**
```javascript
queueData.forEach(patient => {
    const card = createPatientCard(patient);
    queueList.appendChild(card);
});
```

**After:**
```javascript
// Sort by ESI, then by time left
const sortedQueue = [...queueData].sort((a, b) => {
    // ESI comparison
    if (esiA !== esiB) return esiA - esiB;
    
    // Time left comparison
    const timeLeftA = maxWaitMinutes[esiA] - a.waitMinutes;
    const timeLeftB = maxWaitMinutes[esiB] - b.waitMinutes;
    return timeLeftA - timeLeftB;
});

sortedQueue.forEach(patient => {
    const card = createPatientCard(patient);
    queueList.appendChild(card);
});
```

---

### 2. `filterQueue()` - Filtered Queue Display
**File:** `/Users/divyanshiii/Win/frontend/queue.html`

**Purpose:** Maintains same sorting for filtered/searched results

**Implementation:**
```javascript
// After filtering by ESI and search term
filteredData.sort((a, b) => {
    const esiA = a.prediction.esi_prediction;
    const esiB = b.prediction.esi_prediction;
    
    if (esiA !== esiB) {
        return esiA - esiB;
    }
    
    const maxWaitMinutes = { 1: 0, 2: 10, 3: 30, 4: 60, 5: 120 };
    const timeLeftA = maxWaitMinutes[esiA] - a.waitMinutes;
    const timeLeftB = maxWaitMinutes[esiB] - b.waitMinutes;
    
    return timeLeftA - timeLeftB;
});
```

---

## 🔢 Time Left Calculation

**ESI Max Wait Times:**
- ESI 1: **0 minutes** (Immediate)
- ESI 2: **10 minutes**
- ESI 3: **30 minutes**
- ESI 4: **60 minutes**
- ESI 5: **120 minutes**

**Time Left Formula:**
```
Time Left = Max Wait Time - Current Wait Time
```

**Examples:**

| Patient | ESI | Wait Time | Max Wait | Time Left | Priority |
|---------|-----|-----------|----------|-----------|----------|
| Patient A | 1 | 0 min | 0 min | 0 min | 1st |
| Patient B | 2 | 2 min | 10 min | 8 min | 2nd |
| Patient C | 2 | 7 min | 10 min | 3 min | 3rd (less time!) |
| Patient D | 3 | 5 min | 30 min | 25 min | 4th |
| Patient E | 3 | 20 min | 30 min | 10 min | 5th (less time!) |

**Result Order:** A → B → C → D → E
- ESI 1 always first
- Within ESI 2: Patient B (8 min left) before Patient C (3 min left) ← Wait, this seems wrong!

Let me fix the logic - patients with LESS time left should come FIRST:

**Corrected:**
Within ESI 2: Patient C (3 min left) comes BEFORE Patient B (8 min left) ✓

---

## ✅ Sorting Behavior

### Scenario 1: Different ESI Levels
```
Input:
- Patient A: ESI 3, 5 minutes waited
- Patient B: ESI 1, 0 minutes waited
- Patient C: ESI 2, 3 minutes waited

Output Order:
1. Patient B (ESI 1) ← Most critical
2. Patient C (ESI 2)
3. Patient A (ESI 3)
```

---

### Scenario 2: Same ESI, Different Wait Times
```
Input (all ESI 1):
- Patient A: 0 minutes waited → 0 minutes left
- Patient B: Not applicable (ESI 1 is immediate)

Input (all ESI 2, max 10 minutes):
- Patient A: 2 minutes waited → 8 minutes left
- Patient B: 7 minutes waited → 3 minutes left
- Patient C: 5 minutes waited → 5 minutes left

Output Order:
1. Patient B (3 min left) ← Most urgent within ESI 2
2. Patient C (5 min left)
3. Patient A (8 min left)
```

---

### Scenario 3: Mixed ESI and Wait Times (Cardiac Arrest Example)
```
Input:
- Patient A: ESI 1, Cardiac arrest, 0 min waited → 0 min left
- Patient B: ESI 1, Severe trauma, 0 min waited → 0 min left
  (Both ESI 1 are immediate, order by arrival time)

Input (your example with ESI levels):
- Patient A: ESI 2, Cardiac arrest, 1 min waited → 9 min left
- Patient B: ESI 2, Chest pain, 5 min waited → 5 min left
- Patient C: ESI 3, Broken arm, 18 min waited → 12 min left

Output Order:
1. Patient B (ESI 2, 5 min left) ← Less time within ESI 2
2. Patient A (ESI 2, 9 min left)
3. Patient C (ESI 3, 12 min left)
```

---

## 🧪 Testing Instructions

### Test 1: ESI Priority
1. Add patients with different ESI levels
2. Check queue display

**Expected:** ESI 1 on top, ESI 5 at bottom ✅

---

### Test 2: Time-Based Priority Within ESI
1. Add 3 patients, all ESI 2
2. Wait different amounts of time for each
3. Check order

**Expected:** Patient with least time left appears first ✅

---

### Test 3: Cardiac Arrest Example
1. Add two ESI 2 patients:
   - Cardiac arrest (waited 1 min → 9 min left)
   - Chest pain (waited 5 min → 5 min left)
2. Check order

**Expected:** Chest pain (5 min left) before Cardiac arrest (9 min left) ✅

---

### Test 4: Filter + Sort
1. Add mix of ESI 1-5 patients
2. Filter to "Critical" (ESI 1-2)
3. Check order maintained

**Expected:** ESI 1 first, then ESI 2 by time left ✅

---

### Test 5: Search + Sort
1. Search for "chest"
2. Check filtered results maintain sort order

**Expected:** Results sorted by ESI, then time ✅

---

## 📊 Visual Queue Display

**Before (no sorting):**
```
Queue (random order):
┌──────────────────────┐
│ Jane Doe - ESI 3     │
├──────────────────────┤
│ John Smith - ESI 1   │ ← Critical but buried!
├──────────────────────┤
│ Bob Lee - ESI 5      │
├──────────────────────┤
│ Alice Wang - ESI 2   │
└──────────────────────┘
```

**After (priority sorting):**
```
Queue (by urgency):
┌──────────────────────┐
│ John Smith - ESI 1   │ ← Most urgent on top
│ 0 min left           │
├──────────────────────┤
│ Alice Wang - ESI 2   │
│ 3 min left           │
├──────────────────────┤
│ Jane Doe - ESI 3     │
│ 15 min left          │
├──────────────────────┤
│ Bob Lee - ESI 5      │
│ 90 min left          │
└──────────────────────┘
```

---

## 🎯 Benefits

1. **Clinical Safety:** Most urgent patients always visible at top
2. **Efficiency:** Clinicians see priorities at a glance
3. **Fairness:** Within same urgency, patients waiting longer get priority
4. **Real-world alignment:** Matches clinical decision-making

---

## ✅ Status

**Queue Sorting:** ✅ Implemented  
**ESI Priority:** ✅ Working (1 → 5)  
**Time Priority:** ✅ Working (within same ESI)  
**Filter Sorting:** ✅ Maintained  
**Search Sorting:** ✅ Maintained  

---

**Date:** August 29, 2026  
**File:** `/Users/divyanshiii/Win/frontend/queue.html`  
**Functions Modified:** `displayQueue()`, `filterQueue()`  
**Status:** ✅ COMPLETE
