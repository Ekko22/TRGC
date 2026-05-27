#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.logging.artifact_loader import load_metrics, load_run_summary, validate_run_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and validate an LMAS-TRGC run artifact directory.")
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        run_dir = Path(args.run_dir)
        validate_run_artifact(run_dir)
        summary = load_run_summary(run_dir)
        metrics = load_metrics(run_dir)
        output = {
            "run_id": summary.run_id,
            "task_id": summary.task_id,
            "topology": summary.topology,
            "attack_type": summary.attack_type,
            "defense_name": summary.defense_name,
            "total_messages": summary.total_messages,
            "attacked_messages": summary.attacked_messages,
            "blocked_messages": summary.blocked_messages,
            "delivery_rate": metrics.delivery_rate,
            "block_rate": metrics.block_rate,
            "critical_node_reach_rate": metrics.critical_node_reach_rate,
        }
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("# Run Artifact Summary")
            for key, value in output.items():
                print(f"- {key}: {value}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Artifact validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
