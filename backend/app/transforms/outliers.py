"""Outlier capping (Winsorization) transformation."""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class CapOutliers(Transformation):
    """
    Winsorizes extreme numeric values to IQR fences (Q25 - 1.5*IQR, Q75 + 1.5*IQR)
    or percentile bounds (p05, p95).
    """

    @property
    def name(self) -> str:
        return "cap_outliers"

    @property
    def description(self) -> str:
        return "Winsorizes extreme numeric outliers to statistical IQR fences or percentile caps."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Winsorizes {dry_res.cells_modified} outlier values across {', '.join(cols)}.",
            requires_approval=True,  # Approval recommended for outlier alteration
            predicted_loss=dry_res,
        )

    def _calc_bounds(self, series: pd.Series, method: str = "iqr") -> Tuple[Optional[float], Optional[float]]:
        vals: List[float] = []
        for v in series:
            if not is_missing(v):
                try:
                    f = float(str(v).replace(",", ""))
                    if not math.isnan(f) and not math.isinf(f):
                        vals.append(f)
                except ValueError:
                    pass

        if len(vals) < 5:
            return None, None

        arr = np.array(vals)
        if method == "percentile":
            return float(np.percentile(arr, 5)), float(np.percentile(arr, 95))

        q25, q75 = np.percentile(arr, [25, 75])
        iqr = q75 - q25
        return float(q25 - 1.5 * iqr), float(q75 + 1.5 * iqr)

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        method = params.get("method", "iqr")

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            low_b, high_b = self._calc_bounds(df[col], method)
            if low_b is None or high_b is None:
                continue

            for val in df[col]:
                if not is_missing(val):
                    try:
                        f = float(str(val).replace(",", ""))
                        if f < low_b or f > high_b:
                            cells_modified += 1
                    except ValueError:
                        pass

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
            human_summary=f"Caps {cells_modified} extreme outliers using {method} bounds. Loss: ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        method = params.get("method", "iqr")

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols, "method": method})

        for col in cols:
            low_b, high_b = self._calc_bounds(new_df[col], method)
            if low_b is None or high_b is None:
                continue

            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                if not is_missing(val):
                    try:
                        f = float(str(val).replace(",", ""))
                        new_val = None
                        if f < low_b:
                            new_val = str(int(low_b)) if low_b.is_integer() else f"{low_b:.2f}"
                        elif f > high_b:
                            new_val = str(int(high_b)) if high_b.is_integer() else f"{high_b:.2f}"

                        if new_val is not None:
                            rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                            delta.cell_edits.append(
                                CellEdit(rid=rid, column=col, old_value=str(val), new_value=new_val)
                            )
                            new_df.iat[idx, col_idx] = new_val
                    except ValueError:
                        pass

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
