#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.loader import save_tasks_to_jsonl
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset, generate_local_mas_safety_set


def _write_dataset(path: Path, tasks, overwrite: bool) -> int:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")
    save_tasks_to_jsonl(tasks, path)
    return len(tasks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create local synthetic LMAS-TRGC task JSONL files.")
    parser.add_argument("--output-dir", default="data/processed/synthetic")
    parser.add_argument("--constraint-count", type=int, default=16)
    parser.add_argument("--local-mas-count", type=int, default=16)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    try:
        constraint_tasks = generate_constraint_miniset(args.constraint_count)
        safety_tasks = generate_local_mas_safety_set(args.local_mas_count)
        constraint_count = _write_dataset(output_dir / "constraint_miniset.jsonl", constraint_tasks, args.overwrite)
        safety_count = _write_dataset(output_dir / "local_mas_safety.jsonl", safety_tasks, args.overwrite)
    except Exception as exc:
        print(f"synthetic task generation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"constraint_miniset: {constraint_count} tasks -> {output_dir / 'constraint_miniset.jsonl'}")
    print(f"local_mas_safety: {safety_count} tasks -> {output_dir / 'local_mas_safety.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
