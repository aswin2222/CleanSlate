"""Text cleaning transformations: whitespace, case normalization, and phone formatting."""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation


class TrimWhitespace(Transformation):
    """
    Strips leading and trailing whitespace and collapses multiple internal
    consecutive spaces to a single space.
    """

    @property
    def name(self) -> str:
        return "trim_whitespace"

    @property
    def description(self) -> str:
        return "Strips leading/trailing whitespace and collapses internal multiple spaces."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [c for c in df.columns if c != ROW_ID_COL])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Found {dry_res.cells_modified} cells with excessive or trailing whitespace.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [c for c in df.columns if c != ROW_ID_COL])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            for val in df[col]:
                s_val = str(val)
                trimmed = re.sub(r"\s+", " ", s_val.strip())
                if trimmed != s_val:
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
            human_summary=f"Trims whitespace on {cells_modified} cells. Loss: LOW ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [c for c in df.columns if c != ROW_ID_COL])
        cols = [c for c in cols if c in df.columns]

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols})

        for col in cols:
            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                s_val = str(val)
                trimmed = re.sub(r"\s+", " ", s_val.strip())
                if trimmed != s_val:
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=trimmed)
                    )
                    new_df.iat[idx, col_idx] = trimmed

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


class NormalizeCase(Transformation):
    """
    Normalizes casing for categorical or name columns (title, upper, or lower).
    """

    @property
    def name(self) -> str:
        return "normalize_case"

    @property
    def description(self) -> str:
        return "Normalizes text casing (title, upper, lower) to a standard convention."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        casing = params.get("case", "title")
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Standardizes casing to {casing} across columns: {', '.join(cols)}.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        casing = params.get("case", "title")

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            for val in df[col]:
                s_val = str(val)
                if not s_val or is_missing(s_val):
                    continue
                new_val = self._apply_casing(s_val, casing)
                if new_val != s_val:
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
            human_summary=f"Standardizes casing on {cells_modified} cells to {casing}. Loss: LOW ({loss_score}/100).",
        )

    def _apply_casing(self, text: str, casing: str) -> str:
        if casing == "upper":
            return text.upper()
        elif casing == "lower":
            return text.lower()
        return text.title()

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        casing = params.get("case", "title")

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols, "case": casing})

        for col in cols:
            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                s_val = str(val)
                if not s_val or is_missing(s_val):
                    continue
                new_val = self._apply_casing(s_val, casing)
                if new_val != s_val:
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=new_val)
                    )
                    new_df.iat[idx, col_idx] = new_val

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


class NormalizePhone(Transformation):
    """
    Normalizes phone numbers to a consistent international format (+CountryCode ...).
    """

    @property
    def name(self) -> str:
        return "normalize_phone"

    @property
    def description(self) -> str:
        return "Normalizes phone numbers preserving country code and eliminating formatting noise."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Normalizes phone formatting in {', '.join(cols)}.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def _normalize_phone_str(self, val: str) -> str:
        s = val.strip()
        if not s or is_missing(s):
            return s
        has_plus = s.startswith("+")
        digits = "".join(c for c in s if c.isdigit())
        if len(digits) < 7:
            return s  # Invalid or too short, leave unchanged
        if has_plus:
            return f"+{digits}"
        # Default assumption 10-digit US/international without country code
        if len(digits) == 10:
            return f"+1{digits}"
        return f"+{digits}"

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            for val in df[col]:
                s_val = str(val)
                norm = self._normalize_phone_str(s_val)
                if norm != s_val:
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
            human_summary=f"Normalizes {cells_modified} phone numbers. Loss: LOW ({loss_score}/100).",
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
                norm = self._normalize_phone_str(s_val)
                if norm != s_val:
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=norm)
                    )
                    new_df.iat[idx, col_idx] = norm

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
