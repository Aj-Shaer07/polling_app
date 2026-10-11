from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.session import ClassroomSession, SessionStatus
from app.models.question import Question
from app.models.challenge import ReasoningCategory, ChallengeProposal, ChallengeStatus
from app.schemas.challenge import (
    ReasoningCategoryResponse,
    ReasoningCategoryUpdate,
    ChallengeProposalResponse,
    ChallengeReviewRequest,
    ChallengeStudentView,
)
from app.services.reasoning_service import (
    analyze_round_1_and_propose_challenge,
    review_challenge_proposal,
)
from app.websocket.manager import ws_manager
from app.api.deps import get_current_user, require_professor

router = APIRouter(prefix="", tags=["AI Challenges & Reasoning"])


@router.post("/questions/{question_id}/analyze")
async def trigger_analysis_and_challenge(
    question_id: str,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Triggers reasoning clustering and AI challenge proposal (Professor only)."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
    if session.professor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this session.")

    result = analyze_round_1_and_propose_challenge(
        db=db,
        session_id=session.id,
        question_id=question_id,
        professor_id=current_user.id,
    )

    await ws_manager.broadcast(
        session_id=session.id,
        event_type="analysis_ready",
        data={"session_id": session.id, "question_id": question_id},
    )

    return {
        "status": "success",
        "categories_count": len(result["categories"]),
        "challenge_id": result["challenge"].id,
    }


@router.get("/questions/{question_id}/challenge")
def get_challenge(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the challenge proposal for this question."""
    challenge = (
        db.query(ChallengeProposal)
        .filter(ChallengeProposal.question_id == question_id)
        .order_by(ChallengeProposal.created_at.desc())
        .first()
    )
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No challenge proposed yet.")

    if current_user.role in [UserRole.PROFESSOR, UserRole.ADMIN]:
        return ChallengeProposalResponse.model_validate(challenge)
    else:
        # Students only see challenge if approved or round 2 is active
        question = db.query(Question).filter(Question.id == question_id).first()
        session = db.query(ClassroomSession).filter(ClassroomSession.id == question.session_id).first()
        if (
            session.status not in [SessionStatus.OPEN_ROUND_2, SessionStatus.FOLLOW_UP, SessionStatus.COMPLETED]
            and (not question or question.status not in ["OPEN_ROUND_2", "FOLLOW_UP", "COMPLETED"])
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Challenge will be revealed when Round 2 opens.",
            )
        
        display_text = challenge.edited_text if challenge.edited_text else challenge.challenge_text
        return ChallengeStudentView(
            id=challenge.id,
            challenge_type=challenge.challenge_type,
            challenge_text=display_text,
            targeted_reasoning_pattern=challenge.targeted_reasoning_pattern,
        )


@router.post("/challenges/{challenge_id}/review", response_model=ChallengeProposalResponse)
async def review_challenge(
    challenge_id: str,
    review_data: ChallengeReviewRequest,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Professor approves, edits, or rejects the AI-generated challenge."""
    challenge = review_challenge_proposal(
        db=db,
        challenge_id=challenge_id,
        status_choice=review_data.status,
        edited_text=review_data.edited_text,
        instructor_notes=review_data.instructor_notes,
        professor_id=current_user.id,
    )

    if review_data.status == ChallengeStatus.APPROVED:
        question = db.query(Question).filter(Question.id == challenge.question_id).first()
        await ws_manager.broadcast(
            session_id=question.session_id,
            event_type="challenge_approved",
            data={"question_id": question.id, "challenge_id": challenge.id},
        )

    return challenge


@router.get("/questions/{question_id}/categories", response_model=List[ReasoningCategoryResponse])
def get_categories(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve reasoning categories for a question."""
    categories = (
        db.query(ReasoningCategory)
        .filter(ReasoningCategory.question_id == question_id)
        .order_by(ReasoningCategory.response_count.desc())
        .all()
    )
    return categories


@router.patch("/categories/{category_id}", response_model=ReasoningCategoryResponse)
def update_category(
    category_id: str,
    update_data: ReasoningCategoryUpdate,
    current_user: User = Depends(require_professor),
    db: Session = Depends(get_db),
):
    """Professor modifies or approves a reasoning category."""
    cat = db.query(ReasoningCategory).filter(ReasoningCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    if update_data.title is not None:
        cat.title = update_data.title.strip()
    if update_data.description is not None:
        cat.description = update_data.description.strip()
    if update_data.is_misconception is not None:
        cat.is_misconception = update_data.is_misconception
    if update_data.is_approved is not None:
        cat.is_approved = update_data.is_approved

    db.commit()
    db.refresh(cat)
    return cat
