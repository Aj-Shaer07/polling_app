import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class QuestionType(str, enum.Enum):
    FACTUAL = "FACTUAL"
    SUBJECTIVE = "SUBJECTIVE"
    PREDICTION = "PREDICTION"
    OPEN_REASONING = "OPEN_REASONING"


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("classroom_sessions.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(SAEnum(QuestionType, name="question_type_enum"), nullable=False, default=QuestionType.FACTUAL)
    reference_answer = Column(Text, nullable=True)
    accepted_reasoning = Column(Text, nullable=True)
    choices = Column(JSON, nullable=True)  # List of choices e.g. ["Option A", "Option B", ...]
    confidence_required = Column(Boolean, default=True, nullable=False)
    reasoning_required = Column(Boolean, default=True, nullable=False)
    prediction_enabled = Column(Boolean, default=False, nullable=False)
    order_index = Column(Integer, default=1, nullable=False)
    is_follow_up = Column(Boolean, default=False, nullable=False)
    status = Column(String(30), default="DRAFT", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = relationship("ClassroomSession", back_populates="questions")
    responses = relationship("StudentResponse", back_populates="question", cascade="all, delete-orphan")
    reasoning_categories = relationship("ReasoningCategory", back_populates="question", cascade="all, delete-orphan")
    challenge_proposals = relationship("ChallengeProposal", back_populates="question", cascade="all, delete-orphan")
