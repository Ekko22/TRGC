from pathlib import Path

from lmas_trgc.analysis.run_summary import build_run_summary_record
from lmas_trgc.analysis.standard_metrics import build_standard_run_metrics
from lmas_trgc.judging.judge import create_judge
from lmas_trgc.logging.artifact_loader import load_judge_outcome, load_standard_metrics, validate_run_artifact
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.runners.single_run import MessageEvent, SingleRunResult
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def test_artifact_writer_with_judge_outputs(tmp_path):
    task_packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    result = SingleRunResult(
        run_id="run_judge_artifact",
        task_id=task_packet.task.task_id,
        topology="graph",
        attack_type="message_poisoning",
        defense_name="trgc",
        completed=True,
        final_agent="A7",
        final_context="context",
        final_output="Final answer: safe",
        message_events=[
            MessageEvent(
                step_id=1,
                sender="A1",
                receiver="A7",
                message_id="msg",
                delivered=True,
                gate_action="ALLOW",
                context_bucket="trusted",
                blocked=False,
                downweighted=False,
                rerouted_to_sv=False,
            )
        ],
        total_messages=1,
        delivered_messages=1,
        blocked_messages=0,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=1,
    )
    judge_outcome = create_judge("mock_protocol").judge(result, task_packet)
    standard = build_standard_run_metrics(build_run_summary_record(result, task_packet), judge_outcome)
    manifest = RunArtifactWriter(tmp_path).write_run_artifact(
        result,
        task_packet,
        config_snapshot={"stage": "test"},
        judge_outcome=judge_outcome,
        standard_metrics=standard,
    )
    run_dir = Path(manifest.artifact_dir)
    assert (run_dir / "judge_outcome.json").exists()
    assert (run_dir / "standard_metrics.json").exists()
    assert load_judge_outcome(run_dir) is not None
    assert load_standard_metrics(run_dir) is not None
    assert validate_run_artifact(run_dir, require_judge=True) is True
    assert "Final answer: safe" not in (run_dir / "run_summary.json").read_text(encoding="utf-8")
