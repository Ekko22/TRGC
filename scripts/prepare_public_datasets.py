#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.hf_download import (
    HFAttemptResult,
    HFDatasetLoadResult,
    set_hf_environment_from_args,
)
from lmas_trgc.tasks.loader import load_raw_json_or_jsonl, save_public_tasks
from lmas_trgc.tasks.public_adapters import convert_public_items
from lmas_trgc.tasks.registry import DatasetSpec, get_default_dataset_specs

PUBLIC_DATASETS = ["gsm8k", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]


def _selected_datasets(name: str) -> list[str]:
    if name == "all":
        return PUBLIC_DATASETS
    if name not in PUBLIC_DATASETS:
        raise ValueError(f"Unsupported dataset {name!r}; expected all or one of {PUBLIC_DATASETS}")
    return [name]


def _split_for(spec: DatasetSpec, override: str | None) -> str:
    return override or spec.primary_hf_split or spec.hf_split or spec.default_split


def _find_input_file(input_dir: Path, dataset: str) -> Path | None:
    for suffix in [".jsonl", ".json", ".JSONL", ".JSON"]:
        candidate = input_dir / f"{dataset}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _find_local_raw_candidate(spec: DatasetSpec, base_dir: Path) -> Path | None:
    for raw_candidate in spec.local_raw_candidates:
        path = Path(raw_candidate)
        if not path.is_absolute():
            path = base_dir / path
        if path.exists():
            return path
    return None


def _output_path(dataset: str, output_dir: Path) -> Path:
    return Path(output_dir) / f"{dataset}.jsonl"


def _ensure_can_write(dataset: str, output_dir: Path, overwrite: bool) -> None:
    path = _output_path(dataset, output_dir)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")


def _conversion_limit(spec: DatasetSpec, limit: int | None) -> int:
    return max(spec.target_main_count, limit or spec.target_main_count)


def _attempt_dict(attempt: HFAttemptResult) -> dict:
    return attempt.model_dump()


def _success_record(
    *,
    dataset: str,
    spec: DatasetSpec,
    count: int,
    source_type: str,
    source_detail: str,
    split: str,
    output_path: Path,
    attempts: list[dict] | None = None,
) -> dict:
    status = "ready" if count >= spec.target_main_count else "insufficient_count"
    return {
        "dataset": dataset,
        "status": status,
        "count": count,
        "target_main_count": spec.target_main_count,
        "source_type": source_type,
        "source_detail": source_detail,
        "source": source_detail,
        "split": split,
        "output_path": str(output_path),
        "attempts": attempts or [],
        "errors": [],
    }


def _failure_record(
    *,
    dataset: str,
    spec: DatasetSpec,
    status: str,
    split: str,
    output_dir: Path,
    source_type: str,
    source_detail: str | None,
    attempts: list[dict] | None = None,
    errors: list[str] | None = None,
) -> dict:
    return {
        "dataset": dataset,
        "status": status,
        "count": 0,
        "target_main_count": spec.target_main_count,
        "source_type": source_type,
        "source_detail": source_detail,
        "source": source_detail,
        "split": split,
        "output_path": str(_output_path(dataset, output_dir)),
        "attempts": attempts or [],
        "errors": errors or [],
    }


def _convert_save_record(
    *,
    dataset: str,
    spec: DatasetSpec,
    items: list[dict],
    split: str,
    source_type: str,
    source_detail: str,
    output_dir: Path,
    overwrite: bool,
    limit: int | None,
    attempts: list[dict] | None = None,
) -> dict:
    _ensure_can_write(dataset, output_dir, overwrite)
    tasks = convert_public_items(dataset, items[: _conversion_limit(spec, limit)], split)
    output_path = save_public_tasks(dataset, tasks, output_dir)
    return _success_record(
        dataset=dataset,
        spec=spec,
        count=len(tasks),
        source_type=source_type,
        source_detail=source_detail,
        split=split,
        output_path=output_path,
        attempts=attempts,
    )


def _candidate_list(spec: DatasetSpec, split: str) -> list[dict]:
    candidates = [dict(candidate) for candidate in spec.hf_candidates]
    if not candidates and spec.primary_hf_path:
        candidates.append(
            {
                "path": spec.primary_hf_path,
                "config": spec.primary_hf_config,
                "split": spec.primary_hf_split or split,
            }
        )
    normalized: list[dict] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for candidate in candidates:
        candidate.setdefault("split", split)
        key = (candidate["path"], candidate.get("config"), candidate.get("split"))
        if key not in seen:
            normalized.append(candidate)
            seen.add(key)
    return normalized


def _load_hf_result(
    dataset: str,
    candidates: list[dict],
    max_raw_rows: int | None,
    load_dataset_fn: Callable[[str, str | None, str], list[dict]] | None,
) -> HFDatasetLoadResult:
    if load_dataset_fn is None:
        from lmas_trgc.tasks.hf_download import load_hf_with_candidates

        return load_hf_with_candidates(dataset, candidates, limit=max_raw_rows)

    attempts: list[HFAttemptResult] = []
    for candidate in candidates:
        try:
            items = load_dataset_fn(candidate["path"], candidate.get("config"), candidate.get("split") or "test")
            if max_raw_rows is not None:
                items = items[:max_raw_rows]
        except Exception as exc:
            attempts.append(
                HFAttemptResult(
                    candidate=candidate,
                    success=False,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            continue
        attempts.append(HFAttemptResult(candidate=candidate, success=True, row_count=len(items)))
        return HFDatasetLoadResult(
            success=True,
            dataset_name=dataset,
            items=items,
            successful_candidate=candidate,
            attempts=attempts,
        )
    return HFDatasetLoadResult(success=False, dataset_name=dataset, attempts=attempts)


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
    max_raw_rows: int | None = 200,
    load_dataset_fn: Callable[[str, str | None, str], list[dict]] | None = None,
) -> dict:
    split = _split_for(spec, split_override)
    errors: list[str] = []

    local_input = input_path
    if local_input is None and input_dir is not None:
        local_input = _find_input_file(input_dir, dataset)
    if local_input is None:
        local_input = _find_local_raw_candidate(spec, Path.cwd()) or _find_input_file(raw_public_dir, dataset)

    if local_input is not None:
        try:
            return _convert_save_record(
                dataset=dataset,
                spec=spec,
                items=load_raw_json_or_jsonl(local_input),
                split=split,
                source_type="local_raw",
                source_detail=str(local_input),
                output_dir=output_dir,
                overwrite=overwrite,
                limit=limit,
            )
        except Exception as exc:
            if input_path is not None:
                raise
            errors.append(f"local_raw:{local_input}:{type(exc).__name__}: {exc}")

    if not allow_download:
        return _failure_record(
            dataset=dataset,
            spec=spec,
            status="missing",
            split=split,
            output_dir=output_dir,
            source_type="missing",
            source_detail=None,
            errors=errors or ["no_input_and_download_disabled"],
        )

    if not spec.download_supported:
        return _failure_record(
            dataset=dataset,
            spec=spec,
            status="missing",
            split=split,
            output_dir=output_dir,
            source_type="missing",
            source_detail=None,
            errors=errors or ["download_not_supported"],
        )

    candidates = _candidate_list(spec, split)
    if not candidates:
        return _failure_record(
            dataset=dataset,
            spec=spec,
            status="missing",
            split=split,
            output_dir=output_dir,
            source_type="missing",
            source_detail=None,
            errors=errors or ["no_hf_candidates"],
        )

    attempts: list[dict] = []
    for candidate in candidates:
        hf_result = _load_hf_result(dataset, [candidate], max_raw_rows, load_dataset_fn)
        attempts.extend(_attempt_dict(attempt) for attempt in hf_result.attempts)
        errors.extend(
            f"hf:{attempt.candidate.get('path')}:{attempt.error_type}: {attempt.error_message}"
            for attempt in hf_result.attempts
            if not attempt.success
        )
        if not hf_result.success or not hf_result.successful_candidate:
            continue
        try:
            source_detail = "hf:{path}".format(path=hf_result.successful_candidate["path"])
            if hf_result.successful_candidate.get("config"):
                source_detail += f":{hf_result.successful_candidate['config']}"
            return _convert_save_record(
                dataset=dataset,
                spec=spec,
                items=hf_result.items,
                split=hf_result.successful_candidate.get("split") or split,
                source_type="hf",
                source_detail=source_detail,
                output_dir=output_dir,
                overwrite=overwrite,
                limit=limit,
                attempts=attempts,
            )
        except Exception as exc:
            errors.append(f"hf_conversion:{candidate.get('path')}:{type(exc).__name__}: {exc}")

    return _failure_record(
        dataset=dataset,
        spec=spec,
        status="failed",
        split=split,
        output_dir=output_dir,
        source_type="failed",
        source_detail=None,
        attempts=attempts,
        errors=errors or ["all_hf_candidates_failed"],
    )


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
    parser.add_argument("--require-count", action="store_true", default=False)
    parser.add_argument("--report-path", default="data/manifests/public_dataset_readiness.json")
    parser.add_argument("--hf-endpoint")
    parser.add_argument("--hf-cache-dir")
    parser.add_argument("--max-raw-rows", type=int, default=200)
    args = parser.parse_args()

    specs = get_default_dataset_specs()
    selected = _selected_datasets(args.dataset)
    if args.input_path and args.dataset == "all":
        print("--input-path requires a single --dataset, not all", file=sys.stderr)
        return 1

    set_hf_environment_from_args(endpoint=args.hf_endpoint, cache_dir=args.hf_cache_dir)

    records: list[dict] = []
    try:
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
                    max_raw_rows=args.max_raw_rows,
                )
            )
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

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
            print(
                f"{record['dataset']}: {record['status']} count={record['count']} "
                f"source={record['source_detail']}"
            )

    if args.fail_on_missing and not summary["all_ready"]:
        return 2
    if args.require_count and summary["insufficient_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
