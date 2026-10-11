import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.session import ClassroomSession, SessionStatus, SessionParticipation
from app.models.question import Question
from app.models.roster import EligibleStudent
from app.models.user import User
from app.schemas.session import ParticipationDashboard, StudentParticipationStatus
from app.services.audit import log_audit_event


def generate_join_code(length: int = 6) -> str:
    # Use distinct uppercase letters and digits without confusing 0/O, 1/I
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_session(db: Session, title: str, professor_id: str) -> ClassroomSession:
    # Ensure unique join code
    for _ in range(10):
        code = generate_join_code()
        if not db.query(ClassroomSession).filter(ClassroomSession.join_code == code).first():
            break
    else:
        code = secrets.token_hex(3).upper()

    session = ClassroomSession(
        title=title,
        join_code=code,
        professor_id=professor_id,
        status=SessionStatus.DRAFT,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    log_audit_event(
        db=db,
        action="SESSION_CREATED",
        resource_type="classroom_sessions",
        resource_id=session.id,
        user_id=professor_id,
        details={"join_code": code, "title": title},
    )

    return session


def transition_session_status(
    db: Session,
    session: ClassroomSession,
    new_status: SessionStatus,
    professor_id: str
) -> ClassroomSession:
    # Allow legitimate state machine transitions or administrative override
    allowed_transitions = {
        SessionStatus.DRAFT: [SessionStatus.OPEN_ROUND_1, SessionStatus.COMPLETED],
        SessionStatus.OPEN_ROUND_1: [SessionStatus.ANALYZING, SessionStatus.DRAFT, SessionStatus.COMPLETED],
        SessionStatus.ANALYZING: [SessionStatus.CHALLENGE_PENDING, SessionStatus.OPEN_ROUND_1, SessionStatus.COMPLETED],
        SessionStatus.CHALLENGE_PENDING: [SessionStatus.OPEN_ROUND_2, SessionStatus.ANALYZING, SessionStatus.COMPLETED],
        SessionStatus.OPEN_ROUND_2: [SessionStatus.FOLLOW_UP, SessionStatus.CHALLENGE_PENDING, SessionStatus.COMPLETED],
        SessionStatus.FOLLOW_UP: [SessionStatus.COMPLETED, SessionStatus.OPEN_ROUND_2],
        SessionStatus.COMPLETED: [SessionStatus.ARCHIVED, SessionStatus.FOLLOW_UP, SessionStatus.OPEN_ROUND_1, SessionStatus.DRAFT],
        SessionStatus.ARCHIVED: [SessionStatus.COMPLETED],
    }

    if new_status not in allowed_transitions.get(session.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Illegal session status transition from {session.status.value} to {new_status.value}.",
        )

    session.status = new_status
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    log_audit_event(
        db=db,
        action="SESSION_STATUS_CHANGED",
        resource_type="classroom_sessions",
        resource_id=session.id,
        user_id=professor_id,
        details={"old_status": session.status.value, "new_status": new_status.value},
    )

    return session


def join_session(
    db: Session,
    join_code: str,
    student_user: User
) -> Tuple[ClassroomSession, SessionParticipation]:
    if not student_user.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an associated student ID.",
        )

    session = db.query(ClassroomSession).filter(ClassroomSession.join_code == join_code.strip().upper()).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session join code.",
        )

    if session.status == SessionStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This classroom session has been archived.",
        )

    # Check or create participation record
    participation = (
        db.query(SessionParticipation)
        .filter(
            SessionParticipation.session_id == session.id,
            SessionParticipation.student_id == student_user.student_id,
        )
        .first()
    )

    if not participation:
        # Create fresh pseudonymous participant ID
        participant_id = str(uuid.uuid4())
        participation = SessionParticipation(
            session_id=session.id,
            student_id=student_user.student_id,
            participant_id=participant_id,
        )
        db.add(participation)
        db.commit()
        db.refresh(participation)

    return session, participation


def get_session_participation_dashboard(
    db: Session,
    session_id: str
) -> ParticipationDashboard:
    # Fetch all 45 eligible students
    eligible = db.query(EligibleStudent).order_by(EligibleStudent.student_id).all()
    participations = (
        db.query(SessionParticipation)
        .filter(SessionParticipation.session_id == session_id)
        .all()
    )
    part_map = {p.student_id: p for p in participations}

    student_statuses: List[StudentParticipationStatus] = []
    joined_count = 0
    round_1_answered = 0
    round_2_answered = 0
    follow_up_answered = 0

    for s in eligible:
        p = part_map.get(s.student_id)
        if p:
            joined_count += 1
            if p.round_1_submitted:
                round_1_answered += 1
            if p.round_2_submitted:
                round_2_answered += 1
            if p.follow_up_submitted:
                follow_up_answered += 1

            student_statuses.append(StudentParticipationStatus(
                student_id=s.student_id,
                joined=True,
                round_1_submitted=p.round_1_submitted,
                round_1_submitted_at=p.round_1_submitted_at,
                round_2_submitted=p.round_2_submitted,
                round_2_submitted_at=p.round_2_submitted_at,
                follow_up_submitted=p.follow_up_submitted,
                follow_up_submitted_at=p.follow_up_submitted_at,
            ))
        else:
            student_statuses.append(StudentParticipationStatus(
                student_id=s.student_id,
                joined=False,
                round_1_submitted=False,
                round_2_submitted=False,
                follow_up_submitted=False,
            ))

    eligible_total = len(eligible) if len(eligible) > 0 else 45

    return ParticipationDashboard(
        eligible_total=eligible_total,
        joined_count=joined_count,
        round_1_answered=round_1_answered,
        round_1_pending=eligible_total - round_1_answered,
        round_2_answered=round_2_answered,
        round_2_pending=eligible_total - round_2_answered,
        follow_up_answered=follow_up_answered,
        follow_up_pending=eligible_total - follow_up_answered,
        students=student_statuses,
    )
