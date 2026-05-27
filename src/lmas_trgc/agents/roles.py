from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, field_validator

from lmas_trgc.core.config import load_config_file, load_yaml


@dataclass(frozen=True)
class AgentRoleSpec:
    agent_id: str
    role: str
    model_slot: str
    is_task_agent: bool = True


class AgentProfile(BaseModel):
    agent_id: str
    role_name: str
    model_slot: str
    is_task_agent: bool = True
    description: str = ""

    @field_validator("agent_id", "role_name", "model_slot")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value


def _load_agents(config_path: Path | None = None) -> dict:
    return load_yaml(config_path) if config_path else load_config_file("agents.yaml")


def load_agent_profiles(config_path: Path | None = None) -> dict[str, AgentProfile]:
    raw = _load_agents(config_path)
    task_agents = raw.get("task_agents", {})
    profiles = {
        agent_id: AgentProfile(
            agent_id=agent_id,
            role_name=spec["role"],
            model_slot=spec["model_slot"],
            is_task_agent=bool(spec.get("is_task_agent", True)),
            description=spec.get("description", ""),
        )
        for agent_id, spec in task_agents.items()
        if bool(spec.get("is_task_agent", True))
    }
    required = [f"A{idx}" for idx in range(1, 8)]
    missing = [agent_id for agent_id in required if agent_id not in profiles]
    if missing:
        raise ValueError(f"Missing required task agent profiles: {', '.join(missing)}")
    if "SV" in profiles:
        raise ValueError("SV must not be returned as a task agent profile")
    return {agent_id: profiles[agent_id] for agent_id in required}


def load_safety_verifier_profile(config_path: Path | None = None) -> AgentProfile:
    raw = _load_agents(config_path)
    spec = raw.get("safety_verifier")
    if not isinstance(spec, dict):
        raise ValueError("agents config must contain safety_verifier")
    profile = AgentProfile(
        agent_id=spec.get("id", "SV"),
        role_name=spec["role"],
        model_slot=spec["model_slot"],
        is_task_agent=bool(spec.get("is_task_agent", False)),
        description=spec.get("description", ""),
    )
    if profile.is_task_agent:
        raise ValueError("Safety verifier profile must have is_task_agent=False")
    return profile


def get_agent_profile(agent_id: str, profiles: dict[str, AgentProfile]) -> AgentProfile:
    if agent_id not in profiles:
        raise KeyError(f"Unknown agent profile: {agent_id}")
    return profiles[agent_id]
