"""Sparsity and low-evidence assessment module."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import pandas as pd

from app.config import settings
from app.profiling.patterns import is_missing


@dataclass
class ColumnSparsityInfo:
    column_name: str
    total_count: int
    missing_count: int
    null_rate: float
    is_extreme_sparse: bool
    reason: str


@dataclass
class DatasetSparsityReport:
    total_rows: int
    total_columns: int
    dataset_sparsity_rate: float
    is_low_evidence: bool
    extreme_sparse_columns: List[str]
    column_reports: Dict[str, ColumnSparsityInfo]
    summary_sentence: str


def evaluate_sparsity(
    df: pd.DataFrame,
    sparse_threshold: float = settings.SPARSE_THRESHOLD,
    min_rows: int = settings.MIN_ROWS_FOR_INFERENCE,
) -> DatasetSparsityReport:
    """
    Evaluates null density and data availability per column and globally across the dataset.
    Flags columns above sparse_threshold (default 0.90) as EXTREME_SPARSE.
    Flags datasets with < min_rows valid records as LOW_EVIDENCE.
    """
    total_rows = len(df)
    cols = [c for c in df.columns if c != "_rid"]
    total_cols = len(cols)

    if total_rows == 0 or total_cols == 0:
        return DatasetSparsityReport(
            total_rows=total_rows,
            total_columns=total_cols,
            dataset_sparsity_rate=1.0,
            is_low_evidence=True,
            extreme_sparse_columns=[],
            column_reports={},
            summary_sentence="Dataset is empty; zero evidence available.",
        )

    is_low_evidence = total_rows < min_rows
    total_missing_cells = 0
    extreme_sparse_cols: List[str] = []
    column_reports: Dict[str, ColumnSparsityInfo] = {}

    for col in cols:
        series = df[col]
        missing_count = int(series.apply(is_missing).sum())
        total_missing_cells += missing_count
        null_rate = missing_count / total_rows if total_rows > 0 else 1.0

        is_extreme = null_rate >= sparse_threshold
        if is_extreme:
            extreme_sparse_cols.append(col)
            reason = f"Column has {null_rate * 100:.1f}% missing values (exceeds {sparse_threshold * 100:.0f}% threshold). Risky transformations like imputation must be skipped."
        else:
            reason = f"Normal null rate of {null_rate * 100:.1f}%."

        column_reports[col] = ColumnSparsityInfo(
            column_name=col,
            total_count=total_rows,
            missing_count=missing_count,
            null_rate=null_rate,
            is_extreme_sparse=is_extreme,
            reason=reason,
        )

    overall_sparsity = total_missing_cells / (total_rows * total_cols) if total_rows * total_cols > 0 else 0.0

    if is_low_evidence:
        summary_sentence = (
            f"Dataset has only {total_rows} rows (below minimum {min_rows}). Flagged as LOW_EVIDENCE; all automatic rule induction and imputation will be suppressed."
        )
    elif extreme_sparse_cols:
        summary_sentence = (
            f"Dataset has overall sparsity of {overall_sparsity * 100:.1f}%. {len(extreme_sparse_cols)} columns are EXTREME_SPARSE ({', '.join(extreme_sparse_cols[:3])}{'...' if len(extreme_sparse_cols) > 3 else ''})."
        )
    else:
        summary_sentence = f"Dataset sparsity is healthy at {overall_sparsity * 100:.1f}% across {total_rows} rows."

    return DatasetSparsityReport(
        total_rows=total_rows,
        total_columns=total_cols,
        dataset_sparsity_rate=overall_sparsity,
        is_low_evidence=is_low_evidence,
        extreme_sparse_columns=extreme_sparse_cols,
        column_reports=column_reports,
        summary_sentence=summary_sentence,
    )
