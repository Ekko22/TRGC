from __future__ import annotations

import csv
from pathlib import Path


MESSAGE_LOG_FIELDS = [
    "run_id",
    "task_id",
    "topology",
    "attack_condition",
    "defense_method",
    "round_id",
    "message_id",
    "parent_message_id",
    "sender",
    "receiver",
    "topology_edge",
    "gate_action",
    "delivered",
    "blocked",
    "downweighted",
    "rerouted_to_sv",
    "sv_called",
    "critical_nodes_reachable",
    "propagation_depth",
    "fanout_count",
]


class MessageLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, row: dict) -> None:
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=MESSAGE_LOG_FIELDS)
            if not exists:
                writer.writeheader()
            writer.writerow({field: row.get(field, "") for field in MESSAGE_LOG_FIELDS})
