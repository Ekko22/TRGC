from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from lmas_trgc.core.config import load_config_file, load_yaml, resolve_env_value


class ModelSlotConfig(BaseModel):
    slot_id: str
    model_name: str
    provider: str
    base_url: str
    api_key_env: str
    api_key_set: bool
    temperature: float = 0
    top_p: float = 1
    max_output_tokens: int | None = None
    response_format: str | None = None
    is_task_agent: bool = True

    @field_validator("slot_id", "provider")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_slot_shape(self) -> "ModelSlotConfig":
        if self.slot_id == "SV" and self.is_task_agent:
            raise ValueError("safety_verifier must have is_task_agent=False")
        if self.is_task_agent and self.slot_id not in {"M1", "M2", "M3", "M4"}:
            raise ValueError(
                f"Task model slot {self.slot_id!r} is outside the current M1/M2/M3/M4 design; "
                "extend the registry deliberately before using it."
            )
        return self


class ModelRegistry(BaseModel):
    task_models: dict[str, ModelSlotConfig]
    safety_verifier: ModelSlotConfig

    def get_task_model(self, slot_id: str) -> ModelSlotConfig:
        if slot_id not in self.task_models:
            raise KeyError(f"Unknown task model slot: {slot_id}")
        return self.task_models[slot_id]

    def get_safety_verifier(self) -> ModelSlotConfig:
        return self.safety_verifier

    def list_task_model_slots(self) -> list[str]:
        return sorted(self.task_models)

    def validate_required_slots(self, required_slots: list[str]) -> None:
        missing = [slot for slot in required_slots if slot not in self.task_models]
        if missing:
            raise RuntimeError(f"Missing required task model slots: {', '.join(missing)}")

    def to_safe_dict(self) -> dict:
        return {
            "task_models": {slot: config.model_dump() for slot, config in self.task_models.items()},
            "safety_verifier": self.safety_verifier.model_dump(),
        }


def _resolve_slot(slot_id: str, raw: dict, *, is_task_agent: bool) -> ModelSlotConfig:
    model_name = resolve_env_value(raw.get("model_name_env"), raw.get("default_model_name") or "") or ""
    base_url = resolve_env_value(raw.get("base_url_env"), raw.get("default_base_url") or "") or ""
    api_key_env = raw.get("api_key_env") or ""
    api_key_set = bool(api_key_env and os.environ.get(api_key_env))
    return ModelSlotConfig(
        slot_id=slot_id,
        model_name=model_name,
        provider=raw.get("provider") or "",
        base_url=base_url,
        api_key_env=api_key_env,
        api_key_set=api_key_set,
        temperature=raw.get("temperature", 0),
        top_p=raw.get("top_p", 1),
        max_output_tokens=raw.get("max_output_tokens"),
        response_format=raw.get("response_format"),
        is_task_agent=is_task_agent,
    )


def build_model_registry(
    models_config_path: Path | None = None,
    require_keys: bool = False,
) -> ModelRegistry:
    raw = load_yaml(models_config_path) if models_config_path else load_config_file("models.example.yaml")
    task_raw = raw.get("task_models")
    sv_raw = raw.get("safety_verifier")
    if not isinstance(task_raw, dict):
        raise RuntimeError("models config must contain task_models mapping")
    if not isinstance(sv_raw, dict):
        raise RuntimeError("models config must contain safety_verifier mapping")

    task_models = {
        slot_id: _resolve_slot(slot_id, spec, is_task_agent=True)
        for slot_id, spec in task_raw.items()
    }
    missing_slots = [slot for slot in ["M1", "M2", "M3", "M4"] if slot not in task_models]
    if missing_slots:
        raise RuntimeError(f"models config missing required task model slots: {', '.join(missing_slots)}")

    sv_slot_id = sv_raw.get("id") or "SV"
    safety_verifier = _resolve_slot(sv_slot_id, sv_raw, is_task_agent=bool(sv_raw.get("is_task_agent", False)))
    if safety_verifier.is_task_agent:
        raise RuntimeError("safety_verifier must have is_task_agent=False")

    registry = ModelRegistry(task_models=task_models, safety_verifier=safety_verifier)
    if require_keys:
        missing_keys = [
            config.slot_id
            for config in [*registry.task_models.values(), registry.safety_verifier]
            if not config.api_key_set
        ]
        if missing_keys:
            raise RuntimeError(f"Missing API keys for model slots: {', '.join(missing_keys)}")
    return registry
