# Changelog

## 1.1.0 — Final audited portfolio release

- Added Benjamini-Hochberg FDR correction for exploratory segment scans.
- Added adjusted segment p-values to the dashboard and launch decision logic.
- Fixed data-quality accounting so removed duplicates, invalid variants, missing metrics, and total removed rows are reported correctly.
- Added a conservative pre-treatment feature filter for the exploratory T-learner to reduce obvious post-treatment leakage.
- Reworked launch scoring so significantly harmful experiments do not receive a misleadingly high score.
- Hardened continuous-metric inference against constant/non-finite inputs.
- Hardened static file serving against path traversal outside the frontend directory.
- Improved deterministic Copilot answers for launch, segment, SRM, and sample-size questions.
- Added anomaly-scan results and adjusted-p-value labeling to the UI.
- Added responsive UI behavior for tablet/mobile widths.
- Expanded automated coverage to 13 tests.
