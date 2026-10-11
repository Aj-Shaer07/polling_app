# Cold Start & Production Deployment Guide: Belief Stress Test

This guide covers local startup, Gemini 3.8 Flash configuration, automated verification, and production deployment using **Neon PostgreSQL**, **Render (Native Python Runtime)**, and **Vercel**.

---

## 1. Local Cold Start (Single Command)

In your terminal at the project root:

```bash
./start.sh
```

This script automatically:
1. Verifies the Python virtual environment (`backend/.venv`).
2. Runs database schema initialization and seeds the 45 eligible students (`241AI001`–`241AI044` + `231AI007`) and local accounts.
3. Starts the FastAPI backend on **`http://127.0.0.1:8000`**.
4. Starts the Vite React frontend on **`http://localhost:5173`**.

---

## 2. Default Local Credentials

| Role | Username / ID | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Professor** | `prof_nash` | `ProfPassword2026!` | `http://localhost:5173/login` |
| **Administrator** | `admin` | `AdminSecurePass2026!` | `http://localhost:5173/login` |
| **Student** | `241AI001`–`241AI044`, `231AI007` | Set during activation | `http://localhost:5173/student/activate` |

---

## 3. Configuring Gemini 3.8 Flash (`GEMINI_API_KEY`)

The backend uses the official Google GenAI SDK (`google-genai`) via [`backend/app/services/llm_provider.py`](./backend/app/services/llm_provider.py):
1. Copy `backend/.env.example` to `backend/.env`.
2. Configure your Gemini API key and model:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.8-flash
   ```
3. When Round 1 closes, `GeminiProvider` evaluates student answers and explanations against the professor's **Instructor Benchmark** (`reference_answer` and `accepted_reasoning`), groups students into mental-model categories (`ReasoningCategory`), and proposes a targeted Round 2 Socratic challenge.
4. If `GEMINI_API_KEY` is omitted or rate-limited during a live class, the backend automatically falls back to `MockAIProvider` so the lecture never stalls.

---

## 4. Student Roster & Account Management

Exactly **45 students** are eligible:
- `241AI001` through `241AI044` (44 students)
- `231AI007` (1 student)

- **Student Activation (`/student/activate`):** Students enter their eligible Student ID and create a password (min 6 characters). Unapproved IDs (such as `241AI045`) are rejected with `403 Forbidden`.
- **Admin Activation Reset (`/admin`):** If a student needs their password reset or an activation cleared, the Admin can click **Reset Activation** next to that student ID in the Admin Console.

---

## 5. Running the Automated Test Suite & Migrations

Run Alembic migrations:
```bash
cd backend && .venv/bin/alembic upgrade head
```

Run all 16 automated tests:
```bash
backend/.venv/bin/pytest backend/tests -v
```

---

## 6. Production Deployment (Neon + Render + Vercel)

- **Live Frontend (Vercel):** [https://polling-app-murex.vercel.app](https://polling-app-murex.vercel.app)
- **Live Backend (Render):** [https://polling-app-lpjc.onrender.com](https://polling-app-lpjc.onrender.com)

### Step A: Push Repository to GitHub
```bash
git remote add origin https://github.com/Aj-Shaer07/polling_app.git
git push -u origin main
```

### Step B: Provision Managed PostgreSQL on Neon
1. Create a new PostgreSQL project in [Neon Console](https://console.neon.tech).
2. Copy the PostgreSQL connection string (`postgresql://...` with `?sslmode=require`).

### Step C: Deploy Backend to Render (Native Python Runtime)
1. In [Render Dashboard](https://dashboard.render.com), create a **New Web Service** connected to your GitHub repository (or use the Blueprint [`render.yaml`](./render.yaml)).
2. Configure:
   - **Runtime:** `Python 3` (Native Python runtime — no Docker)
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
3. Set Environment Variables in Render:
   - `PYTHON_VERSION` = `3.12.6`
   - `ENVIRONMENT` = `production`
   - `LOG_LEVEL` = `INFO`
   - `DATABASE_URL` = *(your Neon PostgreSQL connection string with `?sslmode=require`)*
   - `SECRET_KEY` = *(unique random string of at least 32 characters)*
   - `GEMINI_API_KEY` = *(your Gemini API key)*
   - `GEMINI_MODEL` = `gemini-3.8-flash`
   - `INITIAL_ADMIN_USERNAME` = `admin`
   - `INITIAL_ADMIN_EMAIL` = `admin@classroom.edu`
   - `INITIAL_ADMIN_PASSWORD` = *(admin password; auto-bootstraps the initial admin and 45-student roster on startup)*
   - `CORS_ORIGINS` = `https://polling-app-murex.vercel.app`

### Step D: Deploy Frontend to Vercel
1. In [Vercel Dashboard](https://vercel.com/new), import the GitHub repository.
2. Configure:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Set Environment Variable in Vercel:
   - `VITE_API_BASE_URL` = `https://polling-app-lpjc.onrender.com`
