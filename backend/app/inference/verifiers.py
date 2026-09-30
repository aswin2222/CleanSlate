"""Empirical rule verification against actual dataset observations."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.config import settings
from app.inference.candidates import RuleCandidate
from app.inference.dsl import Rule, RuleKind, RuleSource, RuleStatus
from app.ingestion.rowid import ROW_ID_COL
from app.profiling.patterns import (
    DATE_EUR,
    DATE_ISO,
    DATE_US,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    UUID_PATTERN,
    is_missing,
)


def verify_candidate(
    candidate: RuleCandidate,
    df: pd.DataFrame,
    min_rows: int = settings.MIN_ROWS_FOR_INFERENCE,
) -> Rule:
    """
    Empirically verifies a candidate rule on df.
    Calculates support, violation count, violating rids, and sample-size calibrated confidence:
      confidence = support * (1.0 - exp(-n_applicable / 50.0))
    Promotes to ACTIVE only if support >= 0.90 and n_applicable >= min_rows (30).
    """
    total_rows = len(df)
    n_applicable = 0
    satisfying_count = 0
    violating_rids: List[int] = []

    kind = candidate.kind
    cols = [c for c in candidate.columns if c in df.columns]

    if not cols:
        return Rule(
            id=f"rule_{uuid.uuid4().hex[:8]}",
            kind=kind,
            columns=candidate.columns,
            params=candidate.params,
            support=0.0,
            confidence=0.0,
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.REJECTED_BY_USER,
            evidence="Rejected: target columns not found in dataset.",
        )

    if kind == RuleKind.DATE_ORDER and len(cols) < 2:
        return Rule(
            id=f"rule_{uuid.uuid4().hex[:8]}",
            kind=kind,
            columns=cols,
            params=candidate.params,
            support=0.0,
            confidence=0.0,
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.REJECTED_BY_USER,
            evidence="Rejected: DATE_ORDER requires 2 valid columns.",
        )

    if kind == RuleKind.ARITHMETIC and len(cols) < 3:
        return Rule(
            id=f"rule_{uuid.uuid4().hex[:8]}",
            kind=kind,
            columns=cols,
            params=candidate.params,
            support=0.0,
            confidence=0.0,
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.REJECTED_BY_USER,
            evidence="Rejected: ARITHMETIC requires 3 valid columns (target, a, b).",
        )

    # Verify rule kind
    if kind == RuleKind.NOT_NULL:
        col = cols[0]
        n_applicable = total_rows
        for idx in range(total_rows):
            val = df.at[idx, col]
            rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
            if not is_missing(val):
                satisfying_count += 1
            else:
                if len(violating_rids) < 50:
                    violating_rids.append(rid)

    elif kind == RuleKind.UNIQUE:
        col = cols[0]
        n_applicable = total_rows
        seen = set()
        for idx in range(total_rows):
            val = str(df.at[idx, col])
            rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
            if val not in seen and not is_missing(val):
                seen.add(val)
                satisfying_count += 1
            else:
                if len(violating_rids) < 50:
                    violating_rids.append(rid)

    elif kind == RuleKind.NON_NEGATIVE:
        col = cols[0]
        for idx in range(total_rows):
            val = df.at[idx, col]
            if not is_missing(val):
                n_applicable += 1
                try:
                    f = float(str(val).replace(",", ""))
                    rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                    if f >= 0:
                        satisfying_count += 1
                    else:
                        if len(violating_rids) < 50:
                            violating_rids.append(rid)
                except ValueError:
                    pass

    elif kind == RuleKind.RANGE:
        col = cols[0]
        min_v = candidate.params.get("min", -math.inf)
        max_v = candidate.params.get("max", math.inf)
        for idx in range(total_rows):
            val = df.at[idx, col]
            if not is_missing(val):
                n_applicable += 1
                try:
                    f = float(str(val).replace(",", ""))
                    rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                    if min_v <= f <= max_v:
                        satisfying_count += 1
                    else:
                        if len(violating_rids) < 50:
                            violating_rids.append(rid)
                except ValueError:
                    pass

    elif kind == RuleKind.PATTERN:
        col = cols[0]
        p_name = candidate.params.get("pattern_name", "")
        for idx in range(total_rows):
            val = df.at[idx, col]
            if not is_missing(val):
                n_applicable += 1
                s = str(val).strip()
                rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                matches = False
                if p_name == "email":
                    matches = bool(EMAIL_PATTERN.match(s))
                elif p_name == "phone":
                    matches = bool(PHONE_PATTERN.match(s))
                elif p_name == "uuid":
                    matches = bool(UUID_PATTERN.match(s))
                elif p_name == "iso_date":
                    matches = bool(DATE_ISO.match(s) or DATE_US.match(s) or DATE_EUR.match(s))

                if matches:
                    satisfying_count += 1
                else:
                    if len(violating_rids) < 50:
                        violating_rids.append(rid)

    elif kind == RuleKind.ALLOWED_VALUES:
        col = cols[0]
        allowed = set(candidate.params.get("allowed_values", []))
        for idx in range(total_rows):
            val = df.at[idx, col]
            if not is_missing(val):
                n_applicable += 1
                rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                if str(val) in allowed:
                    satisfying_count += 1
                else:
                    if len(violating_rids) < 50:
                        violating_rids.append(rid)

    elif kind == RuleKind.DATE_ORDER:
        col_a, col_b = cols[0], cols[1]
        for idx in range(total_rows):
            va, vb = df.at[idx, col_a], df.at[idx, col_b]
            if not is_missing(va) and not is_missing(vb):
                n_applicable += 1
                rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                # ISO date string comparison
                if str(va) <= str(vb):
                    satisfying_count += 1
                else:
                    if len(violating_rids) < 50:
                        violating_rids.append(rid)

    elif kind == RuleKind.ARITHMETIC:
        target, col_a, col_b = cols[0], cols[1], cols[2]
        op = candidate.params.get("operation", "*")
        for idx in range(total_rows):
            vt, va, vb = df.at[idx, target], df.at[idx, col_a], df.at[idx, col_b]
            if not is_missing(vt) and not is_missing(va) and not is_missing(vb):
                n_applicable += 1
                rid = int(df.at[idx, ROW_ID_COL]) if ROW_ID_COL in df.columns else idx
                try:
                    ft = float(str(vt).replace(",", ""))
                    fa = float(str(va).replace(",", ""))
                    fb = float(str(vb).replace(",", ""))
                    expected = fa * fb if op == "*" else (fa + fb if op == "+" else fa - fb)
                    if abs(ft - expected) <= 0.05:
                        satisfying_count += 1
                    else:
                        if len(violating_rids) < 50:
                            violating_rids.append(rid)
                except ValueError:
                    pass

    else:
        # Generic fallback
        n_applicable = total_rows
        satisfying_count = total_rows

    support = round(satisfying_count / n_applicable, 4) if n_applicable > 0 else 0.0
    violation_count = n_applicable - satisfying_count

    # Confidence calculation per specification:
    # confidence = support * (1 - exp(-n_applicable / 50.0))
    sample_factor = 1.0 - math.exp(-n_applicable / 50.0) if n_applicable > 0 else 0.0
    confidence = round(support * sample_factor, 4)

    # Status evaluation
    if n_applicable < min_rows:
        status = RuleStatus.INSUFFICIENT_EVIDENCE
        evidence_text = f"Insufficient evidence: only {n_applicable} applicable rows (minimum {min_rows} required)."
    elif support >= 0.90:
        status = RuleStatus.ACTIVE
        evidence_text = f"Empirical support {support * 100:.1f}% across {n_applicable} rows with {violation_count} violations."
    elif support >= 0.70:
        status = RuleStatus.NEEDS_REVIEW
        evidence_text = f"Borderline support {support * 100:.1f}%; requires human operator review."
    else:
        status = RuleStatus.INSUFFICIENT_EVIDENCE
        evidence_text = f"Low empirical support ({support * 100:.1f}%); rejected automatically."

    return Rule(
        id=candidate.id,
        kind=kind,
        columns=cols,
        params=candidate.params,
        support=support,
        confidence=confidence,
        evidence=evidence_text,
        source=RuleSource.DETERMINISTIC,
        status=status,
        violation_count=violation_count,
        violating_rids=violating_rids,
    )
