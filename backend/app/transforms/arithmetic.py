"""Arithmetic relation reconciliation transformation."""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class FixArithmetic(Transformation):
    """
    Repairs or fills target/operand in an arithmetic relationship (target = a * b, target = a + b, or target = a - b).
    Rules:
    - Never divide by zero
    - Never overwrite a value that already satisfies the relation
    - Solves when exactly one operand or target is missing/broken
    """

    @property
    def name(self) -> str:
        return "fix_arithmetic"

    @property
    def description(self) -> str:
        return "Repairs arithmetic relationships (e.g., total = qty * price) when unambiguous."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        target = params.get("target", "")
        op1 = params.get("col_a", "")
        op2 = params.get("col_b", "")
        op = params.get("operation", "*")
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=[target, op1, op2],
            rationale=f"Repairs {dry_res.cells_modified} arithmetic violations for {target} = {op1} {op} {op2}.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def _eval_row(
        self,
        t_val: str,
        a_val: str,
        b_val: str,
        op: str,
    ) -> Optional[Tuple[str, str]]:  # (target_to_update, new_value)
        """Evaluates whether an arithmetic repair is required and unambiguous."""
        t_miss = is_missing(t_val)
        a_miss = is_missing(a_val)
        b_miss = is_missing(b_val)

        def to_f(v: str) -> Optional[float]:
            try:
                f = float(str(v).replace(",", ""))
                return f if not math.isnan(f) and not math.isinf(f) else None
            except ValueError:
                return None

        t_f, a_f, b_f = to_f(t_val), to_f(a_val), to_f(b_val)

        if op == "*":
            # Target missing, a and b present
            if (t_miss or t_f is None) and (a_f is not None and b_f is not None):
                res = a_f * b_f
                return "target", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))

            # a missing, target and b present
            if (a_miss or a_f is None) and (t_f is not None and b_f is not None):
                if abs(b_f) > 1e-9:
                    res = t_f / b_f
                    return "col_a", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))

            # b missing, target and a present
            if (b_miss or b_f is None) and (t_f is not None and a_f is not None):
                if abs(a_f) > 1e-9:
                    res = t_f / a_f
                    return "col_b", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))

            # All present: check if broken
            if t_f is not None and a_f is not None and b_f is not None:
                expected = a_f * b_f
                if abs(t_f - expected) > 0.01:
                    return "target", f"{expected:.2f}" if abs(expected - round(expected)) > 1e-4 else str(int(round(expected)))

        elif op == "+":
            if (t_miss or t_f is None) and (a_f is not None and b_f is not None):
                res = a_f + b_f
                return "target", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))
            if (a_miss or a_f is None) and (t_f is not None and b_f is not None):
                res = t_f - b_f
                return "col_a", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))
            if (b_miss or b_f is None) and (t_f is not None and a_f is not None):
                res = t_f - a_f
                return "col_b", f"{res:.2f}" if abs(res - round(res)) > 1e-4 else str(int(round(res)))
            if t_f is not None and a_f is not None and b_f is not None:
                expected = a_f + b_f
                if abs(t_f - expected) > 0.01:
                    return "target", f"{expected:.2f}" if abs(expected - round(expected)) > 1e-4 else str(int(round(expected)))

        return None

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        target = params.get("target", "")
        col_a = params.get("col_a", "")
        col_b = params.get("col_b", "")
        op = params.get("operation", "*")

        if not all(c in df.columns for c in (target, col_a, col_b)):
            return DryRunResult(0, 0.0, 0, 0.0, 0, 0.0, "LOW", "Arithmetic columns not found.")

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for _, row in df[[target, col_a, col_b]].iterrows():
            res = self._eval_row(str(row[target]), str(row[col_a]), str(row[col_b]), op)
            if res is not None:
                cells_modified += 1

        cells_pct = round(cells_modified / total_cells, 4)
        loss_score = min(100.0, round(100.0 * (0.15 * min(1.0, cells_pct / 0.25)), 2))

        return DryRunResult(
            rows_removed=0,
            rows_removed_pct=0.0,
            cells_modified=cells_modified,
            cells_modified_pct=cells_pct,
            non_null_cells_destroyed=0,
            loss_score=loss_score,
            loss_label="LOW",
            human_summary=f"Repairs {cells_modified} arithmetic values ({target} = {col_a} {op} {col_b}). Loss: LOW ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        target = params.get("target", "")
        col_a = params.get("col_a", "")
        col_b = params.get("col_b", "")
        op = params.get("operation", "*")

        delta = Delta(transformation=self.name, metadata=params)
        if not all(c in df.columns for c in (target, col_a, col_b)):
            return df.copy(), delta

        new_df = df.copy()
        col_map = {"target": target, "col_a": col_a, "col_b": col_b}

        for idx in range(len(new_df)):
            t_val = str(new_df.at[idx, target])
            a_val = str(new_df.at[idx, col_a])
            b_val = str(new_df.at[idx, col_b])

            res = self._eval_row(t_val, a_val, b_val, op)
            if res is not None:
                slot, new_val = res
                update_col = col_map[slot]
                old_val = str(new_df.at[idx, update_col])
                rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx

                delta.cell_edits.append(
                    CellEdit(rid=rid, column=update_col, old_value=old_val, new_value=new_val)
                )
                new_df.at[idx, update_col] = new_val

        return new_df, delta

    def invert(self, df: pd.DataFrame, delta: Delta) -> pd.DataFrame:
        restored = df.copy()
        if ROW_ID_COL in restored.columns:
            rid_to_idx = {int(rid): idx for idx, rid in enumerate(restored[ROW_ID_COL])}
            for edit in delta.cell_edits:
                if edit.rid in rid_to_idx and edit.column in restored.columns:
                    loc = rid_to_idx[edit.rid]
                    col_idx = restored.columns.get_loc(edit.column)
                    restored.iat[loc, col_idx] = edit.old_value
        else:
            for edit in delta.cell_edits:
                if edit.rid < len(restored) and edit.column in restored.columns:
                    restored.iat[edit.rid, restored.columns.get_loc(edit.column)] = edit.old_value
        return restored
