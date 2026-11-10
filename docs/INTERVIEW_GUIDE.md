# Interview Guide

## 30-second explanation
ExperimentForge is a full-stack experimentation platform. A user uploads A/B-test data, the backend validates assignment quality, runs the correct statistical test for binary or continuous outcomes, scans user segments, uses ML to explore heterogeneous treatment effects, stores results, and gives an AI copilot a read-only structured summary so it can explain the evidence without inventing the statistics.

## Questions you should be ready for

### Why not let the LLM calculate p-values?
Because language models are not a deterministic numerical inference engine. The statistical layer computes the result; AI only translates verified outputs into product language.

### What is sample-ratio mismatch?
A check for unexpected imbalance in control/treatment assignment. A strong mismatch can indicate broken randomization, logging, or eligibility logic and can invalidate interpretation.

### Why Welch's t-test?
It does not assume equal variance between control and treatment, making it a safer default for continuous product metrics.

### What does the T-learner do?
It fits one outcome model to control users and another to treatment users. The difference between their predictions is used as an exploratory estimate of how treatment effect may vary across users.

### Is the ML model causal proof?
No. The primary randomized comparison is the causal anchor. The T-learner is used to generate segment hypotheses and investigate heterogeneity.

### How do you avoid false-positive subgroup findings?
The segment scan applies Benjamini-Hochberg false-discovery-rate correction across the tested subgroup p-values. I still treat those results as exploratory because subgroup analyses can be unstable and should be validated with follow-up experiments.

### How do you avoid leakage in the treatment-effect model?
The T-learner should only use pre-treatment covariates. This portfolio version filters out columns whose names look like outcomes or post-treatment behavior, such as revenue, conversion, sessions, or clicks. In a production system I would use an explicit feature contract rather than relying on name heuristics.

### Why SQLite?
It makes the project run immediately for reviewers. SQLAlchemy keeps the persistence layer portable, and a PostgreSQL URL can be supplied for a production-style deployment.

### Biggest engineering tradeoff
I intentionally used a one-service architecture so the portfolio project is easy to run and reliable. The analytics code is split into services, so it can later move to background workers if analysis volume grows.
