"""Row deletion for rule violations and non-mutating flag_only transformations."""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Tuple
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL
from app.transforms.base import Delta, DroppedRow, DryRunResult, PlanStep, Transformation


class DropRowsViolating(Transformation):
    """
    Drops rows that violate a specified validation rule or expression.
    Hard gate: always requires explicit human approval.
    Preserves all dropped row data in Delta for exact round-trip rollback.
    """

    @property
    def name(self) -> str:
        return "drop_rows_violating"

    @property
    def description(self) -> str:
        return "Purges rows violating high-confidence validation rules (strictly requires approval)."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        dry_res = self.dry_run(df, params)
        rule_desc = params.get("rule_description", "custom rule")
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=params.get("columns", []),
            rationale=f"Drops {dry_res.rows_removed} rows violating rule: {rule_desc}.",
            requires_approval=True,  # Mandatory approval gate
            predicted_loss=dry_res,
        )

    def _get_violating_mask(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        # Check explicit violating row IDs
        if "violating_rids" in params and ROW_ID_COL in df.columns:
            target_rids = set(params["violating_rids"])
            return df[ROW_ID_COL].astype(int).isin(target_rids)

        # Check explicit indices
        if "indices" in params:
            idx_set = set(params["indices"])
            return pd.Series([i in idx_set for i in range(len(df))], index=df.index)

        # Check date order: col_a > col_b
        if params.get("rule_kind") == "date_order":
            col_a = params.get("col_a")
            col_b = params.get("col_b")
            if col_a in df.columns and col_b in df.columns:
                # Violates if col_a > col_b
                mask = pd.Series(False, index=df.index)
                for idx in range(len(df)):
                    v_a = str(df.at[idx, col_a]).strip()
                    v_b = str(df.at[idx, col_b]).strip()
                    if v_a and v_b and v_a > v_b:
                        mask.iloc[idx] = True
                return mask

        # Check non_negative
        if params.get("rule_kind") == "non_negative":
            col = params.get("column")
            if col in df.columns:
                mask = pd.Series(False, index=df.index)
                for idx, v in enumerate(df[col]):
                    try:
                        f = float(str(v).replace(",", ""))
                        if f < 0:
                            mask.iloc[idx] = True
                    except ValueError:
                        pass
                return mask

        return pd.Series(False, index=df.index)

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        total_rows = max(1, len(df))
        viol_mask = self._get_violating_mask(df, params)
        rows_removed = int(viol_mask.sum())
        rows_pct = round(rows_removed / total_rows, 4)

        non_null_destroyed = 0
        if rows_removed > 0:
            dropped_slice = df[viol_mask]
            for col in [c for c in df.columns if c != ROW_ID_COL]:
                non_null_destroyed += int((dropped_slice[col] != "").sum())

        row_comp = min(1.0, rows_pct / 0.10)
        loss_score = min(100.0, round(100.0 * (0.35 * row_comp), 2))
        loss_label = "HIGH" if loss_score > 50 or rows_pct > 0.10 else ("MEDIUM" if loss_score >= 20 else "LOW")

        return DryRunResult(
            rows_removed=rows_removed,
            rows_removed_pct=rows_pct,
            cells_modified=0,
            cells_modified_pct=0.0,
            non_null_cells_destroyed=non_null_destroyed,
            loss_score=loss_score,
            loss_label=loss_label,
            human_summary=f"Drops {rows_removed} violating rows ({rows_pct * 100:.1f}%), destroying {non_null_destroyed} cells. Loss: {loss_label} ({loss_score}/100).",
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        viol_mask = self._get_violating_mask(df, params)
        delta = Delta(transformation=self.name, metadata=params)

        dropped_df = df[viol_mask]
        for orig_idx, (idx_label, row) in enumerate(dropped_df.iterrows()):
            rid = int(row[ROW_ID_COL]) if ROW_ID_COL in row else orig_idx
            delta.dropped_rows.append(
                DroppedRow(
                    rid=rid,
                    original_position=int(df.index.get_loc(idx_label)),
                    data={str(k): str(v) for k, v in row.to_dict().items()},
                )
            )

        new_df = df[~viol_mask].copy().reset_index(drop=True)
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


class FlagOnly(Transformation):
    """
    Non-mutating diagnostic step. Records rule violations or findings without altering data.
    Loss is always exactly 0.0.
    """

    @property
    def name(self) -> str:
        return "flag_only"

    @property
    def description(self) -> str:
        return "Records findings or low-confidence violations without mutating underlying data."

    def plan(self, df: pd.DataFrame, params: Dict[str, Any]) -> PlanStep:
        return PlanStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            transformation=self.name,
            params=params,
            target_columns=params.get("columns", []),
            rationale=params.get("message", "Flagged diagnostic finding."),
            requires_approval=False,
            predicted_loss=self.dry_run(df, params),
        )

    def dry_run(self, df: pd.DataFrame, params: Dict[str, Any]) -> DryRunResult:
        return DryRunResult(
            rows_removed=0,
            rows_removed_pct=0.0,
            cells_modified=0,
            cells_modified_pct=0.0,
            non_null_cells_destroyed=0,
            loss_score=0.0,
            loss_label="LOW",
            human_summary=params.get("message", "Flagged diagnostic check. Zero data mutation."),
        )

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, Delta]:
        return df.copy(), Delta(transformation=self.name, metadata=params)

    def invert(self, df: pd.DataFrame, delta: Delta) -> pd.DataFrame:
        return df.copy()
