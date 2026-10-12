from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import ClassroomSession, SessionStatus, SessionParticipation
from app.models.question import Question
from app.schemas.response import (
    InitialResponseSubmission,
    RevisedResponseSubmission,
    FollowUpResponseSubmission,
    StudentResponseView,
    AggregateAnalysisResponse,
)
from app.services.responses import (
    submit_round_1_response,
    submit_round_2_revision,
    submit_follow_up_response,
    get_participant_responses,
)
from app.services.aggregation import get_aggregate_analysis
from app.websocket.manager import ws_manager
from app.api.deps import get_current_user, require_student

router = APIRouter(prefix="", tags=["Student Responses"])


def get_participant_id_for_session(db: Session, session_id: str, student_id: str) -> str:
    part = (
        db.query(SessionParticipation)
        .filter(
            SessionParticipation.session_id == session_id,
            SessionParticipation.student_id == student_id,
        )
        .first()
    )
    if not part:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student has not joined this classroom session.",
        )
    return part.participant_id


@router.post("/questions/{question_id}/responses/round1", response_model=StudentResponseView)
async def submit_initial_response(
    question_id: str,
    submission: InitialResponseSubmission,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    participant_id = get_participant_id_for_session(db, question.session_id, current_user.student_id)

    resp = submit_round_1_response(
        db=db,
        session_id=question.session_id,
        question_id=question_id,
        participant_id=participant_id,
        student_id=current_user.student_id,
        answer=submission.answer,
        confidence=submission.confidence,
        explanation=submission.explanation,
        prediction=submission.prediction,
    )

    # Broadcast real-time participation update
    await ws_manager.broadcast(
        session_id=question.session_id,
        event_type="response_recorded",
        data={
            "session_id": question.session_id,
            "round": 1,
            "student_id": current_user.student_id,
        },
    )

    return resp


@router.post("/questions/{question_id}/responses/round2", response_model=StudentResponseView)
async def submit_revised_response(
    question_id: str,
    submission: RevisedResponseSubmission,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    participant_id = get_participant_id_for_session(db, question.session_id, current_user.student_id)

    resp = submit_round_2_revision(
        db=db,
        session_id=question.session_id,
        question_id=question_id,
        participant_id=participant_id,
        student_id=current_user.student_id,
        answer=submission.answer,
        confidence=submission.confidence,
        changed_answer=submission.changed_answer,
        change_reason=submission.change_reason,
    )

    await ws_manager.broadcast(
        session_id=question.session_id,
        event_type="response_recorded",
        data={
            "session_id": question.session_id,
            "round": 2,
            "student_id": current_user.student_id,
        },
    )

    return resp


@router.post("/questions/{question_id}/responses/followup", response_model=StudentResponseView)
async def submit_follow_up(
    question_id: str,
    submission: FollowUpResponseSubmission,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    participant_id = get_participant_id_for_session(db, question.session_id, current_user.student_id)

    resp = submit_follow_up_response(
        db=db,
        session_id=question.session_id,
        question_id=question_id,
        participant_id=participant_id,
        student_id=current_user.student_id,
        answer=submission.answer,
        confidence=submission.confidence,
        explanation=submission.explanation,
    )

    await ws_manager.broadcast(
        session_id=question.session_id,
        event_type="response_recorded",
        data={
            "session_id": question.session_id,
            "round": "follow_up",
            "student_id": current_user.student_id,
        },
    )

    return resp


@router.get("/questions/{question_id}/my-responses", response_model=List[StudentResponseView])
def get_my_responses(
    question_id: str,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    participant_id = get_participant_id_for_session(db, question.session_id, current_user.student_id)
    return get_participant_responses(db, question_id, participant_id)


@router.get("/questions/{question_id}/results", response_model=AggregateAnalysisResponse)
def get_question_results(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators do not have access to student response content or classroom results.",
        )

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if current_user.role == UserRole.PROFESSOR and session.professor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access results for another professor's session.",
        )

    # Students can only view aggregate results if round 1 is closed or round 2 / results are open
    if current_user.role == UserRole.STUDENT:
        if session.status in [SessionStatus.DRAFT, SessionStatus.OPEN_ROUND_1] and question.status in ["DRAFT", "OPEN_ROUND_1"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Results will be revealed once the round closes.",
            )

    return get_aggregate_analysis(
        db,
        question_id,
        include_individual=(current_user.role == UserRole.PROFESSOR),
    )
