from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from app.database import Base


class EligibleStudent(Base):
    __tablename__ = "eligible_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, index=True, nullable=False)
    # Optional activation code (not required in closed classroom setting)
    activation_code_hash = Column(String(255), nullable=True)
    is_activated = Column(Boolean, default=False, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
