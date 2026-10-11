# Professor Quickstart Guide: Belief Stress Test
## AI-Powered Live Classroom Diagnostic Platform

Welcome! **Belief Stress Test** helps you diagnose hidden student misconceptions during lectures, evaluate student answers and reasoning against your **Instructor Benchmark**, and stress-test student beliefs using targeted Round 2 challenges.

---

## 1. Quick Login
1. Open your browser and navigate to `/login` on your deployed Vercel URL (or `http://localhost:5173/login` locally).
2. Sign in with your Professor credentials (created by the Administrator in `/admin`, or `prof_nash` / `ProfPassword2026!` locally).

---

## 2. Creating a Lecture Session & Adding Multiple Questions

1. On your **Instructor Dashboard** (`/professor`), click **"+ New Session"** and enter your lecture title (e.g., *Game Theory: Nash Equilibrium & Auctions*).
2. Click **"Launch Control"** to open the **Session Overview** (`/professor/sessions/:sessionId`).
3. Click the **QR Code** button to project the 6-character **Join Code** and QR link for your 45 eligible students.
4. Click **"+ Add Question"** to add as many questions as you need for the lecture:
   - **Select Question Type:**
     - **Factual / Technical:** Has an objective reference answer and expected conceptual derivation.
     - **Subjective / Competing Viewpoints:** Explores trade-offs and competing arguments.
     - **Prediction:** Solicits quantitative estimates or categorical forecasts.
     - **Open-Ended Reasoning:** Free-form conceptual derivation or proof.
   - **Choose Answer Input Format:** Multiple Choice Options, Numerical Estimate, or Free-Form Text Response.
   - **Configure Instructor Benchmark:**
     - **Reference / Target Answer (`reference_answer`):** The correct choice, target numerical value, or core thesis.
     - **Expected Reasoning / Conceptual Rubric (`accepted_reasoning`):** The causal mechanism or key trade-offs students should articulate.
5. While a question is in **`DRAFT`** mode, you can edit or delete it at any time.

---

## 3. Running the Diagnostic Workflow for Each Question

Click **"Manage Question & Rounds"** on any question card to open its dedicated control page (`/professor/sessions/:sessionId/questions/:questionId`):

### Step 1: Open Round 1 (Initial Belief)
- Click **"Start Round 1"**.
- Students immediately see the question on their devices and submit their answer, **Confidence Rating (1–5)**, and **written reasoning**.
- Monitor real-time completion across the 45-student roster.

### Step 2: AI Benchmark Evaluation & Challenge Review
- Click **"Analyze & Propose Challenge"**.
- The backend batches all Round 1 responses and uses **Gemini 3.8 Flash** (`gemini-3.8-flash`) to:
  1. Evaluate student answers against your `reference_answer`.
  2. Evaluate student written explanations against your `accepted_reasoning` rubric.
  3. Group students into **Mental-Model / Reasoning Categories** (separating benchmark-aligned reasoning from surface guesses and specific misconceptions).
  4. Propose a targeted Socratic **Round 2 Challenge** (`COUNTEREXAMPLE`, `OPPOSING_ARGUMENTS`, `PREDICTION_REVEAL`, or `TRANSFER_QUESTION`).
- Review or edit the proposed challenge in the modal and click **"Approve & Open Round 2"**.

### Step 3: Round 2 (Belief Stress Test & Revision)
- Students read the approved challenge on their screen and choose whether to **keep** or **revise** their Round 1 answer, updating their confidence and explaining why.
- Watch the live **Belief Transitions Matrix** and **Round 1 vs. Round 2 Distribution Charts** update in real time.

### Step 4: Complete Question & Reveal Benchmark
- Click **"Complete Question"** when Round 2 concludes.
- Completing a question reveals the **Instructor Benchmark** (`reference_answer` and `accepted_reasoning`) on each student's personal review card alongside their Round 1 and Round 2 submissions.
- Switch to the next question in your session using the top question selector bar, or click **"End Session"** on the Session Overview page when your lecture concludes.

---

## Privacy & Academic Integrity Note
- Attendance tracking (`SessionParticipation`) is logically separated from pseudonymous response content (`StudentResponse.participant_id`).
- Students only see their own submissions and the revealed Instructor Benchmark—never class vote distributions during active rounds or another student's identity/responses.
