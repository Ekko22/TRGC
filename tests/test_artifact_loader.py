import pytest

from lmas_trgc.logging.artifact_loader import (
    load_manifest,
    load_message_events,
    load_metrics,
    load_run_summary,
    validate_run_artifact,
)
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.runners.single_run import MessageEvent, SingleRunResult
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def _write_artifact(tmp_path):
    result = SingleRunResult(
        run_id="run_loader_test",
        task_id="local_mas_safety_000",
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        final_context="final context",
        message_events=[
            MessageEvent(
                step_id=1,
                sender="A3",
                receiver="A7",
                message_id="msg_loader",
                delivered=True,
                gate_action="ALLOW",
                context_bucket="trusted",
                blocked=False,
                downweighted=False,
                rerouted_to_sv=False,
                attack_injected=True,
                attack_type="message_poisoning",
                attack_changed_fields=["content"],
                route_meta={"edge": "A3->A7", "critical_nodes_reachable": ["A7"]},
            )
        ],
        total_messages=1,
        delivered_messages=1,
        blocked_messages=0,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=1,
    )
    task_packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    manifest = RunArtifactWriter(tmp_path).write_run_artifact(result, task_packet, {"topology": "graph"})
    return tmp_path / "stage_b" / manifest.run_id


def test_artifact_loader_validates_and_loads(tmp_path):
    run_dir = _write_artifact(tmp_path)
    assert validate_run_artifact(run_dir) is True
    assert load_run_summary(run_dir).run_id == "run_loader_test"
    assert len(load_message_events(run_dir)) == 1
    assert load_metrics(run_dir).attacked_messages == 1
    assert load_manifest(run_dir).schema_version == "1.0"


def test_artifact_loader_rejects_missing_required_file(tmp_path):
    run_dir = _write_artifact(tmp_path)
    (run_dir / "metrics.json").unlink()
    with pytest.raises(ValueError):
        validate_run_artifact(run_dir)
