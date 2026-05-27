from lmas_trgc.agents.prompt_builder import PromptBuilder
from lmas_trgc.agents.roles import load_agent_profiles
from lmas_trgc.defenses.factory import create_defense_adapter
from lmas_trgc.defenses.trgc.safety_verifier import SafetyVerifier
from lmas_trgc.llm.mock_client import MockLLMClient
from lmas_trgc.runners.protocol import ProtocolManager
from lmas_trgc.runners.single_run import SingleRunConfig, SingleRunExecutor
from lmas_trgc.tasks.anchors import build_task_packet
from lmas_trgc.tasks.local_synthetic import generate_local_mas_safety_set
from lmas_trgc.topology.manager import TopologyManager


def _run(topology: str, defense: str):
    topology_manager = TopologyManager()
    profiles = load_agent_profiles()
    verifier = SafetyVerifier(mode="mock")
    adapter = create_defense_adapter(defense, topology_manager, safety_verifier=verifier)
    executor = SingleRunExecutor(
        topology_manager=topology_manager,
        protocol_manager=ProtocolManager(topology_manager=topology_manager),
        agent_profiles=profiles,
        defense_adapter=adapter,
        llm_clients_by_agent={agent_id: MockLLMClient(model_name=f"mock-{agent_id}") for agent_id in profiles},
        prompt_builder=PromptBuilder(),
    )
    packet = build_task_packet(generate_local_mas_safety_set(1)[0])
    return executor.run(
        packet,
        SingleRunConfig(
            run_id=f"test_{topology}_{defense}",
            topology=topology,
            attack_type="none",
            defense_name=defense,
            use_mock_llm=True,
        ),
    )


def test_star_no_defense_completes():
    result = _run("star", "no_defense")
    assert result.completed is True
    assert result.total_messages > 0


def test_chain_no_defense_delivers_to_a7():
    result = _run("chain", "no_defense")
    assert result.final_agent == "A7"
    assert result.delivered_messages >= 1
    assert "Trusted messages" in result.final_context or "Safety notices" in result.final_context


def test_graph_and_tree_trgc_complete_and_exclude_sv():
    for topology in ["graph", "tree"]:
        result = _run(topology, "trgc")
        assert result.completed is True
        assert result.total_messages > 0
        assert result.delivered_messages + result.blocked_messages <= result.total_messages
        assert result.final_agent == "A7"
        for event in result.message_events:
            assert event.sender != "SV"
            assert event.receiver != "SV"
