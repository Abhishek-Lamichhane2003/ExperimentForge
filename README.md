# ExperimentForge

ExperimentForge is a full-stack A/B testing and experimentation platform that I built to combine data science, statistics, machine learning, and software engineering in one project.

The main idea is simple: upload experiment data, compare a control group and a treatment group, check whether the result is statistically meaningful, look for risky user segments, and get a final launch recommendation.

I wanted this project to be more than just a notebook, so I built it as a complete application with a backend API, database support, a web interface, automated tests, and an AI-assisted explanation layer.

## What the project does

ExperimentForge can:

- upload and analyze A/B test data
- compare control and treatment groups
- calculate lift and confidence intervals
- run significance tests for binary and continuous metrics
- check sample-ratio mismatch (SRM)
- scan user segments such as device type and country
- apply Benjamini-Hochberg correction when testing multiple segments
- detect unusual observations with anomaly detection
- estimate heterogeneous treatment effects with a T-learner model
- recommend whether an experiment should be shipped, held, or tested longer
- explain experiment results through an AI Copilot / deterministic fallback

## Example

The included demo experiment tests a new recommendation-ranking system.

The overall experiment shows a positive result:

- Control conversion rate: about 12.35%
- Treatment conversion rate: about 14.93%
- Relative lift: about +20.9%
- p-value: about 0.0036

At first this looks like a successful experiment.

However, the segment analysis finds that mobile users have a negative treatment effect of about -2.85 percentage points. After multiple-testing correction, the result is still statistically significant.

Because of that, ExperimentForge recommends **HOLD** instead of immediately shipping the experiment.

This was an important part of the project because it shows how a positive overall result can still hide problems inside specific user groups.

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite
- PostgreSQL-compatible configuration

### Data Science
- pandas
- NumPy
- SciPy
- scikit-learn

### Machine Learning / Statistics
- two-proportion z-test
- Welch's t-test
- confidence intervals
- effect-size calculations
- sample-ratio mismatch checks
- Benjamini-Hochberg correction
- Isolation Forest
- T-learner treatment-effect modeling

### Frontend
- HTML
- CSS
- JavaScript

### Other Tools
- pytest
- GitHub Actions
- Docker
- Ollama support for local AI explanations

## Project Structure

```text
ExperimentForge/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   └── tests/
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── data/
│   └── sample_experiment.csv
├── docs/
├── scripts/
├── requirements.txt
├── run.sh
└── README.md
```

## How to Run

Clone the repository:

```bash
git clone https://github.com/Abhishek-Lamichhane2003/ExperimentForge.git
cd ExperimentForge
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
./run.sh
```

Then open:

```text
http://127.0.0.1:5190
```

## Running the Tests

Install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Then run:

```bash
pytest -q
```

## AI Copilot

The Copilot is designed to explain experiment results instead of calculating them.

The statistical pipeline remains the source of truth. The AI layer only receives already-computed results such as:

- lift
- p-values
- confidence intervals
- significant segments
- launch recommendation

If a local Ollama model is not available, ExperimentForge automatically uses a deterministic fallback so the application can still explain the experiment without failing.

## What I Learned

This project helped me practice both data science and software engineering.

Some of the main things I worked with were:

- designing an end-to-end data pipeline
- validating experiment data
- implementing statistical tests
- handling multiple-comparison problems
- building machine-learning models for treatment-effect exploration
- designing REST APIs with FastAPI
- storing experiment results
- testing backend logic with pytest
- connecting analysis results to a web interface
- thinking about how AI should be used without replacing deterministic statistical logic

## Why I Built This

I wanted a project that was useful for both data science and software engineering roles.

Instead of only training a model or only building a web application, ExperimentForge combines:

- experimentation
- statistics
- machine learning
- backend engineering
- data pipelines
- API development
- frontend development
- AI-assisted explanations

## Future Improvements

Some features I would like to add later are:

- sequential testing
- CUPED variance reduction
- experiment scheduling
- richer dashboards
- experiment comparison
- authentication and multi-user support
- deployment to a cloud platform
- stronger causal-inference methods

## License

This project is licensed under the MIT License.
