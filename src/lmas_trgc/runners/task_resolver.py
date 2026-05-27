from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from lmas_trgc.tasks.dataset_sampler import deterministic_sample
from lmas_trgc.tasks.loader import load_tasks_from_jsonl
from lmas_trgc.tasks.local_synthetic import generate_constraint_miniset, generate_local_mas_safety_set
from lmas_trgc.tasks.manifest import load_task_manifest
from lmas_trgc.tasks.registry import get_dataset_spec
from lmas_trgc.tasks.schema import TaskRecord


SYNTHETIC_DATASETS = {"constraint_miniset", "local_mas_safety"}


class TaskResolverConfig(BaseModel):
    mode: str
    datasets: list[str]
    task_limit_per_dataset: int | None = None
    synthetic_count_per_dataset: int = 16
    processed_root: str = "data/processed"
    manifest_path: str | None = None
    seed: int = 20260527

    @field_validator("mode")
    @classmethod
    def _valid_mode(cls, value: str) -> str:
        if value not in {"synthetic", "processed", "manifest"}:
            raise ValueError("mode must be synthetic, processed, or manifest")
        return value

    @field_validator("datasets")
    @classmethod
    def _datasets_nonempty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("datasets must not be empty")
        return value


def _synthetic_tasks(dataset: str, count: int) -> list[TaskRecord]:
    if dataset == "constraint_miniset":
        return generate_constraint_miniset(count)
    if dataset == "local_mas_safety":
        return generate_local_mas_safety_set(count)
    raise ValueError(f"synthetic mode only supports {sorted(SYNTHETIC_DATASETS)}, got: {dataset}")


def load_processed_tasks_by_dataset(dataset: str, processed_root: Path) -> list[TaskRecord]:
    spec = get_dataset_spec(dataset)
    subdir = "synthetic" if spec.source_type == "synthetic" else "public"
    path = Path(processed_root) / subdir / f"{dataset}.jsonl"
    if not path.exists():
        raise ValueError(f"Processed dataset {dataset!r} is missing at {path}")
    return load_tasks_from_jsonl(path)


class TaskResolver:
    def resolve(self, config: TaskResolverConfig) -> list[TaskRecord]:
        if config.mode == "synthetic":
            return self._resolve_synthetic(config)
        if config.mode == "processed":
            return self._resolve_processed(config)
        if config.mode == "manifest":
            return self._resolve_manifest(config)
        raise ValueError(f"Unsupported task resolver mode: {config.mode}")

    def _resolve_synthetic(self, config: TaskResolverConfig) -> list[TaskRecord]:
        tasks: list[TaskRecord] = []
        for dataset in config.datasets:
            if dataset not in SYNTHETIC_DATASETS:
                raise ValueError(f"synthetic mode does not support public dataset {dataset!r}")
            generated = sorted(
                _synthetic_tasks(dataset, config.synthetic_count_per_dataset),
                key=lambda task: task.task_id,
            )
            if config.task_limit_per_dataset is not None:
                generated = generated[: config.task_limit_per_dataset]
            tasks.extend(generated)
        return tasks

    def _resolve_processed(self, config: TaskResolverConfig) -> list[TaskRecord]:
        tasks: list[TaskRecord] = []
        for dataset in config.datasets:
            loaded = load_processed_tasks_by_dataset(dataset, Path(config.processed_root))
            if config.task_limit_per_dataset is not None:
                loaded = deterministic_sample(loaded, config.task_limit_per_dataset, seed=config.seed)
            tasks.extend(sorted(loaded, key=lambda task: task.task_id))
        return tasks

    def _resolve_manifest(self, config: TaskResolverConfig) -> list[TaskRecord]:
        if not config.manifest_path:
            raise ValueError("manifest mode requires manifest_path")
        manifest = load_task_manifest(Path(config.manifest_path))
        selected_entries = [entry for entry in manifest.entries if entry.dataset in set(config.datasets)]
        tasks_by_dataset: dict[str, dict[str, TaskRecord]] = {}
        for dataset in sorted({entry.dataset for entry in selected_entries}):
            loaded = load_processed_tasks_by_dataset(dataset, Path(config.processed_root))
            tasks_by_dataset[dataset] = {task.task_id: task for task in loaded}

        resolved: list[TaskRecord] = []
        per_dataset_counts: dict[str, int] = {dataset: 0 for dataset in config.datasets}
        for entry in selected_entries:
            if (
                config.task_limit_per_dataset is not None
                and per_dataset_counts.get(entry.dataset, 0) >= config.task_limit_per_dataset
            ):
                continue
            task = tasks_by_dataset.get(entry.dataset, {}).get(entry.task_id)
            if task is None:
                raise ValueError(
                    f"Manifest entry {entry.task_id!r} for dataset {entry.dataset!r} "
                    "was not found in processed JSONL"
                )
            resolved.append(task)
            per_dataset_counts[entry.dataset] = per_dataset_counts.get(entry.dataset, 0) + 1
        return resolved
