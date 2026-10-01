"""Pipeline run routes: profiling, inference, planning, loss, execution, rollback, tests, export."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import (
    ApplyPlanRequest,
    CreateRunRequest,
    PlanStepUpdateRequest,
    RollbackRequest,
    RollbackResponse,
    RuleUpdateRequest,
    RunResponse,
)
from app.api.sse import broadcaster, sse_event_generator
from app.config import settings
from app.db.models import (
    AuditEvent,
    Dataset,
    LedgerEntryModel,
    PlanStepModel,
    Profile,
    RuleModel,
    Run,
    TestResultModel,
    TestRunModel,
    User,
)
from app.db.session import get_db
from app.execution.canonical_hash import compute_canonical_hash
from app.execution.executor import PipelineExecutor
from app.execution.ledger import TransformationLedger
from app.execution.rollback import RollbackEngine
from app.inference.dsl import Rule, RuleKind, RuleSource, RuleStatus
from app.inference.semantic import run_semantic_inference
from app.ingestion.readers import read_dataset_file
from app.loss.estimator import (
    calculate_loss_between_frames,
    compare_predicted_vs_actual,
    estimate_pipeline_cumulative_loss,
)
from app.planning.planner import TransformationPlanner
from app.planning.registry import registry
from app.profiling.profiler import DatasetProfile, profile_dataset
from app.security.crypto import encryptor
from app.security.sanitize import neutralize_for_export
from app.testgen.generator import TestGenerator
from app.testgen.mutation_check import mutation_checker
from app.testgen.runner import TestRunner
from app.transforms.base import PlanStep

runs_router = APIRouter(tags=["Runs"])

# In-memory DataFrame state cache: run_id -> current_df
_ACTIVE_DFS: Dict[str, pd.DataFrame] = {}
_ACTIVE_LEDGERS: Dict[str, TransformationLedger] = {}


def _get_or_load_df(run: Run, dataset: Dataset) -> pd.DataFrame:
    """Retrieves current working DataFrame for run, or loads and decrypts from storage or Cloudinary."""
    if run.id in _ACTIVE_DFS:
        return _ACTIVE_DFS[run.id]

    # Check if cleaned cache exists for applied run
    cleaned_path = settings.storage_path / "cleaned" / f"{run.id}.parquet"
    if run.status == "applied" and cleaned_path.exists():
        try:
            cleaned_df = pd.read_parquet(cleaned_path)
            _ACTIVE_DFS[run.id] = cleaned_df
            return cleaned_df
        except Exception:
            pass

    # Decrypt from storage or fetch from Cloudinary
    enc_path = Path(dataset.stored_path)
    if enc_path.exists():
        enc_bytes = enc_path.read_bytes()
        raw_bytes = encryptor.decrypt_bytes(enc_bytes)
    elif getattr(dataset, "cloudinary_url", None):
        import urllib.request
        with urllib.request.urlopen(dataset.cloudinary_url, timeout=20) as resp:
            raw_bytes = resp.read()
    else:
        raise HTTPException(status_code=404, detail="Dataset storage file not found")

    res = read_dataset_file(raw_bytes, dataset.original_filename_sanitized)
    _ACTIVE_DFS[run.id] = res.df
    return res.df


def _get_ledger(run_id: str) -> TransformationLedger:
    if run_id not in _ACTIVE_LEDGERS:
        _ACTIVE_LEDGERS[run_id] = TransformationLedger(run_id=run_id)
    return _ACTIVE_LEDGERS[run_id]


def _get_or_create_active_run(dataset: Dataset, db: Session, llm_mode: str = "heuristic") -> Run:
    """Returns the most recent Run for dataset, or creates a new one if absent."""
    run = db.query(Run).filter(Run.dataset_id == dataset.id).order_by(Run.created_at.desc()).first()
    if not run:
        run = Run(
            dataset_id=dataset.id,
            status="created",
            llm_mode=llm_mode,
            config_json="{}",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
    return run


@runs_router.get("/datasets/{dataset_id}/runs", response_model=List[RunResponse])
def get_dataset_runs(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RunResponse]:
    """Retrieves all pipeline runs for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    runs = db.query(Run).filter(Run.dataset_id == dataset.id).order_by(Run.created_at.desc()).all()
    if not runs:
        initial_run = _get_or_create_active_run(dataset, db)
        runs = [initial_run]

    return [
        RunResponse(
            id=run.id,
            dataset_id=run.dataset_id,
            status=run.status,
            llm_mode=run.llm_mode,
            config_json=run.config_json or "{}",
            created_at=run.created_at.isoformat() if run.created_at else "",
            updated_at=run.updated_at.isoformat() if run.updated_at else "",
        )
        for run in runs
    ]


@runs_router.get("/datasets/{dataset_id}/profile")
@runs_router.post("/datasets/{dataset_id}/profile")
def get_or_run_dataset_profile(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves or automatically computes profile for dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = _get_or_create_active_run(dataset, db)
    prof_record = db.query(Profile).filter(Profile.run_id == run.id).first()
    if prof_record:
        try:
            return json.loads(prof_record.profile_json)
        except Exception:
            pass

    df = _get_or_load_df(run, dataset)
    profile = profile_dataset(df)
    prof_dict = profile.to_dict()
    prof_json = json.dumps(prof_dict)

    if prof_record:
        prof_record.profile_json = prof_json
        prof_record.fingerprint = profile.fingerprint
    else:
        db.add(Profile(run_id=run.id, profile_json=prof_json, fingerprint=profile.fingerprint))

    run.status = "profiled"
    db.commit()
    return prof_dict


@runs_router.get("/datasets/{dataset_id}/rules")
def get_dataset_rules(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves inferred rules for dataset, auto-inferring if not yet done."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = _get_or_create_active_run(dataset, db)
    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    if not rule_models:
        df = _get_or_load_df(run, dataset)
        prof_record = db.query(Profile).filter(Profile.run_id == run.id).first()
        if prof_record:
            prof = profile_dataset(df)
        else:
            prof = profile_dataset(df)
            db.add(Profile(run_id=run.id, profile_json=json.dumps(prof.to_dict()), fingerprint=prof.fingerprint))
            db.commit()

        _, rules = run_semantic_inference(prof, df)
        for r in rules:
            rm = RuleModel(
                id=r.id,
                run_id=run.id,
                kind=r.kind.value,
                columns_json=json.dumps(r.columns),
                params_json=json.dumps(r.params),
                support=r.support,
                confidence=r.confidence,
                source=r.source.value,
                status=r.status.value,
                evidence=r.evidence,
            )
            db.add(rm)
        run.status = "inferred"
        db.commit()
        rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()

    resp = []
    for rm in rule_models:
        resp.append({
            "id": rm.id,
            "kind": rm.kind,
            "columns": json.loads(rm.columns_json),
            "params": json.loads(rm.params_json),
            "support": rm.support,
            "confidence": rm.confidence,
            "source": rm.source,
            "status": rm.status,
            "evidence": rm.evidence,
        })
    return resp


@runs_router.post("/datasets/{dataset_id}/infer")
def infer_dataset_rules(
    dataset_id: str,
    req: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Infers semantic rules for dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = _get_or_create_active_run(dataset, db)
    df = _get_or_load_df(run, dataset)
    prof = profile_dataset(df)

    existing_prof = db.query(Profile).filter(Profile.run_id == run.id).first()
    if existing_prof:
        existing_prof.profile_json = json.dumps(prof.to_dict())
        existing_prof.fingerprint = prof.fingerprint
    else:
        db.add(Profile(run_id=run.id, profile_json=json.dumps(prof.to_dict()), fingerprint=prof.fingerprint))

    semantics, rules = run_semantic_inference(prof, df)
    db.query(RuleModel).filter(RuleModel.run_id == run.id).delete()
    for r in rules:
        rm = RuleModel(
            id=r.id,
            run_id=run.id,
            kind=r.kind.value,
            columns_json=json.dumps(r.columns),
            params_json=json.dumps(r.params),
            support=r.support,
            confidence=r.confidence,
            source=r.source.value,
            status=r.status.value,
            evidence=r.evidence,
        )
        db.add(rm)

    run.status = "inferred"
    db.commit()

    return {
        "column_semantics": semantics,
        "inferred_count": len(rules),
        "rules_count": len(rules),
        "rules": [r.to_dict() for r in rules],
    }


@runs_router.post("/datasets/{dataset_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    dataset_id: str,
    req: CreateRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    """Creates a new cleaning and planning run for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = Run(
        dataset_id=dataset.id,
        status="created",
        llm_mode=req.llm_mode or "heuristic",
        config_json=json.dumps(req.config),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status,
        llm_mode=run.llm_mode,
        config_json=run.config_json,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


@runs_router.get("/runs", response_model=List[RunResponse])
def list_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RunResponse]:
    """Retrieves all pipeline runs belonging to current user (or all if admin)."""
    if current_user.role == "admin":
        runs = db.query(Run).order_by(Run.created_at.desc()).all()
    else:
        runs = (
            db.query(Run)
            .join(Dataset, Run.dataset_id == Dataset.id)
            .filter(Dataset.owner_id == current_user.id)
            .order_by(Run.created_at.desc())
            .all()
        )
    return [
        RunResponse(
            id=run.id,
            dataset_id=run.dataset_id,
            status=run.status,
            llm_mode=run.llm_mode,
            config_json=run.config_json or "{}",
            created_at=run.created_at.isoformat() if run.created_at else "",
            updated_at=run.updated_at.isoformat() if run.updated_at else "",
        )
        for run in runs
    ]


@runs_router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    """Retrieves pipeline run details."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status,
        llm_mode=run.llm_mode,
        config_json=run.config_json,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


@runs_router.post("/runs/{run_id}/profile")
def run_profile(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Executes deep dataset profiling on the raw data."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    profile = profile_dataset(df)

    # Persist or update Profile
    existing_prof = db.query(Profile).filter(Profile.run_id == run.id).first()
    prof_dict = profile.to_dict()
    prof_json = json.dumps(prof_dict)

    if existing_prof:
        existing_prof.profile_json = prof_json
        existing_prof.fingerprint = profile.fingerprint
    else:
        db.add(Profile(run_id=run.id, profile_json=prof_json, fingerprint=profile.fingerprint))

    run.status = "profiled"
    db.commit()

    return prof_dict


@runs_router.get("/runs/{run_id}/profile")
def get_profile(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves saved profile for run."""
    prof = db.query(Profile).join(Run).join(Dataset).filter(Profile.run_id == run_id, Dataset.owner_id == current_user.id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found for this run")
    return json.loads(prof.profile_json)


@runs_router.post("/runs/{run_id}/infer")
def run_inference(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Induces candidate rules, empirical support, and semantic tags."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    profile_record = db.query(Profile).filter(Profile.run_id == run.id).first()
    if not profile_record:
        # Auto-profile if not profiled yet
        prof = profile_dataset(df)
        db.add(Profile(run_id=run.id, profile_json=json.dumps(prof.to_dict()), fingerprint=prof.fingerprint))
        db.commit()
    else:
        prof = profile_dataset(df)

    semantics, rules = run_semantic_inference(prof, df)

    # Clear previous rules
    db.query(RuleModel).filter(RuleModel.run_id == run.id).delete()

    for r in rules:
        rm = RuleModel(
            id=r.id,
            run_id=run.id,
            kind=r.kind.value,
            columns_json=json.dumps(r.columns),
            params_json=json.dumps(r.params),
            support=r.support,
            confidence=r.confidence,
            source=r.source.value,
            status=r.status.value,
            evidence=r.evidence,
        )
        db.add(rm)

    run.status = "inferred"
    db.commit()

    return {
        "column_semantics": semantics,
        "rules_count": len(rules),
        "rules": [r.to_dict() for r in rules],
    }


@runs_router.get("/runs/{run_id}/rules")
def get_rules(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists inferred rules for run."""
    rule_models = db.query(RuleModel).join(Run).join(Dataset).filter(RuleModel.run_id == run_id, Dataset.owner_id == current_user.id).all()
    resp = []
    for rm in rule_models:
        resp.append({
            "id": rm.id,
            "run_id": rm.run_id,
            "kind": rm.kind,
            "columns": json.loads(rm.columns_json),
            "params": json.loads(rm.params_json),
            "support": rm.support,
            "confidence": rm.confidence,
            "source": rm.source,
            "status": rm.status,
            "evidence": rm.evidence,
        })
    return resp


@runs_router.patch("/runs/{run_id}/rules/{rule_id}")
def update_rule(
    run_id: str,
    rule_id: str,
    req: RuleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Allows user to explicitly approve or reject a candidate rule."""
    rule = db.query(RuleModel).join(Run).join(Dataset).filter(RuleModel.id == rule_id, RuleModel.run_id == run_id, Dataset.owner_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = req.status
    db.commit()
    return {"id": rule.id, "status": rule.status}


@runs_router.post("/runs/{run_id}/plan")
def generate_plan(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generates a dependency-ordered transformation plan with pre-execution loss estimates."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    prof = profile_dataset(df)

    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    domain_rules = []
    for rm in rule_models:
        domain_rules.append(
            Rule(
                id=rm.id,
                kind=RuleKind(rm.kind),
                columns=json.loads(rm.columns_json),
                params=json.loads(rm.params_json),
                support=rm.support,
                confidence=rm.confidence,
                evidence=rm.evidence,
                source=RuleSource(rm.source),
                status=RuleStatus(rm.status),
            )
        )

    planner = TransformationPlanner()
    plan_steps = planner.generate_plan(df, prof, domain_rules)

    # Compute compound cumulative pipeline loss
    cum_report, _ = estimate_pipeline_cumulative_loss(df, plan_steps)

    # Persist PlanSteps
    db.query(PlanStepModel).filter(PlanStepModel.run_id == run.id).delete()
    for step in plan_steps:
        psm = PlanStepModel(
            id=step.id,
            run_id=run.id,
            seq=step.seq,
            transformation=step.transformation,
            params_json=json.dumps(step.params),
            rationale=step.rationale,
            requires_approval=step.requires_approval,
            approved=step.approved,
            predicted_loss_json=json.dumps(step.predicted_loss.to_dict()),
            loss_score=step.predicted_loss.loss_score,
            loss_label=step.predicted_loss.loss_label,
            status=step.status,
        )
        db.add(psm)

    run.status = "planned"
    db.commit()

    return {
        "steps": [s.to_dict() for s in plan_steps],
        "cumulative_loss": cum_report.to_dict(),
    }


@runs_router.get("/runs/{run_id}/plan")
def get_plan(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves plan steps and compound cumulative loss."""
    steps = db.query(PlanStepModel).join(Run).join(Dataset).filter(PlanStepModel.run_id == run_id, Dataset.owner_id == current_user.id).order_by(PlanStepModel.seq).all()
    if not steps:
        try:
            return generate_plan(run_id, current_user, db)
        except Exception:
            pass

    resp_steps = []
    for s in steps:
        resp_steps.append({
            "id": s.id,
            "seq": s.seq,
            "transformation": s.transformation,
            "params": json.loads(s.params_json),
            "rationale": s.rationale,
            "requires_approval": s.requires_approval,
            "approved": s.approved,
            "loss_score": s.loss_score,
            "loss_label": s.loss_label,
            "predicted_loss": json.loads(s.predicted_loss_json),
            "status": s.status,
        })
    return {"steps": resp_steps}


@runs_router.patch("/runs/{run_id}/plan/{step_id}")
@runs_router.patch("/runs/{run_id}/steps/{step_id}")
def update_plan_step(
    run_id: str,
    step_id: str,
    req: PlanStepUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Approves or skips a specific transformation step."""
    step = (
        db.query(PlanStepModel)
        .join(Run)
        .join(Dataset)
        .filter(
            (PlanStepModel.id == step_id) | (PlanStepModel.seq == (int(step_id) if step_id.isdigit() else -1)),
            PlanStepModel.run_id == run_id,
            Dataset.owner_id == current_user.id,
        )
        .first()
    )
    if not step:
        # Fallback to direct run_id check
        step = db.query(PlanStepModel).filter(
            (PlanStepModel.id == step_id) | (PlanStepModel.seq == (int(step_id) if step_id.isdigit() else -1)),
            PlanStepModel.run_id == run_id
        ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Plan step not found")

    step.approved = req.approved
    step.status = "approved" if req.approved else "skipped"
    db.commit()
    return {"id": step.id, "approved": step.approved, "status": step.status}


@runs_router.post("/runs/{run_id}/plan/approve-all")
@runs_router.post("/runs/{run_id}/steps/approve-all")
def approve_all_steps(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Approves all steps in the plan in one single atomic operation."""
    steps = db.query(PlanStepModel).join(Run).join(Dataset).filter(
        PlanStepModel.run_id == run_id,
        Dataset.owner_id == current_user.id,
    ).all()
    if not steps:
        steps = db.query(PlanStepModel).filter(PlanStepModel.run_id == run_id).all()

    for s in steps:
        s.approved = True
        s.status = "approved"
    db.commit()
    return {"approved_count": len(steps), "status": "approved"}



@runs_router.post("/runs/{run_id}/apply")
def apply_plan(
    run_id: str,
    req: Optional[ApplyPlanRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Applies approved transformation steps in dependency order.
    Atomically writes ledger entries and computes actual loss metrics.
    """
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    step_models = db.query(PlanStepModel).filter(PlanStepModel.run_id == run.id).order_by(PlanStepModel.seq).all()
    if not step_models:
        raise HTTPException(status_code=400, detail="No plan steps exist to apply")

    df = _get_or_load_df(run, run.dataset)
    orig_hash = run.dataset.canonical_hash

    ledger = _get_ledger(run.id)
    executor = PipelineExecutor(ledger=ledger, actor=current_user.email)

    # Convert to domain PlanStep objects
    steps_to_run: List[PlanStep] = []
    for sm in step_models:
        if req and req.approved_step_ids is not None:
            approved = sm.id in req.approved_step_ids
        else:
            approved = sm.approved

        if approved:
            dry_dict = json.loads(sm.predicted_loss_json)
            from app.transforms.base import DryRunResult
            dry_obj = DryRunResult(**dry_dict)
            steps_to_run.append(
                PlanStep(
                    id=sm.id,
                    transformation=sm.transformation,
                    params=json.loads(sm.params_json),
                    target_columns=[],
                    rationale=sm.rationale,
                    requires_approval=sm.requires_approval,
                    predicted_loss=dry_obj,
                    seq=sm.seq,
                    approved=True,
                )
            )

    exec_res = executor.execute_plan(df, steps_to_run)
    if not exec_res.success:
        run.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {exec_res.error_message}")

    # Update in-memory active DataFrame and persist to disk cache
    _ACTIVE_DFS[run.id] = exec_res.current_df
    try:
        cleaned_dir = settings.storage_path / "cleaned"
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        exec_res.current_df.to_parquet(cleaned_dir / f"{run.id}.parquet", index=False)
    except Exception:
        pass

    # Record ledger entries in DB
    for entry in exec_res.executed_entries:
        lem = LedgerEntryModel(
            id=entry.id,
            run_id=run.id,
            seq=entry.seq,
            step_id=entry.step_id,
            hash_before=entry.hash_before,
            hash_after=entry.hash_after,
            delta_ref=entry.delta_ref,
            actual_loss_json=json.dumps(entry.actual_loss),
            applied_at=pd.Timestamp.now(tz="UTC").to_pydatetime(),
            actor=entry.actor,
            reverted=False,
        )
        db.add(lem)

        # Update step model status
        step_rec = db.query(PlanStepModel).filter(PlanStepModel.id == entry.step_id).first()
        if step_rec:
            step_rec.status = "applied"

    run.status = "applied"

    # Audit event
    audit = AuditEvent(
        actor=current_user.email,
        run_id=run.id,
        event="PLAN_APPLIED",
        details_json=json.dumps({"applied_steps": len(exec_res.executed_entries)}),
    )
    db.add(audit)
    db.commit()

    return {
        "status": "applied",
        "applied_steps_count": len(exec_res.executed_entries),
        "current_canonical_hash": compute_canonical_hash(exec_res.current_df),
    }


@runs_router.post("/runs/{run_id}/rollback", response_model=RollbackResponse)
def rollback(
    run_id: str,
    req: RollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RollbackResponse:
    """
    Rolls back applied transformations to a specific sequence or all the way to origin.
    Strictly verifies that restored hash matches the original dataset canonical hash.
    """
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    orig_hash = run.dataset.canonical_hash
    ledger = _get_ledger(run.id)
    engine = RollbackEngine(ledger=ledger, original_hash=orig_hash)

    if req.all_steps or req.to_seq is None or req.to_seq <= 1:
        res = engine.rollback_all(df)
        run.status = "rolled_back" if res.matches_original else "corrupted"
    else:
        res = engine.rollback_to(df, req.to_seq)

    _ACTIVE_DFS[run.id] = res.restored_df
    try:
        cleaned_file = settings.storage_path / "cleaned" / f"{run.id}.parquet"
        if res.matches_original:
            if cleaned_file.exists():
                cleaned_file.unlink()
        else:
            res.restored_df.to_parquet(cleaned_file, index=False)
    except Exception:
        pass

    # Sync ledger reverted flags to DB
    for entry in ledger.entries:
        if entry.reverted:
            lem = db.query(LedgerEntryModel).filter(LedgerEntryModel.seq == entry.seq, LedgerEntryModel.run_id == run.id).first()
            if lem:
                lem.reverted = True

    # Audit event
    audit = AuditEvent(
        actor=current_user.email,
        run_id=run.id,
        event="ROLLBACK",
        details_json=json.dumps({"matches_original": bool(res.matches_original), "reverted": res.reverted_steps_count}),
    )
    db.add(audit)
    db.commit()

    return RollbackResponse(
        success=res.success,
        hash_original=res.hash_original,
        hash_current=res.hash_current,
        matches_original=res.matches_original,
        reverted_steps_count=res.reverted_steps_count,
        message=res.message,
    )


@runs_router.get("/runs/{run_id}/ledger")
def get_ledger(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Returns append-only transformation ledger timeline."""
    entries = db.query(LedgerEntryModel).join(Run).join(Dataset).filter(LedgerEntryModel.run_id == run_id, Dataset.owner_id == current_user.id).order_by(LedgerEntryModel.seq).all()
    resp = []
    for e in entries:
        resp.append({
            "id": e.id,
            "seq": e.seq,
            "step_id": e.step_id,
            "hash_before": e.hash_before,
            "hash_after": e.hash_after,
            "actual_loss": json.loads(e.actual_loss_json),
            "applied_at": e.applied_at.isoformat(),
            "actor": e.actor,
            "reverted": e.reverted,
        })
    return resp


@runs_router.get("/runs/{run_id}/diff")
def get_diff(
    run_id: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves paginated before/after diff of changed cells."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    ledger = _get_ledger(run.id)
    diffs = []
    for entry in ledger.entries:
        if not entry.reverted:
            delta = ledger.get_delta(entry.delta_ref)
            if delta:
                for edit in delta.cell_edits:
                    diffs.append({
                        "rid": edit.rid,
                        "column": edit.column,
                        "old_value": edit.old_value,
                        "new_value": edit.new_value,
                        "transformation": delta.transformation,
                    })

    return {
        "total_diffs": len(diffs),
        "diffs": diffs[:limit],
    }


@runs_router.post("/runs/{run_id}/tests/generate")
def generate_tests(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Generates real Pandera, Pytest, and Integration test files on disk."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    domain_rules = [
        Rule(
            id=rm.id,
            kind=RuleKind(rm.kind),
            columns=json.loads(rm.columns_json),
            params=json.loads(rm.params_json),
            support=rm.support,
            confidence=rm.confidence,
            evidence=rm.evidence,
            source=RuleSource(rm.source),
            status=RuleStatus(rm.status),
        )
        for rm in rule_models
    ]

    generator = TestGenerator()
    suite_dir = generator.generate_suite(run.id, df, domain_rules, [])
    return {"status": "generated", "suite_path": str(suite_dir)}


@runs_router.post("/runs/{run_id}/tests/run")
def run_tests(
    run_id: str,
    stage: str = Query("post", pattern="^(pre|post)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Executes validation tests for stage (pre or post) and saves results."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    domain_rules = [
        Rule(
            id=rm.id,
            kind=RuleKind(rm.kind),
            columns=json.loads(rm.columns_json),
            params=json.loads(rm.params_json),
            support=rm.support,
            confidence=rm.confidence,
            evidence=rm.evidence,
            source=RuleSource(rm.source),
            status=RuleStatus(rm.status),
        )
        for rm in rule_models
    ]

    runner = TestRunner()
    report = runner.evaluate_rules_on_frame(df, domain_rules, stage=stage)

    # Save to database
    t_run = TestRunModel(
        run_id=run.id,
        stage=stage,
        passed=report.passed,
        failed=report.failed,
        total=report.total,
    )
    db.add(t_run)
    db.flush()

    for item in report.results:
        tr_m = TestResultModel(
            test_run_id=t_run.id,
            name=item.name,
            rule_id=item.rule_id,
            outcome=item.outcome,
            message=item.message,
        )
        db.add(tr_m)

    db.commit()
    return report.to_dict()


@runs_router.post("/runs/{run_id}/verify")
def verify_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Runs pre- and post-cleaning test suite evaluation and outputs Pandera schema code."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    domain_rules = [
        Rule(
            id=rm.id,
            kind=RuleKind(rm.kind),
            columns=json.loads(rm.columns_json),
            params=json.loads(rm.params_json),
            support=rm.support,
            confidence=rm.confidence,
            evidence=rm.evidence,
            source=RuleSource(rm.source),
            status=RuleStatus(rm.status),
        )
        for rm in rule_models
    ]

    runner = TestRunner()
    post_report = runner.evaluate_rules_on_frame(df, domain_rules, stage="post")
    pre_report = runner.evaluate_rules_on_frame(df, domain_rules, stage="pre")

    test_code = "# Auto-generated Pandera Schema & Tests\nimport pandera as pa\nfrom pandera import Column, Check, DataFrameSchema\n\n"
    try:
        generator = TestGenerator()
        suite_dir = generator.generate_suite(run.id, df, domain_rules, [])
        pandera_file = suite_dir / "test_pandera_schema.py"
        if pandera_file.exists():
            test_code = pandera_file.read_text(encoding="utf-8")
    except Exception:
        pass

    return {
        "pre_report": pre_report.to_dict(),
        "post_report": post_report.to_dict(),
        "test_code": test_code,
    }


@runs_router.post("/runs/{run_id}/mutation-test")
@runs_router.post("/runs/{run_id}/tests/mutation-check")
def run_mutation_check(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Injects synthetic faults to evaluate fault detection rate."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    rule_models = db.query(RuleModel).filter(RuleModel.run_id == run.id).all()
    domain_rules = [
        Rule(
            id=rm.id,
            kind=RuleKind(rm.kind),
            columns=json.loads(rm.columns_json),
            params=json.loads(rm.params_json),
            support=rm.support,
            confidence=rm.confidence,
            evidence=rm.evidence,
            source=RuleSource(rm.source),
            status=RuleStatus(rm.status),
        )
        for rm in rule_models
    ]

    rep = mutation_checker.run_mutation_check(df, domain_rules, k_faults=8)
    return rep.to_dict()


@runs_router.get("/runs/{run_id}/export")
def export_dataset(
    run_id: str,
    format: str = Query("auto", pattern="^(auto|csv|tsv|xlsx|json|jsonl|parquet|ledger)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Exports cleaned dataset in original or requested format with formula injection neutralization."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    df = _get_or_load_df(run, run.dataset)
    ledger_entries = db.query(LedgerEntryModel).filter(LedgerEntryModel.run_id == run.id).order_by(LedgerEntryModel.seq).all()

    from app.export.exporter import export_dataframe_to_response
    return export_dataframe_to_response(
        df=df,
        original_filename=run.dataset.original_filename_sanitized,
        detected_format=run.dataset.format,
        requested_format=format,
        ledger_entries=ledger_entries,
    )


@runs_router.get("/runs/{run_id}/data-preview")
def preview_dataset_data(
    run_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Returns sample comparison of raw input vs cleaned/current rows for UI inspection."""
    run = db.query(Run).join(Dataset).filter(Run.id == run_id, Dataset.owner_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Load raw baseline
    raw_df = pd.DataFrame()
    try:
        enc_path = Path(run.dataset.stored_path)
        if enc_path.exists():
            raw_bytes = encryptor.decrypt_bytes(enc_path.read_bytes())
            raw_df = read_dataset_file(raw_bytes, run.dataset.original_filename_sanitized).df
        elif getattr(run.dataset, "cloudinary_url", None):
            import urllib.request
            with urllib.request.urlopen(run.dataset.cloudinary_url, timeout=20) as resp:
                raw_bytes = resp.read()
                raw_df = read_dataset_file(raw_bytes, run.dataset.original_filename_sanitized).df
    except Exception:
        pass

    # Load current/cleaned
    current_df = _get_or_load_df(run, run.dataset)

    clean_cols = [c for c in current_df.columns if c != "_rid"]
    raw_cols = [c for c in raw_df.columns if c != "_rid"]
    cols = clean_cols if clean_cols else raw_cols

    raw_sample = (
        raw_df[cols].head(limit).fillna("").to_dict(orient="records")
        if not raw_df.empty and set(cols).issubset(set(raw_df.columns))
        else []
    )
    current_sample = (
        current_df[cols].head(limit).fillna("").to_dict(orient="records")
        if not current_df.empty and set(cols).issubset(set(current_df.columns))
        else []
    )

    diff_count = 0
    if raw_sample and current_sample:
        for r_row, c_row in zip(raw_sample, current_sample):
            for col in cols:
                if str(r_row.get(col, "")) != str(c_row.get(col, "")):
                    diff_count += 1

    from app.export.exporter import resolve_export_format, build_export_filename
    recommended_fmt = resolve_export_format(run.dataset.format, run.dataset.original_filename_sanitized, "auto")
    download_filename = build_export_filename(run.dataset.original_filename_sanitized, recommended_fmt)

    return {
        "run_id": run.id,
        "dataset_id": run.dataset.id,
        "filename": run.dataset.original_filename_sanitized,
        "input_format": run.dataset.format,
        "recommended_format": recommended_fmt,
        "download_filename": download_filename,
        "status": run.status,
        "is_cleaned": run.status == "applied",
        "total_rows": len(current_df),
        "columns": cols,
        "raw_sample": raw_sample,
        "current_sample": current_sample,
        "sample_mutations_count": diff_count,
    }


@runs_router.get("/runs/{run_id}/events")
async def stream_events(run_id: str) -> StreamingResponse:
    """Streams SSE pipeline events for real-time UI progress."""
    return StreamingResponse(
        sse_event_generator(run_id),
        media_type="text/event-stream",
    )
