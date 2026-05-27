import pytest

from lmas_trgc.core.config import (
    load_dotenv_if_exists,
    load_project_config,
    load_yaml,
    redact_secret,
    resolve_env_value,
)


def test_load_example_configs_without_env_values():
    models = load_yaml("configs/models.example.yaml")
    agents = load_yaml("configs/agents.yaml")
    topologies = load_yaml("configs/topologies.yaml")

    assert "task_models" in models
    assert "safety_verifier" in models
    assert "task_agents" in agents
    assert "topologies" in topologies


def test_load_project_config():
    config = load_project_config("configs")
    assert "models.example.yaml" in config
    assert config["topologies.yaml"]["topologies"]["chain"]["name"] == "chain"


def test_resolve_env_value_default(monkeypatch):
    monkeypatch.delenv("LMAS_TRGC_TEST_MISSING", raising=False)
    assert resolve_env_value("LMAS_TRGC_TEST_MISSING", default="fallback") == "fallback"


def test_load_dotenv_if_exists_does_not_require_dotenv(tmp_path):
    assert load_dotenv_if_exists(tmp_path) is False


def test_redact_secret_never_reveals_value():
    assert redact_secret(None) == "MISSING"
    assert redact_secret("") == "MISSING"
    assert redact_secret("abc") == "SET(length=3)"


def test_resolve_env_value_required(monkeypatch):
    monkeypatch.delenv("LMAS_TRGC_TEST_REQUIRED", raising=False)
    assert resolve_env_value("LMAS_TRGC_TEST_REQUIRED", default="fallback", required=False) == "fallback"
    with pytest.raises(RuntimeError):
        resolve_env_value("LMAS_TRGC_TEST_REQUIRED", required=True)
