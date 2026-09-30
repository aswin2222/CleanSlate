"""Row ID assignment and column header deduplication."""
from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd


ROW_ID_COL = "_rid"


def deduplicate_headers(headers: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Deduplicates duplicate header column names by appending suffix _2, _3, etc.
    Returns:
        (deduplicated_headers, original_to_deduped_mapping)
    """
    counts: Dict[str, int] = {}
    deduped: List[str] = []
    mapping: Dict[str, List[str]] = {}

    for raw_header in headers:
        clean_name = str(raw_header).strip()
        if not clean_name:
            clean_name = "unnamed_column"

        if clean_name not in counts:
            counts[clean_name] = 1
            final_name = clean_name
        else:
            counts[clean_name] += 1
            final_name = f"{clean_name}_{counts[clean_name]}"

        deduped.append(final_name)
        mapping.setdefault(clean_name, []).append(final_name)

    return deduped, mapping


def assign_stable_row_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns an integer row ID column `_rid` (0..n-1) in order of ingestion.
    Ensures `_rid` is the first column while preserving the exact relative order
    of all original columns.
    """
    df_copy = df.copy()
    if ROW_ID_COL in df_copy.columns:
        df_copy = df_copy.drop(columns=[ROW_ID_COL])

    df_copy.insert(0, ROW_ID_COL, list(range(len(df_copy))))
    return df_copy
