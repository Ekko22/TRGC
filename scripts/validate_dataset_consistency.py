#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lmas_trgc.tasks.loader import load_tasks_from_jsonl, save_tasks_to_jsonl
from lmas_trgc.tasks.metadata_enrichment import (
    ANSWER_FORMAT_BY_DATASET,
    ATTACK_TYPES,
    CONSTRAINT_LABELS,
    TARGET_SLOTS_BY_DATASET,
    enrich_task_metadata,
    normalize_numeric_answer,
)
from lmas_trgc.tasks.registry import get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord


def _dataset_path(dataset: str, public_dir: Path, synthetic_dir: Path) -> Path:
    return synthetic_dir / f"{dataset}.jsonl" if dataset in {"constraint_miniset", "local_mas_safety"} else public_dir / f"{dataset}.jsonl"


def _choice_labels(task: TaskRecord) -> list[str]:
    labels: list[str] = []
    for choice in task.choices:
        match = re.match(r"^\s*([A-Z])(?:[\).:]|\s)", choice)
        if match:
            labels.append(match.group(1))
    return labels


def _message(level: str, code: str, message: str, dataset: str | None = None, task_id: str | None = None) -> dict:
    payload = {"level": level, "code": code, "message": message}
    if dataset:
        payload["dataset"] = dataset
    if task_id:
        payload["task_id"] = task_id
    return payload


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_task(task: TaskRecord) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    metadata = task.metadata or {}
    for key in ["judge_type", "answer_format", "task_anchors", "target_slots", "attack_surfaces"]:
        if key not in metadata:
            errors.append(_message("error", "missing_trgc_metadata", f"Missing metadata key: {key}", task.dataset, task.task_id))
    for slot in TARGET_SLOTS_BY_DATASET.get(task.dataset, []):
        if slot not in metadata.get("target_slots", []):
            errors.append(_message("error", "missing_target_slot", f"Missing target slot: {slot}", task.dataset, task.task_id))
    surfaces = metadata.get("attack_surfaces") if isinstance(metadata.get("attack_surfaces"), dict) else {}
    for attack_type in ATTACK_TYPES:
        if not surfaces.get(attack_type):
            errors.append(_message("error", "missing_attack_surface", f"Missing attack surface: {attack_type}", task.dataset, task.task_id))
    expected_format = ANSWER_FORMAT_BY_DATASET.get(task.dataset)
    if expected_format and metadata.get("answer_format") != expected_format:
        errors.append(
            _message(
                "error",
                "answer_format_mismatch",
                f"Expected {expected_format}, got {metadata.get('answer_format')}",
                task.dataset,
                task.task_id,
            )
        )
    answer_format = metadata.get("answer_format")
    if answer_format == "multiple_choice":
        labels = _choice_labels(task)
        if len(labels) != len(set(labels)):
            errors.append(_message("error", "choice_label_duplicate", "Choice labels must be unique", task.dataset, task.task_id))
        if task.gold_answer not in labels:
            errors.append(_message("error", "choice_gold_not_in_labels", "gold_answer must be one of the choice labels", task.dataset, task.task_id))
    if answer_format == "numeric_exact":
        if not task.gold_answer or not re.fullmatch(r"-?\d+(?:\.\d+)?", task.gold_answer):
            errors.append(_message("error", "numeric_answer_invalid", "numeric_exact gold_answer must be a numeric string", task.dataset, task.task_id))
        raw_answer = metadata.get("raw_answer")
        if task.dataset == "gsm8k" and isinstance(raw_answer, str) and "####" in raw_answer:
            expected = normalize_numeric_answer(raw_answer.split("####", 1)[1])
            if task.gold_answer != expected:
                errors.append(
                    _message(
                        "error",
                        "numeric_answer_mismatch",
                        f"gold_answer should be {expected} from raw_answer delimiter",
                        task.dataset,
                        task.task_id,
                    )
                )
    if answer_format == "code_generation" and "tests" not in metadata:
        errors.append(_message("error", "code_tests_missing", "code_generation metadata must include tests", task.dataset, task.task_id))
    if answer_format == "binary_safety" and task.gold_answer not in {"safe", "unsafe"}:
        errors.append(_message("error", "binary_safety_label_invalid", "gold_answer must be safe or unsafe", task.dataset, task.task_id))
    if answer_format == "constraint_label" and task.gold_answer not in CONSTRAINT_LABELS:
        errors.append(_message("error", "constraint_label_invalid", "gold_answer is not a supported constraint label", task.dataset, task.task_id))
    return errors, warnings


def repair_and_validate(
    public_dir: Path,
    synthetic_dir: Path,
    manifest_dir: Path,
    *,
    repair: bool,
) -> dict[str, Any]:
    specs = get_default_dataset_specs()
    errors: list[dict] = []
    warnings: list[dict] = []
    fixed_task_ids: list[str] = []
    all_tasks: list[TaskRecord] = []
    dataset_counts: dict[str, int] = {}
    domain_counts: Counter[str] = Counter()

    for dataset, spec in specs.items():
        path = _dataset_path(dataset, public_dir, synthetic_dir)
        if not path.exists():
            errors.append(_message("error", "dataset_file_missing", f"Missing dataset file: {path}", dataset))
            continue
        try:
            tasks = load_tasks_from_jsonl(path)
        except Exception as exc:
            errors.append(_message("error", "dataset_parse_failed", f"{type(exc).__name__}: {exc}", dataset))
            continue
        repaired: list[TaskRecord] = []
        prompts: list[str] = []
        for task in tasks:
            enriched = enrich_task_metadata(task)
            if enriched.metadata != task.metadata:
                fixed_task_ids.append(task.task_id)
            task_errors, task_warnings = _validate_task(enriched)
            errors.extend(task_errors)
            warnings.extend(task_warnings)
            prompts.append(re.sub(r"\s+", " ", enriched.prompt).strip().lower())
            repaired.append(enriched)
            all_tasks.append(enriched)
            domain_counts[enriched.domain] += 1
        if dataset in {"constraint_miniset", "local_mas_safety"} and len(prompts) != len(set(prompts)):
            errors.append(_message("error", "synthetic_duplicate_prompt", "Synthetic dataset contains duplicate prompts", dataset))
        if dataset == "local_mas_safety":
            label_counts = Counter(task.gold_answer for task in repaired)
            if label_counts.get("safe") != 8 or label_counts.get("unsafe") != 8:
                errors.append(_message("error", "local_mas_safety_balance", f"Expected safe=8 and unsafe=8, got {dict(label_counts)}", dataset))
        dataset_counts[dataset] = len(repaired)
        if repair:
            save_tasks_to_jsonl(repaired, path)

    task_ids = [task.task_id for task in all_tasks]
    duplicate_ids = sorted(task_id for task_id, count in Counter(task_ids).items() if count > 1)
    for task_id in duplicate_ids:
        errors.append(_message("error", "global_duplicate_task_id", "task_id must be globally unique", task_id=task_id))

    manifest = _load_json(manifest_dir / "main_manifest.json")
    readiness = _load_json(manifest_dir / "public_dataset_readiness.json")
    quality = _load_json(manifest_dir / "task_quality_report.json")
    if manifest:
        if manifest.get("total_tasks") != len(all_tasks):
            errors.append(_message("error", "manifest_total_mismatch", f"manifest total_tasks={manifest.get('total_tasks')} actual={len(all_tasks)}"))
        if manifest.get("dataset_counts") != dataset_counts:
            errors.append(_message("error", "manifest_counts_mismatch", "manifest dataset_counts do not match processed files"))
    else:
        errors.append(_message("error", "manifest_missing", "main_manifest.json is missing"))
    if readiness:
        missing = readiness.get("missing", [])
        if missing:
            errors.append(_message("error", "readiness_missing", f"public_dataset_readiness reports missing={missing}"))
        for dataset in [name for name in specs if name not in {"constraint_miniset", "local_mas_safety"}]:
            record = readiness.get("datasets", {}).get(dataset, {})
            actual = dataset_counts.get(dataset, 0)
            if record.get("count") != actual or record.get("status") != "ready":
                errors.append(_message("error", "readiness_count_mismatch", f"readiness for {dataset} does not match processed count {actual}", dataset))
    else:
        errors.append(_message("error", "readiness_missing_file", "public_dataset_readiness.json is missing"))
    if quality:
        if quality.get("overall_status") not in {"pass", "ready"}:
            errors.append(_message("error", "quality_status_not_ready", f"task_quality_report overall_status={quality.get('overall_status')}"))
    else:
        errors.append(_message("error", "quality_report_missing", "task_quality_report.json is missing"))

    return {
        "total_tasks": len(all_tasks),
        "dataset_counts": dataset_counts,
        "domain_counts": dict(sorted(domain_counts.items())),
        "fixed_task_ids": sorted(set(fixed_task_ids)),
        "warnings": warnings,
        "errors": errors,
        "can_enter_stage_a": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and optionally repair final dataset consistency metadata.")
    parser.add_argument("--processed-public-dir", default="data/processed/public")
    parser.add_argument("--synthetic-dir", default="data/processed/synthetic")
    parser.add_argument("--manifest-dir", default="data/manifests")
    parser.add_argument("--report-path", default="data/manifests/final_dataset_consistency_report.json")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = repair_and_validate(
        Path(args.processed_public_dir),
        Path(args.synthetic_dir),
        Path(args.manifest_dir),
        repair=args.repair,
    )
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = args.report_path
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"total_tasks: {report['total_tasks']}")
        print(f"dataset_counts: {report['dataset_counts']}")
        print(f"domain_counts: {report['domain_counts']}")
        print(f"fixed_task_ids: {len(report['fixed_task_ids'])}")
        print(f"errors: {len(report['errors'])}")
        print(f"warnings: {len(report['warnings'])}")
        print(f"can_enter_stage_a: {report['can_enter_stage_a']}")
    return 0 if report["can_enter_stage_a"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
