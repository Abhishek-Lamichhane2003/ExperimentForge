from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .statistics import (
    ALPHA,
    AnalysisError,
    adjust_pvalues_bh,
    binary_test,
    continuous_test,
    recommended_sample_size,
    sample_ratio_mismatch,
)

RESERVED = {"user_id", "variant"}
POST_TREATMENT_HINTS = (
    "revenue", "converted", "conversion", "session", "click", "purchase",
    "order", "outcome", "watch", "engagement", "metric",
)


@dataclass
class PipelineOutput:
    cleaned: pd.DataFrame
    result: dict[str, Any]


def _clean_variant(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().replace({"a": "control", "b": "treatment"})


def _quality_before_cleaning(raw: pd.DataFrame, metric: str) -> dict[str, int]:
    duplicate_users = int(raw.duplicated(subset=["user_id"]).sum()) if "user_id" in raw.columns else 0
    missing_metric = int(pd.to_numeric(raw[metric], errors="coerce").isna().sum()) if metric in raw.columns else 0
    normalized_variant = _clean_variant(raw["variant"]) if "variant" in raw.columns else pd.Series(dtype=str)
    invalid_variant = int((~normalized_variant.isin(["control", "treatment"])).sum()) if len(normalized_variant) else 0
    return {
        "original_rows": int(len(raw)),
        "missing_cells_original": int(raw.isna().sum().sum()),
        "duplicate_users_removed": duplicate_users,
        "missing_metric_rows_removed": missing_metric,
        "invalid_variant_rows_removed": invalid_variant,
        "columns": int(len(raw.columns)),
    }


def _data_quality(raw_quality: dict[str, int], cleaned: pd.DataFrame) -> dict[str, Any]:
    return {
        **raw_quality,
        "rows_after_cleaning": int(len(cleaned)),
        "rows_removed": int(raw_quality["original_rows"] - len(cleaned)),
        "missing_cells_after_cleaning": int(cleaned.isna().sum().sum()),
    }


def _segment_analysis(df: pd.DataFrame, metric: str, metric_type: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    candidates: list[str] = []
    for col in df.columns:
        if col in RESERVED or col == metric:
            continue
        nunique = df[col].nunique(dropna=True)
        if 2 <= nunique <= 10 and (df[col].dtype == "object" or str(df[col].dtype).startswith("category")):
            candidates.append(col)
    for col in candidates[:5]:
        for value, seg in df.groupby(col, dropna=False):
            c = seg.loc[seg["variant"] == "control", metric]
            t = seg.loc[seg["variant"] == "treatment", metric]
            if len(c) < 25 or len(t) < 25:
                continue
            try:
                stat = binary_test(c, t) if metric_type == "binary" else continuous_test(c, t)
            except AnalysisError:
                continue
            results.append({
                "feature": col,
                "segment": str(value),
                "control_n": int(len(c)),
                "treatment_n": int(len(t)),
                "effect": float(stat["absolute_effect"]),
                "lift_pct": stat["relative_lift_pct"],
                "p_value": float(stat["p_value"]),
                "direction_raw": stat["direction"],
            })
    adjusted = adjust_pvalues_bh([r["p_value"] for r in results])
    for row, adj in zip(results, adjusted):
        row["adjusted_p_value"] = adj
        row["significant"] = bool(adj < ALPHA)
        row["direction"] = "positive" if row["significant"] and row["effect"] > 0 else "negative" if row["significant"] and row["effect"] < 0 else "neutral"
    return sorted(results, key=lambda x: (not x["significant"], x["adjusted_p_value"], -abs(x["effect"])))[:20]


def _anomaly_detection(df: pd.DataFrame, metric: str) -> dict[str, Any]:
    numeric = [c for c in df.select_dtypes(include=[np.number]).columns if c != metric]
    if not numeric or len(df) < 50:
        return {"enabled": False, "reason": "Not enough numeric features for anomaly detection."}
    x = df[numeric].replace([np.inf, -np.inf], np.nan)
    medians = x.median(numeric_only=True)
    x = x.fillna(medians).dropna(axis=1, how="all")
    if x.empty:
        return {"enabled": False, "reason": "No usable numeric features."}
    model = IsolationForest(contamination=min(0.02, max(0.005, 10 / len(df))), random_state=42)
    labels = model.fit_predict(x)
    count = int((labels == -1).sum())
    return {"enabled": True, "anomaly_count": count, "anomaly_rate": float(count / len(df)), "features": list(x.columns[:8])}


def _is_plausible_pretreatment_feature(name: str) -> bool:
    lower = name.lower()
    return not any(hint in lower for hint in POST_TREATMENT_HINTS)


def _ml_heterogeneity(df: pd.DataFrame, metric: str, metric_type: str) -> dict[str, Any]:
    if len(df) < 300:
        return {"enabled": False, "reason": "At least 300 rows are required for the treatment-effect model."}
    features = [c for c in df.columns if c not in {metric, "variant", "user_id"} and _is_plausible_pretreatment_feature(c)]
    if not features:
        return {"enabled": False, "reason": "No plausible pre-treatment feature columns are available."}
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in features if c not in numeric and 2 <= df[c].nunique(dropna=True) <= 20]
    used = numeric[:8] + categorical[:5]
    if not used:
        return {"enabled": False, "reason": "No supported pre-treatment feature columns are available."}
    x = df[used].copy()
    for col in numeric:
        if col in x:
            values = pd.to_numeric(x[col], errors="coerce")
            x[col] = values.fillna(values.median())
    for col in categorical:
        if col in x:
            x[col] = x[col].fillna("missing").astype(str)
    transformer = ColumnTransformer([
        ("num", "passthrough", [c for c in used if c in numeric]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), [c for c in used if c in categorical]),
    ], remainder="drop")
    model_cls = RandomForestClassifier if metric_type == "binary" else RandomForestRegressor
    kwargs = {"n_estimators": 120, "max_depth": 8, "min_samples_leaf": 8, "random_state": 42, "n_jobs": -1}
    control_mask = df["variant"] == "control"
    treatment_mask = df["variant"] == "treatment"
    if control_mask.sum() < 100 or treatment_mask.sum() < 100:
        return {"enabled": False, "reason": "Each variant needs at least 100 rows for the ML treatment-effect model."}
    control_model = Pipeline([("prep", transformer), ("model", model_cls(**kwargs))])
    treatment_model = Pipeline([("prep", transformer), ("model", model_cls(**kwargs))])
    try:
        control_model.fit(x.loc[control_mask], df.loc[control_mask, metric])
        treatment_model.fit(x.loc[treatment_mask], df.loc[treatment_mask, metric])
        if metric_type == "binary":
            pred_c = control_model.predict_proba(x)[:, 1]
            pred_t = treatment_model.predict_proba(x)[:, 1]
        else:
            pred_c = control_model.predict(x)
            pred_t = treatment_model.predict(x)
        tau = pred_t - pred_c
        q25, q75 = np.quantile(tau, [0.25, 0.75])
        return {
            "enabled": True,
            "method": "T-learner with random forests",
            "average_predicted_effect": float(np.mean(tau)),
            "top_quartile_effect": float(np.mean(tau[tau >= q75])),
            "bottom_quartile_effect": float(np.mean(tau[tau <= q25])),
            "predicted_effect_std": float(np.std(tau)),
            "features_used": used,
            "feature_policy": "Heuristic filter excludes columns whose names look like post-treatment outcomes.",
            "note": "Exploratory heterogeneity model; use pre-treatment covariates only and validate findings with follow-up experiments.",
        }
    except Exception as exc:
        return {"enabled": False, "reason": f"ML model skipped: {type(exc).__name__}"}


def _decision_score(primary: dict[str, Any], srm: dict[str, Any], harmful: list[dict[str, Any]], quality: dict[str, Any]) -> int:
    score = 50
    if primary["significant"] and primary["absolute_effect"] > 0:
        score += 30
    elif primary["significant"] and primary["absolute_effect"] < 0:
        score -= 35
    else:
        score -= 10
    if srm["detected"]:
        score -= 30
    if harmful:
        score -= 40
    if quality["original_rows"] and quality["rows_removed"] / quality["original_rows"] > 0.05:
        score -= 10
    return max(0, min(100, score))


def analyze_dataframe(raw: pd.DataFrame, metric: str, metric_type: str) -> PipelineOutput:
    if metric_type not in {"binary", "continuous"}:
        raise AnalysisError("metric_type must be 'binary' or 'continuous'.")
    if "variant" not in raw.columns:
        raise AnalysisError("Dataset must contain a 'variant' column.")
    if metric not in raw.columns:
        raise AnalysisError(f"Metric column '{metric}' was not found.")
    raw_quality = _quality_before_cleaning(raw, metric)
    df = raw.copy()
    df["variant"] = _clean_variant(df["variant"])
    df = df[df["variant"].isin(["control", "treatment"])].copy()
    if "user_id" not in df.columns:
        df.insert(0, "user_id", [f"row_{i}" for i in range(len(df))])
    df = df.drop_duplicates(subset=["user_id"], keep="first")
    df[metric] = pd.to_numeric(df[metric], errors="coerce")
    df = df.dropna(subset=[metric, "variant"])
    if len(df) < 40:
        raise AnalysisError("At least 40 valid rows are required.")
    c = df.loc[df["variant"] == "control", metric]
    t = df.loc[df["variant"] == "treatment", metric]
    if len(c) < 20 or len(t) < 20:
        raise AnalysisError("Each variant needs at least 20 rows.")
    primary = binary_test(c, t) if metric_type == "binary" else continuous_test(c, t)
    srm = sample_ratio_mismatch(df["variant"])
    quality = _data_quality(raw_quality, df)
    segments = _segment_analysis(df, metric, metric_type)
    anomalies = _anomaly_detection(df, metric)
    ml = _ml_heterogeneity(df, metric, metric_type)
    sample_needed = recommended_sample_size(metric_type, primary["control_value"])

    warnings: list[str] = []
    if srm["detected"]:
        warnings.append("Sample-ratio mismatch detected. Check randomization or assignment logging before trusting the result.")
    if quality["original_rows"] and quality["rows_removed"] / quality["original_rows"] > 0.05:
        warnings.append("More than 5% of rows were removed during cleaning.")
    harmful = [s for s in segments if s["significant"] and s["effect"] < 0]
    if harmful:
        warnings.append(f"{len(harmful)} negative segment(s) remain significant after Benjamini-Hochberg correction.")

    if srm["detected"]:
        decision = "INVESTIGATE"
    elif primary["significant"] and primary["absolute_effect"] > 0 and not harmful:
        decision = "SHIP"
    elif primary["significant"] and primary["absolute_effect"] < 0:
        decision = "DO NOT SHIP"
    elif harmful:
        decision = "HOLD"
    else:
        decision = "KEEP TESTING"

    pipeline = [
        {"stage": "Schema validation", "status": "passed"},
        {"stage": "Data cleaning", "status": "passed", "detail": f"{quality['rows_after_cleaning']} rows retained"},
        {"stage": "Statistical test", "status": "passed", "detail": primary["test"]},
        {"stage": "Segment scan", "status": "passed", "detail": f"{len(segments)} BH-adjusted segment results"},
        {"stage": "ML heterogeneity", "status": "passed" if ml.get("enabled") else "skipped", "detail": ml.get("method") or ml.get("reason")},
    ]
    result = {
        "metric": metric,
        "metric_type": metric_type,
        "decision": decision,
        "decision_score": _decision_score(primary, srm, harmful, quality),
        "primary": primary,
        "sample_ratio_mismatch": srm,
        "data_quality": quality,
        "segments": segments,
        "segment_multiple_testing": "Benjamini-Hochberg FDR correction",
        "anomalies": anomalies,
        "ml_heterogeneity": ml,
        "recommended_sample_size_per_variant": sample_needed,
        "warnings": warnings,
        "pipeline": pipeline,
    }
    return PipelineOutput(cleaned=df, result=result)
