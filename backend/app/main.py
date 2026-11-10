from __future__ import annotations
import io
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import STATIC_DIR
from .database import Base, engine, get_db
from .models import Experiment
from .schemas import CopilotRequest, CopilotResponse, ExperimentDetail, ExperimentSummary
from .services.copilot import answer_question
from .services.demo import generate_demo
from .services.pipeline import analyze_dataframe
from .services.statistics import AnalysisError

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="ExperimentForge", version="1.1.0", lifespan=lifespan)


def _detail(row: Experiment) -> ExperimentDetail:
    return ExperimentDetail(
        id=row.id,
        name=row.name,
        metric_column=row.metric_column,
        metric_type=row.metric_type,
        sample_size=row.sample_size,
        decision=row.decision,
        status=row.status,
        created_at=row.created_at,
        result=json.loads(row.result_json),
    )


def _persist(db: Session, *, name: str, metric: str, metric_type: str, result: dict, sample_size: int) -> Experiment:
    row = Experiment(
        id=str(uuid.uuid4()),
        name=name.strip()[:160] or "Untitled experiment",
        metric_column=metric,
        metric_type=metric_type,
        sample_size=sample_size,
        decision=result["decision"],
        status="completed",
        result_json=json.dumps(result),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ExperimentForge"}

@app.get("/api/experiments", response_model=list[ExperimentSummary])
def list_experiments(db: Session = Depends(get_db)):
    rows = db.scalars(select(Experiment).order_by(Experiment.created_at.desc())).all()
    return rows

@app.get("/api/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    row = db.get(Experiment, experiment_id)
    if not row:
        raise HTTPException(404, "Experiment not found")
    return _detail(row)

@app.delete("/api/experiments/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    row = db.get(Experiment, experiment_id)
    if not row:
        raise HTTPException(404, "Experiment not found")
    db.delete(row)
    db.commit()

@app.post("/api/experiments/analyze", response_model=ExperimentDetail)
async def analyze_upload(
    name: str = Form(...),
    metric_column: str = Form(...),
    metric_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a CSV file.")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "CSV is larger than 15 MB.")
    try:
        frame = pd.read_csv(io.BytesIO(data))
        output = analyze_dataframe(frame, metric_column.strip(), metric_type.strip().lower())
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "The uploaded file is not a readable CSV.") from exc
    except AnalysisError as exc:
        raise HTTPException(422, str(exc)) from exc
    row = _persist(db, name=name, metric=metric_column.strip(), metric_type=metric_type.strip().lower(), result=output.result, sample_size=len(output.cleaned))
    return _detail(row)

@app.post("/api/demo", response_model=ExperimentDetail)
def create_demo(db: Session = Depends(get_db)):
    frame = generate_demo()
    output = analyze_dataframe(frame, "converted", "binary")
    row = _persist(db, name="Recommendation Ranking Experiment", metric="converted", metric_type="binary", result=output.result, sample_size=len(output.cleaned))
    return _detail(row)

@app.post("/api/copilot", response_model=CopilotResponse)
async def copilot(request: CopilotRequest, db: Session = Depends(get_db)):
    row = db.get(Experiment, request.experiment_id)
    if not row:
        raise HTTPException(404, "Experiment not found")
    mode, answer = await answer_question(json.loads(row.result_json), request.question)
    return CopilotResponse(mode=mode, answer=answer)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

@app.get("/{path:path}")
def spa(path: str):
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(503, "Frontend files are missing from the release package.")

    static_root = STATIC_DIR.resolve()
    requested = (STATIC_DIR / path).resolve()
    try:
        requested.relative_to(static_root)
    except ValueError:
        raise HTTPException(404, "File not found")

    if path and requested.exists() and requested.is_file():
        return FileResponse(requested)
    return FileResponse(index)
