"""FastAPI dependencies for authentication, database session, and role enforcement."""
from __future__ import annotations

from typing import Callable, Generator, Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.security.auth import decode_token

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token: Optional[str] = Query(None, description="Optional access token query parameter"),
    db: Session = Depends(get_db),
) -> User:
    """Extracts and verifies JWT token from Bearer header or query param, returning User instance."""
    raw_token = None
    if auth_header and auth_header.credentials:
        raw_token = auth_header.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_REQUIRED", "message": "Missing authentication token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(raw_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_INVALID", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User account no longer exists"},
        )

    return user


def require_role(allowed_roles: list[str]) -> Callable[[User], User]:
    """Dependency factory checking user has one of allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Operation requires role in {allowed_roles}, user has '{current_user.role}'",
                },
            )
        return current_user

    return role_checker
