"""Semantic analysis layer and deterministic heuristic keyword taxonomy."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.inference.candidates import RuleCandidate, generate_candidate_rules
from app.inference.dsl import Rule, RuleKind, RuleSource, RuleStatus
from app.inference.llm_client import llm_client
from app.inference.verifiers import verify_candidate
from app.profiling.profiler import DatasetProfile
from app.security.pii_mask import mask_sample_values


# Heuristic keyword dictionary mapping column substrings to semantic tags
HEURISTIC_TAXONOMY: Dict[str, str] = {
    "dob": "date_of_birth",
    "birth": "date_of_birth",
    "age": "age",
    "email": "email_address",
    "phone": "phone_number",
    "mobile": "phone_number",
    "tel": "phone_number",
    "price": "unit_price",
    "cost": "unit_cost",
    "amount": "monetary_amount",
    "total": "order_total",
    "subtotal": "order_subtotal",
    "qty": "quantity",
    "quantity": "quantity",
    "start": "start_date",
    "end": "end_date",
    "admit": "admission_date",
    "discharge": "discharge_date",
    "date": "calendar_date",
    "country": "country_code",
    "id": "identifier",
    "key": "primary_key",
    "sku": "product_sku",
    "zip": "postal_code",
    "postal": "postal_code",
    "name": "person_name",
    "gender": "gender",
    "status": "record_status",
}


def infer_heuristic_semantics(columns: List[str]) -> Dict[str, str]:
    """Infers semantic meaning tags using deterministic column-name keyword matching."""
    semantics: Dict[str, str] = {}
    for col in columns:
        col_low = col.lower()
        matched = False
        for kw, tag in HEURISTIC_TAXONOMY.items():
            if kw in col_low:
                semantics[col] = tag
                matched = True
                break
        if not matched:
            semantics[col] = "general_attribute"
    return semantics


def build_masked_summary_payload(profile: DatasetProfile, df: pd.DataFrame) -> str:
    """Prepares anonymized, PII-masked dataset metadata for LLM prompt."""
    summary_obj: Dict[str, Any] = {
        "total_rows": profile.total_rows,
        "total_columns": profile.total_columns,
        "columns": {},
    }

    for col_name, cp in profile.columns.items():
        if col_name == "_rid":
            continue
        raw_vals = df[col_name].dropna().head(20).tolist() if col_name in df.columns else []
        masked_samples = mask_sample_values(raw_vals, max_samples=5)

        summary_obj["columns"][col_name] = {
            "inferred_type": cp.primary_type,
            "null_rate": cp.null_rate,
            "distinct_count": cp.distinct_count,
            "top_patterns": [p for p, _ in cp.pattern_signatures[:3]],
            "samples": masked_samples,
        }

    return json.dumps(summary_obj, indent=2)


def run_semantic_inference(
    profile: DatasetProfile,
    df: pd.DataFrame,
) -> Tuple[Dict[str, str], List[Rule]]:
    """
    Orchestrates full semantic inference pipeline:
    1. Induces deterministic rule candidates and verifies empirical support/confidence.
    2. Enriches with LLM if configured; otherwise gracefully falls back to heuristic taxonomy.
    3. Returns (column_semantics_mapping, verified_rules).
    """
    valid_cols = [c for c in df.columns if c != "_rid"]

    # 1. Deterministic candidates + empirical verification
    candidates = generate_candidate_rules(profile, df)
    verified_rules: List[Rule] = [verify_candidate(c, df) for c in candidates]

    # 2. Semantic layer (LLM or Heuristic)
    column_semantics: Dict[str, str] = {}
    llm_succeeded = False

    if llm_client.is_configured():
        masked_json = build_masked_summary_payload(profile, df)
        llm_resp = llm_client.suggest_semantics_and_rules(masked_json, valid_cols)
        if llm_resp:
            column_semantics = llm_resp.column_semantics
            llm_succeeded = True
            # Add LLM proposed rules through empirical verification
            for r_sug in llm_resp.suggested_rules:
                try:
                    cand = RuleCandidate(
                        kind=RuleKind(r_sug.kind),
                        columns=r_sug.columns,
                        params=r_sug.params,
                        rationale=r_sug.rationale,
                    )
                    verified_rule = verify_candidate(cand, df)
                    verified_rule.source = RuleSource.LLM
                    verified_rules.append(verified_rule)
                except ValueError:
                    pass

    if not llm_succeeded:
        # Transparent heuristic fallback
        column_semantics = infer_heuristic_semantics(valid_cols)
        for r in verified_rules:
            if r.source == RuleSource.LLM:
                r.source = RuleSource.HEURISTIC

    return column_semantics, verified_rules
