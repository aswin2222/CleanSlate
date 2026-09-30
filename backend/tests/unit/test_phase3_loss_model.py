"""Unit tests for Phase 3: Information Loss Estimation and Calibration."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from app.loss.metrics import (
    compute_shannon_entropy,
    compute_relative_entropy_change,
    compute_jensen_shannon_divergence,
    compute_normalized_wasserstein,
    compute_correlation_drift,
    compute_cardinality_loss,
)
from app.loss.estimator import (
    calculate_loss_between_frames,
    estimate_pipeline_cumulative_loss,
    compare_predicted_vs_actual,
)
from app.planning.registry import registry
from app.transforms.base import PlanStep


class TestLossMetrics:
    def test_shannon_entropy_calculation(self):
        # Uniform distribution across 4 elements: H = log2(4) = 2.0
        s = pd.Series(["A", "B", "C", "D"])
        ent = compute_shannon_entropy(s)
        assert abs(ent - 2.0) < 1e-4

        # Zero entropy when all values identical
        s_const = pd.Series(["A", "A", "A", "A"])
        assert compute_shannon_entropy(s_const) == 0.0

    def test_jensen_shannon_divergence(self):
        s1 = pd.Series(["cat", "dog", "bird"])
        s2 = pd.Series(["cat", "dog", "bird"])
        # Identical distribution -> JSD = 0
        assert compute_jensen_shannon_divergence(s1, s2) == 0.0

        s_disjoint = pd.Series(["fish", "snake", "lizard"])
        jsd = compute_jensen_shannon_divergence(s1, s_disjoint)
        assert jsd > 0.5  # Distinct distributions

    def test_normalized_wasserstein(self):
        s1 = pd.Series([str(i) for i in range(100)])
        s2 = pd.Series([str(i) for i in range(100)])
        assert compute_normalized_wasserstein(s1, s2) == 0.0

        # Shifted distribution
        s_shifted = pd.Series([str(i + 50) for i in range(100)])
        dist = compute_normalized_wasserstein(s1, s_shifted)
        assert dist > 0.0
        assert dist <= 1.0

    def test_correlation_drift(self):
        np.random.seed(42)
        x = np.linspace(1, 100, 50)
        y = x * 2.0 + np.random.normal(0, 5, 50)
        df_b = pd.DataFrame({"x": x.astype(str), "y": y.astype(str)})

        # Unchanged -> 0 drift
        assert compute_correlation_drift(df_b, df_b, ["x", "y"]) == 0.0

        # Break correlation completely
        df_a = pd.DataFrame({"x": x.astype(str), "y": np.random.permutation(y).astype(str)})
        drift = compute_correlation_drift(df_b, df_a, ["x", "y"])
        assert drift > 0.3


class TestLossEstimator:
    def test_loss_score_components_and_labels(self):
        df_b = pd.DataFrame({
            "_rid": list(range(100)),
            "cat": ["A", "B", "C", "D"] * 25,
            "num": [str(i) for i in range(100)],
        })

        # Scenario 1: Minor change (5 cells modified out of 200) -> LOW
        df_a1 = df_b.copy()
        for idx in range(5):
            df_a1.at[idx, "cat"] = "A "
        rep_low = calculate_loss_between_frames(df_b, df_a1)
        assert rep_low.loss_label == "LOW"
        assert rep_low.loss_score < 20.0

        # Scenario 2: Drop 40% of rows -> HIGH
        df_a2 = df_b.iloc[:60].copy()
        rep_high = calculate_loss_between_frames(df_b, df_a2)
        assert rep_high.rows_removed == 40
        assert rep_high.loss_label == "HIGH"
        assert rep_high.loss_score >= 50.0

    def test_predicted_vs_actual_calibration(self):
        pred = {"rows_removed": 15, "cells_modified": 42}
        act = {"rows_removed": 15, "cells_modified": 42}
        calib = compare_predicted_vs_actual(pred, act)
        assert calib["exact_count_match"] is True
        assert calib["rows_error"] == 0
        assert calib["cells_error"] == 0
        assert calib["prediction_accuracy_pct"] == 100.0

    def test_pipeline_cumulative_loss(self):
        # 100 rows dataset where 5 rows have formatting dirt
        df = pd.DataFrame({
            "_rid": list(range(100)),
            "text": ["  hello  "] * 5 + ["world"] * 95,
            "num": ["$10.00"] * 5 + ["20.50"] * 95,
        })
        steps = [
            PlanStep(
                id="s1",
                transformation="trim_whitespace",
                params={"columns": ["text"]},
                target_columns=["text"],
                rationale="trim",
                requires_approval=False,
                predicted_loss=registry.get("trim_whitespace").dry_run(df, {"columns": ["text"]}),
            ),
            PlanStep(
                id="s2",
                transformation="parse_numeric",
                params={"columns": ["num"]},
                target_columns=["num"],
                rationale="parse",
                requires_approval=False,
                predicted_loss=registry.get("parse_numeric").dry_run(df, {"columns": ["num"]}),
            ),
        ]
        cum_report, step_res = estimate_pipeline_cumulative_loss(df, steps)
        assert len(step_res) == 2
        assert cum_report.cells_modified > 0
        assert cum_report.loss_label == "LOW"
        assert "modifies" in cum_report.human_summary
