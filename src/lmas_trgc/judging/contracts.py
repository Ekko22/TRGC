from __future__ import annotations

from pydantic import BaseModel, Field

from lmas_trgc.tasks.schema import TaskPacket


class JudgeResult(BaseModel):
    task_id: str
    is_correct: bool
    normalized_answer: str
    score: float


class JudgeContract(BaseModel):
    metric: str
    expected_answer: str | None = None
    exact_match_required: bool = False
    normalization: str | None = None
    violation_types: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    requires_review: bool = False


def build_judge_contract_from_task_packet(task_packet: TaskPacket) -> JudgeContract:
    answer_contract = task_packet.answer_contract
    safety_contract = task_packet.safety_contract
    return JudgeContract(
        metric=answer_contract.get("metric", "exact_match"),
        expected_answer=answer_contract.get("expected_answer") or task_packet.task.gold_answer,
        exact_match_required=bool(answer_contract.get("exact_match_required", False)),
        normalization=answer_contract.get("normalization"),
        violation_types=list(safety_contract.get("violation_types", [])),
        forbidden_actions=list(safety_contract.get("forbidden_actions", [])),
        forbidden_paths=list(safety_contract.get("forbidden_paths", [])),
        requires_review=bool(safety_contract.get("requires_review", False)),
    )


def determine_metric(task_packet: TaskPacket) -> str:
    return task_packet.answer_contract.get("metric", "exact_match")
