"""Deterministic candidate rule generation from dataset profiles."""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional
import pandas as pd

from app.inference.dsl import RuleKind
from app.profiling.profiler import DatasetProfile


class RuleCandidate:
    def __init__(
        self,
        kind: RuleKind,
        columns: List[str],
        params: Optional[Dict[str, Any]] = None,
        rationale: str = "",
    ) -> None:
        self.id = f"cand_{uuid.uuid4().hex[:8]}"
        self.kind = kind
        self.columns = columns
        self.params = params or {}
        self.rationale = rationale


def generate_candidate_rules(profile: DatasetProfile, df: pd.DataFrame) -> List[RuleCandidate]:
    """
    Generates rule candidates using deterministic heuristics on column profile statistics.
    Candidates will be subsequently empirically verified for support and confidence.
    """
    candidates: List[RuleCandidate] = []
    col_names = [c for c in df.columns if c != "_rid"]

    date_cols: List[str] = []
    numeric_cols: List[str] = []

    for col in col_names:
        cp = profile.columns.get(col)
        if not cp:
            continue

        col_lower = col.lower()

        # 1. Type and Pattern Candidates
        if cp.primary_type in ("int", "float"):
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.TYPE,
                    columns=[col],
                    params={"type": cp.primary_type},
                    rationale=f"Observed predominantly {cp.primary_type} values.",
                )
            )
            numeric_cols.append(col)

            # Check non-negative
            if cp.min_value is not None and cp.min_value >= 0:
                candidates.append(
                    RuleCandidate(
                        kind=RuleKind.NON_NEGATIVE,
                        columns=[col],
                        params={},
                        rationale="Observed numeric values are all non-negative.",
                    )
                )

            # Range candidate
            if cp.min_value is not None and cp.max_value is not None:
                candidates.append(
                    RuleCandidate(
                        kind=RuleKind.RANGE,
                        columns=[col],
                        params={"min": cp.min_value, "max": cp.max_value},
                        rationale=f"Bounded numeric range [{cp.min_value}, {cp.max_value}].",
                    )
                )

        elif cp.primary_type == "date":
            date_cols.append(col)
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.PATTERN,
                    columns=[col],
                    params={"pattern_name": "iso_date"},
                    rationale="Date column candidate.",
                )
            )
            # Not future check candidate
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.NOT_FUTURE,
                    columns=[col],
                    params={},
                    rationale="Historical date column.",
                )
            )

        elif cp.primary_type == "email":
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.PATTERN,
                    columns=[col],
                    params={"pattern_name": "email"},
                    rationale="Detected standard email addresses.",
                )
            )

        elif cp.primary_type == "phone":
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.PATTERN,
                    columns=[col],
                    params={"pattern_name": "phone"},
                    rationale="Detected phone numbers.",
                )
            )

        elif cp.primary_type == "uuid":
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.PATTERN,
                    columns=[col],
                    params={"pattern_name": "uuid"},
                    rationale="Detected UUID identifiers.",
                )
            )

        # 2. Allowed Values (Categorical with <= 10 distinct values)
        if cp.distinct_count > 1 and cp.distinct_count <= 10 and not cp.is_extreme_sparse:
            categories = [val for val, _ in cp.top_values]
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.ALLOWED_VALUES,
                    columns=[col],
                    params={"allowed_values": categories},
                    rationale=f"Discrete category column with {cp.distinct_count} distinct values.",
                )
            )

        # 3. Not Null candidates (for identity or key-like columns)
        if any(kw in col_lower for kw in ("id", "key", "email", "code", "sku")):
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.NOT_NULL,
                    columns=[col],
                    params={},
                    rationale=f"Column name '{col}' indicates an essential identifier.",
                )
            )

        # 4. Unique candidate (if distinct count close to total rows)
        if cp.distinct_count >= 0.95 * profile.total_rows and profile.total_rows >= 10:
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.UNIQUE,
                    columns=[col],
                    params={},
                    rationale=f"High cardinality ({cp.distinct_count}/{profile.total_rows}) indicates unique key.",
                )
            )

    # 5. Date Order Candidates (e.g. order_date <= ship_date, admit_date <= discharge_date)
    if len(date_cols) >= 2:
        for i in range(len(date_cols)):
            for j in range(i + 1, len(date_cols)):
                c1, c2 = date_cols[i], date_cols[j]
                c1_low, c2_low = c1.lower(), c2.lower()
                # Check semantic ordering patterns
                if ("order" in c1_low and "ship" in c2_low) or ("start" in c1_low and "end" in c2_low) or ("admit" in c1_low and "discharge" in c2_low):
                    candidates.append(
                        RuleCandidate(
                            kind=RuleKind.DATE_ORDER,
                            columns=[c1, c2],
                            params={"col_a": c1, "col_b": c2},
                            rationale=f"Logical chronological sequence: {c1} <= {c2}.",
                        )
                    )

    # 6. Arithmetic Candidates (target = qty * price or target = a + b)
    if len(numeric_cols) >= 3:
        # Check column names like total = quantity * price
        total_col = next((c for c in numeric_cols if any(k in c.lower() for k in ("total", "amount", "cost"))), None)
        qty_col = next((c for c in numeric_cols if any(k in c.lower() for k in ("qty", "quantity", "count"))), None)
        price_col = next((c for c in numeric_cols if any(k in c.lower() for k in ("price", "rate", "unit"))), None)

        if total_col and qty_col and price_col and len({total_col, qty_col, price_col}) == 3:
            candidates.append(
                RuleCandidate(
                    kind=RuleKind.ARITHMETIC,
                    columns=[total_col, qty_col, price_col],
                    params={"target": total_col, "col_a": qty_col, "col_b": price_col, "operation": "*"},
                    rationale=f"Arithmetic accounting identity: {total_col} = {qty_col} * {price_col}.",
                )
            )

    return candidates
