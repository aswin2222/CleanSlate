"""Numeric parsing and standardization transformation."""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class ParseNumeric(Transformation):
    """
    Strips currency symbols ($ € £ ¥ ₹), commas, and spaces from numeric strings.
    Converts numbers to canonical float/int strings. Leaves unparseable cells unchanged.
    """

    @property
    def name(self) -> str:
        return "parse_numeric"

    @property
    def description(self) -> str:
        return "Strips currency symbols and thousand-separators, standardizing numeric cells."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Parses and cleans numeric values in {', '.join(cols)}.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def _clean_numeric_str(self, val: str) -> Optional[str]:
        s = val.strip()
        if not s or is_missing(s):
            return None
        # Remove currency symbols and spaces
        cleaned = re.sub(r"[\$€£¥₹\s]", "", s)
        # Check standard integer
        if re.match(r"^-?\d+$", cleaned):
            return cleaned
        # Check commas as thousand separators: 1,234.56
        if re.match(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$", cleaned):
            return cleaned.replace(",", "")
        # Check standard float
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return None

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            for val in df[col]:
                s_val = str(val)
                parsed = self._clean_numeric_str(s_val)
                if parsed is not None and parsed != s_val:
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
            human_summary=f"Standardizes {cells_modified} numeric cells. Loss: LOW ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols})

        for col in cols:
            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                s_val = str(val)
                parsed = self._clean_numeric_str(s_val)
                if parsed is not None and parsed != s_val:
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=parsed)
                    )
                    new_df.iat[idx, col_idx] = parsed

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
