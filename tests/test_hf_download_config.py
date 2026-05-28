import sys
from types import SimpleNamespace

from lmas_trgc.tasks.hf_download import load_hf_with_candidates


def test_load_hf_with_candidates_fallback_and_limit(monkeypatch):
    calls = []

    def fake_load_dataset(path, *args, **kwargs):
        calls.append((path, args, kwargs))
        if len(calls) == 1:
            raise RuntimeError("first candidate failed")
        return [{"question": str(i), "answer": str(i)} for i in range(5)]

    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(load_dataset=fake_load_dataset))
    result = load_hf_with_candidates(
        "gsm8k",
        [
            {"path": "bad/source", "config": None, "split": "test"},
            {"path": "openai/gsm8k", "config": "main", "split": "test"},
        ],
        limit=2,
    )
    assert result.success is True
    assert len(result.items) == 2
    assert len(result.attempts) == 2
    assert result.attempts[0].success is False
    assert result.attempts[1].success is True


def test_load_hf_with_candidates_all_failed(monkeypatch):
    def fake_load_dataset(path, *args, **kwargs):
        raise RuntimeError(f"failed {path}")

    monkeypatch.setitem(sys.modules, "datasets", SimpleNamespace(load_dataset=fake_load_dataset))
    result = load_hf_with_candidates("gsm8k", [{"path": "bad/source", "split": "test"}])
    assert result.success is False
    assert result.items == []
    assert result.attempts[0].error_type == "RuntimeError"


def test_hf_download_module_does_not_import_datasets_at_import_time():
    assert "load_dataset" not in vars(sys.modules["lmas_trgc.tasks.hf_download"])
