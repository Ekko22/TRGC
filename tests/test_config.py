from lmas_trgc.core.config import load_project_config, load_yaml, resolve_env_value


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
