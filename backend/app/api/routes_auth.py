"""Authentication routes for registration, login, and identity verification."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.db.models import AuditEvent, User
from app.db.session import get_db
from app.security.auth import create_access_token, create_refresh_token, hash_password, verify_password

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Registers a new user account."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "EMAIL_EXISTS", "message": "Email is already registered"},
        )

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role or "analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit event
    audit = AuditEvent(actor=user.email, event="USER_REGISTERED", details_json=f'{{"role": "{user.role}"}}')
    db.add(audit)
    db.commit()

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticates user credentials and issues signed JWT tokens."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id)

    audit = AuditEvent(actor=user.email, event="USER_LOGIN", details_json='{"status": "success"}')
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_minutes=60,
    )


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns profile for currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at.isoformat(),
    )
