# ExperimentForge Architecture

## Goal
ExperimentForge turns raw A/B-test data into a defensible product decision. Statistical calculations remain deterministic; the optional AI layer only explains computed results.

## Request flow

```text
Browser UI
   |
   |  CSV upload / API request
   v
FastAPI application
   |
   +--> ingestion + validation
   |       - required columns
   |       - variant normalization
   |       - deduplication
   |       - missing metric removal
   |
   +--> statistical engine
   |       - SRM chi-square check
   |       - two-proportion z-test
   |       - Welch t-test
   |       - confidence intervals
   |       - effect sizes
   |
   +--> analytics pipeline
   |       - segment scan + BH FDR correction
   |       - Isolation Forest
   |       - T-learner random forests
   |       - pre-treatment feature filtering
   |
   +--> persistence
   |       - SQLAlchemy
   |       - SQLite by default
   |       - PostgreSQL-compatible URL
   |
   +--> Copilot
           - computed JSON only
           - optional Ollama
           - deterministic fallback
```

## Reliability choices
- One application process and one browser port (`5190`).
- No CORS dependency in the default deployment because UI and API share one origin.
- No required Docker, Redis, Kafka, or cloud services.
- AI failure does not break experiment analysis.
- SQLite works out of the box; PostgreSQL is optional.

## Statistical boundaries
The ML heterogeneity model is exploratory. The randomized primary A/B estimate remains the source of truth for the average treatment effect. Segment p-values are adjusted with Benjamini-Hochberg false-discovery-rate correction, but subgroup findings are still investigation signals rather than definitive causal claims. The T-learner should use pre-treatment covariates only; ExperimentForge applies a conservative name-based filter to avoid obvious post-treatment outcome columns, but a real production system would require an explicit feature contract. The SRM check assumes a 50/50 intended assignment.
