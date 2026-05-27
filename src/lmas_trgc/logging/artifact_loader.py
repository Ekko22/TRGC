from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lmas_trgc.logging.schemas import (
    MessageEventRecord,
    MetricsRecord,
    RunArtifactManifest,
    RunSummaryRecord,
    TopologyEventRecord,
)


REQUIRED_FILES = {
    "run_summary.json",
    "message_events.jsonl",
    "message_events.csv",
    "topology_events.jsonl",
    "metrics.json",
    "config_snapshot.json",
    "README.md",
    "manifest.json",
}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL in {path} line {line_number}: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"JSONL record must be an object in {path} line {line_number}")
            records.append(item)
    return records


def load_run_summary(run_dir: Path) -> RunSummaryRecord:
    return RunSummaryRecord(**_read_json(Path(run_dir) / "run_summary.json"))


def load_message_events(run_dir: Path) -> list[MessageEventRecord]:
    return [MessageEventRecord(**item) for item in _read_jsonl(Path(run_dir) / "message_events.jsonl")]


def load_topology_events(run_dir: Path) -> list[TopologyEventRecord]:
    return [TopologyEventRecord(**item) for item in _read_jsonl(Path(run_dir) / "topology_events.jsonl")]


def load_metrics(run_dir: Path) -> MetricsRecord:
    return MetricsRecord(**_read_json(Path(run_dir) / "metrics.json"))


def load_manifest(run_dir: Path) -> RunArtifactManifest:
    return RunArtifactManifest(**_read_json(Path(run_dir) / "manifest.json"))


def validate_run_artifact(run_dir: Path) -> bool:
    run_dir = Path(run_dir)
    missing = sorted(name for name in REQUIRED_FILES if not (run_dir / name).exists())
    if missing:
        raise ValueError(f"run artifact is missing required files in {run_dir}: {missing}")

    summary = load_run_summary(run_dir)
    message_events = load_message_events(run_dir)
    topology_events = load_topology_events(run_dir)
    metrics = load_metrics(run_dir)
    manifest = load_manifest(run_dir)

    if summary.run_id != metrics.run_id or summary.run_id != manifest.run_id:
        raise ValueError(
            "run_id mismatch across artifact files: "
            f"summary={summary.run_id}, metrics={metrics.run_id}, manifest={manifest.run_id}"
        )
    if len(message_events) != summary.total_messages:
        raise ValueError(
            f"message_events count {len(message_events)} does not match summary.total_messages {summary.total_messages}"
        )
    if len(topology_events) != summary.total_messages:
        raise ValueError(
            f"topology_events count {len(topology_events)} does not match summary.total_messages {summary.total_messages}"
        )
    return True
