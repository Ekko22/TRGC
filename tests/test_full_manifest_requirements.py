import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.tasks.loader import save_tasks_to_jsonl
from lmas_trgc.tasks.registry import get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord

PUBLIC_DATASETS = ["gsm8k", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


def _fake_task(dataset: str, index: int) -> TaskRecord:
    spec = get_default_dataset_specs()[dataset]
    return TaskRecord(
        task_id=f"{dataset}_test_{index:05d}",
        dataset=dataset,
        domain=spec.domain,
        split=spec.default_split,
        prompt=f"{dataset} prompt {index}",
        gold_answer="A" if spec.metric == "accuracy" else str(index),
        choices=["A. option", "B. other"] if spec.metric == "accuracy" else [],
        source="test",
    )


def _run_build(repo_root: Path, cwd: Path, *args: str):
    cmd = [sys.executable, str(repo_root / "scripts" / "build_task_manifest.py"), *args]
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def test_build_manifest_require_full_fails_without_public_data(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = _run_build(
        repo_root,
        tmp_path,
        "--require-full",
        "--output",
        "data/manifests/main_manifest.json",
        "--json",
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["is_full_manifest"] is False


def test_build_manifest_require_full_succeeds_with_all_fake_public_data(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    public_dir = tmp_path / "data" / "processed" / "public"
    for dataset in PUBLIC_DATASETS:
        save_tasks_to_jsonl([_fake_task(dataset, i) for i in range(8)], public_dir / f"{dataset}.jsonl")

    completed = _run_build(
        repo_root,
        tmp_path,
        "--require-full",
        "--output",
        "data/manifests/main_manifest.json",
        "--json",
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["total_tasks"] == 96
    expected = {dataset: 8 for dataset in PUBLIC_DATASETS}
    expected.update({"constraint_miniset": 16, "local_mas_safety": 16})
    assert payload["dataset_counts"] == expected
    manifest_text = (tmp_path / "data" / "manifests" / "main_manifest.json").read_text(encoding="utf-8")
    assert "prompt" not in manifest_text


def test_build_manifest_require_full_fails_when_one_public_file_missing(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    public_dir = tmp_path / "data" / "processed" / "public"
    for dataset in PUBLIC_DATASETS:
        if dataset == "mbpp":
            continue
        save_tasks_to_jsonl([_fake_task(dataset, i) for i in range(8)], public_dir / f"{dataset}.jsonl")

    completed = _run_build(
        repo_root,
        tmp_path,
        "--require-full",
        "--output",
        "data/manifests/main_manifest.json",
        "--json",
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["is_full_manifest"] is False
    assert "mbpp" in payload["missing_datasets"]
