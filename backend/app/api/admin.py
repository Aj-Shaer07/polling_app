from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.roster import EligibleStudent
from app.models.audit import AuditLog
from app.schemas.auth import ProfessorCreateRequest, UserResponse
from app.schemas.roster import EligibleStudentResponse, RosterBootstrapResponse, RosterItemWithCode
from app.schemas.audit import AuditLogResponse
from app.services.auth import hash_password
from app.services.roster import initialize_roster, get_roster_status, reset_student_activation
from app.services.audit import log_audit_event
from app.api.deps import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/roster", response_model=List[EligibleStudentResponse])
def get_roster(db: Session = Depends(get_db)):
    """Inspect all eligible student records and their activation status."""
    return get_roster_status(db)


@router.post("/roster/{student_id}/reset-activation", response_model=EligibleStudentResponse)
def reset_student(
    student_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin reset of student activation status, permitting student to claim account freshly."""
    return reset_student_activation(db=db, student_id=student_id, admin_user_id=current_admin.id)


@router.post("/roster/bootstrap", response_model=RosterBootstrapResponse)
def bootstrap_roster(
    force_reset: bool = Query(False, description="Whether to overwrite existing roster"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Initializes the exact 45-student eligible roster:
    - 241AI001 to 241AI044
    - 231AI007
    Generates secure one-time activation codes for administrative distribution.
    """
    codes = initialize_roster(db=db, force_reset=force_reset)
    if not codes and not force_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Roster already initialized. Use force_reset=true to regenerate.",
        )

    return RosterBootstrapResponse(
        total_eligible=len(codes),
        students=[RosterItemWithCode(**item) for item in codes],
    )


@router.post("/professors", response_model=UserResponse)
def create_professor(
    prof_data: ProfessorCreateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a professor account."""
    existing = db.query(User).filter(
        (User.username == prof_data.username) | (User.email == prof_data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that username or email already exists.",
        )

    prof = User(
        username=prof_data.username,
        email=prof_data.email,
        hashed_password=hash_password(prof_data.password),
        role=UserRole.PROFESSOR,
        is_active=True,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)

    log_audit_event(
        db=db,
        action="PROFESSOR_CREATED",
        resource_type="users",
        resource_id=prof.id,
        user_id=current_admin.id,
        details={"username": prof.username, "email": prof.email},
    )

    return prof


@router.get("/professors", response_model=List[UserResponse])
def list_professors(db: Session = Depends(get_db)):
    """List all registered professors."""
    return db.query(User).filter(User.role == UserRole.PROFESSOR).all()


@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_trail(limit: int = 100, db: Session = Depends(get_db)):
    """Inspect system audit trail."""
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/health")
def admin_health(db: Session = Depends(get_db)):
    total_eligible = db.query(EligibleStudent).count()
    activated = db.query(EligibleStudent).filter(EligibleStudent.is_activated == True).count()
    total_professors = db.query(User).filter(User.role == UserRole.PROFESSOR).count()
    return {
        "status": "healthy",
        "eligible_roster_count": total_eligible,
        "activated_students": activated,
        "professors_count": total_professors,
    }
