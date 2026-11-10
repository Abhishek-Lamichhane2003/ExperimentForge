import pandas as pd
from backend.app.services.statistics import binary_test, sample_ratio_mismatch
from backend.app.services.pipeline import analyze_dataframe
from backend.app.services.demo import generate_demo


def test_binary_test_detects_positive_effect():
    control = pd.Series([0] * 80 + [1] * 20)
    treatment = pd.Series([0] * 60 + [1] * 40)
    result = binary_test(control, treatment)
    assert result["treatment_value"] > result["control_value"]
    assert result["significant"] is True
    assert result["direction"] == "positive"


def test_sample_ratio_mismatch():
    variants = pd.Series(["control"] * 900 + ["treatment"] * 100)
    result = sample_ratio_mismatch(variants)
    assert result["detected"] is True
    assert result["p_value"] < 0.01


def test_demo_pipeline_has_segments_and_ml():
    frame = generate_demo(n=1200)
    output = analyze_dataframe(frame, "converted", "binary")
    assert output.result["primary"]["control_value"] >= 0
    assert output.result["decision"] in {"SHIP", "HOLD", "KEEP TESTING", "INVESTIGATE", "DO NOT SHIP"}
    assert len(output.result["segments"]) > 0
    assert output.result["ml_heterogeneity"]["enabled"] is True


def test_continuous_pipeline():
    frame = generate_demo(n=1000)
    output = analyze_dataframe(frame, "session_minutes", "continuous")
    assert output.result["primary"]["test"] == "Welch's t-test"
    assert output.result["data_quality"]["rows_after_cleaning"] == 1000


def test_segment_pvalues_are_bh_adjusted():
    frame = generate_demo(n=2400)
    result = analyze_dataframe(frame, "converted", "binary").result
    assert result["segment_multiple_testing"] == "Benjamini-Hochberg FDR correction"
    assert result["segments"]
    assert all("adjusted_p_value" in row for row in result["segments"])
    assert all(row["adjusted_p_value"] >= row["p_value"] - 1e-12 for row in result["segments"])


def test_data_quality_reports_removed_duplicates_and_invalid_rows():
    frame = generate_demo(n=500)
    duplicate = frame.iloc[[0]].copy()
    invalid = frame.iloc[[1]].copy()
    invalid["variant"] = "mystery"
    bad_metric = frame.iloc[[2]].copy()
    bad_metric["converted"] = None
    dirty = pd.concat([frame, duplicate, invalid, bad_metric], ignore_index=True)
    quality = analyze_dataframe(dirty, "converted", "binary").result["data_quality"]
    assert quality["duplicate_users_removed"] >= 1
    assert quality["invalid_variant_rows_removed"] >= 1
    assert quality["missing_metric_rows_removed"] >= 1
    assert quality["rows_removed"] >= 3


def test_ml_heterogeneity_avoids_obvious_post_treatment_columns():
    result = analyze_dataframe(generate_demo(n=1600), "converted", "binary").result
    used = set(result["ml_heterogeneity"].get("features_used", []))
    assert "revenue" not in used
    assert "session_minutes" not in used
    assert "sessions" not in used


def test_negative_primary_effect_has_low_launch_score():
    frame = generate_demo(n=2000)
    frame["converted"] = 0
    control_mask = frame["variant"] == "control"
    treatment_mask = frame["variant"] == "treatment"
    frame.loc[control_mask, "converted"] = (frame.loc[control_mask, "tenure_days"] % 3 == 0).astype(int)
    frame.loc[treatment_mask, "converted"] = (frame.loc[treatment_mask, "tenure_days"] % 10 == 0).astype(int)
    result = analyze_dataframe(frame, "converted", "binary").result
    assert result["decision"] == "DO NOT SHIP"
    assert result["decision_score"] < 50
