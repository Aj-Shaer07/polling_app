from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.question import QuestionType


class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionType = QuestionType.FACTUAL
    reference_answer: Optional[str] = None
    accepted_reasoning: Optional[str] = None
    choices: Optional[List[str]] = None
    confidence_required: bool = True
    reasoning_required: bool = True
    prediction_enabled: bool = False
    is_follow_up: bool = False


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    reference_answer: Optional[str] = None
    accepted_reasoning: Optional[str] = None
    choices: Optional[List[str]] = None
    confidence_required: Optional[bool] = None
    reasoning_required: Optional[bool] = None
    prediction_enabled: Optional[bool] = None
    status: Optional[str] = None


class QuestionStatusUpdate(BaseModel):
    status: str


class QuestionResponse(BaseModel):
    id: str
    session_id: str
    question_text: str
    question_type: QuestionType
    reference_answer: Optional[str] = None
    accepted_reasoning: Optional[str] = None
    choices: Optional[List[str]] = None
    confidence_required: bool
    reasoning_required: bool
    prediction_enabled: bool
    order_index: int
    is_follow_up: bool
    status: str = "DRAFT"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionStudentView(BaseModel):
    id: str
    session_id: str
    question_text: str
    question_type: QuestionType
    choices: Optional[List[str]] = None
    confidence_required: bool
    reasoning_required: bool
    prediction_enabled: bool
    order_index: int
    is_follow_up: bool
    status: str = "DRAFT"
    reference_answer: Optional[str] = None
    accepted_reasoning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
