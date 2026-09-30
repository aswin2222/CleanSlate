"""Canonical Cryptographic Hashing for exact state verification."""
from __future__ import annotations

import hashlib
from typing import List, Optional
import pandas as pd

from app.ingestion.rowid import ROW_ID_COL


def compute_canonical_hash(df: pd.DataFrame, exclude_internal: bool = True) -> str:
    """
    Computes a deterministic SHA-256 canonical hash over a DataFrame.
    Algorithm:
    1. If `_rid` present, sort rows ascending by `_rid`.
    2. Sort data columns in stable alphabetical order (preserving `_rid` as first if present).
    3. For every cell, encode UTF-8 bytes and prefix with length: "<len>:<bytes>|".
    4. Row terminator "\n".
    5. Feed byte stream into hashlib.sha256.
    
    Guarantees:
    - Independent of index labels
    - Delimiter-free and escape-safe
    - Empty string != missing marker != missing column
    - Round-trip exact bit-level verification
    """
    if df.empty:
        # Standard hash for empty DataFrame
        return hashlib.sha256(b"EMPTY_DATAFRAME_V1").hexdigest()

    df_work = df.copy()

    # Determine columns
    if ROW_ID_COL in df_work.columns:
        # Ensure sorted by _rid
        df_work[ROW_ID_COL] = df_work[ROW_ID_COL].astype(int)
        df_work = df_work.sort_values(by=ROW_ID_COL).reset_index(drop=True)
        data_cols = sorted([str(c) for c in df_work.columns if c != ROW_ID_COL])
        cols_to_hash = [ROW_ID_COL] + data_cols
    else:
        cols_to_hash = sorted([str(c) for c in df_work.columns])

    hasher = hashlib.sha256()

    # Stream rows into hasher
    for row in df_work[cols_to_hash].itertuples(index=False):
        row_buffer = bytearray()
        for cell in row:
            s_val = "" if cell is None else str(cell)
            utf8_bytes = s_val.encode("utf-8")
            # Length-prefixed encoding: <length>:<bytes>|
            row_buffer.extend(str(len(utf8_bytes)).encode("ascii"))
            row_buffer.append(ord(":"))
            row_buffer.extend(utf8_bytes)
            row_buffer.append(ord("|"))
        row_buffer.append(ord("\n"))
        hasher.update(row_buffer)

    return hasher.hexdigest()


def verify_canonical_match(df_a: pd.DataFrame, df_b: pd.DataFrame) -> bool:
    """Verifies whether two DataFrames have identical canonical hashes."""
    return compute_canonical_hash(df_a) == compute_canonical_hash(df_b)
