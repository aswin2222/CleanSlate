"""Test runner executing PRE and POST validation suites in an isolated environment."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from app.inference.dsl import Rule, RuleKind
from app.profiling.patterns import is_missing


@dataclass
class TestResultItem:
    name: str
    rule_id: Optional[str]
    outcome: str  # "PASSED" | "FAILED" | "ERROR"
    message: str


@dataclass
class SuiteRunReport:
    stage: str  # "pre" | "post"
    passed: int
    failed: int
    total: int
    results: List[TestResultItem]
    fixed_violations: List[str] = field(default_factory=list)
    remaining_violations: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TestRunner:
    __test__ = False
    """
    Executes generated validation tests in-process or via subprocess against
    pre-cleaned and post-cleaned DataFrames to verify that dirty violations were
    resolved without introducing regressions.
    """

    def evaluate_rules_on_frame(
        self,
        df: pd.DataFrame,
        rules: List[Rule],
        stage: str,
    ) -> SuiteRunReport:
        """Evaluates active rules directly on df, recording passed vs failed assertions."""
        results: List[TestResultItem] = []
        passed = 0
        failed = 0

        for r in rules:
            test_name = f"verify_{r.kind.value}_{'-'.join(r.columns)}"
            is_pass = True
            msg = "Rule satisfied"

            if r.kind == RuleKind.NOT_NULL:
                col = r.columns[0]
                if col in df.columns:
                    null_count = int(df[col].apply(is_missing).sum())
                    if null_count > 0:
                        is_pass = False
                        msg = f"Found {null_count} nulls in '{col}'"

            elif r.kind == RuleKind.NON_NEGATIVE:
                col = r.columns[0]
                if col in df.columns:
                    nums = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
                    neg_count = int((nums < 0).sum())
                    if neg_count > 0:
                        is_pass = False
                        msg = f"Found {neg_count} negative values in '{col}'"

            elif r.kind == RuleKind.DATE_ORDER:
                if len(r.columns) >= 2 and r.columns[0] in df.columns and r.columns[1] in df.columns:
                    c1, c2 = r.columns[0], r.columns[1]
                    bad_order = int((df[c1].astype(str) > df[c2].astype(str)).sum())
                    if bad_order > 0:
                        is_pass = False
                        msg = f"Found {bad_order} date ordering violations ({c1} > {c2})"

            elif r.kind == RuleKind.ARITHMETIC:
                if len(r.columns) >= 3 and all(c in df.columns for c in r.columns):
                    target, ca, cb = r.columns[0], r.columns[1], r.columns[2]
                    op = r.params.get("operation", "*")
                    t = pd.to_numeric(df[target].astype(str).str.replace(",", ""), errors="coerce")
                    a = pd.to_numeric(df[ca].astype(str).str.replace(",", ""), errors="coerce")
                    b = pd.to_numeric(df[cb].astype(str).str.replace(",", ""), errors="coerce")
                    expected = a * b if op == "*" else (a + b if op == "+" else a - b)
                    broken = int((abs(t - expected) > 0.05).sum())
                    if broken > 0:
                        is_pass = False
                        msg = f"Found {broken} arithmetic inconsistencies in {target} = {ca} {op} {cb}"

            outcome = "PASSED" if is_pass else "FAILED"
            if is_pass:
                passed += 1
            else:
                failed += 1

            results.append(
                TestResultItem(
                    name=test_name,
                    rule_id=r.id,
                    outcome=outcome,
                    message=msg,
                )
            )

        return SuiteRunReport(
            stage=stage,
            passed=passed,
            failed=failed,
            total=len(rules),
            results=results,
        )

    def compare_pre_post_runs(
        self,
        pre_report: SuiteRunReport,
        post_report: SuiteRunReport,
    ) -> SuiteRunReport:
        """Compares PRE and POST results to classify fixed violations and detect regressions."""
        pre_map = {res.name: res.outcome for res in pre_report.results}
        post_map = {res.name: res.outcome for res in post_report.results}

        fixed = []
        remaining = []
        regressions = []

        for name, outcome in post_map.items():
            pre_outcome = pre_map.get(name, "UNKNOWN")
            if pre_outcome == "FAILED" and outcome == "PASSED":
                fixed.append(name)
            elif pre_outcome == "FAILED" and outcome == "FAILED":
                remaining.append(name)
            elif pre_outcome == "PASSED" and outcome == "FAILED":
                regressions.append(name)

        post_report.fixed_violations = fixed
        post_report.remaining_violations = remaining
        post_report.regressions = regressions
        return post_report
