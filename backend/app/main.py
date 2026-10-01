"""CleanSlate FastAPI Application Entrypoint."""
from __future__ import annotations

import re
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.types import ASGIApp, Receive, Scope, Send
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes_admin import admin_router
from app.api.routes_auth import auth_router
from app.api.routes_automation import automation_router
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
        # Seed admin users (support both titan.local and cleanslate.local)
        for email, pwd in [("admin@titan.local", "titan123!"), ("admin@cleanslate.local", "cleanslate123!")]:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, password_hash=hash_password(pwd), role="admin"))
                db.commit()
                logger.info(f"Default admin user created: {email}")
    finally:
        db.close()

    yield


app = FastAPI(
    title="TITAN API",
    description="TITAN: Autonomous, Safe, Reversible Data Cleaning Agent for Messy Enterprise Datasets",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class NormalizePathMiddleware:
    """Normalizes consecutive slashes (e.g. //api/auth/login) into single slashes."""
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if "//" in path:
                scope["path"] = re.sub(r"/+", "/", path)
        await self.app(scope, receive, send)

app.add_middleware(NormalizePathMiddleware)

# CORS middleware - supports localhost, Netlify preview & production domains
_origins = settings.cors_origins
_allow_all = "*" in _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_origin_regex=None if _allow_all else r"https://.*\.netlify\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=False if _allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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


@app.get("/", tags=["Info"])
def root():
    """API root — returns service info."""
    return {
        "service": "CleanSlate / TITAN API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/metrics", tags=["Observability"])
def prometheus_metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Mount API routers under /api (for frontend SPA and Nginx reverse proxy)
api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(runs_router)
api_router.include_router(admin_router)
api_router.include_router(health_router)
api_router.include_router(automation_router)
app.include_router(api_router)

# Mount routers at root for direct calls and test compatibility
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(runs_router)
app.include_router(admin_router)
app.include_router(health_router)
app.include_router(automation_router)
