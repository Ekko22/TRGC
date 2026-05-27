import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.tasks.loader import load_tasks_from_jsonl


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_public_datasets.py"


def test_prepare_public_dataset_from_input_path(tmp_path):
    raw = tmp_path / "gsm8k.jsonl"
    raw.write_text(json.dumps({"question": "What is 6 * 7?", "answer": "#### 42"}) + "\n", encoding="utf-8")
    output_dir = tmp_path / "public"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dataset",
            "gsm8k",
            "--input-path",
            str(raw),
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = output_dir / "gsm8k.jsonl"
    assert output.exists()
    tasks = load_tasks_from_jsonl(output)
    assert tasks[0].gold_answer == "42"

    second = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dataset",
            "gsm8k",
            "--input-path",
            str(raw),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert second.returncode == 1


def test_prepare_public_dataset_default_missing_no_network():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dataset", "all", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["ok"] is True
    assert "gsm8k" in summary["missing"]
