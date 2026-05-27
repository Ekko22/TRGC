from lmas_trgc.analysis.batch_aggregate import aggregate_metrics, group_metrics, metrics_to_rows
from lmas_trgc.logging.schemas import MetricsRecord


def _metric(run_id: str, topology: str, block_rate: float) -> MetricsRecord:
    return MetricsRecord(
        run_id=run_id,
        task_id="task",
        topology=topology,
        attack_type="message_poisoning",
        defense_name="trgc",
        total_messages=10,
        delivered_messages=8,
        blocked_messages=2,
        downweighted_messages=1,
        rerouted_messages=1,
        attacked_messages=5,
        attack_injection_rate=0.5,
        block_rate=block_rate,
        downweight_rate=0.1,
        reroute_rate=0.1,
        delivery_rate=0.8,
        critical_node_reach_count=2,
        critical_node_reach_rate=0.4,
        propagation_depth_proxy=3,
    )


def test_aggregate_metrics_empty():
    aggregate = aggregate_metrics([])
    assert aggregate["total_runs"] == 0
    assert aggregate["total_messages"] == 0


def test_aggregate_metrics_means():
    aggregate = aggregate_metrics([_metric("run_1", "graph", 0.2), _metric("run_2", "graph", 0.4)])
    assert aggregate["total_runs"] == 2
    assert aggregate["mean_block_rate"] == 0.30000000000000004
    assert aggregate["total_attacked_messages"] == 10


def test_group_metrics_by_topology():
    groups = group_metrics([_metric("run_1", "graph", 0.2), _metric("run_2", "tree", 0.4)], ["topology"])
    assert {row["topology"] for row in groups} == {"graph", "tree"}
    assert all(row["total_runs"] == 1 for row in groups)


def test_metrics_to_rows_fields():
    rows = metrics_to_rows([_metric("run_1", "graph", 0.2)])
    row = rows[0]
    assert row["run_id"] == "run_1"
    assert "critical_node_reach_rate" in row
    assert "propagation_depth_proxy" in row
