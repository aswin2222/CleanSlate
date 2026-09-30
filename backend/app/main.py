"""CleanSlate FastAPI Application Entrypoint."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes_admin import admin_router
from app.api.routes_auth import auth_router
from app.api.routes_datasets import datasets_router
from app.api.routes_runs import runs_router
from app.config import settings
from app.db.models import User
from app.db.session import Base, SessionLocal, engine
from app.logging import logger
from app.observability.health import health_router
from app.observability.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION
from app.security.auth import hash_password
from app.security.ratelimit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

    # Create default admin user if absent
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == "admin@cleanslate.local").first()
        if not admin_user:
            admin = User(
                email="admin@cleanslate.local",
                password_hash=hash_password("cleanslate123!"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user created: admin@cleanslate.local")
    finally:
        db.close()

    yield


app = FastAPI(
    title="CleanSlate API",
    description="Autonomous, Safe, Reversible Data Cleaning Agent for Messy Enterprise Datasets",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    path = request.url.path
    # Group dynamic run/dataset IDs in path for clean metric cardinality
    for prefix in ("/runs/", "/datasets/"):
        if prefix in path:
            parts = path.split("/")
            if len(parts) >= 3:
                parts[2] = "{id}"
            path = "/".join(parts)

    HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=path, status_code=str(response.status_code)).inc()
    HTTP_REQUEST_DURATION.labels(method=request.method, endpoint=path).observe(duration)
    return response


@app.get("/metrics", tags=["Observability"])
def prometheus_metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Mount routers
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(runs_router)
app.include_router(admin_router)
app.include_router(health_router)
