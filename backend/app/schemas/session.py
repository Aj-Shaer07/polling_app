from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.session import SessionStatus
from app.schemas.question import QuestionResponse


class SessionCreate(BaseModel):
    title: str


class SessionStatusUpdate(BaseModel):
    status: SessionStatus


class SessionResponse(BaseModel):
    id: str
    title: str
    join_code: str
    professor_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JoinSessionRequest(BaseModel):
    join_code: str


class StudentParticipationStatus(BaseModel):
    student_id: str
    joined: bool
    round_1_submitted: bool
    round_1_submitted_at: Optional[datetime] = None
    round_2_submitted: bool
    round_2_submitted_at: Optional[datetime] = None
    follow_up_submitted: bool
    follow_up_submitted_at: Optional[datetime] = None


class ParticipationDashboard(BaseModel):
    eligible_total: int = 45
    joined_count: int
    round_1_answered: int
    round_1_pending: int
    round_2_answered: int
    round_2_pending: int
    follow_up_answered: int
    follow_up_pending: int
    students: List[StudentParticipationStatus]


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    join_code: str
    professor_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    questions: List[QuestionResponse] = []
    participation: ParticipationDashboard

    model_config = ConfigDict(from_attributes=True)
