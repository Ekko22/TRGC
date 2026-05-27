import json
import subprocess
import sys
from pathlib import Path


def test_stage_b_aggregate_script_groups(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    batch_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_b_batch.py"),
        "--output-root",
        str(tmp_path),
        "--json",
    ]
    batch = subprocess.run(batch_cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert batch.returncode == 0, batch.stderr or batch.stdout
    batch_payload = json.loads(batch.stdout)

    aggregate_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "aggregate_stage_b_artifacts.py"),
        "--batch-dir",
        batch_payload["batch_dir"],
        "--group-by",
        "topology",
        "--group-by",
        "defense_name",
        "--json",
    ]
    aggregate = subprocess.run(aggregate_cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert aggregate.returncode == 0, aggregate.stderr or aggregate.stdout
    payload = json.loads(aggregate.stdout)
    assert payload["total_runs"] > 0
    assert payload["groups"]
