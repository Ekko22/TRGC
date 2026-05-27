from __future__ import annotations

from lmas_trgc.tasks.schema import TaskRecord


def sample_records(records: list[TaskRecord], limit: int) -> list[TaskRecord]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return records[:limit]
