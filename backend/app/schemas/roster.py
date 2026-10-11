from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict


class EligibleStudentResponse(BaseModel):
    id: int
    student_id: str
    is_activated: bool
    activated_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RosterItemWithCode(BaseModel):
    student_id: str
    activation_code: str
    is_activated: bool


class RosterBootstrapResponse(BaseModel):
    total_eligible: int
    students: List[RosterItemWithCode]


class RosterImportRequest(BaseModel):
    student_ids: List[str]

    @field_validator("student_ids")
    @classmethod
    def clean_student_ids(cls, v: List[str]) -> List[str]:
        return [s.strip().upper() for s in v if s.strip()]
