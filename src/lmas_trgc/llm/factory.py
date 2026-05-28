from __future__ import annotations

import os

from lmas_trgc.agents.roles import AgentProfile
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.llm.registry import ModelRegistry, ModelSlotConfig


def _api_key_for_slot(slot: ModelSlotConfig, require_key: bool) -> str | None:
    api_key = os.environ.get(slot.api_key_env) if slot.api_key_env else None
    if require_key and not api_key:
        raise RuntimeError(f"Missing API key for model slot {slot.slot_id}: env {slot.api_key_env}")
    return api_key


def build_openai_client_from_slot(slot: ModelSlotConfig, require_key: bool = True) -> OpenAICompatibleClient:
    if not slot.base_url:
        raise RuntimeError(f"Model slot {slot.slot_id} is missing base_url")
    if not slot.model_name:
        raise RuntimeError(f"Model slot {slot.slot_id} is missing model_name")
    api_key = _api_key_for_slot(slot, require_key=require_key)
    return OpenAICompatibleClient(model_name=slot.model_name, base_url=slot.base_url, api_key=api_key)


def build_deepseek_client_from_registry(
    registry: ModelRegistry,
    require_key: bool = True,
) -> OpenAICompatibleClient:
    slot = registry.get_task_model("M1")
    return build_openai_client_from_slot(slot, require_key=require_key)


def build_single_model_agent_clients(
    agent_profiles: dict[str, AgentProfile],
    client: OpenAICompatibleClient,
) -> dict[str, OpenAICompatibleClient]:
    clients: dict[str, OpenAICompatibleClient] = {}
    for agent_id, profile in agent_profiles.items():
        if agent_id == "SV" or not profile.is_task_agent:
            continue
        clients[agent_id] = client
    required = [f"A{idx}" for idx in range(1, 8)]
    missing = [agent_id for agent_id in required if agent_id not in clients]
    if missing:
        raise ValueError(f"Missing task agent clients for: {', '.join(missing)}")
    return {agent_id: clients[agent_id] for agent_id in required}


def build_agent_clients_from_profiles(
    agent_profiles: dict[str, AgentProfile],
    registry: ModelRegistry,
    require_keys: bool = True,
) -> dict[str, OpenAICompatibleClient]:
    clients_by_slot: dict[str, OpenAICompatibleClient] = {}
    clients_by_agent: dict[str, OpenAICompatibleClient] = {}
    for agent_id, profile in agent_profiles.items():
        if agent_id == "SV" or not profile.is_task_agent:
            continue
        slot = registry.get_task_model(profile.model_slot)
        if profile.model_slot not in clients_by_slot:
            clients_by_slot[profile.model_slot] = build_openai_client_from_slot(slot, require_key=require_keys)
        clients_by_agent[agent_id] = clients_by_slot[profile.model_slot]
    required = [f"A{idx}" for idx in range(1, 8)]
    missing = [agent_id for agent_id in required if agent_id not in clients_by_agent]
    if missing:
        raise ValueError(f"Missing task agent clients for: {', '.join(missing)}")
    return {agent_id: clients_by_agent[agent_id] for agent_id in required}


def build_safety_verifier_from_registry(
    registry: ModelRegistry,
    require_key: bool = True,
    mode: str = "client",
) -> SafetyVerifier:
    if mode == "mock":
        return SafetyVerifier(mode="mock", client=MockLLMClient(model_name="mock-sv"))
    if mode != "client":
        raise ValueError("SV mode must be mock or client")
    slot = registry.get_safety_verifier()
    client = build_openai_client_from_slot(slot, require_key=require_key)
    return SafetyVerifier(mode="client", client=client, model_name=slot.model_name)


def check_deepseek_configuration(registry: ModelRegistry, require_sv: bool = False) -> list[str]:
    missing: list[str] = []
    m1 = registry.get_task_model("M1")
    if not m1.model_name:
        missing.append("M1 model_name")
    if not m1.base_url:
        missing.append("M1 base_url")
    if not m1.api_key_set:
        missing.append("M1 api_key")
    if require_sv:
        sv = registry.get_safety_verifier()
        if not sv.model_name:
            missing.append("SV model_name")
        if not sv.base_url:
            missing.append("SV base_url")
        if not sv.api_key_set:
            missing.append("SV api_key")
    return missing
