# ExperimentForge — AI Experimentation & Decision Intelligence

**Release:** 1.1.0 — final audited portfolio build

ExperimentForge is a full-stack A/B-testing platform built for a Data Science + Software Engineering portfolio. It ingests experiment data, validates experiment health, runs deterministic statistical inference, explores treatment-effect heterogeneity with machine learning, persists results, and uses an optional AI copilot to explain the evidence.

**Design principle:** **Math decides. AI explains.**

## What it demonstrates

### Data Science
- A/B testing and hypothesis testing
- two-proportion z-tests for binary metrics
- Welch's t-tests for continuous metrics
- confidence intervals and effect sizes
- sample-ratio mismatch detection
- segment-level treatment analysis with Benjamini-Hochberg FDR correction
- Isolation Forest anomaly detection
- random-forest T-learner for exploratory heterogeneous effects using plausible pre-treatment covariates
- pandas / NumPy / SciPy / scikit-learn

### Software Engineering
- FastAPI REST API
- SQLAlchemy persistence
- file-upload validation and defensive error handling
- service-layer architecture
- responsive product UI
- API tests + analytics unit tests
- GitHub Actions CI
- optional Docker deployment
- configuration through environment variables

### AI
- optional Ollama integration
- grounded prompts using computed JSON results only
- deterministic fallback when no model is available
- AI never computes significance or overrides launch status

## Fastest way to run it on macOS

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5190
```

Then open:

```text
http://localhost:5190
```

There is **no npm install, frontend build, CORS setup, PostgreSQL server, or Docker requirement** for the default path.

You can also run:

```bash
./run.sh
```

## First demo

1. Open `http://localhost:5190`.
2. Click **Load demo**.
3. Inspect the primary metric, SRM check, segment scan, ML heterogeneity panel, and pipeline stages.
4. Open **AI Copilot** and ask whether the experiment should ship.
5. Upload `data/sample_experiment.csv` to test CSV ingestion yourself.

For the sample CSV, choose:

```text
Metric column: converted
Metric type: Binary (0/1)
```

## Optional Ollama

ExperimentForge works without AI infrastructure. For a real local LLM response, install/run Ollama separately and set:

```bash
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=qwen2.5-coder:7b
```

If Ollama is unavailable, Copilot automatically falls back to a deterministic explanation derived from computed results.

## Tests

The final release includes 13 automated backend/API/statistical checks, including path-traversal protection, multiple-testing correction, data-cleaning accounting, and ML feature-leakage safeguards.


```bash
pip install -r requirements-dev.txt
pytest
node --check frontend/app.js
```

## Docker (optional)

```bash
docker build -t experimentforge .
docker run --rm -p 5190:5190 experimentforge
```

Open `http://localhost:5190`.

## Project structure

```text
ExperimentForge/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── services/
│   │       ├── statistics.py
│   │       ├── pipeline.py
│   │       ├── copilot.py
│   │       └── demo.py
│   └── tests/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/
│   └── sample_experiment.csv
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   └── INTERVIEW_GUIDE.md
├── .github/workflows/ci.yml
├── Dockerfile
├── requirements.txt
└── run.sh
```

## Important statistical caveats

The randomized primary comparison remains the main causal launch signal. Segment scans apply Benjamini-Hochberg false-discovery-rate correction, but subgroup findings are still exploratory and should motivate follow-up analysis or experiments. The ML T-learner uses a heuristic filter to avoid obvious post-treatment/outcome-like columns; for real experiments, only pre-treatment covariates should be supplied to a treatment-effect model. The built-in SRM check assumes an intended 50/50 allocation.

## Resume-ready framing (after you personally run and understand it)

**ExperimentForge — AI Experimentation & Decision Intelligence Platform**
- Built a full-stack A/B-testing platform with Python, FastAPI, SQLAlchemy, SciPy, and scikit-learn to ingest experiment data, validate randomization, compute statistical significance and confidence intervals, and persist launch decisions.
- Implemented segment analysis, Isolation Forest anomaly detection, and a random-forest T-learner to surface heterogeneous treatment effects and product-risk signals across user cohorts.
- Added a grounded AI copilot that explains deterministic experiment results and suggests follow-up investigations without allowing the language model to alter statistical conclusions.

See `docs/INTERVIEW_GUIDE.md` before using the project in interviews.
