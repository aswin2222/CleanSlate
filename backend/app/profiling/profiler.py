"""Deep Dataset Profiler and Streaming Statistical Aggregator."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from app.config import settings
from app.profiling.patterns import (
    DATE_EUR,
    DATE_ISO,
    DATE_US,
    DATETIME_ISO,
    generate_pattern_signature,
    infer_value_type,
    is_missing,
)
from app.profiling.sparsity import DatasetSparsityReport, evaluate_sparsity

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


@dataclass
class ColumnProfile:
    column_name: str
    total_count: int
    missing_count: int
    null_rate: float
    distinct_count: int
    top_values: List[Tuple[str, int]]
    inferred_types: Dict[str, int]
    primary_type: str
    is_mixed_type: bool
    pattern_signatures: List[Tuple[str, int]]
    format_variants: Dict[str, int]
    leading_trailing_whitespace_count: int
    case_inconsistencies: int

    # Numeric metrics
    is_numeric: bool
    numeric_count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    quantiles: Dict[str, float] = field(default_factory=dict)
    iqr_outliers_count: int = 0
    mad_outliers_count: int = 0

    # String metrics
    min_length: int = 0
    max_length: int = 0
    avg_length: float = 0.0

    # Sparsity
    is_extreme_sparse: bool = False


@dataclass
class DatasetProfile:
    fingerprint: str
    total_rows: int
    total_columns: int
    columns: Dict[str, ColumnProfile]
    exact_duplicate_rows: int
    near_duplicate_candidates_count: int
    sparsity_report: DatasetSparsityReport
    undecodable_byte_count: int = 0
    summary_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_dataset_fingerprint(df: pd.DataFrame) -> str:
    """Computes a deterministic MD5/SHA256 fingerprint for caching profiles."""
    shape_str = f"{df.shape[0]}x{df.shape[1]}"
    col_str = ",".join(str(c) for c in df.columns)
    sample_str = ""
    if not df.empty:
        # First 5 and last 5 rows sample
        sample_rows = pd.concat([df.head(5), df.tail(5)])
        sample_str = sample_rows.to_csv(index=False)
    raw = f"{shape_str}|{col_str}|{sample_str}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def profile_column(col_name: str, series: pd.Series) -> ColumnProfile:
    """Computes deep statistical profile for a single column series of strings."""
    total_count = len(series)
    non_null_vals: List[str] = []
    missing_count = 0
    ws_count = 0
    type_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    date_variants: Counter[str] = Counter()
    lengths: List[int] = []

    for val in series:
        if is_missing(val):
            missing_count += 1
            type_counts["null"] += 1
        else:
            s_val = str(val)
            non_null_vals.append(s_val)
            lengths.append(len(s_val))

            # Whitespace check
            if s_val != s_val.strip():
                ws_count += 1

            # Type inference
            v_type = infer_value_type(s_val)
            type_counts[v_type] += 1

            # Pattern signature
            pat = generate_pattern_signature(s_val)
            pattern_counts[pat] += 1

            # Date format tracking
            if DATE_ISO.match(s_val):
                date_variants["YYYY-MM-DD (ISO)"] += 1
            elif DATE_US.match(s_val):
                date_variants["MM/DD/YYYY (US)"] += 1
            elif DATE_EUR.match(s_val):
                date_variants["DD-MM-YYYY (EUR)"] += 1
            elif DATETIME_ISO.match(s_val):
                date_variants["ISO-8601 Datetime"] += 1

    null_rate = missing_count / total_count if total_count > 0 else 1.0
    val_counter = Counter(non_null_vals)
    distinct_count = len(val_counter)
    top_values = val_counter.most_common(5)

    # Determine primary type
    non_null_types = {k: v for k, v in type_counts.items() if k != "null"}
    if non_null_types:
        primary_type = max(non_null_types.items(), key=lambda x: x[1])[0]
        # Check if mixed types present
        majority_type_count = non_null_types[primary_type]
        is_mixed_type = (majority_type_count / len(non_null_vals)) < 0.85 if non_null_vals else False
    else:
        primary_type = "null"
        is_mixed_type = False

    # Check case inconsistency (e.g. "USA", "Usa", "usa")
    lowered_groups: Dict[str, set[str]] = {}
    for v in non_null_vals:
        lowered_groups.setdefault(v.lower(), set()).add(v)
    case_inconsistencies = sum(1 for variants in lowered_groups.values() if len(variants) > 1)

    # Numeric evaluation
    numeric_vals: List[float] = []
    for v in non_null_vals:
        # Strip currency symbols, commas, percent
        cleaned = re.sub(r"[\$,€£¥₹\s%]", "", v).replace(",", "")
        try:
            val_float = float(cleaned)
            if not math.isnan(val_float) and not math.isinf(val_float):
                numeric_vals.append(val_float)
        except ValueError:
            pass

    is_numeric = len(numeric_vals) >= 0.70 * len(non_null_vals) if non_null_vals else False
    numeric_count = len(numeric_vals)

    min_val, max_val, mean_val, med_val, std_val = None, None, None, None, None
    quantiles_dict: Dict[str, float] = {}
    iqr_outliers = 0
    mad_outliers = 0

    if numeric_vals:
        arr = np.array(numeric_vals, dtype=float)
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        mean_val = float(np.mean(arr))
        med_val = float(np.median(arr))
        std_val = float(np.std(arr))

        q25, q50, q75 = np.percentile(arr, [25, 50, 75])
        quantiles_dict = {
            "p05": float(np.percentile(arr, 5)),
            "p25": float(q25),
            "p50": float(q50),
            "p75": float(q75),
            "p95": float(np.percentile(arr, 95)),
        }

        # IQR Outliers
        iqr = q75 - q25
        lower_fence = q25 - 1.5 * iqr
        upper_fence = q75 + 1.5 * iqr
        iqr_outliers = int(np.sum((arr < lower_fence) | (arr > upper_fence)))

        # MAD Outliers (Median Absolute Deviation)
        mad = float(np.median(np.abs(arr - med_val)))
        if mad > 1e-9:
            mad_scores = np.abs(arr - med_val) / (1.4826 * mad)
            mad_outliers = int(np.sum(mad_scores > 3.0))

    # String length stats
    min_len = min(lengths) if lengths else 0
    max_len = max(lengths) if lengths else 0
    avg_len = sum(lengths) / len(lengths) if lengths else 0.0

    return ColumnProfile(
        column_name=col_name,
        total_count=total_count,
        missing_count=missing_count,
        null_rate=round(null_rate, 4),
        distinct_count=distinct_count,
        top_values=top_values,
        inferred_types=dict(type_counts),
        primary_type=primary_type,
        is_mixed_type=is_mixed_type,
        pattern_signatures=pattern_counts.most_common(5),
        format_variants=dict(date_variants),
        leading_trailing_whitespace_count=ws_count,
        case_inconsistencies=case_inconsistencies,
        is_numeric=is_numeric,
        numeric_count=numeric_count,
        min_value=min_val,
        max_value=max_val,
        mean=round(mean_val, 4) if mean_val is not None else None,
        median=round(med_val, 4) if med_val is not None else None,
        std=round(std_val, 4) if std_val is not None else None,
        quantiles=quantiles_dict,
        iqr_outliers_count=iqr_outliers,
        mad_outliers_count=mad_outliers,
        min_length=min_len,
        max_length=max_len,
        avg_length=round(avg_len, 2),
        is_extreme_sparse=(null_rate >= settings.SPARSE_THRESHOLD),
    )


def profile_dataset(
    df: pd.DataFrame,
    undecodable_byte_count: int = 0,
    max_near_dupe_rows: int = 500,
) -> DatasetProfile:
    """
    Profiles an entire dataset, evaluating columns, duplicate rows,
    near-duplicate clusters, and sparsity.
    """
    fingerprint = compute_dataset_fingerprint(df)
    total_rows = len(df)
    data_cols = [c for c in df.columns if c != "_rid"]
    total_columns = len(data_cols)

    # Sparsity evaluation
    sparsity_report = evaluate_sparsity(df)

    # Column profiles
    columns: Dict[str, ColumnProfile] = {}
    for col in data_cols:
        col_prof = profile_column(col, df[col])
        columns[col] = col_prof

    # Exact duplicate row detection (excluding _rid)
    if not df.empty and data_cols:
        exact_duplicate_rows = int(df.duplicated(subset=data_cols).sum())
    else:
        exact_duplicate_rows = 0

    # Near duplicate row detection (capped work with rapidfuzz)
    near_dupes_count = 0
    if RAPIDFUZZ_AVAILABLE and total_rows > 1 and total_rows <= max_near_dupe_rows and data_cols:
        # Concatenate normalized strings for each row
        row_strings = (
            df[data_cols]
            .astype(str)
            .apply(lambda r: " ".join(str(x) for x in r.values).lower().strip(), axis=1)
            .tolist()
        )
        # Pairwise comparison
        for i in range(len(row_strings)):
            for j in range(i + 1, min(i + 50, len(row_strings))):  # sliding window
                if row_strings[i] != row_strings[j]:
                    score = fuzz.ratio(row_strings[i], row_strings[j])
                    if score >= 88:
                        near_dupes_count += 1

    summary_text = (
        f"Profiled {total_rows} rows across {total_columns} columns. "
        f"Found {exact_duplicate_rows} exact duplicates, "
        f"{near_dupes_count} near-duplicate candidates. "
        f"{sparsity_report.summary_sentence}"
    )

    return DatasetProfile(
        fingerprint=fingerprint,
        total_rows=total_rows,
        total_columns=total_columns,
        columns=columns,
        exact_duplicate_rows=exact_duplicate_rows,
        near_duplicate_candidates_count=near_dupes_count,
        sparsity_report=sparsity_report,
        undecodable_byte_count=undecodable_byte_count,
        summary_text=summary_text,
    )


class DatasetProfiler:
    """Class wrapper for profiling datasets."""

    def __init__(self, max_near_dupe_rows: int = 500):
        self.max_near_dupe_rows = max_near_dupe_rows

    def profile(self, df: pd.DataFrame) -> DatasetProfile:
        return profile_dataset(df, max_near_dupe_rows=self.max_near_dupe_rows)

