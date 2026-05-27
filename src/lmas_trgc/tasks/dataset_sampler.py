from __future__ import annotations

import random
from dataclasses import dataclass

from lmas_trgc.tasks.registry import DatasetSpec
from lmas_trgc.tasks.schema import TaskRecord


def sample_records(records: list[TaskRecord], limit: int) -> list[TaskRecord]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return records[:limit]


@dataclass(frozen=True)
class MainTaskSelectionResult:
    selected_tasks: list[TaskRecord]
    missing_datasets: list[str]


def deterministic_sample(tasks: list[TaskRecord], n: int, seed: int = 20260527) -> list[TaskRecord]:
    if n < 0:
        raise ValueError("n must be non-negative")
    ordered = sorted(tasks, key=lambda task: task.task_id)
    if len(ordered) <= n:
        return list(ordered)
    rng = random.Random(seed)
    shuffled = list(ordered)
    rng.shuffle(shuffled)
    return sorted(shuffled[:n], key=lambda task: task.task_id)


def build_main_task_selection(
    all_tasks_by_dataset: dict[str, list[TaskRecord]],
    specs: dict[str, DatasetSpec],
) -> MainTaskSelectionResult:
    selected: list[TaskRecord] = []
    missing: list[str] = []
    for dataset_name, spec in specs.items():
        tasks = all_tasks_by_dataset.get(dataset_name, [])
        if not tasks:
            missing.append(dataset_name)
            continue
        if spec.source_type == "synthetic" and len(tasks) < spec.target_main_count:
            raise ValueError(
                f"Synthetic dataset {dataset_name!r} has {len(tasks)} tasks; "
                f"requires at least {spec.target_main_count}."
            )
        selected.extend(deterministic_sample(tasks, spec.target_main_count))
    return MainTaskSelectionResult(
        selected_tasks=selected,
        missing_datasets=missing,
    )
