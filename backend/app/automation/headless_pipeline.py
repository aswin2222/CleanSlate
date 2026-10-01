"""TITAN Headless Autonomous Cleaning Pipeline.

Executes end-to-end ingestion, profiling, semantic inference, planning,
auto-approval, atomic execution, ledger tracking, and format-matched export
without requiring any manual UI approvals.
"""
from __future__ import annotations

import io
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from app.export.exporter import (
    build_export_filename,
    export_dataframe_to_response,
    resolve_export_format,
)
from app.execution.executor import PipelineExecutor
from app.execution.ledger import TransformationLedger
from app.inference.semantic import run_semantic_inference
from app.ingestion.readers import read_dataset_file
from app.logging import logger
from app.planning.planner import TransformationPlanner
from app.profiling.profiler import profile_dataset
from app.execution.canonical_hash import compute_canonical_hash
from app.transforms.base import PlanStep


@dataclass
class HeadlessCleanResult:
    """Outcome of an autonomous dataset cleaning run."""
    run_id: str
    original_filename: str
    cleaned_filename: str
    target_format: str
    cleaned_bytes: bytes
    initial_rows: int
    cleaned_rows: int
    initial_columns: int
    cleaned_columns: int
    rows_dropped: int
    cells_modified: int
    steps_applied: List[Dict[str, Any]]
    initial_hash: str
    cleaned_hash: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


def clean_dataset_headless(
    file_bytes: bytes,
    original_filename: str,
    run_id: Optional[str] = None,
) -> HeadlessCleanResult:
    """
    Autonomously executes the complete TITAN data pipeline on raw file bytes.
    No human approval or UI interaction required.
    """
    start_time = time.perf_counter()
    active_run_id = run_id or f"auto_{uuid.uuid4().hex[:12]}"
    logger.info(f"[HeadlessPipeline] Starting autonomous run {active_run_id} for '{original_filename}'")

    try:
        # 1. Ingestion & Format Detection
        ingestion_result = read_dataset_file(file_bytes, original_filename)
        raw_df = ingestion_result.df
        detected_format = ingestion_result.detected_format or "csv"
        initial_hash = compute_canonical_hash(raw_df)
        initial_rows = len(raw_df)
        initial_cols = len(raw_df.columns)

        logger.info(
            f"[HeadlessPipeline] Ingested '{original_filename}' ({detected_format}): "
            f"{initial_rows} rows, {initial_cols} cols"
        )

        # 2. Deep Profiling
        profile = profile_dataset(raw_df)

        # 3. Semantic Inference & Candidate Verification
        _semantics, verified_rules = run_semantic_inference(profile, raw_df)
        logger.info(f"[HeadlessPipeline] Inferred {len(verified_rules)} verified domain rules")

        # 4. Dependency-Ordered Transformation Planning
        planner = TransformationPlanner()
        plan_steps: List[PlanStep] = planner.generate_plan(raw_df, profile, verified_rules)
        logger.info(f"[HeadlessPipeline] Generated plan with {len(plan_steps)} transformation steps")

        # 5. Headless Autonomous Auto-Approval
        # In headless automated mode, all verified and recommended plan steps are approved
        for step in plan_steps:
            step.approved = True
            step.status = "approved"

        # 6. Pipeline Execution with Atomic Ledger Logging
        ledger = TransformationLedger(run_id=active_run_id)
        executor = PipelineExecutor(ledger=ledger, actor="headless-email-automation")
        exec_result = executor.execute_plan(raw_df, plan_steps)

        if not exec_result.success:
            err = exec_result.error_message or "Transformation pipeline failed"
            logger.error(f"[HeadlessPipeline] Run {active_run_id} failed: {err}")
            return HeadlessCleanResult(
                run_id=active_run_id,
                original_filename=original_filename,
                cleaned_filename=original_filename,
                target_format=detected_format,
                cleaned_bytes=b"",
                initial_rows=initial_rows,
                cleaned_rows=initial_rows,
                initial_columns=initial_cols,
                cleaned_columns=initial_cols,
                rows_dropped=0,
                cells_modified=0,
                steps_applied=[],
                initial_hash=initial_hash,
                cleaned_hash="",
                duration_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error_message=err,
            )

        cleaned_df = exec_result.current_df
        cleaned_hash = compute_canonical_hash(cleaned_df)
        cleaned_rows = len(cleaned_df)
        cleaned_cols = len([c for c in cleaned_df.columns if c != "_rid"])

        # Aggregate actual loss statistics
        total_rows_dropped = initial_rows - cleaned_rows
        total_cells_modified = 0
        steps_summary: List[Dict[str, Any]] = []

        for entry in exec_result.executed_entries:
            act_loss = entry.actual_loss or {}
            total_cells_modified += act_loss.get("cells_modified", 0)
            steps_summary.append({
                "seq": entry.seq,
                "step_id": entry.step_id,
                "transformation": entry.transformation,
                "rows_removed": act_loss.get("rows_removed", 0),
                "cells_modified": act_loss.get("cells_modified", 0),
                "duration_ms": act_loss.get("duration_ms", 0),
            })

        # 7. Format-Preserving Export & Sanitization
        target_format = resolve_export_format(detected_format, original_filename, "auto")
        export_resp = export_dataframe_to_response(
            df=cleaned_df,
            original_filename=original_filename,
            detected_format=detected_format,
            requested_format="auto",
            ledger_entries=ledger.entries,
        )
        cleaned_bytes = bytes(export_resp.body)
        cleaned_filename = build_export_filename(original_filename, target_format)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"[HeadlessPipeline] Successfully cleaned '{original_filename}' -> '{cleaned_filename}' "
            f"in {duration_ms:.2f}ms. Rows: {initial_rows} -> {cleaned_rows}, "
            f"Cells edited: {total_cells_modified}"
        )

        return HeadlessCleanResult(
            run_id=active_run_id,
            original_filename=original_filename,
            cleaned_filename=cleaned_filename,
            target_format=target_format,
            cleaned_bytes=cleaned_bytes,
            initial_rows=initial_rows,
            cleaned_rows=cleaned_rows,
            initial_columns=initial_cols,
            cleaned_columns=cleaned_cols,
            rows_dropped=max(0, total_rows_dropped),
            cells_modified=total_cells_modified,
            steps_applied=steps_summary,
            initial_hash=initial_hash,
            cleaned_hash=cleaned_hash,
            duration_ms=round(duration_ms, 2),
            success=True,
            error_message=None,
        )

    except Exception as exc:
        logger.exception(f"[HeadlessPipeline] Unhandled exception in run {active_run_id}: {exc}")
        return HeadlessCleanResult(
            run_id=active_run_id,
            original_filename=original_filename,
            cleaned_filename=original_filename,
            target_format="csv",
            cleaned_bytes=b"",
            initial_rows=0,
            cleaned_rows=0,
            initial_columns=0,
            cleaned_columns=0,
            rows_dropped=0,
            cells_modified=0,
            steps_applied=[],
            initial_hash="",
            cleaned_hash="",
            duration_ms=(time.perf_counter() - start_time) * 1000,
            success=False,
            error_message=str(exc),
        )
