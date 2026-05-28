from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


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
    hf_split: str | None = None
    primary_hf_path: str | None = None
    primary_hf_config: str | None = None
    primary_hf_split: str | None = None
    hf_candidates: list[dict[str, str | None]] = Field(default_factory=list)
    local_raw_candidates: list[str] = Field(default_factory=list)
    processed_path: str | None = None
    download_supported: bool = True
    requires_local_raw: bool = False

    @field_validator("source_type")
    @classmethod
    def _valid_source_type(cls, value: str) -> str:
        valid = {"local_jsonl", "local_jsonl_or_hf_candidates", "hf", "hf_or_local", "synthetic"}
        if value not in valid:
            allowed = ", ".join(sorted(valid))
            raise ValueError(f"source_type must be one of: {allowed}")
        return value

    @field_validator("hf_candidates", mode="before")
    @classmethod
    def _normalize_hf_candidates(cls, value: object) -> list[dict[str, str | None]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("hf_candidates must be a list")
        candidates: list[dict[str, str | None]] = []
        for item in value:
            if isinstance(item, str):
                candidates.append({"path": item, "config": None, "split": None})
                continue
            if isinstance(item, dict):
                path = item.get("path")
                if not path:
                    raise ValueError("hf candidate entries must include path")
                candidates.append(
                    {
                        "path": str(path),
                        "config": None if item.get("config") in {"", None} else str(item.get("config")),
                        "split": None if item.get("split") in {"", None} else str(item.get("split")),
                    }
                )
                continue
            raise ValueError("hf_candidates entries must be strings or mappings")
        return candidates

    @field_validator("local_raw_candidates", mode="before")
    @classmethod
    def _normalize_raw_candidates(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("local_raw_candidates must be a list")
        return [str(item) for item in value if str(item)]

    @model_validator(mode="after")
    def _fill_compat_fields(self) -> DatasetSpec:
        if self.processed_path and not self.local_path:
            self.local_path = self.processed_path
        if self.local_path and not self.processed_path:
            self.processed_path = self.local_path
        if self.hf_path and not self.primary_hf_path:
            self.primary_hf_path = self.hf_path
        if self.primary_hf_path and not self.hf_path:
            self.hf_path = self.primary_hf_path
        if self.hf_config and not self.primary_hf_config:
            self.primary_hf_config = self.hf_config
        if self.primary_hf_config and not self.hf_config:
            self.hf_config = self.primary_hf_config
        if self.hf_split and not self.primary_hf_split:
            self.primary_hf_split = self.hf_split
        if self.primary_hf_split and not self.hf_split:
            self.hf_split = self.primary_hf_split
        if self.primary_hf_path and not self.hf_candidates:
            self.hf_candidates = [
                {
                    "path": self.primary_hf_path,
                    "config": self.primary_hf_config,
                    "split": self.primary_hf_split or self.default_split,
                }
            ]
        return self


_DATASET_ORDER = [
    "gsm8k",
    "mmlu",
    "csqa",
    "svamp",
    "multiarith",
    "aqua",
    "humaneval",
    "mbpp",
    "constraint_miniset",
    "local_mas_safety",
]


def _project_root_from_module() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_dataset_rows_from_yaml(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    datasets = raw.get("datasets")
    if not isinstance(datasets, dict):
        raise ValueError(f"datasets.yaml must contain a top-level datasets mapping: {config_path}")
    return datasets


def _fallback_dataset_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for name in _DATASET_ORDER:
        if name == "constraint_miniset":
            rows[name] = {
                "name": name,
                "domain": "constraints",
                "source_type": "synthetic",
                "default_split": "test",
                "target_main_count": 16,
                "metric": "task_success_and_safety",
                "description": "Local synthetic constraint-following tasks.",
                "local_path": "data/processed/synthetic/constraint_miniset.jsonl",
                "processed_path": "data/processed/synthetic/constraint_miniset.jsonl",
                "download_supported": False,
            }
        elif name == "local_mas_safety":
            rows[name] = {
                "name": name,
                "domain": "local_mas_safety",
                "source_type": "synthetic",
                "default_split": "test",
                "target_main_count": 16,
                "metric": "task_success_and_safety",
                "description": "Local multi-agent safety scenarios.",
                "local_path": "data/processed/synthetic/local_mas_safety.jsonl",
                "processed_path": "data/processed/synthetic/local_mas_safety.jsonl",
                "download_supported": False,
            }
        else:
            rows[name] = {
                "name": name,
                "domain": {
                    "gsm8k": "math_reasoning",
                    "mmlu": "knowledge_reasoning",
                    "csqa": "commonsense_reasoning",
                    "svamp": "math_reasoning",
                    "multiarith": "math_reasoning",
                    "aqua": "math_reasoning",
                    "humaneval": "code",
                    "mbpp": "code",
                }[name],
                "source_type": "hf_or_local" if name in {"svamp", "multiarith"} else "hf",
                "default_split": "validation" if name == "csqa" else "test",
                "target_main_count": 8,
                "metric": {
                    "gsm8k": "exact_match",
                    "mmlu": "accuracy",
                    "csqa": "accuracy",
                    "svamp": "exact_match",
                    "multiarith": "exact_match",
                    "aqua": "accuracy",
                    "humaneval": "pass_at_1_or_review_accuracy",
                    "mbpp": "pass_at_1_or_review_accuracy",
                }[name],
                "description": f"{name} public dataset.",
                "local_path": f"data/processed/public/{name}.jsonl",
                "processed_path": f"data/processed/public/{name}.jsonl",
                "local_raw_candidates": [f"data/raw/public/{name}.jsonl", f"data/raw/public/{name}.json"],
                "hf_candidates": [],
            }
    return rows


def load_dataset_specs(config_path: Path | None = None) -> dict[str, DatasetSpec]:
    path = config_path or (_project_root_from_module() / "configs" / "datasets.yaml")
    try:
        rows = _load_dataset_rows_from_yaml(path)
    except FileNotFoundError:
        rows = _fallback_dataset_rows()
    specs = {name: DatasetSpec(**row) for name, row in rows.items()}
    missing = [name for name in _DATASET_ORDER if name not in specs]
    if missing:
        raise ValueError(f"datasets config is missing required datasets: {missing}")
    return {name: specs[name] for name in _DATASET_ORDER}


def get_default_dataset_specs() -> dict[str, DatasetSpec]:
    return load_dataset_specs()


def get_dataset_spec(name: str) -> DatasetSpec:
    specs = get_default_dataset_specs()
    if name not in specs:
        raise KeyError(f"Unknown dataset: {name}")
    return specs[name]


def list_dataset_names() -> list[str]:
    return list(get_default_dataset_specs())


def total_target_main_count() -> int:
    return sum(spec.target_main_count for spec in get_default_dataset_specs().values())
