import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_b_pilot.py"


def test_stage_b_pilot_graph_message_poisoning_json():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--topology",
            "graph",
            "--attack",
            "message_poisoning",
            "--defense",
            "trgc",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["completed"] is True
    assert data["attacked_messages"] > 0
