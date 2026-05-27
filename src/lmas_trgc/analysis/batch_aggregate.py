from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from lmas_trgc.logging.artifact_loader import load_metrics, validate_run_artifact
from lmas_trgc.logging.schemas import MetricsRecord


def load_metrics_from_artifact_dirs(artifact_dirs: list[str | Path]) -> list[MetricsRecord]:
    metrics: list[MetricsRecord] = []
    for artifact_dir in artifact_dirs:
        run_dir = Path(artifact_dir)
        validate_run_artifact(run_dir)
        metrics.append(load_metrics(run_dir))
    return metrics


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_metrics(metrics: list[MetricsRecord]) -> dict:
    return {
        "total_runs": len(metrics),
        "mean_attack_injection_rate": _mean([item.attack_injection_rate for item in metrics]),
        "mean_block_rate": _mean([item.block_rate for item in metrics]),
        "mean_downweight_rate": _mean([item.downweight_rate for item in metrics]),
        "mean_reroute_rate": _mean([item.reroute_rate for item in metrics]),
        "mean_delivery_rate": _mean([item.delivery_rate for item in metrics]),
        "mean_critical_node_reach_rate": _mean([item.critical_node_reach_rate for item in metrics]),
        "mean_propagation_depth_proxy": _mean([float(item.propagation_depth_proxy) for item in metrics]),
        "total_messages": sum(item.total_messages for item in metrics),
        "total_attacked_messages": sum(item.attacked_messages for item in metrics),
        "total_blocked_messages": sum(item.blocked_messages for item in metrics),
        "total_downweighted_messages": sum(item.downweighted_messages for item in metrics),
        "total_rerouted_messages": sum(item.rerouted_messages for item in metrics),
    }


def metrics_to_rows(metrics: list[MetricsRecord]) -> list[dict]:
    return [
        {
            "run_id": item.run_id,
            "task_id": item.task_id,
            "topology": item.topology,
            "attack_type": item.attack_type,
            "defense_name": item.defense_name,
            "total_messages": item.total_messages,
            "attacked_messages": item.attacked_messages,
            "blocked_messages": item.blocked_messages,
            "attack_injection_rate": item.attack_injection_rate,
            "block_rate": item.block_rate,
            "critical_node_reach_rate": item.critical_node_reach_rate,
            "propagation_depth_proxy": item.propagation_depth_proxy,
        }
        for item in metrics
    ]


def group_metrics(metrics: list[MetricsRecord], by: list[str]) -> list[dict]:
    allowed = {"topology", "attack_type", "defense_name"}
    unsupported = [field for field in by if field not in allowed]
    if unsupported:
        raise ValueError(f"Unsupported group-by fields: {unsupported}")
    if not by:
        return []

    groups: dict[tuple[Any, ...], list[MetricsRecord]] = defaultdict(list)
    for item in metrics:
        key = tuple(getattr(item, field) for field in by)
        groups[key].append(item)

    rows: list[dict] = []
    for key in sorted(groups):
        group_items = groups[key]
        row = {field: key[index] for index, field in enumerate(by)}
        row.update(aggregate_metrics(group_items))
        rows.append(row)
    return rows
