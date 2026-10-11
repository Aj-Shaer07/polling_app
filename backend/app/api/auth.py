from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    StudentActivateRequest,
    StudentLoginRequest,
    UserResponse,
    Token,
)
from app.services.auth import verify_password, create_access_token
from app.services.roster import activate_student_account, is_student_eligible
from app.services.audit import log_audit_event
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.username == login_data.username) | (User.email == login_data.username))
        .first()
    )
    if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    token = create_access_token({"sub": user.id, "role": user.role.value, "username": user.username})
    set_auth_cookie(response, token)

    log_audit_event(
        db=db,
        action="USER_LOGIN",
        resource_type="users",
        resource_id=user.id,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username,
        student_id=user.student_id,
    )


@router.post("/student-activate", response_model=Token)
def student_activate(
    act_data: StudentActivateRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    user = activate_student_account(
        db=db,
        student_id=act_data.student_id,
        new_password=act_data.new_password,
        ip_address=request.client.host if request.client else None,
    )

    token = create_access_token({"sub": user.id, "role": user.role.value, "username": user.username})
    set_auth_cookie(response, token)

    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username,
        student_id=user.student_id,
    )


@router.post("/student-login", response_model=Token)
def student_login(
    login_data: StudentLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    norm_id = login_data.student_id.strip().upper()
    user = db.query(User).filter(User.student_id == norm_id, User.role == UserRole.STUDENT).first()
    if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password. If this is your first time, please activate your account.",
        )

    token = create_access_token({"sub": user.id, "role": user.role.value, "username": user.username})
    set_auth_cookie(response, token)

    log_audit_event(
        db=db,
        action="STUDENT_LOGIN",
        resource_type="users",
        resource_id=user.id,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        username=user.username,
        student_id=user.student_id,
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
