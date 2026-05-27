#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.loader import load_raw_json_or_jsonl, save_public_tasks
from lmas_trgc.tasks.public_adapters import CONVERTERS, convert_public_items
from lmas_trgc.tasks.registry import DatasetSpec, get_default_dataset_specs

PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


def _split_for(spec: DatasetSpec, override: str | None) -> str:
    return override or spec.default_split


def _output_path(dataset: str, output_dir: Path) -> Path:
    return output_dir / f"{dataset}.jsonl"


def _ensure_can_write(dataset: str, output_dir: Path, overwrite: bool) -> None:
    path = _output_path(dataset, output_dir)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")


def _convert_and_save(
    *,
    dataset: str,
    items: list[dict],
    split: str,
    output_dir: Path,
    overwrite: bool,
    limit: int | None,
) -> dict:
    _ensure_can_write(dataset, output_dir, overwrite)
    limited = items[:limit] if limit is not None else items
    tasks = convert_public_items(dataset, limited, split)
    path = save_public_tasks(dataset, tasks, output_dir)
    return {"dataset": dataset, "converted": len(tasks), "output": str(path), "status": "converted"}


def _load_from_hf(spec: DatasetSpec, split: str) -> list[dict]:
    if not spec.hf_path:
        raise ValueError(f"Dataset {spec.name} has no hf_path configured")
    from datasets import load_dataset

    dataset = load_dataset(spec.hf_path, spec.hf_config, split=split)
    return [dict(item) for item in dataset]


def _find_input_file(input_dir: Path, dataset: str) -> Path | None:
    for suffix in [".jsonl", ".json", ".JSONL", ".JSON"]:
        candidate = input_dir / f"{dataset}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _selected_datasets(name: str) -> list[str]:
    if name == "all":
        return PUBLIC_DATASETS
    if name not in PUBLIC_DATASETS:
        raise ValueError(f"Unsupported dataset {name!r}; expected all or one of {PUBLIC_DATASETS}")
    return [name]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare standardized public dataset JSONL files.")
    parser.add_argument("--dataset", default="all", choices=["all", *PUBLIC_DATASETS])
    parser.add_argument("--input-path")
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir", default="data/processed/public")
    parser.add_argument("--split")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow-download", action="store_true", default=False)
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    specs = get_default_dataset_specs()
    results: list[dict] = []
    missing: list[str] = []

    try:
        selected = _selected_datasets(args.dataset)
        if args.input_path:
            if args.dataset == "all":
                raise ValueError("--input-path requires a single --dataset, not all")
            dataset = selected[0]
            items = load_raw_json_or_jsonl(Path(args.input_path))
            results.append(
                _convert_and_save(
                    dataset=dataset,
                    items=items,
                    split=_split_for(specs[dataset], args.split),
                    output_dir=output_dir,
                    overwrite=args.overwrite,
                    limit=args.limit,
                )
            )
        elif args.input_dir:
            input_dir = Path(args.input_dir)
            for dataset in selected:
                path = _find_input_file(input_dir, dataset)
                if path is None:
                    missing.append(dataset)
                    results.append({"dataset": dataset, "status": "missing", "reason": "input_file_not_found"})
                    continue
                items = load_raw_json_or_jsonl(path)
                results.append(
                    _convert_and_save(
                        dataset=dataset,
                        items=items,
                        split=_split_for(specs[dataset], args.split),
                        output_dir=output_dir,
                        overwrite=args.overwrite,
                        limit=args.limit,
                    )
                )
        elif args.allow_download:
            for dataset in selected:
                spec = specs[dataset]
                if spec.source_type != "hf":
                    missing.append(dataset)
                    results.append({"dataset": dataset, "status": "missing", "reason": "local_jsonl_requires_input_file"})
                    continue
                items = _load_from_hf(spec, _split_for(spec, args.split))
                results.append(
                    _convert_and_save(
                        dataset=dataset,
                        items=items,
                        split=_split_for(spec, args.split),
                        output_dir=output_dir,
                        overwrite=args.overwrite,
                        limit=args.limit,
                    )
                )
        else:
            missing = selected
            results = [
                {
                    "dataset": dataset,
                    "status": "missing",
                    "reason": "no_input_and_download_disabled",
                }
                for dataset in selected
            ]
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}, indent=2))
        else:
            print(f"public dataset preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    summary = {"ok": True, "results": results, "missing": missing}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for result in results:
            if result["status"] == "converted":
                print(f"{result['dataset']}: converted {result['converted']} tasks -> {result['output']}")
            else:
                print(f"{result['dataset']}: missing ({result['reason']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
