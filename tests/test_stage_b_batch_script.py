import json
import subprocess
import sys
from pathlib import Path


def test_stage_b_batch_script_default(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_b_batch.py"),
        "--output-root",
        str(tmp_path),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["total_runs"] == 8
    assert payload["successful_runs"] == 8
    assert payload["failed_runs"] == 0
    assert Path(payload["batch_dir"]).exists()
    assert Path(payload["run_index_path"]).exists()
    assert Path(payload["aggregate_metrics_path"]).exists()
