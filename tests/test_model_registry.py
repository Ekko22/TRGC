import pytest

from lmas_trgc.llm.registry import build_model_registry


MODEL_ENV_NAMES = [
    "DEEPSEEK_API_KEY",
    "MODEL2_API_KEY",
    "MODEL3_API_KEY",
    "MODEL4_API_KEY",
    "LOCAL_SV_API_KEY",
]


def test_build_model_registry_without_keys(monkeypatch):
    for name in MODEL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    registry = build_model_registry(require_keys=False)
    assert registry.list_task_model_slots() == ["M1", "M2", "M3", "M4"]
    assert registry.get_safety_verifier().is_task_agent is False
    assert registry.get_task_model("M1").api_key_set is False


def test_model_registry_access_and_validation(monkeypatch):
    for name in MODEL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    registry = build_model_registry(require_keys=False)
    with pytest.raises(KeyError):
        registry.get_task_model("BAD")
    registry.validate_required_slots(["M1", "M2", "M3", "M4"])


def test_model_registry_safe_dict_excludes_key_values(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    registry = build_model_registry(require_keys=False)
    safe = registry.to_safe_dict()
    assert "secret-value" not in str(safe)
    assert safe["task_models"]["M1"]["api_key_set"] is True
    assert "api_key_env" in safe["task_models"]["M1"]
