import json

from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.runners.single_run import MessageEvent, SingleRunResult
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def _fake_result() -> SingleRunResult:
    return SingleRunResult(
        run_id="run_artifact_test",
        task_id="local_mas_safety_000",
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        final_context="do not persist this final context text",
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
                route_meta={
                    "edge": "A1->A2",
                    "fanout_count": 3,
                    "critical_nodes_reachable": ["A7"],
                    "exposure_level": "medium",
                },
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
                reason="unsafe",
                route_meta={
                    "edge": "A3->A7",
                    "fanout_count": 1,
                    "critical_nodes_reachable": ["A7"],
                    "exposure_level": "high",
                },
            ),
        ],
        total_messages=2,
        delivered_messages=1,
        blocked_messages=1,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=1,
    )


def test_run_artifact_writer_writes_required_files(tmp_path):
    task_packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    writer = RunArtifactWriter(tmp_path, overwrite=False)
    manifest = writer.write_run_artifact(_fake_result(), task_packet, {"api_key": "secret-value", "topology": "graph"})
    run_dir = tmp_path / "stage_b" / "run_artifact_test"

    for filename in manifest.files.values():
        assert (run_dir / filename).exists()

    jsonl_lines = (run_dir / "message_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(jsonl_lines) == 2
    assert (run_dir / "message_events.csv").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "manifest.json").exists()

    summary_text = (run_dir / "run_summary.json").read_text(encoding="utf-8")
    assert "do not persist this final context text" not in summary_text
    config_snapshot = json.loads((run_dir / "config_snapshot.json").read_text(encoding="utf-8"))
    assert config_snapshot["api_key"] == "REDACTED"
