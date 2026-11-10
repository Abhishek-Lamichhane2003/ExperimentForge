from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ExperimentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    metric_column: str
    metric_type: str
    sample_size: int
    decision: str
    status: str
    created_at: datetime

class ExperimentDetail(ExperimentSummary):
    result: dict[str, Any]

class CopilotRequest(BaseModel):
    experiment_id: str
    question: str = Field(min_length=3, max_length=500)

class CopilotResponse(BaseModel):
    mode: str
    answer: str
