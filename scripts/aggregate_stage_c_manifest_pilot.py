#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.analysis.batch_aggregate import aggregate_metrics, load_metrics_from_artifact_dirs
from lmas_trgc.analysis.effect_aggregate import (
    aggregate_standard_metrics,
    compute_benign_drop_by_defense,
    group_standard_metrics,
)
from lmas_trgc.logging.artifact_loader import load_standard_metrics, validate_run_artifact


def _read_run_index(batch_dir: Path) -> list[dict]:
    path = batch_dir / "run_index.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"run index not found: {path}")
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid run_index JSONL at {path}:{line_number}: {exc}") from exc
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Stage-C DeepSeek manifest pilot artifacts.")
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--group-by", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        batch_dir = Path(args.batch_dir)
        records = _read_run_index(batch_dir)
        artifact_dirs = [record["artifact_dir"] for record in records if record.get("artifact_dir")]
        propagation_metrics = load_metrics_from_artifact_dirs(artifact_dirs)
        standard_metrics = []
        skipped = []
        for record in records:
            artifact_dir = record.get("artifact_dir")
            if not artifact_dir:
                skipped.append({"run_id": record.get("run_id"), "reason": "missing_artifact_dir"})
                continue
            run_dir = Path(artifact_dir)
            validate_run_artifact(run_dir)
            standard = load_standard_metrics(run_dir)
            if standard is None:
                skipped.append({"run_id": record.get("run_id"), "reason": "missing_standard_metrics"})
                continue
            standard_metrics.append(standard)

        propagation = aggregate_metrics(propagation_metrics)
        standard = aggregate_standard_metrics(standard_metrics)
        output = {
            **propagation,
            **standard,
            "batch_dir": str(batch_dir),
            "artifact_count": len(artifact_dirs),
            "skipped": skipped,
            "groups": group_standard_metrics(standard_metrics, args.group_by) if args.group_by else [],
            "benign_drop_by_defense": compute_benign_drop_by_defense(standard_metrics),
        }
        if args.output:
            Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("# Stage-C Manifest Pilot Aggregate")
            for key, value in output.items():
                if key not in {"groups", "skipped", "benign_drop_by_defense"}:
                    print(f"- {key}: {value}")
            print(f"- groups: {len(output['groups'])}")
            print(f"- skipped: {len(skipped)}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Stage-C manifest pilot aggregation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
