import json
from pathlib import Path

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.logging.artifact_loader import validate_run_artifact
from lmas_trgc.runners.batch_runner import StageBBatchConfig, StageBBatchRunner
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunExecutor
from lmas_trgc.runners.task_resolver import TaskResolver, TaskResolverConfig
from lmas_trgc.topology.manager import TopologyManager


def _stage_b_runner(tmp_path):
    topology_manager = TopologyManager()
    return StageBBatchRunner(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=load_agent_profiles(),
        prompt_builder=PromptBuilder(),
        safety_verifier=SafetyVerifier(mode="mock"),
        output_root=tmp_path,
    )


def test_stage_b_batch_runner_writes_artifacts_and_batch_index(tmp_path):
    tasks = TaskResolver().resolve(
        TaskResolverConfig(mode="synthetic", datasets=["local_mas_safety"], task_limit_per_dataset=2)
    )
    runner = _stage_b_runner(tmp_path)
    result = runner.run_batch(
        tasks,
        StageBBatchConfig(
            batch_id="batch_runner_test",
            task_source_mode="synthetic",
            datasets=["local_mas_safety"],
            task_limit_per_dataset=2,
            topologies=["graph"],
            attacks=["message_poisoning"],
            defenses=["no_defense", "trgc"],
            output_root=str(tmp_path),
            overwrite=False,
            max_workers=2,
            show_progress=False,
        ),
    )
    assert result.total_runs == 4
    assert result.successful_runs == 4
    assert result.failed_runs == 0
    assert len(result.artifact_dirs) == 4
    assert result.batch_dir and Path(result.batch_dir).exists()
    assert result.run_index_path and Path(result.run_index_path).exists()
    assert result.aggregate_metrics_path and Path(result.aggregate_metrics_path).exists()
    for artifact_dir in result.artifact_dirs:
        assert validate_run_artifact(Path(artifact_dir)) is True
    run_index = [
        json.loads(line)
        for line in Path(result.run_index_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["run_order"] for record in run_index] == [0, 1, 2, 3]


def test_stage_b_batch_runner_records_failed_run_without_blocking_others(tmp_path, monkeypatch):
    tasks = TaskResolver().resolve(
        TaskResolverConfig(mode="synthetic", datasets=["local_mas_safety"], task_limit_per_dataset=2)
    )
    runner = _stage_b_runner(tmp_path)
    original_run = SingleRunExecutor.run
    failed_task_id = tasks[0].task_id

    def failing_run(self, task_packet, config):
        if task_packet.task.task_id == failed_task_id and config.defense_name == "trgc":
            raise RuntimeError("intentional failure sk-secret")
        return original_run(self, task_packet, config)

    monkeypatch.setattr(SingleRunExecutor, "run", failing_run)
    result = runner.run_batch(
        tasks,
        StageBBatchConfig(
            batch_id="batch_runner_failure_test",
            task_source_mode="synthetic",
            datasets=["local_mas_safety"],
            task_limit_per_dataset=2,
            topologies=["graph"],
            attacks=["message_poisoning"],
            defenses=["no_defense", "trgc"],
            output_root=str(tmp_path),
            overwrite=False,
            max_workers=2,
            show_progress=False,
        ),
    )

    assert result.completed is False
    assert result.total_runs == 4
    assert result.successful_runs == 3
    assert result.failed_runs == 1
    assert len(result.failures) == 1
    assert result.failures[0]["error_type"] == "RuntimeError"
    assert "[REDACTED]" in result.failures[0]["error"]
    for artifact_dir in result.artifact_dirs:
        assert validate_run_artifact(Path(artifact_dir)) is True
    run_index = [
        json.loads(line)
        for line in Path(result.run_index_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["run_order"] for record in run_index] == [0, 1, 2, 3]
    assert sum(1 for record in run_index if record["failed"]) == 1
