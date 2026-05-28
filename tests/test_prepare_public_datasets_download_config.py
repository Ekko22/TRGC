import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.tasks.registry import get_default_dataset_specs


def test_prepare_default_without_download_does_not_call_loader(tmp_path):
    from scripts.prepare_public_datasets import prepare_one_dataset

    def fail_loader(path, config, split):
        raise AssertionError("load_dataset should not be called without --allow-download")

    record = prepare_one_dataset(
        dataset="gsm8k",
        spec=get_default_dataset_specs()["gsm8k"],
        output_dir=tmp_path,
        overwrite=True,
        allow_download=False,
        load_dataset_fn=fail_loader,
        raw_public_dir=tmp_path / "raw",
    )
    assert record["status"] == "missing"


def test_prepare_allow_download_uses_converter_with_mock_loader(tmp_path):
    from scripts.prepare_public_datasets import prepare_one_dataset

    def loader(path, config, split):
        return [{"question": "What is 40+2?", "answer": "calc #### 42"}]

    record = prepare_one_dataset(
        dataset="gsm8k",
        spec=get_default_dataset_specs()["gsm8k"],
        output_dir=tmp_path,
        overwrite=True,
        allow_download=True,
        load_dataset_fn=loader,
    )
    assert record["status"] == "insufficient_count"
    assert record["count"] == 1
    assert (tmp_path / "gsm8k.jsonl").exists()


def test_prepare_allow_download_can_reach_ready_with_mock_loader(tmp_path):
    from scripts.prepare_public_datasets import prepare_one_dataset

    def loader(path, config, split):
        return [{"question": f"What is {i}+0?", "answer": f"calc #### {i}"} for i in range(8)]

    record = prepare_one_dataset(
        dataset="gsm8k",
        spec=get_default_dataset_specs()["gsm8k"],
        output_dir=tmp_path,
        overwrite=True,
        allow_download=True,
        load_dataset_fn=loader,
    )
    assert record["status"] == "ready"
    assert record["source_type"] == "hf"


def test_prepare_hf_candidates_fallback(tmp_path):
    from scripts.prepare_public_datasets import prepare_one_dataset

    calls = []

    def loader(path, config, split):
        calls.append(path)
        if len(calls) == 1:
            raise RuntimeError("candidate failed")
        return [{"question": "Is A true?", "answer": "yes"}]

    record = prepare_one_dataset(
        dataset="prontoqa",
        spec=get_default_dataset_specs()["prontoqa"],
        output_dir=tmp_path,
        overwrite=True,
        allow_download=True,
        load_dataset_fn=loader,
        raw_public_dir=tmp_path / "raw",
    )
    assert record["status"] == "insufficient_count"
    assert len(calls) == 2
    assert record["source"].startswith("hf:")


def test_prepare_fail_on_missing_exit_code(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "prepare_public_datasets.py"),
        "--dataset",
        "gsm8k",
        "--output-dir",
        str(tmp_path / "public"),
        "--report-path",
        str(tmp_path / "readiness.json"),
        "--fail-on-missing",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["missing"] == ["gsm8k"]


def test_prepare_hf_endpoint_sets_environment(monkeypatch):
    from lmas_trgc.tasks.hf_download import set_hf_environment_from_args

    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    set_hf_environment_from_args(endpoint="https://hf-mirror.com")
    assert __import__("os").environ["HF_ENDPOINT"] == "https://hf-mirror.com"
