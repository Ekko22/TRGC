import json
import subprocess
import sys
from pathlib import Path

from lmas_trgc.analysis.run_summary import build_run_summary_record
from lmas_trgc.analysis.standard_metrics import build_standard_run_metrics
from lmas_trgc.judging.judge import create_judge
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.logging.batch_writer import StageBBatchWriter
from lmas_trgc.runners.single_run import MessageEvent, SingleRunResult
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set


def _result(run_id: str, attack: str, defense: str) -> SingleRunResult:
    attacked = attack != "none"
    return SingleRunResult(
        run_id=run_id,
        task_id="local_mas_safety_001",
        topology="graph",
        attack_type=attack,
        defense_name=defense,
        completed=True,
        final_agent="A7",
        final_context="safe",
        final_output="Final answer: safe",
        message_events=[
            MessageEvent(
                step_id=1,
                sender="A1",
                receiver="A7",
                message_id=f"{run_id}_msg",
                delivered=True,
                gate_action="ALLOW",
                context_bucket="trusted",
                blocked=False,
                downweighted=False,
                rerouted_to_sv=False,
                attack_injected=attacked,
                attack_type=attack if attacked else None,
                attack_changed_fields=["content"] if attacked else [],
                route_meta={"edge": "A1->A7", "critical_nodes_reachable": ["A7"]},
                source_model="deepseek-test",
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            )
        ],
        total_messages=1,
        delivered_messages=1,
        blocked_messages=0,
        downweighted_messages=0,
        rerouted_messages=0,
        attacked_messages=1 if attacked else 0,
        total_llm_calls=1,
        total_input_tokens=10,
        total_output_tokens=5,
        total_tokens=15,
    )


def test_stage_c_manifest_pilot_aggregate_script(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    task_packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    writer = RunArtifactWriter(tmp_path, stage_name="stage_c_manifest", overwrite=True)
    batch_writer = StageBBatchWriter(tmp_path, overwrite=True, batch_stage_name="stage_c_manifest_batches")
    batch_dir = batch_writer.make_batch_dir("batch_test")
    records = []
    for index, (attack, defense) in enumerate([("none", "no_defense"), ("message_poisoning", "trgc")]):
        result = _result(f"run_stage_c_test_{index}", attack, defense)
        judge_outcome = create_judge("rule_based").judge(result, task_packet)
        standard_metrics = build_standard_run_metrics(build_run_summary_record(result, task_packet), judge_outcome)
        manifest = writer.write_run_artifact(
            result,
            task_packet,
            {"stage": "stage_c_manifest_test"},
            judge_outcome=judge_outcome,
            standard_metrics=standard_metrics,
        )
        records.append(
            {
                "batch_id": "batch_test",
                "run_id": result.run_id,
                "task_id": result.task_id,
                "dataset": task_packet.task.dataset,
                "topology": result.topology,
                "attack": attack,
                "defense": defense,
                "artifact_dir": manifest.artifact_dir,
                "completed": True,
                "failed": False,
                "error": None,
            }
        )
    batch_writer.write_run_index(batch_dir, records)

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "aggregate_stage_c_manifest_pilot.py"),
        "--batch-dir",
        str(batch_dir),
        "--group-by",
        "dataset",
        "--group-by",
        "defense_name",
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["total_runs"] == 2
    assert payload["total_llm_calls"] == 2
    assert "clean_tsr" in payload
    assert "robust_tsr" in payload
    assert payload["groups"]
