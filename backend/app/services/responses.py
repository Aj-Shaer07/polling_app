from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.session import ClassroomSession, SessionStatus, SessionParticipation
from app.models.question import Question
from app.models.response import StudentResponse


def submit_round_1_response(
    db: Session,
    session_id: str,
    question_id: str,
    participant_id: str,
    student_id: str,
    answer: str,
    confidence: int,
    explanation: Optional[str] = None,
    prediction: Optional[str] = None,
) -> StudentResponse:
    # 1. Verify question belongs to this session and is not follow-up
    question = db.query(Question).filter(Question.id == question_id, Question.session_id == session_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in this session.",
        )
    if question.is_follow_up:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit initial response to a follow-up assessment question.",
        )

    # 2. Verify state: allow if either question.status or session.status is OPEN_ROUND_1
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    is_r1_open = (question.status == "OPEN_ROUND_1") or (session and session.status == SessionStatus.OPEN_ROUND_1)
    if not is_r1_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submissions are not open for Round 1 on this question.",
        )

    # 3. Check for existing response - prevent duplicates
    existing = (
        db.query(StudentResponse)
        .filter(
            StudentResponse.question_id == question_id,
            StudentResponse.participant_id == participant_id,
            StudentResponse.round_number == 1,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a response for Round 1.",
        )

    # 4. Save response in transaction
    response_record = StudentResponse(
        question_id=question_id,
        participant_id=participant_id,
        round_number=1,
        answer=answer.strip(),
        confidence=confidence,
        explanation=explanation.strip() if explanation else None,
        prediction=prediction.strip() if prediction else None,
    )
    db.add(response_record)

    # 5. Update participation attendance record
    participation = (
        db.query(SessionParticipation)
        .filter(
            SessionParticipation.session_id == session_id,
            SessionParticipation.student_id == student_id,
        )
        .first()
    )
    if participation:
        participation.round_1_submitted = True
        participation.round_1_submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response_record)
    return response_record


def submit_round_2_revision(
    db: Session,
    session_id: str,
    question_id: str,
    participant_id: str,
    student_id: str,
    answer: str,
    confidence: int,
    changed_answer: bool,
    change_reason: Optional[str] = None,
) -> StudentResponse:
    # 1. Verify question
    question = db.query(Question).filter(Question.id == question_id, Question.session_id == session_id).first()
    if not question or question.is_follow_up:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Valid question not found for Round 2 revisions.",
        )

    # 2. Verify state: allow if either question.status or session.status is OPEN_ROUND_2
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    is_r2_open = (question.status == "OPEN_ROUND_2") or (session and session.status == SessionStatus.OPEN_ROUND_2)
    if not is_r2_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submissions are not open for Round 2 revisions on this question.",
        )

    # 3. Check existing round 2 submission
    existing = (
        db.query(StudentResponse)
        .filter(
            StudentResponse.question_id == question_id,
            StudentResponse.participant_id == participant_id,
            StudentResponse.round_number == 2,
        )
        .first()
    )

    if existing:
        # Update existing revision
        existing.answer = answer.strip()
        existing.confidence = confidence
        existing.changed_answer = changed_answer
        existing.change_reason = change_reason.strip() if change_reason else None
        response_record = existing
    else:
        response_record = StudentResponse(
            question_id=question_id,
            participant_id=participant_id,
            round_number=2,
            answer=answer.strip(),
            confidence=confidence,
            changed_answer=changed_answer,
            change_reason=change_reason.strip() if change_reason else None,
        )
        db.add(response_record)

    # Update participation attendance
    participation = (
        db.query(SessionParticipation)
        .filter(
            SessionParticipation.session_id == session_id,
            SessionParticipation.student_id == student_id,
        )
        .first()
    )
    if participation:
        participation.round_2_submitted = True
        participation.round_2_submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response_record)
    return response_record


def submit_follow_up_response(
    db: Session,
    session_id: str,
    question_id: str,
    participant_id: str,
    student_id: str,
    answer: str,
    confidence: int,
    explanation: Optional[str] = None,
) -> StudentResponse:
    # 1. Verify question is a follow-up question
    question = db.query(Question).filter(Question.id == question_id, Question.session_id == session_id).first()
    if not question or not question.is_follow_up:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up assessment question not found.",
        )

    # 2. Verify session / question state
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    is_fu_open = (question.status == "FOLLOW_UP") or (session and session.status == SessionStatus.FOLLOW_UP)
    if not is_fu_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow-up assessment is not currently active.",
        )

    existing = (
        db.query(StudentResponse)
        .filter(
            StudentResponse.question_id == question_id,
            StudentResponse.participant_id == participant_id,
            StudentResponse.round_number == 1,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a response for this follow-up question.",
        )

    response_record = StudentResponse(
        question_id=question_id,
        participant_id=participant_id,
        round_number=1,
        answer=answer.strip(),
        confidence=confidence,
        explanation=explanation.strip() if explanation else None,
    )
    db.add(response_record)

    participation = (
        db.query(SessionParticipation)
        .filter(
            SessionParticipation.session_id == session_id,
            SessionParticipation.student_id == student_id,
        )
        .first()
    )
    if participation:
        participation.follow_up_submitted = True
        participation.follow_up_submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response_record)
    return response_record


def get_participant_responses(
    db: Session,
    question_id: str,
    participant_id: str
) -> List[StudentResponse]:
    return (
        db.query(StudentResponse)
        .filter(
            StudentResponse.question_id == question_id,
            StudentResponse.participant_id == participant_id,
        )
        .order_by(StudentResponse.round_number)
        .all()
    )
