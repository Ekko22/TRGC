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


def load_raw_json_or_jsonl(path: Path) -> list[dict]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        rows: list[dict] = []
        with source.open("r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at {source}:{line_number}: {exc}") from exc
                if not isinstance(item, dict):
                    raise ValueError(f"JSONL row must be an object at {source}:{line_number}")
                rows.append(item)
        return rows
    if suffix == ".json":
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {source}: {exc}") from exc
        if isinstance(raw, list):
            if not all(isinstance(item, dict) for item in raw):
                raise ValueError(f"JSON list must contain objects: {source}")
            return raw
        if isinstance(raw, dict) and isinstance(raw.get("data"), list):
            data = raw["data"]
            if not all(isinstance(item, dict) for item in data):
                raise ValueError(f"JSON data list must contain objects: {source}")
            return data
        raise ValueError(f"Unsupported JSON structure in {source}; expected list or dict with data list")
    raise ValueError(f"Unsupported raw dataset extension for {source}; expected .json or .jsonl")


def save_tasks_to_jsonl(tasks: list[TaskRecord], path: Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as fh:
        for task in tasks:
            fh.write(orjson.dumps(task.model_dump(), option=orjson.OPT_APPEND_NEWLINE))


def save_public_tasks(dataset: str, tasks: list[TaskRecord], output_dir: Path) -> Path:
    target = Path(output_dir) / f"{dataset}.jsonl"
    save_tasks_to_jsonl(tasks, target)
    return target


def load_public_jsonl_dataset(dataset: str, processed_dir: Path) -> list[TaskRecord]:
    path = Path(processed_dir) / f"{dataset}.jsonl"
    if not path.exists():
        return []
    return load_tasks_from_jsonl(path)


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
    local_tasks = load_local_dataset(spec, base_dir)
    if local_tasks:
        return local_tasks
    if spec.source_type in {"local_jsonl", "synthetic"}:
        return []
    if spec.source_type == "hf":
        return load_hf_dataset_stub(spec, allow_download=allow_download)
    raise ValueError(f"Unsupported dataset source_type: {spec.source_type}")
