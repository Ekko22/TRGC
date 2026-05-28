#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.loader import load_tasks_from_jsonl
from lmas_trgc.tasks.registry import get_default_dataset_specs

PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]
SYNTHETIC_DATASETS = ["constraint_miniset", "local_mas_safety"]


def _dataset_path(dataset: str, public_dir: Path, synthetic_dir: Path) -> Path:
    if dataset in SYNTHETIC_DATASETS:
        return synthetic_dir / f"{dataset}.jsonl"
    return public_dir / f"{dataset}.jsonl"


def audit_datasets(processed_public_dir: Path, synthetic_dir: Path) -> dict:
    specs = get_default_dataset_specs()
    records: dict[str, dict] = {}
    for dataset in [*PUBLIC_DATASETS, *SYNTHETIC_DATASETS]:
        path = _dataset_path(dataset, processed_public_dir, synthetic_dir)
        exists = path.exists()
        count = 0
        error = None
        if exists:
            try:
                count = len(load_tasks_from_jsonl(path))
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        target = specs[dataset].target_main_count
        records[dataset] = {
            "dataset": dataset,
            "path": str(path),
            "exists": exists,
            "count": count,
            "target_main_count": target,
            "ready": exists and error is None and count >= target,
            "error": error,
        }
    public_ready = sum(1 for dataset in PUBLIC_DATASETS if records[dataset]["ready"])
    synthetic_ready = sum(1 for dataset in SYNTHETIC_DATASETS if records[dataset]["ready"])
    total_available = sum(min(record["count"], record["target_main_count"]) for record in records.values())
    return {
        "datasets": records,
        "public_ready_count": public_ready,
        "synthetic_ready_count": synthetic_ready,
        "total_available_tasks": total_available,
        "can_build_full_manifest": public_ready == len(PUBLIC_DATASETS) and synthetic_ready == len(SYNTHETIC_DATASETS),
        "missing_datasets": [name for name, record in records.items() if not record["ready"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local dataset readiness for the 104-task main manifest.")
    parser.add_argument("--processed-public-dir", default="data/processed/public")
    parser.add_argument("--synthetic-dir", default="data/processed/synthetic")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-full", action="store_true")
    parser.add_argument("--report-path", default="data/manifests/dataset_audit.json")
    args = parser.parse_args()

    report = audit_datasets(Path(args.processed_public_dir), Path(args.synthetic_dir))
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = args.report_path

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for dataset, record in report["datasets"].items():
            print(f"{dataset}: ready={record['ready']} count={record['count']} target={record['target_main_count']}")
        print(f"can_build_full_manifest: {report['can_build_full_manifest']}")

    if args.require_full and not report["can_build_full_manifest"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
