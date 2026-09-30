"""Statistical metrics for information loss estimation: Shannon Entropy, JSD, Wasserstein, and Correlation."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance

from app.profiling.patterns import is_missing


def compute_shannon_entropy(series: pd.Series) -> float:
    """
    Computes Shannon entropy (base 2) on discrete value frequencies of a column.
    H(X) = - sum(p(x) * log2(p(x)))
    """
    non_nulls = [str(v).strip() for v in series if not is_missing(v)]
    if not non_nulls:
        return 0.0

    counts = pd.Series(non_nulls).value_counts()
    probs = counts / len(non_nulls)
    entropy = -float(np.sum(probs * np.log2(probs + 1e-12)))
    return max(0.0, entropy)


def compute_relative_entropy_change(before_series: pd.Series, after_series: pd.Series) -> float:
    """
    Computes absolute relative change in Shannon entropy:
    |H_after - H_before| / max(1e-6, H_before)
    Clipped to [0.0, 1.0].
    """
    h_before = compute_shannon_entropy(before_series)
    h_after = compute_shannon_entropy(after_series)
    if h_before < 1e-6:
        return min(1.0, h_after)
    rel_change = abs(h_after - h_before) / h_before
    return min(1.0, float(rel_change))


def compute_jensen_shannon_divergence(before_series: pd.Series, after_series: pd.Series) -> float:
    """
    Computes Jensen-Shannon divergence (base 2, range [0, 1]) between categorical distributions.
    Strips whitespace so cosmetic whitespace changes do not falsely register as 100% categorical divergence.
    """
    vals_b = [str(v).strip() for v in before_series if not is_missing(v)]
    vals_a = [str(v).strip() for v in after_series if not is_missing(v)]

    if not vals_b and not vals_a:
        return 0.0
    if not vals_b or not vals_a:
        return 1.0

    all_categories = sorted(list(set(vals_b).union(set(vals_a))))
    counts_b = pd.Series(vals_b).value_counts()
    counts_a = pd.Series(vals_a).value_counts()

    prob_b = np.array([counts_b.get(cat, 0) / len(vals_b) for cat in all_categories])
    prob_a = np.array([counts_a.get(cat, 0) / len(vals_a) for cat in all_categories])

    jsd = jensenshannon(prob_b, prob_a, base=2)
    if math.isnan(jsd) or math.isinf(jsd):
        return 0.0
    return float(np.clip(jsd, 0.0, 1.0))


def compute_normalized_wasserstein(before_series: pd.Series, after_series: pd.Series) -> float:
    """
    Computes 1D Wasserstein distance between numeric values, normalized by (P95 - P5) of before.
    Clipped to [0.0, 1.0].
    """
    def to_nums(s: pd.Series) -> np.ndarray:
        nums = []
        for v in s:
            if not is_missing(v):
                try:
                    cleaned = str(v).replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
                    f = float(cleaned)
                    if not math.isnan(f) and not math.isinf(f):
                        nums.append(f)
                except ValueError:
                    pass
        return np.array(nums, dtype=float)

    u = to_nums(before_series)
    v = to_nums(after_series)

    if len(u) == 0 and len(v) == 0:
        return 0.0
    if len(u) == 0 or len(v) == 0:
        return 1.0

    dist = wasserstein_distance(u, v)
    p05, p95 = np.percentile(u, [5, 95])
    scale = max(1e-6, p95 - p05)
    normalized = dist / scale
    return float(np.clip(normalized, 0.0, 1.0))


def compute_correlation_drift(df_before: pd.DataFrame, df_after: pd.DataFrame, numeric_cols: List[str]) -> float:
    """
    Computes mean absolute change in pairwise Pearson correlation among numeric columns.
    Returns 0.0 if fewer than 2 numeric columns exist.
    """
    if len(numeric_cols) < 2:
        return 0.0

    def get_corr(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        sub = pd.DataFrame()
        for col in numeric_cols:
            if col in df.columns:
                sub[col] = pd.to_numeric(
                    df[col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
                    errors="coerce",
                )
        if sub.shape[1] < 2 or len(sub.dropna()) < 3:
            return None
        return sub.corr(method="pearson").fillna(0.0)

    corr_b = get_corr(df_before)
    corr_a = get_corr(df_after)

    if corr_b is None or corr_a is None:
        return 0.0

    diffs: List[float] = []
    cols = list(corr_b.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c1, c2 = cols[i], cols[j]
            if c1 in corr_a.columns and c2 in corr_a.columns:
                val_b = corr_b.loc[c1, c2]
                val_a = corr_a.loc[c1, c2]
                if not math.isnan(val_b) and not math.isnan(val_a):
                    diffs.append(abs(val_a - val_b))

    if not diffs:
        return 0.0
    mean_drift = float(np.mean(diffs))
    return float(np.clip(mean_drift, 0.0, 1.0))


def compute_cardinality_loss(before_series: pd.Series, after_series: pd.Series) -> float:
    """
    Computes relative distinct count reduction:
    (|U_before| - |U_after|) / max(1, |U_before|)
    Clipped to [0.0, 1.0].
    """
    u_before = len(set(str(v).strip() for v in before_series if not is_missing(v)))
    u_after = len(set(str(v).strip() for v in after_series if not is_missing(v)))

    if u_before <= u_after:
        return 0.0
    loss = (u_before - u_after) / max(1, u_before)
    return float(np.clip(loss, 0.0, 1.0))
