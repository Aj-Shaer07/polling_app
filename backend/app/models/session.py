import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base


class SessionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN_ROUND_1 = "OPEN_ROUND_1"
    ANALYZING = "ANALYZING"
    CHALLENGE_PENDING = "CHALLENGE_PENDING"
    OPEN_ROUND_2 = "OPEN_ROUND_2"
    FOLLOW_UP = "FOLLOW_UP"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    join_code = Column(String(10), unique=True, index=True, nullable=False)
    professor_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(SessionStatus, name="session_status_enum"), nullable=False, default=SessionStatus.DRAFT)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    professor = relationship("User", back_populates="sessions")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan", order_by="Question.order_index")
    participations = relationship("SessionParticipation", back_populates="session", cascade="all, delete-orphan")


class SessionParticipation(Base):
    __tablename__ = "session_participations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("classroom_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(20), nullable=False)
    participant_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    round_1_submitted = Column(Boolean, default=False, nullable=False)
    round_1_submitted_at = Column(DateTime, nullable=True)
    round_2_submitted = Column(Boolean, default=False, nullable=False)
    round_2_submitted_at = Column(DateTime, nullable=True)
    follow_up_submitted = Column(Boolean, default=False, nullable=False)
    follow_up_submitted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
        UniqueConstraint("session_id", "participant_id", name="uq_session_participant"),
    )

    session = relationship("ClassroomSession", back_populates="participations")
