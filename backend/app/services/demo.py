from __future__ import annotations
import numpy as np
import pandas as pd

def generate_demo(seed: int = 42, n: int = 6000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    variant = rng.choice(["control", "treatment"], size=n)
    device = rng.choice(["desktop", "mobile", "tablet"], size=n, p=[0.42, 0.48, 0.10])
    country = rng.choice(["US", "CA", "UK", "AU"], size=n, p=[0.55, 0.15, 0.2, 0.1])
    tenure = rng.integers(1, 900, size=n)
    sessions = np.maximum(1, rng.poisson(4.5, size=n))
    base = 0.115 + 0.02 * (tenure > 365) + 0.015 * (device == "desktop")
    treatment_effect = np.where(device == "desktop", 0.06, np.where(device == "mobile", -0.04, 0.03))
    prob = np.clip(base + (variant == "treatment") * treatment_effect, 0.02, 0.55)
    converted = rng.binomial(1, prob)
    session_minutes = rng.gamma(shape=2.8, scale=5.8, size=n) + (variant == "treatment") * np.where(device == "desktop", 1.8, 0.3)
    revenue = converted * np.maximum(0, rng.normal(52, 15, size=n))
    return pd.DataFrame({
        "user_id": [f"u_{i:05d}" for i in range(n)],
        "variant": variant,
        "converted": converted,
        "session_minutes": np.round(session_minutes, 2),
        "revenue": np.round(revenue, 2),
        "device": device,
        "country": country,
        "tenure_days": tenure,
        "sessions": sessions,
    })
