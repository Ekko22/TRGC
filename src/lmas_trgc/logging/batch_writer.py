from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECRET_KEY_HINTS = ("api_key", "token", "secret", "credential", "password", "prompt")


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize(value: Any, key_name: str = "") -> Any:
    if any(hint in key_name.lower() for hint in SECRET_KEY_HINTS):
        return "REDACTED"
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        redacted_index = 0
        for key, item in value.items():
            key_text = str(key)
            if any(hint in key_text.lower() for hint in SECRET_KEY_HINTS):
                redacted_index += 1
                sanitized[f"redacted_field_{redacted_index}"] = "REDACTED"
            else:
                sanitized[key_text] = _sanitize(item, key_text)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    return value


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


class StageBBatchWriter:
    def __init__(self, output_root: str | Path, overwrite: bool = False) -> None:
        self.output_root = Path(output_root)
        self.overwrite = overwrite

    def make_batch_dir(self, batch_id: str) -> Path:
        batch_dir = self.output_root / "stage_b_batches" / batch_id
        if batch_dir.exists():
            if not self.overwrite:
                raise FileExistsError(f"batch artifact already exists: {batch_dir}")
            shutil.rmtree(batch_dir)
        batch_dir.mkdir(parents=True, exist_ok=False)
        return batch_dir

    def write_run_index(self, batch_dir: Path, run_records: list[dict]) -> Path:
        path = Path(batch_dir) / "run_index.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for record in run_records:
                fh.write(json.dumps(_sanitize(record), ensure_ascii=False, sort_keys=True))
                fh.write("\n")
        return path

    def write_batch_summary(self, batch_dir: Path, summary: dict) -> Path:
        path = Path(batch_dir) / "batch_summary.json"
        path.write_text(json.dumps(_sanitize(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def write_aggregate_metrics(self, batch_dir: Path, aggregate: dict, rows: list[dict]) -> tuple[Path, Path]:
        json_path = Path(batch_dir) / "aggregate_metrics.json"
        csv_path = Path(batch_dir) / "aggregate_metrics.csv"
        payload = {"aggregate": _sanitize(aggregate), "rows": _sanitize(rows)}
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        fieldnames = list(rows[0]) if rows else [
            "run_id",
            "task_id",
            "topology",
            "attack_type",
            "defense_name",
            "total_messages",
            "attacked_messages",
            "blocked_messages",
            "attack_injection_rate",
            "block_rate",
            "critical_node_reach_rate",
            "propagation_depth_proxy",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: _csv_value(row.get(field, "")) for field in fieldnames})
        return json_path, csv_path

    def write_manifest(self, batch_dir: Path, files: dict, metadata: dict) -> Path:
        path = Path(batch_dir) / "manifest.json"
        payload = {
            "schema_version": "1.0",
            "created_at": _created_at(),
            "files": files,
            "metadata": _sanitize(metadata),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def write_readme(self, batch_dir: Path, summary: dict) -> Path:
        path = Path(batch_dir) / "README.md"
        lines = [
            "# LMAS-TRGC Stage-B Batch Artifact",
            "",
            f"- batch_id: `{summary.get('batch_id')}`",
            f"- total_runs: `{summary.get('total_runs')}`",
            f"- successful_runs: `{summary.get('successful_runs')}`",
            f"- failed_runs: `{summary.get('failed_runs')}`",
            "",
            "This batch artifact indexes Stage-B run artifacts and aggregate metrics. "
            "It does not store sensitive configuration values, final context text, or attack payload text.",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
