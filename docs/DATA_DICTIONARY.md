# CSV Data Contract

Required:
- `variant`: `control` or `treatment` (also accepts `A`/`B`).
- primary metric column selected in the UI.

Recommended:
- `user_id`: unique experiment unit. If absent, row IDs are generated.

Useful optional columns:
- `device`, `country`, `plan`: categorical features used in segment analysis.
- `tenure_days`, `age`, `prior_sessions`: pre-treatment numeric features that can be used by anomaly detection / ML.
- Post-treatment outcome-like columns such as `revenue`, `converted`, `session_minutes`, or `clicks` are not appropriate covariates for treatment-effect modeling.

Binary metrics must contain only `0` and `1` after missing values are removed.
Continuous metrics must be numeric.

For the included demo file, use:
- metric column: `converted`
- metric type: `binary`
