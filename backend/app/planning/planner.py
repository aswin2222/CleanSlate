"""Transformation Planner producing deterministic, dependency-ordered PlanSteps."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
import pandas as pd

from app.inference.dsl import Rule, RuleKind, RuleStatus
from app.ingestion.rowid import ROW_ID_COL
from app.planning.registry import registry
from app.profiling.profiler import DatasetProfile
from app.transforms.base import PlanStep


# Fixed canonical transformation execution sequence defined in Section 4.5:
# missing markers -> whitespace -> case -> parse -> dates -> arithmetic -> dedupe -> outliers -> impute -> drop
TRANSFORMATION_EXECUTION_ORDER = [
    "normalize_missing_markers",
    "trim_whitespace",
    "normalize_case",
    "parse_numeric",
    "standardize_dates",
    "normalize_phone",
    "fix_arithmetic",
    "dedupe_exact",
    "dedupe_fuzzy",
    "cap_outliers",
    "impute_median",
    "impute_mode",
    "merge_categories",
    "drop_rows_violating",
]


class TransformationPlanner:
    """
    Synthesizes active rules and profiling findings into an executable,
    dependency-ordered cleaning plan with pre-execution loss estimates.
    """

    def generate_plan(
        self,
        df: pd.DataFrame,
        profile: DatasetProfile,
        rules: List[Rule],
    ) -> List[PlanStep]:
        """Generates a complete list of PlanSteps ordered by dependency sequence."""
        proposed_steps: List[PlanStep] = []
        data_cols = [c for c in df.columns if c != ROW_ID_COL]

        # 1. Missing markers normalization
        missing_markers_cols = [
            c for c, cp in profile.columns.items() if cp.missing_count > 0 and c in data_cols
        ]
        if missing_markers_cols:
            t = registry.get("normalize_missing_markers")
            if t:
                step = t.plan(df, {"columns": missing_markers_cols})
                proposed_steps.append(step)

        # 2. Trim whitespace
        ws_cols = [
            c for c, cp in profile.columns.items()
            if cp.leading_trailing_whitespace_count > 0 and c in data_cols
        ]
        if ws_cols:
            t = registry.get("trim_whitespace")
            if t:
                step = t.plan(df, {"columns": ws_cols})
                proposed_steps.append(step)

        # 3. Numeric parsing
        num_cols = [
            c for c, cp in profile.columns.items()
            if cp.is_numeric and c in data_cols
        ]
        if num_cols:
            t = registry.get("parse_numeric")
            if t:
                step = t.plan(df, {"columns": num_cols})
                if step.predicted_loss.cells_modified > 0:
                    proposed_steps.append(step)

        # 4. Date standardization
        date_cols = [
            c for c, cp in profile.columns.items()
            if (cp.primary_type == "date" or len(cp.format_variants) > 1) and c in data_cols
        ]
        if date_cols:
            t = registry.get("standardize_dates")
            if t:
                step = t.plan(df, {"columns": date_cols})
                if step.predicted_loss.cells_modified > 0:
                    proposed_steps.append(step)

        # 5. Exact deduplication
        if profile.exact_duplicate_rows > 0:
            t = registry.get("dedupe_exact")
            if t:
                step = t.plan(df, {"subset": data_cols})
                proposed_steps.append(step)

        # 6. Rule-driven transformations (Arithmetic, drop rows, outliers)
        active_rules = [r for r in rules if r.status == RuleStatus.ACTIVE and r.violation_count > 0]
        for rule in active_rules:
            if rule.kind == RuleKind.ARITHMETIC:
                t = registry.get("fix_arithmetic")
                if t:
                    step = t.plan(df, rule.params)
                    step.rule_refs.append(rule.id)
                    proposed_steps.append(step)

            elif rule.kind in (RuleKind.DATE_ORDER, RuleKind.NON_NEGATIVE, RuleKind.RANGE):
                # When violation exists on active rule, propose drop_rows_violating
                t = registry.get("drop_rows_violating")
                if t:
                    params = {
                        "rule_kind": rule.kind.value,
                        "columns": rule.columns,
                        "violating_rids": rule.violating_rids,
                        "rule_description": rule.evidence,
                    }
                    if rule.kind == RuleKind.DATE_ORDER and len(rule.columns) >= 2:
                        params["col_a"] = rule.columns[0]
                        params["col_b"] = rule.columns[1]
                    elif rule.kind == RuleKind.NON_NEGATIVE and rule.columns:
                        params["column"] = rule.columns[0]

                    step = t.plan(df, params)
                    step.rule_refs.append(rule.id)
                    # Hard gate: always requires explicit approval
                    step.requires_approval = True
                    proposed_steps.append(step)

        # 7. Category consolidation (if case inconsistencies detected)
        cat_cols = [
            c for c, cp in profile.columns.items()
            if cp.case_inconsistencies > 0 and c in data_cols
        ]
        if cat_cols:
            t = registry.get("merge_categories")
            if t:
                step = t.plan(df, {"columns": cat_cols})
                if step.predicted_loss.cells_modified > 0:
                    proposed_steps.append(step)

        # 8. Dependency sort according to TRANSFORMATION_EXECUTION_ORDER
        def order_key(step: PlanStep) -> int:
            try:
                return TRANSFORMATION_EXECUTION_ORDER.index(step.transformation)
            except ValueError:
                return 999

        sorted_steps = sorted(proposed_steps, key=order_key)

        # Assign sequence and approval flags
        for seq, step in enumerate(sorted_steps, start=1):
            step.seq = seq
            # Check loss label: if HIGH or drops rows -> requires approval
            if step.predicted_loss.loss_label == "HIGH" or step.predicted_loss.rows_removed > 0:
                step.requires_approval = True
                step.approved = False  # Locked OFF review until human toggles
            else:
                step.approved = True

        return sorted_steps


planner = TransformationPlanner()
