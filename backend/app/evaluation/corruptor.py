"""Synthetic dataset corruptor for benchmark and evaluation with ground-truth tracking."""
import random
import copy
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np


class GroundTruthMutation:
    def __init__(self, row_idx: int, col: str, original_val: Any, corrupted_val: Any, mutation_type: str):
        self.row_idx = row_idx
        self.col = col
        self.original_val = original_val
        self.corrupted_val = corrupted_val
        self.mutation_type = mutation_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_idx": self.row_idx,
            "col": self.col,
            "original_val": str(self.original_val),
            "corrupted_val": str(self.corrupted_val),
            "mutation_type": self.mutation_type,
        }


class SyntheticCorruptor:
    """Injects realistic enterprise data anomalies while recording precise ground truth."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        np.random.seed(seed)

    def corrupt(
        self,
        df: pd.DataFrame,
        whitespace_rate: float = 0.1,
        case_rate: float = 0.1,
        date_rate: float = 0.15,
        phone_rate: float = 0.15,
        duplicate_count: int = 5,
        outlier_rate: float = 0.05,
        null_rate: float = 0.05,
        arithmetic_rate: float = 0.05,
    ) -> Tuple[pd.DataFrame, List[GroundTruthMutation]]:
        corrupted = df.copy()
        mutations: List[GroundTruthMutation] = []
        n_rows = len(corrupted)

        # 1. Whitespace Glitches on string columns
        for col in corrupted.select_dtypes(include=["object"]).columns:
            for i in range(n_rows):
                if self.rng.random() < whitespace_rate and pd.notna(corrupted.at[i, col]):
                    orig = corrupted.at[i, col]
                    choice = self.rng.choice(["lead", "trail", "both", "inner"])
                    if choice == "lead":
                        val = "   " + str(orig)
                    elif choice == "trail":
                        val = str(orig) + "  \t"
                    elif choice == "both":
                        val = "  " + str(orig) + "   "
                    else:
                        val = str(orig).replace(" ", "   ")
                    corrupted.at[i, col] = val
                    mutations.append(GroundTruthMutation(i, col, orig, val, "whitespace"))

        # 2. Case Inconsistencies on text/category columns
        for col in corrupted.select_dtypes(include=["object"]).columns:
            if "status" in col.lower() or "category" in col.lower() or "state" in col.lower():
                for i in range(n_rows):
                    if self.rng.random() < case_rate and pd.notna(corrupted.at[i, col]):
                        orig = corrupted.at[i, col]
                        choice = self.rng.choice(["upper", "lower", "mixed"])
                        s = str(orig)
                        if choice == "upper":
                            val = s.upper()
                        elif choice == "lower":
                            val = s.lower()
                        else:
                            val = "".join(c.upper() if idx % 2 == 0 else c.lower() for idx, c in enumerate(s))
                        corrupted.at[i, col] = val
                        mutations.append(GroundTruthMutation(i, col, orig, val, "case_inconsistency"))

        # 3. Date Format Glitches
        for col in corrupted.columns:
            if "date" in col.lower():
                for i in range(n_rows):
                    if self.rng.random() < date_rate and pd.notna(corrupted.at[i, col]):
                        orig = corrupted.at[i, col]
                        # E.g. swap YYYY-MM-DD to MM/DD/YYYY or DD-Mon-YYYY
                        try:
                            dt = pd.to_datetime(orig)
                            fmt = self.rng.choice(["%m/%d/%Y", "%d-%b-%Y", "%Y/%m/%d %H:%M:%S"])
                            val = dt.strftime(fmt)
                            corrupted.at[i, col] = val
                            mutations.append(GroundTruthMutation(i, col, orig, val, "date_format"))
                        except Exception:
                            pass

        # 4. Outlier Injections in numeric columns
        for col in corrupted.select_dtypes(include=[np.number]).columns:
            if "id" not in col.lower() and "rid" not in col.lower():
                for i in range(n_rows):
                    if self.rng.random() < outlier_rate and pd.notna(corrupted.at[i, col]):
                        orig = corrupted.at[i, col]
                        mult = self.rng.choice([10.0, 50.0, -5.0])
                        val = orig * mult
                        corrupted.at[i, col] = val
                        mutations.append(GroundTruthMutation(i, col, orig, val, "outlier"))

        # 5. Missing value injections
        for col in corrupted.columns:
            if "_rid" not in col.lower():
                for i in range(n_rows):
                    if self.rng.random() < null_rate and pd.notna(corrupted.at[i, col]):
                        orig = corrupted.at[i, col]
                        val = np.nan
                        corrupted.at[i, col] = val
                        mutations.append(GroundTruthMutation(i, col, orig, val, "missing_value"))

        # 6. Duplicate Rows
        if duplicate_count > 0 and n_rows > 5:
            dup_indices = self.rng.sample(range(n_rows), min(duplicate_count, n_rows))
            dup_rows = corrupted.iloc[dup_indices].copy()
            corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
            for idx in dup_indices:
                mutations.append(GroundTruthMutation(len(corrupted) - 1, "_row", "unique", "duplicate", "exact_duplicate"))

        return corrupted, mutations
