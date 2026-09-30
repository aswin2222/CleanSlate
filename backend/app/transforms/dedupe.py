"""Deduplication transformations: exact and fuzzy clustering."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.transforms.base import Delta, DroppedRow, DryRunResult, PlanStep, Transformation

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class DedupeExact(Transformation):
    """
    Identifies exact duplicate records (by specified subset or all data columns),
    retains the first occurrence, and drops subsequent duplicate rows.
    Preserves all dropped row data in Delta for exact rollback.
    """

    @property
    def name(self) -> str:
        return "dedupe_exact"

    @property
    def description(self) -> str:
        return "Removes exact duplicate rows, retaining the first occurrence."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Removes {dry_res.rows_removed} duplicate rows matching on {', '.join(cols)}.",
            requires_approval=dry_res.rows_removed_pct > 0.05,
            predicted_loss=dry_res,
        )

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        subset = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        subset = [c for c in subset if c in df.columns]

        total_rows = max(1, len(df))
        dupe_mask = df.duplicated(subset=subset, keep="first") if subset else pd.Series(False, index=df.index)
        rows_removed = int(dupe_mask.sum())
        rows_pct = round(rows_removed / total_rows, 4)

        # Destroys all non-null cells in those dropped rows
        non_null_destroyed = 0
        if rows_removed > 0:
            dropped_slice = df[dupe_mask]
            for col in [c for c in df.columns if c != ROW_ID_COL]:
                non_null_destroyed += int((dropped_slice[col] != "").sum())

        row_comp = min(1.0, rows_pct / 0.10)
        loss_score = min(100.0, round(100.0 * (0.35 * row_comp), 2))
        loss_label = "HIGH" if loss_score > 50 else ("MEDIUM" if loss_score >= 20 else "LOW")

        return DryRunResult(
            rows_removed=rows_removed,
            rows_removed_pct=rows_pct,
            cells_modified=0,
            cells_modified_pct=0.0,
            non_null_cells_destroyed=non_null_destroyed,
            loss_score=loss_score,
            loss_label=loss_label,
            human_summary=f"Drops {rows_removed} duplicate rows ({rows_pct * 100:.1f}%), destroying {non_null_destroyed} cells. Loss: {loss_label} ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        subset = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        subset = [c for c in subset if c in df.columns]

        delta = Delta(transformation=self.name, metadata={"subset": subset})
        if not subset:
            return df.copy(), delta

        dupe_mask = df.duplicated(subset=subset, keep="first")
        dropped_df = df[dupe_mask]

        # Record dropped rows in delta with position and full dictionary
        for orig_idx, (idx_label, row) in enumerate(dropped_df.iterrows()):
            rid = int(row[ROW_ID_COL]) if ROW_ID_COL in row else orig_idx
            delta.dropped_rows.append(
                DroppedRow(
                    rid=rid,
                    original_position=int(df.index.get_loc(idx_label)),
                    data={str(k): str(v) for k, v in row.to_dict().items()},
                )
            )

        new_df = df[~dupe_mask].copy().reset_index(drop=True)
        return new_df, delta

    def invert(self, df: pd.DataFrame, delta: Delta) -> pd.DataFrame:
        if not delta.dropped_rows:
            return df.copy()

        rows_to_restore = []
        for dropped in delta.dropped_rows:
            rows_to_restore.append(dropped.data)

        restored_rows_df = pd.DataFrame(rows_to_restore, columns=df.columns)
        combined = pd.concat([df, restored_rows_df], ignore_index=True)

        if ROW_ID_COL in combined.columns:
            combined[ROW_ID_COL] = combined[ROW_ID_COL].astype(int)
            combined = combined.sort_values(by=ROW_ID_COL).reset_index(drop=True)

        return combined


class DedupeFuzzy(Transformation):
    """
    Clusters records via Levenshtein string similarity on key columns.
    Retains first occurrence as survivor; records dropped fuzzy duplicates in delta.
    Requires human approval by default.
    """

    @property
    def name(self) -> str:
        return "dedupe_fuzzy"

    @property
    def description(self) -> str:
        return "Clusters and deduplicates near-duplicate rows based on string similarity."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        cols = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=cols,
            rationale=f"Clusters near-duplicate records with similarity threshold {params.get('threshold', 90)}%.",
            requires_approval=True,  # Always requires approval per spec
            predicted_loss=dry_res,
        )

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        subset = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        subset = [c for c in subset if c in df.columns]
        threshold = int(params.get("threshold", 90))

        if not RAPIDFUZZ_AVAILABLE or len(df) <= 1 or not subset:
            return DryRunResult(0, 0.0, 0, 0.0, 0, 0.0, "LOW", "No fuzzy duplicates detected.")

        # Limit inspection to top 1000 rows to keep dry_run fast
        sample_df = df[subset].head(1000).astype(str)
        row_keys = [" ".join(r).lower().strip() for r in sample_df.values]

        dropped_indices = set()
        for i in range(len(row_keys)):
            if i in dropped_indices:
                continue
            for j in range(i + 1, min(i + 100, len(row_keys))):
                if j not in dropped_indices:
                    sim = fuzz.ratio(row_keys[i], row_keys[j])
                    if sim >= threshold:
                        dropped_indices.add(j)

        rows_removed = len(dropped_indices)
        rows_pct = round(rows_removed / max(1, len(df)), 4)
        row_comp = min(1.0, rows_pct / 0.10)
        loss_score = min(100.0, round(100.0 * (0.35 * row_comp), 2))
        loss_label = "HIGH" if loss_score > 50 else ("MEDIUM" if loss_score >= 20 else "LOW")

        return DryRunResult(
            rows_removed=rows_removed,
            rows_removed_pct=rows_pct,
            cells_modified=0,
            cells_modified_pct=0.0,
            non_null_cells_destroyed=rows_removed * len(subset),
            loss_score=loss_score,
            loss_label=loss_label,
            human_summary=f"Fuzzy dedupe clusters {rows_removed} near-duplicate rows. Loss: {loss_label} ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        subset = params.get("subset", [c for c in df.columns if c != ROW_ID_COL])
        subset = [c for c in subset if c in df.columns]
        threshold = int(params.get("threshold", 90))

        delta = Delta(transformation=self.name, metadata={"subset": subset, "threshold": threshold})
        if not RAPIDFUZZ_AVAILABLE or len(df) <= 1 or not subset:
            return df.copy(), delta

        row_keys = [" ".join(r).lower().strip() for r in df[subset].astype(str).values]
        dropped_indices = set()
        for i in range(len(row_keys)):
            if i in dropped_indices:
                continue
            for j in range(i + 1, min(i + 100, len(row_keys))):
                if j not in dropped_indices:
                    sim = fuzz.ratio(row_keys[i], row_keys[j])
                    if sim >= threshold:
                        dropped_indices.add(j)

        dropped_rows_list = []
        keep_indices = []
        for idx in range(len(df)):
            if idx in dropped_indices:
                row_dict = {str(k): str(v) for k, v in df.iloc[idx].to_dict().items()}
                rid = int(df[ROW_ID_COL].iloc[idx]) if ROW_ID_COL in df.columns else idx
                delta.dropped_rows.append(
                    DroppedRow(rid=rid, original_position=idx, data=row_dict)
                )
            else:
                keep_indices.append(idx)

        new_df = df.iloc[keep_indices].copy().reset_index(drop=True)
        return new_df, delta

    def invert(self, df: pd.DataFrame, delta: Delta) -> pd.DataFrame:
        if not delta.dropped_rows:
            return df.copy()

        rows_to_restore = [r.data for r in delta.dropped_rows]
        restored_rows_df = pd.DataFrame(rows_to_restore, columns=df.columns)
        combined = pd.concat([df, restored_rows_df], ignore_index=True)

        if ROW_ID_COL in combined.columns:
            combined[ROW_ID_COL] = combined[ROW_ID_COL].astype(int)
            combined = combined.sort_values(by=ROW_ID_COL).reset_index(drop=True)

        return combined
