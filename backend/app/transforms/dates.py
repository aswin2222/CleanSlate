"""Date standardization transformation with ambiguous dd/mm vs mm/dd resolution."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from dateutil import parser as date_parser

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import DATE_ISO, is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class StandardizeDates(Transformation):
    """
    Standardizes heterogeneous date representations into ISO 8601 (YYYY-MM-DD).
    Ambiguous dd/mm vs mm/dd is resolved by unambiguous evidence (>12 in first/second token).
    """

    @property
    def name(self) -> str:
        return "standardize_dates"

    @property
    def description(self) -> str:
        return "Converts diverse date formats into ISO 8601 (YYYY-MM-DD) standard."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Standardizes dates in {', '.join(cols)} to ISO 8601.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def _determine_column_dayfirst(self, series: pd.Series) -> bool:
        """Determines if dayfirst should be preferred based on unambiguous tokens (>12)."""
        dayfirst_votes = 0
        monthfirst_votes = 0
        for val in series:
            s = str(val).strip()
            if not s or is_missing(s) or DATE_ISO.match(s):
                continue
            parts = re.split(r"[-/\.]", s)
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                p1, p2 = int(parts[0]), int(parts[1])
                if p1 > 12 and p2 <= 12:
                    dayfirst_votes += 1
                elif p2 > 12 and p1 <= 12:
                    monthfirst_votes += 1
        return dayfirst_votes >= monthfirst_votes

    def _parse_to_iso(self, val: str, dayfirst: bool) -> Optional[str]:
        s = val.strip()
        if not s or is_missing(s):
            return None
        if DATE_ISO.match(s):
            return s  # Already ISO

        try:
            parsed = date_parser.parse(s, dayfirst=dayfirst)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return None

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            dayfirst = self._determine_column_dayfirst(df[col])
            for val in df[col]:
                s_val = str(val)
                iso_val = self._parse_to_iso(s_val, dayfirst)
                if iso_val is not None and iso_val != s_val:
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
            human_summary=f"Standardizes {cells_modified} dates to ISO-8601 format. Loss: LOW ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols})

        for col in cols:
            dayfirst = self._determine_column_dayfirst(new_df[col])
            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                s_val = str(val)
                iso_val = self._parse_to_iso(s_val, dayfirst)
                if iso_val is not None and iso_val != s_val:
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=iso_val)
                    )
                    new_df.iat[idx, col_idx] = iso_val

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
