"""Missing value imputation transformations with strict safety thresholds."""
from __future__ import annotations

import math
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.config import settings
from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class ImputeMedian(Transformation):
    """
    Imputes missing numeric cells with the median of observed values.
    Enforces safety guards:
    - Skipped if null rate > IMPUTE_MAX_NULL_RATE (default 0.30)
    - Skipped if column is EXTREME_SPARSE (null rate >= 0.90)
    - Skipped if valid evidence rows < MIN_ROWS_FOR_INFERENCE (default 30)
    """

    @property
    def name(self) -> str:
        return "impute_median"

    @property
    def description(self) -> str:
        return "Fills missing numeric values with the column median (subject to strict evidence thresholds)."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Imputes missing numeric cells in {', '.join(cols)} using column median.",
            requires_approval=True,  # Imputation alters distribution; approval required
            predicted_loss=dry_res,
        )

    def _can_impute(
        self,
        series: pd.Series,
        max_null_rate: float = settings.IMPUTE_MAX_NULL_RATE,
        min_rows: int = settings.MIN_ROWS_FOR_INFERENCE,
    ) -> Tuple[bool, Optional[str], str]:
        total = len(series)
        if total < min_rows:
            return False, None, f"Insufficient rows ({total} < {min_rows})"

        vals: List[float] = []
        missing_count = 0
        for v in series:
            if is_missing(v):
                missing_count += 1
            else:
                try:
                    f = float(str(v).replace(",", ""))
                    if not math.isnan(f) and not math.isinf(f):
                        vals.append(f)
                except ValueError:
                    pass

        null_rate = missing_count / total
        if null_rate > max_null_rate:
            return False, None, f"Null rate {null_rate * 100:.1f}% exceeds max threshold {max_null_rate * 100:.0f}%"

        if len(vals) < 10:
            return False, None, "Insufficient numeric evidence"

        med = float(np.median(vals))
        fill_val = str(int(med)) if med.is_integer() else f"{med:.2f}"
        return True, fill_val, "OK"

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))
        reasons = []

        for col in cols:
            can_imp, fill_val, reason = self._can_impute(df[col])
            if can_imp and fill_val is not None:
                for v in df[col]:
                    if is_missing(v):
                        cells_modified += 1
            else:
                reasons.append(f"Skipped '{col}': {reason}")

        cells_pct = round(cells_modified / total_cells, 4)
        loss_score = min(100.0, round(100.0 * (0.15 * min(1.0, cells_pct / 0.25)), 2))

        return DryRunResult(
            rows_removed=0,
            rows_removed_pct=0.0,
            cells_modified=cells_modified,
            cells_modified_pct=cells_pct,
            non_null_cells_destroyed=0,
            loss_score=loss_score,
            loss_label="LOW" if loss_score < 20 else "MEDIUM",
            human_summary=f"Imputes {cells_modified} cells with median. {'; '.join(reasons[:2])} Loss: ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols})

        for col in cols:
            can_imp, fill_val, _ = self._can_impute(new_df[col])
            if not can_imp or fill_val is None:
                continue

            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                if is_missing(val):
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=str(val), new_value=fill_val)
                    )
                    new_df.iat[idx, col_idx] = fill_val

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


class ImputeMode(Transformation):
    """
    Imputes missing categorical cells with the mode (most common value).
    Enforces safety guards identical to ImputeMedian.
    """

    @property
    def name(self) -> str:
        return "impute_mode"

    @property
    def description(self) -> str:
        return "Fills missing categorical values with the column mode (subject to safety thresholds)."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Imputes missing categorical cells in {', '.join(cols)} using mode.",
            requires_approval=True,
            predicted_loss=dry_res,
        )

    def _can_impute(
        self,
        series: pd.Series,
        max_null_rate: float = settings.IMPUTE_MAX_NULL_RATE,
        min_rows: int = settings.MIN_ROWS_FOR_INFERENCE,
    ) -> Tuple[bool, Optional[str], str]:
        total = len(series)
        if total < min_rows:
            return False, None, f"Insufficient rows ({total} < {min_rows})"

        non_null_vals = [str(v) for v in series if not is_missing(v)]
        missing_count = total - len(non_null_vals)

        null_rate = missing_count / total
        if null_rate > max_null_rate:
            return False, None, f"Null rate {null_rate * 100:.1f}% exceeds max threshold {max_null_rate * 100:.0f}%"

        if not non_null_vals:
            return False, None, "No observed category values"

        mode_val = Counter(non_null_vals).most_common(1)[0][0]
        return True, mode_val, "OK"

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))
        reasons = []

        for col in cols:
            can_imp, fill_val, reason = self._can_impute(df[col])
            if can_imp and fill_val is not None:
                for v in df[col]:
                    if is_missing(v):
                        cells_modified += 1
            else:
                reasons.append(f"Skipped '{col}': {reason}")

        cells_pct = round(cells_modified / total_cells, 4)
        loss_score = min(100.0, round(100.0 * (0.15 * min(1.0, cells_pct / 0.25)), 2))

        return DryRunResult(
            rows_removed=0,
            rows_removed_pct=0.0,
            cells_modified=cells_modified,
            cells_modified_pct=cells_pct,
            non_null_cells_destroyed=0,
            loss_score=loss_score,
            loss_label="LOW" if loss_score < 20 else "MEDIUM",
            human_summary=f"Imputes {cells_modified} cells with mode. {'; '.join(reasons[:2])} Loss: ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols})

        for col in cols:
            can_imp, fill_val, _ = self._can_impute(new_df[col])
            if not can_imp or fill_val is None:
                continue

            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                if is_missing(val):
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=str(val), new_value=fill_val)
                    )
                    new_df.iat[idx, col_idx] = fill_val

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
