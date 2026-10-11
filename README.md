# Belief Stress Test
### AI-Powered Live Classroom Diagnostic Platform

[![Tests](https://img.shields.io/badge/pytest-11%20passed-emerald)](file:///backend/tests)
[![Frontend](https://img.shields.io/badge/frontend-Vite%20%2B%20React%2018%20%2B%20Tailwind-indigo)](file:///frontend)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20SQLAlchemy%202.x-blue)](file:///backend)
[![Roster](https://img.shields.io/badge/roster-45%20Eligible%20Students-green)](file:///backend/app/services/roster.py)

---

## 1. Project Overview

In a typical university classroom of 45 students, professors typically hear responses from only a vocal few. The remaining majority represents a hidden distribution: some understand the concept, some are uncertain, and some confidently hold persistent misconceptions. Ordinary polling tools count votes but do not probe *why* students chose their answers or whether their beliefs withstand targeted scrutiny.

**Belief Stress Test** is a live classroom interaction platform that transforms student responses into actionable pedagogical diagnostics.

### Core Workflow:
$$\text{Question} \longrightarrow \text{Initial Responses} \longrightarrow \text{Reasoning Analysis} \longrightarrow \text{Targeted Challenge} \longrightarrow \text{Revised Responses} \longrightarrow \text{Follow-Up Assessment} \longrightarrow \text{Instructor Insights}$$

---

## 2. Key Features

- **Fixed 45-Student Eligibility Enforcement:** Strictly validates the exact 45 eligible students (`241AI001` through `241AI044` + `231AI007`). Rejects `241AI045` and unapproved IDs.
- **Two-Factor Identity Activation:** Knowing an eligible student ID is insufficient to impersonate someone; students must enter an administrative one-time activation credential (`ACT-XXXXXX`) to activate their account.
- **Privacy-Preserving Response Architecture:**
  - *Participation Records:* Track which students have answered each round (attendance/completion visibility for the professor).
  - *Response Records:* Link only to a session-specific pseudonymous participant identifier (`participant_id`), never student IDs or real names.
  - Student IDs are never transmitted to external LLM providers.
- **Semantic Text Clustering & AI Reasoning Diagnostics:**
  - Groups student explanations using TF-IDF and `MiniBatchKMeans` (`scikit-learn`).
  - Synthesizes mental models and misconception patterns.
  - Automatically proposes targeted challenges (Counterexamples for factual questions, Opposing arguments for subjective questions, Prediction reveals, or Transfer questions).
  - **Human-in-the-Loop:** AI proposals require instructor review and approval before students see them.
- **Before-and-After Belief Transitions Matrix:**
  - Real-time tracking of student position changes (who switched from an incorrect belief to the correct concept, who retained their position).
  - Confidence calibration analysis (1 to 5 scale).
  - Student self-reported explanations of what influenced their decision.
- **Concept Retention Follow-Up Assessment:** Releasing a secondary scenario tests whether students can independently apply the concept.
- **Real-Time Live Updates:** Bi-directional WebSockets push participation updates, round changes, and approvals immediately to professor and student screens.

---

## 3. Technology Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons, QR Code SVG.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, WebSockets, Argon2id, PyJWT, Scikit-learn, NumPy.
- **Database:** SQLite (local dev) / PostgreSQL (production) with strict foreign key constraints and uniqueness constraints.
- **AI Integration:** Google GenAI SDK (`google-genai`) with Gemini 2.5 Flash / Gemini 2.0 Flash, plus an intelligent local `MockAIProvider` for deterministic testing and offline reliability.

---

## 4. Quickstart

### Start the Application (Single Command):
```bash
./start.sh
```

- **Frontend Portal:** [http://localhost:5173](http://localhost:5173)
- **Backend API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Default User Accounts:
- **Professor:** `prof_nash` / `ProfPassword2026!`
- **Administrator:** `admin` / `AdminSecurePass2026!`
- **Students:** See [`COLD_START.md`](file:///COLD_START.md) or run `backend/.venv/bin/python backend/reset_roster_codes.py` to view all 45 activation codes.

---

## 5. Verification & Test Suite

The comprehensive test suite verifies:
1. Role-based access control and cookie/token authentication.
2. Exact 45-student roster boundary checks (`241AI045` rejected).
3. Round-locking and duplicate submission rejection.
4. AI provider challenge generation and text clustering fallbacks.
5. **Full 45-Student Classroom Simulation:** Simulates all 45 students activating accounts, joining a live session, answering Round 1, AI reasoning categorization, professor challenge review & approval, Round 2 revisions, follow-up assessment, and belief transition matrix calculation.

Run all tests:
```bash
backend/.venv/bin/pytest backend/tests -v
```
*Result: 11 passed (100% pass rate).*

---

## 6. Guides & Documentation

- [**Professor Quickstart Guide**](file:///PROFESSOR_GUIDE.md): 3-minute classroom walkthrough.
- [**Cold Start & Deployment Guide**](file:///COLD_START.md): Environment configuration, Gemini API key integration, and Render/Vercel deployment instructions.
