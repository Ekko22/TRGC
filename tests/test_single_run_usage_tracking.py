import json
from pathlib import Path

from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.attacks.manager import AttackManager
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.logging.artifact_writer import RunArtifactWriter
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set
from lmas_trgc.topology.manager import TopologyManager


def _run_mock_single():
    topology_manager = TopologyManager()
    profiles = load_agent_profiles()
    executor = SingleRunExecutor(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=profiles,
        defense_adapter=create_defense_adapter("trgc", topology_manager, safety_verifier=SafetyVerifier(mode="mock")),
        llm_clients_by_agent={agent_id: MockLLMClient(model_name=f"mock-{agent_id}") for agent_id in profiles},
        prompt_builder=PromptBuilder(),
        attack_manager=AttackManager("message_poisoning"),
    )
    task_packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    result = executor.run(
        task_packet,
        SingleRunConfig(
            run_id="run_usage",
            topology="graph",
            attack_type="message_poisoning",
            defense_name="trgc",
            max_steps=2,
        ),
    )
    return result, task_packet


def test_single_run_usage_tracking_fields():
    result, _ = _run_mock_single()
    assert result.completed is True
    assert result.total_llm_calls > 0
    assert result.total_tokens > 0
    event = result.message_events[0]
    assert event.source_model
    assert event.input_tokens > 0
    assert event.output_tokens > 0
    assert event.total_tokens > 0


def test_artifact_metrics_include_total_tokens(tmp_path):
    result, task_packet = _run_mock_single()
    manifest = RunArtifactWriter(tmp_path, overwrite=True).write_run_artifact(result, task_packet, {"stage": "test"})
    metrics = json.loads((Path(manifest.artifact_dir) / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["total_tokens"] > 0
    assert metrics["total_llm_calls"] > 0
