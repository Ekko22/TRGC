from __future__ import annotations

from collections import Counter
from pathlib import Path

import orjson
from pydantic import BaseModel, Field

from lmas_trgc.core.ids import stable_hash
from lmas_trgc.tasks.schema import TaskManifestEntry, TaskRecord


class TaskManifest(BaseModel):
    manifest_id: str
    created_at: str
    total_tasks: int
    dataset_counts: dict[str, int]
    entries: list[TaskManifestEntry]
    missing_datasets: list[str] = Field(default_factory=list)


def build_task_manifest(
    tasks: list[TaskRecord],
    manifest_id: str,
    missing_datasets: list[str] | None = None,
) -> TaskManifest:
    entries = [
        TaskManifestEntry(
            manifest_id=manifest_id,
            task_id=task.task_id,
            dataset=task.dataset,
            domain=task.domain,
            split=task.split,
            selected=True,
            selection_reason="deterministic_main_selection",
            original_index=index,
            metadata={
                "input_chars": len(task.prompt),
                "source": task.source,
                "entry_hash": stable_hash(task.task_id, task.dataset, task.domain, length=12),
            },
        )
        for index, task in enumerate(sorted(tasks, key=lambda item: (item.dataset, item.task_id)))
    ]
    counts = dict(sorted(Counter(entry.dataset for entry in entries).items()))
    return TaskManifest(
        manifest_id=manifest_id,
        created_at="2026-05-27T00:00:00+08:00",
        total_tasks=len(entries),
        dataset_counts=counts,
        entries=entries,
        missing_datasets=missing_datasets or [],
    )


def save_task_manifest(manifest: TaskManifest, path: Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(orjson.dumps(manifest.model_dump(), option=orjson.OPT_INDENT_2))


def load_task_manifest(path: Path) -> TaskManifest:
    try:
        raw = orjson.loads(Path(path).read_bytes())
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"Invalid task manifest JSON: {path}: {exc}") from exc
    return TaskManifest(**raw)


def validate_manifest_counts(manifest: TaskManifest, expected_counts: dict[str, int]) -> None:
    for dataset, expected in expected_counts.items():
        actual = manifest.dataset_counts.get(dataset, 0)
        if actual != expected:
            raise ValueError(f"Manifest count mismatch for {dataset}: expected {expected}, got {actual}")
