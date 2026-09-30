"""SQLAlchemy models representing the CleanSlate relational schema."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst", nullable=False)  # admin | analyst | auditor
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename_sanitized = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    sha256_original = Column(String(64), nullable=False)
    canonical_hash = Column(String(64), nullable=False)
    format = Column(String(32), nullable=False)  # csv | tsv | json | jsonl | xlsx | parquet
    rows = Column(Integer, default=0, nullable=False)
    cols = Column(Integer, default=0, nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    encrypted = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    owner = relationship("User", back_populates="datasets")
    quarantine_rows = relationship("QuarantineRow", back_populates="dataset", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="dataset", cascade="all, delete-orphan")


class QuarantineRow(Base):
    __tablename__ = "quarantine_rows"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    reason = Column(String(512), nullable=False)

    dataset = relationship("Dataset", back_populates="quarantine_rows")


class Run(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    # created | profiled | inferred | planned | applied | rolled_back | failed | corrupted
    status = Column(String(32), default="created", nullable=False)
    llm_mode = Column(String(32), default="heuristic", nullable=False)
    config_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="runs")
    profile = relationship("Profile", back_populates="run", uselist=False, cascade="all, delete-orphan")
    rules = relationship("RuleModel", back_populates="run", cascade="all, delete-orphan")
    plan_steps = relationship("PlanStepModel", back_populates="run", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntryModel", back_populates="run", cascade="all, delete-orphan")
    test_runs = relationship("TestRunModel", back_populates="run", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    profile_json = Column(Text, nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)

    run = relationship("Run", back_populates="profile")


class RuleModel(Base):
    __tablename__ = "rules"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(50), nullable=False)
    columns_json = Column(Text, nullable=False)
    params_json = Column(Text, default="{}", nullable=False)
    support = Column(Float, default=0.0, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    source = Column(String(32), default="deterministic", nullable=False)
    # active | needs_review | insufficient_evidence | rejected_by_user
    status = Column(String(32), default="active", nullable=False)
    evidence = Column(Text, default="", nullable=False)

    run = relationship("Run", back_populates="rules")


class PlanStepModel(Base):
    __tablename__ = "plan_steps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    seq = Column(Integer, nullable=False)
    transformation = Column(String(100), nullable=False)
    params_json = Column(Text, default="{}", nullable=False)
    rationale = Column(Text, default="", nullable=False)
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved = Column(Boolean, default=True, nullable=False)
    predicted_loss_json = Column(Text, default="{}", nullable=False)
    loss_score = Column(Float, default=0.0, nullable=False)
    loss_label = Column(String(20), default="LOW", nullable=False)
    # pending | approved | applied | skipped
    status = Column(String(32), default="pending", nullable=False)

    run = relationship("Run", back_populates="plan_steps")


class LedgerEntryModel(Base):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    seq = Column(Integer, nullable=False)
    step_id = Column(String(36), nullable=False)
    hash_before = Column(String(64), nullable=False)
    hash_after = Column(String(64), nullable=False)
    delta_ref = Column(String(128), nullable=False)
    actual_loss_json = Column(Text, default="{}", nullable=False)
    applied_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    actor = Column(String(100), default="system", nullable=False)
    reverted = Column(Boolean, default=False, nullable=False)

    run = relationship("Run", back_populates="ledger_entries")


class TestRunModel(Base):
    __tablename__ = "test_runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(20), nullable=False)  # pre | post
    passed = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)
    junit_ref = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    run = relationship("Run", back_populates="test_runs")
    test_results = relationship("TestResultModel", back_populates="test_run", cascade="all, delete-orphan")


class TestResultModel(Base):
    __tablename__ = "test_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_run_id = Column(String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    rule_id = Column(String(36), nullable=True)
    outcome = Column(String(20), nullable=False)  # PASSED | FAILED
    message = Column(Text, default="", nullable=False)

    test_run = relationship("TestRunModel", back_populates="test_results")


class AuditEvent(Base):
    """Append-only audit table. No update or delete operations permitted."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    ts = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    actor = Column(String(100), nullable=False)
    run_id = Column(String(36), nullable=True, index=True)
    event = Column(String(100), nullable=False)  # INGEST | PROFILE | APPLY | ROLLBACK | REJECT
    details_json = Column(Text, default="{}", nullable=False)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    ts = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    config_json = Column(Text, nullable=False)
    results_json = Column(Text, nullable=False)
