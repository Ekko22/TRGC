from lmas_trgc.analysis.effect_aggregate import (
    aggregate_standard_metrics,
    compute_benign_drop_by_defense,
    group_standard_metrics,
)
from lmas_trgc.analysis.standard_metrics import StandardRunMetrics


def _metric(
    run_id: str,
    attack_type: str,
    defense_name: str,
    task_success: bool,
    attack_success: bool | None = None,
    topology: str = "graph",
) -> StandardRunMetrics:
    return StandardRunMetrics(
        run_id=run_id,
        task_id="task",
        dataset="local_mas_safety",
        domain="local_mas_safety",
        topology=topology,
        attack_type=attack_type,
        defense_name=defense_name,
        judge_mode="rule_based",
        valid_for_paper=True,
        clean_success=task_success if attack_type == "none" else None,
        robust_success=task_success if attack_type != "none" else None,
        attack_success=attack_success if attack_type != "none" else None,
        safety_violation=False,
        task_success=task_success,
        answer_correct=task_success,
    )


def test_aggregate_empty():
    aggregate = aggregate_standard_metrics([])
    assert aggregate["total_runs"] == 0
    assert aggregate["clean_tsr"] is None


def test_standard_effect_rates():
    metrics = [
        _metric("clean_1", "none", "no_defense", True),
        _metric("clean_2", "none", "trgc", False),
        _metric("attack_1", "message_poisoning", "trgc", True, attack_success=False),
        _metric("attack_2", "message_poisoning", "trgc", False, attack_success=True),
    ]
    aggregate = aggregate_standard_metrics(metrics)
    assert aggregate["clean_tsr"] == 0.5
    assert aggregate["robust_tsr"] == 0.5
    assert aggregate["asr"] == 0.5
    assert aggregate["svr"] == 0.0


def test_group_standard_metrics():
    groups = group_standard_metrics(
        [_metric("run_1", "none", "no_defense", True, topology="graph"), _metric("run_2", "none", "trgc", True, topology="tree")],
        ["topology", "defense_name"],
    )
    assert {row["topology"] for row in groups} == {"graph", "tree"}


def test_benign_drop_by_defense():
    rows = compute_benign_drop_by_defense(
        [
            _metric("base", "none", "no_defense", True),
            _metric("trgc", "none", "trgc", False),
        ]
    )
    trgc = [row for row in rows if row["defense_name"] == "trgc"][0]
    assert trgc["benign_drop"] == 1.0
