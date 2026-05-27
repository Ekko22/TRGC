from __future__ import annotations

from pathlib import Path

from lmas_trgc.tasks.schema import TaskRecord


def load_manifest_records(path: str | Path) -> list[TaskRecord]:
    raise FileNotFoundError(f"Task manifest is not available yet: {path}")
