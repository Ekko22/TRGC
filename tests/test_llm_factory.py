import pytest

from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.llm.client import OpenAICompatibleClient
from lmas_trgc.llm.factory import (
    build_deepseek_client_from_registry,
    build_openai_client_from_slot,
    build_safety_verifier_from_registry,
    build_single_model_agent_clients,
    check_deepseek_configuration,
)
from lmas_trgc.llm.registry import build_model_registry


def test_check_deepseek_configuration_reports_missing_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    registry = build_model_registry(require_keys=False)
    assert "M1 api_key" in check_deepseek_configuration(registry)


def test_build_openai_client_requires_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    slot = build_model_registry(require_keys=False).get_task_model("M1")
    with pytest.raises(RuntimeError):
        build_openai_client_from_slot(slot, require_key=True)


def test_build_openai_client_without_key_does_not_request_network(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    slot = build_model_registry(require_keys=False).get_task_model("M1")
    client = build_openai_client_from_slot(slot, require_key=False)
    assert isinstance(client, OpenAICompatibleClient)


def test_build_deepseek_client_without_key_does_not_request_network(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    registry = build_model_registry(require_keys=False)
    client = build_deepseek_client_from_registry(registry, require_key=False)
    assert client.model_name


def test_build_single_model_agent_clients_for_all_task_agents(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = build_deepseek_client_from_registry(build_model_registry(require_keys=False), require_key=False)
    clients = build_single_model_agent_clients(load_agent_profiles(), client)
    assert sorted(clients) == [f"A{idx}" for idx in range(1, 8)]


def test_build_safety_verifier_mock_from_registry():
    verifier = build_safety_verifier_from_registry(build_model_registry(require_keys=False), mode="mock")
    assert isinstance(verifier, SafetyVerifier)
    assert verifier.mode == "mock"
