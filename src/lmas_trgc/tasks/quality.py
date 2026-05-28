from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.loader import load_tasks_from_jsonl
from lmas_trgc.tasks.manifest import TaskManifest, load_task_manifest
from lmas_trgc.tasks.metadata_enrichment import (
    ANSWER_FORMAT_BY_DATASET,
    ATTACK_TYPES,
    CONSTRAINT_LABELS,
    TARGET_SLOTS_BY_DATASET,
    normalize_numeric_answer,
)
from lmas_trgc.tasks.registry import DatasetSpec, get_default_dataset_specs
from lmas_trgc.tasks.schema import TaskRecord

EXPECTED_TOTAL_TASKS = 104
PUBLIC_DATASETS = ["gsm8k", "prontoqa", "mmlu", "csqa", "svamp", "multiarith", "aqua", "humaneval", "mbpp"]
SYNTHETIC_DATASETS = ["constraint_miniset", "local_mas_safety"]
ACTIVE_DATASETS = [*PUBLIC_DATASETS, *SYNTHETIC_DATASETS]
EXPECTED_DATASET_COUNTS = {dataset: 8 for dataset in PUBLIC_DATASETS} | {
    "constraint_miniset": 16,
    "local_mas_safety": 16,
}
ANSWER_REQUIRED_DATASETS = set(ACTIVE_DATASETS)
POLLUTION_TERMS = ["Injected communication update", "TRGC Notice", "Safety Notice"]
SECRET_TERMS = ["api key", "apikey", "secret key", "DEEPSEEK_API_KEY", "LOCAL_SV_API_KEY"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_for_duplicate_check(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _json_len(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


def _message(level: str, dataset: str | None, code: str, message: str, task_id: str | None = None) -> dict:
    payload = {"level": level, "code": code, "message": message}
    if dataset is not None:
        payload["dataset"] = dataset
    if task_id is not None:
        payload["task_id"] = task_id
    return payload


def _dataset_path(dataset: str, spec: DatasetSpec, public_dir: Path, synthetic_dir: Path) -> Path:
    if dataset in SYNTHETIC_DATASETS:
        return synthetic_dir / f"{dataset}.jsonl"
    return public_dir / f"{dataset}.jsonl"


def _sample_summary(task: TaskRecord) -> dict:
    return {
        "task_id": task.task_id,
        "prompt_chars": len(task.prompt),
        "gold_answer_preview": (task.gold_answer or "")[:80],
        "choices_count": len(task.choices),
        "anchors_count": len(build_task_packet(task).anchors),
        "target_slots_count": len(build_task_packet(task).attack_surface.get("target_slots", [])),
        "metadata_keys": sorted(task.metadata),
    }


def _has_any(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _check_dataset_task(task: TaskRecord, dataset: str) -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    metadata = task.metadata or {}
    if task.dataset != dataset:
        errors.append(_message("error", dataset, "dataset_mismatch", f"Task dataset {task.dataset!r} does not match file {dataset!r}", task.task_id))
    if not task.prompt.strip():
        errors.append(_message("error", dataset, "empty_prompt", "Prompt must not be empty", task.task_id))
    if not task.split.strip():
        errors.append(_message("error", dataset, "empty_split", "Split must not be empty", task.task_id))
    if dataset in ANSWER_REQUIRED_DATASETS and not (task.gold_answer or "").strip():
        errors.append(_message("error", dataset, "missing_gold_answer", "Gold answer is required", task.task_id))
    if len(task.prompt) < 20:
        warnings.append(_message("warning", dataset, "short_prompt", "Prompt is shorter than 20 characters", task.task_id))
    if len(task.prompt) > 8000:
        warnings.append(_message("warning", dataset, "long_prompt", "Prompt is longer than 8000 characters", task.task_id))
    if task.gold_answer and len(task.gold_answer) > 4000:
        warnings.append(_message("warning", dataset, "long_gold_answer", "Gold answer is longer than 4000 characters", task.task_id))
    if _json_len(task.metadata) > 8000:
        warnings.append(_message("warning", dataset, "large_metadata", "Metadata JSON is larger than 8000 characters", task.task_id))
    if dataset in PUBLIC_DATASETS:
        for term in _has_any(task.prompt, POLLUTION_TERMS):
            errors.append(_message("error", dataset, "prompt_pollution", f"Public prompt contains forbidden marker: {term}", task.task_id))
    if dataset in {"mmlu", "csqa", "aqua"} and len(task.choices) < 2:
        errors.append(_message("error", dataset, "choices_too_short", "Multiple-choice task should have at least 2 choices", task.task_id))
    for key in ["judge_type", "answer_format", "task_anchors", "target_slots", "attack_surfaces"]:
        if key not in metadata:
            errors.append(_message("error", dataset, "trgc_metadata_missing", f"Missing TRGC metadata key: {key}", task.task_id))
    for slot in TARGET_SLOTS_BY_DATASET.get(dataset, []):
        if slot not in metadata.get("target_slots", []):
            errors.append(_message("error", dataset, "target_slot_missing", f"Missing target slot: {slot}", task.task_id))
    attack_surfaces = metadata.get("attack_surfaces") if isinstance(metadata.get("attack_surfaces"), dict) else {}
    for attack_type in ATTACK_TYPES:
        if not attack_surfaces.get(attack_type):
            errors.append(_message("error", dataset, "attack_surface_missing", f"Missing attack surface: {attack_type}", task.task_id))
    expected_format = ANSWER_FORMAT_BY_DATASET.get(dataset)
    if expected_format and metadata.get("answer_format") != expected_format:
        errors.append(_message("error", dataset, "answer_format_mismatch", f"Expected {expected_format}, got {metadata.get('answer_format')}", task.task_id))
    if metadata.get("answer_format") == "multiple_choice":
        labels = []
        for choice in task.choices:
            match = re.match(r"^\s*([A-Z])(?:[\).:]|\s)", choice)
            if match:
                labels.append(match.group(1))
        if len(labels) != len(set(labels)):
            errors.append(_message("error", dataset, "choice_label_duplicate", "Choice labels must be unique", task.task_id))
        if task.gold_answer not in labels:
            errors.append(_message("error", dataset, "choice_gold_not_in_labels", "gold_answer must be one of the choice labels", task.task_id))
    if metadata.get("answer_format") == "numeric_exact":
        if not task.gold_answer or not re.fullmatch(r"-?\d+(?:\.\d+)?", task.gold_answer):
            errors.append(_message("error", dataset, "numeric_answer_invalid", "numeric_exact gold_answer must be a numeric string", task.task_id))
        raw_answer = metadata.get("raw_answer")
        if dataset == "gsm8k" and isinstance(raw_answer, str) and "####" in raw_answer:
            expected = normalize_numeric_answer(raw_answer.split("####", 1)[1])
            if task.gold_answer != expected:
                errors.append(_message("error", dataset, "numeric_answer_mismatch", f"Expected {expected} from raw_answer delimiter", task.task_id))
    if metadata.get("answer_format") == "code_generation" and "tests" not in metadata:
        errors.append(_message("error", dataset, "code_tests_missing", "code_generation metadata must include tests", task.task_id))
    if metadata.get("answer_format") == "binary_safety" and task.gold_answer not in {"safe", "unsafe"}:
        errors.append(_message("error", dataset, "binary_safety_label_invalid", "gold_answer must be safe or unsafe", task.task_id))
    if metadata.get("answer_format") == "constraint_label" and task.gold_answer not in CONSTRAINT_LABELS:
        errors.append(_message("error", dataset, "constraint_label_invalid", "gold_answer is not a supported constraint label", task.task_id))
    if dataset == "prontoqa":
        if not any(key in metadata for key in ["rule_chain", "reasoning_chain"]):
            errors.append(_message("error", dataset, "prontoqa_metadata_missing", "ProntoQA metadata should include rule_chain or reasoning_chain", task.task_id))
        for key in ["target_property", "attackable_link", "gold_label"]:
            if key not in metadata:
                errors.append(_message("error", dataset, "prontoqa_metadata_missing", f"Missing metadata key: {key}", task.task_id))
    if dataset == "humaneval":
        if "def " not in task.prompt and "function" not in task.prompt.lower():
            warnings.append(_message("warning", dataset, "humaneval_prompt_semantics", "HumanEval prompt lacks obvious function wording", task.task_id))
        if not any(key in task.metadata for key in ["entry_point", "test", "canonical_solution"]):
            errors.append(_message("error", dataset, "humaneval_metadata_missing", "HumanEval metadata should include entry_point, test, or canonical_solution", task.task_id))
    if dataset == "mbpp":
        if not task.prompt.strip():
            errors.append(_message("error", dataset, "mbpp_empty_prompt", "MBPP prompt/text must be non-empty", task.task_id))
        if not any(key in task.metadata for key in ["test_list", "challenge_test_list", "code"]):
            errors.append(_message("error", dataset, "mbpp_metadata_missing", "MBPP metadata should include test_list or code summary", task.task_id))
    if dataset == "constraint_miniset":
        required = ["decisive_gate", "gold_gate_value", "attack_flip_value", "violation_types"]
        for key in required:
            if key not in task.metadata:
                errors.append(_message("error", dataset, "constraint_metadata_missing", f"Missing metadata key: {key}", task.task_id))
    if dataset == "local_mas_safety":
        required = ["allowed_paths", "forbidden_paths", "allowed_actions", "forbidden_actions", "unsafe_target_action"]
        for key in required:
            if key not in task.metadata:
                errors.append(_message("error", dataset, "local_mas_safety_metadata_missing", f"Missing metadata key: {key}", task.task_id))
        if task.gold_answer not in {"safe", "unsafe"}:
            errors.append(_message("error", dataset, "local_mas_safety_gold_answer", "Gold answer must be safe or unsafe", task.task_id))
    return errors, warnings


def audit_dataset_file(dataset: str, spec: DatasetSpec, path: Path) -> tuple[dict, list[TaskRecord]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    tasks: list[TaskRecord] = []
    if not path.exists():
        errors.append(_message("error", dataset, "dataset_file_missing", f"Dataset file missing: {path}"))
        return {
            "exists": False,
            "count": 0,
            "target_count": spec.target_main_count,
            "ready": False,
            "errors": errors,
            "warnings": warnings,
            "sample_summaries": [],
        }, tasks
    try:
        tasks = load_tasks_from_jsonl(path)
    except Exception as exc:
        errors.append(_message("error", dataset, "dataset_parse_failed", f"Failed to load dataset JSONL: {type(exc).__name__}: {exc}"))
        return {
            "exists": True,
            "count": 0,
            "target_count": spec.target_main_count,
            "ready": False,
            "errors": errors,
            "warnings": warnings,
            "sample_summaries": [],
        }, tasks
    seen_ids: set[str] = set()
    prompt_groups: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        if task.task_id in seen_ids:
            errors.append(_message("error", dataset, "duplicate_task_id", "Duplicate task_id within dataset", task.task_id))
        seen_ids.add(task.task_id)
        prompt_groups[normalize_for_duplicate_check(task.prompt)].append(task.task_id)
        task_errors, task_warnings = _check_dataset_task(task, dataset)
        errors.extend(task_errors)
        warnings.extend(task_warnings)
    if len(tasks) < spec.target_main_count:
        errors.append(_message("error", dataset, "insufficient_count", f"Dataset has {len(tasks)} tasks, target is {spec.target_main_count}"))
    for normalized_prompt, task_ids in prompt_groups.items():
        if normalized_prompt and len(task_ids) > 1:
            warnings.append(
                _message(
                    "warning",
                    dataset,
                    "duplicate_prompt",
                    f"Normalized prompt is duplicated {len(task_ids)} times; sample task_ids={task_ids[:5]}",
                )
            )
    if dataset == "local_mas_safety":
        counts = Counter(task.gold_answer for task in tasks)
        if counts.get("safe", 0) == 0 or counts.get("unsafe", 0) == 0:
            errors.append(_message("error", dataset, "local_mas_safety_class_balance", "Both safe and unsafe labels must be present"))
    return {
        "exists": True,
        "count": len(tasks),
        "target_count": spec.target_main_count,
        "ready": not errors and len(tasks) >= spec.target_main_count,
        "errors": errors,
        "warnings": warnings,
        "sample_summaries": [_sample_summary(task) for task in tasks[:2]],
    }, tasks


def _load_manifest_raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_manifest(path: Path, tasks_by_dataset: dict[str, dict[str, TaskRecord]]) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    raw: dict[str, Any] = {}
    manifest: TaskManifest | None = None
    if not path.exists():
        errors.append(_message("error", None, "manifest_missing", f"Manifest missing: {path}"))
        return {"exists": False, "errors": errors, "warnings": warnings}
    try:
        raw = _load_manifest_raw(path)
        manifest = TaskManifest(**raw)
    except Exception as exc:
        errors.append(_message("error", None, "manifest_parse_failed", f"Failed to parse manifest: {type(exc).__name__}: {exc}"))
        return {"exists": True, "errors": errors, "warnings": warnings}
    if manifest.total_tasks != EXPECTED_TOTAL_TASKS:
        errors.append(_message("error", None, "manifest_total_mismatch", f"Expected {EXPECTED_TOTAL_TASKS}, got {manifest.total_tasks}"))
    if manifest.dataset_counts != EXPECTED_DATASET_COUNTS:
        errors.append(_message("error", None, "manifest_count_mismatch", f"Expected counts {EXPECTED_DATASET_COUNTS}, got {manifest.dataset_counts}"))
    if manifest.missing_datasets:
        errors.append(_message("error", None, "manifest_missing_datasets", f"Manifest has missing_datasets={manifest.missing_datasets}"))
    if len(manifest.entries) != EXPECTED_TOTAL_TASKS:
        errors.append(_message("error", None, "manifest_entry_count_mismatch", f"Expected {EXPECTED_TOTAL_TASKS} entries, got {len(manifest.entries)}"))
    manifest_text = json.dumps(raw, ensure_ascii=False)
    for forbidden in ["prompt", "content", "final_context", "final_output"]:
        if f'"{forbidden}"' in manifest_text:
            errors.append(_message("error", None, "manifest_forbidden_field", f"Manifest contains forbidden field: {forbidden}"))
    for term in SECRET_TERMS:
        if term.lower() in manifest_text.lower():
            errors.append(_message("error", None, "manifest_secret_term", f"Manifest contains secret-like term: {term}"))
    selected_counts: Counter[str] = Counter()
    for entry in manifest.entries:
        if entry.dataset not in ACTIVE_DATASETS:
            errors.append(_message("error", entry.dataset, "manifest_unknown_dataset", "Manifest dataset is not in active pool", entry.task_id))
        if not entry.selected:
            errors.append(_message("error", entry.dataset, "manifest_entry_not_selected", "Manifest entry selected must be true", entry.task_id))
        selected_counts[entry.dataset] += 1
        if entry.task_id not in tasks_by_dataset.get(entry.dataset, {}):
            errors.append(_message("error", entry.dataset, "manifest_task_missing", "Manifest task_id not found in processed JSONL", entry.task_id))
    for dataset, count in selected_counts.items():
        target = EXPECTED_DATASET_COUNTS.get(dataset)
        if target is not None and count > target:
            errors.append(_message("error", dataset, "manifest_dataset_over_selected", f"Selected {count}, target is {target}"))
    return {
        "exists": True,
        "manifest_id": manifest.manifest_id,
        "total_tasks": manifest.total_tasks,
        "dataset_counts": manifest.dataset_counts,
        "missing_datasets": manifest.missing_datasets,
        "entries_count": len(manifest.entries),
        "errors": errors,
        "warnings": warnings,
    }


def audit_anchors(tasks_by_dataset: dict[str, dict[str, TaskRecord]], manifest_path: Path) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    checked = 0
    if not manifest_path.exists():
        errors.append(_message("error", None, "anchor_manifest_missing", f"Manifest missing: {manifest_path}"))
        return {"checked_tasks": checked, "errors": errors, "warnings": warnings}
    try:
        manifest = load_task_manifest(manifest_path)
    except Exception as exc:
        errors.append(_message("error", None, "anchor_manifest_parse_failed", f"Failed to parse manifest: {exc}"))
        return {"checked_tasks": checked, "errors": errors, "warnings": warnings}
    for entry in manifest.entries:
        task = tasks_by_dataset.get(entry.dataset, {}).get(entry.task_id)
        if task is None:
            continue
        checked += 1
        try:
            packet = build_task_packet(task)
        except Exception as exc:
            errors.append(_message("error", entry.dataset, "task_packet_failed", f"build_task_packet failed: {type(exc).__name__}: {exc}", entry.task_id))
            continue
        if "metric" not in packet.answer_contract:
            errors.append(_message("error", entry.dataset, "answer_contract_missing_metric", "answer_contract missing metric", entry.task_id))
        if "violation_types" not in packet.safety_contract:
            errors.append(_message("error", entry.dataset, "safety_contract_missing_violation_types", "safety_contract missing violation_types", entry.task_id))
        if "target_slots" not in packet.attack_surface:
            errors.append(_message("error", entry.dataset, "attack_surface_missing_target_slots", "attack_surface missing target_slots", entry.task_id))
        anchor_types = {anchor.anchor_type for anchor in packet.anchors}
        if entry.dataset in {"gsm8k", "svamp", "multiarith"} and not (anchor_types & {"numeric", "expected_answer"}):
            warnings.append(_message("warning", entry.dataset, "math_anchor_missing", "Math task has no numeric or expected_answer anchor", entry.task_id))
        if entry.dataset in {"mmlu", "csqa", "aqua"} and not (anchor_types & {"entity", "expected_answer"}):
            warnings.append(_message("warning", entry.dataset, "choice_anchor_missing", "Choice task has no entity or expected_answer anchor", entry.task_id))
        if entry.dataset in {"humaneval", "mbpp"} and not (anchor_types & {"code_spec", "expected_answer"}):
            warnings.append(_message("warning", entry.dataset, "code_anchor_missing", "Code task has no code_spec or expected_answer anchor", entry.task_id))
        if entry.dataset == "constraint_miniset" and not (anchor_types & {"constraint", "permission", "forbidden_action"}):
            errors.append(_message("error", entry.dataset, "synthetic_constraint_anchor_missing", "Synthetic constraint task lacks required anchor type", entry.task_id))
        if entry.dataset == "local_mas_safety" and not (anchor_types & {"safety_requirement", "forbidden_action", "allowed_action"}):
            errors.append(_message("error", entry.dataset, "synthetic_safety_anchor_missing", "Synthetic safety task lacks required anchor type", entry.task_id))
    return {"checked_tasks": checked, "errors": errors, "warnings": warnings}


def audit_task_quality(
    processed_public_dir: Path,
    synthetic_dir: Path,
    manifest_path: Path,
) -> dict:
    specs = get_default_dataset_specs()
    dataset_reports: dict[str, dict] = {}
    tasks_by_dataset: dict[str, dict[str, TaskRecord]] = {}
    errors: list[dict] = []
    warnings: list[dict] = []
    for dataset in ACTIVE_DATASETS:
        spec = specs[dataset]
        report, tasks = audit_dataset_file(dataset, spec, _dataset_path(dataset, spec, processed_public_dir, synthetic_dir))
        dataset_reports[dataset] = report
        tasks_by_dataset[dataset] = {task.task_id: task for task in tasks}
        errors.extend(report["errors"])
        warnings.extend(report["warnings"])
    manifest_report = audit_manifest(manifest_path, tasks_by_dataset)
    errors.extend(manifest_report["errors"])
    warnings.extend(manifest_report["warnings"])
    anchor_report = audit_anchors(tasks_by_dataset, manifest_path)
    errors.extend(anchor_report["errors"])
    warnings.extend(anchor_report["warnings"])
    overall_status = "fail" if errors else ("warning" if warnings else "pass")
    manifest_total = manifest_report.get("total_tasks", 0)
    summary = {
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "datasets_ready": [dataset for dataset, report in dataset_reports.items() if report["ready"]],
        "datasets_failed": [dataset for dataset, report in dataset_reports.items() if not report["ready"]],
        "can_run_main_manifest": not errors and manifest_total == EXPECTED_TOTAL_TASKS,
    }
    return {
        "created_at": _now_iso(),
        "active_dataset_count": len(ACTIVE_DATASETS),
        "expected_total_tasks": EXPECTED_TOTAL_TASKS,
        "manifest_total_tasks": manifest_total,
        "overall_status": overall_status,
        "dataset_reports": dataset_reports,
        "manifest_report": manifest_report,
        "anchor_report": anchor_report,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def write_json_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _format_messages(messages: list[dict]) -> str:
    if not messages:
        return "- none\n"
    return "\n".join(
        f"- `{item.get('code')}`"
        f"{' [' + item.get('dataset', '') + ']' if item.get('dataset') else ''}"
        f"{' task=' + item.get('task_id', '') if item.get('task_id') else ''}: {item.get('message')}"
        for item in messages[:50]
    ) + ("\n- ... truncated\n" if len(messages) > 50 else "\n")


def write_markdown_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = report["overall_status"]
    if status == "pass":
        decision = "The 104-task manifest is accepted for the next experimental stage."
    elif status == "warning":
        decision = "The manifest is usable for pilot runs, but warnings should be reviewed before main experiments."
    else:
        decision = "The manifest is not accepted; listed errors must be fixed before running real experiments."
    lines = [
        "# Data Quality Audit",
        "",
        "## Date time",
        "",
        report["created_at"],
        "",
        "## Scope",
        "",
        f"- Active datasets: {len(PUBLIC_DATASETS)} public datasets and {len(SYNTHETIC_DATASETS)} synthetic datasets.",
        "- Expected manifest size: 104 tasks.",
        "- Full prompts, code bodies, tests, and data rows are intentionally omitted.",
        "",
        "## Overall Status",
        "",
        f"- overall_status: `{status}`",
        f"- total_errors: {report['summary']['total_errors']}",
        f"- total_warnings: {report['summary']['total_warnings']}",
        "",
        "## Dataset Counts",
        "",
        "| Dataset | Count | Target | Ready | Errors | Warnings |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for dataset, item in report["dataset_reports"].items():
        lines.append(
            f"| {dataset} | {item['count']} | {item['target_count']} | {item['ready']} | "
            f"{len(item['errors'])} | {len(item['warnings'])} |"
        )
    lines.extend(
        [
            "",
            "## Manifest Validation",
            "",
            f"- manifest_total_tasks: {report['manifest_total_tasks']}",
            f"- expected_total_tasks: {report['expected_total_tasks']}",
            f"- missing_datasets: {report['manifest_report'].get('missing_datasets', [])}",
            "",
            "## Anchor and Attack Surface Validation",
            "",
            f"- checked_tasks: {report['anchor_report'].get('checked_tasks', 0)}",
            f"- anchor_errors: {len(report['anchor_report'].get('errors', []))}",
            f"- anchor_warnings: {len(report['anchor_report'].get('warnings', []))}",
            "",
            "## Errors",
            "",
            _format_messages(report["errors"]),
            "## Warnings",
            "",
            _format_messages(report["warnings"]),
            "## Sample Summaries",
            "",
        ]
    )
    for dataset, item in report["dataset_reports"].items():
        lines.append(f"### {dataset}")
        lines.append("")
        for sample in item["sample_summaries"]:
            lines.append(
                "- "
                f"task_id=`{sample['task_id']}`, "
                f"prompt_chars={sample['prompt_chars']}, "
                f"gold_answer_preview=`{sample['gold_answer_preview']}`, "
                f"choices_count={sample['choices_count']}, "
                f"anchors_count={sample['anchors_count']}, "
                f"target_slots_count={sample['target_slots_count']}, "
                f"metadata_keys={sample['metadata_keys']}"
            )
        if not item["sample_summaries"]:
            lines.append("- none")
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            decision,
            "",
            "## Git Commit",
            "",
            "commit hash is reported in final execution summary",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
