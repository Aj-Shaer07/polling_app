import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ChallengeStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"


class ReasoningCategory(Base):
    __tablename__ = "reasoning_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, default=1, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    is_misconception = Column(Boolean, default=False, nullable=False)
    sample_explanations = Column(JSON, default=list, nullable=False)
    response_count = Column(Integer, default=0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    is_ai_proposed = Column(Boolean, default=True, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="reasoning_categories")
    responses = relationship("StudentResponse", back_populates="category")


class ChallengeProposal(Base):
    __tablename__ = "challenge_proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    challenge_type = Column(String(50), nullable=False)
    challenge_text = Column(Text, nullable=False)
    targeted_reasoning_pattern = Column(Text, nullable=False)
    relevance_evidence = Column(Text, nullable=False)
    learning_objective = Column(Text, nullable=False)
    assumptions_and_uncertainties = Column(Text, nullable=False)
    status = Column(SAEnum(ChallengeStatus, name="challenge_status_enum"), default=ChallengeStatus.PROPOSED, nullable=False)
    edited_text = Column(Text, nullable=True)
    instructor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    question = relationship("Question", back_populates="challenge_proposals")
