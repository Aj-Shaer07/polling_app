from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.challenge import ChallengeStatus


class ReasoningCategoryResponse(BaseModel):
    id: str
    question_id: str
    round_number: int
    title: str
    description: str
    is_misconception: bool
    sample_explanations: List[str] = []
    response_count: int
    percentage: float
    is_ai_proposed: bool
    is_approved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReasoningCategoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_misconception: Optional[bool] = None
    is_approved: Optional[bool] = None


class ChallengeProposalResponse(BaseModel):
    id: str
    question_id: str
    challenge_type: str
    challenge_text: str
    targeted_reasoning_pattern: str
    relevance_evidence: str
    learning_objective: str
    assumptions_and_uncertainties: str
    status: ChallengeStatus
    edited_text: Optional[str] = None
    instructor_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeReviewRequest(BaseModel):
    status: ChallengeStatus  # APPROVED, EDITED, REJECTED
    edited_text: Optional[str] = None
    instructor_notes: Optional[str] = None


class ChallengeStudentView(BaseModel):
    id: str
    challenge_type: str
    challenge_text: str
    targeted_reasoning_pattern: Optional[str] = None
