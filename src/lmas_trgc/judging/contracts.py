from __future__ import annotations

from pydantic import BaseModel


class JudgeResult(BaseModel):
    task_id: str
    is_correct: bool
    normalized_answer: str
    score: float
