#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.dataset_sampler import build_main_task_selection
from lmas_trgc.tasks.loader import load_dataset_tasks, save_tasks_to_jsonl
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset, generate_local_mas_safety_set
from lmas_trgc.tasks.manifest import build_task_manifest, save_task_manifest
from lmas_trgc.tasks.registry import get_default_dataset_specs


def _ensure_synthetic_files(synthetic_dir: Path) -> None:
    files = {
        "constraint_miniset": synthetic_dir / "constraint_miniset.jsonl",
        "local_mas_safety": synthetic_dir / "local_mas_safety.jsonl",
    }
    if not files["constraint_miniset"].exists():
        save_tasks_to_jsonl(generate_constraint_miniset(16), files["constraint_miniset"])
    if not files["local_mas_safety"].exists():
        save_tasks_to_jsonl(generate_local_mas_safety_set(16), files["local_mas_safety"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the LMAS-TRGC main task manifest.")
    parser.add_argument("--output", default="data/manifests/main_manifest.json")
    parser.add_argument("--synthetic-dir", default="data/processed/synthetic")
    parser.add_argument("--allow-download", action="store_true", default=False)
    parser.add_argument("--manifest-id", default="main_v1_104")
    parser.add_argument("--create-synthetic-if-missing", dest="create_synthetic_if_missing", action="store_true", default=True)
    parser.add_argument("--no-create-synthetic-if-missing", dest="create_synthetic_if_missing", action="store_false")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    specs = get_default_dataset_specs()
    synthetic_dir = Path(args.synthetic_dir)
    if args.create_synthetic_if_missing:
        _ensure_synthetic_files(synthetic_dir)

    all_tasks_by_dataset = {}
    for name, spec in specs.items():
        all_tasks_by_dataset[name] = load_dataset_tasks(spec, Path.cwd(), allow_download=args.allow_download)

    selection = build_main_task_selection(all_tasks_by_dataset, specs)
    manifest = build_task_manifest(
        selection.selected_tasks,
        manifest_id=args.manifest_id,
        missing_datasets=selection.missing_datasets,
    )
    save_task_manifest(manifest, Path(args.output))

    summary = {
        "manifest_id": manifest.manifest_id,
        "total_tasks": manifest.total_tasks,
        "dataset_counts": manifest.dataset_counts,
        "missing_datasets": manifest.missing_datasets,
        "output": args.output,
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"manifest_id: {manifest.manifest_id}")
        print(f"total_tasks: {manifest.total_tasks}")
        print(f"dataset_counts: {manifest.dataset_counts}")
        print(f"missing_datasets: {manifest.missing_datasets}")
        print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
