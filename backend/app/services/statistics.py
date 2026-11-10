from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05


class AnalysisError(ValueError):
    pass


def _normal_cdf(x: float) -> float:
    return float(stats.norm.cdf(x))


def _effect_label(p_value: float, effect: float) -> str:
    if p_value < ALPHA and effect > 0:
        return "positive"
    if p_value < ALPHA and effect < 0:
        return "negative"
    return "neutral"


def adjust_pvalues_bh(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR correction, returned in original order."""
    if not p_values:
        return []
    arr = np.asarray(p_values, dtype=float)
    if np.any(~np.isfinite(arr)):
        raise AnalysisError("Segment analysis produced a non-finite p-value.")
    n = len(arr)
    order = np.argsort(arr)
    ranked = arr[order]
    adjusted_ranked = np.empty(n, dtype=float)
    running = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        running = min(running, ranked[i] * n / rank)
        adjusted_ranked[i] = min(running, 1.0)
    adjusted = np.empty(n, dtype=float)
    adjusted[order] = adjusted_ranked
    return [float(x) for x in adjusted]


def binary_test(control: pd.Series, treatment: pd.Series) -> dict[str, Any]:
    c = pd.to_numeric(control, errors="coerce").dropna().astype(float)
    t = pd.to_numeric(treatment, errors="coerce").dropna().astype(float)
    values = set(pd.concat([c, t]).unique())
    if not values.issubset({0.0, 1.0}):
        raise AnalysisError("Binary metrics must contain only 0/1 values.")
    n_c, n_t = len(c), len(t)
    if n_c < 2 or n_t < 2:
        raise AnalysisError("Each variant needs at least two observations.")
    p_c, p_t = float(c.mean()), float(t.mean())
    pooled = (c.sum() + t.sum()) / (n_c + n_t)
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / n_c + 1 / n_t), 1e-12))
    z = (p_t - p_c) / se
    p_value = 2 * (1 - _normal_cdf(abs(z)))
    diff = p_t - p_c
    unpooled_se = math.sqrt(max(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t, 1e-12))
    lo, hi = diff - 1.96 * unpooled_se, diff + 1.96 * unpooled_se
    lift = (diff / p_c * 100) if p_c else None
    h = 2 * math.asin(math.sqrt(p_t)) - 2 * math.asin(math.sqrt(p_c))
    return {
        "control_value": p_c,
        "treatment_value": p_t,
        "absolute_effect": diff,
        "relative_lift_pct": lift,
        "p_value": float(p_value),
        "confidence_interval": [float(lo), float(hi)],
        "effect_size": float(h),
        "effect_size_name": "Cohen's h",
        "significant": bool(p_value < ALPHA),
        "direction": _effect_label(p_value, diff),
        "test": "two-proportion z-test",
    }


def continuous_test(control: pd.Series, treatment: pd.Series) -> dict[str, Any]:
    c = pd.to_numeric(control, errors="coerce").dropna().astype(float)
    t = pd.to_numeric(treatment, errors="coerce").dropna().astype(float)
    if len(c) < 2 or len(t) < 2:
        raise AnalysisError("Each variant needs at least two numeric observations.")
    if not np.isfinite(c.to_numpy()).all() or not np.isfinite(t.to_numpy()).all():
        raise AnalysisError("Continuous metrics must contain finite numeric values.")
    var_c, var_t = float(c.var(ddof=1)), float(t.var(ddof=1))
    if var_c <= 0 or var_t <= 0:
        raise AnalysisError("Continuous metrics need variation in both variants.")
    mean_c, mean_t = float(c.mean()), float(t.mean())
    test = stats.ttest_ind(t, c, equal_var=False, nan_policy="omit")
    p_value = float(test.pvalue)
    if not math.isfinite(p_value):
        raise AnalysisError("Continuous test could not produce a finite p-value.")
    diff = mean_t - mean_c
    se = math.sqrt(var_c / len(c) + var_t / len(t))
    df_num = (var_c / len(c) + var_t / len(t)) ** 2
    df_den = ((var_c / len(c)) ** 2 / (len(c) - 1)) + ((var_t / len(t)) ** 2 / (len(t) - 1))
    dof = df_num / max(df_den, 1e-12)
    critical = float(stats.t.ppf(0.975, dof))
    lo, hi = diff - critical * se, diff + critical * se
    pooled_sd = math.sqrt(((len(c) - 1) * var_c + (len(t) - 1) * var_t) / max(len(c) + len(t) - 2, 1))
    d = diff / pooled_sd if pooled_sd > 0 else 0.0
    lift = (diff / mean_c * 100) if mean_c else None
    return {
        "control_value": mean_c,
        "treatment_value": mean_t,
        "absolute_effect": diff,
        "relative_lift_pct": lift,
        "p_value": p_value,
        "confidence_interval": [float(lo), float(hi)],
        "effect_size": float(d),
        "effect_size_name": "Cohen's d",
        "significant": bool(p_value < ALPHA),
        "direction": _effect_label(p_value, diff),
        "test": "Welch's t-test",
    }


def sample_ratio_mismatch(variant: pd.Series) -> dict[str, Any]:
    counts = variant.value_counts()
    control = int(counts.get("control", 0))
    treatment = int(counts.get("treatment", 0))
    total = control + treatment
    if total == 0:
        return {"detected": True, "p_value": 0.0, "control_n": 0, "treatment_n": 0, "expected_split": [0.5, 0.5]}
    expected = total / 2
    chi2 = ((control - expected) ** 2 / expected) + ((treatment - expected) ** 2 / expected)
    p_value = float(1 - stats.chi2.cdf(chi2, df=1))
    return {
        "detected": bool(p_value < 0.01),
        "p_value": p_value,
        "control_n": control,
        "treatment_n": treatment,
        "expected_split": [0.5, 0.5],
    }


def recommended_sample_size(metric_type: str, baseline: float, mde_relative: float = 0.05) -> int | None:
    try:
        if metric_type == "binary":
            target = min(max(baseline * (1 + mde_relative), 1e-4), 0.9999)
            h = abs(2 * math.asin(math.sqrt(target)) - 2 * math.asin(math.sqrt(baseline)))
            if h <= 1e-9:
                return None
            z_alpha, z_beta = 1.96, 0.84
            return int(math.ceil(2 * ((z_alpha + z_beta) / h) ** 2))
    except Exception:
        return None
    return None
