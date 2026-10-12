# Project Overview: Class Polling App
### AI-Powered Live Classroom Diagnostic & Polling Platform

- **Live Web Application (Vercel):** [https://polling-app-murex.vercel.app](https://polling-app-murex.vercel.app)
- **Live Backend API (Render):** [https://polling-app-lpjc.onrender.com](https://polling-app-lpjc.onrender.com)

---

## 1. The Pedagogical Problem

In a university lecture hall of 45 students, an instructor typically hears answers from only 2 or 3 vocal students. The remaining students form an invisible distribution:
1. Some understand both the correct answer and the underlying mechanism.
2. Some arrive at the right answer through a **lucky guess or superficial heuristic**.
3. Some confidently hold **persistent conceptual misconceptions**.

Standard classroom polling tools (such as clickers or basic multiple-choice polls) only count votes. They cannot tell the professor *why* students selected an answer, whether students who chose the right option actually used sound reasoning, or whether students' answers hold up when challenged by a counterexample.

---

## 2. What Class Polling App Does

**Class Polling App** is a real-time classroom diagnostic platform that goes beyond vote counting to evaluate **what** students answer, **how confident** they are, **why** they chose that answer, and **how their thinking evolves** when challenged by an AI-generated Socratic follow-up prompt.

### The Core Diagnostic Lifecycle (Per Question)

```text
Question ➔ Round 1 (Initial Answer & Reasoning) ➔ AI Benchmark & Mental-Model Analysis ➔ Targeted Challenge (Round 2 Revision) ➔ Instructor Insight & Benchmark Reveal
```

1. **Question Configuration & Instructor Benchmark:**
   - The professor creates one or more questions inside a classroom session across four supported types:
     - **Factual / Technical:** Objective reference answer + conceptual derivation.
     - **Subjective / Competing Viewpoints:** Multi-stakeholder trade-offs.
     - **Prediction:** Quantitative estimate or outcome forecast.
     - **Open-Ended Reasoning:** Free-form proof or causal explanation.
   - The professor configures the **Answer Format** (*Multiple Choice*, *Numerical Estimate*, or *Free-Form Text*) and sets the **Instructor Benchmark**:
     - `reference_answer`: The target choice, numerical value, or core thesis.
     - `accepted_reasoning`: The expected conceptual mechanism or key trade-offs.

2. **Round 1 — Initial Response Capture:**
   - All eligible students submit:
     - Their **Answer**
     - Their **Confidence Rating (1 to 5)**
     - Their **Written Explanation / Reasoning**
     - An optional **Class Prediction**

3. **Batch AI Evaluation & Mental-Model Grouping (`gemini-3.8-flash`):**
   - Once Round 1 closes, the backend runs a two-stage diagnostic pipeline:
     - **Stage 1 (Local Semantic Clustering):** `scikit-learn` (`TfidfVectorizer` + `MiniBatchKMeans`) clusters student explanations to extract dominant keywords and representative quotes.
     - **Stage 2 (Gemini 3.8 Flash Evaluation):** A single anonymized batch call evaluates each student's answer against `reference_answer` and each student's written reasoning against `accepted_reasoning`.
   - Students are grouped into **2–4 Mental-Model Categories (`ReasoningCategory`)**:
     - *Benchmark-Aligned Reasoning* (`is_misconception: false`)
     - *Correct Answer with Incomplete / Surface Intuition* (`is_misconception: true`)
     - *Divergent / Misconception Models* (`is_misconception: true`)
   - Based on the dominant misconception, the AI generates a targeted **Round 2 Socratic Challenge** (`COUNTEREXAMPLE`, `OPPOSING_ARGUMENTS`, `PREDICTION_REVEAL`, or `TRANSFER_QUESTION`) without giving away the final answer.

4. **Human-in-the-Loop Instructor Review:**
   - The professor reviews the AI-proposed reasoning categories and challenge, edits the challenge prompt if needed, and clicks **Approve & Open Round 2**.

5. **Round 2 — Challenge & Revision:**
   - Students read the approved challenge on their devices and decide whether to **maintain** or **revise** their Round 1 answer, updating their confidence (1–5) and explaining what influenced their decision.

6. **Response Transitions & Benchmark Reveal:**
   - The professor views the real-time **Response Transitions Matrix** (who switched from which option to which option, confidence shifts, and anonymized student quotes).
   - When the professor marks the question **Completed**, the **Instructor Benchmark** (`reference_answer` and `accepted_reasoning`) is revealed on each student's personal review card alongside their Round 1 and Round 2 responses.

---

## 3. Role-Based Architecture & Privacy Model

### Three Strictly Separated Roles
| Role | Capabilities | Restrictions |
| :--- | :--- | :--- |
| **Administrator (`ADMIN`)** | Manages professor accounts, monitors and resets the 45-student roster activations, views system audit logs. | Strictly blocked from accessing classroom sessions or viewing student response content. |
| **Professor (`PROFESSOR`)** | Creates sessions and multi-question queues, controls round states, reviews/edits AI challenges, views aggregate distributions, mental-model groups, and attendance completion. | Cannot modify the eligible student roster or access admin endpoints. |
| **Student (`STUDENT`)** | Activates eligible student ID (`241AI001`–`241AI044`, `231AI007`), joins live sessions, submits Round 1 & Round 2 responses, views personal submission history and revealed Instructor Benchmark. | Cannot see class vote distributions during rounds, cannot view other students' responses, and cannot access professor/admin controls. |

### Privacy-Preserving Separation of Attendance and Content
- **Attendance Tracking (`SessionParticipation`):** Records *whether* a given `student_id` has joined and submitted Round 1 / Round 2 so the professor can track class participation.
- **Anonymous Response Storage (`StudentResponse`):** Keyed only by a session-scoped pseudonymous `participant_id`—never by `student_id` or name.
- **Zero PII Sent to LLM:** Only anonymized answers, explanations, and confidence scores are sent to the Gemini API.

---

## 4. System Architecture & Production Stack

- **Frontend (Vercel):** React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Router v6, `BroadcastChannel` multi-tab auth sync, and automatic cold-start retry + 4-minute keep-warm heartbeat.
- **Backend (Render Native Python 3.12 Runtime):** FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic migrations, Argon2id password hashing, JWT (`Bearer` + `HttpOnly` cookie), and authenticated session-isolated WebSockets (`/ws/sessions/{session_id}`).
- **Database (Neon Managed PostgreSQL):** Enforces foreign keys and unique constraints (`(question_id, participant_id, round_number)`) so duplicate submissions in the same round are impossible at the database level.
- **AI Engine:** Official Google GenAI SDK (`google-genai`) powered by **`gemini-3.8-flash`**, with an automatic fail-safe fallback to `MockAIProvider` if external API connectivity is interrupted.
