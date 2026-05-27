from pathlib import Path

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.logging.artifact_loader import validate_run_artifact
from lmas_trgc.runners.batch_runner import StageBBatchConfig, StageBBatchRunner
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.task_resolver import TaskResolver, TaskResolverConfig
from lmas_trgc.topology.manager import TopologyManager


def test_stage_b_batch_runner_writes_artifacts_and_batch_index(tmp_path):
    tasks = TaskResolver().resolve(
        TaskResolverConfig(mode="synthetic", datasets=["local_mas_safety"], task_limit_per_dataset=2)
    )
    topology_manager = TopologyManager()
    runner = StageBBatchRunner(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=load_agent_profiles(),
        prompt_builder=PromptBuilder(),
        safety_verifier=SafetyVerifier(mode="mock"),
        output_root=tmp_path,
    )
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
