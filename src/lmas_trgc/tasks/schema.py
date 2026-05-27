from __future__ import annotations

from pydantic import BaseModel, Field


class TaskRecord(BaseModel):
    task_id: str
    dataset: str
    prompt: str
    answer: str | None = None
    metadata: dict = Field(default_factory=dict)
