# Professor Quickstart Guide: Belief Stress Test
## AI-Powered Live Classroom Diagnostic Platform

Welcome! **Belief Stress Test** is designed to help you quickly diagnose hidden student misconceptions during lectures and stress-test student reasoning using targeted counterexamples and challenges.

---

## 1. Quick Login
1. Open your browser and navigate to: **`http://localhost:5173/login`** (or your deployed URL).
2. Enter your credentials:
   - **Username:** `prof_nash`
   - **Password:** `ProfPassword2026!`

---

## 2. Launching a Classroom Session (Under 60 Seconds)

1. On your **Instructor Dashboard**, click **"+ New Session"**.
2. Enter a lecture topic (e.g., *Second-Price Auction Theory* or *Market Equilibrium*).
3. The platform will automatically generate a **unique 6-character Join Code** (e.g. `K8M2W9`) and an interactive **QR Code**.
4. Click the **QR Code icon** to project the full-screen QR code onto the lecture hall screen for students to scan with their phones.

---

## 3. The 5-Step Classroom Diagnostic Workflow

### Step 1: Set Up the Question
- Enter your question prompt.
- Select the question type:
  - **Factual / Technical:** Has a reference answer; targets misconceptions.
  - **Subjective:** Explores trade-offs; targets one-sided biases.
  - **Prediction:** Solicits group forecasts.
  - **Open-Ended Reasoning:** Conceptual inquiry.
- Add choices (e.g., *Above valuation*, *Equal to valuation*, *Below valuation*).
- Click **Save Question**.

### Step 2: Open Round 1
- Click **"Open Round 1"**.
- Students submit their choice, a **Confidence Rating (1 to 5)**, and a **short explanation** of their reasoning.
- Watch your **Classroom Roster panel**:
  - Live counter tracks all **45 eligible students** (`241AI001`–`241AI044` & `231AI007`).
  - See in real-time who has answered and who is pending.

### Step 3: AI Reasoning Analysis & Challenge Review
- Once submissions slow down, click **"Close & Analyze Round 1"**.
- The system automatically:
  1. Anonymizes explanations (strips all student identities).
  2. Clusters explanations into semantic mental models using machine learning.
  3. Uses an LLM to propose a **targeted challenge / counterexample** targeting the observed misconception.
- A review drawer pops up showing:
  - **Proposed Challenge text** (which students will see in Round 2).
  - **Targeted Misconception pattern**.
  - **Learning Objective**.
- You can freely edit the challenge text or click **"Approve & Open Round 2"**.

### Step 4: Round 2 Revisions
- Students immediately see your approved challenge on their phones.
- They decide whether to **retain** or **switch** their answer and report what influenced their decision.
- Your dashboard displays the live **Belief Transitions Matrix**:
  - Exactly how many students switched from an incorrect belief to the correct concept.
  - Average changes in confidence.
  - Real, anonymized student quotes explaining their shifts.

### Step 5: Follow-Up Assessment & Wrap Up
- Click **"Proceed to Follow-Up Question"**.
- Ask a quick transfer question to test if students can apply the concept independently in an adjacent scenario.
- Review the summary and click **"Complete Session"**.

---

## Privacy Note
- Student identities are strictly isolated from response content. You can see *who* has submitted for attendance, but student answers and explanations are decoupled via session pseudonyms.
