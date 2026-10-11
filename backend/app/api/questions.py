from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import ClassroomSession
from app.models.question import Question
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionStudentView,
    QuestionStatusUpdate,
)
from app.services.audit import log_audit_event
from app.websocket.manager import ws_manager
from app.api.deps import get_current_user, require_professor

router = APIRouter(prefix="", tags=["Questions"])


@router.post("/sessions/{session_id}/questions", response_model=QuestionResponse)
def create_question(
    session_id: str,
    q_data: QuestionCreate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Create a new question for a session (Professor only)."""
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if session.professor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    # Determine order index
    count = db.query(Question).filter(Question.session_id == session_id).count()

    question = Question(
        session_id=session_id,
        question_text=q_data.question_text.strip(),
        question_type=q_data.question_type,
        reference_answer=q_data.reference_answer.strip() if q_data.reference_answer else None,
        accepted_reasoning=q_data.accepted_reasoning.strip() if q_data.accepted_reasoning else None,
        choices=q_data.choices,
        confidence_required=q_data.confidence_required,
        reasoning_required=q_data.reasoning_required,
        prediction_enabled=q_data.prediction_enabled,
        is_follow_up=q_data.is_follow_up,
        order_index=count + 1,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    log_audit_event(
        db=db,
        action="QUESTION_CREATED",
        resource_type="questions",
        resource_id=question.id,
        user_id=current_user.id,
        details={"session_id": session_id, "is_follow_up": question.is_follow_up},
    )

    return question


@router.get("/sessions/{session_id}/questions")
def get_session_questions(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List questions for a session. Students only see StudentView (reference answers stripped)."""
    session = db.query(ClassroomSession).filter(ClassroomSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    questions = (
        db.query(Question)
        .filter(Question.session_id == session_id)
        .order_by(Question.order_index)
        .all()
    )

    if current_user.role in [UserRole.PROFESSOR, UserRole.ADMIN]:
        return [QuestionResponse.model_validate(q) for q in questions]
    else:
        results = []
        for q in questions:
            view = QuestionStudentView.model_validate(q)
            if q.status == "COMPLETED":
                view.reference_answer = q.reference_answer
                view.accepted_reasoning = q.accepted_reasoning
            else:
                view.reference_answer = None
                view.accepted_reasoning = None
            results.append(view)
        return results


@router.get("/questions/{question_id}")
def get_question_by_id(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    if current_user.role in [UserRole.PROFESSOR, UserRole.ADMIN]:
        return QuestionResponse.model_validate(question)
    else:
        view = QuestionStudentView.model_validate(question)
        if question.status == "COMPLETED":
            view.reference_answer = question.reference_answer
            view.accepted_reasoning = question.accepted_reasoning
        else:
            view.reference_answer = None
            view.accepted_reasoning = None
        return view


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    update_data: QuestionUpdate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Edit question text, type, benchmark, and choices while in DRAFT mode (Professor only)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
    if not session or (session.professor_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    if question.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Questions can only be edited while in DRAFT mode before rounds commence.",
        )

    if update_data.question_text is not None:
        question.question_text = update_data.question_text.strip()
    if update_data.question_type is not None:
        question.question_type = update_data.question_type
    if update_data.reference_answer is not None:
        question.reference_answer = update_data.reference_answer.strip() if update_data.reference_answer else None
    if update_data.accepted_reasoning is not None:
        question.accepted_reasoning = update_data.accepted_reasoning.strip() if update_data.accepted_reasoning else None
    if update_data.choices is not None:
        question.choices = update_data.choices
    if update_data.confidence_required is not None:
        question.confidence_required = update_data.confidence_required
    if update_data.reasoning_required is not None:
        question.reasoning_required = update_data.reasoning_required
    if update_data.prediction_enabled is not None:
        question.prediction_enabled = update_data.prediction_enabled

    db.commit()
    db.refresh(question)

    await ws_manager.broadcast(
        session_id=question.session_id,
        event_type="question_updated",
        data={"question_id": question.id},
    )

    return QuestionResponse.model_validate(question)


@router.post("/questions/{question_id}/status", response_model=QuestionResponse)
async def update_question_status(
    question_id: str,
    status_data: QuestionStatusUpdate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Update round/status for a specific question (Professor only)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
    if not session or (session.professor_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    question.status = status_data.status
    db.commit()
    db.refresh(question)

    # Broadcast question status change
    await ws_manager.broadcast(
        session_id=question.session_id,
        event_type="question_status_changed",
        data={"question_id": question.id, "status": question.status},
    )

    return QuestionResponse.model_validate(question)


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: str,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Delete a question from a session (Professor only)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
    if not session or (session.professor_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    db.delete(question)
    db.commit()
    return {"message": "Question successfully deleted."}
