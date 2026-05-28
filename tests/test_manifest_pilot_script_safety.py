import json
import subprocess
import sys
from pathlib import Path


def test_stage_c_manifest_pilot_dry_run_is_safe():
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_c_deepseek_manifest_pilot.py"),
        "--dry-run",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["did_call_real_llm"] is False
    assert payload["selected_tasks"] == 11
    assert "prontoqa" in payload["selected_datasets"]


def test_stage_c_manifest_pilot_refuses_without_confirm():
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_c_deepseek_manifest_pilot.py"),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["did_call_real_llm"] is False
    assert "Refusing to run real DeepSeek manifest pilot" in payload["message"]


def test_stage_c_manifest_pilot_check_config_only_does_not_print_keys():
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_stage_c_deepseek_manifest_pilot.py"),
        "--check-config-only",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode in {0, 1}
    payload = json.loads(completed.stdout)
    assert payload["did_call_real_llm"] is False
    assert "DEEPSEEK_API_KEY" not in completed.stdout
    assert "LOCAL_SV_API_KEY" not in completed.stdout
