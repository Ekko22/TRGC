from lmas_trgc.analysis.metrics import compute_metrics_from_run_result
from lmas_trgc.runners.single_run import MessageEvent, SingleRunResult


def test_compute_metrics_from_run_result_rates_and_critical_reach():
    result = SingleRunResult(
        run_id="run_metrics",
        task_id="task_metrics",
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        final_context="final context",
        message_events=[
            MessageEvent(
                step_id=1,
                sender="A1",
                receiver="A2",
                message_id="msg_1",
                delivered=True,
                gate_action="ALLOW",
                context_bucket="trusted",
                blocked=False,
                downweighted=False,
                rerouted_to_sv=False,
            ),
            MessageEvent(
                step_id=2,
                sender="A3",
                receiver="A7",
                message_id="msg_2",
                delivered=False,
                gate_action="BLOCK",
                context_bucket="safety_notice",
                blocked=True,
                downweighted=False,
                rerouted_to_sv=False,
                attack_injected=True,
                attack_type="message_poisoning",
                attack_changed_fields=["content"],
            ),
            MessageEvent(
                step_id=3,
                sender="A4",
                receiver="A5",
                message_id="msg_3",
                delivered=True,
                gate_action="DOWNWEIGHT",
                context_bucket="untrusted",
                blocked=False,
                downweighted=True,
                rerouted_to_sv=True,
                attack_injected=True,
                attack_type="message_poisoning",
                attack_changed_fields=["content"],
            ),
            MessageEvent(
                step_id=4,
                sender="A5",
                receiver="A6",
                message_id="msg_4",
                delivered=True,
                gate_action="ALLOW",
                context_bucket="trusted",
                blocked=False,
                downweighted=False,
                rerouted_to_sv=False,
            ),
        ],
        total_messages=4,
        delivered_messages=3,
        blocked_messages=1,
        downweighted_messages=1,
        rerouted_messages=1,
        attacked_messages=2,
    )
    metrics = compute_metrics_from_run_result(result, "task_metrics", "graph", "message_poisoning", "trgc")
    assert metrics.attack_injection_rate == 0.5
    assert metrics.block_rate == 0.25
    assert metrics.critical_node_reach_count >= 1
    assert metrics.critical_node_reach_rate > 0
    assert metrics.propagation_depth_proxy == 3
