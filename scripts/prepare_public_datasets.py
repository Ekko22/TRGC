#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.loader import load_raw_json_or_jsonl, save_public_tasks
from lmas_trgc.tasks.public_adapters import convert_public_items
from lmas_trgc.tasks.registry import DatasetSpec, get_default_dataset_specs

PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


def _selected_datasets(name: str) -> list[str]:
    if name == "all":
        return PUBLIC_DATASETS
    if name not in PUBLIC_DATASETS:
        raise ValueError(f"Unsupported dataset {name!r}; expected all or one of {PUBLIC_DATASETS}")
    return [name]


def _split_for(spec: DatasetSpec, override: str | None) -> str:
    return override or spec.hf_split or spec.default_split


def _find_input_file(input_dir: Path, dataset: str) -> Path | None:
    for suffix in [".jsonl", ".json", ".JSONL", ".JSON"]:
        candidate = input_dir / f"{dataset}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _output_path(dataset: str, output_dir: Path) -> Path:
    return Path(output_dir) / f"{dataset}.jsonl"


def _ensure_can_write(dataset: str, output_dir: Path, overwrite: bool) -> None:
    path = _output_path(dataset, output_dir)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")


def _load_dataset_from_hf(path: str, config: str | None, split: str) -> list[dict]:
    from datasets import load_dataset

    dataset = load_dataset(path, config, split=split)
    return [dict(item) for item in dataset]


def _convert_save_record(
    *,
    dataset: str,
    spec: DatasetSpec,
    items: list[dict],
    split: str,
    source: str,
    output_dir: Path,
    overwrite: bool,
    limit: int | None,
) -> dict:
    _ensure_can_write(dataset, output_dir, overwrite)
    limited = items[:limit] if limit is not None else items
    tasks = convert_public_items(dataset, limited, split)
    output_path = save_public_tasks(dataset, tasks, output_dir)
    status = "ready" if len(tasks) >= spec.target_main_count else "insufficient_count"
    return {
        "dataset": dataset,
        "status": status,
        "count": len(tasks),
        "target_main_count": spec.target_main_count,
        "source": source,
        "split": split,
        "output_path": str(output_path),
        "errors": [],
    }


def prepare_one_dataset(
    *,
    dataset: str,
    spec: DatasetSpec,
    output_dir: Path,
    overwrite: bool,
    split_override: str | None = None,
    limit: int | None = None,
    input_path: Path | None = None,
    input_dir: Path | None = None,
    allow_download: bool = False,
    raw_public_dir: Path = Path("data/raw/public"),
    load_dataset_fn: Callable[[str, str | None, str], list[dict]] = _load_dataset_from_hf,
) -> dict:
    split = _split_for(spec, split_override)
    errors: list[str] = []

    local_input = input_path
    if local_input is None and input_dir is not None:
        local_input = _find_input_file(input_dir, dataset)
    if local_input is None:
        local_input = _find_input_file(raw_public_dir, dataset)

    if local_input is not None:
        try:
            return _convert_save_record(
                dataset=dataset,
                spec=spec,
                items=load_raw_json_or_jsonl(local_input),
                split=split,
                source=str(local_input),
                output_dir=output_dir,
                overwrite=overwrite,
                limit=limit,
            )
        except Exception as exc:
            if input_path is not None:
                raise
            errors.append(f"local_input:{type(exc).__name__}: {exc}")

    if not allow_download:
        return {
            "dataset": dataset,
            "status": "missing",
            "count": 0,
            "target_main_count": spec.target_main_count,
            "source": None,
            "split": split,
            "output_path": str(_output_path(dataset, output_dir)),
            "errors": errors or ["no_input_and_download_disabled"],
        }

    candidates: list[tuple[str, str | None]] = []
    if spec.hf_path:
        candidates.append((spec.hf_path, spec.hf_config))
    candidates.extend((candidate, None) for candidate in spec.hf_candidates)
    if not candidates or not spec.download_supported:
        return {
            "dataset": dataset,
            "status": "missing",
            "count": 0,
            "target_main_count": spec.target_main_count,
            "source": None,
            "split": split,
            "output_path": str(_output_path(dataset, output_dir)),
            "errors": errors or ["download_not_supported_or_no_candidates"],
        }

    for hf_path, hf_config in candidates:
        try:
            items = load_dataset_fn(hf_path, hf_config, split)
            return _convert_save_record(
                dataset=dataset,
                spec=spec,
                items=items,
                split=split,
                source=f"hf:{hf_path}" + (f":{hf_config}" if hf_config else ""),
                output_dir=output_dir,
                overwrite=overwrite,
                limit=limit,
            )
        except Exception as exc:
            errors.append(f"hf:{hf_path}:{type(exc).__name__}: {exc}")

    return {
        "dataset": dataset,
        "status": "failed",
        "count": 0,
        "target_main_count": spec.target_main_count,
        "source": None,
        "split": split,
        "output_path": str(_output_path(dataset, output_dir)),
        "errors": errors,
    }


def write_report(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_ready = all(record["status"] == "ready" for record in records)
    payload = {
        "ok": True,
        "all_ready": all_ready,
        "datasets": {record["dataset"]: record for record in records},
        "missing": [record["dataset"] for record in records if record["status"] == "missing"],
        "failed": [record["dataset"] for record in records if record["status"] == "failed"],
        "insufficient_count": [
            record["dataset"] for record in records if record["status"] == "insufficient_count"
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument("--fail-on-missing", action="store_true", default=False)
    parser.add_argument("--report-path", default="data/manifests/public_dataset_readiness.json")
    args = parser.parse_args()

    specs = get_default_dataset_specs()
    selected = _selected_datasets(args.dataset)
    if args.input_path and args.dataset == "all":
        print("--input-path requires a single --dataset, not all", file=sys.stderr)
        return 1

    records: list[dict] = []
    for dataset in selected:
        records.append(
            prepare_one_dataset(
                dataset=dataset,
                spec=specs[dataset],
                output_dir=Path(args.output_dir),
                overwrite=args.overwrite,
                split_override=args.split,
                limit=args.limit,
                input_path=Path(args.input_path) if args.input_path else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                allow_download=args.allow_download,
            )
        )

    write_report(Path(args.report_path), records)
    summary = {
        "ok": True,
        "all_ready": all(record["status"] == "ready" for record in records),
        "results": records,
        "missing": [record["dataset"] for record in records if record["status"] == "missing"],
        "failed": [record["dataset"] for record in records if record["status"] == "failed"],
        "insufficient_count": [
            record["dataset"] for record in records if record["status"] == "insufficient_count"
        ],
        "report_path": args.report_path,
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for record in records:
            print(f"{record['dataset']}: {record['status']} count={record['count']} source={record['source']}")

    if args.fail_on_missing and not summary["all_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
