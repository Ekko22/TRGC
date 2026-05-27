from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lmas_trgc.analysis.metrics import compute_metrics_from_run_result
from lmas_trgc.analysis.run_summary import (
    build_message_event_records,
    build_run_summary_record,
    build_topology_event_records,
)
from lmas_trgc.logging.schemas import RunArtifactManifest
from lmas_trgc.runners.single_run import SingleRunResult
from lmas_trgc.tasks.schema import TaskPacket


SECRET_KEY_HINTS = ("key", "token", "secret", "credential", "password")


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    return value


def _sanitize_config(value: Any, key_name: str = "") -> Any:
    if any(hint in key_name.lower() for hint in SECRET_KEY_HINTS):
        return "REDACTED"
    if isinstance(value, dict):
        return {str(key): _sanitize_config(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_config(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_config(item) for item in value]
    return value


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_to_plain(value), ensure_ascii=False, sort_keys=True)
    return value


class RunArtifactWriter:
    def __init__(self, output_root: str | Path, stage_name: str = "stage_b", overwrite: bool = False) -> None:
        self.output_root = Path(output_root)
        self.stage_name = stage_name
        self.overwrite = overwrite

    def make_run_dir(self, run_id: str) -> Path:
        run_dir = self.output_root / self.stage_name / run_id
        if run_dir.exists():
            if not self.overwrite:
                raise FileExistsError(f"run artifact already exists: {run_dir}")
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def write_run_artifact(
        self,
        result: SingleRunResult,
        task_packet: TaskPacket,
        config_snapshot: dict,
    ) -> RunArtifactManifest:
        created_at = _created_at()
        run_dir = self.make_run_dir(result.run_id)

        summary = build_run_summary_record(result, task_packet, created_at=created_at)
        message_events = build_message_event_records(result, result.task_id, result.topology)
        topology_events = build_topology_event_records(result, result.task_id, result.topology)
        metrics = compute_metrics_from_run_result(
            result,
            task_id=result.task_id,
            topology=result.topology,
            attack_type=result.attack_type,
            defense_name=result.defense_name,
        )

        files = {
            "run_summary": "run_summary.json",
            "message_events_jsonl": "message_events.jsonl",
            "message_events_csv": "message_events.csv",
            "topology_events_jsonl": "topology_events.jsonl",
            "metrics": "metrics.json",
            "config_snapshot": "config_snapshot.json",
            "readme": "README.md",
            "manifest": "manifest.json",
        }

        self.write_json(run_dir / files["run_summary"], summary)
        self.write_jsonl(run_dir / files["message_events_jsonl"], message_events)
        self.write_csv(run_dir / files["message_events_csv"], message_events)
        self.write_jsonl(run_dir / files["topology_events_jsonl"], topology_events)
        self.write_json(run_dir / files["metrics"], metrics)
        self.write_json(run_dir / files["config_snapshot"], _sanitize_config(config_snapshot))
        self.write_readme(run_dir / files["readme"], summary, metrics)

        manifest = RunArtifactManifest(
            run_id=result.run_id,
            artifact_dir=str(run_dir),
            files=files,
            created_at=created_at,
            metadata={"stage_name": self.stage_name},
        )
        self.write_json(run_dir / files["manifest"], manifest)
        return manifest

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(_to_plain(data), fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    def write_jsonl(self, path: Path, records: list[Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(_to_plain(record), ensure_ascii=False, sort_keys=True))
                fh.write("\n")

    def write_csv(self, path: Path, records: list[Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [_to_plain(record) for record in records]
        fieldnames = list(rows[0]) if rows else []
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            if fieldnames:
                writer.writeheader()
                for row in rows:
                    writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})

    def write_readme(self, path: Path, summary: Any, metrics: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# LMAS-TRGC Run Artifact",
            "",
            f"- run_id: `{summary.run_id}`",
            f"- task_id: `{summary.task_id}`",
            f"- topology: `{summary.topology}`",
            f"- attack: `{summary.attack_type}`",
            f"- defense: `{summary.defense_name}`",
            f"- total_messages: `{summary.total_messages}`",
            f"- attacked_messages: `{summary.attacked_messages}`",
            f"- blocked_messages: `{summary.blocked_messages}`",
            f"- delivery_rate: `{metrics.delivery_rate:.4f}`",
            f"- block_rate: `{metrics.block_rate:.4f}`",
            "",
            "This artifact stores structured run metadata, event records, and metrics only. "
            "It does not store full prompts, final context text, API keys, or raw LLM responses.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
