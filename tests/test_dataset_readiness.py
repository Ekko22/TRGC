import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.tasks.loader import save_tasks_to_jsonl
from lmas_trgc.tasks.schema import TaskRecord


def _task(dataset: str, index: int) -> TaskRecord:
    return TaskRecord(
        task_id=f"{dataset}_test_{index:05d}",
        dataset=dataset,
        domain="math_reasoning",
        split="test",
        prompt=f"{dataset} prompt {index}",
        gold_answer=str(index),
        source="test",
    )


def test_audit_dataset_readiness_empty_dirs(tmp_path):
    from scripts.audit_dataset_readiness import audit_datasets

    report = audit_datasets(tmp_path / "public", tmp_path / "synthetic")
    assert report["public_ready_count"] == 0
    assert "gsm8k" in report["missing_datasets"]


def test_audit_dataset_readiness_counts_fake_processed(tmp_path):
    from scripts.audit_dataset_readiness import audit_datasets

    public_dir = tmp_path / "public"
    save_tasks_to_jsonl([_task("gsm8k", i) for i in range(8)], public_dir / "gsm8k.jsonl")
    report = audit_datasets(public_dir, tmp_path / "synthetic")
    assert report["datasets"]["gsm8k"]["count"] == 8
    assert report["datasets"]["gsm8k"]["ready"] is True


def test_audit_dataset_readiness_require_full_exit_code(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_dataset_readiness.py"),
        "--processed-public-dir",
        str(tmp_path / "public"),
        "--synthetic-dir",
        str(tmp_path / "synthetic"),
        "--report-path",
        str(tmp_path / "audit.json"),
        "--require-full",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["can_build_full_manifest"] is False
