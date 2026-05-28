import json
import subprocess
import sys
from pathlib import Path


def _run(args):
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(repo_root / "scripts" / "run_stage_c_deepseek_smoke.py"), *args]
    return subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)


def test_deepseek_smoke_dry_run_no_real_call():
    completed = _run(["--dry-run", "--json"])
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["did_call_real_llm"] is False
    assert payload["dry_run"] is True


def test_deepseek_smoke_refuses_without_confirm():
    completed = _run(["--json"])
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Refusing to call DeepSeek" in payload["message"]
    assert payload["did_call_real_llm"] is False


def test_deepseek_smoke_check_config_only_does_not_print_key():
    completed = _run(["--check-config-only", "--json"])
    assert completed.returncode in {0, 1}
    output = completed.stdout
    payload = json.loads(output)
    assert payload["did_call_real_llm"] is False
    assert "github_pat" not in output
    assert "sk-" not in output
    assert "DEEPSEEK_API_KEY" not in output
