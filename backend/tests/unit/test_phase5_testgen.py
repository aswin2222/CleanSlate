"""Unit tests for Phase 5: Test Generation, Runner, and Mutation Testing."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pandas as pd
import pytest

from app.inference.dsl import Rule, RuleKind, RuleSource, RuleStatus
from app.testgen.generator import TestGenerator
from app.testgen.runner import TestRunner
from app.testgen.mutation_check import MutationChecker


@pytest.fixture
def sample_rules():
    return [
        Rule(
            id="r1",
            kind=RuleKind.NOT_NULL,
            columns=["customer_id"],
            params={},
            support=1.0,
            confidence=1.0,
            evidence="customer_id cannot be null",
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.ACTIVE,
        ),
        Rule(
            id="r2",
            kind=RuleKind.NON_NEGATIVE,
            columns=["amount"],
            params={},
            support=1.0,
            confidence=0.98,
            evidence="amount must be non-negative",
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.ACTIVE,
        ),
        Rule(
            id="r3",
            kind=RuleKind.ARITHMETIC,
            columns=["total", "qty", "price"],
            params={"operation": "*"},
            support=1.0,
            confidence=0.95,
            evidence="total = qty * price",
            source=RuleSource.DETERMINISTIC,
            status=RuleStatus.ACTIVE,
        ),
    ]


class TestTestGenAndRunner:
    def test_test_generator_creates_files(self, sample_rules):
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestGenerator(output_base_dir=Path(tmpdir))
            df = pd.DataFrame({
                "customer_id": ["1", "2"],
                "amount": ["10", "20"],
                "total": ["20", "40"],
                "qty": ["2", "2"],
                "price": ["10", "20"],
            })
            suite_dir = generator.generate_suite(
                run_id="run_test",
                df=df,
                rules=sample_rules,
                plan_steps=[],
            )
            assert (suite_dir / "test_schema.py").exists()
            assert (suite_dir / "test_rules.py").exists()
            assert (suite_dir / "test_integration.py").exists()

            content = (suite_dir / "test_rules.py").read_text(encoding="utf-8")
            assert "test_rule_not_null_0" in content
            assert "test_rule_arithmetic_2" in content

    def test_runner_evaluates_pre_and_post_reconciliation(self, sample_rules):
        runner = TestRunner()

        # Pre dataset with violations (null customer_id, broken arithmetic)
        df_pre = pd.DataFrame({
            "customer_id": ["1", ""],  # 1 null
            "amount": ["10", "20"],
            "total": ["20", "999"],   # 1 broken arithmetic (2*20 != 999)
            "qty": ["2", "2"],
            "price": ["10", "20"],
        })

        # Post dataset with violations fixed
        df_post = pd.DataFrame({
            "customer_id": ["1", "2"],
            "amount": ["10", "20"],
            "total": ["20", "40"],
            "qty": ["2", "2"],
            "price": ["10", "20"],
        })

        pre_rep = runner.evaluate_rules_on_frame(df_pre, sample_rules, stage="pre")
        assert pre_rep.failed == 2
        assert pre_rep.passed == 1

        post_rep = runner.evaluate_rules_on_frame(df_post, sample_rules, stage="post")
        assert post_rep.failed == 0
        assert post_rep.passed == 3

        compared = runner.compare_pre_post_runs(pre_rep, post_rep)
        assert len(compared.fixed_violations) == 2
        assert len(compared.remaining_violations) == 0
        assert len(compared.regressions) == 0

    def test_mutation_checker_achieves_100pct_fault_detection(self, sample_rules):
        checker = MutationChecker()
        df_clean = pd.DataFrame({
            "_rid": list(range(20)),
            "customer_id": [str(i) for i in range(20)],
            "amount": ["100"] * 20,
            "total": ["200"] * 20,
            "qty": ["2"] * 20,
            "price": ["100"] * 20,
        })
        rep = checker.run_mutation_check(df_clean, sample_rules, k_faults=6)
        assert rep.total_mutations == 6
        assert rep.detected_mutations == 6
        assert rep.fault_detection_rate_pct == 100.0
