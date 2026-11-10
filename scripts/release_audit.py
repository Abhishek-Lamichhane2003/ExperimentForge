from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

required = [
    "backend/app/main.py", "backend/app/services/statistics.py", "backend/app/services/pipeline.py",
    "frontend/index.html", "frontend/app.js", "frontend/styles.css", "data/sample_experiment.csv",
    "README.md", "CHANGELOG.md", "Dockerfile", ".github/workflows/ci.yml",
]
missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")

subprocess.run([sys.executable, "-m", "compileall", "-q", str(ROOT / "backend"), str(ROOT / "scripts")], check=True)
subprocess.run(["node", "--check", str(ROOT / "frontend" / "app.js")], check=True)
subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)

from backend.app.services.demo import generate_demo
from backend.app.services.pipeline import analyze_dataframe
result = analyze_dataframe(generate_demo(), "converted", "binary").result
assert result["primary"]["significant"] is True
assert result["decision"] == "HOLD"
assert result["segment_multiple_testing"] == "Benjamini-Hochberg FDR correction"
mobile = [s for s in result["segments"] if s["feature"] == "device" and s["segment"] == "mobile"]
assert mobile and mobile[0]["significant"] and mobile[0]["effect"] < 0
used = set(result["ml_heterogeneity"].get("features_used", []))
assert not ({"revenue", "session_minutes", "sessions"} & used)
print(json.dumps({
    "status": "PASS",
    "tests": 13,
    "demo_decision": result["decision"],
    "overall_lift_pct": round(result["primary"]["relative_lift_pct"], 2),
    "mobile_effect": round(mobile[0]["effect"], 4),
    "mobile_adjusted_p": round(mobile[0]["adjusted_p_value"], 4),
    "ml_features": sorted(used),
}, indent=2))
