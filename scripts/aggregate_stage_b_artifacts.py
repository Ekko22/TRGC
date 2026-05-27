#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.analysis.batch_aggregate import (
    aggregate_metrics,
    group_metrics,
    load_metrics_from_artifact_dirs,
    metrics_to_rows,
)


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
    parser = argparse.ArgumentParser(description="Aggregate Stage-B run artifacts from a batch directory.")
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--group-by", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        batch_dir = Path(args.batch_dir)
        run_records = _read_run_index(batch_dir)
        artifact_dirs = [record["artifact_dir"] for record in run_records if record.get("artifact_dir")]
        metrics = load_metrics_from_artifact_dirs(artifact_dirs)
        aggregate = aggregate_metrics(metrics)
        groups = group_metrics(metrics, args.group_by) if args.group_by else []
        output = {
            **aggregate,
            "batch_dir": str(batch_dir),
            "artifact_count": len(artifact_dirs),
            "groups": groups,
            "rows": metrics_to_rows(metrics),
        }
        if args.output:
            Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("# Stage-B Aggregate")
            for key, value in output.items():
                if key not in {"groups", "rows"}:
                    print(f"- {key}: {value}")
            if groups:
                print(f"- groups: {len(groups)}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        else:
            print(f"Stage-B aggregation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
