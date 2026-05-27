from __future__ import annotations

import csv
from pathlib import Path


class RunLogger:
    """Append-only CSV logger kept for compatibility.

    Stage-B and later structured artifacts should use RunArtifactWriter.
    """

    def __init__(self, path: str | Path, fieldnames: list[str] | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = fieldnames or ["run_id", "stage", "topology", "attack_condition", "defense_method", "status"]

    def append(self, row: dict) -> None:
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.fieldnames)
            if not exists:
                writer.writeheader()
            writer.writerow({field: row.get(field, "") for field in self.fieldnames})
