from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.roster import EligibleStudent
from app.models.user import User, UserRole
from app.services.auth import generate_activation_code, hash_password, verify_password
from app.services.audit import log_audit_event


def get_standard_eligible_student_ids() -> List[str]:
    """
    Programmatically returns exactly the 45 eligible student IDs:
    - 241AI001 through 241AI044 (44 IDs)
    - 231AI007 (1 ID)
    Total: exactly 45 IDs.
    """
    ids = [f"241AI{i:03d}" for i in range(1, 45)]
    ids.append("231AI007")
    return sorted(ids)


def initialize_roster(db: Session, force_reset: bool = False) -> List[Dict[str, str]]:
    """
    Initializes the eligible roster table with the exact 45 student IDs.
    """
    standard_ids = get_standard_eligible_student_ids()
    assert len(standard_ids) == 45, f"Roster must be exactly 45, got {len(standard_ids)}"
    assert "241AI045" not in standard_ids, "241AI045 must NOT be eligible"

    existing_count = db.query(EligibleStudent).count()
    if existing_count > 0 and not force_reset:
        return []

    if force_reset:
        db.query(EligibleStudent).delete()
        db.commit()

    roster_list: List[Dict[str, str]] = []

    for s_id in standard_ids:
        student_record = EligibleStudent(
            student_id=s_id,
            activation_code_hash=None,
            is_activated=False,
            activated_at=None,
        )
        db.add(student_record)
        roster_list.append({
            "student_id": s_id,
            "activation_code": "NOT_REQUIRED",
            "is_activated": False,
        })

    db.commit()

    log_audit_event(
        db=db,
        action="ROSTER_INITIALIZED",
        resource_type="eligible_students",
        details={"count": len(roster_list)},
    )

    return roster_list


def is_student_eligible(db: Session, student_id: str) -> bool:
    normalized = student_id.strip().upper()
    return db.query(EligibleStudent).filter(EligibleStudent.student_id == normalized).first() is not None


def get_roster_status(db: Session) -> List[EligibleStudent]:
    return db.query(EligibleStudent).order_by(EligibleStudent.student_id).all()


def activate_student_account(
    db: Session,
    student_id: str,
    new_password: str,
    ip_address: Optional[str] = None
) -> User:
    normalized_id = student_id.strip().upper()
    
    # 1. Check eligibility: must be in the 45 approved roster
    record = db.query(EligibleStudent).filter(EligibleStudent.student_id == normalized_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student ID is not eligible for this platform.",
        )
    
    # 2. Check if already activated
    if record.is_activated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This student identity has already set their password. Please sign in directly.",
        )
    
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )
    
    # 3. Mark student as activated
    record.is_activated = True
    record.activated_at = datetime.now(timezone.utc)
    
    # 4. Create or update user record
    existing_user = db.query(User).filter(User.student_id == normalized_id).first()
    if existing_user:
        existing_user.hashed_password = hash_password(new_password)
        existing_user.is_active = True
        user = existing_user
    else:
        user = User(
            username=normalized_id,
            student_id=normalized_id,
            hashed_password=hash_password(new_password),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    log_audit_event(
        db=db,
        action="STUDENT_ACTIVATED",
        resource_type="users",
        resource_id=user.id,
        user_id=user.id,
        details={"student_id": normalized_id},
        ip_address=ip_address,
    )
    
    return user


def reset_student_activation(db: Session, student_id: str, admin_user_id: str) -> EligibleStudent:
    normalized_id = student_id.strip().upper()
    record = db.query(EligibleStudent).filter(EligibleStudent.student_id == normalized_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student ID {normalized_id} not found in eligible roster.",
        )
    
    # Reset activation state in eligible roster
    record.is_activated = False
    record.activated_at = None
    
    # Remove student user account so the student can perform a clean activation
    user = db.query(User).filter(User.student_id == normalized_id, User.role == UserRole.STUDENT).first()
    if user:
        db.delete(user)
    
    db.commit()
    db.refresh(record)
    
    log_audit_event(
        db=db,
        action="STUDENT_ACTIVATION_RESET",
        resource_type="eligible_students",
        resource_id=record.id,
        user_id=admin_user_id,
        details={"student_id": normalized_id},
    )
    
    return record

