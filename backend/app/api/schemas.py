"""Pydantic request and response models for CleanSlate REST API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(min_length=6)
    role: str = Field(default="analyst")


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in_minutes: int


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    created_at: str


# Dataset Schemas
class DatasetResponse(BaseModel):
    id: str
    owner_id: str
    filename: str
    sha256_original: str
    canonical_hash: str
    format: str
    rows: int
    cols: int
    size_bytes: int
    created_at: str
    quarantined_count: int = 0


class UploadGuardResponse(BaseModel):
    is_valid: bool
    error_code: Optional[str] = None
    message: str
    dataset: Optional[DatasetResponse] = None
    quarantined_count: int = 0
    null_bytes_stripped: int = 0
    formula_injection_cells_detected: int = 0


# Run Schemas
class CreateRunRequest(BaseModel):
    llm_mode: str = Field(default="heuristic")  # "none" | "heuristic" | "openai_compatible"
    config: Dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    dataset_id: str
    status: str
    llm_mode: str
    config_json: str
    created_at: str
    updated_at: str


# Rules & Plan Schemas
class RuleUpdateRequest(BaseModel):
    status: str = Field(description="'active', 'rejected_by_user', 'needs_review'")


class PlanStepUpdateRequest(BaseModel):
    approved: bool


class ApplyPlanRequest(BaseModel):
    approved_step_ids: Optional[List[str]] = None


class RollbackRequest(BaseModel):
    to_seq: Optional[int] = None
    all_steps: bool = False


class RollbackResponse(BaseModel):
    success: bool
    hash_original: str
    hash_current: str
    matches_original: bool
    reverted_steps_count: int
    message: str


# Generic Error Schema
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
