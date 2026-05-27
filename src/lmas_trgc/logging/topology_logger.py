from __future__ import annotations

import csv
from pathlib import Path


class TopologyLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = ["run_id", "topology", "node", "fanout_count", "critical_nodes_reachable"]

    def append(self, row: dict) -> None:
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.fieldnames)
            if not exists:
                writer.writeheader()
            writer.writerow({field: row.get(field, "") for field in self.fieldnames})
