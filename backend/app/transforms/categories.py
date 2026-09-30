"""Categorical consolidation and spelling variant harmonization transformation."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import is_missing
from app.transforms.base import CellEdit, Delta, DryRunResult, PlanStep, Transformation

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class MergeCategories(Transformation):
    """
    Consolidates spelling, case, and slight typographical variants of categories
    to a dominant canonical representative value.
    """

    @property
    def name(self) -> str:
        return "merge_categories"

    @property
    def description(self) -> str:
        return "Harmonizes spelling and typographical variants of categorical values."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("columns", [])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Harmonizes {dry_res.cells_modified} category variants across {', '.join(cols)}.",
            requires_approval=False,
            predicted_loss=dry_res,
        )

    def _build_variant_mapping(
        self, series: pd.Series, threshold: int = 85
    ) -> Dict[str, str]:
        """Maps minor variants to dominant frequency canonical form."""
        counts = series.value_counts()
        mapping: Dict[str, str] = {}
        unique_vals = [str(v) for v in counts.index if not is_missing(v)]

        for i, val_a in enumerate(unique_vals):
            for val_b in unique_vals[i + 1 :]:
                if val_b in mapping:
                    continue
                # Exact case-insensitive match
                if val_a.lower() == val_b.lower():
                    # Map less frequent to more frequent
                    mapping[val_b] = val_a
                elif RAPIDFUZZ_AVAILABLE:
                    score = fuzz.ratio(val_a.lower(), val_b.lower())
                    if score >= threshold:
                        mapping[val_b] = val_a

        return mapping

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        threshold = int(params.get("threshold", 85))

        cells_modified = 0
        total_cells = max(1, len(df) * max(1, len([c for c in df.columns if c != ROW_ID_COL])))

        for col in cols:
            mapping = self._build_variant_mapping(df[col], threshold)
            for v in df[col]:
                s = str(v)
                if s in mapping and mapping[s] != s:
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
            human_summary=f"Harmonizes {cells_modified} categorical variants. Loss: LOW ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        cols = params.get("columns", [])
        cols = [c for c in cols if c in df.columns]
        threshold = int(params.get("threshold", 85))

        new_df = df.copy()
        delta = Delta(transformation=self.name, metadata={"columns": cols, "threshold": threshold})

        for col in cols:
            mapping = self._build_variant_mapping(new_df[col], threshold)
            if not mapping:
                continue

            col_idx = new_df.columns.get_loc(col)
            for idx, val in enumerate(new_df[col]):
                s_val = str(val)
                if s_val in mapping and mapping[s_val] != s_val:
                    canonical = mapping[s_val]
                    rid = int(new_df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in new_df.columns else idx
                    delta.cell_edits.append(
                        CellEdit(rid=rid, column=col, old_value=s_val, new_value=canonical)
                    )
                    new_df.iat[idx, col_idx] = canonical

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
