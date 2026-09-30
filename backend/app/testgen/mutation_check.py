"""Mutation testing checker: injects synthetic faults to measure test suite fault detection rate."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.inference.dsl import Rule, RuleKind
from app.testgen.runner import TestRunner


@dataclass
class MutationResult:
    mutation_type: str
    target_column: str
    row_index: int
    detected: bool
    diagnostic: str


@dataclass
class MutationReport:
    total_mutations: int
    detected_mutations: int
    fault_detection_rate_pct: float
    mutations: List[MutationResult]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MutationChecker:
    """
    Injects K known synthetic faults into the cleaned DataFrame:
    1. Null a cell in a not_null column
    2. Inject a negative number into a non_negative column
    3. Invert chronological order in a date_order pair
    4. Corrupt arithmetic identity (e.g. set total = total + 999)
    Asserts that the validation suite FAILS for each mutation, computing
    the test suite's empirical fault detection rate.
    """

    def __init__(self) -> None:
        self.runner = TestRunner()

    def run_mutation_check(
        self,
        clean_df: pd.DataFrame,
        rules: List[Rule],
        k_faults: int = 10,
    ) -> MutationReport:
        """Injects k faults and evaluates whether the test runner flags the mutation."""
        if clean_df.empty or not rules:
            return MutationReport(0, 0, 100.0, [])

        mutations: List[MutationResult] = []
        detected_count = 0

        # Gather inject-able rules
        injectable_rules = [
            r for r in rules
            if r.kind in (RuleKind.NOT_NULL, RuleKind.NON_NEGATIVE, RuleKind.DATE_ORDER, RuleKind.ARITHMETIC)
        ]

        if not injectable_rules:
            return MutationReport(0, 0, 100.0, [])

        for i in range(k_faults):
            rule = injectable_rules[i % len(injectable_rules)]
            mutant_df = clean_df.copy()
            row_idx = random.randint(0, len(mutant_df) - 1)
            detected = False
            diag = ""

            if rule.kind == RuleKind.NOT_NULL:
                col = rule.columns[0]
                mutant_df.at[row_idx, col] = ""
                m_type = f"null_injection_{col}"

            elif rule.kind == RuleKind.NON_NEGATIVE:
                col = rule.columns[0]
                mutant_df.at[row_idx, col] = "-999.00"
                m_type = f"negative_injection_{col}"

            elif rule.kind == RuleKind.DATE_ORDER:
                c1, c2 = rule.columns[0], rule.columns[1]
                # Reverse dates
                mutant_df.at[row_idx, c1] = "2099-12-31"
                mutant_df.at[row_idx, c2] = "2000-01-01"
                m_type = f"date_order_inversion_{c1}_{c2}"

            elif rule.kind == RuleKind.ARITHMETIC:
                target = rule.columns[0]
                # Corrupt target arithmetic
                mutant_df.at[row_idx, target] = "999999.99"
                m_type = f"arithmetic_corruption_{target}"

            else:
                continue

            # Run test suite against mutant
            suite_rep = self.runner.evaluate_rules_on_frame(mutant_df, rules, stage="mutant")
            if suite_rep.failed > 0:
                detected = True
                detected_count += 1
                diag = f"Fault caught by test suite ({suite_rep.failed} test(s) failed)"
            else:
                diag = "Fault escaped test detection"

            mutations.append(
                MutationResult(
                    mutation_type=m_type,
                    target_column=rule.columns[0],
                    row_index=row_idx,
                    detected=detected,
                    diagnostic=diag,
                )
            )

        total = len(mutations)
        rate = round((detected_count / total) * 100.0, 2) if total > 0 else 100.0

        return MutationReport(
            total_mutations=total,
            detected_mutations=detected_count,
            fault_detection_rate_pct=rate,
            mutations=mutations,
        )


mutation_checker = MutationChecker()
