from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRoleSpec:
    agent_id: str
    role: str
    model_slot: str
    is_task_agent: bool = True
