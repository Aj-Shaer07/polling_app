#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  Ψ BELIEF STRESS TEST — LIVE CLASSROOM PLATFORM"
echo "=========================================================="

# Check Python environment
if [ ! -d "backend/.venv" ]; then
    echo "[!] Setting up Python virtual environment in backend/.venv..."
    /opt/homebrew/bin/python3.12 -m venv backend/.venv || python3 -m venv backend/.venv
    backend/.venv/bin/pip install -r backend/requirements.txt
fi

# Ensure database is initialized with admin and 45 roster
if [ ! -f "belief_stress_test.db" ]; then
    echo "[*] Initializing local database and default admin..."
    backend/.venv/bin/python backend/app/bootstrap.py --username admin --email admin@classroom.edu --password AdminSecurePass2026!
    backend/.venv/bin/python -c '
import sys, os
sys.path.insert(0, "backend")
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth import hash_password

db = SessionLocal()
if not db.query(User).filter(User.username == "prof_nash").first():
    db.add(User(
        username="prof_nash",
        email="nash@princeton.edu",
        hashed_password=hash_password("ProfPassword2026!"),
        role=UserRole.PROFESSOR,
        is_active=True
    ))
    db.commit()
db.close()
'
fi

echo ""
echo "[+] Starting FastAPI backend on http://127.0.0.1:8000 ..."
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "[+] Starting Vite frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

cleanup() {
    echo ""
    echo "[*] Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "[+] Done."
    exit 0
}

trap cleanup INT TERM

echo ""
echo "=========================================================="
echo "  Application running successfully!"
echo "  • Frontend:  http://localhost:5173"
echo "  • Backend:   http://127.0.0.1:8000"
echo "  • API Docs:  http://127.0.0.1:8000/docs"
echo ""
echo "  Default Professor Login:  prof_nash / ProfPassword2026!"
echo "  Default Admin Login:      admin / AdminSecurePass2026!"
echo "=========================================================="
echo "Press Ctrl+C to stop all servers."
wait
