import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_a_smoke.py"


def test_stage_a_smoke_script_json_star_trgc():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--topology", "star", "--defense", "trgc", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["completed"] is True
    assert data["total_messages"] > 0
