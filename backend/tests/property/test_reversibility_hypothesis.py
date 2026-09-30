"""Hypothesis property-based tests for mathematical reversibility of all transformations."""
from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given, settings as hyp_settings, strategies as st

from app.execution.canonical_hash import compute_canonical_hash
from app.execution.executor import PipelineExecutor
from app.execution.ledger import TransformationLedger
from app.execution.rollback import RollbackEngine
from app.ingestion.rowid import ROW_ID_COL, assign_stable_row_ids
from app.planning.registry import registry
from app.transforms.base import PlanStep, Transformation


# Strategy for generating arbitrary messy string data
messy_string_st = st.one_of(
    st.text(min_size=0, max_size=30),
    st.sampled_from(["", " ", "N/A", "null", "NULL", "None", "nan", "-", "--", "?", "unknown", "#N/A"]),
    st.sampled_from(["  leading", "trailing  ", "  both  ", "multiple   spaces   inside"]),
    st.sampled_from(["2024-01-01", "01/15/2024", "25-12-2023", "2024-05-10T12:00:00Z"]),
    st.sampled_from(["$1,234.50", "€99.99", "5000", "42.123", "-15.00", "99%"]),
    st.sampled_from(["+1-800-555-1234", "9876543210", "+91 9988776655", "123-4567"]),
    st.sampled_from(["apple", "Apple", "APPLE", "banana", "Banana", "aple"]),
    st.sampled_from(["=cmd|'calc'!A0", "+HYPERLINK('bad')", "@SUM(1+1)", "-100"]),
)

@st.composite
def messy_dataframe_st(draw):
    num_rows = draw(st.integers(min_value=1, max_value=25))
    columns = ["col_text", "col_num", "col_date", "col_cat"]
    data = {c: [draw(messy_string_st) for _ in range(num_rows)] for c in columns}
    df = pd.DataFrame(data, dtype=str)
    return assign_stable_row_ids(df)


class TestReversibilityHypothesis:
    """
    Core Mathematical Reversibility Suite:
    For every registered transformation, apply followed by invert MUST produce
    a DataFrame with the identical canonical SHA-256 hash.
    """

    @pytest.mark.parametrize("transform_name", [
        "normalize_missing_markers",
        "trim_whitespace",
        "normalize_case",
        "standardize_dates",
        "parse_numeric",
        "normalize_phone",
        "dedupe_exact",
        "dedupe_fuzzy",
        "cap_outliers",
        "impute_median",
        "impute_mode",
        "merge_categories",
        "drop_rows_violating",
        "flag_only",
    ])
    @given(df=messy_dataframe_st())
    @hyp_settings(max_examples=10, deadline=5000)
    def test_single_transformation_apply_invert_hash_identity(self, transform_name: str, df: pd.DataFrame):
        transform = registry.get(transform_name)
        assert transform is not None, f"Transform {transform_name} not registered"

        orig_hash = compute_canonical_hash(df)
        data_cols = [c for c in df.columns if c != ROW_ID_COL]

        # Parameters customized per transformation
        params = {"columns": data_cols, "subset": data_cols}
        if transform_name == "normalize_case":
            params["case"] = "title"
        elif transform_name == "drop_rows_violating":
            params["indices"] = [0] if len(df) > 1 else []

        # 1. Apply
        new_df, delta = transform.apply(df, params)

        # 2. Invert
        restored_df = transform.invert(new_df, delta)
        restored_hash = compute_canonical_hash(restored_df)

        assert orig_hash == restored_hash, (
            f"Transformation '{transform_name}' failed hash equality on invert! "
            f"Original: {orig_hash}, Restored: {restored_hash}"
        )

    @given(df=messy_dataframe_st())
    @hyp_settings(max_examples=5, deadline=8000)
    def test_pipeline_sequence_rollback_all_hash_identity(self, df: pd.DataFrame):
        """
        Executes a sequence of multiple random transformations, then rolls back all.
        Asserts canonical hash matches original with 100% fidelity.
        """
        orig_hash = compute_canonical_hash(df)
        ledger = TransformationLedger(run_id="hyp_test_run")
        executor = PipelineExecutor(ledger=ledger)
        rollback = RollbackEngine(ledger=ledger, original_hash=orig_hash)

        data_cols = [c for c in df.columns if c != ROW_ID_COL]

        # Construct plan with 4 chained steps
        steps = [
            PlanStep(
                id="s1",
                transformation="normalize_missing_markers",
                params={"columns": data_cols},
                target_columns=data_cols,
                rationale="Step 1",
                requires_approval=False,
                predicted_loss=registry.get("normalize_missing_markers").dry_run(df, {"columns": data_cols}),
            ),
            PlanStep(
                id="s2",
                transformation="trim_whitespace",
                params={"columns": data_cols},
                target_columns=data_cols,
                rationale="Step 2",
                requires_approval=False,
                predicted_loss=registry.get("trim_whitespace").dry_run(df, {"columns": data_cols}),
            ),
            PlanStep(
                id="s3",
                transformation="dedupe_exact",
                params={"subset": data_cols},
                target_columns=data_cols,
                rationale="Step 3",
                requires_approval=False,
                predicted_loss=registry.get("dedupe_exact").dry_run(df, {"subset": data_cols}),
            ),
        ]

        exec_res = executor.execute_plan(df, steps)
        assert exec_res.success, f"Execution failed: {exec_res.error_message}"

        # Rollback all steps
        rollback_res = rollback.rollback_all(exec_res.current_df)
        assert rollback_res.matches_original, (
            f"Rollback all failed hash match! Orig={orig_hash}, Restored={rollback_res.hash_current}"
        )
