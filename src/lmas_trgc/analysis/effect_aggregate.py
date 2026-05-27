from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from lmas_trgc.analysis.standard_metrics import StandardRunMetrics


class EffectAggregate(BaseModel):
    total_runs: int
    valid_for_paper_runs: int
    clean_tsr: float | None
    robust_tsr: float | None
    asr: float | None
    svr: float | None
    benign_drop: float | None
    by_group: list[dict] = Field(default_factory=list)


def _mean_bool(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def aggregate_standard_metrics(metrics: list[StandardRunMetrics]) -> dict:
    clean = [item.clean_success for item in metrics if item.attack_type == "none" and item.clean_success is not None]
    robust = [item.robust_success for item in metrics if item.attack_type != "none" and item.robust_success is not None]
    attack = [item.attack_success for item in metrics if item.attack_type != "none" and item.attack_success is not None]
    safety = [item.safety_violation for item in metrics if item.safety_violation is not None]
    return {
        "total_runs": len(metrics),
        "valid_for_paper_runs": sum(1 for item in metrics if item.valid_for_paper),
        "clean_tsr": _mean_bool(clean),
        "robust_tsr": _mean_bool(robust),
        "asr": _mean_bool(attack),
        "svr": _mean_bool(safety),
        "benign_drop": None,
    }


def group_standard_metrics(metrics: list[StandardRunMetrics], by: list[str]) -> list[dict]:
    allowed = {"topology", "attack_type", "defense_name", "dataset", "domain", "judge_mode", "valid_for_paper"}
    unsupported = [field for field in by if field not in allowed]
    if unsupported:
        raise ValueError(f"Unsupported group-by fields: {unsupported}")
    if not by:
        return []
    grouped: dict[tuple[Any, ...], list[StandardRunMetrics]] = defaultdict(list)
    for item in metrics:
        grouped[tuple(getattr(item, field) for field in by)].append(item)
    rows: list[dict] = []
    for key in sorted(grouped):
        row = {field: key[index] for index, field in enumerate(by)}
        aggregate = aggregate_standard_metrics(grouped[key])
        row.update({"n": aggregate["total_runs"], **aggregate})
        rows.append(row)
    return rows


def compute_benign_drop_by_defense(metrics: list[StandardRunMetrics]) -> list[dict]:
    clean_metrics = [item for item in metrics if item.attack_type == "none" and item.clean_success is not None]
    baseline_values = [item.clean_success for item in clean_metrics if item.defense_name == "no_defense"]
    baseline = _mean_bool(baseline_values)
    if baseline is None:
        return []
    by_defense: dict[str, list[bool]] = defaultdict(list)
    for item in clean_metrics:
        by_defense[item.defense_name].append(bool(item.clean_success))
    rows: list[dict] = []
    for defense_name in sorted(by_defense):
        defense_tsr = _mean_bool(by_defense[defense_name])
        rows.append(
            {
                "defense_name": defense_name,
                "baseline_clean_tsr": baseline,
                "defense_clean_tsr": defense_tsr,
                "benign_drop": baseline - defense_tsr if defense_tsr is not None else None,
                "n": len(by_defense[defense_name]),
            }
        )
    return rows
