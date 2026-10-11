from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import ClassroomSession, SessionStatus
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    SessionStatusUpdate,
    JoinSessionRequest,
    ParticipationDashboard,
)
from app.services.sessions import (
    create_session,
    transition_session_status,
    join_session,
    get_session_participation_dashboard,
)
from app.websocket.manager import ws_manager
from app.api.deps import get_current_user, require_professor, require_student

router = APIRouter(prefix="/sessions", tags=["Classroom Sessions"])


@router.post("", response_model=SessionResponse)
def create_new_session(
    data: SessionCreate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Create a new classroom session (Professor only)."""
    return create_session(db=db, title=data.title, professor_id=current_user.id)


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """List sessions created by the current professor (Professor only)."""
    return (
        db.query(ClassroomSession)
        .filter(ClassroomSession.professor_id == current_user.id)
        .order_by(ClassroomSession.created_at.desc())
        .all()
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full details of a session, including questions and participation counts."""
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators do not have access to classroom sessions or response data.",
        )

    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    # Authorization: professor owner or student
    if current_user.role == UserRole.PROFESSOR and session.professor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another professor's session.")

    dashboard = get_session_participation_dashboard(db, session.id)

    # If student, scrub other students' identifiers from participation dashboard
    if current_user.role == UserRole.STUDENT:
        dashboard.students = [s for s in dashboard.students if s.student_id == current_user.student_id]

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        join_code=session.join_code,
        professor_id=session.professor_id,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        questions=session.questions,
        participation=dashboard,
    )


@router.post("/{session_id}/status", response_model=SessionResponse)
async def update_session_status(
    session_id: str,
    status_update: SessionStatusUpdate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Transition session lifecycle status (Professor only)."""
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if session.professor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    updated_session = transition_session_status(
        db=db,
        session=session,
        new_status=status_update.status,
        professor_id=current_user.id,
    )

    # Broadcast event via WebSocket
    await ws_manager.broadcast(
        session_id=session_id,
        event_type="status_changed",
        data={"session_id": session_id, "new_status": updated_session.status.value},
    )

    return updated_session


@router.post("/join")
async def join_active_session(
    join_data: JoinSessionRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Eligible authenticated student joins an active classroom session."""
    session, participation = join_session(
        db=db,
        join_code=join_data.join_code,
        student_user=current_user,
    )

    # Broadcast joined event to professor dashboard
    await ws_manager.broadcast(
        session_id=session.id,
        event_type="participant_joined",
        data={
            "session_id": session.id,
            "student_id": current_user.student_id,
            "joined_at": participation.joined_at.isoformat(),
        },
    )

    return {
        "session_id": session.id,
        "title": session.title,
        "status": session.status,
        "participant_id": participation.participant_id,
    }


@router.get("/{session_id}/participation", response_model=ParticipationDashboard)
def get_participation(
    session_id: str,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Get live participation dashboard for all 45 students (Professor only)."""
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if session.professor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    return get_session_participation_dashboard(db, session_id)
