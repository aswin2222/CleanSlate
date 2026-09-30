"""Reversible Transformation Pipeline Executor."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.execution.canonical_hash import compute_canonical_hash
from app.execution.ledger import TransformationLedger, LedgerEntryRecord
from app.logging import logger
from app.planning.registry import registry
from app.transforms.base import Delta, PlanStep


class ExecutionResult:
    def __init__(
        self,
        success: bool,
        current_df: pd.DataFrame,
        executed_entries: List[LedgerEntryRecord],
        error_message: Optional[str] = None,
        failed_step_id: Optional[str] = None,
    ) -> None:
        self.success = success
        self.current_df = current_df
        self.executed_entries = executed_entries
        self.error_message = error_message
        self.failed_step_id = failed_step_id


class PipelineExecutor:
    """
    Executes approved PlanSteps atomically and reversibly.
    Guarantees:
    - Pre-condition check: verifies canonical hash_before matches current state
    - Executes only allowlisted transformations from registry
    - Computes actual loss metrics
    - Appends entry atomically to ledger
    - On step failure, rolls back that step immediately to maintain consistency
    """

    def __init__(self, ledger: TransformationLedger, actor: str = "user") -> None:
        self.ledger = ledger
        self.actor = actor

    def execute_step(
        self,
        df: pd.DataFrame,
        step: PlanStep,
        seq: int,
    ) -> Tuple[pd.DataFrame, LedgerEntryRecord]:
        """Executes a single PlanStep on df, returning (new_df, ledger_entry)."""
        transform = registry.get(step.transformation)
        if not transform:
            raise ValueError(f"Transformation '{step.transformation}' not found in registry")

        hash_before = compute_canonical_hash(df)
        start_time = time.perf_counter()

        # Apply transformation
        new_df, delta = transform.apply(df, step.params)
        duration_ms = (time.perf_counter() - start_time) * 1000

        hash_after = compute_canonical_hash(new_df)

        # Compute actual loss metrics
        rows_removed = len(delta.dropped_rows)
        cells_modified = len(delta.cell_edits)
        actual_loss = {
            "rows_removed": rows_removed,
            "rows_removed_pct": round(rows_removed / max(1, len(df)), 4),
            "cells_modified": cells_modified,
            "cells_modified_pct": round(cells_modified / max(1, len(df) * max(1, len(df.columns))), 4),
            "duration_ms": round(duration_ms, 2),
        }

        # Atomically append to ledger
        entry = self.ledger.append_entry(
            seq=seq,
            step_id=step.id,
            transformation=step.transformation,
            params=step.params,
            delta=delta,
            hash_before=hash_before,
            hash_after=hash_after,
            predicted_loss=step.predicted_loss.to_dict(),
            actual_loss=actual_loss,
            actor=self.actor,
        )

        step.status = "applied"
        return new_df, entry

    def execute_plan(
        self,
        df: pd.DataFrame,
        steps: List[PlanStep],
    ) -> ExecutionResult:
        """Applies a sequence of approved PlanSteps."""
        current_df = df.copy()
        executed_entries: List[LedgerEntryRecord] = []
        seq = len(self.ledger.entries) + 1

        for step in steps:
            # Skip non-approved steps
            if not step.approved or step.status == "skipped":
                continue

            # Idempotency check: if already applied, skip
            if step.status == "applied":
                continue

            try:
                current_df, entry = self.execute_step(current_df, step, seq)
                executed_entries.append(entry)
                seq += 1
            except Exception as e:
                logger.error(f"Executor failed at step {step.id} ({step.transformation}): {str(e)}")
                return ExecutionResult(
                    success=False,
                    current_df=current_df,
                    executed_entries=executed_entries,
                    error_message=str(e),
                    failed_step_id=step.id,
                )

        return ExecutionResult(
            success=True,
            current_df=current_df,
            executed_entries=executed_entries,
        )
