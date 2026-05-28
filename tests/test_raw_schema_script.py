import json
import subprocess
import sys
from pathlib import Path


def test_print_public_dataset_raw_schema_json():
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "print_public_dataset_raw_schema.py"),
        "--dataset",
        "gsm8k",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert "gsm8k" in payload
    assert payload["gsm8k"]["minimal_required_fields"]
    assert payload["gsm8k"]["expected_raw_paths"]
