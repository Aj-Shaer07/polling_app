from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class StudentActivateRequest(BaseModel):
    student_id: str
    new_password: str
    activation_code: Optional[str] = None


class StudentLoginRequest(BaseModel):
    student_id: str
    password: str


class ProfessorCreateRequest(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: UserRole
    student_id: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    username: str
    student_id: Optional[str] = None
