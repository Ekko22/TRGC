from __future__ import annotations

from pydantic import BaseModel, field_validator


class DatasetSpec(BaseModel):
    name: str
    domain: str
    source_type: str
    default_split: str
    target_main_count: int
    metric: str
    description: str
    local_path: str | None = None
    hf_path: str | None = None
    hf_config: str | None = None

    @field_validator("source_type")
    @classmethod
    def _valid_source_type(cls, value: str) -> str:
        if value not in {"local_jsonl", "hf", "synthetic"}:
            raise ValueError("source_type must be local_jsonl, hf, or synthetic")
        return value


def get_default_dataset_specs() -> dict[str, DatasetSpec]:
    rows = [
        {
            "name": "gsm8k",
            "domain": "math_reasoning",
            "source_type": "hf",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "exact_match",
            "description": "Grade-school math word problems.",
            "local_path": "data/processed/public/gsm8k.jsonl",
            "hf_path": "gsm8k",
            "hf_config": "main",
        },
        {
            "name": "prontoqa",
            "domain": "logic_reasoning",
            "source_type": "local_jsonl",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "accuracy",
            "description": "Logic reasoning tasks stored as local JSONL.",
            "local_path": "data/processed/public/prontoqa.jsonl",
        },
        {
            "name": "mmlu",
            "domain": "knowledge_reasoning",
            "source_type": "hf",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "accuracy",
            "description": "Knowledge reasoning multiple-choice tasks.",
            "local_path": "data/processed/public/mmlu.jsonl",
            "hf_path": "cais/mmlu",
            "hf_config": "all",
        },
        {
            "name": "csqa",
            "domain": "commonsense_reasoning",
            "source_type": "hf",
            "default_split": "validation",
            "target_main_count": 8,
            "metric": "accuracy",
            "description": "CommonsenseQA multiple-choice tasks.",
            "local_path": "data/processed/public/csqa.jsonl",
            "hf_path": "commonsense_qa",
        },
        {
            "name": "svamp",
            "domain": "math_reasoning",
            "source_type": "local_jsonl",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "exact_match",
            "description": "SVAMP math reasoning tasks stored as local JSONL.",
            "local_path": "data/processed/public/svamp.jsonl",
        },
        {
            "name": "multiarith",
            "domain": "math_reasoning",
            "source_type": "local_jsonl",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "exact_match",
            "description": "MultiArith math reasoning tasks stored as local JSONL.",
            "local_path": "data/processed/public/multiarith.jsonl",
        },
        {
            "name": "aqua",
            "domain": "math_reasoning",
            "source_type": "hf",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "accuracy",
            "description": "AQuA rationales and answer selection tasks.",
            "local_path": "data/processed/public/aqua.jsonl",
            "hf_path": "aqua_rat",
        },
        {
            "name": "humaneval",
            "domain": "code",
            "source_type": "hf",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "pass_at_1_or_review_accuracy",
            "description": "HumanEval code generation tasks.",
            "local_path": "data/processed/public/humaneval.jsonl",
            "hf_path": "openai_humaneval",
        },
        {
            "name": "mbpp",
            "domain": "code",
            "source_type": "hf",
            "default_split": "test",
            "target_main_count": 8,
            "metric": "pass_at_1_or_review_accuracy",
            "description": "MBPP code generation tasks.",
            "local_path": "data/processed/public/mbpp.jsonl",
            "hf_path": "mbpp",
        },
        {
            "name": "constraint_miniset",
            "domain": "constraints",
            "source_type": "synthetic",
            "default_split": "test",
            "target_main_count": 16,
            "metric": "task_success_and_safety",
            "description": "Local synthetic constraint-following tasks.",
            "local_path": "data/processed/synthetic/constraint_miniset.jsonl",
        },
        {
            "name": "local_mas_safety",
            "domain": "local_mas_safety",
            "source_type": "synthetic",
            "default_split": "test",
            "target_main_count": 16,
            "metric": "task_success_and_safety",
            "description": "Local multi-agent safety scenarios independent of any specific product.",
            "local_path": "data/processed/synthetic/local_mas_safety.jsonl",
        },
    ]
    return {row["name"]: DatasetSpec(**row) for row in rows}


def get_dataset_spec(name: str) -> DatasetSpec:
    specs = get_default_dataset_specs()
    if name not in specs:
        raise KeyError(f"Unknown dataset: {name}")
    return specs[name]


def list_dataset_names() -> list[str]:
    return list(get_default_dataset_specs())


def total_target_main_count() -> int:
    return sum(spec.target_main_count for spec in get_default_dataset_specs().values())
