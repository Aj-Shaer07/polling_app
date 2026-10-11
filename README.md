# Belief Stress Test
### AI-Powered Live Classroom Diagnostic Platform

[![Live App](https://img.shields.io/badge/Live%20App-Vercel-black)](https://polling-app-murex.vercel.app)
[![Backend API](https://img.shields.io/badge/API%20Health-Render-emerald)](https://polling-app-lpjc.onrender.com/health)
[![Tests](https://img.shields.io/badge/pytest-16%20passed-emerald)](./backend/tests)
[![Frontend](https://img.shields.io/badge/frontend-Vite%20%2B%20React%2018%20%2B%20Tailwind-indigo)](./frontend)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20SQLAlchemy%202.x%20%2B%20Alembic-blue)](./backend)
[![Roster](https://img.shields.io/badge/roster-45%20Eligible%20Students-green)](./backend/app/services/roster.py)

---

## Live Production Deployment

- **Live Frontend (Vercel):** [https://polling-app-murex.vercel.app](https://polling-app-murex.vercel.app)
- **Live Backend API (Render):** [https://polling-app-lpjc.onrender.com](https://polling-app-lpjc.onrender.com)
- **Live Health Check:** [https://polling-app-lpjc.onrender.com/health](https://polling-app-lpjc.onrender.com/health)

---

## 1. Project Overview

In a typical university classroom of 45 students, professors hear responses from only a vocal few. The remaining majority represents a hidden distribution: some understand the concept, some are uncertain, and some confidently hold persistent misconceptions. Ordinary polling tools count votes but do not probe *why* students chose their answers or whether their beliefs withstand targeted scrutiny.

**Belief Stress Test** is a live classroom interaction platform that transforms student responses into actionable pedagogical diagnostics across multiple questions per lecture session.

### Core Workflow (Per Question):
```text
Question ➔ Round 1 (Initial Belief) ➔ AI Benchmark & Reasoning Analysis ➔ Targeted Challenge (Round 2) ➔ Instructor Insights & Benchmark Reveal
```

---

## 2. Key Features

- **Fixed 45-Student Eligibility Enforcement:** Strictly validates the exact 45 eligible students (`241AI001` through `241AI044` + `231AI007`). Rejects `241AI045` and unapproved IDs.
- **Direct Student Account Activation & Admin Reset:**
  - Eligible students activate their account directly at `/student/activate` using their whitelisted Student ID and a chosen password (no paper activation codes required).
  - Administrators can reset any mistaken or locked student activation in `/admin` with one click (`Reset Activation`).
- **Strict Role Separation & Cross-Tab Auth Sync:**
  - `ADMIN` manages professor accounts, student roster activations, and audit logs, and is strictly blocked from accessing classroom sessions or student response content.
  - `PROFESSOR` manages sessions, questions, rounds, and AI challenge reviews.
  - `STUDENT` joins live sessions, submits Round 1 & Round 2 responses, and reviews their personal submission history and the revealed Instructor Benchmark.
  - `BroadcastChannel` (`bst_auth_sync`) + `storage` events keep authentication and logout synchronized instantaneously across all open browser tabs.
- **Multi-Question Sessions & Adaptive Question Builder:**
  - Professors can add multiple questions to a single lecture session, edit questions while in `DRAFT` mode, and manage each question's round lifecycle (`DRAFT` → `OPEN_ROUND_1` → `ANALYZING` → `CHALLENGE_PENDING` → `OPEN_ROUND_2` → `COMPLETED`) on a dedicated page (`/professor/sessions/:sessionId/questions/:questionId`).
  - Supports 4 question types (**Factual / Technical**, **Subjective / Viewpoints**, **Prediction**, **Open-Ended Reasoning**) with adaptive student inputs (Multiple Choice, Numerical Estimate, or Free-Form Text) and **Instructor Benchmarks** (`reference_answer` and `accepted_reasoning`).
- **Benchmark Matching, Semantic Clustering & Gemini 3.8 Flash Reasoning Evaluation:**
  - Evaluates student answers against the professor's `reference_answer` (exact match, numerical tolerance, or semantic equivalence).
  - Evaluates student written explanations against the professor's `accepted_reasoning` rubric using TF-IDF + `MiniBatchKMeans` (`scikit-learn`) combined with **Gemini 3.8 Flash** (`gemini-3.8-flash` via `google-genai`).
  - Groups every student submission into evaluated mental-model categories (`ReasoningCategory`) and proposes a Socratic Round 2 challenge (`COUNTEREXAMPLE`, `OPPOSING_ARGUMENTS`, `PREDICTION_REVEAL`, or `TRANSFER_QUESTION`) for instructor review and approval.
- **Authenticated Real-Time WebSockets & Cold-Start Resilience:**
  - Authenticated `/ws/sessions/{session_id}` streams real-time participation and round updates while isolating sessions so students can only subscribe to sessions they have joined.
  - Built-in automatic retry, cold-start waking banner, and 4-minute keep-warm heartbeat for free-tier cloud hosting.

---

## 3. Technology Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Router v6, Lucide Icons, QR Code SVG (Deployed on **Vercel**).
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, WebSockets, Argon2id, PyJWT, Scikit-learn, NumPy (Deployed on **Render Native Python Runtime**).
- **Database:** Managed PostgreSQL (**Neon**) in production; SQLite supported for local development.
- **AI Integration:** Google GenAI SDK (`google-genai`) using `gemini-3.8-flash`, with automatic fail-safe fallback to `MockAIProvider`.

---

## 4. Local Quickstart

### Start the Application (Single Command):
```bash
./start.sh
```

- **Frontend Portal:** `http://localhost:5173`
- **Backend API & Health Check:** `http://127.0.0.1:8000/health`

### Default Local Accounts:
- **Professor:** `prof_nash` / `ProfPassword2026!`
- **Administrator:** `admin` / `AdminSecurePass2026!`
- **Students:** Any of the 45 eligible IDs (`241AI001`–`241AI044`, `231AI007`) via `/student/activate`.

---

## 5. Verification & Automated Test Suite

Run all 16 backend unit, integration, deployment-readiness, and 45-student classroom simulation tests:
```bash
backend/.venv/bin/pytest backend/tests -v
```
*Result: 16 passed (100% pass rate).*

---

## 6. Guides & Documentation

- [**Professor Quickstart Guide**](./PROFESSOR_GUIDE.md): Classroom workflow for multi-question sessions, Instructor Benchmarks, and AI Challenge review.
- [**Cold Start & Production Deployment Guide**](./COLD_START.md): Local setup, `gemini-3.8-flash` configuration, and step-by-step Neon PostgreSQL + Render + Vercel deployment guide.
