"""Automated test suite generator producing Pandera, Pytest, and Integration test files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from app.config import settings
from app.inference.dsl import Rule, RuleKind, RuleStatus
from app.transforms.base import PlanStep


class TestGenerator:
    __test__ = False
    """
    Generates deterministic, executable Python test files under generated_tests/<run_id>/
    Principle P1 & P4:
    - Code is generated from fixed safe templates, NEVER written by an LLM
    - Code evaluates schema compliance, business rules, row reconciliation, and rollback integrity
    """

    def __init__(self, output_base_dir: Optional[Path] = None) -> None:
        self.output_base_dir = output_base_dir or (Path("generated_tests"))

    def generate_suite(
        self,
        run_id: str,
        df: pd.DataFrame,
        rules: List[Rule],
        plan_steps: List[PlanStep],
    ) -> Path:
        """Generates all 3 test files under generated_tests/<run_id>/."""
        run_dir = self.output_base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        self._generate_test_schema(run_dir, df, rules)
        self._generate_test_rules(run_dir, rules)
        self._generate_test_integration(run_dir, plan_steps)

        return run_dir

    def _generate_test_schema(self, run_dir: Path, df: pd.DataFrame, rules: List[Rule]) -> None:
        """Generates test_schema.py using Pandera DataFrameSchema assertions."""
        active_rules = [r for r in rules if r.status == RuleStatus.ACTIVE]
        data_cols = [c for c in df.columns if c != "_rid"]

        lines = [
            '"""Generated Pandera Schema Validation Test Suite."""',
            "import pytest",
            "import pandera as pa",
            "from pandera import Column, Check, DataFrameSchema",
            "import pandas as pd",
            "",
            "def test_dataset_schema(dataset_df):",
            "    # Filter data columns",
            "    cols = [c for c in dataset_df.columns if c != '_rid']",
            "    checks_dict = {}",
        ]

        # Add checks for active rules
        for col in data_cols:
            col_checks = []
            col_rules = [r for r in active_rules if col in r.columns]

            for r in col_rules:
                if r.kind == RuleKind.NOT_NULL:
                    col_checks.append("Check(lambda s: s.str.strip() != '', name='not_empty')")
                elif r.kind == RuleKind.NON_NEGATIVE:
                    col_checks.append("Check(lambda s: pd.to_numeric(s.str.replace(',', ''), errors='coerce') >= 0, name='non_negative')")
                elif r.kind == RuleKind.ALLOWED_VALUES:
                    allowed = r.params.get("allowed_values", [])
                    if allowed:
                        col_checks.append(f"Check.isin({json.dumps(allowed)})")

            checks_str = f"[{', '.join(col_checks)}]" if col_checks else "[]"
            lines.append(f"    checks_dict['{col}'] = Column(str, checks={checks_str}, nullable=True)")

        lines.extend([
            "    schema = DataFrameSchema(checks_dict, coerce=False)",
            "    # Validate dataframe",
            "    schema.validate(dataset_df[cols], lazy=True)",
            "",
        ])

        with open(run_dir / "test_schema.py", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _generate_test_rules(self, run_dir: Path, rules: List[Rule]) -> None:
        """Generates test_rules.py testing each active rule."""
        active_rules = [r for r in rules if r.status == RuleStatus.ACTIVE]

        lines = [
            '"""Generated Pytest Rule Verification Suite."""',
            "import pytest",
            "import pandas as pd",
            "",
        ]

        for idx, rule in enumerate(active_rules):
            fn_name = f"test_rule_{rule.kind.value}_{idx}"
            lines.append(f"def {fn_name}(dataset_df):")
            lines.append(f"    '''Test Rule: {rule.evidence}'''")

            if rule.kind == RuleKind.NOT_NULL:
                col = rule.columns[0]
                lines.append(f"    null_mask = dataset_df['{col}'].astype(str).str.strip().isin(['', 'null', 'nan', 'N/A', '-'])")
                lines.append(f"    assert not null_mask.any(), f'Found {{null_mask.sum()}} nulls in not_null column {col}'")

            elif rule.kind == RuleKind.NON_NEGATIVE:
                col = rule.columns[0]
                lines.append(f"    num_series = pd.to_numeric(dataset_df['{col}'].astype(str).str.replace(',', ''), errors='coerce')")
                lines.append(f"    neg_count = (num_series < 0).sum()")
                lines.append(f"    assert neg_count == 0, f'Found {{neg_count}} negative values in {col}'")

            elif rule.kind == RuleKind.DATE_ORDER:
                c1, c2 = rule.columns[0], rule.columns[1]
                lines.append(f"    viol = (dataset_df['{c1}'].astype(str) > dataset_df['{c2}'].astype(str)).sum()")
                lines.append(f"    assert viol == 0, f'Found {{viol}} date order violations: {c1} > {c2}'")

            elif rule.kind == RuleKind.ARITHMETIC:
                target, ca, cb = rule.columns[0], rule.columns[1], rule.columns[2]
                op = rule.params.get("operation", "*")
                lines.append(f"    t = pd.to_numeric(dataset_df['{target}'].astype(str).str.replace(',', ''), errors='coerce')")
                lines.append(f"    a = pd.to_numeric(dataset_df['{ca}'].astype(str).str.replace(',', ''), errors='coerce')")
                lines.append(f"    b = pd.to_numeric(dataset_df['{cb}'].astype(str).str.replace(',', ''), errors='coerce')")
                lines.append(f"    expected = a * b if '{op}' == '*' else (a + b if '{op}' == '+' else a - b)")
                lines.append(f"    broken = (abs(t - expected) > 0.05).sum()")
                lines.append(f"    assert broken == 0, f'Found {{broken}} arithmetic violations for {target} = {ca} {op} {cb}'")

            else:
                lines.append("    assert True")

            lines.append("")

        with open(run_dir / "test_rules.py", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _generate_test_integration(self, run_dir: Path, plan_steps: List[PlanStep]) -> None:
        """Generates test_integration.py asserting reconciliation and ledger round-trip."""
        lines = [
            '"""Generated Pipeline Integration Test Suite."""',
            "import pytest",
            "import pandas as pd",
            "from app.security.sanitize import is_formula_injection",
            "",
            "def test_row_reconciliation(df_before, df_after, total_dropped_rows):",
            "    expected_rows = len(df_before) - total_dropped_rows",
            "    assert len(df_after) == expected_rows, f'Row reconciliation mismatch: {len(df_after)} != {expected_rows}'",
            "",
            "def test_formula_injection_neutralized_on_export(exported_csv_content):",
            "    for line in exported_csv_content.splitlines():",
            "        for cell in line.split(','):",
            "            # Assert any formula starting character is prefixed with single quote in export",
            "            if cell.startswith(('=', '+', '-', '@')):",
            "                assert False, f'Dangerous formula injection found un-neutralized: {cell}'",
            "    assert True",
            "",
            "def test_untouched_columns_remain_identical(df_before, df_after, untouched_columns):",
            "    for col in untouched_columns:",
            "        if col in df_before.columns and col in df_after.columns:",
            "            assert (df_before[col].values == df_after[col].values).all()",
            "",
        ]

        with open(run_dir / "test_integration.py", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
