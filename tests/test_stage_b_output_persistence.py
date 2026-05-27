import json
import subprocess
import sys
from pathlib import Path


def test_stage_b_save_artifact_and_inspect(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    run_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_b_pilot.py"),
        "--topology",
        "graph",
        "--attack",
        "message_poisoning",
        "--defense",
        "trgc",
        "--save-artifact",
        "--output-root",
        str(tmp_path),
        "--json",
    ]
    completed = subprocess.run(run_cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["completed"] is True
    assert payload["attacked_messages"] > 0
    assert payload["artifact_dir"]
    artifact_dir = Path(payload["artifact_dir"])
    assert artifact_dir.exists()

    inspect_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "inspect_run_artifact.py"),
        str(artifact_dir),
        "--json",
    ]
    inspected = subprocess.run(inspect_cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert inspected.returncode == 0, inspected.stderr or inspected.stdout
    inspected_payload = json.loads(inspected.stdout)
    assert inspected_payload["run_id"] == payload["run_id"]
    assert inspected_payload["attacked_messages"] == payload["attacked_messages"]
