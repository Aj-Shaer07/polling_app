import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class StudentResponse(Base):
    __tablename__ = "student_responses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    # Pseudonymous participant identifier, keeping response decoupled from student ID
    participant_id = Column(String(36), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)  # 1 for initial, 2 for revision
    answer = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=False)  # 1 to 5
    explanation = Column(Text, nullable=True)
    prediction = Column(Text, nullable=True)
    changed_answer = Column(Boolean, nullable=True)  # Round 2: whether answer changed
    change_reason = Column(Text, nullable=True)  # Round 2: self-reported reason for change/retention
    category_id = Column(String(36), ForeignKey("reasoning_categories.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("question_id", "participant_id", "round_number", name="uq_question_participant_round"),
    )

    # Relationships
    question = relationship("Question", back_populates="responses")
    category = relationship("ReasoningCategory", back_populates="responses")
