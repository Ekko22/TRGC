import json
import subprocess
import sys
from pathlib import Path


def test_aggregate_standard_metrics_script(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    batch_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_b_batch.py"),
        "--output-root",
        str(tmp_path),
        "--judge-mode",
        "mock_protocol",
        "--json",
    ]
    batch = subprocess.run(batch_cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert batch.returncode == 0, batch.stderr or batch.stdout
    batch_payload = json.loads(batch.stdout)

    aggregate_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "aggregate_standard_metrics.py"),
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
    assert "clean_tsr" in payload
    assert "robust_tsr" in payload
    assert "asr" in payload
    assert "svr" in payload
