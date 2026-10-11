from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class InitialResponseSubmission(BaseModel):
    answer: str
    confidence: int = Field(..., ge=1, le=5)
    explanation: Optional[str] = None
    prediction: Optional[str] = None


class RevisedResponseSubmission(BaseModel):
    answer: str
    confidence: int = Field(..., ge=1, le=5)
    changed_answer: bool
    change_reason: Optional[str] = None


class FollowUpResponseSubmission(BaseModel):
    answer: str
    confidence: int = Field(..., ge=1, le=5)
    explanation: Optional[str] = None


class StudentResponseView(BaseModel):
    id: str
    round_number: int
    answer: str
    confidence: int
    explanation: Optional[str] = None
    prediction: Optional[str] = None
    changed_answer: Optional[bool] = None
    change_reason: Optional[str] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerDistributionItem(BaseModel):
    answer: str
    count: int
    percentage: float
    average_confidence: float
    is_reference_correct: Optional[bool] = None


class ConfidenceDistributionItem(BaseModel):
    confidence: int
    count: int
    percentage: float


class BeliefTransitionItem(BaseModel):
    from_answer: str
    to_answer: str
    count: int
    percentage: float
    avg_initial_confidence: float
    avg_revised_confidence: float
    sample_change_reasons: List[str] = []


class AggregateAnalysisResponse(BaseModel):
    question_id: str
    round_1_total: int
    round_2_total: int
    round_1_distributions: List[AnswerDistributionItem] = []
    round_2_distributions: List[AnswerDistributionItem] = []
    confidence_distributions_round_1: List[ConfidenceDistributionItem] = []
    confidence_distributions_round_2: List[ConfidenceDistributionItem] = []
    belief_transitions: List[BeliefTransitionItem] = []
    instructor_insight: Optional[str] = None
    ai_summary: Optional[str] = None
