from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.demo import generate_demo

out = ROOT / "data" / "sample_experiment.csv"
out.parent.mkdir(parents=True, exist_ok=True)
generate_demo().to_csv(out, index=False)
print(f"Wrote {out}")
