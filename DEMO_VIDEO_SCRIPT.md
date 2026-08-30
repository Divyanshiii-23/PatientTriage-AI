# Demo Video Script - PatientTriage.ai
## Complete Narration Script for 7-Minute Demo

---

## 🎬 Video Structure

**Total Duration:** 7 minutes  
**Format:** Screen recording with voiceover  
**Resolution:** 1920x1080 (1080p)  
**Frame Rate:** 30 fps

---

## 📝 Full Script with Timing

### SEGMENT 1: Introduction (0:00 - 0:30)

**Visual:** Title slide or README on GitHub

**Narration:**
> "Hello! I'm presenting PatientTriage.ai - an ML-powered Emergency Department triage system.
>
> This prototype demonstrates how machine learning can assist triage nurses in assessing patient acuity using the Emergency Severity Index scale, from ESI 1 - life-threatening - to ESI 5 - non-urgent.
>
> The system provides ESI predictions with multi-dimensional confidence scores, safety validation, and explainable AI to support clinical decision-making.
>
> Let's see it in action."

**Action:**
- Show project title
- Briefly flash key features list
- Transition to live demo

---

### SEGMENT 2: Patient Intake & Normal Flow (0:30 - 2:00)

**Visual:** Open `index.html` in browser

**Narration:**
> "Here's the patient intake interface. A triage nurse enters patient demographics, vital signs, and chief complaint.
>
> Let me load a test patient to demonstrate."

**Action:**
- Click "Load Test Patient" dropdown
- Select "Moderate Injury - 35yo Male"
- Pause briefly to show auto-populated form

**Narration:**
> "The form automatically populates with realistic patient data. Notice the data completeness indicator at the top - currently 87%.
>
> We have demographics: 35-year-old male.
>
> Vital signs: heart rate 88, blood pressure 125 over 80, oxygen saturation 98%, respiratory rate 16, temperature 37.
>
> Chief complaint: moderate injury from a fall. Arrived by walk-in. Mental status: alert. Pain score: 4 out of 10.
>
> Now, let's get the AI triage recommendation."

**Action:**
- Scroll through form (don't go too fast)
- Click "Get AI Triage Recommendation" button
- Wait for results to load (~100ms)

**Narration:**
> "The system returns comprehensive results instantly.
>
> ESI prediction: Level 3 - Urgent. This means the patient should be seen within 30 minutes.
>
> The probability distribution chart shows the model's confidence across all five ESI levels. Here, it's most confident about ESI 3 at 50%.
>
> Confidence breakdown shows four dimensions:
> - Model certainty: 75% - the prediction is fairly confident
> - Data completeness: 87% - most fields are present
> - Clinical consistency: 100% - vitals align with symptoms
> - Pattern recognition: 100% - typical presentation
>
> Overall confidence: MEDIUM at 77%. This is reasonable for an ambiguous moderate injury.
>
> The safety flag is YELLOW - recommending clinical validation, which is appropriate.
>
> Most importantly, we see explainability. The SHAP chart shows which factors influenced the prediction. Chief complaint 'moderate injury' increased urgency by 40%. Vital signs were mostly normal, decreasing urgency slightly. Arrival mode 'walk-in' suggests lower acuity.
>
> This natural language explanation helps the nurse understand the model's reasoning."

**Action:**
- Point cursor to each section as you narrate
- Hover over ESI badge
- Point to confidence scores
- Highlight SHAP explanation

---

### SEGMENT 3: Critical Patient with RED Flag (2:00 - 3:30)

**Visual:** Clear previous results, load new patient

**Narration:**
> "Now let's see how the system handles a critical case."

**Action:**
- Scroll to top, click "Load Test Patient"
- Select "Cardiac Arrest - 68yo Male"
- Briefly show form

**Narration:**
> "This is a 68-year-old male with cardiac arrest. Arrived by ambulance. Notice the vital signs: oxygen saturation is dangerously low at 85%.
>
> Let's get the prediction."

**Action:**
- Click "Get AI Triage Recommendation"
- Wait for results - notice pulsing red border

**Narration:**
> "The system immediately flags this as ESI 1 - life-threatening. Notice the pulsing red border around the entire results panel - this draws immediate attention.
>
> At the top, a prominent RED safety banner alerts: CRITICAL ALERT - Immediate Review Required.
>
> Safety criteria triggered include: oxygen saturation below 90%, age over 65 with cardiac chief complaint.
>
> The safety validation layer has overridden any lower urgency prediction to force ESI 1. This patient needs immediate resuscitation - zero minutes wait time.
>
> The explanation shows why: Chief complaint 'cardiac arrest' increases urgency by 95%. Low oxygen saturation is a critical factor. Age 68 increases risk for cardiac presentations.
>
> This demonstrates the multi-layered safety approach: machine learning plus rule-based validation plus visual alerts."

**Action:**
- Point to pulsing border
- Point to RED banner
- Point to safety criteria
- Point to ESI 1 badge
- Highlight SHAP explanation

---

### SEGMENT 4: Clinician Override Workflow (3:30 - 5:00)

**Visual:** Still on same results or load a new patient

**Narration:**
> "Clinicians always retain full decision authority. They can override any recommendation.
>
> Suppose the nurse disagrees with this assessment. She clicks 'Override Recommendation'."

**Action:**
- Click "Override Recommendation" button
- Override dialog appears

**Narration:**
> "The override dialog opens. She selects her clinical ESI assessment - let's say ESI 2 instead of the predicted ESI 3.
>
> She chooses a reason category - in this case, 'Clinical Judgment'.
>
> Then provides detailed justification: 'Patient appears more distressed and anxious than vitals suggest. Sweating profusely and pale. Escalating as a precaution.'
>
> Critically, for accountability, she enters her clinician ID: Dr. Sarah Johnson.
>
> Now she submits the override."

**Action:**
- Select ESI 2 from dropdown
- Select "Clinical Judgment" from reason dropdown
- Type the reason text (can speed up video slightly here)
- Type "Dr. Sarah Johnson" in clinician ID field
- Click "Submit Override"
- Show success alert

**Narration:**
> "The system confirms: override logged successfully. The patient is now added to the queue with ESI 2 - the clinician's assessment, not the model's.
>
> This override is logged for quality improvement and model retraining.
>
> Let's verify this in the governance view."

**Action:**
- Close alert
- Switch to `queue.html` browser tab (or open it)
- Click "Governance & Audit" tab

**Narration:**
> "Here's the governance view - designed for quality assurance and compliance.
>
> At the top, we see accountability metrics: total patients, escalation rate, override rate, and safety flags triggered.
>
> Scrolling down, we find our overridden patient - notice the orange background indicating an override.
>
> The timeline shows the complete audit trail:
> - Patient arrived at 10:15 AM
> - ML assessed as ESI 3 with 77% confidence
> - Dr. Sarah Johnson overrode to ESI 2 just now
>
> The override details are fully transparent:
> - Direction: ESCALATION from ESI 3 to ESI 2
> - Magnitude: 1 level increase
> - Reason category: Clinical Judgment
> - Detailed justification is displayed
> - Most importantly, clinician accountability: 'Overridden By: Dr. Sarah Johnson'
>
> This complete audit trail supports DPDPA 2023 compliance and enables model improvement."

**Action:**
- Point to accountability cards
- Scroll to find overridden patient (orange)
- Point to timeline elements
- Point to clinician ID display
- Hover over override details

---

### SEGMENT 5: Clinical Queue Management (5:00 - 6:00)

**Visual:** Switch to "Clinical Queue" tab

**Narration:**
> "After triage, patients enter the clinical queue. This is the view nurses use to prioritize care.
>
> Patients are automatically sorted by urgency: ESI 1 at the top, ESI 5 at the bottom.
>
> But within each ESI level, patients are further sorted by time left until their assessment deadline. This ensures the most time-critical patients within each urgency category appear first.
>
> For example, this ESI 2 patient has only 5 minutes left until the 10-minute deadline. They appear before another ESI 2 patient who has 8 minutes left.
>
> Notice the time display: it shows time REMAINING, not time elapsed. '15 min left' means 15 minutes until assessment deadline.
>
> When time is critical - under 5 minutes - the display turns red and pulses to draw attention.
>
> When a patient is overdue, it displays 'OVERDUE' with a red background.
>
> Each patient card shows their ESI badge - color-coded for quick recognition - demographics, chief complaint, and wait time.
>
> Nurses can search in real-time."

**Action:**
- Point to patient cards in sorted order
- Hover over time left displays
- Point to a critical time (red, pulsing) if available
- Type in search box - show filtering
- Clear search

**Narration:**
> "When a patient is seen and assigned a bed, nurses can remove them from the queue. The count updates immediately."

**Action:**
- Click on a patient card to select
- Click "Remove from Queue" button
- Show queue count decrease

---

### SEGMENT 6: Closing & Summary (6:00 - 7:00)

**Visual:** Return to overview or show GitHub README

**Narration:**
> "PatientTriage.ai addresses key real-world complexities in emergency triage:
>
> Ambiguous presentations: The system transparently shows when it's uncertain and recommends validation.
>
> Age-specific thresholds: Pediatric, adult, and geriatric patients are processed with appropriate vital sign ranges.
>
> Data quality: The confidence scoring reflects completeness and consistency, not just model certainty.
>
> Safety first: Rule-based validation catches high-risk cases and overrides unsafe predictions.
>
> Explainability: SHAP values provide natural language explanations in seconds, crucial for time-pressured decisions.
>
> Clinical accountability: Every override is logged with clinician identification for quality improvement.
>
> Full audit trail: The governance view ensures transparency and supports compliance with data protection regulations like DPDPA 2023.
>
> The technology stack includes FastAPI for the backend, CatBoost for ESI classification, SHAP for explainability, and a responsive HTML/CSS/JavaScript frontend.
>
> Complete documentation, automated tests, and 20 diverse test patient scenarios are included.
>
> This is a demonstration prototype trained on synthetic data - not for clinical use. But it illustrates how ML can augment clinical decision-making while maintaining human oversight.
>
> The full code, documentation, and setup instructions are available on GitHub.
>
> Thank you for watching!"

**Action:**
- Show GitHub repository page
- Briefly scroll through README
- Show repository structure
- End with project logo or title screen

---

## 🎥 Recording Tips

### Before Recording

1. **Close unnecessary applications** - clean desktop
2. **Hide bookmarks bar** in browser
3. **Set browser zoom** to 100% or 110% for readability
4. **Test microphone** - clear audio is critical
5. **Rehearse** - practice the script at least once
6. **Prepare test data** - ensure all test patients load correctly
7. **Backend running** - start uvicorn before recording

### During Recording

1. **Speak clearly** and at moderate pace
2. **Pause 2 seconds** between major actions
3. **Move cursor deliberately** - highlight important elements
4. **Don't rush** - better to be slow and clear
5. **If you make a mistake** - pause, then restart that segment (edit later)
6. **Keep energy up** - enthusiasm is engaging

### Recording Settings

**QuickTime (macOS):**
- File → New Screen Recording
- Options → Show Mouse Clicks: Yes
- Options → Microphone: Built-in or external
- Record full screen or select area

**OBS Studio (All platforms):**
- Settings → Video: 1920x1080, 30 FPS
- Settings → Output: MP4, High Quality, x264
- Sources → Display Capture
- Audio: Desktop Audio + Microphone

### After Recording

1. **Trim beginning/end** - remove setup/cleanup
2. **Cut out mistakes** - seamless transitions
3. **Add title card** - 5 seconds at start: "PatientTriage.ai Demo"
4. **Add end card** - 5 seconds at end: "GitHub: github.com/YOUR_USERNAME/PatientTriage-AI"
5. **Add captions** (optional but helpful)
6. **Export as MP4** - H.264, 1080p, 30fps
7. **Compress if > 100MB** (GitHub limit)

---

## 📝 Narration Notes

### Key Phrases to Use

✅ **Do say:**
- "ML-powered" (not "AI-powered" alone)
- "Emergency Severity Index" or "ESI"
- "Triage nurse"
- "Clinical decision support"
- "Explainable AI" or "SHAP explanations"
- "Multi-dimensional confidence"
- "Safety validation layer"
- "Clinician accountability"
- "Audit trail"
- "Demonstration prototype"

❌ **Don't say:**
- "Artificial Intelligence diagnoses..." (implies clinical use)
- "This will replace doctors/nurses"
- "100% accurate"
- "Production-ready for hospitals" (it's a prototype)
- Overly technical jargon (entropy, gradient boosting internals)

### Tone Guidelines

- **Professional** but conversational
- **Confident** but not overreaching
- **Clear** explanations without condescension
- **Enthusiastic** about the technology
- **Honest** about limitations

---

## ✅ Pre-Recording Checklist

**Environment:**
- [ ] Backend server running (`uvicorn app:app --reload`)
- [ ] Browser tabs ready (index.html, queue.html)
- [ ] Test patients loading correctly
- [ ] Desktop clean (no sensitive data visible)
- [ ] Notifications disabled

**Technical:**
- [ ] Screen resolution: 1920x1080
- [ ] Browser zoom: 100-110%
- [ ] Microphone tested and levels good
- [ ] Recording software configured correctly
- [ ] Storage space available (at least 2GB)

**Content:**
- [ ] Script reviewed and rehearsed
- [ ] Demo flow practiced
- [ ] Timing checked (should be 6-8 minutes)
- [ ] All features to demonstrate identified

**Backup Plan:**
- [ ] Record in segments if full take is difficult
- [ ] Can edit segments together
- [ ] Have script printed or on second screen

---

## 🎬 Alternative: Segment Recording

If recording all at once is difficult, record in segments:

**Segment Files:**
1. `intro.mp4` - Introduction (0:30)
2. `normal_patient.mp4` - Normal flow (1:30)
3. `critical_patient.mp4` - RED flag case (1:30)
4. `override.mp4` - Override workflow (1:30)
5. `queue.mp4` - Queue management (1:00)
6. `conclusion.mp4` - Closing (1:00)

**Then merge using FFmpeg:**
```bash
# Create file list
echo "file 'intro.mp4'" > concat.txt
echo "file 'normal_patient.mp4'" >> concat.txt
echo "file 'critical_patient.mp4'" >> concat.txt
echo "file 'override.mp4'" >> concat.txt
echo "file 'queue.mp4'" >> concat.txt
echo "file 'conclusion.mp4'" >> concat.txt

# Concatenate
ffmpeg -f concat -safe 0 -i concat.txt -c copy demo_video.mp4
```

---

## 📊 Success Criteria

**Your demo video is ready when:**

- [ ] Duration: 5-8 minutes
- [ ] All 6 segments covered
- [ ] Audio is clear and professional
- [ ] No mistakes or stuttering
- [ ] All features demonstrated
- [ ] Visuals are smooth (no lag)
- [ ] File size: <100MB (or hosted on YouTube)
- [ ] Format: MP4, 1080p, 30fps
- [ ] Saved as: `docs/demo_video.mp4`

---

## 🚀 Ready to Record!

Follow this script, speak clearly, and you'll create a professional demo video that showcases all the hard work you've put into PatientTriage.ai.

**Good luck! You've got this! 🎥**

---

**Script Version:** 1.0  
**Last Updated:** August 29, 2026  
**Estimated Recording Time:** 10-15 minutes (including retakes)  
**Final Video Length:** 7 minutes
