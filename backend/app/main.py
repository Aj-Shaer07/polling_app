import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal, get_db
from app.api import auth, admin, sessions, questions, responses, challenges
from app.models.user import User, UserRole
from app.models.session import ClassroomSession, SessionParticipation
from app.services.auth import decode_access_token
from app.services.roster import initialize_roster
from app.websocket.manager import ws_manager

log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Validate required configuration in production
    settings.validate_for_startup()

    # 2. Ensure database schema tables exist
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized.")

    # 3. Ensure the fixed 45-student eligible roster and optional initial admin exist
    db = SessionLocal()
    try:
        initialize_roster(db=db, force_reset=False)
        if settings.INITIAL_ADMIN_PASSWORD and len(settings.INITIAL_ADMIN_PASSWORD.strip()) >= 4:
            from app.bootstrap import bootstrap_admin_and_roster
            bootstrap_admin_and_roster(
                username=settings.INITIAL_ADMIN_USERNAME.strip(),
                email=settings.INITIAL_ADMIN_EMAIL.strip(),
                password=settings.INITIAL_ADMIN_PASSWORD.strip(),
                init_roster=False,
            )
    except Exception as e:
        logger.warning(f"Startup roster/admin check warning: {e}")
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Live Classroom Diagnostic Platform for AI-powered belief stress-testing.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(responses.router, prefix="/api")
app.include_router(challenges.router, prefix="/api")


@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    ai_active = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "ai_provider": "gemini" if ai_active else "mock",
            "gemini_model": settings.GEMINI_MODEL,
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "service": settings.PROJECT_NAME,
                "environment": settings.ENVIRONMENT,
            },
        )


@app.websocket("/ws/sessions/{session_id}")
async def websocket_session_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db),
):
    token = websocket.query_params.get("token") or websocket.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not user or not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if user.role == UserRole.PROFESSOR:
        if session.professor_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    elif user.role == UserRole.STUDENT:
        participant = (
            db.query(SessionParticipation)
            .filter(
                SessionParticipation.session_id == session_id,
                SessionParticipation.student_id == user.student_id,
            )
            .first()
        )
        if not participant:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    else:
        # Admins do not subscribe to classroom live response streams
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        ws_manager.disconnect(session_id, websocket)

