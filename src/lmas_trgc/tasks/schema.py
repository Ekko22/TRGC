from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_DOMAINS = {
    "math_reasoning",
    "logic_reasoning",
    "knowledge_reasoning",
    "commonsense_reasoning",
    "code",
    "constraints",
    "local_mas_safety",
}

VALID_DATASETS = {
    "gsm8k",
    "prontoqa",
    "mmlu",
    "csqa",
    "svamp",
    "multiarith",
    "aqua",
    "humaneval",
    "mbpp",
    "constraint_miniset",
    "local_mas_safety",
}

VALID_ANCHOR_TYPES = {
    "numeric",
    "entity",
    "constraint",
    "permission",
    "forbidden_action",
    "allowed_action",
    "code_spec",
    "logic_rule",
    "expected_answer",
    "safety_requirement",
}


class TaskRecord(BaseModel):
    task_id: str
    dataset: str
    domain: str
    split: str
    prompt: str
    gold_answer: str | None = None
    choices: list[str] = Field(default_factory=list)
    source: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("task_id", "dataset", "domain", "split", "prompt")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("domain")
    @classmethod
    def _valid_domain(cls, value: str) -> str:
        if value not in VALID_DOMAINS:
            raise ValueError(f"domain must be one of {sorted(VALID_DOMAINS)}")
        return value

    @field_validator("dataset")
    @classmethod
    def _valid_dataset(cls, value: str) -> str:
        if value not in VALID_DATASETS:
            raise ValueError(f"dataset must be one of {sorted(VALID_DATASETS)}")
        return value


class TaskAnchor(BaseModel):
    anchor_id: str
    task_id: str
    key: str
    value: str
    anchor_type: str
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: str = "auto"

    @field_validator("anchor_id", "task_id", "key", "value", "anchor_type")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("anchor_type")
    @classmethod
    def _valid_anchor_type(cls, value: str) -> str:
        if value not in VALID_ANCHOR_TYPES:
            raise ValueError(f"anchor_type must be one of {sorted(VALID_ANCHOR_TYPES)}")
        return value


class TaskPacket(BaseModel):
    task: TaskRecord
    anchors: list[TaskAnchor] = Field(default_factory=list)
    answer_contract: dict
    safety_contract: dict
    attack_surface: dict

    @model_validator(mode="after")
    def _required_contract_keys(self) -> "TaskPacket":
        if "metric" not in self.answer_contract:
            raise ValueError("answer_contract must contain metric")
        if "violation_types" not in self.safety_contract:
            raise ValueError("safety_contract must contain violation_types")
        if "target_slots" not in self.attack_surface:
            raise ValueError("attack_surface must contain target_slots")
        return self


class TaskManifestEntry(BaseModel):
    manifest_id: str
    task_id: str
    dataset: str
    domain: str
    split: str
    selected: bool = True
    selection_reason: str | None = None
    original_index: int | None = None
    metadata: dict = Field(default_factory=dict)
