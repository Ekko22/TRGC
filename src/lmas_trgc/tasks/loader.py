from __future__ import annotations

import json
from pathlib import Path

import orjson

from lmas_trgc.tasks.registry import DatasetSpec
from lmas_trgc.tasks.schema import TaskRecord


def load_manifest_records(path: str | Path) -> list[TaskRecord]:
    raise FileNotFoundError(f"Task manifest is not available yet: {path}")


def load_tasks_from_jsonl(path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            try:
                tasks.append(TaskRecord(**raw))
            except Exception as exc:
                raise ValueError(f"Invalid TaskRecord at {path}:{line_number}: {exc}") from exc
    return tasks


def save_tasks_to_jsonl(tasks: list[TaskRecord], path: Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as fh:
        for task in tasks:
            fh.write(orjson.dumps(task.model_dump(), option=orjson.OPT_APPEND_NEWLINE))


def load_local_dataset(spec: DatasetSpec, base_dir: Path) -> list[TaskRecord]:
    if not spec.local_path:
        return []
    path = Path(spec.local_path)
    if not path.is_absolute():
        path = base_dir / path
    if not path.exists():
        return []
    return load_tasks_from_jsonl(path)


def load_hf_dataset_stub(spec: DatasetSpec, allow_download: bool = False) -> list[TaskRecord]:
    if not allow_download:
        return []
    raise NotImplementedError(
        f"HuggingFace loading for {spec.name!r} is intentionally disabled in Step 3; "
        "dataset download support must be implemented in a later controlled step."
    )


def load_dataset_tasks(
    spec: DatasetSpec,
    base_dir: Path,
    allow_download: bool = False,
) -> list[TaskRecord]:
    if spec.source_type in {"local_jsonl", "synthetic"}:
        return load_local_dataset(spec, base_dir)
    if spec.source_type == "hf":
        return load_hf_dataset_stub(spec, allow_download=allow_download)
    raise ValueError(f"Unsupported dataset source_type: {spec.source_type}")
