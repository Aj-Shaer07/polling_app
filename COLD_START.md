# Cold Start & Operational Guide: Belief Stress Test

This guide contains everything you need to cold start, configure, run tests, and deploy **Belief Stress Test**.

---

## 1. Quick Cold Start (Single Command)

In your terminal at the project root:

```bash
./start.sh
```

This will automatically:
1. Verify the Python virtual environment (`backend/.venv`).
2. Initialize the local database (`belief_stress_test.db`) with the 45 eligible students and admin/professor accounts if not already initialized.
3. Start the FastAPI backend on **`http://127.0.0.1:8000`**.
4. Start the Vite React frontend on **`http://localhost:5173`**.

Open your browser at **`http://localhost:5173`**.

---

## 2. Default Logins & Credentials

| Role | Username / ID | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Professor** | `prof_nash` | `ProfPassword2026!` | `http://localhost:5173/login` |
| **Administrator** | `admin` | `AdminSecurePass2026!` | `http://localhost:5173/login` |
| **Student** | Any of the 45 IDs (e.g. `241AI001`) | Set during activation | `http://localhost:5173/student/activate` |

---

## 3. Configuring the Gemini API Key

The application is built with a **provider-neutral AI interface (`AIProvider`)**.
- **Without an API key:** The application automatically runs on a high-fidelity, deterministic `MockAIProvider`. It clusters explanations using `scikit-learn` and creates structured reasoning categories and counterexamples locally without external API dependencies.
- **To connect your real Gemini API key:**
  1. Open or create `backend/.env` (or copy from `backend/.env.example`).
  2. Set:
     ```env
     GEMINI_API_KEY="AIzaSyYourActualGeminiApiKeyHere"
     GEMINI_MODEL="gemini-2.5-flash"
     ```
  3. Restart the backend.
  4. The platform will automatically use the official `google-genai` SDK with structured JSON schemas. If a rate limit or API outage occurs, the backend will gracefully fall back to the local provider without interrupting the live classroom!

---

## 4. Student Roster (The Exact 45 IDs) & Account Activation

Exactly **45 students** are permitted:
- `241AI001` through `241AI044` (44 students)
- `231AI007` (1 student)

### Direct Password Activation:
Students activate their accounts directly without needing paper activation codes:
1. Student visits `/student/activate` (or scans classroom QR).
2. Student enters their eligible Student ID (e.g. `241AI001`) and chooses their personal password (min 6 characters).
3. The platform validates against the 45-student roster table. Ineligible IDs (such as `241AI045` or non-whitelisted strings) are immediately rejected with `403 Forbidden`.
4. Once activated, the student identity is claimed and can log in with their chosen password. Repeated attempts to claim an already-activated student ID are rejected with `400 Bad Request`.

---

## 5. Running the Automated Test Suite

To run all 11 unit, integration, and simulation tests:

```bash
backend/.venv/bin/pytest backend/tests -v
```

This tests:
- Password hashing & JWT RBAC
- Exact 45-student roster boundary checks (`241AI045` rejected)
- Response integrity & duplicate submission rejection
- AI clustering & fallback resilience
- **Full 45-student simulated classroom:** All 45 students join, submit answers, AI groups reasoning, professor approves challenge, students submit revisions, and the belief transition matrix is calculated.

---

## 6. Production Deployment Instructions

### A. Database (PostgreSQL)
1. Provision a PostgreSQL instance (e.g., on Render, Neon, Supabase, or AWS RDS).
2. Set the connection string in your backend environment variables:
   `DATABASE_URL="postgresql://user:password@host:5432/dbname"`

### B. Backend (Render Free Web Service)
1. In Render, create a **New Web Service** connected to your repository.
2. Select **Docker** environment (uses `backend/Dockerfile`), or Python with:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add Environment Variables:
   - `DATABASE_URL` = your PostgreSQL URL
   - `SECRET_KEY` = a 32+ character random string
   - `COOKIE_SECURE` = `True`
   - `CORS_ORIGINS` = `https://your-frontend.vercel.app`
   - `GEMINI_API_KEY` = your Gemini API key (optional)
   - `ENVIRONMENT` = `production`

### C. Frontend (Vercel)
1. In Vercel, import the repository and set Root Directory to `frontend`.
2. Framework Preset: **Vite**.
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Environment Variables:
   - `VITE_API_BASE_URL` = `https://your-backend.onrender.com`
   - `VITE_WS_BASE_URL` = `wss://your-backend.onrender.com`
