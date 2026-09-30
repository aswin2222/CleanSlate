"""Liveness and Readiness health endpoints."""
from __future__ import annotations

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db

health_router = APIRouter(tags=["Health"])


@health_router.get("/health/live", status_code=status.HTTP_200_OK)
def liveness() -> Dict[str, str]:
    """Kubernetes liveness probe: returns 200 if ASGI process is up."""
    return {"status": "live"}


@health_router.get("/health/ready", status_code=status.HTTP_200_OK)
def readiness(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Kubernetes readiness probe: tests database connection and storage writeability.
    """
    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity failure: {str(e)}",
        )

    # 2. Storage writeability check
    try:
        test_file = settings.storage_path / ".health_check.tmp"
        test_file.write_text("health_ok", encoding="utf-8")
        if test_file.exists():
            test_file.unlink()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage directory write failure: {str(e)}",
        )

    return {"status": "ready"}


@health_router.get("/health", status_code=status.HTTP_200_OK)
def overall_health(db: Session = Depends(get_db)) -> Dict[str, str]:
    """Overall health check returning system and DB status."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "healthy", "database": db_status}
