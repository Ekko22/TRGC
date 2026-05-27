import pytest

from lmas_trgc.logging.schemas import MessageEventRecord, MetricsRecord, RunArtifactManifest, RunSummaryRecord


def test_run_summary_record_constructs():
    record = RunSummaryRecord(
        run_id="run_1",
        task_id="task_1",
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        total_messages=1,
        delivered_messages=1,
        blocked_messages=0,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=1,
        created_at="2026-05-28T00:00:00+00:00",
    )
    assert record.run_id == "run_1"


def test_message_event_record_default_lists_are_not_shared():
    first = MessageEventRecord(
        run_id="run_1",
        task_id="task_1",
        step_id=1,
        sender="A1",
        receiver="A7",
        message_id="msg_1",
        delivered=True,
        gate_action="ALLOW",
        context_bucket="trusted",
        blocked=False,
        downweighted=False,
        rerouted_to_sv=False,
        topology="graph",
    )
    second = MessageEventRecord(
        run_id="run_1",
        task_id="task_1",
        step_id=1,
        sender="A2",
        receiver="A7",
        message_id="msg_2",
        delivered=True,
        gate_action="ALLOW",
        context_bucket="trusted",
        blocked=False,
        downweighted=False,
        rerouted_to_sv=False,
        topology="graph",
    )
    first.attack_changed_fields.append("content")
    assert second.attack_changed_fields == []


def test_metrics_record_rates_available():
    record = MetricsRecord(
        run_id="run_1",
        task_id="task_1",
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        total_messages=4,
        delivered_messages=3,
        blocked_messages=1,
        downweighted_messages=0,
        rerouted_messages=1,
        attacked_messages=2,
        attack_injection_rate=0.5,
        block_rate=0.25,
        downweight_rate=0.0,
        reroute_rate=0.25,
        delivery_rate=0.75,
        critical_node_reach_count=1,
        critical_node_reach_rate=0.5,
        propagation_depth_proxy=3,
    )
    assert record.delivery_rate == 0.75


def test_run_artifact_manifest_constructs():
    manifest = RunArtifactManifest(
        run_id="run_1",
        artifact_dir="/tmp/run_1",
        files={"run_summary": "run_summary.json"},
        created_at="2026-05-28T00:00:00+00:00",
    )
    assert manifest.schema_version == "1.0"


def test_negative_message_count_rejected():
    with pytest.raises(ValueError):
        RunSummaryRecord(
            run_id="run_1",
            task_id="task_1",
            topology="graph",
            attack_type="none",
            defense_name="trgc",
            completed=True,
            final_agent="A7",
            total_messages=-1,
            delivered_messages=0,
            blocked_messages=0,
            downweighted_messages=0,
            rerouted_messages=0,
            attacked_messages=0,
            created_at="2026-05-28T00:00:00+00:00",
        )
